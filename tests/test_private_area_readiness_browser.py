"""Refresh, actual server restart, SQLite/map/review persistence and packet-loss UI."""
import hashlib,json,os,shutil,socket,sqlite3,subprocess,sys,time,traceback
from pathlib import Path
from uuid import uuid4
import httpx
from playwright.sync_api import sync_playwright,expect
sys.stdout.reconfigure(encoding='utf-8')
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'runtime/private-area-hardware-readiness';OUT.mkdir(parents=True,exist_ok=True)
RUN=OUT/('browser-'+str(time.time_ns()));RUN.mkdir()
B='http://127.0.0.1:18830';D='http://127.0.0.1:3001';TOKEN='readiness-browser';ROWS=[];PROCESSES=[]
env={**os.environ,'SAFESENSE_DB_PATH':str(RUN/'isolated.sqlite3'),'TELEGRAM_MODE':'disabled','TELEGRAM_STAFF_DISPATCH_ENABLED':'false',
     'SAFESENSE_API_TOKEN':TOKEN,'VITE_SAFESENSE_API_TOKEN':TOKEN,'VITE_API_BASE_URL':B,'VITE_AI_BASE_URL':'http://127.0.0.1:18832'}
client=httpx.Client(base_url=B,headers={'X-SafeSense-Token':TOKEN},timeout=5)
protected=['ai_models/radar/benchmark_radar.py','backend/radar_simulation.py','backend/scenario_testing.py','scripts/scenario_sensor_worker.py',
           'yolo11n-pose.pt','evaluation/outputs/fight_multiclip_v2/fight_multiclip_classifier.joblib','evaluation/outputs/fight_v3/fight_v3_classifier.joblib']
hashes={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in protected}
def record(name,actual):
    ROWS.append({'test':name,'status':'PASS','actual':actual});print('PASS',name,json.dumps(actual)[:600],flush=True)
    (OUT/'browser-readiness-results.json').write_text(json.dumps(ROWS,indent=2),encoding='utf-8')
