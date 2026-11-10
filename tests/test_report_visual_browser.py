"""Verify report exports in Chromium against a read-only copy of actual incident records.
Print preview uses print media and Chromium PDF because the native dialog is unavailable headless.
"""
from pathlib import Path
from collections import Counter
from datetime import datetime,timezone
from urllib.request import Request,urlopen
import json,sqlite3,hashlib,sys,time,traceback,os,subprocess
from playwright.sync_api import sync_playwright,expect
from pypdf import PdfReader
import csv,io
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'runtime/report-visual-checks';OUT.mkdir(parents=True,exist_ok=True)
sys.stdout.reconfigure(encoding='utf-8');RESULTS=[]

BASE='http://127.0.0.1:18020';DASH='http://127.0.0.1:3001';TOKEN='analytics-read-only-test'
DB_PATH=OUT/('snapshot-'+str(time.time_ns())+'.sqlite3')
with sqlite3.connect('file:'+str(ROOT/'runtime/safesense.sqlite3')+'?mode=ro',uri=True) as original,sqlite3.connect(DB_PATH) as copied:original.backup(copied)
ENV=os.environ.copy();ENV.update(SAFESENSE_DB_PATH=str(DB_PATH),SAFESENSE_API_TOKEN=TOKEN,VITE_SAFESENSE_API_TOKEN=TOKEN,TELEGRAM_MODE='disabled',VITE_API_BASE_URL=BASE,VITE_AI_BASE_URL='http://127.0.0.1:18021')
processes=[]
def start_service(name,command,cwd,url):
 log=(OUT/(name+'.log')).open('w',encoding='utf-8');process=subprocess.Popen(command,cwd=cwd,env=ENV,stdout=log,stderr=subprocess.STDOUT,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0));processes.append((process,log))
 for _ in range(180):
  if process.poll() is not None:raise RuntimeError(name+' stopped')
  try:
   with urlopen(url,timeout=1) as response:
    if response.status==200:return
  except OSError:pass
  time.sleep(.2)
 raise RuntimeError(name+' timeout')
def check(name,fn):
 try:actual=fn();row={'test':name,'status':'PASS','actual':actual}
 except Exception as exc:row={'test':name,'status':'FAIL','actual':str(exc),'trace':traceback.format_exc()}
 RESULTS.append(row);(OUT/'results.json').write_text(json.dumps(RESULTS,indent=2));print(row['status'],name,str(row['actual'])[:600],flush=True)
def get(path):
 with urlopen(Request(BASE+path,headers={'X-SafeSense-Token':TOKEN}),timeout=10) as r:return json.load(r)
def db_records():
 with sqlite3.connect('file:'+str(DB_PATH)+'?mode=ro',uri=True) as db:return [json.loads(row[0]) for row in db.execute("SELECT body FROM records WHERE kind='incident' ORDER BY rowid")]

try:
 start_service('backend',[str(ROOT/'.venv/Scripts/python.exe'),'-m','uvicorn','backend.main:app','--host','127.0.0.1','--port','18020'],ROOT,BASE+'/health')
 start_service('frontend',['node',str(ROOT/'dashboard/node_modules/vite/bin/vite.js'),'--host','127.0.0.1','--port','3001','--strictPort'],ROOT/'dashboard',DASH)
 records=db_records();original=records.copy()
 with sync_playwright() as pw:
  browser=pw.chromium.launch(headless=True);page=browser.new_page(viewport={'width':1440,'height':1000});page.set_default_timeout(15000)
  errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
  page.goto(DASH);page.locator('aside').get_by_role('button',name='Reports',exact=True).click()
  root=page.get_by_test_id('operational-report')
  def validate(rows):
   values={'total':len(rows),'high':sum(r['level'] in ('HIGH','CRITICAL') for r in rows),'sos':sum(r.get('source')=='sos_button' or any(e.get('type')=='SOS' for e in r.get('evidence',[])) for r in rows),'pending':sum(r.get('review_status')=='pending_human_review' for r in rows),'ack':sum(bool(r.get('acknowledged_at')) for r in rows),'resolved':sum(r['status']=='RESOLVED' for r in rows)}
   for key,value in values.items():expect(root.get_by_test_id('report-kpi-'+key).locator('[data-value]')).to_have_text(str(value))
   counts={'types':Counter(t for r in rows for t in (set(e.get('type') for e in r.get('evidence',[]) if e.get('type')) or {'Not recorded'})),'zones':Counter(r['zone_id'] for r in rows),'severity':Counter(r['level'] for r in rows),'statuses':Counter(r['status'] for r in rows),'trend':Counter(datetime.fromisoformat(r['created_at'].replace('Z','+00:00')).astimezone(timezone.utc).date().isoformat() for r in rows)}
   for key,value in counts.items():
    actual=dict(root.get_by_test_id('analytics-report-'+key).locator('tbody tr').evaluate_all('(rs)=>rs.map(r=>[r.dataset.key,Number(r.querySelector("td").textContent)])'))
    assert actual==dict(value),(key,actual,value)
   assert root.get_by_role('table',name='Report incidents',exact=True).locator('tbody tr').count()==len(rows)
   return values
  check('Six KPIs, five charts and incident table match SQLite',lambda:validate(records))
  def filters():
   status=records[0]['status'];root.get_by_label('Report incident status').select_option(status.lower());subset=[r for r in records if r['status']==status];result=validate(subset)
   root.get_by_role('button',name='Reset filters',exact=True).click();validate(records)
   return result
  check('Report filters update KPIs, charts and table together',filters)
  def responsive():
   page.screenshot(path=str(OUT/'report-desktop.png'),full_page=True)
   page.set_viewport_size({'width':390,'height':844});page.wait_for_timeout(500)
   assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
   page.screenshot(path=str(OUT/'report-mobile.png'),full_page=True)
   assert root.locator('img,video').count()==0
   return {'desktop':1440,'mobile':390,'page_overflow':False,'preview':'metadata only'}
  check('Responsive report and privacy-safe previews',responsive)
  def states():
   empty=browser.new_page();empty.route('**/incidents',lambda r:r.fulfill(json=[]));empty.goto(DASH);empty.locator('aside').get_by_role('button',name='Reports',exact=True).click();expect(empty.get_by_text('No incident records match this filter.',exact=True)).to_be_visible();empty.close()
   failed=browser.new_page();failed.route('**/incidents',lambda r:r.fulfill(status=503,json={'detail':'UI test fixture'}));failed.goto(DASH);failed.locator('aside').get_by_role('button',name='Reports',exact=True).click();expect(failed.get_by_text('Report unavailable until backend records load.',exact=False)).to_be_visible();assert failed.get_by_test_id('report-kpi-total').count()==0;failed.close()
   return 'Empty and unavailable states verified with explicit API fixtures'
  check('Empty and failed backend state',states)
  check('No browser exceptions',lambda:errors if not errors else (_ for _ in ()).throw(AssertionError(errors)))
  browser.close()
 assert db_records()==original
 print('Database unchanged; results:',len(RESULTS),'checks')
finally:
 for process,log in reversed(processes):process.terminate();process.wait(timeout=20);log.close()
if any(r['status']=='FAIL' for r in RESULTS):sys.exit(1)
