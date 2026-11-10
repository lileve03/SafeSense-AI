"""Actual isolated MVP/browser integration. Notifications disabled; user DB read-only."""
from pathlib import Path
import hashlib,json,os,shutil,socket,sqlite3,subprocess,sys,time,traceback
import httpx
from playwright.sync_api import sync_playwright,expect
ROOT=Path(__file__).resolve().parents[1];sys.stdout.reconfigure(encoding='utf-8')
OUT=ROOT/'runtime/sos-telegram-diagnosis/browser';OUT.mkdir(parents=True,exist_ok=True)
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
 with socket.socket() as probe:
  probe.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1);probe.bind(('127.0.0.1',port))
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
case_index=0
def run_case(mode,has_route):
 global ENV,B,D,case_index
 case_index+=1;backend_port=18820+case_index;frontend_port=3020+case_index
 B=f'http://127.0.0.1:{backend_port}';D=f'http://127.0.0.1:{frontend_port}'
 ENV.update(VITE_API_BASE_URL=B,SAFESENSE_BACKEND_URL=B,SAFESENSE_TEST_CORS_ORIGIN=D)
 case=mode+('-assigned' if has_route else '-no-route');caseout=OUT/case;caseout.mkdir(parents=True,exist_ok=True)
 route=caseout/'fixture-route.json';route.write_text(json.dumps([{'zone_id':'ZONE_TOILET_BLINDSPOT','staff':'Authorized TEST teacher fixture','role':'duty_teacher','active':True}] if has_route else []),encoding='utf-8')
 ENV.update(SAFESENSE_DB_PATH=str(caseout/('test-'+str(time.time_ns())+'.sqlite3')),TELEGRAM_MODE=mode,TELEGRAM_BOT_TOKEN='fake-browser-token',TELEGRAM_TEST_CHAT_ID='-100123',TELEGRAM_TEST_ACK_USER_IDS='42',SAFESENSE_STAFF_ROUTES=str(route),SAFESENSE_TEST_RECEIPT_FLAG=str(caseout/'no-reply'))
 try:
  start('backend-'+case,[sys.executable,'-m','uvicorn','telegram_browser_backend:app','--app-dir','tests','--host','127.0.0.1','--port',str(backend_port)],ROOT,backend_port,B+'/health')
  start('frontend-'+case,[shutil.which('node'),str(ROOT/'dashboard/node_modules/vite/bin/vite.js'),'--host','127.0.0.1','--port',str(frontend_port),'--strictPort'],ROOT/'dashboard',frontend_port,D)
  with sync_playwright() as pw:
   browser=pw.chromium.launch(headless=True,args=['--enable-unsafe-swiftshader']);page=browser.new_page(viewport={'width':1500,'height':1100});errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
   page.goto(D);page.locator('aside').get_by_role('button',name='Digital Twin Map',exact=True).click();page.locator('[data-zone-id="ZONE_TOILET_BLINDSPOT"] polygon').first.click()
   page.get_by_role('button',name='Use original local simulation',exact=True).click()
   page.get_by_role('button',name='ACTIVATE SOS EMERGENCY',exact=True).click();expect(page.get_by_text('Authorize Prototype SOS Test',exact=True)).to_be_visible()
   with page.expect_response(lambda r:r.url==B+'/event' and r.request.method=='POST') as response:page.get_by_role('button',name='Confirm Test Broadcast',exact=True).click()
   request=response.value.request.post_data_json;result=response.value.json();identifier=result['incident']['id'];assert request['type']=='sos' and request['source']=='sos_button' and request['is_test']
   banner=page.get_by_test_id('private-sos-outcome');expect(banner).to_contain_text('saved in SQLite')
   if mode=='disabled':expect(banner).to_contain_text('Telegram NOT SENT: backend TELEGRAM_MODE=disabled')
   elif not has_route:expect(banner).to_contain_text('no authorized on-duty teacher route')
   else:expect(banner).to_contain_text('Telegram API accepted - receipt unconfirmed')
   report=client.get(B+'/incidents/'+identifier+'/report').json();assert report['level']=='CRITICAL' and report['zone_type']=='PRIVATE'
   expected='DISABLED' if mode=='disabled' else 'NO_ACTIVE_ASSIGNMENT' if not has_route else 'SENT'
   assert report['notifications'][-1]['status']==expected
   repeated=client.post(B+'/event',json=request).json();assert repeated['deduplicated'] and repeated['incident']['id']==identifier
   assert len(client.get(B+'/incidents/'+identifier+'/report').json()['notifications'])==1
   assert not page.get_by_test_id('private-monitoring-view').locator('video,img,audio').count();assert not errors,errors
   banner.screenshot(path=str(caseout/'sos-result.png'));browser.close()
   return {'initial_view':'local simulation','actual_POST':'/event','SQLite_incident':identifier,'notification_status':expected,'banner_truthful':True,'duplicate_event_deduplicated':True,'transport':'MOCKED / no external Telegram','browser_errors':errors}
 finally:
  for process,log in reversed(processes):
   process.terminate()
   try:process.wait(timeout=15)
   except subprocess.TimeoutExpired:process.kill();process.wait(timeout=5)
   log.close()
  processes.clear()
for mode,assigned in [('disabled',True),('test',False),('test',True)]:check('Prominent SOS from local room -> actual backend: '+mode+' / assigned='+str(assigned),lambda m=mode,a=assigned:run_case(m,a))
assert original_incidents()==before_original
sys.exit(any(r['status']=='FAIL' for r in rows))
