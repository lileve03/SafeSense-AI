"""Actual isolated HTTP + browser workflow. Never sends Telegram or touches existing services."""
from pathlib import Path
import json,os,subprocess,sys,time,traceback,shutil
import httpx

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
sys.stdout.reconfigure(encoding='utf-8')
OUT=ROOT/'runtime/fight-participants/v2-verification'
OUT.mkdir(parents=True,exist_ok=True)
RESULTS=[]
ENV=os.environ.copy()
ENV.update(SAFESENSE_DB_PATH=str(OUT/('test-'+str(int(time.time()))+'.sqlite3')),
           SAFESENSE_BACKEND_URL='http://127.0.0.1:18000',TELEGRAM_MODE='disabled',
           SAFESENSE_AI_URL='http://127.0.0.1:18001',
           VITE_API_BASE_URL='http://127.0.0.1:18000',VITE_AI_BASE_URL='http://127.0.0.1:18001',SAFESENSE_DASHBOARD_URL='http://127.0.0.1:3001',
           SAFESENSE_API_TOKEN='monitoring-integration-test',VITE_SAFESENSE_API_TOKEN='monitoring-integration-test')
H={'X-SafeSense-Token':ENV['SAFESENSE_API_TOKEN']}
B='http://127.0.0.1:18000';A='http://127.0.0.1:18001'
client=httpx.Client(headers=H,timeout=20)
processes=[]

def check(name,fn):
    started=time.perf_counter()
    try:
        actual=fn();row={'test':name,'status':'PASS','actual':actual}
    except Exception as exc:
        row={'test':name,'status':'FAIL','actual':str(exc),'trace':traceback.format_exc()}
    row['seconds']=round(time.perf_counter()-started,3);RESULTS.append(row)
    (OUT/'results.json').write_text(json.dumps(RESULTS,indent=2),encoding='utf-8')
    print(row['status'],name,str(row['actual'])[:500],flush=True)

def expect(response,code=200):
    assert response.status_code==code,(response.status_code,response.text[:500])
    return response.json()

