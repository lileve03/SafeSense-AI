"""Actual isolated HTTP + browser workflow. Never sends Telegram or touches existing services."""
from pathlib import Path
import json,os,subprocess,sys,time,traceback,shutil
import httpx

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
sys.stdout.reconfigure(encoding='utf-8')
OUT=ROOT/'runtime/automatic-monitoring'
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

ENV['SAFESENSE_EVIDENCE_DIR']=str(OUT/('evidence-'+str(time.time_ns())))

# Operator-configured V2 baseline for Corridor A; other cameras use global V3.
configured=[]
for cid,zone,name,scenario in [('CAM_CORRIDOR_A','ZONE_CORRIDOR_A','Corridor A','conflict'),('CAM_CANTEEN','ZONE_CANTEEN','Canteen','normal'),('CAM_STAIRCASE','ZONE_STAIRCASE','Staircase','fall'),('CAM_ENTRANCE','ZONE_ENTRANCE','School Entrance','adl_01'),('CAM_HALL','ZONE_SCHOOL_HALL','School Hall','adl_02')]:
    row=dict(camera_id=cid,zone_id=zone,camera_name=name,scenario_id=scenario)
    if cid=='CAM_CORRIDOR_A':row['fight_model']='v2'
    configured.append(row)
config=OUT/'camera-baselines.json';config.write_text(json.dumps(configured))
ENV['SAFESENSE_CAMERA_REGISTRY']=str(config);ENV['SAFESENSE_FIGHT_BASELINE']='v3'

