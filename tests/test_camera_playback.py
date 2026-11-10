"""Actual isolated HTTP + browser workflow. Never sends Telegram or touches existing services."""
from pathlib import Path
import json,os,subprocess,sys,time,traceback,shutil
import httpx

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
sys.stdout.reconfigure(encoding='utf-8')
OUT=ROOT/'runtime/camera-playback-task2'
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

try:
    start('backend',[sys.executable,'-m','uvicorn','backend.main:app','--host','127.0.0.1','--port','18000'],B+'/health')
    start('inference',[sys.executable,'-m','uvicorn','fight_api:app','--host','127.0.0.1','--port','18001'],A+'/health')
    start('frontend',['node',str(ROOT/'dashboard/node_modules/vite/bin/vite.js'),'--host','127.0.0.1','--port','3001'],'http://127.0.0.1:3001',ROOT/'dashboard')
    from playwright.sync_api import sync_playwright,expect as browser_expect
    cameras=expect(client.get(B+'/monitoring/cameras'))
    with sync_playwright() as pw:
        browser=pw.chromium.launch(headless=True)
        page=browser.new_page(viewport={'width':1500,'height':1050})
        requests=[];page.on('request',lambda r:requests.append(r.url))
        errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
        page.goto('http://127.0.0.1:3001',wait_until='domcontentloaded')
        page.locator('aside').get_by_role('button',name='Live Monitoring',exact=True).click()
        panel=page.get_by_test_id('camera-monitoring')
        for camera in cameras:
            def playback(camera=camera):
                assert camera['available'],camera
                panel.get_by_role('button',name=camera['camera_name']+' '+camera['camera_id']+' '+camera['source_type'],exact=True).click()
                page.wait_for_function("id=>{const v=document.querySelector('[data-testid=camera-monitoring] video');return v?.dataset.cameraId===id && v.readyState>=2 && !v.paused && v.currentTime>0.15}",arg=camera['camera_id'],timeout=20000)
                v=panel.locator('video')
                raw=v.evaluate('(v)=>({src:v.currentSrc,time:v.currentTime,duration:v.duration,width:v.videoWidth,height:v.videoHeight,muted:v.muted,controls:v.controls})')
                assert any('/monitoring/sources/'+camera['scenario']['id']+'?' in url for url in requests),raw
                assert '/monitoring/sources/'+camera['scenario']['id']+'?' in raw['src'] or '/ai/fall/artifacts/' in raw['src'],raw
                assert raw['muted'] and raw['controls'] and raw['width']>0
                # Wait for actual existing models, not simulated job results.
                page.wait_for_function("()=>document.querySelector('[data-testid=camera-monitoring]').innerText.includes('COMPLETED')",timeout=240000)
                page.wait_for_function("()=>{let v=document.querySelector('[data-testid=camera-monitoring] video');return v.readyState>=2 && !v.paused && v.currentTime>0.15}",timeout=20000)
                v.evaluate('(v)=>v.pause()');assert v.evaluate('(v)=>v.paused')
                seek=min(1,raw['duration']/2);v.evaluate('(v,t)=>v.currentTime=t',seek)
                page.wait_for_function("t=>Math.abs(document.querySelector('[data-testid=camera-monitoring] video').currentTime-t)<0.2",arg=seek)
                panel.get_by_role('button',name='Replay',exact=True).click()
                page.wait_for_function("()=>{let v=document.querySelector('[data-testid=camera-monitoring] video');return !v.paused && v.currentTime<1}")
                assert 'Demo zone assignment; not footage from this school.' in panel.inner_text()
                page.screenshot(path=str(OUT/(camera['camera_id']+'.png')),full_page=True)
                return {'camera':camera['camera_id'],'file':camera['scenario']['path'],'raw_playback':raw,'real_models_completed':True,'pause_seek_replay':True}
            check('Actual browser playback '+camera['camera_id'],playback)
        def switching():
            for camera in cameras:
                panel.get_by_role('button',name=camera['camera_name']+' '+camera['camera_id']+' '+camera['source_type'],exact=True).click()
                browser_expect(panel.locator('video')).to_have_attribute('data-camera-id',camera['camera_id'])
                assert '/monitoring/sources/'+camera['scenario']['id']+'?' in panel.locator('video').get_attribute('src')
                assert 'Candidate requires human review' not in panel.inner_text()
            return 'All five rapid switches immediately select correct real source and clear old results; CPU queue may report busy honestly.'
        check('Rapid camera switching',switching)
        check('No JavaScript errors',lambda: errors if not errors else (_ for _ in ()).throw(AssertionError(errors)))
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
