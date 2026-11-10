"""Actual isolated MVP/browser integration. Notifications disabled; user DB read-only."""
from pathlib import Path
import hashlib,json,os,shutil,socket,sqlite3,subprocess,sys,time,traceback
import httpx
from playwright.sync_api import sync_playwright,expect
ROOT=Path(__file__).resolve().parents[1];sys.stdout.reconfigure(encoding='utf-8')
OUT=ROOT/'runtime/telegram-integration/browser';OUT.mkdir(parents=True,exist_ok=True)
B='http://127.0.0.1:18770';A='http://127.0.0.1:18772';D='http://127.0.0.1:3001';TOKEN='zip-integration-test'
ENV=os.environ.copy();ENV.update(SAFESENSE_DB_PATH=str(OUT/('test-'+str(time.time_ns())+'.sqlite3')),SAFESENSE_API_TOKEN=TOKEN,VITE_SAFESENSE_API_TOKEN=TOKEN,SAFESENSE_BACKEND_URL=B,SAFESENSE_AI_URL=A,VITE_API_BASE_URL=B,VITE_AI_BASE_URL=A,TELEGRAM_MODE='disabled',SAFESENSE_PRECOMPUTE_ON_START='false',SAFESENSE_EVIDENCE_DIR=str(OUT/'evidence'),SAFESENSE_ANNOTATION_DIR=str(OUT/'annotations'),SAFESENSE_ANALYSIS_CACHE_DIR=str(OUT/'cache'))
H={'X-SafeSense-Token':TOKEN};client=httpx.Client(headers=H,timeout=10);processes=[];rows=[]
protected=['fight_api.py','monitoring_ai.py','backend/fight_participants.py','yolo11n-pose.pt','evaluation/outputs/fight_multiclip_v2/fight_multiclip_classifier.joblib','evaluation/outputs/fight_v3/fight_v3_classifier.joblib','dashboard/src/components/private-area/PrivateAreaDigitalTwin3D.tsx','dashboard/src/components/private-area/PrivateAreaMonitoringView.tsx','dashboard/src/pages/LiveMonitoringPage.tsx','dashboard/src/pages/AnalyticsReportsPage.tsx']
hashes={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in protected}
def original_incidents():
 with sqlite3.connect('file:'+str(ROOT/'runtime/safesense.sqlite3')+'?mode=ro',uri=True) as db:return dict(db.execute("SELECT id,body FROM records WHERE kind='incident'"))
before_original=original_incidents()
def check(name,fn):
 try:row={'test':name,'status':'PASS','actual':fn()}
 except Exception as error:row={'test':name,'status':'FAIL','actual':str(error),'trace':traceback.format_exc()}
 rows.append(row);(OUT/'results.json').write_text(json.dumps(rows,indent=2),encoding='utf-8');print(row['status'],name,str(row['actual'])[:600],flush=True)
def start(name,command,cwd,port,url):
 with socket.socket() as probe:probe.bind(('127.0.0.1',port))
 log=(OUT/(name+'.log')).open('w',encoding='utf-8');process=subprocess.Popen(command,cwd=cwd,env=ENV,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW);processes.append((process,log))
 for _ in range(180):
  if process.poll() is not None:raise RuntimeError(name+' exited')
  try:
   if httpx.get(url,timeout=1).status_code==200:return
  except httpx.HTTPError:pass
  time.sleep(.2)
 raise RuntimeError(name+' startup timeout')
def state():return client.get(B+'/state').json()
def counts():
 value=state();return len(value['events']),len(value['incidents'])
