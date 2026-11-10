"""Full scenario playback and response workflow in real Chromium; isolated DB.
No physical capture or external Telegram traffic. Actual registered inference runs.
"""
import json,os,shutil,socket,subprocess,tempfile,time,traceback,sys
from pathlib import Path
import httpx
from playwright.sync_api import sync_playwright,expect

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'runtime/connected-private-demo-checks';OUT.mkdir(parents=True,exist_ok=True)
sys.stdout.reconfigure(encoding='utf-8')
ROWS=[];PROCESSES=[];B='http://127.0.0.1:18830';D='http://127.0.0.1:3001';TOKEN='connected-private-test'
def record(name,actual):
    ROWS.append({'test':name,'status':'PASS','actual':actual});print('PASS',name,json.dumps(actual)[:650],flush=True)
    (OUT/'results.json').write_text(json.dumps(ROWS,indent=2),encoding='utf-8')

with tempfile.TemporaryDirectory() as temp:
    env={**os.environ,'SAFESENSE_DB_PATH':str(Path(temp)/'workflow.sqlite3'),'TELEGRAM_MODE':'disabled',
         'TELEGRAM_STAFF_DISPATCH_ENABLED':'false','SAFESENSE_API_TOKEN':TOKEN,'VITE_SAFESENSE_API_TOKEN':TOKEN,
         'VITE_API_BASE_URL':B,'VITE_AI_BASE_URL':'http://127.0.0.1:18832'}
    client=httpx.Client(base_url=B,headers={'X-SafeSense-Token':TOKEN},timeout=10)
    try:
        for port in (18830,3001):
            with socket.socket() as probe:probe.bind(('127.0.0.1',port))
        for name,cmd,cwd,url in [
          ('backend',[str(ROOT/'.venv/Scripts/python.exe'),'-m','uvicorn','backend.main:app','--host','127.0.0.1','--port','18830'],ROOT,B+'/health'),
          ('frontend',[shutil.which('node'),str(ROOT/'dashboard/node_modules/vite/bin/vite.js'),'--host','127.0.0.1','--port','3001','--strictPort'],ROOT/'dashboard',D)]:
            log=(OUT/(name+'.log')).open('w',encoding='utf-8')
            proc=subprocess.Popen(cmd,cwd=cwd,env=env,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW);PROCESSES.append((proc,log))
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
            errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
            page.add_init_script("window.captureCalls=0;if(navigator.mediaDevices)navigator.mediaDevices.getUserMedia=async()=>{window.captureCalls++;throw Error('Capture prohibited');};")
            page.goto(D)
            def enter(demo=None):
                page.locator('aside').get_by_role('button',name='Digital Twin Map',exact=True).click()
                if page.get_by_test_id('private-monitoring-view').count()==0:
                    page.locator('[data-zone-id="ZONE_TOILET_BLINDSPOT"] polygon').first.click()
                page.get_by_role('button',name='Advanced Monitoring',exact=True).click()
                source=page.get_by_test_id('normalized-sensor-panel');source.get_by_role('combobox',name='Source mode').select_option('SIMULATION')
                panel=page.get_by_test_id('private-danger-scenarios')
                if demo:panel.get_by_role('combobox',name='Private-area demo scenario').select_option(demo)
                return panel
            panel=enter();controls=page.get_by_test_id('tracking-playback-controls')
            scene=page.get_by_test_id('private-twin-scene');renderer=page.get_by_test_id('private-three-renderer')
            expect(scene.locator('canvas')).to_be_visible()
            choices=panel.get_by_role('combobox').locator('option').all_text_contents()
            assert len(choices)==5,choices
            record('Five labeled demos and preserved original WebGL Toilet',choices)
            for demo,expected in [('normal',None),('proximity',None),('repetitive','OBSERVE'),('fall','HIGH'),('sos','CRITICAL')]:
                panel.get_by_role('combobox',name='Private-area demo scenario').select_option(demo)
                controls.get_by_role('combobox',name='Tracking playback speed').select_option('4')
                before=client.get('/state').json();before_ids={i['id'] for i in before['incidents']}
                panel.get_by_role('button',name='Run connected test demo',exact=True).click()
                expect(panel.get_by_test_id('private-demo-progress')).to_contain_text('Test signals saved',timeout=22000)
                expect(panel.get_by_test_id('private-demo-progress')).to_contain_text('Playback complete',timeout=22000)
                snapshot=client.get('/state').json();added=[i for i in snapshot['incidents'] if i['id'] not in before_ids]
                assert len(added)==(1 if expected else 0),(demo,added)
                for event in snapshot['events']:
                    assert event['processing_mode']=='simulation' and event['source_type']=='SIMULATION'
                    assert event['is_test'] and event['score'] is None and event['model_version'] is None
                    assert event['evidence_reference'].startswith('SIMULATED')
                if demo=='proximity':expect(controls.get_by_test_id('motion-analysis-readout')).to_contain_text('not proof of fighting or bullying')
                if not expected:
                    expect(panel).to_contain_text('No test incident created')
                    record('Complete '+demo+' playback with no fabricated danger incident',{'events':len(snapshot['events']),'new_incidents':0,'time':40})
                    continue
                incident=added[0];identifier=incident['id'];assert incident['level']==expected and incident['status']=='NEW'
                if demo=='sos':assert next(e for e in incident['evidence'] if e['type']=='sos')['confidence']==0
                if demo=='fall':assert {e['type'] for e in incident['evidence']}=={'fall','impact'}
                expect(panel.get_by_test_id('demo-telegram-status')).to_contain_text('Sending disabled')
                record('Complete '+demo+' playback uses canonical test incident and actual Telegram state',{'id':identifier,'level':expected,'notification':'DISABLED','source':'SIMULATION'})
                # Replaying the same run must not create another incident.
                panel.get_by_role('button',name='Replay same connected test',exact=True).click()
                controls.get_by_role('button',name='Pause tracking',exact=True).click()
                assert len(client.get('/state').json()['incidents'])==len(snapshot['incidents'])
                record(demo+' replay does not duplicate incidents',identifier)
                panel.get_by_role('button',name='View synchronized Digital Twin Map',exact=True).click()
                expect(page.locator('[data-zone-id="ZONE_TOILET_BLINDSPOT"]')).to_have_attribute('data-risk-level',expected)
                record(demo+' Map risk synchronizes with backend incident',expected)
                panel=enter(demo);controls=page.get_by_test_id('tracking-playback-controls')
                panel.get_by_role('button',name='View synchronized Alerts',exact=True).click()
                expect(page.get_by_text('#'+identifier[:8],exact=True).first).to_be_visible()
                record(demo+' Alerts shows the same persisted incident',identifier[:8])
                panel=enter(demo);controls=page.get_by_test_id('tracking-playback-controls')
                panel.get_by_role('button',name='Acknowledge test incident',exact=True).click()
                expect(panel.get_by_test_id('demo-incident-status')).to_have_text('ACKNOWLEDGED')
                panel.get_by_role('button',name='Record human test verification',exact=True).click()
                expect(panel.get_by_test_id('demo-incident-status')).to_have_text('VERIFIED')
                panel.get_by_role('textbox',name='Demo resolution note').fill('Completed isolated SIMULATED scenario response; no physical danger asserted.')
                panel.get_by_role('button',name='Resolve test incident',exact=True).click()
                expect(panel.get_by_test_id('demo-incident-status')).to_have_text('RESOLVED')
                report=client.get('/incidents/'+identifier+'/report').json()
                assert {'NEW','ACKNOWLEDGED','VERIFIED','RESOLVED'}<={h['status'] for h in report['history']}
                assert report['notification_state']=='DISABLED'
                record(demo+' response transition NEW → ACKNOWLEDGED → VERIFIED → RESOLVED',{'id':identifier,'resolved_by':report['resolved_by']})
                panel.get_by_role('button',name='View synchronized Incident Review',exact=True).click()
                expect(page.get_by_text('#'+identifier[:8],exact=True)).to_be_visible()
                expect(page.get_by_text('RESOLVED',exact=True).first).to_be_visible()
                record(demo+' Incident Review retains canonical resolved history',identifier[:8])
                panel=enter(demo);controls=page.get_by_test_id('tracking-playback-controls')
                panel.get_by_role('button',name='View synchronized Digital Twin Map',exact=True).click()
                expect(page.locator('[data-zone-id="ZONE_TOILET_BLINDSPOT"]')).to_have_attribute('data-risk-level','LOW')
                record(demo+' Map clears active risk after resolution','LOW')
                panel=enter(demo);controls=page.get_by_test_id('tracking-playback-controls')
            # Direct SOS still uses the existing stable run, with no model dependency or duplicate.
            before=len(client.get('/state').json()['incidents'])
            panel.get_by_role('button',name='Replay same test SOS request',exact=True).click()
            expect(panel.get_by_test_id('private-demo-progress')).to_contain_text('Test signals saved')
            assert len(client.get('/state').json()['incidents'])==before
            record('Direct test SOS request is idempotent after resolution',{'incidents':before})
            scene=page.get_by_test_id('private-twin-scene');scene.screenshot(path=str(OUT/'connected-sos.png'))
            # Real offline models run through the existing worker API/UI; no mocked score.
            source=page.get_by_test_id('normalized-sensor-panel');source.get_by_role('combobox',name='Source mode').select_option('RECORDED_REPLAY')
            recorded=page.get_by_test_id('recorded-private-evidence')
            for source_id in ('radar_raw_fall','acoustic_scream'):
                recorded.get_by_role('combobox',name='Recorded private evidence input').select_option(source_id)
                recorded.get_by_role('button',name='Run actual registered inference',exact=True).click()
                expect(recorded.get_by_test_id('recorded-evidence-result')).to_contain_text('COMPLETED',timeout=200000)
                expect(recorded.get_by_test_id('recorded-evidence-result')).to_contain_text('Actual model score')
                runs=client.get('/testing/runs').json();run=next(r for r in runs if r['scenario_id']==source_id)
                detail=client.get('/testing/runs/'+run['id']).json();result=detail['result']
                assert result['output_origin']=='fresh_raw_input_inference' and len(result['input_sha256'])==64
                event=next(e for e in client.get('/state').json()['events'] if e['id']==result['event_delivery']['event_id'])
                assert event['source_type']=='RECORDED SENSOR REPLAY' and event['processing_mode']=='real_model' and event['is_test']
                if result['event_delivery']['incident_id']:
                    saved=client.get('/incidents/'+result['event_delivery']['incident_id']+'/report').json();assert saved['level']=='OBSERVE'
                record('Actual registered '+source_id+' inference',{'score':result['score'],'candidate':result['candidate_detected'],'sha256':result['input_sha256'],'model':result['model_version'],'event':event['id']})
            expect(page.get_by_test_id('private-twin-scene')).to_have_attribute('data-positioned-occupants','0')
            expect(recorded).to_contain_text('not a synchronized fall-plus-impact recording')
            assert page.evaluate('window.captureCalls')==0 and not errors,errors
            record('Recorded evidence has no fabricated tracks/fusion; no browser errors or capture',{'positioned_tracks':0,'capture_calls':0,'browser_errors':errors})
            ROWS.append({'test':'External Telegram delivery / recipient receipt','status':'NOT_RUN','actual':'External sending disabled; actual DISABLED backend status verified. No delivery or receipt claimed.'})
            browser.close()
    except Exception as error:
        ROWS.append({'test':'Connected browser workflow','status':'FAIL','actual':str(error),'trace':traceback.format_exc()})
        raise
    finally:
        (OUT/'results.json').write_text(json.dumps(ROWS,indent=2),encoding='utf-8')
        client.close()
        for proc,log in reversed(PROCESSES):
            proc.terminate()
            try:proc.wait(timeout=8)
            except subprocess.TimeoutExpired:proc.kill();proc.wait()
            log.close()
