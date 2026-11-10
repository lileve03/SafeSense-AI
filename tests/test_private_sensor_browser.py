"""Actual isolated MVP/browser integration. Notifications disabled; user DB read-only."""
from pathlib import Path
import hashlib,json,os,shutil,socket,sqlite3,subprocess,sys,time,traceback
import httpx
from playwright.sync_api import sync_playwright,expect
ROOT=Path(__file__).resolve().parents[1];sys.stdout.reconfigure(encoding='utf-8')
OUT=ROOT/'runtime/private-sensor-browser';OUT.mkdir(parents=True,exist_ok=True)
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
  view=page.get_by_test_id('private-monitoring-view');expect(view).to_be_visible()
  def recorded():
   select=page.get_by_label('Raw sensor recording',exact=True);expect(select.locator('option')).to_have_count(5)
   select.select_option('radar_raw_fall');page.get_by_label('Use authorized offline research input').check()
   page.get_by_role('button',name='Analyze recording',exact=True).click()
   expect(page.get_by_text('Model: SVM_RBF-LOSO-reconstructed',exact=True)).to_be_visible(timeout=90000)
   expect(page.get_by_text('Model score (uncalibrated): 0.9932906517861326',exact=True)).to_be_visible()
   expect(page.get_by_test_id('private-twin-scene')).to_have_attribute('data-positioned-occupants','0')
   assert view.locator('video,img,audio').count()==0 and page.evaluate('window.captureCalls')==0
   page.screenshot(path=str(OUT/'recorded-radar-private-twin.png'),full_page=True)
   return {'score':.9932906517861326,'incidents':len(state()['incidents']),'positioned_occupants':0,'capture_calls':0}
  check('Real browser raw radar inference synchronizes existing private Twin without invented occupants',recorded)
  def duplicate():
   before=counts();page.get_by_role('button',name='Analyze recording',exact=True).click()
   expect(page.get_by_text('Already recorded: original incident retained.',exact=True)).to_be_visible(timeout=90000)
   assert counts()==before
   return {'counts_before_and_after':before}
  check('Repeated fresh recorded inference does not generate another incident',duplicate)
  def fusion():
   page.get_by_role('button',name='Simulate radar + acoustic fusion',exact=True).click()
   for _ in range(100):
    if any(e['level']=='HIGH' and e['processing_mode']=='simulation' for e in state()['events']):break
    page.wait_for_timeout(100)
   assert any(e['level']=='HIGH' and e['processing_mode']=='simulation' for e in state()['events'])
   page.screenshot(path=str(OUT/'simulation-fusion-private-twin.png'),full_page=True)
   page.get_by_role('button',name='Trigger test SOS',exact=True).click()
   for _ in range(100):
    if any(e['type']=='sos' and e['level']=='CRITICAL' for e in state()['events']):break
    page.wait_for_timeout(100)
   assert any(e['type']=='sos' and e['level']=='CRITICAL' for e in state()['events'])
   return {'fusion':'HIGH simulation','sos':'CRITICAL simulation'}
  check('Private controls create explainable simulation fusion and SOS through SQLite',fusion)
  def preserved():
   assert original_incidents()==before_original
   assert all(hashlib.sha256((ROOT/n).read_bytes()).hexdigest()==d for n,d in hashes.items())
   assert page.evaluate('window.captureCalls')==0 and not errors,errors
   return {'protected_files_unchanged':len(hashes),'original_incidents_unchanged':len(before_original),'browser_errors':errors}
  check('Original incidents models pose fight and private scenes preserved',preserved)
  browser.close()
finally:
 for process,log in reversed(processes):
  process.terminate()
  try:process.wait(timeout=15)
  except subprocess.TimeoutExpired:process.kill();process.wait(timeout=5)
  log.close()
sys.exit(any(r['status']=='FAIL' for r in rows))
