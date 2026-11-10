"""Actual isolated HTTP + browser workflow. Never sends Telegram or touches existing services."""
from pathlib import Path
import json,os,subprocess,sys,time,traceback,shutil
import httpx

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
sys.stdout.reconfigure(encoding='utf-8')
OUT=ROOT/'runtime/detection-task3'
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
try:
    start('backend',[sys.executable,'-m','uvicorn','backend.main:app','--host','127.0.0.1','--port','18000'],B+'/health')
    start('inference',[sys.executable,'-m','uvicorn','fight_api:app','--host','127.0.0.1','--port','18001'],A+'/health')
    def api_models():
        import hashlib
        from backend.registry import source
        r=camera_job('conflict','CAM_CORRIDOR_A','ZONE_CORRIDOR_A')['result'];saved['conflict']=r
        assert len(r['model_results'])==2 and not r['model_errors'],r
        _,path=source('conflict');digest=hashlib.sha256(path.read_bytes()).hexdigest()
        assert all(m['input_sha256']==digest for m in r['model_results'])
        assert r['camera_id']=='CAM_CORRIDOR_A' and r['zone_id']=='ZONE_CORRIDOR_A'
        pose=r['model_results'][1];frames=pose['pose_frames'];alignment=pose['annotation_alignment']
        assert len(frames)==alignment['frame_count']==pose['processed_frames']
        assert r['pose_frames']==frames and not r['tracking_available']
        assert any(f['persons'] for f in frames)
        for index,frame in enumerate(frames):
            assert frame['frame_index']==index and abs(frame['time_sec']-index/alignment['fps'])<1e-6
            for person in frame['persons']:
                assert len(person['bbox_xyxy'])==4 and len(person['keypoints'])==17
                assert 0<=person['confidence']<=1 and 'track_id' not in person
        for m in r['model_results'][:1]:
            assert m['threshold']==({'v2':.4,'v3':.7}[m['model_version']]) and 0<=m['score']<=1
            assert not m.get('events') and not m.get('pose_frames')
        return {'sha256':digest,'models':[{'model':m['model_version'],'score':m.get('score'),'latency':m['inference_time_sec']} for m in r['model_results']],'frames':len(frames),'tracking':False}
    check('API: all mode resolves configured fight baseline and actual pose metadata',api_models)
    def independent_pose():
        import cv2,numpy as np
        from ultralytics import YOLO
        from backend.registry import source
        _,path=source('conflict');cap=cv2.VideoCapture(str(path));cap.set(cv2.CAP_PROP_POS_FRAMES,12);ok,frame=cap.read();cap.release();assert ok
        assert (ROOT/'yolo11n-pose.pt').is_file(), 'Use the existing local model; never download a replacement'
        prediction=YOLO(str(ROOT/'yolo11n-pose.pt')).predict(frame,device='cpu',conf=.25,imgsz=640,verbose=False)[0]
        actual=saved['conflict']['pose_frames'][12]['persons']
        assert len(actual)==len(prediction.boxes)
        for person,bounds,confidence,points in zip(actual,prediction.boxes.xyxy.cpu().tolist(),prediction.boxes.conf.cpu().tolist(),prediction.keypoints.xy.cpu().tolist()):
            assert np.allclose(person['bbox_xyxy'],bounds,atol=.001)
            assert abs(person['confidence']-confidence)<1e-6
            assert np.allclose([[p['x'],p['y']] for p in person['keypoints']],points,atol=.001)
        response=client.get(A+saved['conflict']['annotated_video_url']);assert response.status_code==200
        output=OUT/'actual-annotated.mp4';output.write_bytes(response.content)
        cap=cv2.VideoCapture(str(output));count=int(cap.get(cv2.CAP_PROP_FRAME_COUNT));fps=cap.get(cv2.CAP_PROP_FPS);cap.release()
        assert count==len(saved['conflict']['pose_frames']) and abs(fps-saved['conflict']['annotation_alignment']['fps'])<.01
        return {'independent_frame':12,'real_persons':len(actual),'annotation_frames':count,'annotation_fps':fps}
    check('Independent YOLO frame matches API boxes, keypoints and confidence; encoded timing matches',independent_pose)
    def privacy():
        expect(client.post(A+'/monitoring/jobs',json={'scenario_id':'fall','camera_id':'CAM_STAIRCASE','zone_id':'ZONE_TOILET_BLINDSPOT','model':'all','authorized':True}),403)
        expect(httpx.get(A+saved['conflict']['annotated_video_url']),401)
        response=client.get(A+saved['conflict']['annotated_video_url'],headers={'Range':'bytes=0-1023'});assert response.status_code==206
        return 'Private inference rejected; annotation authenticated and seekable'
    check('API privacy and annotation byte-range access',privacy)
    # Expire only the annotation created above by this isolated test. The next
    # camera click must refresh that invalid cache entry and exercise fresh handoff.
    annotation_id=saved['conflict']['annotated_video_url'].rsplit('/',1)[-1]
    __import__('uuid').UUID(annotation_id)
    annotation=(ROOT/'runtime/annotations'/(annotation_id+'.mp4')).resolve()
    assert annotation.parent==(ROOT/'runtime/annotations').resolve()
    annotation.unlink()
    start('frontend',[shutil.which('node'),str(ROOT/'dashboard/node_modules/vite/bin/vite.js'),'--host','127.0.0.1','--port','3001','--strictPort'],'http://127.0.0.1:3001',ROOT/'dashboard')
    from playwright.sync_api import sync_playwright,expect as browser_expect
    with sync_playwright() as pw:
        browser=pw.chromium.launch(headless=True)
        page=browser.new_page(viewport={'width':1500,'height':1050});page.set_default_timeout(20000)
        errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
        completed=[]
        def response(r):
            if ('/monitoring/jobs/' in r.url and r.status==200) or (r.url.endswith('/monitoring/jobs') and r.status==202):
                data=r.json()
                if data['status']=='COMPLETED':completed.append(data)
        page.on('response',response)
        page.goto('http://127.0.0.1:3001',wait_until='domcontentloaded');page.locator('aside').get_by_role('button',name='Live Monitoring',exact=True).click()
        panel=page.get_by_test_id('camera-monitoring');video=panel.locator('video').first
        def handoff():
            panel.get_by_role('button',name='Corridor A CAM_CORRIDOR_A RECORDED REAL VIDEO',exact=True).click()
            # Legacy all-model API output is a different execution policy. The camera
            # automatically starts the configured baseline plus pose, without controls.
            browser_expect(panel.get_by_label('Camera analysis model',exact=True)).to_have_count(0)
            browser_expect(panel.get_by_role('button',name='Analyze recording again',exact=True)).to_have_count(0)
            page.wait_for_function("()=>{const v=document.querySelector('[data-testid=camera-monitoring] video');return v?.readyState>=2 && !v.paused && v.currentTime>0.1}")
            assert '/monitoring/sources/conflict?' in video.get_attribute('src')
            t1=video.evaluate('(v)=>v.currentTime');page.wait_for_timeout(300);assert video.evaluate('(v)=>v.currentTime')>t1
            video.evaluate('(v)=>{v.pause();v.currentTime=1.2;v.playbackRate=1.5}')
            browser_expect(video).to_have_attribute('src',__import__('re').compile('/ai/fall/artifacts/'),timeout=180000)
            page.wait_for_function("()=>{let v=document.querySelector('[data-testid=camera-monitoring] video');return v.readyState>=2 && Math.abs(v.currentTime-1.2)<0.04}")
            assert video.evaluate('(v)=>v.paused') and video.evaluate('(v)=>v.playbackRate')==1.5
            browser_expect(panel.get_by_role('heading',name='Detection Results',exact=True)).to_be_visible()
            for name in ('v3','yolo11n-pose-temporal-rule-v1'):browser_expect(panel.get_by_text(name,exact=True)).to_be_visible()
            assert len(completed[-1]['result']['model_results'])==2
            assert completed and not completed[-1]['result']['model_errors']
            assert str(round(completed[-1]['result']['model_results'][0]['score'],6)) in panel.inner_text()
            page.screenshot(path=str(OUT/'compact-detection-desktop.png'),full_page=True)
            return {'paused_preserved':True,'time':video.evaluate('(v)=>v.currentTime'),'rate':video.evaluate('(v)=>v.playbackRate'),'playback_advanced_while_cpu_running':True}
        check('Browser: autoplay during real CPU inference, compact scores, paused handoff preserves position',handoff)
        def seek_alignment():
            r=completed[-1]['result'];fps=r['annotation_alignment']['fps'];observed=[]
            for target in (.6,2.3,4.1):
                video.evaluate('(v,t)=>{v.pause();v.currentTime=t}',target)
                page.wait_for_function("({target,fps})=>{let v=document.querySelector('[data-testid=camera-monitoring] video');let f=document.querySelector('[data-testid=frame-detections]');return Math.abs(v.currentTime-target)<.01 && Math.abs(Number(f.dataset.frameIndex)-Math.floor(target*fps))<=1}",arg={'target':target,'fps':fps})
                index=int(panel.get_by_test_id('frame-detections').get_attribute('data-frame-index'));expected=r['pose_frames'][index]
                text=panel.get_by_test_id('frame-detections').inner_text()
                assert f"{len(expected['persons'])} person detections" in text
                for person in expected['persons']:assert f"{person['confidence']:.3f}" in text
                observed.append({'seek':target,'displayed_frame':index,'expected_frame':int(target*fps)})
            panel.get_by_role('button',name='Replay',exact=True).click();page.wait_for_function("()=>{let v=document.querySelector('[data-testid=camera-monitoring] video');return !v.paused && v.currentTime>.1 && v.currentTime<1}")
            video.evaluate('(v)=>v.pause()')
            return {'seek_samples':observed,'replay':True,'tolerance':'one decoded frame; video overlays are baked into matching frames'}
        check('Browser: seek, pause, replay and actual frame metadata stay aligned',seek_alignment)
        def evidence():
            panel.get_by_role('button',name='Preview v3 evidence',exact=True).click()
            preview=panel.locator('aside video');browser_expect(preview).to_be_visible();preview.evaluate('(v)=>v.play()')
            page.wait_for_function("()=>{let v=document.querySelector('[aria-label=\"Detection Results\"] video');return v.readyState>=2 && !v.paused && v.currentTime>0}")
            url=panel.get_by_role('link',name='Open captured clip',exact=True).first.get_attribute('href')
            assert client.get(url,headers={'Range':'bytes=0-1023'}).status_code==206
            panel.get_by_role('button',name='Close preview',exact=True).click()
            return 'Actual retained V3 clip decodes/plays; authenticated evidence link supports seeking'
        check('Browser: captured evidence preview and actual clip links',evidence)
        def timeline_switch():
            panel.get_by_role('button',name='Staircase CAM_STAIRCASE RECORDED REAL VIDEO',exact=True).click()
            browser_expect(video).to_have_attribute('data-camera-id','CAM_STAIRCASE')
            assert 'confidence' not in panel.get_by_test_id('frame-detections').inner_text()
            assert '0.999' not in panel.locator('[data-model=v3]').inner_text()
            browser_expect(video).to_have_attribute('src',__import__('re').compile('/ai/fall/artifacts/'),timeout=180000)
            timeline=panel.get_by_label('Detection timeline',exact=True)
            browser_expect(timeline.get_by_role('button').first).to_be_visible()
            event=completed[-1]['result']['events'][0]
            video.evaluate('(v)=>v.pause()');timeline.get_by_role('button').first.click()
            page.wait_for_function("t=>Math.abs(document.querySelector('[data-testid=camera-monitoring] video').currentTime-t)<.04",arg=event['time_sec'])
            page.screenshot(path=str(OUT/'pose-timeline.png'),full_page=True)
            return {'camera':'CAM_STAIRCASE','actual_pose_event':event,'no_fight_timestamps':True}
        check('Browser: camera change clears old outputs; actual pose marker seeks correct video',timeline_switch)
        def mobile_tools():
            page.set_viewport_size({'width':390,'height':844})
            page.wait_for_timeout(150)
            assert page.evaluate('document.documentElement.scrollWidth<=window.innerWidth+1')
            browser_expect(page.get_by_role('heading',name='Scenario Testing Library',exact=True)).to_have_count(0)
            browser_expect(page.get_by_test_id('additional-monitoring-tools')).to_have_count(0)
            browser_expect(page.get_by_label('Video upload',exact=True)).to_have_count(0)
            page.evaluate("window.location.hash='/developer/testing'")
            browser_expect(page.get_by_role('heading',name='Scenario Testing Library',exact=True)).to_be_visible()
            browser_expect(page.get_by_label('Video upload',exact=True)).to_be_visible();browser_expect(page.get_by_role('button',name='Trigger test SOS',exact=True)).to_be_visible()
            assert page.get_by_text('Simulated mmWave Coordinate Plane',exact=True).count()==0
            page.screenshot(path=str(OUT/'responsive-tools.png'),full_page=True)
            assert not errors,errors
            return {'width':390,'no_horizontal_overflow':True,'upload_and_SOS_tools_preserved':True,'scenario_library_preserved':True,'browser_errors':errors}
        check('Browser: responsive layout, retained scenario/upload/SOS tools, no fake diagrams',mobile_tools)
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
