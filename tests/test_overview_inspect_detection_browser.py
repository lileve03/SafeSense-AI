"""Actual isolated MVP/browser integration. Notifications disabled; user DB read-only."""
from pathlib import Path
import hashlib,json,os,shutil,socket,sqlite3,subprocess,sys,time,traceback
import httpx
from playwright.sync_api import sync_playwright,expect
ROOT=Path(__file__).resolve().parents[1];sys.stdout.reconfigure(encoding='utf-8')
OUT=ROOT/'runtime/overview-inspect-detections';OUT.mkdir(parents=True,exist_ok=True)
B='http://127.0.0.1:18770';A='http://127.0.0.1:18772';D='http://127.0.0.1:3001';TOKEN='zip-integration-test'
ENV=os.environ.copy();ENV.update(SAFESENSE_DB_PATH=str(OUT/('test-'+str(time.time_ns())+'.sqlite3')),SAFESENSE_API_TOKEN=TOKEN,VITE_SAFESENSE_API_TOKEN=TOKEN,SAFESENSE_BACKEND_URL=B,SAFESENSE_AI_URL=A,VITE_API_BASE_URL=B,VITE_AI_BASE_URL=A,TELEGRAM_MODE='disabled',SAFESENSE_PRECOMPUTE_ON_START='false',SAFESENSE_EVIDENCE_DIR=str(OUT/'evidence'),SAFESENSE_ANNOTATION_DIR=str(OUT/'annotations'),SAFESENSE_ANALYSIS_CACHE_DIR=str(OUT/'cache'))
H={'X-SafeSense-Token':TOKEN};client=httpx.Client(headers=H,timeout=10);processes=[];rows=[]
protected=['dashboard/src/pages/OverviewPage.tsx','dashboard/src/pages/AlertsPage.tsx','fight_api.py','monitoring_ai.py','backend/fight_participants.py','yolo11n-pose.pt','evaluation/outputs/fight_multiclip_v2/fight_multiclip_classifier.joblib','evaluation/outputs/fight_v3/fight_v3_classifier.joblib','dashboard/src/components/private-area/PrivateAreaDigitalTwin3D.tsx','dashboard/src/components/private-area/PrivateAreaMonitoringView.tsx','dashboard/src/pages/LiveMonitoringPage.tsx','dashboard/src/pages/AnalyticsReportsPage.tsx']
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
completed={};requests=[]
try:
 start('backend',[sys.executable,'-m','uvicorn','backend.main:app','--host','127.0.0.1','--port','18770'],ROOT,18770,B+'/health')
 start('inference',[sys.executable,'-m','uvicorn','fight_api:app','--host','127.0.0.1','--port','18772'],ROOT,18772,A+'/health')
 start('frontend',[shutil.which('node'),str(ROOT/'dashboard/node_modules/vite/bin/vite.js'),'--host','127.0.0.1','--port','3001','--strictPort'],ROOT/'dashboard',3001,D)
 with sync_playwright() as pw:
  browser=pw.chromium.launch(headless=True,args=['--enable-unsafe-swiftshader']);page=browser.new_page(viewport={'width':1500,'height':1100});page.set_default_timeout(25000);errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
  page.on('request',lambda r:requests.append(r.post_data_json) if r.url==A+'/monitoring/jobs' and r.method=='POST' else None)
  def response(r):
   if '/monitoring/jobs' in r.url and r.status in (200,202):
    try:
     row=r.json()
     if row.get('status')=='COMPLETED':completed[row['camera_id']]=row
    except Exception:pass
  page.on('response',response);page.goto(D)
  def inspect(zone,camera):
   page.locator('aside').get_by_role('button',name='Overview',exact=True).click();page.locator('[data-zone-id="'+zone+'"] polygon').first.click();before=len(requests)
   page.get_by_role('button',name='Inspect Zone Feeds',exact=False).click()
   panel=page.get_by_test_id('camera-monitoring');video=panel.locator('video').first;expect(video).to_have_attribute('data-camera-id',camera)
   page.wait_for_function("()=>{const v=document.querySelector('[data-testid=camera-monitoring] video');return v?.readyState>=2&&!v.paused&&v.currentTime>.1}")
   expect(panel.get_by_test_id('fight-video-overlay')).to_be_visible(timeout=240000)
   row=completed[camera];result=row['result'];assert not result['model_errors']
   assert len(requests)==before+1 and requests[-1]['model']=='all' and requests[-1]['camera_id']==camera
   assert row['resolved_models']==['v3','pose']
   frames=[f for f in result['pose_frames'] if f['persons']];assert frames
   candidates=[f for f in frames if any(p.get('fall_candidate') for p in f['persons'])]
   frame=candidates[len(candidates)//2] if candidates else frames[len(frames)//2]
   video.evaluate('(v,t)=>{v.pause();v.currentTime=t}',frame['time_sec']+.001)
   expect(panel.get_by_test_id('video-detection-overlay')).to_have_attribute('data-frame-index',str(frame['frame_index']))
   expect(panel.get_by_test_id('person-box')).to_have_count(len(frame['persons']));assert panel.get_by_test_id('pose-bone').count()>0
   fight=next(m for m in result['model_results'] if m['model_version']=='v3');expect(panel.get_by_test_id('fight-video-overlay')).to_contain_text(f"{fight['score']:.4f}")
   if camera=='CAM_STAIRCASE':assert candidates and panel.locator('[data-fall-candidate=true] [data-testid=person-box]').first.get_attribute('stroke')=='#ef4444'
   panel.screenshot(path=str(OUT/(camera+'.png')))
   return {'camera':camera,'automatic_requests':1,'model_versions':row['resolved_models'],'cache_hit':row.get('cache_hit',False),'pose_frames':len(result['pose_frames']),'visible_boxes':len(frame['persons']),'fall_candidate_frames':len(candidates),'fight_score':fight['score'],'autoplay':True}
  for zone,camera in [('ZONE_CORRIDOR_A','CAM_CORRIDOR_A'),('ZONE_ENTRANCE','CAM_ENTRANCE'),('ZONE_STAIRCASE','CAM_STAIRCASE')]:check('Overview Inspect Zone starts genuine detection: '+zone,lambda z=zone,c=camera:inspect(z,c))
  check('Repeated Overview inspect reuses cached results',lambda:inspect('ZONE_CORRIDOR_A','CAM_CORRIDOR_A'))
  assert not errors,errors;assert original_incidents()==before_original
  browser.close()
finally:
 for process,log in reversed(processes):
  process.terminate()
  try:process.wait(timeout=15)
  except subprocess.TimeoutExpired:process.kill();process.wait(timeout=5)
  log.close()
sys.exit(any(r['status']=='FAIL' for r in rows))