def start_backend(index):
    stop=RUN/f'stop-{index}';pid=RUN/f'pid-{index}';log=(RUN/f'backend-{index}.log').open('w',encoding='utf-8')
    proc=subprocess.Popen([str(ROOT/'.venv/Scripts/python.exe'),str(ROOT/'tests/readiness_test_server.py'),'--port','18830','--stop-file',str(stop),'--pid-file',str(pid)],
                          cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
    PROCESSES.append((proc,log,stop))
    for _ in range(150):
        if proc.poll() is not None:raise RuntimeError('Readiness backend exited')
        try:
            if client.get('/health').status_code==200 and pid.exists():return proc,stop,int(pid.read_text())
        except httpx.HTTPError:pass
        time.sleep(.1)
    raise RuntimeError('Backend startup timeout')
def stop_backend(proc,stop):
    stop.write_text('stop');proc.wait(timeout=15)

try:
    for port in (18830,3001):
        with socket.socket() as probe:probe.bind(('127.0.0.1',port))
    backend,stop,pid1=start_backend(1)
    log=(RUN/'frontend.log').open('w',encoding='utf-8')
    frontend=subprocess.Popen([shutil.which('node'),str(ROOT/'dashboard/node_modules/vite/bin/vite.js'),'--host','127.0.0.1','--port','3001','--strictPort'],
                              cwd=ROOT/'dashboard',env=env,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
    PROCESSES.append((frontend,log,None))
    for _ in range(100):
        try:
            if httpx.get(D,timeout=1).status_code==200:break
        except httpx.HTTPError:pass
        time.sleep(.1)
    with sync_playwright() as pw:
        browser=pw.chromium.launch(headless=True,args=['--enable-unsafe-swiftshader'])
        page=browser.new_page(viewport={'width':1600,'height':1100});page.set_default_timeout(15000)
        errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
        page.add_init_script("window.captureCalls=0;if(navigator.mediaDevices)navigator.mediaDevices.getUserMedia=async()=>{window.captureCalls++;throw Error('Private capture forbidden');};")
        def enter():
            page.locator('aside').get_by_role('button',name='Digital Twin Map',exact=True).click()
            if not page.get_by_test_id('private-monitoring-view').count():page.locator('[data-zone-id="ZONE_TOILET_BLINDSPOT"] polygon').first.click()
            return page.get_by_test_id('guided-private-demo')
        page.goto(D);guide=enter();guide.get_by_role('combobox',name='Guided playback speed').select_option('2')
        guide.get_by_role('button',name='Start guided demo',exact=True).click()
        page.wait_for_function("(()=>{const r=JSON.parse(sessionStorage.getItem('safesense-private-demo-v1:guided:fall')||'null');return !!r?.complete&&!!r.incidentId;})()")
        guide.get_by_role('button',name='Pause guided demo',exact=True).click()
        run=page.evaluate("JSON.parse(sessionStorage.getItem('safesense-private-demo-v1:guided:fall'))")
        identifier=run['incidentId'];before=client.get('/state').json();assert len(before['incidents'])==1
        assert before['incidents'][0]['status']=='NEW' and before['incidents'][0]['level']=='HIGH'
        page.reload();guide=enter();expect(guide.get_by_test_id('guided-demo-progress')).to_contain_text('Ready')
        expect(guide.get_by_role('button',name='Open linked test incident #'+identifier[:8],exact=True)).to_be_visible()
        page.wait_for_timeout(1200)
        assert len(client.get('/state').json()['incidents'])==1 and len(client.get('/state').json()['events'])==2
        assert client.get('/incidents/'+identifier+'/report').json()['status']=='NEW'
        expect(guide).to_contain_text('Hardware Disconnected')
        record('Browser refresh restores the same test identity paused; no duplicate events or automatic response',{'incident_id':identifier,'events':2,'status':'NEW','playback':'Ready at 0s'})
        stop_backend(backend,stop)
        with sqlite3.connect('file:'+str(RUN/'isolated.sqlite3')+'?mode=ro',uri=True) as db:
            saved=json.loads(db.execute("SELECT body FROM records WHERE kind='incident' AND id=?",(identifier,)).fetchone()[0])
            self_ids=[row[0] for row in db.execute("SELECT id FROM records WHERE kind='event'")]
        assert saved['status']=='NEW' and len(saved['event_ids'])==2
        backend,stop,pid2=start_backend(2);assert pid2!=pid1
        loaded=client.get('/incidents/'+identifier+'/report').json();assert loaded['status']=='NEW' and loaded['event_ids']==saved['event_ids']
        for event in run['events']:
            repeat=client.post('/event',json=event);repeat.raise_for_status();assert repeat.json()['deduplicated'] and repeat.json()['incident']['id']==identifier
        assert len(client.get('/state').json()['incidents'])==1
        record('Actual backend process restart reloads SQLite incident/evidence and deduplicates replay',{'different_pid':True,'persisted_id':identifier,'event_ids':self_ids,'incidents':1})
        guide.get_by_role('combobox',name='Guided playback speed').select_option('4')
        guide.get_by_role('button',name='Start guided demo',exact=True).click()
        expect(guide.get_by_test_id('guided-demo-progress')).to_contain_text('Demo complete',timeout=25000)
        report=client.get('/incidents/'+identifier+'/report').json();assert report['status']=='RESOLVED' and len(client.get('/state').json()['incidents'])==1
        page.get_by_role('button',name='Return to campus map',exact=True).click()
        expect(page.locator('[data-zone-id="ZONE_TOILET_BLINDSPOT"]')).to_have_attribute('data-risk-level','LOW')
        page.locator('aside').get_by_role('button',name='Incident Review',exact=True).click()
        expect(page.get_by_text('#'+identifier[:8],exact=True)).to_be_visible();expect(page.get_by_text('RESOLVED',exact=True)).to_be_visible()
        record('Post-refresh/restart response resumes on the same incident; Map and Review synchronize resolution',{'status':'RESOLVED','map_risk':'LOW','incidents':1})
        guide=enter();page.get_by_role('button',name='Advanced Monitoring',exact=True).click()
        # These are explicit browser fault fixtures, not real recording/hardware output.
        fixture={'observation_id':'TEST_FIXTURE_ONLY','source_mode':'RECORDED_REPLAY','device_id':'TEST_FIXTURE_NOT_HARDWARE','zone_id':'ZONE_TOILET_BLINDSPOT',
          'timestamp':'2026-11-02T00:00:00Z','timestamp_basis':'CAPTURE_TIME','tracking_session_id':'fault-session','data_validity':'VALID',
          'validity_reason':'Synthetic browser fault fixture only; not physical measurements or corpus results',
          'coordinate_frame':'zone_meters_x_right_y_forward_z_up','hardware_verified':False,'sos_state':'UNKNOWN',
          'tracks':[{'id':'A','position':{'x':0,'y':0,'z':.3}},{'id':'B','position':{'x':3,'y':4,'z':.3}}]}
        current={'observation':fixture,'hardware':{'connected':False,'verified':False,'label':'Hardware Disconnected'}}
        page.route('**/sensors/observations?*',lambda route:route.fulfill(json=current))
        renderer=page.get_by_test_id('private-three-renderer')
        def wait_tracks(count):
            page.wait_for_function('(n)=>JSON.parse(document.querySelector(\'[data-testid="private-three-renderer"]\').dataset.tracking).active===n',arg=count,timeout=10000)
            return json.loads(renderer.get_attribute('data-tracking'))
        full=wait_tracks(2);assert full['pairs'][0]['meters']==5
        current['observation']={**fixture,'tracks':[{'id':'A','position':None},fixture['tracks'][1]],'timestamp':'2026-11-02T00:00:00.100Z'}
        one=wait_tracks(1);assert one['positions'][0]['id']=='B' and not one['pairs']
        current['observation']={**fixture,'tracks':None,'timestamp':'2026-11-02T00:00:00.200Z'}
        none=wait_tracks(0);assert not none['pairs'] and none['trailVertices']==0
        record('Missing coordinates / track loss remove markers, distances and trails without zero-value invention',{'full_tracks':2,'distance_m':5,'one_remaining_id':'B','unsupported_tracks':0})
        current['observation']={**fixture,'tracks':[{'id':'NEW_ID','position':{'x':.1,'y':.2,'z':.3}}],'timestamp':'2026-11-02T00:00:00.300Z'}
        replaced=wait_tracks(1);assert replaced['positions'][0]['id']=='NEW_ID'
        current['observation']={**fixture,'data_validity':'STALE','timestamp':'2026-11-02T00:00:00.400Z'}
        assert wait_tracks(0)['highlightedTrackIds']==[]
        current['observation']={**fixture,'timestamp':'','tracks':fixture['tracks']}
        page.wait_for_timeout(3300);assert json.loads(renderer.get_attribute('data-tracking'))['active']==0
        record('ID changes, stale packets and missing capture timestamps cannot keep ghost tracks or highlights',{'new_id':'NEW_ID','stale_count':0,'missing_timestamp_count':0})
        source=page.get_by_test_id('normalized-sensor-panel');source.get_by_role('combobox',name='Source mode').select_option('LIVE_HARDWARE')
        current['observation']={**fixture,'source_mode':'LIVE_HARDWARE','hardware_verified':False,'timestamp':'2026-11-02T00:00:00Z'}
        page.wait_for_timeout(3300);assert json.loads(renderer.get_attribute('data-tracking'))['active']==0
        expect(source).to_contain_text('Hardware Disconnected')
        expect(source).to_contain_text('No observation available for this mode')
        record('Unverified live-shaped packet stays unpositioned and hardware remains Disconnected',{'rendered_tracks':0,'physical_verification':False})
        page.unroute('**/sensors/observations?*')
        status=client.get('/sensors/observations/status').json();assert status['hardware']['connected'] is False and status['hardware']['verified'] is False
        assert page.evaluate('window.captureCalls')==0 and not errors,errors
        assert all(hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest for name,digest in hashes.items())
        record('No privacy capture, no runtime errors, disconnected real backend and protected model/source hashes retained',{'capture_calls':0,'errors':errors,'protected_files':len(hashes),'hardware_verified':False})
        browser.close()
except Exception as error:
    ROWS.append({'test':'Readiness fault/restart suite','status':'FAIL','actual':str(error),'trace':traceback.format_exc()});raise
finally:
    (OUT/'browser-readiness-results.json').write_text(json.dumps(ROWS,indent=2),encoding='utf-8');client.close()
    for proc,log,marker in reversed(PROCESSES):
        if proc.poll() is None:
            if marker is not None:
                try:stop_backend(proc,marker)
                except subprocess.TimeoutExpired:proc.kill();proc.wait()
            else:
                proc.terminate()
                try:proc.wait(timeout=8)
                except subprocess.TimeoutExpired:proc.kill();proc.wait()
        log.close()
