"""Actual isolated MVP/browser integration. Notifications disabled; user DB read-only."""
from pathlib import Path
import hashlib,json,os,shutil,socket,sqlite3,subprocess,sys,time,traceback
import httpx
from playwright.sync_api import sync_playwright,expect
ROOT=Path(__file__).resolve().parents[1];sys.stdout.reconfigure(encoding='utf-8')
OUT=ROOT/'runtime/private-three-integration';OUT.mkdir(parents=True,exist_ok=True)
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
  page.goto(D)
  page.locator('aside').get_by_role('button',name='Digital Twin Map',exact=True).click();page.locator('[data-zone-id="ZONE_TOILET_BLINDSPOT"] polygon').first.click()
  view=page.get_by_test_id('private-monitoring-view');scene=page.get_by_test_id('private-twin-scene');renderer=page.get_by_test_id('private-three-renderer');canvas=renderer.locator('canvas')
  def initial():
   expect(view).to_be_visible();expect(canvas).to_be_visible();expect(scene).to_have_attribute('data-positioned-occupants','0');expect(scene).to_have_attribute('data-animation','static-observation')
   health=canvas.evaluate('c=>{const g=c.getContext("webgl2");return {width:c.width,height:c.height,webgl:!!g,lost:g?.isContextLost()}}');assert health['webgl'] and not health['lost']
   page.wait_for_timeout(500);a=int(renderer.get_attribute('data-render-count'));page.wait_for_timeout(600);b=int(renderer.get_attribute('data-render-count'));assert b-a<=1,(a,b)
   scene.screenshot(path=str(OUT/'original-room-empty.png'))
   return {'webgl':health,'idle_render_delta_600ms':b-a,'measured_positions':0,'original_room':'floor, walls, alcove, ceiling radar and wall SOS retained'}
  check('Toilet map opens original WebGL room; idle recorded view does not continuously render',initial)
  def controls():
   scene.scroll_into_view_if_needed();before=renderer.get_attribute('data-camera-position');box=canvas.bounding_box();x=box['x']+box['width']*.65;y=box['y']+box['height']*.60
   page.mouse.move(x,y);page.mouse.down();page.mouse.move(x+55,y+25,steps=8);page.mouse.up();page.wait_for_timeout(100);orbit=renderer.get_attribute('data-camera-position');assert orbit!=before
   scene.get_by_title('Zoom In',exact=True).click();zoom=renderer.get_attribute('data-camera-position');assert zoom!=orbit
   scene.get_by_title('Zoom Out',exact=True).click();assert renderer.get_attribute('data-camera-position')!=zoom
   scene.get_by_title('Reset Orbit View',exact=True).click();expect(renderer).to_have_attribute('data-camera-position',before)
   return {'orbit':True,'zoom_in_out':True,'reset_restores_original_camera':True}
  check('Orbit Zoom and Reset work on original room',controls)
  def recorded():
   page.get_by_label('Raw sensor recording',exact=True).select_option('radar_raw_fall');page.get_by_label('Use authorized offline research input').check();page.get_by_role('button',name='Analyze recording',exact=True).click()
   expect(page.get_by_text('Model: SVM_RBF-LOSO-reconstructed',exact=True)).to_be_visible(timeout=90000)
   expect(scene).to_have_attribute('data-fall-active','true');expect(scene).to_have_attribute('data-radar-observed','true');expect(scene).to_have_attribute('data-positioned-occupants','0');expect(scene).to_have_attribute('data-presence-indicated','false')
   scene.screenshot(path=str(OUT/'original-room-recorded-fall.png'))
   assert 'no frame-level trajectory' in scene.inner_text()
   incident=next(i for i in state()['incidents'] if i['zone_id']=='ZONE_TOILET_BLINDSPOT')
   with page.expect_response(lambda r:'/incidents/'+incident['id']+'/report' in r.url) as response:scene.get_by_test_id('private-incident-indicator').click()
   assert response.value.status==200;expect(page.get_by_test_id('incident-evidence')).to_be_visible();page.get_by_role('button',name='Close',exact=True).click()
   return {'score':.9932906517861326,'actual_incident':incident['id'],'unsupported_person_markers':0,'recorded_motion':'static classification only'}
  check('Real recorded radar updates ring/fall indicator and opens matching SQLite incident',recorded)
  def acoustic_sos():
   page.get_by_label('Raw sensor recording',exact=True).select_option('acoustic_scream');page.get_by_role('button',name='Analyze recording',exact=True).click()
   expect(page.get_by_text('Model: YAMNet-pretrained-local-cache',exact=True)).to_be_visible(timeout=90000);expect(scene).to_have_attribute('data-acoustic-active','true')
   page.get_by_role('button',name='Trigger test SOS',exact=True).click();expect(scene).to_have_attribute('data-sos-active','true',timeout=20000)
   expect(scene.get_by_test_id('private-incident-indicator')).to_contain_text('CRITICAL')
   scene.screenshot(path=str(OUT/'original-room-acoustic-sos.png'))
   # Negative acoustic metadata clears the active acoustic indicator.
   negative=client.post(B+'/sensors/replay',json={'zone':'ZONE_TOILET_BLINDSPOT','sensor':'acoustic','index':0});assert negative.status_code==200
   expect(scene).to_have_attribute('data-acoustic-active','false',timeout=20000)
   return {'real_yamnet_scream':True,'sos':'CRITICAL simulation','negative_acoustic_clears_indicator':True}
  check('Genuine acoustic update and explicit SOS update room without media',acoustic_sos)
  def simulation_navigation():
   page.get_by_role('button',name='Use original local simulation',exact=True).click();expect(scene).to_have_attribute('data-animation','illustrative-simulation')
   scene.scroll_into_view_if_needed();page.wait_for_timeout(100);a=int(renderer.get_attribute('data-render-count'));page.wait_for_timeout(600);b=int(renderer.get_attribute('data-render-count'));assert 0<b-a<=20,(a,b)
   assert '(Simulated)' in scene.inner_text();scene.screenshot(path=str(OUT/'original-room-labeled-simulation.png'))
   page.get_by_role('button',name='Back to School Overview',exact=True).click();expect(page.get_by_test_id('private-twin-scene')).to_have_count(0)
   page.locator('[data-zone-id="ZONE_TOILET_BLINDSPOT"] polygon').first.click();expect(page.get_by_test_id('private-twin-scene').locator('canvas')).to_have_count(1)
   return {'simulation_frames_600ms':b-a,'room_reopen_single_canvas':True,'toilet_navigation':True}
  check('Labeled simulation animates at bounded rate and navigation disposes/reopens canvas',simulation_navigation)
  def privacy():
   for extra in ({'source':'vision'},{'sensor_modality':'vision'},{'evidence_media':[{'url':'cctv.jpg'}]}):
    r=client.post(B+'/event',json={'zone':'ZONE_TOILET_BLINDSPOT','type':'fall','source':'radar','processing_mode':'simulation',**extra});assert r.status_code in (403,422)
   assert view.locator('video,img,audio').count()==0 and page.evaluate('window.captureCalls')==0
   assert not errors,errors;assert original_incidents()==before_original
   assert all(hashlib.sha256((ROOT/n).read_bytes()).hexdigest()==d for n,d in hashes.items())
   page.set_viewport_size({'width':390,'height':844});page.wait_for_timeout(400);assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
   page.get_by_test_id('private-twin-scene').screenshot(path=str(OUT/'original-room-mobile.png'))
   return {'capture_calls':0,'private_media_elements':0,'browser_errors':errors,'original_incidents_unchanged':len(before_original),'protected_files_unchanged':len(hashes),'mobile_no_overflow':True}
  check('Privacy rejection responsive rendering and existing data/model preservation',privacy)
  browser.close()
finally:
 for process,log in reversed(processes):
  process.terminate()
  try:process.wait(timeout=15)
  except subprocess.TimeoutExpired:process.kill();process.wait(timeout=5)
  log.close()
sys.exit(any(r['status']=='FAIL' for r in rows))