def start(name,cmd,url,cwd=ROOT):
    log=(OUT/(name+'.log')).open('w',encoding='utf-8')
    p=subprocess.Popen(cmd,cwd=cwd,env=ENV,stdout=log,stderr=subprocess.STDOUT,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    processes.append((p,log))
    for _ in range(180):
        if p.poll() is not None:raise RuntimeError(name+' exited; see log')
        try:
            if httpx.get(url,timeout=1).status_code==200:return p
        except OSError:pass
        except httpx.HTTPError:pass
        time.sleep(.25)
    raise RuntimeError(name+' startup timed out')

def job(scenario,model,zone):
    r=expect(client.post(A+'/monitoring/jobs',json={'scenario_id':scenario,'model':model,'zone_id':zone,'authorized':True}),202)
    if scenario=='conflict' and model=='v2':
        duplicate=expect(client.post(A+'/monitoring/jobs',json={'scenario_id':scenario,'model':model,'zone_id':zone,'authorized':True}),202)
        assert duplicate['id']==r['id'],'Active identical CPU jobs must coalesce'
    deadline=time.monotonic()+240
    while time.monotonic()<deadline:
        row=expect(client.get(A+'/monitoring/jobs/'+r['id']))
        if row['status']=='COMPLETED':return row
        assert row['status'] in ('QUEUED','RUNNING'),row
        time.sleep(.5)
    raise AssertionError('Inference timed out')

saved={}
def camera_job(scenario,camera,zone):
    row=expect(client.post(A+'/monitoring/jobs',json={'scenario_id':scenario,'camera_id':camera,'zone_id':zone,'model':'all','authorized':True}),202)
    for _ in range(480):
        row=expect(client.get(A+'/monitoring/jobs/'+row['id']))
        if row['status']=='COMPLETED':return row
        assert row['status'] in ('RUNNING','QUEUED'),row
        time.sleep(.5)
    raise AssertionError('Inference deadline exceeded')

ENV.update(SAFESENSE_EVIDENCE_DIR=str(OUT/'evidence'),SAFESENSE_ANNOTATION_DIR=str(OUT/'annotations'),SAFESENSE_ANALYSIS_CACHE_DIR=str(OUT/'cache'),SAFESENSE_PRECOMPUTE_ON_START='false')
registry=[{'camera_id':identifier,'camera_name':name,'zone_id':zone,'scenario_id':scenario} for identifier,name,zone,scenario in [
 ('CAM_CORRIDOR_A','Corridor A','ZONE_CORRIDOR_A','conflict'),('CAM_CANTEEN','Canteen','ZONE_CANTEEN','normal'),
 ('CAM_STAIRCASE','Staircase','ZONE_STAIRCASE','fall'),('CAM_ENTRANCE','School Entrance','ZONE_ENTRANCE','adl_01'),('CAM_HALL','School Hall','ZONE_SCHOOL_HALL','adl_02'),
 ('CAM_FIGHT_CAM2','AIRTLab Fight Cam2','ZONE_CORRIDOR_A','conflict_cam2'),('CAM_NORMAL_CAM2','AIRTLab Normal Cam2','ZONE_CANTEEN','normal_cam2')]]
config=OUT/'camera-registry.json';config.write_text(json.dumps(registry));ENV['SAFESENSE_CAMERA_REGISTRY']=str(config)

registry=[{'camera_id':'CAM_CORRIDOR_A','camera_name':'Corridor A','zone_id':'ZONE_CORRIDOR_A','scenario_id':'conflict','fight_model':'v2'},
          {'camera_id':'CAM_CANTEEN','camera_name':'Canteen','zone_id':'ZONE_CANTEEN','scenario_id':'normal','fight_model':'v2'}]
config.write_text(json.dumps(registry))
try:
 start('backend',[sys.executable,'-m','uvicorn','backend.main:app','--host','127.0.0.1','--port','18000'],B+'/health')
 start('inference',[sys.executable,'-m','uvicorn','fight_api:app','--host','127.0.0.1','--port','18001'],A+'/health')
 start('frontend',[shutil.which('node'),str(ROOT/'dashboard/node_modules/vite/bin/vite.js'),'--host','127.0.0.1','--port','3001','--strictPort'],'http://127.0.0.1:3001',ROOT/'dashboard')
 from playwright.sync_api import sync_playwright,expect as be
 with sync_playwright() as pw:
  browser=pw.chromium.launch(headless=True);page=browser.new_page(viewport={'width':1600,'height':1100});completed={}
  def response(r):
   if '/monitoring/jobs' in r.url and r.status in (200,202):
    try:
     row=r.json()
     if row.get('status')=='COMPLETED':completed[row['camera_id']]=row
    except Exception:pass
  page.on('response',response)
  page.goto('http://127.0.0.1:3001');page.locator('aside').get_by_role('button',name='Live Monitoring',exact=True).click()
  panel=page.get_by_test_id('camera-monitoring');video=panel.locator('video').first
  def case(camera,positive):
   panel.get_by_role('button',name=camera['camera_name']+' '+camera['camera_id']+' RECORDED REAL VIDEO',exact=True).click()
   be(panel.get_by_test_id('fight-video-overlay')).to_be_visible(timeout=240000)
   row=completed[camera['camera_id']];r=row['result'];fight=next(m for m in r['model_results'] if m['model_version']=='v2')
   assert row['resolved_models']==['v2','pose'] and fight['candidate_detected']==positive
   frames=[f for f in r['pose_frames'] if any(p['fight_participant'] for p in f['persons'])]
   if positive:
    assert frames
    page.wait_for_function("()=>document.querySelectorAll('[data-fight-participant=true]').length>=2")
    video.evaluate('v=>v.pause()');page.wait_for_timeout(60)
    banner=panel.get_by_test_id('fight-video-overlay').inner_text();assert 'V2' in banner and f"{fight['score']:.4f}" in banner
    for g in panel.locator('[data-fight-participant=true]').all():assert 'participant score:' in g.text_content() and g.get_by_test_id('person-box').get_attribute('stroke')=='#ef4444'
    video.locator('..').screenshot(path=str(OUT/'v2-participants.png'))
    item=fight['evidence_media'][0];manifest=expect(client.get(A+'/monitoring/incidents/'+fight['event_delivery']['incident_id']+'/evidence/'+item['id']+'/metadata'))
    assert manifest['overlay_result']['model_results'][0]['model_version']=='v2'
    assert any(p['fight_participant'] for f in manifest['overlay_result']['pose_frames'] for p in f['persons'])
   else:
    assert not frames;assert panel.locator('[data-fight-participant=true]').count()==0
   (OUT/(camera['camera_id']+'-result.json')).write_text(json.dumps(row),encoding='utf-8')
   return {'camera':camera['camera_id'],'selected_models':row['resolved_models'],'version':'v2','whole_clip_score':fight['score'],'participant_frames':len(frames),'participant_instances':sum(p['fight_participant'] for f in r['pose_frames'] for p in f['persons']),'evidence_metadata_verified':positive}
  check('Actual V2 whole-clip score and separate red interaction participants',lambda:case(registry[0],True))
  check('Actual V2 non-fight recording abstains from person red overlays',lambda:case(registry[1],False))
  browser.close()
finally:
 for process,log in reversed(processes):
  if process.poll() is None:
   process.terminate()
   try:process.wait(timeout=10)
   except subprocess.TimeoutExpired:process.kill()
  log.close()
 client.close()
sys.exit(any(r['status']=='FAIL' for r in RESULTS))
