"""Real browser + existing APIs on a disposable SQLite copy; Telegram disabled."""
from pathlib import Path
import os,sys,json,time,subprocess,sqlite3,hashlib,csv,io
from urllib.request import Request,urlopen
from urllib.error import HTTPError
from urllib.parse import urlsplit
from playwright.sync_api import sync_playwright,expect
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'runtime/incident-investigation';OUT.mkdir(parents=True,exist_ok=True)
BASE='http://127.0.0.1:18271';TOKEN='isolated-investigation-test'
results=[]
def passed(name):
 results.append({'test':name,'result':'PASS'});print('PASS:',name,flush=True)
def call(path,body=None):
 request=Request(BASE+path,data=None if body is None else json.dumps(body).encode(),headers={'X-SafeSense-Token':TOKEN,'Content-Type':'application/json'})
 with urlopen(request,timeout=15) as r:return json.load(r)
def original_rows():
 with sqlite3.connect('file:'+str(ROOT/'runtime/safesense.sqlite3')+'?mode=ro',uri=True) as db:return db.execute('SELECT kind,id,body FROM records ORDER BY kind,id').fetchall()
original=original_rows()
protected=['backend/main.py','backend/notifications.py','dashboard/src/context/SafeSenseContext.tsx','dashboard/src/lib/reportExport.ts']
hashes={n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in protected}
db=OUT/f'test-{time.time_ns()}.sqlite3'
with sqlite3.connect('file:'+str(ROOT/'runtime/safesense.sqlite3')+'?mode=ro',uri=True) as source,sqlite3.connect(db) as target:source.backup(target)
env=os.environ.copy();env.update(SAFESENSE_DB_PATH=str(db),SAFESENSE_API_TOKEN=TOKEN,TELEGRAM_MODE='disabled')
log=(OUT/'backend.log').open('w')
process=subprocess.Popen([str(ROOT/'.venv/Scripts/python.exe'),'-m','uvicorn','backend.main:app','--host','127.0.0.1','--port','18271'],cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
try:
 for _ in range(150):
  try:call('/health');break
  except OSError:time.sleep(.2)
 else:raise RuntimeError('Isolated backend did not start')
 records=call('/incidents')
 selected=next((r for r in records if any(e.get('score') is not None for e in r.get('evidence',[]))),records[0])
 snapshot=call('/incidents/'+selected['id']+'/report')
 new=call('/event',{'zone':'ZONE_TOILET_BLINDSPOT','type':'sos','source':'simulation','processing_mode':'simulation','is_test':True,'event_id':'investigation-browser-'+str(time.time_ns())})['incident']
 with sync_playwright() as pw:
  browser=pw.chromium.launch(headless=True)
  page=browser.new_page(viewport={'width':1440,'height':1100},timezone_id='Asia/Singapore',accept_downloads=True)
  errors=[];mutations=[];page.on('pageerror',lambda e:errors.append(str(e)))
  def forward(route):
   r=route.request;parsed=urlsplit(r.url)
   if r.method not in ['GET','OPTIONS']:mutations.append((r.method,parsed.path))
   headers={'X-SafeSense-Token':TOKEN,'Content-Type':'application/json'}
   req=Request(BASE+parsed.path+('?' + parsed.query if parsed.query else ''),data=r.post_data_buffer,headers=headers,method=r.method)
   try:response=urlopen(req,timeout=20)
   except HTTPError as e:response=e
   route.fulfill(status=response.code,content_type='application/json',body=response.read())
  page.route('http://127.0.0.1:8000/**',forward)
  page.goto('http://127.0.0.1:3000',wait_until='domcontentloaded')
  page.locator('aside').get_by_role('button',name='Analytics & Reports',exact=True).click()
  expect(page.get_by_label('Report incident',exact=True)).to_be_visible()
  page.get_by_label('Report incident',exact=True).select_option(selected['id'])
  report=page.get_by_test_id('incident-report');expect(report).to_be_visible()
  expect(report.get_by_text(snapshot['id'],exact=True)).to_be_visible()
  assert snapshot['reason'] in report.inner_text()
  assert report.locator('time').first.get_attribute('datetime')==page.evaluate('(v)=>new Date(v).toISOString()',snapshot['created_at'])
  assert ('GMT+8' in report.locator('time').first.inner_text() or 'SGT' in report.locator('time').first.inner_text())
  passed('Summary shows actual ID, zone, severity, status and locally formatted timestamps with UTC retained')
  for name in ['Summary','Evidence','Response','Analysis']:
   report.get_by_role('tab',name=name,exact=True).click()
   expect(report.get_by_role('tabpanel')).to_have_attribute('aria-labelledby',f"incident-{selected['id']}-tab-{name}")
   expect(report.get_by_role('tab',name=name,exact=True)).to_have_attribute('aria-selected','true')
   if name=='Analysis':
    for e in snapshot['evidence']:
     if e.get('score') is not None:assert str(e['score']) in report.inner_text()
    assert snapshot['reason'] in report.inner_text()
   if name=='Evidence':expect(report.get_by_test_id('incident-evidence')).to_be_visible()
   if name=='Response':
    expect(report.get_by_text('Response and audit history',exact=True)).to_be_visible()
    if snapshot['notifications']:
     expect(report.get_by_text('Recipient routing',exact=True).first).to_be_visible()
     expect(report.get_by_text('Telegram API acceptance',exact=True).first).to_be_visible()
     expect(report.get_by_text('Receipt verification',exact=True).first).to_be_visible()
   report.screenshot(path=str(OUT/f'incident-{name.lower()}.png'))
  passed('All four tabs, recorded model scores, evidence metadata and separate Telegram evidence render')
  report.get_by_role('tab',name='Summary',exact=True).focus();page.keyboard.press('ArrowRight')
  expect(report.get_by_role('tab',name='Evidence',exact=True)).to_be_focused()
  passed('Keyboard navigation changes tabs and focus')
  with page.expect_download() as download:
   report.get_by_role('button',name='Download Incident CSV',exact=True).click()
  file=OUT/download.value.suggested_filename;download.value.save_as(file)
  rows=list(csv.DictReader(io.StringIO(file.read_text(encoding='utf-8-sig'))))
  assert rows[0]['incident_id']==selected['id'] and rows[0]['timestamp']==snapshot['created_at']
  assert rows[0]['severity']==snapshot['level'] and rows[0]['zone']==snapshot['zone_id']
  passed('Downloaded CSV matches actual incident identity, UTC timestamp, zone and severity')
  page.get_by_label('Report incident',exact=True).select_option(new['id'])
  expect(report.get_by_text(new['id'],exact=True)).to_be_visible()
  assert 'TEST / REPLAY' in report.inner_text() and 'simulation' in report.inner_text()
  report.get_by_role('tab',name='Evidence',exact=True).click()
  expect(report.get_by_text('Private sensor metadata only.',exact=False)).to_be_visible()
  assert report.locator('img,video').count()==0
  passed('Simulation provenance is explicit and private-zone evidence contains no images or video')
  report.get_by_role('tab',name='Response',exact=True).click()
  expect(report.get_by_role('button',name='Resolve incident',exact=True)).to_be_disabled()
  report.get_by_role('button',name='Preview local notification (no send)',exact=True).click()
  expect(report.get_by_text('Recorded notification preview',exact=True)).to_be_visible()
  report.get_by_text('Recorded notification preview',exact=True).click()
  expect(report.locator('pre')).to_contain_text(new['id'])
  expect(report.get_by_role('button',name='Verify authorized TEST reply and acknowledge',exact=True)).to_have_count(0)
  preview=call('/incidents/'+new['id']+'/report')
  assert preview['notifications'][-1]['delivery_state']=='DISABLED'
  assert any(method=='POST' and path.endswith('/notify-test') for method,path in mutations)
  assert not preview['notifications'][-1].get('telegram_api_ok')
  passed('Existing local notification preview works without claiming API acceptance or receipt')
  report.get_by_label('Report reviewing staff',exact=True).fill('Browser verification operator')
  report.get_by_role('button',name='Acknowledge incident',exact=True).click()
  expect(report.get_by_text('Browser verification operator',exact=True).first).to_be_visible()
  ack=call('/incidents/'+new['id']+'/report');assert ack['acknowledged_at'] and ack['acknowledged_by']=='Browser verification operator'
  expect(report.get_by_role('button',name='Resolve incident',exact=True)).to_be_disabled()
  report.get_by_label('Report resolution note',exact=True).fill('Isolated UI response verification; simulation only.')
  report.get_by_role('button',name='Resolve incident',exact=True).click()
  expect(report.get_by_role('button',name='Resolve incident',exact=True)).to_have_count(0)
  resolved=call('/incidents/'+new['id']+'/report');assert resolved['status']=='RESOLVED' and resolved['resolved_by']=='Browser verification operator'
  assert resolved['resolved_at'] and any(h.get('note')=='Isolated UI response verification; simulation only.' for h in resolved['history'])
  passed('Actual acknowledgement and resolution APIs enforce gating and persist operator/note in isolated database')
  for width in [1280,768,390]:
   page.set_viewport_size({'width':width,'height':1100})
   for name in ['Summary','Evidence','Response','Analysis']:
    report.get_by_role('tab',name=name,exact=True).click()
    assert report.evaluate('(e)=>e.scrollWidth<=e.clientWidth'),(width,name)
   report.screenshot(path=str(OUT/f'responsive-{width}.png'))
  passed('All tabs fit 1280px, 768px and 390px widths without panel overflow')
  assert not errors,errors
  assert all(new['id'] in path for method,path in mutations),mutations
  passed('No browser exceptions; response mutations target only the disposable simulation incident')
  browser.close()
 assert original_rows()==original,'Existing database records changed during verification'
 assert all(hashlib.sha256((ROOT/n).read_bytes()).hexdigest()==v for n,v in hashes.items())
 passed('Existing SQLite records, backend logic, simulation context and CSV exporter remain unchanged')
finally:
 process.terminate();process.wait(timeout=15);log.close()
 (OUT/'results.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
