"""Actual isolated MVP/browser integration. Notifications disabled; user DB read-only."""
from pathlib import Path
import hashlib,json,os,shutil,socket,sqlite3,subprocess,sys,time,traceback
import httpx
from playwright.sync_api import sync_playwright,expect
ROOT=Path(__file__).resolve().parents[1];sys.stdout.reconfigure(encoding='utf-8')
OUT=ROOT/'runtime/reference-folder-integration';OUT.mkdir(parents=True,exist_ok=True)
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
  browser=pw.chromium.launch(headless=True,args=['--enable-unsafe-swiftshader']);page=browser.new_page(viewport={'width':1500,'height':1100});page.set_default_timeout(30000);errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
  page.add_init_script("window.captureCalls=0;if(navigator.mediaDevices)navigator.mediaDevices.getUserMedia=async()=>{window.captureCalls++;throw Error('Forbidden');};")
  page.goto(D);page.locator('aside').get_by_role('button',name='Digital Twin Map',exact=True).click();page.locator('[data-zone-id="ZONE_TOILET_BLINDSPOT"] polygon').first.click()
  scene=page.get_by_test_id('private-twin-scene');renderer=page.get_by_test_id('private-three-renderer');canvas=renderer.locator('canvas')
  def fixtures():
   expect(canvas).to_be_visible();expect(scene).to_have_attribute('data-sensor-labels','true');expect(scene).to_have_attribute('data-positioned-occupants','0')
   scene.scroll_into_view_if_needed();page.wait_for_timeout(150)
   pixels=json.loads(renderer.get_attribute('data-fixture-pixels'));bounds=canvas.bounding_box();point=pixels['radar'];assert 0<point['x']<bounds['width'] and 0<point['y']<bounds['height']
   page.mouse.click(bounds['x']+point['x'],bounds['y']+point['y']);expect(scene).to_have_attribute('data-selected-fixture','radar');expect(scene.get_by_test_id('private-fixture-detail')).to_contain_text('no observation')
   for kind in ('acoustic','sos'):
    scene.get_by_role('button',name='Inspect '+kind+' sensor',exact=True).click();expect(scene).to_have_attribute('data-selected-fixture',kind)
   scene.get_by_title('Toggle sensor labels',exact=True).click();expect(scene).to_have_attribute('data-sensor-labels','false');scene.get_by_title('Toggle sensor labels',exact=True).click()
   camera=renderer.get_attribute('data-camera-position');scene.get_by_title('Zoom In',exact=True).click();assert renderer.get_attribute('data-camera-position')!=camera;scene.get_by_title('Reset Orbit View',exact=True).click();expect(renderer).to_have_attribute('data-camera-position',camera)
   page.wait_for_timeout(400);a=int(renderer.get_attribute('data-render-count'));page.wait_for_timeout(500);assert int(renderer.get_attribute('data-render-count'))-a<=1
   scene.screenshot(path=str(OUT/'original-room-clickable-sensors.png'))
   return {'actual_canvas_sensor_click':True,'accessible_sensor_inspection':3,'label_toggle':True,'zoom_reset':True,'idle_extra_renders':int(renderer.get_attribute('data-render-count'))-a}
  check('Adapted Three.js text sprites raycast inspection toggle and original controls',fixtures)
  def analyze(identifier,version):
   page.get_by_label('Raw sensor recording',exact=True).select_option(identifier);page.get_by_label('Use authorized offline research input').check();page.get_by_role('button',name='Analyze recording',exact=True).click();expect(page.get_by_text('Model: '+version,exact=True)).to_be_visible(timeout=90000)
   history=client.get(B+'/testing/runs').json();row=next(r for r in history if r['scenario_id']==identifier and r['status']=='COMPLETED');return client.get(B+'/testing/runs/'+row['id']).json()['result']
  def acoustic():
   result=analyze('acoustic_scream','YAMNet-pretrained-local-cache');windows=result['score_windows'];assert windows and abs(max(w['score'] for w in windows)-result['score'])<1e-8
   assert all(w['start_sec']==round(w['index']*.48,6) and 0<=w['score']<=1 and w['start_sec']<w['end_sec']<=result['audio_duration_sec'] for w in windows)
   timeline=page.get_by_test_id('acoustic-score-timeline');expect(timeline).to_be_visible();assert len(timeline.get_by_test_id('acoustic-score-line').get_attribute('points').split())==len(windows)
   timeline.get_by_role('button',name='Inspect peak window',exact=True).click();peak=max(windows,key=lambda w:w['score']);expect(timeline).to_have_attribute('data-window-index',str(peak['index']));expect(timeline.get_by_test_id('acoustic-window-detail')).to_contain_text(f"{peak['score']:.6f}")
   before=counts();timeline.get_by_role('button',name='Play score replay',exact=True).click();page.wait_for_timeout(300);timeline.get_by_role('button',name='Pause score replay',exact=True).click();assert counts()==before
   expect(scene).to_have_attribute('data-acoustic-active','true');expect(scene).to_have_attribute('data-positioned-occupants','0')
   timeline.screenshot(path=str(OUT/'actual-yamnet-score-windows.png'))
   return {'model':result['model_version'],'actual_score':result['score'],'score_windows':len(windows),'above_threshold':result['above_threshold_windows'],'peak_window':peak,'replay_incidents_added':0,'incident_id':result['event_delivery']['incident_id']}
  check('Phase 2 score-window plot adapted to fresh local YAMNet with side-effect-free replay',acoustic)
  def radar_and_fusion():
   result=analyze('radar_raw_fall','SVM_RBF-LOSO-reconstructed');assert result['n_points']==238 and result['n_frames']==24;expect(scene).to_have_attribute('data-fall-active','true');expect(scene).to_have_attribute('data-positioned-occupants','0')
   real=[i for i in state()['incidents'] if i['processing_mode']=='real_model'];assert len(real)==2 and all(i['level']=='OBSERVE' for i in real)
   page.get_by_role('button',name='Simulate radar + acoustic fusion',exact=True).click()
   for _ in range(100):
    fusion=[i for i in state()['incidents'] if i['processing_mode']=='simulation' and i['level']=='HIGH']
    if fusion:break
    page.wait_for_timeout(100)
   assert fusion;scene.get_by_role('button',name='Inspect radar sensor',exact=True).click();scene.screenshot(path=str(OUT/'sensor-fusion-original-room.png'))
   page.get_by_role('button',name='Trigger test SOS',exact=True).click();expect(scene).to_have_attribute('data-sos-active','true');scene.get_by_test_id('private-incident-indicator').click();expect(page.get_by_test_id('incident-evidence')).to_be_visible();assert page.get_by_test_id('incident-evidence').locator('video,img,audio').count()==0;page.get_by_role('button',name='Close',exact=True).click()
   return {'radar_points_not_people':238,'radar_frames':24,'separate_recordings_unfused':True,'labeled_simulation_fusion':'HIGH','SOS':'CRITICAL','actual_incident_dossier':True}
  check('Actual radar existing fusion SOS SQLite and incident details stay integrated',radar_and_fusion)
  def negative():
   result=analyze('acoustic_background','YAMNet-pretrained-local-cache');assert not result['candidate_detected'] and not any(w['above_threshold'] for w in result['score_windows']);expect(scene).to_have_attribute('data-acoustic-active','false')
   return {'actual_score':result['score'],'genuine_windows':len(result['score_windows']),'false_scream_incident':result['event_delivery']['incident_id']}
  check('Actual negative YAMNet input remains negative and clears acoustic indicator',negative)
  def privacy_navigation():
   for extra in ({'source':'vision'},{'sensor_modality':'vision'},{'evidence_media':[{'url':'cctv.jpg'}]}):assert client.post(B+'/event',json={'zone':'ZONE_TOILET_BLINDSPOT','type':'fall','source':'radar','processing_mode':'simulation',**extra}).status_code in (403,422)
   assert page.evaluate('window.captureCalls')==0
   assert not page.get_by_test_id('private-monitoring-view').locator('video,img,audio').count()
   page.locator('aside').get_by_role('button',name='Alerts',exact=True).click();expect(page.get_by_title('Inspect Full Incident Review Dossier').first).to_be_visible()
   page.locator('aside').get_by_role('button',name='Analytics & Reports',exact=True).click();expect(page.get_by_test_id('analytics-reports')).to_be_visible()
   page.locator('aside').get_by_role('button',name='Digital Twin Map',exact=True).click()
   if not page.get_by_test_id('private-twin-scene').count():page.locator('[data-zone-id="ZONE_TOILET_BLINDSPOT"] polygon').first.click()
   expect(page.get_by_test_id('private-twin-scene').locator('canvas')).to_have_count(1)
   page.set_viewport_size({'width':390,'height':844});page.wait_for_timeout(300);assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1');page.get_by_test_id('private-twin-scene').screenshot(path=str(OUT/'original-room-mobile-sensors.png'))
   assert original_incidents()==before_original and not errors,errors
   assert all(hashlib.sha256((ROOT/n).read_bytes()).hexdigest()==d for n,d in hashes.items())
   return {'private_capture_calls':0,'privacy_rejection':True,'Alerts_Reports_original_room_navigation':True,'mobile_overflow':False,'browser_errors':errors,'original_incidents_unchanged':len(before_original),'protected_file_hashes':len(hashes)}
  check('Privacy sensor synchronization page navigation responsive design and models preserved',privacy_navigation)
  browser.close()
finally:
 for process,log in reversed(processes):
  process.terminate()
  try:process.wait(timeout=15)
  except subprocess.TimeoutExpired:process.kill();process.wait(timeout=5)
  log.close()
sys.exit(any(r['status']=='FAIL' for r in rows))
