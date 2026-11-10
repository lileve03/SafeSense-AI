"""Actual isolated HTTP + browser workflow. Never sends Telegram or touches existing services."""
from pathlib import Path
import json,os,subprocess,sys,time,traceback,shutil
import httpx

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
sys.stdout.reconfigure(encoding='utf-8')
OUT=ROOT/'runtime/monitoring-cleanup'
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


import sqlite3,socket
for port in [18000,18001,3001]:
    try: connection=socket.create_connection(('127.0.0.1',port),timeout=.3)
    except OSError:continue
    else:connection.close();raise RuntimeError('Test port is already occupied: '+str(port))
with sqlite3.connect('file:'+str(ROOT/'runtime/safesense.sqlite3')+'?mode=ro',uri=True) as original,sqlite3.connect(ENV['SAFESENSE_DB_PATH']) as copied:original.backup(copied)

try:
    start('backend',[sys.executable,'-m','uvicorn','backend.main:app','--host','127.0.0.1','--port','18000'],B+'/health')
    start('inference',[sys.executable,'-m','uvicorn','fight_api:app','--host','127.0.0.1','--port','18001'],A+'/health')
    start('frontend',['node',str(ROOT/'dashboard/node_modules/vite/bin/vite.js'),'--host','127.0.0.1','--port','3001','--strictPort'],'http://127.0.0.1:3001',ROOT/'dashboard')
    from playwright.sync_api import sync_playwright,expect as browser_expect
    import hashlib
    with sync_playwright() as pw:
        browser=pw.chromium.launch(headless=True,args=['--enable-unsafe-swiftshader']);page=browser.new_page(viewport={'width':1500,'height':1050});page.set_default_timeout(20000)
        errors=[];requests=[];page.on('pageerror',lambda e:errors.append(str(e)));page.on('request',lambda r:requests.append(r.url))
        page.goto('http://127.0.0.1:3001');browser_expect(page.get_by_text('FastAPI Connected',exact=True)).to_be_visible()
        def nav(name):page.locator('aside').get_by_role('button',name=name,exact=True).click()
        def compact():
            requests.clear();nav('Live Monitoring');browser_expect(page.get_by_role('heading',name='Campus Camera Feeds',exact=True)).to_be_visible()
            main=page.locator('main');panel=page.get_by_test_id('camera-monitoring')
            for title in ['Scenario Testing Library','Public-area Video Analysis','Sensor Replay & SOS Demo']:
                browser_expect(main.get_by_role('heading',name=title,exact=True)).to_have_count(0)
            for selector in ['[data-testid=scenario-testing-library]','[data-testid=additional-monitoring-tools]','input[type=file]']:
                browser_expect(main.locator(selector)).to_have_count(0)
            assert 'Saved sensor predictions & controlled tests' not in main.inner_text()
            assert 'Upload & sensor tools' not in main.inner_text()
            wrapper=panel.locator('..');layout=wrapper.evaluate('(r)=>({children:r.children.length,last:r.lastElementChild.getAttribute("aria-label"),bottomGap:r.getBoundingClientRect().bottom-r.lastElementChild.getBoundingClientRect().bottom})')
            assert layout['children']==2 and layout['last']=='Recent Events' and abs(layout['bottomGap'])<1,layout
            assert not any(any(p in url for p in ['/testing/scenarios','/testing/runs','/sensors/replay','/monitoring/scenarios']) for url in requests),requests
            page.screenshot(path=str(OUT/'compact-main.png'),full_page=True)
            return {'only_camera_and_recent_events':True,'layout':layout,'testing_panels_and_requests_absent':True}
        check('Main Live Monitoring removes complete testing panels without blank wrappers',compact)
        def automatic():
            panel=page.get_by_test_id('camera-monitoring');panel.get_by_role('button',name='Canteen CAM_CANTEEN RECORDED REAL VIDEO',exact=True).click()
            page.wait_for_function("()=>{const v=document.querySelector('[data-testid=camera-monitoring] video');return v?.readyState>=2&&!v.paused&&v.currentTime>.1}")
            browser_expect(panel.get_by_test_id('monitoring-outcome')).to_contain_text('Normal monitoring',timeout=180000)
            browser_expect(panel.locator('[data-model=v3]')).to_be_visible();browser_expect(panel.locator('[data-model=yolo11n-pose-temporal-rule-v1]')).to_be_visible()
            browser_expect(panel.get_by_test_id('frame-detections')).to_be_visible();browser_expect(panel.get_by_role('heading',name='Event Timeline',exact=True)).to_be_visible()
            browser_expect(panel.get_by_role('heading',name='Evidence Preview',exact=True)).to_be_visible()
            page.screenshot(path=str(OUT/'automatic-camera.png'),full_page=True)
            page.set_viewport_size({'width':390,'height':844});assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1');page.screenshot(path=str(OUT/'compact-mobile.png'),full_page=True);page.set_viewport_size({'width':1500,'height':1050})
            return {'actual_recording_autoplay':True,'automatic_v3_pose_completed':True,'overlays_timeline_evidence_retained':True,'mobile_no_overflow':True}
        check('Camera automatic playback and actual Fight/Fall monitoring still work',automatic)
        def developer():
            page.evaluate("window.location.hash='/developer/testing'")
            root=page.get_by_test_id('developer-testing-page');browser_expect(root).to_be_visible()
            for title in ['Scenario Testing Library','Public-area Video Analysis','Sensor Replay & SOS Demo']:browser_expect(root.get_by_role('heading',name=title,exact=True)).to_be_visible()
            browser_expect(root.get_by_label('Video upload',exact=True)).to_be_visible()
            page.wait_for_function("()=>document.querySelectorAll('select[aria-label=\"Scenario recording\"] option').length>=12")
            browser_expect(root.get_by_label('Recorded sensor result',exact=True).locator('option')).not_to_have_count(1)
            browser_expect(root.get_by_role('heading',name='Saved predictions & controlled tests',exact=True)).to_be_visible()
            browser_expect(root.get_by_text('Telegram TEST dispatch',exact=True)).to_be_visible()
            page.reload();browser_expect(page.get_by_test_id('developer-testing-page')).to_be_visible()
            page.screenshot(path=str(OUT/'developer-tools.png'),full_page=True)
            nav('Live Monitoring');browser_expect(page.get_by_test_id('camera-monitoring')).to_be_visible();assert page.evaluate('location.hash')==''
            page.goto('http://127.0.0.1:3001/#/developer/testing');browser_expect(page.get_by_test_id('developer-testing-page')).to_be_visible()
            page.get_by_role('button',name='Return to Live Monitoring',exact=True).click();browser_expect(page.get_by_test_id('camera-monitoring')).to_be_visible();assert page.evaluate('location.hash')==''
            return {'route':'#/developer/testing','all_research_tools_retained':True,'direct_load_reload_sidebar_and_return_work':True}
        check('Separate developer route retains scenario/upload/replay tools',developer)
        def history():
            page.goto('http://127.0.0.1:3001');browser_expect(page.get_by_text('Monitored School Zones',exact=True)).to_be_visible()
            page.evaluate("window.location.hash='/developer/testing'");browser_expect(page.get_by_test_id('developer-testing-page')).to_be_visible()
            page.go_back();browser_expect(page.get_by_test_id('developer-testing-page')).to_have_count(0);browser_expect(page.get_by_text('Monitored School Zones',exact=True)).to_be_visible()
            page.go_forward();browser_expect(page.get_by_test_id('developer-testing-page')).to_be_visible()
            nav('Live Monitoring');page.evaluate("window.location.hash='/developer/testing'");browser_expect(page.get_by_test_id('developer-testing-page')).to_be_visible()
            page.go_back();browser_expect(page.get_by_test_id('camera-monitoring')).to_be_visible()
            page.go_forward();browser_expect(page.get_by_test_id('developer-testing-page')).to_be_visible()
            return {'browser_back_forward':True,'return_to_previous_operator_page':True}
        check('Developer route supports browser back and forward',history)
        def replay():
            root=page.get_by_test_id('developer-testing-page');root.get_by_label('Recorded sensor result',exact=True).select_option('radar:0')
            with page.expect_response(lambda r:r.url.endswith('/sensors/replay') and r.request.method=='POST') as result:root.get_by_role('button',name='Replay recorded prediction',exact=True).click()
            data=result.value.json();assert result.value.ok and data['event']['processing_mode']=='recorded_sensor_replay'
            browser_expect(page.get_by_test_id('incident-evidence')).to_be_visible();page.get_by_role('button',name='Close',exact=True).click()
            return {'saved_replay_works':True,'mode':data['event']['processing_mode'],'test_database_only':True}
        check('Moved saved-sensor replay remains functional against backend',replay)
        def operational():
            nav('Digital Twin Map');page.locator('[data-zone-id="ZONE_TOILET_BLINDSPOT"] polygon').first.click()
            view=page.get_by_test_id('private-monitoring-view');browser_expect(view).to_be_visible();browser_expect(view.get_by_test_id('private-twin-scene').locator('canvas')).to_be_visible()
            view.get_by_role('button',name='ACTIVATE SOS EMERGENCY',exact=True).click()
            browser_expect(page.get_by_role('heading',name='Authorize Prototype SOS Test',exact=True)).to_be_visible()
            page.get_by_role('button',name='Cancel',exact=True).click()
            assert view.locator('video,audio,img').count()==0
            for name in ['Overview','Live Monitoring','Digital Twin Map','Alerts','Incident Review','Analytics','Devices & Sensors','Reports','Settings']:
                nav(name);browser_expect(page.locator('main')).not_to_be_empty()
            assert len(page.locator('aside nav button').all_text_contents())==9
            assert not errors,errors
            return {'original_3D_canvas':True,'operational_SOS_confirmation_accessible':True,'SOS_cancelled_without_broadcast':True,'nine_original_navigation_items':True,'browser_errors':errors}
        check('Original navigation, Digital Twin/private 3D and SOS access preserved',operational)
        browser.close()
    preserved=json.loads((OUT/'preserved-before.json').read_text());assert all(hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest for name,digest in preserved.items())
    (OUT/'preserved-after.json').write_text(json.dumps(preserved,indent=2));print('PASS protected operational pages and backend source hashes unchanged',flush=True)
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
