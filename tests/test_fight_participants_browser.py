"""Actual isolated HTTP + browser workflow. Never sends Telegram or touches existing services."""
from pathlib import Path
import json,os,subprocess,sys,time,traceback,shutil
import httpx

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
sys.stdout.reconfigure(encoding='utf-8')
OUT=ROOT/'runtime/fight-participants/verification'
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
try:
 start('backend',[sys.executable,'-m','uvicorn','backend.main:app','--host','127.0.0.1','--port','18000'],B+'/health')
 start('inference',[sys.executable,'-m','uvicorn','fight_api:app','--host','127.0.0.1','--port','18001'],A+'/health')
 start('frontend',[shutil.which('node'),str(ROOT/'dashboard/node_modules/vite/bin/vite.js'),'--host','127.0.0.1','--port','3001','--strictPort'],'http://127.0.0.1:3001',ROOT/'dashboard')
 from playwright.sync_api import sync_playwright,expect as be
 from backend.fight_participants import annotate_participants
 with sync_playwright() as pw:
  browser=pw.chromium.launch(headless=True);page=browser.new_page(viewport={'width':1600,'height':1100});page.set_default_timeout(20000)
  errors=[];page.on('pageerror',lambda e:errors.append(str(e)));completed={}
  def response(r):
   if '/monitoring/jobs' in r.url and r.status in (200,202):
    try:
     row=r.json()
     if row.get('status')=='COMPLETED':completed[row['camera_id']]=row
    except Exception:pass
  page.on('response',response)
  page.goto('http://127.0.0.1:3001');page.locator('aside').get_by_role('button',name='Live Monitoring',exact=True).click()
  panel=page.get_by_test_id('camera-monitoring');video=panel.locator('video').first
  def choose(camera):
   panel.get_by_role('button',name=camera['camera_name']+' '+camera['camera_id']+' RECORDED REAL VIDEO',exact=True).click()
   be(video).to_have_attribute('data-camera-id',camera['camera_id'])
   page.wait_for_function("()=>{const v=document.querySelector('[data-testid=camera-monitoring] video');return v.readyState>=2&&!v.paused}")
   be(panel.get_by_test_id('fight-video-overlay')).to_be_visible(timeout=240000)
   return completed[camera['camera_id']]
  def case(camera,require_positive=False,require_none=False):
   started=time.perf_counter();row=choose(camera);r=row['result'];saved[camera['camera_id']]=r
   assert not r['model_errors'] and len(r['model_results'])==2
   assert r['participant_heuristic']['version']=='pose-interaction-v1'
   rawpose=next(m for m in r['model_results'] if m['model_version'].startswith('yolo'));fight=next(m for m in r['model_results'] if m['model_version']=='v3')
   assert len(rawpose['pose_frames'])==len(r['pose_frames'])
   for original,enriched in zip(rawpose['pose_frames'],r['pose_frames']):
    assert len(original['persons'])==len(enriched['persons'])
    for p,q in zip(original['persons'],enriched['persons']):assert p['bbox_xyxy']==q['bbox_xyxy'] and p['keypoints']==q['keypoints']
   candidates=[f for f in r['pose_frames'] if any(p['fight_participant'] for p in f['persons'])]
   if require_positive:assert candidates
   if require_none:assert not candidates
   if candidates:
    # Verify the first red candidates are seen during natural playback, before seeking.
    page.wait_for_function("()=>{const v=document.querySelector('[data-testid=camera-monitoring] video');return !v.paused&&document.querySelectorAll('[data-fight-participant=true]').length>0}",timeout=20000)
    video.evaluate('v=>v.pause()');page.wait_for_timeout(70)
    video.locator('..').screenshot(path=str(OUT/(camera['camera_id']+'-natural-playback.png')))
    # Pick an actual candidate frame with visible bystanders for the main proof.
    frame=next((f for f in candidates if len(f['persons'])>=4),candidates[len(candidates)//2])
    for target in [frame['time_sec']+.001,0,frame['time_sec']+.001]:
     video.evaluate('(v,t)=>{v.pause();v.currentTime=t}',target)
     page.wait_for_function("()=>{const v=document.querySelector('[data-testid=camera-monitoring] video');return !v.seeking&&v.readyState>=2}")
     actual_index=int(panel.get_by_test_id('video-detection-overlay').get_attribute('data-frame-index'))
     actual=r['pose_frames'][actual_index];red=panel.locator('[data-fight-participant=true]')
     assert red.count()==sum(p['fight_participant'] for p in actual['persons'])
    red=panel.locator('[data-fight-participant=true]');assert red.count()>=2
    for element in red.all():
     assert element.get_by_test_id('person-box').get_attribute('stroke')=='#ef4444'
     assert 'participant score:' in element.text_content() and 'heuristic' in element.text_content()
     assert int(element.get_attribute('data-interaction-track-id'))>0
    normals=panel.locator('[data-fight-participant=false][data-fall-candidate=false]')
    for element in normals.all():assert element.get_by_test_id('person-box').get_attribute('stroke')=='#22d3ee'
    assert panel.get_by_test_id('pose-bone').count()>0
    assert f"{fight['score']:.4f}" in panel.get_by_test_id('fight-video-overlay').inner_text()
    video.locator('..').screenshot(path=str(OUT/(camera['camera_id']+'-participants.png')))
    page.screenshot(path=str(OUT/(camera['camera_id']+'-dashboard.png')),full_page=True)
   else:
    frame=next(f for f in r['pose_frames'] if f['persons'])
    video.evaluate('(v,t)=>{v.pause();v.currentTime=t}',frame['time_sec']+.001)
    page.wait_for_function("()=>{const v=document.querySelector('[data-testid=camera-monitoring] video');return !v.seeking}")
    assert panel.locator('[data-fight-participant=true]').count()==0
    video.locator('..').screenshot(path=str(OUT/(camera['camera_id']+'-no-participants.png')))
   (OUT/(camera['camera_id']+'-result.json')).write_text(json.dumps(row),encoding='utf-8')
   return {'camera':camera['camera_id'],'classifier_score':fight['score'],'classifier_positive':fight['candidate_detected'],'pose_frames':len(r['pose_frames']),'participant_frames':len(candidates),'participant_instances':sum(p['fight_participant'] for f in r['pose_frames'] for p in f['persons']),'interaction_track_ids':sorted({p['interaction_track_id'] for f in candidates for p in f['persons'] if p['fight_participant']}),'events':r['participant_events'],'heuristic_cpu_sec':r['participant_processing_sec'],'wall_sec':round(time.perf_counter()-started,3)}
  for camera_id,positive,none in [('CAM_CORRIDOR_A',True,False),('CAM_CANTEEN',False,True),('CAM_FIGHT_CAM2',False,False),('CAM_NORMAL_CAM2',False,True)]:
   camera=next(c for c in registry if c['camera_id']==camera_id)
   check('Actual AIRTLab interaction localization: '+camera_id,lambda camera=camera,positive=positive,none=none:case(camera,positive,none))
  def strict_control():
   r=saved['CAM_CORRIDOR_A'];pose=next(m for m in r['model_results'] if m['model_version'].startswith('yolo'));fight=next(m for m in r['model_results'] if m['model_version']=='v3')
   # Actual pose sequence remains unchanged; removing classifier support must remove all red candidates.
   output=annotate_participants(pose,{**fight,'candidate_detected':False})
   assert not any(p['fight_participant'] for f in output['pose_frames'] for p in f['persons'])
   mismatched=annotate_participants(pose,{**fight,'input_sha256':'different-source'})
   assert not mismatched['participant_heuristic']['enabled']
   return {'same_actual_poses_no_classifier_support':'no participants','wrong_source_hash':'no participants'}
  check('Actual pose negative-gating and source-provenance controls',strict_control)
  def evidence():
   r=saved['CAM_CORRIDOR_A'];fight=next(m for m in r['model_results'] if m['model_version']=='v3');identifier=fight['event_delivery']['incident_id'];item=fight['evidence_media'][0]
   url=A+'/monitoring/incidents/'+identifier+'/evidence/'+item['id']
   metadata=expect(client.get(url+'/metadata'));overlay=metadata['overlay_result']
   assert overlay['analysis_id']==fight['analysis_id'] and overlay['input_sha256']==fight['input_sha256']
   assert any(p['fight_participant'] for f in overlay['pose_frames'] for p in f['persons'])
   assert client.get(url,headers={'Range':'bytes=0-1023'}).status_code==206
   page.locator('aside').get_by_role('button',name='Incident Review',exact=True).click();page.get_by_placeholder('Search notes, staff, incident #...').fill(identifier[:8]);page.get_by_role('button',name='Audit Details',exact=True).click()
   section=page.get_by_test_id('incident-evidence');clip=section.locator('video');be(clip).to_have_attribute('data-variant','original')
   frame=next(f for f in overlay['pose_frames'] if any(p['fight_participant'] for p in f['persons']))
   page.wait_for_function("()=>document.querySelector('[data-testid=incident-evidence] video')?.readyState>=2")
   clip.evaluate('(v,t)=>{v.pause();v.currentTime=t}',frame['time_sec']-metadata['start_sec']+.001)
   page.wait_for_function("()=>!document.querySelector('[data-testid=incident-evidence] video').seeking")
   be(section.locator('[data-fight-participant=true]').first).to_be_visible()
   clip.scroll_into_view_if_needed();clip.locator('..').screenshot(path=str(OUT/'audit-participant-evidence.png'))
   page.get_by_role('button',name='Close',exact=True).click();page.locator('aside').get_by_role('button',name='Digital Twin Map',exact=True).click();be(page.locator('main')).to_be_visible()
   page.locator('aside').get_by_role('button',name='Alerts',exact=True).click();be(page.get_by_title('Inspect Full Incident Review Dossier').first).to_be_visible()
   return {'incident':identifier,'analysis_id':fight['analysis_id'],'matching_overlay':True,'range_status':206,'audit_browser_red_candidates':True,'digital_twin_and_alerts':True}
  check('Actual incident evidence, Audit Details and downstream pages preserve genuine participant metadata',evidence)
  def switch_and_fall():
   page.locator('aside').get_by_role('button',name='Live Monitoring',exact=True).click()
   for camera_id in ['CAM_ENTRANCE','CAM_HALL']:
    camera=next(c for c in registry if c['camera_id']==camera_id);r=choose(camera)['result'];assert not any(p['fight_participant'] for f in r['pose_frames'] for p in f['persons'])
    assert panel.locator('[data-fight-participant=true]').count()==0
   fall=next(c for c in registry if c['camera_id']=='CAM_STAIRCASE');r=choose(fall)['result']
   frame=next(f for f in r['pose_frames'] if any(p.get('fall_rule_active') for p in f['persons']))
   video.evaluate('(v,t)=>{v.pause();v.currentTime=t}',frame['time_sec']+.001)
   page.wait_for_function("()=>!document.querySelector('[data-testid=camera-monitoring] video').seeking")
   be(panel.locator('[data-fall-candidate=true]').first).to_be_visible();assert panel.locator('[data-fight-participant=true]').count()==0
   page.screenshot(path=str(OUT/'fall-preserved.png'),full_page=True)
   return {'entrance_hall_no_stale_red':True,'fall_binary_red_preserved':True}
  check('Entrance/Hall switching and original fall-rule overlay remain correct',switch_and_fall)
  def cached():
   r=saved['CAM_CORRIDOR_A'];before=expect(client.get(B+'/state'));camera=registry[0]
   started=time.perf_counter();row=expect(client.post(A+'/monitoring/jobs',json={'scenario_id':camera['scenario_id'],'camera_id':camera['camera_id'],'zone_id':camera['zone_id'],'model':'all','authorized':True}),202)
   assert row.get('cache_hit') and row['result']['pose_frames']==r['pose_frames']
   after=expect(client.get(B+'/state'));assert len(before['events'])==len(after['events']) and len(before['incidents'])==len(after['incidents'])
   assert client.post(A+'/monitoring/jobs',json={'scenario_id':'conflict','camera_id':'CAM_CORRIDOR_A','zone_id':'ZONE_TOILET_BLINDSPOT','model':'all','authorized':True}).status_code==403
   return {'cached_metadata_identical':True,'api_ms':round((time.perf_counter()-started)*1000,2),'no_repeated_events':True,'private_video_denied':403}
  check('Participant cache replay is exact, event-idempotent and privacy protected',cached)
  assert not errors,errors;browser.close()
finally:
 for process,log in reversed(processes):
  if process.poll() is None:
   process.terminate()
   try:process.wait(timeout=10)
   except subprocess.TimeoutExpired:process.kill()
  log.close()
 client.close()
print(json.dumps({'passed':sum(r['status']=='PASS' for r in RESULTS),'failed':sum(r['status']=='FAIL' for r in RESULTS)}))
sys.exit(any(r['status']=='FAIL' for r in RESULTS))
