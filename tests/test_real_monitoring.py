"""Actual isolated HTTP + browser workflow. Never sends Telegram or touches existing services."""
from pathlib import Path
import json,os,subprocess,sys,time,traceback,shutil
import httpx

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
sys.stdout.reconfigure(encoding='utf-8')
OUT=ROOT/'runtime/real-monitoring-tests'
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
    bp=start('backend',[sys.executable,'-m','uvicorn','backend.main:app','--host','127.0.0.1','--port','18000'],B+'/health')
    start('inference',[sys.executable,'-m','uvicorn','fight_api:app','--host','127.0.0.1','--port','18001'],A+'/health')
    def registry():
        cameras=expect(client.get(B+'/monitoring/cameras'));scenarios=expect(client.get(B+'/monitoring/scenarios'))
        assert len(cameras)==5 and len(scenarios)>=17 and all(s['available'] for s in scenarios)
        assert all(c['zone_type']=='OPEN_HIDDEN' for c in cameras)
        response=client.get(B+'/monitoring/sources/conflict',headers={'Range':'bytes=0-1023'})
        assert response.status_code==206 and len(response.content)==1024
        return {'cameras':len(cameras),'scenario_registry':len(scenarios),'verified_actual_videos':sum(s['input_type']=='video' for s in scenarios),'byte_range':206}
    check('Source registry, real recordings and seekable media',registry)
    check('Unauthenticated incidents blocked',lambda:expect(httpx.get(B+'/incidents'),401))
    check('Unauthenticated source media blocked',lambda:expect(httpx.get(B+'/monitoring/sources/conflict'),401))
    def privacy():
        for route in ('fight','fall'):
            r=client.post(A+'/ai/'+route+'/analyze',data={'zone_id':'ZONE_TOILET_BLINDSPOT','authorized':'true'},files={'file':('private.mp4',b'invalid','video/mp4')})
            expect(r,403)
        expect(client.post(A+'/monitoring/jobs',json={'scenario_id':'fall','zone_id':'ZONE_TOILET_BLINDSPOT','authorized':True}),403)
        expect(client.post(B+'/event',json={'zone':'ZONE_TOILET_BLINDSPOT','type':'fall','source':'radar','evidence_media':[{'url':'video.mp4'}]}),403)
        return 'Both upload APIs, job API and private evidence ingestion reject video'
    check('Private-zone enforcement at API layer',privacy)
    saved={}
    def inference(scenario,model,zone):
        row=job(scenario,model,zone);r=row['result'];saved[scenario+'-'+model]=r
        assert r['event_delivery']['status']=='recorded',r
        if r['candidate_detected']:
            assert r['evidence_media'],r
            media=r['evidence_media'][0]
            expect(httpx.get(A+media['url']),401)
            response=client.get(A+media['url'],headers={'Range':'bytes=0-1023'})
            assert response.status_code==206,response.text[:500]
            report=expect(client.get(B+'/incidents/'+r['event_delivery']['incident_id']+'/report'))
            assert any(e.get('evidence_media') for e in report['evidence'])
        return {'score':r.get('score'),'candidate':r['candidate_detected'],'events':r.get('events'),
                'seconds':r['inference_time_sec'],'fps':r['inference_fps'],'evidence':r['evidence_media'],'incident':r['event_delivery']['incident_id']}
    check('Actual AIRTLab Fight V2 → candidate → retained evidence → incident',lambda:inference('conflict','v2','ZONE_CORRIDOR_A'))
    check('Actual AIRTLab Fight V3 with feature cache and evidence',lambda:inference('conflict','v3','ZONE_CORRIDOR_A'))
    check('Actual normal recording classification (no forced label)',lambda:inference('normal','v3','ZONE_CANTEEN'))
    check('Actual UR Fall → YOLO boxes/skeletons → candidate/evidence',lambda:inference('fall','pose','ZONE_STAIRCASE'))
    def all_models():
        row=job('conflict','all','ZONE_CORRIDOR_A');result=row['result']
        assert not result['model_errors'],result
        assert {r['model_version'] for r in result['model_results']}=={'v2','v3','yolo11n-pose-temporal-rule-v1'}
        assert result['annotated_video_url'] and result['candidate_detected']
        for model_result in result['model_results']:
            assert model_result['event_delivery']['status']=='recorded'
            if model_result['candidate_detected']:assert model_result['evidence_media']
        report=expect(client.get(B+'/incidents/'+result['event_delivery']['incident_id']+'/report'))
        assert any(e['model_version']=='v2' for e in report['evidence'])
        assert any(e['model_version']=='v3' for e in report['evidence'])
        return {'models':[r['model_version'] for r in result['model_results']], 'actual_pose_annotation':result['annotated_video_url'],'incident':report['id']}
    check('Legacy source all-mode comparison retains V2/V3 and actual YOLO overlays',all_models)
    def lifecycle():
        identifier=saved['conflict-v3']['event_delivery']['incident_id']
        expect(client.post(B+'/incidents/'+identifier+'/ack',json={'staff':'Integration operator'}))
        report=expect(client.get(B+'/incidents/'+identifier+'/report'))
        assert report['status']=='ACKNOWLEDGED'
        zones=expect(client.get(B+'/zones'))
        assert identifier in next(z for z in zones if z['id']=='ZONE_CORRIDOR_A')['active_incident_ids']
        expect(client.post(B+'/incidents/'+identifier+'/review',json={'status':'RESOLVED','note':'Test completed'}))
        assert expect(client.get(B+'/incidents/'+identifier+'/report'))['status']=='RESOLVED'
        expect(client.post(B+'/incidents/'+identifier+'/ack',json={'staff':'Operator'}),409)
        return 'Acknowledgement, history, zone active incident synchronization and terminal ack rejection'
    check('Unified incident lifecycle and Digital Twin state',lifecycle)
    def sensors():
        options=expect(client.get(B+'/sensors/replay'));record=next(r for r in options if r['sensor']=='radar' and r['candidate'])
        r=expect(client.post(B+'/sensors/replay',json={'zone':'ZONE_TOILET_BLINDSPOT','sensor':'radar','index':record['index']}))
        assert r['event']['processing_mode']=='recorded_sensor_replay' and not r['event']['evidence_media']
        return {'record':record,'mode':r['event']['processing_mode']}
    check('Recorded private radar replay → sensor-only incident',sensors)
    def sos():
        payload={'zone':'ZONE_TOILET_BLINDSPOT','type':'sos','source':'simulation','processing_mode':'simulation','event_id':'unique-sos-integration'}
        r=expect(client.post(B+'/event',json=payload));incident=r['incident']
        again=expect(client.post(B+'/event',json=payload));assert again['deduplicated']
        n=expect(client.post(B+'/incidents/'+incident['id']+'/notify-test',json={}))
        assert n['status']=='DISABLED' and 'TEST INCIDENT' in n['preview']
        return {'incident':incident['id'],'risk':incident['level'],'notification':n['status'],'no_external_send':True}
    check('Private test SOS, deduplication and honest Telegram preview',sos)
    def failure():
        expect(client.post(A+'/monitoring/jobs',json={'scenario_id':'missing','zone_id':'ZONE_CORRIDOR_A','authorized':True}),404)
        expect(client.post(A+'/monitoring/jobs',json={'scenario_id':'fall','zone_id':'ZONE_CORRIDOR_A','model':'bad','authorized':True}),422)
        expect(client.get(A+'/monitoring/evidence/not-a-uuid'),404)
        return 'Missing source, invalid model, invalid evidence ID rejected'
    check('Failure conditions and evidence ID traversal defense',failure)
    def sensor_scenarios():
        results={}
        for scenario in ('acoustic','fusion','sos','telegram'):
            result=expect(client.post(B+'/monitoring/scenarios/'+scenario+'/run',json={}))
            assert result.get('incident'),result
            assert not result['event']['evidence_media']
            results[scenario]={'mode':result['event']['processing_mode'],'risk':result['incident']['level']}
        return results
    check('Central acoustic, controlled fusion, SOS and Telegram-test scenarios',sensor_scenarios)
    def evidence_delete():
        media=saved['conflict-v2']['evidence_media'][0]
        expect(client.post(A+media['url']+'/delete',json={}))
        expect(client.get(A+media['url']),410)
        return 'Authenticated deletion removes retained clip; stale reference returns 410'
    check('Evidence deletion and stale-reference handling',evidence_delete)
    def restart():
        before=expect(client.get(B+'/incidents'))
        bp.terminate();bp.wait(timeout=10)
        start('backend-restart',[sys.executable,'-m','uvicorn','backend.main:app','--host','127.0.0.1','--port','18000'],B+'/health')
        after=expect(client.get(B+'/incidents'));assert len(before)==len(after)
        assert {r['id']:r['status'] for r in before}=={r['id']:r['status'] for r in after}
        return {'persisted_incidents':len(after),'db':ENV['SAFESENSE_DB_PATH']}
    check('SQLite persistence across actual backend restart',restart)
    start('dashboard',[shutil.which('node'),str(ROOT/'dashboard/node_modules/vite/bin/vite.js'),'--host','127.0.0.1','--port','3001','--strictPort'],'http://127.0.0.1:3001',ROOT/'dashboard')
    from playwright.sync_api import sync_playwright,expect as browser_expect
    with sync_playwright() as pw:
        browser=pw.chromium.launch(headless=True,args=['--enable-unsafe-swiftshader'])
        page=browser.new_page(viewport={'width':1500,'height':1050});page.set_default_timeout(20000)
        errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
        def nav(name):page.locator('aside').get_by_role('button',name=name,exact=True).click()
        def browser_camera():
            page.goto('http://127.0.0.1:3001',wait_until='domcontentloaded');browser_expect(page.get_by_text('FastAPI Connected',exact=True)).to_be_visible();nav('Live Monitoring')
            panel=page.get_by_test_id('camera-monitoring')
            panel.get_by_role('button',name='Corridor A CAM_CORRIDOR_A RECORDED REAL VIDEO',exact=True).click()
            browser_expect(panel.locator('video')).to_be_visible()
            page.wait_for_function("document.querySelector('[data-testid=camera-monitoring] video')?.currentTime > 0",timeout=30000)
            browser_expect(panel.get_by_text('Review camera incident and evidence',exact=True)).to_be_visible(timeout=180000)
            browser_expect(panel.get_by_label('Camera analysis model',exact=True)).to_have_count(0)
            browser_expect(panel.locator('video')).to_have_attribute('src',__import__('re').compile('/ai/fall/artifacts/'))
            browser_expect(panel.get_by_text('v2',exact=True)).to_have_count(0)
            browser_expect(panel.get_by_text('v3',exact=True)).to_be_visible()
            browser_expect(panel.get_by_text('yolo11n-pose-temporal-rule-v1',exact=True)).to_be_visible()
            panel.get_by_text('Review camera incident and evidence',exact=True).click()
            browser_expect(page.get_by_text('Incident evidence & staff notifications',exact=True)).to_be_visible()
            browser_expect(page.get_by_text('Incident evidence & staff notifications',exact=True).locator('..').locator('video').first).to_be_visible()
            page.screenshot(path=str(OUT/'camera-evidence.png'),full_page=True)
            page.get_by_role('button',name='Close',exact=True).click()
            return 'Click feed autoplays actual recording, runs model, opens incident and retained clip'
        check('Browser public feed → autoplay → inference → evidence',browser_camera)
        def browser_private():
            if page.get_by_role('button',name='Close',exact=True).count():page.get_by_role('button',name='Close',exact=True).click()
            nav('Digital Twin Map');page.locator('[data-zone-id="ZONE_TOILET_BLINDSPOT"] polygon').first.click()
            room=page.get_by_test_id('private-monitoring-view');browser_expect(room).to_be_visible()
            canvas=room.locator('canvas');browser_expect(canvas).to_be_visible()
            assert room.locator('video,audio,img').count()==0
            room.get_by_role('button',name='● Open zone incident · metadata only',exact=True).click()
            browser_expect(page.get_by_text('Private sensor metadata only. No images, video, or speech are captured.',exact=True)).to_be_visible()
            page.get_by_role('button',name='Close',exact=True).click()
            page.screenshot(path=str(OUT/'private-original-3d.png'),full_page=True)
            return {'original_3d':True,'private_media_elements':0,'canvas_count':canvas.count()}
        check('Browser original private 3D navigation and no private media',browser_private)
        def reports():
            nav('Reports');browser_expect(page.get_by_role('heading',name='Reports & analysis',exact=True)).to_be_visible()
            identifier=saved['fall-pose']['event_delivery']['incident_id']
            page.get_by_label('Report incident',exact=True).select_option(identifier)
            report=page.get_by_test_id('incident-report')
            browser_expect(report.get_by_role('tab',name='Summary',exact=True)).to_have_attribute('aria-selected','true')
            report.get_by_role('tab',name='Evidence',exact=True).click();browser_expect(report.locator('video').first).to_be_visible()
            report.get_by_role('tab',name='Response',exact=True).click()
            browser_expect(report.get_by_text('Staff notification delivery',exact=True)).to_be_visible()
            report.get_by_label('Report reviewing staff',exact=True).fill('Integration duty operator')
            report.get_by_role('button',name='Acknowledge incident',exact=True).click()
            browser_expect(report.get_by_role('button',name='Acknowledge incident',exact=True)).to_have_count(0)
            report.get_by_label('Report resolution note',exact=True).fill('Reviewed the actual retained UR Fall clip; controlled test complete')
            report.get_by_role('button',name='Resolve incident',exact=True).click()
            browser_expect(report.get_by_role('button',name='Resolve incident',exact=True)).to_have_count(0)
            actual=expect(client.get(B+'/incidents/'+identifier+'/report'));assert actual['status']=='RESOLVED' and actual['analysis']['resolution_seconds'] is not None
            report.get_by_role('tab',name='Analysis',exact=True).click();browser_expect(report.get_by_text('Detection and response analysis',exact=True)).to_be_visible()
            browser_expect(report.locator('video')).to_have_count(0)
            page.get_by_role('button',name='Operational analysis',exact=True).click();browser_expect(page.get_by_role('heading',name='Operational incident statistics',exact=True)).to_be_visible()
            page.get_by_role('button',name='Model evaluation',exact=True).click();browser_expect(page.get_by_role('heading',name='Saved Research Evaluations',exact=True)).to_be_visible()
            return {'sections':['Summary','Evidence','Response','Analysis'],'resolved_incident':identifier,'acknowledgement_seconds':actual['analysis']['acknowledgement_seconds'],'resolution_seconds':actual['analysis']['resolution_seconds']}
        check('Organized actual incident report → acknowledgement → resolution → analysis',reports)
        def pages():
            for name in ['Overview','Live Monitoring','Digital Twin Map','Alerts','Incident Review','Analytics','Devices & Sensors','Reports','Settings']:
                nav(name);browser_expect(page.locator('main')).not_to_be_empty()
            assert not errors,errors
            return 'All nine existing pages render without JavaScript exceptions'
        check('Existing dashboard navigation preserved',pages)
        browser.close()
    def legacy_browser():
        log=OUT/'legacy-browser-output.txt'
        with log.open('w',encoding='utf-8') as output:
            completed=subprocess.run([sys.executable,str(ROOT/'tests/test_browser_demo.py')],cwd=ROOT,env=ENV,stdout=output,stderr=subprocess.STDOUT,timeout=300,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        assert completed.returncode==0,'Legacy browser regression failed; see '+str(log)
        return 'Original dashboard upload/pose/replay/SOS/report/filter/mobile browser suite passed on isolated services'
    check('Original dashboard browser workflows preserved',legacy_browser)
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