flag=OUT/('reply-ready-'+str(time.time_ns()));routes=OUT/'fixture-routes.json'
routes.write_text(json.dumps([{'zone_id':'ZONE_TOILET_BLINDSPOT','staff':'Telegram test teacher (fixture)','role':'duty_teacher','active':True}]),encoding='utf-8')
ENV.update(TELEGRAM_MODE='test',TELEGRAM_BOT_TOKEN='fake-browser-token',TELEGRAM_TEST_CHAT_ID='-100123',TELEGRAM_TEST_ACK_USER_IDS='42',SAFESENSE_STAFF_ROUTES=str(routes),SAFESENSE_TEST_RECEIPT_FLAG=str(flag))
try:
 start('backend',[sys.executable,'-m','uvicorn','telegram_browser_backend:app','--app-dir','tests','--host','127.0.0.1','--port','18770'],ROOT,18770,B+'/health')
 start('frontend',[shutil.which('node'),str(ROOT/'dashboard/node_modules/vite/bin/vite.js'),'--host','127.0.0.1','--port','3001','--strictPort'],ROOT/'dashboard',3001,D)
 with sync_playwright() as pw:
  browser=pw.chromium.launch(headless=True,args=['--enable-unsafe-swiftshader']);page=browser.new_page(viewport={'width':1500,'height':1100});page.set_default_timeout(25000);errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
  page.goto(D);page.locator('aside').get_by_role('button',name='Digital Twin Map',exact=True).click();page.locator('[data-zone-id="ZONE_TOILET_BLINDSPOT"] polygon').first.click()
  def sos():
   page.get_by_role('button',name='ACTIVATE SOS EMERGENCY',exact=True).click()
   with page.expect_response(lambda r:r.url==B+'/event' and r.request.method=='POST') as response:page.get_by_role('button',name='Confirm Test Broadcast',exact=True).click()
   global identifier
   identifier=response.value.json()['incident']['id']
   page.get_by_test_id('private-incident-indicator').click();evidence=page.get_by_test_id('incident-evidence');expect(evidence).to_have_attribute('data-incident-id',identifier)
   expect(evidence).to_contain_text('Telegram API accepted - receipt unconfirmed')
   report=client.get(B+'/incidents/'+identifier+'/report').json();assert report['status']=='NEW' and not report['notifications'][-1]['receipt_confirmed']
   assert report['assigned_staff']=='Telegram test teacher (fixture)'
   assert 'fake-browser-token' not in json.dumps(report) and 'receipt_nonce_hash' not in json.dumps(report)
   assert not evidence.locator('video,img,audio').count()
   evidence.screenshot(path=str(OUT/'api-accepted-receipt-unconfirmed.png'))
   return {'incident':identifier,'transport':'MOCKED; not actual Telegram','status':'API_ACCEPTED','receipt':False,'assigned_teacher':'fixture only'}
  check('Confirmed private SOS SQLite assignment and truthful API acceptance UI (mock transport)',sos)
  def receipt():
   evidence=page.get_by_test_id('incident-evidence');button=evidence.get_by_role('button',name='Verify authorized TEST reply and acknowledge',exact=True)
   button.click();expect(evidence).to_contain_text('RECEIPT_PENDING');assert client.get(B+'/incidents/'+identifier+'/report').json()['status']=='NEW'
   flag.write_text('explicit fake Telegram user reply for isolated test',encoding='utf-8');button.click()
   expect(evidence).to_contain_text('Receipt confirmed by authorized Telegram test user')
   for _ in range(40):
    report=client.get(B+'/incidents/'+identifier+'/report').json()
    if report['status']=='ACKNOWLEDGED':break
    page.wait_for_timeout(100)
   assert report['status']=='ACKNOWLEDGED' and report['acknowledged_by']=='Telegram test teacher (fixture)'
   evidence.screenshot(path=str(OUT/'verified-test-reply-acknowledged.png'))
   assert len([n for n in report['notifications'] if n['status']=='SENT'])==1
   page.get_by_role('button',name='Close',exact=True).click();page.locator('aside').get_by_role('button',name='Analytics & Reports',exact=True).click();page.get_by_label('Report incident',exact=True).select_option(identifier)
   report_ui=page.get_by_test_id('incident-report');expect(report_ui).to_contain_text('ACKNOWLEDGED');expect(report_ui).to_contain_text('Receipt confirmed by authorized Telegram test user')
   assert not errors,errors;assert original_incidents()==before_original
   return {'transport':'MOCKED; not actual recipient','acknowledged':True,'notification_count':1,'Reports_synchronized':True,'original_incidents_unchanged':len(before_original),'browser_errors':errors}
  check('Authorized reply verification acknowledgement and Dashboard/Reports sync (mock transport)',receipt)
  browser.close()
finally:
 for process,log in reversed(processes):
  process.terminate()
  try:process.wait(timeout=15)
  except subprocess.TimeoutExpired:process.kill();process.wait(timeout=5)
  log.close()
sys.exit(any(r['status']=='FAIL' for r in rows))
