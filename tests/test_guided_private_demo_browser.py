"""Actual default guided experience, hands-off synthetic staff workflow, isolated DB."""
import json,math,os,shutil,socket,subprocess,sys,tempfile,time,traceback
from pathlib import Path
import httpx
from playwright.sync_api import sync_playwright,expect

sys.stdout.reconfigure(encoding='utf-8')
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'runtime/guided-private-demo-checks';OUT.mkdir(parents=True,exist_ok=True)
ROWS=[];PROCESSES=[];B='http://127.0.0.1:18830';D='http://127.0.0.1:3001';TOKEN='guided-demo-browser'
def record(name,actual):
    ROWS.append({'test':name,'status':'PASS','actual':actual});print('PASS',name,json.dumps(actual)[:550],flush=True)
    (OUT/'results.json').write_text(json.dumps(ROWS,indent=2),encoding='utf-8')

with tempfile.TemporaryDirectory() as temp:
    env={**os.environ,'SAFESENSE_DB_PATH':str(Path(temp)/'guided.sqlite3'),'TELEGRAM_MODE':'disabled','TELEGRAM_STAFF_DISPATCH_ENABLED':'false',
         'SAFESENSE_API_TOKEN':TOKEN,'VITE_SAFESENSE_API_TOKEN':TOKEN,'VITE_API_BASE_URL':B,'VITE_AI_BASE_URL':'http://127.0.0.1:18832'}
    client=httpx.Client(base_url=B,headers={'X-SafeSense-Token':TOKEN},timeout=10)
    try:
        for port in (18830,3001):
            with socket.socket() as probe:probe.bind(('127.0.0.1',port))
        for name,cmd,cwd,url in [
          ('backend',[str(ROOT/'.venv/Scripts/python.exe'),'-m','uvicorn','backend.main:app','--host','127.0.0.1','--port','18830'],ROOT,B+'/health'),
          ('frontend',[shutil.which('node'),str(ROOT/'dashboard/node_modules/vite/bin/vite.js'),'--host','127.0.0.1','--port','3001','--strictPort'],ROOT/'dashboard',D)]:
            log=(OUT/(name+'.log')).open('w',encoding='utf-8');proc=subprocess.Popen(cmd,cwd=cwd,env=env,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW);PROCESSES.append((proc,log))
            for _ in range(100):
                if proc.poll() is not None:raise RuntimeError(name+' exited')
                try:
                    if httpx.get(url,timeout=1).status_code==200:break
                except httpx.HTTPError:pass
                time.sleep(.2)
            else:raise RuntimeError(name+' startup timeout')
        with sync_playwright() as pw:
            browser=pw.chromium.launch(headless=True,args=['--enable-unsafe-swiftshader'])
            page=browser.new_page(viewport={'width':1600,'height':1100});page.set_default_timeout(20000)
            errors=[];writes=[]
            page.on('pageerror',lambda e:errors.append(str(e)))
            page.on('request',lambda r:writes.append(r.url) if r.method=='POST' else None)
            page.add_init_script("window.captureCalls=0;if(navigator.mediaDevices)navigator.mediaDevices.getUserMedia=async()=>{window.captureCalls++;throw Error('Capture forbidden');};")
            page.goto(D);page.locator('aside').get_by_role('button',name='Digital Twin Map',exact=True).click()
            page.locator('[data-zone-id="ZONE_TOILET_BLINDSPOT"] polygon').first.click()
            guide=page.get_by_test_id('guided-private-demo');scene=page.get_by_test_id('private-twin-scene');renderer=page.get_by_test_id('private-three-renderer')
            expect(guide).to_be_visible();expect(scene.locator('canvas')).to_be_visible()
            expect(guide).to_contain_text('SIMULATED DEMO');expect(guide).to_contain_text('Hardware Disconnected')
            assert guide.get_by_role('combobox',name='Guided scenario').locator('option').all_text_contents()==['Normal Presence','Proximity','Repetitive Motion','Possible Fall','SOS']
            assert page.get_by_test_id('normalized-sensor-panel').count()==0
            assert page.get_by_test_id('tracking-playback-controls').count()==0
            assert len(client.get('/state').json()['events'])==0
            record('Default compact guided view; five scenarios; unambiguous source/hardware labels; no automatic writes before Start','PASS')
            def stats():return json.loads(renderer.get_attribute('data-tracking'))
            page.wait_for_function("!!document.querySelector('[data-testid=private-three-renderer]').dataset.tracking")
            guide.get_by_role('button',name='Start guided demo',exact=True).click()
            page.wait_for_function("JSON.parse(document.querySelector('[data-testid=private-three-renderer]').dataset.tracking).time>=4.5")
            guide.get_by_role('button',name='Pause guided demo',exact=True).click()
            page.wait_for_timeout(200);before=stats();count=int(renderer.get_attribute('data-render-count'))
            page.wait_for_timeout(700);assert stats()['time']==before['time'];assert int(renderer.get_attribute('data-render-count'))-count<=1
            assert len(client.get('/state').json()['events'])==0
            record('Pause freezes normalized tracks and future workflow steps before incident trigger',{'time':before['time'],'idleRenderDelta':int(renderer.get_attribute('data-render-count'))-count})
            observation=json.loads(renderer.get_attribute('data-normalized-observation'))
            assert observation['schema_version']==1 and observation['source_mode']=='SIMULATION' and observation['data_validity']=='VALID'
            assert observation['coordinate_frame']=='zone_meters_x_right_y_forward_z_up' and observation['tracking_session_id']
            assert len(observation['tracks'])==before['active']==2
            for t in observation['tracks']:
                rendered=next(p for p in before['positions'] if p['id']==t['id'])
                assert all(abs(rendered[k]-t['position'][k])<1e-9 for k in ('x','y','z'))
            response=client.post('/sensors/motion/preview',json={'observations':[observation]});assert response.status_code==200,response.text
            a,b=observation['tracks'];separation=math.dist(list(a['position'].values()),list(b['position'].values()))
            expect(guide.locator('[data-metric="Active tracks"]')).to_have_text('2')
            expect(guide.locator('[data-metric="Simulated separation"]')).to_contain_text(f'{separation:.2f}')
            record('Rendered observation validates against actual backend schema; count/distance match coordinates',{'count':2,'distance_m':separation,'mode':observation['source_mode']})
            scene.scroll_into_view_if_needed();bounds=renderer.bounding_box();point=stats()['trackPixels'][0]
            page.mouse.click(bounds['x']+point['x'],bounds['y']+point['y'])
            expect(guide.get_by_test_id('guided-selection')).to_contain_text('SIMULATED T01')
            fixtures=json.loads(renderer.get_attribute('data-fixture-pixels'));point=fixtures['sos'];bounds=renderer.bounding_box()
            page.mouse.click(bounds['x']+point['x'],bounds['y']+point['y'])
            expect(guide.get_by_test_id('guided-selection')).to_contain_text('SOS')
            guide.get_by_role('button',name='Acoustic ·',exact=False).click()
            expect(guide.get_by_test_id('guided-selection')).to_contain_text('no microphone or speech recording')
            record('Actual 3D track/fixture picking and accessible sensor inspection work','SIMULATED T01 / SOS / Acoustic')
            camera=renderer.get_attribute('data-camera-position');scene.get_by_title('Zoom In',exact=True).click()
            assert renderer.get_attribute('data-camera-position')!=camera
            scene.get_by_title('Reset Orbit View',exact=True).click();assert renderer.get_attribute('data-camera-position')==camera
            record('Original room camera zoom and reset preserved',camera)
            page.evaluate('''()=>{window.guidedStages=[];const root=document.querySelector('[data-testid=guided-private-demo]');
              const capture=()=>{const name=root.querySelector('[aria-current=step]')?.textContent;if(name&&!window.guidedStages.includes(name))window.guidedStages.push(name);};
              window.guidedObserver=new MutationObserver(capture);window.guidedObserver.observe(root,{subtree:true,attributes:true,childList:true});capture();}''')
            guide.get_by_role('combobox',name='Guided playback speed').select_option('4')
            guide.get_by_role('button',name='Restart guided demo',exact=True).click()
            expect(guide.get_by_test_id('guided-demo-progress')).to_contain_text('Demo complete',timeout=25000)
            incidents=client.get('/state').json()['incidents'];assert len(incidents)==1
            report=client.get('/incidents/'+incidents[0]['id']+'/report').json()
            assert report['level']=='HIGH' and report['status']=='RESOLVED'
            assert report['acknowledged_by'].startswith('SIMULATED DEMO') and report['resolved_by'].startswith('SIMULATED DEMO')
            history={h['status'] for h in report['history']};assert {'NEW','ACKNOWLEDGED','RESOLVED'}<=history and 'VERIFIED' not in history
            stages=page.evaluate('window.guidedStages');assert all(any(step in label for label in stages) for step in ['Detection','Risk Assessment','Incident','Staff Response'])
            record('One Start/Restart completes fall detection → assessment → incident → explicitly simulated response',{'level':report['level'],'status':report['status'],'stages':stages,'no_auto_verified':True})
            page.screenshot(path=str(OUT/'guided-fall-desktop.png'),full_page=True)
            guide.get_by_role('button',name='Open linked test incident #'+report['id'][:8],exact=True).click()
            expect(page.get_by_role('heading',name='Incident evidence & staff notifications',exact=True)).to_be_visible()
            record('Linked incident opens the existing canonical report',report['id'])
            page.get_by_role('button',name='Close',exact=True).click()
            guide=page.get_by_test_id('guided-private-demo')
            for demo,expected in [('normal',None),('proximity',None),('repetitive','OBSERVE'),('sos','CRITICAL')]:
                guide.get_by_role('combobox',name='Guided scenario').select_option(demo)
                previous={i['id'] for i in client.get('/state').json()['incidents']}
                guide.get_by_role('button',name='Start guided demo',exact=True).click()
                if demo=='proximity':
                    page.wait_for_function("JSON.parse(document.querySelector('[data-testid=private-three-renderer]').dataset.tracking).time>=10")
                    expect(guide.locator('[data-metric="Simulated separation"]')).to_contain_text('0.60')
                expect(guide.get_by_test_id('guided-demo-progress')).to_contain_text('Demo complete',timeout=25000)
                added=[i for i in client.get('/state').json()['incidents'] if i['id'] not in previous]
                assert len(added)==(1 if expected else 0),(demo,added)
                if expected:
                    current=client.get('/incidents/'+added[0]['id']+'/report').json()
                    assert current['level']==expected and current['status']=='RESOLVED'
                    assert current['is_test'] and current['source_type']=='SIMULATION'
                    assert current['notification_state']=='DISABLED'
                    if demo=='sos':assert current['evidence'][0]['confidence']==0
                record('Hands-off '+demo+' guided workflow',{'new_incidents':len(added),'outcome':expected or 'No danger incident','automatic_response':'SIMULATED only'})
            guard=page.evaluate('''async()=>{const {assertGuidedIncident}=await import('/src/components/private-area/GuidedPrivateDemo.tsx');
              const run={id:'test',incidentId:'demo-id',workflow:'guided'};const valid={id:'demo-id',is_test:true,source_type:'SIMULATION',processing_mode:'simulation',analysis_run_id:'private-demo:test'};
              assertGuidedIncident(valid,run);return [{is_test:false},{source_type:'LIVE SENSOR'},{processing_mode:'real_model'},{analysis_run_id:'other-run'},{id:'other-incident'}].map(patch=>{try{assertGuidedIncident({...valid,...patch},run);return false;}catch{return true;}});}''')
            assert all(guard);record('Automatic responder refuses real, non-test or unrelated incident fixtures',guard)
            before=len(client.get('/state').json()['incidents']);guide.get_by_role('button',name='Restart guided demo',exact=True).click()
            expect(guide.get_by_test_id('guided-demo-progress')).to_contain_text('Demo complete',timeout=20000)
            assert len(client.get('/state').json()['incidents'])==before
            record('Restart replays the same test without duplicate incidents',{'incidents':before})
            guide.locator('summary').click();expect(guide).to_contain_text('No ML result is generated by this guided demo')
            expect(guide).to_contain_text('Sending disabled');assert not any('/testing/runs' in path for path in writes)
            record('Exact simulated-vs-computed disclosure; no fabricated ML inference or Telegram delivery',{'model_job_requests':0,'notification':'DISABLED'})
            page.screenshot(path=str(OUT/'guided-complete-desktop.png'),full_page=True)
            page.set_viewport_size({'width':430,'height':1000});guide.scroll_into_view_if_needed()
            assert page.evaluate('document.documentElement.scrollWidth<=window.innerWidth+1')
            expect(scene.locator('canvas')).to_be_visible();record('Compact guided controls and room remain responsive on mobile','430px viewport')
            page.set_viewport_size({'width':1600,'height':1100});page.get_by_role('button',name='Return to campus map',exact=True).click()
            expect(page.locator('[data-zone-id="ZONE_TOILET_BLINDSPOT"]')).to_have_attribute('data-risk-level','LOW')
            page.locator('[data-zone-id="ZONE_TOILET_BLINDSPOT"] polygon').first.click()
            page.get_by_role('button',name='Advanced Monitoring',exact=True).click()
            expect(page.get_by_test_id('normalized-sensor-panel')).to_be_visible()
            expect(page.get_by_test_id('recorded-private-evidence')).to_be_visible()
            assert page.get_by_test_id('recorded-evidence-result').count()==0
            assert page.evaluate('window.captureCalls')==0 and not errors,errors
            record('Original campus navigation and advanced recorded-inference tools preserved; zero capture/errors',{'capture_calls':0,'errors':errors,'map_risk':'LOW','invented_model_results':0})
            browser.close()
    except Exception as error:
        ROWS.append({'test':'Guided browser workflow','status':'FAIL','actual':str(error),'trace':traceback.format_exc()});raise
    finally:
        (OUT/'results.json').write_text(json.dumps(ROWS,indent=2),encoding='utf-8');client.close()
        for proc,log in reversed(PROCESSES):
            proc.terminate()
            try:proc.wait(timeout=8)
            except subprocess.TimeoutExpired:proc.kill();proc.wait()
            log.close()
