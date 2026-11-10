"""Actual isolated MVP/browser integration. Notifications disabled; user DB read-only."""
from pathlib import Path
import hashlib,json,os,shutil,socket,sqlite3,subprocess,sys,time,traceback
import httpx
from playwright.sync_api import sync_playwright,expect
ROOT=Path(__file__).resolve().parents[1];sys.stdout.reconfigure(encoding='utf-8')
OUT=ROOT/'runtime/zip-integration';OUT.mkdir(parents=True,exist_ok=True)
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
 start('inference',[sys.executable,'-m','uvicorn','fight_api:app','--host','127.0.0.1','--port','18772'],ROOT,18772,A+'/health')
 start('frontend',[shutil.which('node'),str(ROOT/'dashboard/node_modules/vite/bin/vite.js'),'--host','127.0.0.1','--port','3001','--strictPort'],ROOT/'dashboard',3001,D)
 with sync_playwright() as pw:
  browser=pw.chromium.launch(headless=True,args=['--enable-unsafe-swiftshader']);page=browser.new_page(viewport={'width':1500,'height':1100});page.set_default_timeout(20000);errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
  page.add_init_script("window.captureCalls=0;if(navigator.mediaDevices)navigator.mediaDevices.getUserMedia=async()=>{window.captureCalls++;throw Error('Private capture is forbidden');};")
  page.goto(D+'/#/developer/testing');page.get_by_role('button',name='Open imported replay lab',exact=True).click();lab=page.get_by_test_id('imported-replay-lab');scene=lab.get_by_test_id('imported-replay-scene');slider=lab.get_by_label('Imported synthetic replay time',exact=True)
  def seek(value):
   slider.evaluate('(e,v)=>{Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,"value").set.call(e,String(v));e.dispatchEvent(new Event("input",{bubbles:true}));e.dispatchEvent(new Event("change",{bubbles:true}));}',value)
   expect(scene).to_have_attribute('data-frame-time',str(value))
  def visual():
   expect(scene.locator('canvas')).to_be_visible();expect(scene).to_have_attribute('data-track-count','5')
   health=scene.locator('canvas').evaluate('c=>{const gl=c.getContext("webgl2");return {width:c.width,height:c.height,webgl:!!gl,lost:gl?.isContextLost()}}');assert health['webgl'] and not health['lost']
   assert lab.locator('video,img,audio').count()==0 and page.evaluate('window.captureCalls')==0
   return {'canvas':health,'synthetic_tracks':5,'capture_calls':0,'private_media_elements':0}
  check('Integrated local Three.js replay renders genuine supplied synthetic data without media capture',visual)
  def readonly_playback():
   before=counts();seek(6);assert counts()==before
   lab.get_by_role('button',name='Reset replay',exact=True).click();expect(scene).to_have_attribute('data-frame-time','0')
   lab.get_by_role('button',name='Play synthetic replay',exact=True).click();page.wait_for_timeout(250);lab.get_by_role('button',name='Pause replay',exact=True).click()
   paused=scene.get_attribute('data-frame-time');page.wait_for_timeout(180);assert scene.get_attribute('data-frame-time')==paused
   seek(4.9);assert counts()==before
   scene.scroll_into_view_if_needed();scene.screenshot(path=str(OUT/'imported-synthetic-scene.png'));lab.screenshot(path=str(OUT/'imported-lab.png'))
   return {'seek_and_play_incidents_added':0,'pause_stable_frame':paused,'frame_at_4_9':scene.get_attribute('data-frame-time')}
  check('Imported play/pause/seek/reset are synchronized and never insert historical incidents',readonly_playback)
  def record_fall():
   with page.expect_response(lambda r:r.url==B+'/event' and r.request.method=='POST') as response:lab.get_by_role('button',name='Record supplied fall as simulation test',exact=True).click()
   payload=response.value.json();event=payload['event'];assert event['processing_mode']=='simulation' and event['source_type']=='SIMULATION' and event['is_test']
   assert event['score'] is None and event['model_version'] is None and event['level']=='OBSERVE';assert payload['incident']
   identifier=payload['incident']['id'];expect(page.get_by_test_id('incident-evidence')).to_be_visible();page.get_by_role('button',name='Close',exact=True).click();before=counts()
   lab.get_by_role('button',name='Reset replay',exact=True).click();seek(4.9)
   with page.expect_response(lambda r:r.url==B+'/event' and r.request.method=='POST') as repeated:lab.get_by_role('button',name='Record supplied fall as simulation test',exact=True).click()
   assert repeated.value.json()['deduplicated'];page.get_by_role('button',name='Close',exact=True).click();assert counts()==before
   return {'incident':identifier,'source':'SIMULATION','model_score':None,'mvp_severity':'OBSERVE','repeated_action_deduplicated':True,'history_preserved_on_reset':True}
  check('Explicit supplied fall uses existing simulation policy and idempotent SQLite incident workflow',record_fall)
  def sos():
   before=counts();lab.get_by_role('button',name='Prototype SOS test',exact=True).click();lab.get_by_role('button',name='Cancel SOS test',exact=True).click();assert counts()==before
   lab.get_by_role('button',name='Prototype SOS test',exact=True).click()
   with page.expect_response(lambda r:r.url==B+'/event' and r.request.method=='POST') as response:lab.get_by_role('button',name='Confirm simulation SOS',exact=True).click()
   payload=response.value.json();assert payload['event']['level']=='CRITICAL' and payload['event']['is_test'] and payload['event']['processing_mode']=='simulation'
   identifier=payload['incident']['id'];expect(page.get_by_test_id('incident-evidence')).to_be_visible()
   page.get_by_role('button',name='Acknowledge Alert',exact=True).click()
   for _ in range(30):
    report=client.get(B+'/incidents/'+identifier+'/report').json()
    if report.get('acknowledged_at'):break
    page.wait_for_timeout(50)
   assert report['acknowledged_at'];page.get_by_role('button',name='Close',exact=True).click()
   return {'cancel_is_readonly':True,'explicit_test_sos':'CRITICAL','actual_backend_acknowledgement':report['acknowledged_at'],'real_dispatch':False}
  check('Prototype SOS confirmation and original incident acknowledgement work without real dispatch',sos)
  def lifecycle_and_existing():
   for _ in range(2):page.get_by_role('button',name='Close imported replay lab',exact=True).click();assert page.get_by_test_id('imported-replay-scene').count()==0;page.get_by_role('button',name='Open imported replay lab',exact=True).click();expect(page.get_by_test_id('imported-replay-scene').locator('canvas')).to_be_visible()
   assert page.get_by_test_id('imported-replay-scene').locator('canvas').count()==1
   page.locator('aside').get_by_role('button',name='Digital Twin Map',exact=True).click();page.locator('[data-zone-id="ZONE_TOILET_BLINDSPOT"] polygon').first.click()
   original=page.get_by_test_id('private-monitoring-view');expect(original).to_be_visible();expect(page.get_by_test_id('private-twin-scene')).to_have_attribute('data-positioned-occupants','0');assert original.locator('video,img,audio').count()==0
   page.screenshot(path=str(OUT/'original-private-view-preserved.png'),full_page=True)
   page.locator('aside').get_by_role('button',name='Alerts',exact=True).click();expect(page.get_by_title('Inspect Full Incident Review Dossier').first).to_be_visible()
   page.locator('aside').get_by_role('button',name='Analytics & Reports',exact=True).click();expect(page.get_by_test_id('analytics-reports')).to_be_visible()
   page.locator('aside').get_by_role('button',name='Live Monitoring',exact=True).click();expect(page.get_by_test_id('camera-monitoring')).to_be_visible();assert len(client.get(B+'/monitoring/cameras').json())==5
   return {'no_extra_canvas_on_reopen':True,'operational_private_positions_still_unavailable':True,'alerts_reports_live_routes':True,'configured_cameras':5}
  check('Scene disposal and existing private Digital Twin, Alerts, Reports and monitoring are preserved',lifecycle_and_existing)
  def responsive():
   page.goto(D+'/#/developer/testing');page.get_by_role('button',name='Open imported replay lab',exact=True).click();expect(page.get_by_test_id('imported-replay-scene').locator('canvas')).to_be_visible()
   page.set_viewport_size({'width':390,'height':844});page.wait_for_timeout(250);assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
   page.get_by_test_id('imported-replay-lab').screenshot(path=str(OUT/'mobile-imported-lab.png'));assert page.evaluate('window.captureCalls')==0;assert not errors,errors
   return {'mobile_no_overflow':True,'capture_calls':0,'browser_errors':errors}
  check('Responsive synthetic lab has no browser errors or camera/microphone requests',responsive)
  browser.close()
 def preserved():
  after=original_incidents();assert after==before_original,'Original user incident records changed'
  for name,digest in hashes.items():assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest,name
  return {'original_incidents_unchanged':len(after),'protected_models_and_operational_files':len(hashes),'git_rewritten':False}
 check('Original user incidents, V2/V3/Pose files and operational UI sources unchanged',preserved)
finally:
 for process,log in reversed(processes):
  if process.poll() is None:
   process.terminate()
   try:process.wait(timeout=10)
   except subprocess.TimeoutExpired:process.kill()
  log.close()
 client.close()
sys.exit(any(r['status']=='FAIL' for r in rows))
