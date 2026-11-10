"""Actual isolated HTTP + browser workflow. Never sends Telegram or touches existing services."""
from pathlib import Path
import json,os,subprocess,sys,time,traceback,shutil
import httpx

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
sys.stdout.reconfigure(encoding='utf-8')
OUT=ROOT/'runtime/live-ai-final'
OUT.mkdir(parents=True,exist_ok=True)
RESULTS=[]
ENV=os.environ.copy()
ENV.update(SAFESENSE_DB_PATH=str(OUT/('test-'+str(int(time.time()))+'.sqlite3')),
           SAFESENSE_BACKEND_URL='http://127.0.0.1:18000',TELEGRAM_MODE='disabled',
           SAFESENSE_AI_URL='http://127.0.0.1:18001',
           VITE_API_BASE_URL='http://127.0.0.1:18000',VITE_AI_BASE_URL='http://127.0.0.1:18001',SAFESENSE_DASHBOARD_URL='http://127.0.0.1:3001',
           SAFESENSE_API_TOKEN='monitoring-integration-test',VITE_SAFESENSE_API_TOKEN='monitoring-integration-test')
ENV.update(SAFESENSE_EVIDENCE_DIR=str(OUT/'evidence'),SAFESENSE_ANNOTATION_DIR=str(OUT/'annotations'),SAFESENSE_ANALYSIS_CACHE_DIR=str(OUT/'cache'),SAFESENSE_PRECOMPUTE_ON_START='false')
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

ENV['SAFESENSE_DB_PATH']=str(max((ROOT/'runtime/live-ai-final').glob('test-*.sqlite3'),key=lambda p:p.stat().st_mtime))
OUT=ROOT/'runtime/live-ai-final/restarted';OUT.mkdir(parents=True,exist_ok=True)
try:
    start('backend',[sys.executable,'-m','uvicorn','backend.main:app','--host','127.0.0.1','--port','18000'],B+'/health')
    service=start('inference',[sys.executable,'-m','uvicorn','fight_api:app','--host','127.0.0.1','--port','18001'],A+'/health')
    before=expect(client.get(B+'/state'));measurements=[]
    def disk_replay():
        for camera in expect(client.get(B+'/monitoring/cameras')):
            started=time.perf_counter()
            row=expect(client.post(A+'/monitoring/jobs',json={'scenario_id':camera['scenario_id'],'camera_id':camera['camera_id'],'zone_id':camera['zone_id'],'model':'all','authorized':True}),202)
            assert row['status']=='COMPLETED' and row.get('cache_hit') and row.get('cache_tier')=='disk',row.keys()
            assert row['result']['pose_frames'] and row['result']['camera_id']==camera['camera_id']
            measurements.append({'camera':camera['camera_id'],'cache_tier':row['cache_tier'],'api_response_ms':round((time.perf_counter()-started)*1000,2),'pose_frames':len(row['result']['pose_frames'])})
        after=expect(client.get(B+'/state'))
        assert len(before['events'])==len(after['events']) and len(before['incidents'])==len(after['incidents'])
        (OUT/'performance.json').write_text(json.dumps(measurements,indent=2),encoding='utf-8')
        return {'cameras':measurements,'new_events':0,'new_incidents':0}
    check('Five genuine caches survive service restart without inference or duplicate incidents',disk_replay)
    start('frontend',[shutil.which('node'),str(ROOT/'dashboard/node_modules/vite/bin/vite.js'),'--host','127.0.0.1','--port','3001','--strictPort'],'http://127.0.0.1:3001',ROOT/'dashboard')
    from playwright.sync_api import sync_playwright,expect as be
    with sync_playwright() as pw:
        browser=pw.chromium.launch(headless=True);page=browser.new_page(viewport={'width':1500,'height':1050})
        page.goto('http://127.0.0.1:3001');page.locator('aside').get_by_role('button',name='Live Monitoring',exact=True).click()
        panel=page.get_by_test_id('camera-monitoring');video=panel.locator('video').first
        def reselect():
            jobs=[]
            def response(r):
                if r.request.method=='POST' and r.url.endswith('/monitoring/jobs') and r.status==202:jobs.append(r.json()['id'])
            page.on('response',response)
            button=panel.get_by_role('button',name='School Entrance CAM_ENTRANCE RECORDED REAL VIDEO',exact=True)
            button.click();be(panel.get_by_test_id('fight-video-overlay')).to_be_visible(timeout=20000)
            video.evaluate('v=>v.pause()');button.click()
            page.wait_for_function("()=>{const v=document.querySelector('[data-testid=camera-monitoring] video');return !v.paused&&v.currentTime>.1}")
            be(panel.get_by_test_id('fight-video-overlay')).to_be_visible()
            page.wait_for_timeout(200)
            assert len(jobs)==2 and len(set(jobs))==1,jobs
            return {'paused':video.evaluate('v=>v.paused'),'accepted_requests':len(jobs),'unique_jobs':len(set(jobs))}
        check('Confirmed same-camera autoplay bug fixed and cached job reused',reselect)
        def timeline():
            panel.get_by_role('button',name='Staircase CAM_STAIRCASE RECORDED REAL VIDEO',exact=True).click()
            be(panel.get_by_test_id('fight-video-overlay')).to_be_visible()
            timeline=panel.get_by_label('Detection timeline',exact=True)
            timeline.get_by_role('button').first.click()
            page.wait_for_function("()=>{const v=document.querySelector('[data-testid=camera-monitoring] video');return v.readyState>=2&&!v.seeking&&Math.abs(v.currentTime-2.1)<.02}")
            be(panel.locator('[data-fall-candidate=true]')).to_be_visible()
            assert panel.locator('[data-fall-candidate=true] [data-testid=person-box]').get_attribute('stroke')=='#ef4444'
            video.evaluate('v=>v.pause()');video.screenshot(path=str(OUT/'timeline-video.png'))
            page.screenshot(path=str(OUT/'timeline-fall.png'),full_page=True)
            return {'source_time':video.evaluate('v=>v.currentTime'),'rule':'binary ACTIVE','red_box':True}
        check('Actual timeline marker seeks genuine supported fall frame',timeline)
        def feature_evidence():
            page.locator('aside').get_by_role('button',name='Alerts',exact=True).click()
            inspect=page.get_by_title('Inspect Full Incident Review Dossier').first
            be(inspect).to_be_visible();inspect.click()
            be(page.get_by_test_id('incident-evidence')).to_be_visible()
            page.get_by_role('button',name='Close',exact=True).click()
            page.locator('aside').get_by_role('button',name='Digital Twin Map',exact=True).click()
            page.locator('[data-zone-id="ZONE_TOILET_BLINDSPOT"] polygon').first.click()
            scene=page.get_by_test_id('private-twin-scene');canvas=scene.locator('canvas');be(canvas).to_be_visible()
            canvas.scroll_into_view_if_needed();canvas.screenshot(path=str(OUT/'private-3d-canvas.png'));scene.screenshot(path=str(OUT/'private-3d-scene.png'))
            assert page.get_by_test_id('private-monitoring-view').locator('video,img,audio').count()==0
            return {'alerts_details_opens':True,'private_scene_screenshot':'private-3d-scene.png','private_video_elements':0}
        check('Alerts opens actual evidence and private 3D renders without CCTV',feature_evidence)
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
