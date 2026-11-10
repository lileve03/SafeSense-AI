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
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'runtime/reports-task6';OUT.mkdir(parents=True,exist_ok=True)
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
 records=get('/incidents');assert records
 with sync_playwright() as pw:
  browser=pw.chromium.launch(headless=True);page=browser.new_page(viewport={'width':1440,'height':1000});page.set_default_timeout(20000)
  errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
  page.goto(DASH);page.locator('aside').get_by_role('button',name='Reports',exact=True).click()
  root=page.get_by_test_id('incident-report');expect(root).to_be_visible()
  identifier=page.get_by_label('Report incident',exact=True).input_value();report=get('/incidents/'+identifier+'/report')
  def pdf_check():
   with page.expect_download() as d:root.get_by_role('button',name='Download PDF',exact=True).click()
   path=OUT/'selected-report.pdf';d.value.save_as(path)
   pdf=PdfReader(path);text='\n'.join(p.extract_text() for p in pdf.pages);(OUT/'selected-report.txt').write_text(text,encoding='utf-8')
   assert identifier in text
   for term in ['Summary','Evidence','Response','Analysis',report['zone_id'],report['status']]:assert term in text,term
   for p in pdf.pages:
    assert abs(float(p.mediabox.width)-595.28)<1
    assert abs(float(p.mediabox.height)-841.89)<1
    assert len(p.extract_text())>30
    assert len(p.images)==0
   return {'file':str(path),'bytes':path.stat().st_size,'pages':len(pdf.pages),'extractable_characters':len(text),'A4':True}
  check('Download PDF: actual selected report, readable text, A4 pagination',pdf_check)
  def csv_check():
   with page.expect_download() as d:root.get_by_role('button',name='Download CSV',exact=True).click()
   path=OUT/'selected-report.csv';d.value.save_as(path);data=path.read_bytes();assert data.startswith(b'\xef\xbb\xbf')
   rows=list(csv.DictReader(io.StringIO(data.decode('utf-8-sig'))));assert len(rows)==1
   row=rows[0];assert row['incident_id']==identifier and row['zone']==report['zone_id'] and row['status']==report['status']
   assert row['event_type']=='; '.join(e['type'] for e in report['evidence'])
   return {'file':str(path),'bytes':len(data),'records':len(rows),'columns':list(row)}
  check('Download CSV: actual selected incident and UTF-8 columns',csv_check)
  def print_check():
   page.add_init_script("window.print=function(){window.__printed=true}")
   # Patch iframe print before invoking it; Chromium headless has no native preview UI.
   page.evaluate("""() => { const append= document.body.append.bind(document.body);document.body.append=(...nodes)=>{for(const n of nodes)if(n.tagName==='IFRAME'){const original=n.onload;n.onload=()=>{n.contentWindow.print=()=>{n.dataset.printInvoked='true'};original()}}return append(...nodes)}}""")
   root.get_by_role('button',name='Print / Save as PDF',exact=True).click()
   frame=page.locator('iframe[title="Print SafeSense report"]');expect(frame).to_have_attribute('data-print-invoked','true')
   html=frame.evaluate('(f)=>f.contentDocument.documentElement.outerHTML');(OUT/'print-report.html').write_text(html,encoding='utf-8')
   preview=browser.new_page();preview.set_content(html);preview.emulate_media(media='print')
   assert preview.locator('button,nav,aside,video,img').count()==0
   assert preview.locator('h2').all_text_contents()==['Summary','Evidence','Response','Analysis']
   assert identifier in preview.inner_text('body')
   preview.pdf(path=str(OUT/'print-preview.pdf'),prefer_css_page_size=True)
   preview.screenshot(path=str(OUT/'print-preview.png'),full_page=True)
   pdf=PdfReader(OUT/'print-preview.pdf');assert all(abs(float(p.mediabox.width)-595.28)<2 for p in pdf.pages)
   preview.close();frame.evaluate('(f)=>f.remove()')
   return {'browser_print_invoked':True,'preview_pdf':str(OUT/'print-preview.pdf'),'pages':len(pdf.pages),'native_dialog':'Headless browser; print document verified via print media and Chromium PDF'}
  check('Print function and isolated A4 print preview',print_check)
  def filters():
   status=report['status'].lower();day=report['created_at'][:10]
   page.get_by_label('Report incident status').select_option(status)
   page.get_by_label('Report from date').fill(day);page.get_by_label('Report to date').fill(day)
   expected={r['id'] for r in records if r['status'].lower()==status and r['created_at'][:10]==day}
   actual=set(page.get_by_label('Report incident',exact=True).locator('option').evaluate_all('(els)=>els.map(e=>e.value)'))
   assert actual==expected,(actual,expected)
   page.get_by_label('Report from date').fill('2099-01-01');page.get_by_label('Report to date').fill('2099-01-02')
   expect(page.get_by_test_id('incident-report')).to_have_count(0)
   expect(page.get_by_role('button',name='Download PDF',exact=True)).to_have_count(0)
   return {'matched_incidents':len(expected),'empty_scope_has_no_export':True}
  check('UTC date and status filters constrain selected report',filters)
  def security():
   return page.evaluate(r"""async()=>{const m=await import('/src/lib/reportExport.ts');
    const cells=['=1+1',' +SUM(A1)','@evil','-1','\tcmd','normal,comma','quote"text','line\nnext'];
    const escaped=cells.map(m.csvCell);
    if(!escaped.slice(0,5).every(x=>x.startsWith('"\'')))throw Error('formula protection');
    const r={id:'privacy-test',zone_type:'PRIVATE',evidence:[{id:'e',type:'SOS',evidence_reference:'SECRET.mp4',evidence_media:[{url:'SECRET.jpg'}]}]};
    const outputs=[m.reportCsv(r),m.reportPrintHtml(r,'scope','date'),m.reportPdf(r,'scope','date').output()];
    if(outputs.some(x=>x.includes('SECRET')))throw Error('private media leaked');
    const long={...r,history:Array.from({length:100},(_,i)=>({timestamp:'2026-10-29',status:'ACKNOWLEDGED',note:'Pagination verification row '+i+' '+('Long response detail. '.repeat(10))}))};
    const pdf=m.reportPdf(long,'stress','date');if(pdf.getNumberOfPages()<3)throw Error('pagination');
    return {formula_escaping:escaped,private_media_excluded:true,stress_pages:pdf.getNumberOfPages()};}""")
  check('Formula injection, escaping, private media exclusion, long PDF pagination',security)
  def dashboard_smoke():
   page.get_by_label('Report from date').fill('');page.get_by_label('Report to date').fill('');page.get_by_label('Report incident status').select_option('all')
   expect(page.get_by_test_id('incident-report')).to_be_visible()
   for section in ['Summary','Evidence','Response','Analysis']:
    page.get_by_role('tab',name=section,exact=True).click();expect(page.get_by_role('tabpanel',name=section)).to_be_visible()
   for destination in ['Overview','Alerts','Analytics','Reports']:
    page.locator('aside').get_by_role('button',name=destination,exact=True).click();expect(page.locator('main')).to_be_visible()
   expect(page.get_by_test_id('incident-report')).to_be_visible()
   return {'sections':4,'navigation':['Overview','Alerts','Analytics','Reports']}
  check('Existing report sections and dashboard navigation',dashboard_smoke)
  check('No browser exceptions',lambda: {'errors':errors} if not errors else (_ for _ in ()).throw(AssertionError(errors)))
  browser.close()
finally:
 for process,log in reversed(processes):process.terminate();process.wait(timeout=20);log.close()
 (OUT/'results.json').write_text(json.dumps(RESULTS,indent=2),encoding='utf-8')
if any(r['status']=='FAIL' for r in RESULTS):sys.exit(1)