try:
    start('backend',[sys.executable,'-m','uvicorn','backend.main:app','--host','127.0.0.1','--port','18000'],B+'/health')
    start('inference',[sys.executable,'-m','uvicorn','fight_api:app','--host','127.0.0.1','--port','18001'],A+'/health')
    start('frontend',['node',str(ROOT/'dashboard/node_modules/vite/bin/vite.js'),'--host','127.0.0.1','--port','3001','--strictPort'],'http://127.0.0.1:3001',ROOT/'dashboard')
    from playwright.sync_api import sync_playwright,expect as browser_expect
    import hashlib,re
    cameras=expect(client.get(B+'/monitoring/cameras'));actual={};summaries=[]
    with sync_playwright() as pw:
        browser=pw.chromium.launch(headless=True);page=browser.new_page(viewport={'width':1500,'height':1050});page.set_default_timeout(20000)
        errors=[];posts=[];completed={}
        page.on('pageerror',lambda e:errors.append(str(e)))
        page.on('request',lambda r:posts.append(r.post_data_json) if r.url.endswith('/monitoring/jobs') and r.method=='POST' else None)
        def response(r):
            if r.url.endswith('/monitoring/jobs') and r.status==202 or '/monitoring/jobs/' in r.url and r.status==200:
                data=r.json()
                if data.get('status')=='COMPLETED':completed[data['camera_id']]=data
        page.on('response',response)
        page.goto('http://127.0.0.1:3001');page.locator('aside').get_by_role('button',name='Live Monitoring',exact=True).click();panel=page.get_by_test_id('camera-monitoring')
        def choose(c):panel.get_by_role('button',name=c['camera_name']+' '+c['camera_id']+' '+c['source_type'],exact=True).click()
        def done(c):
            page.wait_for_function("id=>{const p=document.querySelector('[data-testid=camera-monitoring]');return p?.querySelector('video')?.dataset.cameraId===id&&p.innerText.includes('COMPLETED')}",arg=c['camera_id'],timeout=240000)
            return completed[c['camera_id']]
        for camera in cameras:
            def automatic(camera=camera):
                before=expect(client.get(B+'/incidents'));initial=len(posts);choose(camera)
                browser_expect(panel.locator('select')).to_have_count(0)
                browser_expect(panel.get_by_role('button',name=re.compile('Analyze'))).to_have_count(0)
                page.wait_for_function("id=>{const v=document.querySelector('[data-testid=camera-monitoring] video');return v?.dataset.cameraId===id&&v.readyState>=2&&!v.paused&&v.currentTime>.1}",arg=camera['camera_id'])
                row=done(camera);r=row['result'];actual[camera['camera_id']]=row
                assert len(posts)==initial+1 and posts[-1]['model']=='all',posts[initial:]
                assert row['resolved_models']==[camera['fight_model'],'pose']
                models=r['model_results'];assert len(models)==2 and not r['model_errors'],r.get('model_errors')
                fight,pose=models
                assert fight['model_version']==camera['fight_model']
                assert pose['model_version']=='yolo11n-pose-temporal-rule-v1'
                assert fight['sampled_frames']==48
                digest=hashlib.sha256((ROOT/camera['scenario']['path']).read_bytes()).hexdigest()
                assert all(m['input_sha256']==digest for m in models)
                assert r['analysis_run_id']==row['id'] and all(m['analysis_run_id']==row['id'] for m in models)
                assert r['events']==pose['events']
                assert not fight.get('events') and not fight.get('pose_frames')
                browser_expect(panel.get_by_test_id('analysis-origin')).to_contain_text('Fresh inference')
                browser_expect(panel.locator('video').first).to_have_attribute('src',re.compile('/ai/fall/artifacts/'))
                assert pose['pose_frames'] and any(f['persons'] for f in pose['pose_frames'])
                for output in models:
                    incident=output['event_delivery']['incident_id']
                    if output['candidate_detected']:
                        assert incident
                        report=expect(client.get(B+'/incidents/'+incident+'/report'));assert report['analysis_run_id']==row['id']
                        zone=next(z for z in expect(client.get(B+'/zones')) if z['id']==camera['zone_id']);assert incident in zone['active_incident_ids']
                        for media in output['evidence_media']:
                            meta=expect(client.get(A+'/monitoring/incidents/'+incident+'/evidence/'+media['id']+'/metadata'))
                            assert meta['incident_id']==incident and meta['camera_id']==camera['camera_id']
                            assert client.get(A+media['url'],headers={'Range':'bytes=0-511'}).status_code==206
                    else:assert incident is None
                if not r['candidate_detected']:
                    assert expect(client.get(B+'/incidents'))==before
                    browser_expect(panel.get_by_test_id('monitoring-outcome')).to_contain_text('Normal monitoring')
                else:browser_expect(panel.get_by_test_id('monitoring-outcome')).to_contain_text('Candidate detected')
                if camera['camera_id']=='CAM_CORRIDOR_A':assert fight['candidate_detected'] and abs(fight['score']-.9745275974273682)<1e-6
                if camera['camera_id']=='CAM_CANTEEN':assert not r['candidate_detected'] and abs(fight['score']-.09235220402479172)<1e-6
                if camera['camera_id']=='CAM_STAIRCASE':assert pose['candidate_detected'] and pose['events'][0]['time_sec']==2.1
                page.screenshot(path=str(OUT/(camera['camera_id']+'.png')),full_page=True)
                summary={'camera':camera['camera_id'],'fight_model':fight['model_version'],'fight_score':fight['score'],'fight_candidate':fight['candidate_detected'],'fall_candidate':pose['candidate_detected'],'fall_events':pose['events'],'latency':r['total_processing_sec'],'single_fight_forward':True,'automatic_post_requests':1,'source_sha256':digest}
                summaries.append(summary);(OUT/'actual-model-results.json').write_text(json.dumps(summaries,indent=2));return summary
            check('Automatic actual Fight + Fall: '+camera['camera_id'],automatic)
        def cache():
            c=cameras[0];before=expect(client.get(B+'/incidents'));choose(c);row=done(c)
            assert row['cache_hit'] and row['id']==actual[c['camera_id']]['id']
            browser_expect(panel.get_by_test_id('analysis-origin')).to_contain_text('Cached / reused')
            assert expect(client.get(B+'/incidents'))==before
            return {'same_job':row['id'],'cache_hit':True,'incident_records_unchanged':True}
        check('Automatic completed-result reuse and visible cached provenance',cache)
        def overlays():
            import cv2,numpy as np
            from ultralytics import YOLO
            row=actual['CAM_CORRIDOR_A'];r=row['result'];frame_data=r['pose_frames'][12]
            cap=cv2.VideoCapture(str(ROOT/cameras[0]['scenario']['path']));cap.set(cv2.CAP_PROP_POS_FRAMES,12);ok,frame=cap.read();cap.release();assert ok
            prediction=YOLO(str(ROOT/'yolo11n-pose.pt')).predict(frame,device='cpu',conf=.25,imgsz=640,verbose=False)[0]
            assert len(prediction.boxes)==len(frame_data['persons'])
            for person,box,points in zip(frame_data['persons'],prediction.boxes.xyxy.cpu().tolist(),prediction.keypoints.xy.cpu().tolist()):
                assert np.allclose(person['bbox_xyxy'],box,atol=.001)
                assert np.allclose([[p['x'],p['y']] for p in person['keypoints']],points,atol=.001)
            video=panel.locator('video').first;video.evaluate('(v)=>{v.pause();v.currentTime=2.3}')
            page.wait_for_function("()=>Math.abs(Number(document.querySelector('[data-testid=frame-detections]').dataset.frameIndex)-69)<=1")
            return {'independent_source_frame':12,'actual_persons':len(frame_data['persons']),'seek_seconds':2.3,'displayed_frame':panel.get_by_test_id('frame-detections').get_attribute('data-frame-index'),'no_fighter_localization':True}
        check('Independent real YOLO boxes/keypoints and synchronized playback',overlays)
        def incident_ui():
            row=actual['CAM_CORRIDOR_A'];identifier=row['result']['event_delivery']['incident_id']
            panel.get_by_role('button',name='Review camera incident and evidence',exact=True).click()
            evidence=page.get_by_test_id('incident-evidence');browser_expect(evidence).to_have_attribute('data-incident-id',identifier)
            browser_expect(evidence.locator('video').first).to_be_visible()
            page.get_by_role('button',name='Close',exact=True).click()
            for destination in ['Alerts','Incident Review']:
                page.locator('aside').get_by_role('button',name=destination,exact=True).click()
                browser_expect(page.locator('main').get_by_text(identifier[:8],exact=False).first).to_be_visible()
            page.locator('aside').get_by_role('button',name='Digital Twin Map',exact=True).click()
            browser_expect(page.locator('[data-zone-id="ZONE_CORRIDOR_A"]')).to_have_attribute('data-risk-level','OBSERVE')
            page.locator('aside').get_by_role('button',name='Live Monitoring',exact=True).click()
            return {'incident':identifier,'captured_evidence_visible':True,'Alerts_Incident_Review_Digital_Twin_synchronized':True}
        check('Automatic candidate evidence and existing incident/map synchronization',incident_ui)
        def rapid():
            initial=len(posts)
            for c in [cameras[3],cameras[4],cameras[0],cameras[3],cameras[4]]:
                choose(c);page.wait_for_timeout(80)
            row=done(cameras[4]);assert row.get('cache_hit') or row.get('deduplicated')
            assert len(posts)-initial<=2,len(posts)-initial
            assert not errors,errors
            page.set_viewport_size({'width':390,'height':844});assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
            page.screenshot(path=str(OUT/'automatic-mobile.png'),full_page=True)
            return {'final_camera':'CAM_HALL','burst_submissions':len(posts)-initial,'browser_errors':errors,'responsive':True}
        check('Rapid automatic selection uses debounce/cache without flooding or crashes',rapid)
        browser.close()
finally:
    for process,log in reversed(processes):
        if process.poll() is None:
            process.terminate()
            try:process.wait(timeout=10)
            except subprocess.TimeoutExpired:process.kill()
        log.close()
    client.close()
print(json.dumps({'passed':sum(r['status']=='PASS' for r in RESULTS),'failed':sum(r['status']=='FAIL' for r in RESULTS)}),flush=True)
sys.exit(any(r['status']=='FAIL' for r in RESULTS))
