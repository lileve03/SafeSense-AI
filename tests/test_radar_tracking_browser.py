"""Actual isolated MVP/browser integration. Notifications disabled; user DB read-only."""
from pathlib import Path
import hashlib,json,os,shutil,socket,sqlite3,subprocess,sys,time,traceback
import httpx
from playwright.sync_api import sync_playwright,expect
ROOT=Path(__file__).resolve().parents[1];sys.stdout.reconfigure(encoding='utf-8')
OUT=ROOT/'runtime/radar-tracking-browser';OUT.mkdir(parents=True,exist_ok=True)
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
try:
 start('backend',[sys.executable,'-m','uvicorn','backend.main:app','--host','127.0.0.1','--port','18770'],ROOT,18770,B+'/health')
 start('frontend',[shutil.which('node'),str(ROOT/'dashboard/node_modules/vite/bin/vite.js'),'--host','127.0.0.1','--port','3001','--strictPort'],ROOT/'dashboard',3001,D)
 with sync_playwright() as pw:
  browser=pw.chromium.launch(headless=True,args=['--enable-unsafe-swiftshader']);page=browser.new_page(viewport={'width':1500,'height':1100});page.set_default_timeout(25000);errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
  page.add_init_script("window.captureCalls=0;if(navigator.mediaDevices)navigator.mediaDevices.getUserMedia=async()=>{window.captureCalls++;throw Error('Forbidden');};")
  page.goto(D);page.locator('aside').get_by_role('button',name='Digital Twin Map',exact=True).click();page.locator('[data-zone-id="ZONE_TOILET_BLINDSPOT"] polygon').first.click()
  scene=page.get_by_test_id('private-twin-scene');panel=page.get_by_test_id('radar-tracking-simulation')
  def preview():
   expect(scene).to_have_attribute('data-positioned-occupants','0');before=counts()
   panel.get_by_role('button',name='Open isolated tracking simulation',exact=True).click();expect(scene).to_have_attribute('data-tracking-preview','SIMULATION');expect(scene).to_have_attribute('data-positioned-occupants','3')
   expect(panel.get_by_text('Simulated count: 3',exact=True)).to_be_visible();expect(panel).to_contain_text('Not real radar people detection')
   panel.get_by_role('button',name='Repeated motion example',exact=True).click();expect(panel).to_contain_text('Repeated motion');panel.get_by_role('button',name='Fall + distress example',exact=True).click()
   expect(scene).to_have_attribute('data-fall-active','true');expect(panel).to_contain_text('Simulated rule status: HIGH')
   actual=json.loads(page.get_by_test_id('private-three-renderer').get_attribute('data-simulated-tracks'));expected=client.get(B+'/testing/radar-simulation').json()['frames'][105]['tracks'];assert len(actual)==3
   for a,e in zip(actual,expected):assert all(abs(a[k]-e[k])<1e-6 for k in ('x','y','height'))
   assert counts()==before
   scene.screenshot(path=str(OUT/'original-room-synthetic-tracks.png'));panel.screenshot(path=str(OUT/'synthetic-tracks-distances-rules.png'))
   return {'original_real_mode_people':0,'synthetic_tracks':3,'mesh_coordinates_match_synthetic_input':True,'fall_distress_status':'HIGH simulation','incidents_created_by_preview':0}
  check('Original room isolated tracks count pair distances and temporal motion/fall rules',preview)
  def fusion_sos():
   with page.expect_response(lambda r:r.url==B+'/testing/radar-simulation/events') as response:panel.get_by_role('button',name='Record simulated fall + acoustic fusion',exact=True).click()
   result=response.value.json();assert result['incident']['level']=='HIGH' and result['incident']['processing_mode']=='simulation';identifier=result['incident']['id']
   expect(page.get_by_test_id('incident-evidence')).to_have_attribute('data-incident-id',identifier);assert not page.get_by_test_id('incident-evidence').locator('video,img,audio').count();page.get_by_role('button',name='Close',exact=True).click();before=counts()
   with page.expect_response(lambda r:r.url==B+'/testing/radar-simulation/events') as response:panel.get_by_role('button',name='Record simulated fall + acoustic fusion',exact=True).click()
   assert response.value.json()['deduplicated'];expect(page.get_by_test_id('incident-evidence')).to_be_visible();page.get_by_role('button',name='Close',exact=True).click();assert counts()==before
   with page.expect_response(lambda r:r.url==B+'/testing/radar-simulation/events') as response:panel.get_by_role('button',name='Record explicit simulation SOS',exact=True).click()
   sos=response.value.json();assert sos['incident']['level']=='CRITICAL' and sos['incident']['is_test'];expect(page.get_by_test_id('incident-evidence')).to_be_visible();page.get_by_role('button',name='Acknowledge Alert',exact=True).click()
   for _ in range(30):
    report=client.get(B+'/incidents/'+sos['incident']['id']+'/report').json()
    if report.get('acknowledged_at'):break
    page.wait_for_timeout(100)
   assert report.get('acknowledged_at');page.get_by_role('button',name='Close',exact=True).click()
   panel.get_by_role('button',name='Close isolated tracking simulation',exact=True).click();expect(scene).to_have_attribute('data-tracking-preview','off');expect(scene).to_have_attribute('data-positioned-occupants','0');expect(scene).to_contain_text('Separation: Unavailable')
   return {'fusion_incident':identifier,'SOS_incident':sos['incident']['id'],'deduplicated':True,'acknowledged':True,'real_mode_reverts_to_unknown_positions':True}
  check('Explicit synthetic fusion and SOS use actual SQLite incidents acknowledgement and dedup',fusion_sos)
  def playback_privacy():
   before=counts();panel.get_by_role('button',name='Open isolated tracking simulation',exact=True).click();panel.get_by_role('button',name='Reset tracking simulation',exact=True).click();panel.get_by_role('button',name='Play tracking simulation',exact=True).click();page.wait_for_timeout(300);panel.get_by_role('button',name='Pause tracking simulation',exact=True).click();assert counts()==before
   for extra in ({'source':'vision'},{'sensor_modality':'vision'},{'evidence_media':[{'url':'private.jpg'}]}):assert client.post(B+'/event',json={'zone':'ZONE_TOILET_BLINDSPOT','type':'fall','source':'radar','processing_mode':'simulation',**extra}).status_code in (403,422)
   assert page.evaluate('window.captureCalls')==0 and not page.get_by_test_id('private-monitoring-view').locator('video,img,audio').count()
   page.set_viewport_size({'width':390,'height':844});page.wait_for_timeout(250);assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
   assert original_incidents()==before_original and not errors,errors
   assert all(hashlib.sha256((ROOT/n).read_bytes()).hexdigest()==d for n,d in hashes.items())
   return {'playback_and_seek_no_incidents':True,'private_capture_calls':0,'privacy_rejection':True,'mobile_overflow':False,'original_incidents_preserved':len(before_original),'browser_errors':errors}
  check('Simulation playback isolation privacy responsive layout and original features preserved',playback_privacy)
  browser.close()
finally:
 for process,log in reversed(processes):
  process.terminate()
  try:process.wait(timeout=15)
  except subprocess.TimeoutExpired:process.kill();process.wait(timeout=5)
  log.close()
sys.exit(any(r['status']=='FAIL' for r in rows))
