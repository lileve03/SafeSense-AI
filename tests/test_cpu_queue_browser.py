"""Actual isolated HTTP + browser workflow. Never sends Telegram or touches existing services."""
from pathlib import Path
import json,os,subprocess,sys,time,traceback,shutil
import httpx

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
sys.stdout.reconfigure(encoding='utf-8')
OUT=ROOT/'runtime/cpu-queue-fix'
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

def submit(camera,model='all',**extra):
    return client.post(A+'/monitoring/jobs',json={'scenario_id':camera['scenario_id'],'camera_id':camera['camera_id'],'zone_id':camera['zone_id'],'model':model,'authorized':True,**extra})
def wait_job(identifier):
    for _ in range(480):
        row=expect(client.get(A+'/monitoring/jobs/'+identifier))
        if row['status']=='COMPLETED':return row
        assert row['status'] in ('QUEUED','RUNNING'),row
        time.sleep(.3)
    raise AssertionError('Job timeout')
def running(identifier):
    for _ in range(100):
        row=expect(client.get(A+'/monitoring/jobs/'+identifier))
        if row['status']=='RUNNING':return
        time.sleep(.05)
    raise AssertionError('Running job not observed')
try:
    start('backend',[sys.executable,'-m','uvicorn','backend.main:app','--host','127.0.0.1','--port','18000'],B+'/health')
    inference=start('inference',[sys.executable,'-m','uvicorn','fight_api:app','--host','127.0.0.1','--port','18001'],A+'/health')
    start('frontend',['node',str(ROOT/'dashboard/node_modules/vite/bin/vite.js'),'--host','127.0.0.1','--port','3001','--strictPort'],'http://127.0.0.1:3001',ROOT/'dashboard')
    cameras=expect(client.get(B+'/monitoring/cameras'));corridor,canteen,stairs,entrance,hall=cameras;protected=[]
    def saturation():
        first=expect(submit(corridor),202);protected.append(first);running(first['id'])
        protected.append(expect(submit(canteen),202));protected.append(expect(submit(stairs,'pose'),202))
        duplicate=expect(submit(corridor),202);assert duplicate['id']==first['id'] and duplicate['deduplicated']
        rejected=submit(entrance,client_id='saturated-panel',selection_seq=1)
        assert rejected.status_code==429 and rejected.headers['Retry-After']=='2',rejected.text
        assert rejected.json()['detail']['code']=='CPU_BUSY'
        return {'capacity':'one running, two waiting','duplicate_id':duplicate['id'],'retry_after':rejected.headers['Retry-After'],'response':rejected.json()}
    check('Real API saturation and active duplicate coalescing',saturation)
    from playwright.sync_api import sync_playwright,expect as browser_expect
    with sync_playwright() as pw:
        browser=pw.chromium.launch(headless=True);page=browser.new_page(viewport={'width':1500,'height':1050});errors=[];requests=[]
        page.on('pageerror',lambda e:errors.append(str(e)))
        page.on('request',lambda r:requests.append({'time':time.monotonic(),'body':r.post_data_json}) if r.url.endswith('/monitoring/jobs') and r.method=='POST' else None)
        page.goto('http://127.0.0.1:3001');page.locator('aside').get_by_role('button',name='Live Monitoring',exact=True).click();panel=page.get_by_test_id('camera-monitoring')
        def choose(camera):panel.get_by_role('button',name=camera['camera_name']+' '+camera['camera_id']+' '+camera['source_type'],exact=True).click()
        def completed():page.wait_for_function("()=>document.querySelector('[data-testid=camera-monitoring]').innerText.includes('COMPLETED')",timeout=240000)
        def rapid():
            choose(entrance)
            browser_expect(panel.get_by_text('AI analysis queued - video playback is available.',exact=True)).to_be_visible()
            page.wait_for_function("()=>{const v=document.querySelector('[data-testid=camera-monitoring] video');return v?.readyState>=2&&!v.paused&&v.currentTime>.1}")
            for camera in [hall,entrance,corridor,hall,entrance,hall]:
                choose(camera);page.wait_for_timeout(230)
            browser_expect(panel.locator('video').first).to_have_attribute('data-camera-id','CAM_HALL')
            assert 'Bounded CPU queue full' not in panel.inner_text()
            completed();assert len(requests)<18,len(requests)
            page.screenshot(path=str(OUT/'rapid-switch-completed.png'),full_page=True)
            return {'final_camera':'CAM_HALL','autoplay_while_busy':True,'submit_requests':len(requests),'page_errors':errors}
        check('Browser rapid Entrance/Hall switching, immediate playback and bounded retry',rapid)
        def cache():
            original=wait_job(protected[0]['id']);before=expect(client.get(B+'/incidents'))
            cached=expect(submit(corridor),202)
            assert cached['id']==original['id'] and cached['cache_hit'],cached
            assert cached['result']['model_results'][0]['score']==original['result']['model_results'][0]['score']
            assert expect(client.get(B+'/incidents'))==before
            for row in protected:assert wait_job(row['id'])['status']=='COMPLETED'
            return {'cache_hit':True,'same_job':cached['id'],'incident_records_unchanged':True,'all_unrelated_jobs_completed':True}
        check('Completed actual-result cache preserves scores and avoids duplicate events',cache)
        def cancellation():
            first=expect(submit(corridor,force=True),202);running(first['id'])
            obsolete=expect(submit(entrance,client_id='selection-proof',selection_seq=1,force=True),202)
            newest=expect(submit(hall,client_id='selection-proof',selection_seq=2,force=True),202)
            assert expect(client.get(A+'/monitoring/jobs/'+obsolete['id']))['status']=='CANCELLED'
            assert expect(client.get(A+'/monitoring/jobs/'+first['id']))['status']=='RUNNING'
            stale=submit(entrance,client_id='selection-proof',selection_seq=1);assert stale.status_code==409
            duplicate=expect(submit(hall,client_id='selection-proof',selection_seq=2,force=True),202);assert duplicate['id']==newest['id']
            wait_job(first['id']);wait_job(newest['id'])
            retried=expect(submit(hall,client_id='selection-proof',selection_seq=2,force=True),202)
            assert retried['id']==newest['id'] and retried['deduplicated']
            return {'obsolete_job':obsolete['id'],'obsolete_status':'CANCELLED','running_preserved':True,'new_selection':newest['id'],'stale_request_http':409}
        check('Real API latest-selection priority, safe queued cancellation and stale request rejection',cancellation)
        def recovery():
            inference.terminate();inference.wait(timeout=20)
            choose(entrance)
            browser_expect(panel.get_by_text('AI analysis queued - video playback is available.',exact=True)).to_be_visible()
            page.wait_for_timeout(700)
            page.wait_for_function("()=>{const v=document.querySelector('[data-testid=camera-monitoring] video');return v?.readyState>=2&&!v.paused&&v.currentTime>.1}")
            start('inference-recovered',[sys.executable,'-m','uvicorn','fight_api:app','--host','127.0.0.1','--port','18001'],A+'/health')
            completed();assert not errors,errors
            page.screenshot(path=str(OUT/'service-recovered.png'),full_page=True)
            return {'actual_service_stop_restart':True,'video_played_during_outage':True,'automatic_retry_completed':True,'page_errors':errors}
        check('Actual inference service outage/restart recovers without blocking video',recovery)
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
