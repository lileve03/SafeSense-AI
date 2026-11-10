"""Actual Chromium + FastAPI + SQLite + YAMNet. External Telegram is mocked."""
import json,os,shutil,subprocess,sys,tempfile,time,traceback
from pathlib import Path
import httpx
from playwright.sync_api import sync_playwright,expect

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'runtime/private-test-actions';OUT.mkdir(parents=True,exist_ok=True)
B='http://127.0.0.1:18830';D='http://127.0.0.1:3001';TOKEN='private-test-actions-browser'
rows=[];children=[]
def record(name,actual):
    rows.append(dict(test=name,status='PASS',actual=actual));print('PASS',name,flush=True)
    (OUT/'browser-results.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')

with tempfile.TemporaryDirectory() as temp:
    route=Path(temp)/'routes.json';route.write_text(json.dumps([{'zone_id':'ZONE_TOILET_BLINDSPOT','staff':'Authorized TEST operator fixture','role':'teacher','active':True}]))
    env={**os.environ,'SAFESENSE_DB_PATH':str(Path(temp)/'actions.sqlite3'),'SAFESENSE_STAFF_ROUTES':str(route),
         'TELEGRAM_MODE':'disabled','TELEGRAM_STAFF_DISPATCH_ENABLED':'false','TELEGRAM_BOT_TOKEN':'fake-not-external',
         'TELEGRAM_TEST_CHAT_ID':'-100123','SAFESENSE_API_TOKEN':TOKEN,'VITE_SAFESENSE_API_TOKEN':TOKEN,
         'VITE_API_BASE_URL':B,'VITE_AI_BASE_URL':'http://127.0.0.1:18832'}
    client=httpx.Client(base_url=B,headers={'X-SafeSense-Token':TOKEN},timeout=10)
    try:
        for name,cmd,cwd,url in [
            ('backend',[str(ROOT/'.venv/Scripts/python.exe'),'-m','uvicorn','private_test_actions_backend:app','--app-dir','tests','--host','127.0.0.1','--port','18830'],ROOT,B+'/health'),
            ('frontend',[shutil.which('node'),str(ROOT/'dashboard/node_modules/vite/bin/vite.js'),'--host','127.0.0.1','--port','3001','--strictPort'],ROOT/'dashboard',D)]:
            log=(OUT/(name+'.log')).open('w',encoding='utf-8')
            proc=subprocess.Popen(cmd,cwd=cwd,env=env,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW);children.append((proc,log))
            for _ in range(150):
                if proc.poll() is not None:raise RuntimeError(name+' exited')
                try:
                    if httpx.get(url,timeout=1).status_code==200:break
                except httpx.HTTPError:pass
                time.sleep(.2)
            else:raise RuntimeError(name+' startup timeout')
        with sync_playwright() as pw:
            browser=pw.chromium.launch(headless=True,args=['--enable-unsafe-swiftshader'])
            def page_for(telegram='disabled',available=False,behavior='accepted'):
                response=client.post('/__test__/configuration',json={'telegram_mode':telegram,'acoustic_available':available,'behavior':behavior});response.raise_for_status()
                context=browser.new_context(viewport={'width':1600,'height':1600})
                page=context.new_page();page.set_default_timeout(20000)
                page.add_init_script("window.captureCalls=0;if(navigator.mediaDevices)navigator.mediaDevices.getUserMedia=async()=>{window.captureCalls++;throw Error('Capture prohibited')};")
                page.goto(D);page.locator('aside').get_by_role('button',name='Digital Twin Map',exact=True).click()
                page.locator('[data-zone-id="ZONE_TOILET_BLINDSPOT"] polygon').first.click()
                return context,page,page.get_by_test_id('private-test-actions')
            def counts():
                snapshot=client.get('/state').json();return len(snapshot['events']),len(snapshot['incidents'])
            context,page,card=page_for(telegram='test',available=True)
            for kind in ('acoustic','sos','fusion'):expect(card.get_by_test_id('test-summary-'+kind)).to_have_text('Not Tested')
            expect(card.get_by_test_id('test-summary-telegram')).to_have_text('Configured')
            record('Initial test statuses and authorized test configuration','Not Tested / Configured; transport mocked')
            errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
            renderer=page.get_by_test_id('private-three-renderer')
            def stats():return json.loads(renderer.get_attribute('data-tracking'))
            def metric(label):return page.get_by_test_id('private-status-panel').locator('dl > div').filter(has_text=label).locator('dd')
            page.evaluate('window.originalTestCanvas=document.querySelector("[data-testid=private-three-renderer] canvas")')
            guide=page.get_by_test_id('guided-private-demo')
            guide.get_by_role('button',name='Start guided demo',exact=True).click()
            page.wait_for_function('JSON.parse(document.querySelector("[data-testid=private-three-renderer]").dataset.tracking).active>0')
            card.get_by_role('button',name='Run Acoustic Test',exact=True).click()
            expect(card.get_by_test_id('test-status-acoustic')).to_have_text('Running')
            expect(card.get_by_role('button',name='Run Acoustic Test',exact=True)).to_be_disabled()
            expect(card.get_by_test_id('test-status-acoustic')).to_have_text('Passed',timeout=200000)
            expect(card.get_by_test_id('test-source-acoustic')).to_have_text('RECORDED ACOUSTIC TEST')
            expect(card.get_by_test_id('test-detected-acoustic')).to_have_text('scream')
            expect(card.get_by_test_id('test-acoustic-notification')).to_have_text('Notification unavailable')
            expect(page.get_by_test_id('private-risk-status')).to_contain_text('OBSERVE')
            expect(page.get_by_test_id('scene-test-source')).to_contain_text('RECORDED ACOUSTIC TEST')
            page.wait_for_function('JSON.parse(document.querySelector("[data-testid=private-three-renderer]").dataset.tracking).acousticEmission>0')
            first_pulse=stats();page.wait_for_timeout(300);second_pulse=stats()
            assert first_pulse['highlightedSensors']==['acoustic'] and second_pulse['active']==0
            assert first_pulse['pulsePhase']!=second_pulse['pulsePhase']
            assert first_pulse['acousticEmission']!=second_pulse['acousticEmission']
            assert first_pulse['sourceMode']=='RECORDED_REPLAY' and first_pulse['visualRisk']=='OBSERVE'
            expect(guide.get_by_role('button',name='Start guided demo',exact=True)).to_be_disabled()
            run=next(r for r in client.get('/testing/runs').json() if r['scenario_id']=='acoustic_scream')
            actual=client.get('/testing/runs/'+run['id']).json()['result']
            assert actual['output_origin']=='fresh_raw_input_inference' and actual['candidate_detected']
            assert stats()['incidentId']==actual['event_delivery']['incident_id']
            expect(metric('Acoustic Status')).to_have_text('scream')
            expect(page.get_by_test_id('private-event-timeline')).to_contain_text('single unverified safety signal')
            assert all(e['source_type']=='RECORDED SENSOR REPLAY' for e in client.get('/state').json()['events'])
            page.screenshot(path=str(OUT/'scene-acoustic.png'),full_page=True)
            record('Visible acoustic pulse, recorded source, OBSERVE risk, same incident; no invented people',{'score':actual['score'],'incident':stats()['incidentId'],'acousticEmission':[first_pulse['acousticEmission'],second_pulse['acousticEmission']],'telegram':'POLICY_SUPPRESSED'})
            record('Acoustic action executes actual registered YAMNet inference',{'score':actual['score'],'event':actual['event_delivery']['event_id']})
            before=counts();jobs=len(client.get('/testing/runs').json())
            card.get_by_role('button',name='Run Acoustic Test',exact=True).click()
            expect(card.get_by_test_id('test-status-acoustic')).to_have_text('Passed')
            expect(card.get_by_role('button',name='Run Acoustic Test',exact=True)).to_be_enabled()
            assert counts()==before and len(client.get('/testing/runs').json())==jobs
            record('Repeated recorded acoustic action reuses the completed job and incident',before)
            # All three actions drive this exact canvas/controller in sequence.
            card.get_by_role('button',name='Run Fusion Test',exact=True).click()
            page.wait_for_function('JSON.parse(document.querySelector("[data-testid=private-three-renderer]").dataset.tracking).avatars.some(a=>a.fallProgress>0&&a.fallProgress<1)')
            falling=stats();page.screenshot(path=str(OUT/'scene-fusion-falling.png'),full_page=True)
            expect(card.get_by_test_id('test-status-fusion')).to_have_text('Passed')
            expect(card.get_by_test_id('test-fusion-notification')).to_have_text('API accepted')
            page.wait_for_function('(()=>{const s=JSON.parse(document.querySelector("[data-testid=private-three-renderer]").dataset.tracking);return s.visualRisk==="HIGH"&&s.avatars.some(a=>a.fallProgress>=.999)&&s.riskAccent==="ef4444"})()')
            fused=stats();assert {'radar','acoustic'}<=set(fused['highlightedSensors'])
            assert fused['acousticEmission']>0 and fused['active']==2 and fused['distanceText']
            expect(page.get_by_test_id('private-risk-status')).to_contain_text('HIGH')
            expect(page.get_by_test_id('scene-test-source')).to_contain_text('SIMULATED FUSION TEST')
            report=client.get('/incidents/'+fused['incidentId']+'/report').json()
            assert report['level']=='HIGH' and {e['type'] for e in report['evidence']}=={'fall','impact'}
            assert report['notification_state']=='API_ACCEPTED'
            expect(metric('Fall Status')).to_have_text('Simulated fall')
            expect(metric('Acoustic Status')).to_have_text('Simulated distress')
            expect(page.get_by_test_id('private-event-timeline')).to_contain_text(report['reason'])
            page.screenshot(path=str(OUT/'scene-fusion-high.png'),full_page=True)
            record('Visible faceless fall, radar/acoustic highlights, HIGH lighting and linked fusion incident',{'fall_progress':[falling['avatars'][0]['fallProgress'],fused['avatars'][0]['fallProgress']],'incident':fused['incidentId'],'riskAccent':fused['riskAccent'],'telegram':'API_ACCEPTED (mock transport)'})
            before_fusion_repeat=counts();fusion_sends=client.get('/__test__/transport').json()['calls']
            card.get_by_role('button',name='Run Fusion Test',exact=True).click()
            expect(card.get_by_test_id('test-status-fusion')).to_have_text('Passed')
            expect(card.get_by_role('button',name='Run Fusion Test',exact=True)).to_be_enabled()
            assert counts()==before_fusion_repeat and client.get('/__test__/transport').json()['calls']==fusion_sends
            record('Replaying the visible fusion does not duplicate its incident or Telegram send',fused['incidentId'])
            card.get_by_role('button',name='Run SOS Test',exact=True).click()
            expect(card.get_by_test_id('test-sos-notification')).to_have_text('API accepted')
            page.wait_for_function('(()=>{const s=JSON.parse(document.querySelector("[data-testid=private-three-renderer]").dataset.tracking);return s.testKind==="sos"&&s.visualRisk==="CRITICAL"&&s.sosDeviceEmission>0})()')
            sos_scene=stats();assert sos_scene['highlightedSensors']==['sos']
            expect(page.get_by_test_id('private-sos-status')).to_have_text('Active')
            expect(page.get_by_test_id('private-risk-status')).to_contain_text('CRITICAL')
            report=client.get('/incidents/'+sos_scene['incidentId']+'/report').json()
            assert report['level']=='CRITICAL' and report['notification_state']=='API_ACCEPTED'
            expect(page.get_by_test_id('private-event-timeline')).to_contain_text(report['reason'])
            assert page.evaluate('window.originalTestCanvas===document.querySelector("[data-testid=private-three-renderer] canvas")')
            assert page.locator('canvas').count()==1
            page.screenshot(path=str(OUT/'scene-sos.png'),full_page=True)
            record('Same canvas shows red physical SOS pulse, CRITICAL risk, linked incident and API status',{'incident':sos_scene['incidentId'],'emission':sos_scene['sosDeviceEmission'],'telegram':'API_ACCEPTED (mock transport)'})
            before=counts();send_count=client.get('/__test__/transport').json()['calls']
            card.get_by_role('button',name='Run SOS Test',exact=True).click()
            expect(card.get_by_role('button',name='Run SOS Test',exact=True)).to_be_enabled()
            assert counts()==tuple(n+1 for n in before) and client.get('/__test__/transport').json()['calls']==send_count+1
            record('Deliberate new SOS click creates one fresh incident and send',counts())
            before=counts()
            card.get_by_role('button',name='Reset Test State',exact=True).click()
            page.wait_for_function('(()=>{const s=JSON.parse(document.querySelector("[data-testid=private-three-renderer]").dataset.tracking);return s.testKind===null&&s.active===0&&s.visualRisk==="LOW"&&s.sosDeviceEmission===0})()')
            assert counts()==before
            assert all(v==0 for v in stats()['sensorHaloOpacity'].values())
            record('Reset clears scene and status without deleting incidents or resending Telegram',before)
            assert not errors and page.evaluate('window.captureCalls')==0
            context.close()

            context,page,card=page_for()
            card.get_by_role('button',name='Run Acoustic Test',exact=True).click()
            expect(card.get_by_test_id('test-status-acoustic')).to_have_text('Passed')
            expect(card.get_by_test_id('test-source-acoustic')).to_have_text('SIMULATED ACOUSTIC TEST')
            expect(card.get_by_test_id('test-detected-acoustic')).to_have_text('scream')
            event=client.get('/state').json()['events'][0]
            assert event['source_type']=='SIMULATION' and event['processing_mode']=='simulation' and event['is_test'] and event['score'] is None
            record('Unavailable recording explicitly falls back to simulated acoustic metadata',event['id'])
            card.get_by_role('button',name='Run Fusion Test',exact=True).click()
            expect(card.get_by_test_id('test-status-fusion')).to_have_text('Passed')
            expect(card.get_by_test_id('test-risk-fusion')).to_have_text('HIGH')
            fusion=next(i for i in client.get('/state').json()['incidents'] if i['level']=='HIGH')
            assert {e['type'] for e in fusion['evidence']}=={'fall','impact'}
            assert all(e['observed_at'] and e['source_type']=='SIMULATION' for e in fusion['evidence'])
            before=counts();card.get_by_role('button',name='Run Fusion Test',exact=True).click()
            expect(card.get_by_role('button',name='Run Fusion Test',exact=True)).to_be_enabled();assert counts()==before
            record('Fusion uses timestamp-compatible synthetic signals and one durable HIGH incident',fusion['id'])
            card.get_by_role('button',name='Run SOS Test',exact=True).click()
            expect(card.get_by_test_id('test-status-sos')).to_have_text('Incident Created')
            expect(card.get_by_test_id('test-sos-notification')).to_have_text('Notification unavailable')
            expect(card.get_by_test_id('test-summary-sos')).to_have_text('Passed')
            sos=next(i for i in client.get('/state').json()['incidents'] if i['level']=='CRITICAL')
            assert sos['is_test'] and sos['source_type']=='SIMULATION'
            expect(page.get_by_test_id('scenario-response-status')).to_have_text('NEW')
            card.get_by_test_id('test-incident-sos').click();expect(page.get_by_role('button',name='Close',exact=True)).to_be_visible()
            page.get_by_role('button',name='Close',exact=True).click()
            record('SOS creates and links a CRITICAL TEST incident without claiming notification',sos['id'])
            before=counts()
            card.get_by_role('button',name='Run SOS Test',exact=True).click()
            expect(card.get_by_role('button',name='Run SOS Test',exact=True)).to_be_enabled()
            page.get_by_role('button',name='ACTIVATE SOS EMERGENCY',exact=True).click()
            page.get_by_role('button',name='Confirm Test Broadcast',exact=True).click()
            expect(card.get_by_role('button',name='Run SOS Test',exact=True)).to_be_enabled()
            assert counts()==before
            record('Toolbar and card SOS share the same idempotent request',before)
            card.get_by_role('button',name='Reset Test State',exact=True).click()
            for kind in ('acoustic','sos','fusion'):expect(card.get_by_test_id('test-status-'+kind)).to_have_text('Not Tested')
            assert counts()==before
            card.get_by_role('button',name='Run SOS Test',exact=True).click()
            expect(card.get_by_test_id('test-status-sos')).to_have_text('Incident Created')
            expect(card.get_by_role('button',name='Run SOS Test',exact=True)).to_be_enabled();assert counts()==before
            page.reload();card=page.get_by_test_id('private-test-actions')
            page.locator('aside').get_by_role('button',name='Digital Twin Map',exact=True).click()
            page.locator('[data-zone-id="ZONE_TOILET_BLINDSPOT"] polygon').first.click()
            card.get_by_role('button',name='Run SOS Test',exact=True).click()
            expect(card.get_by_test_id('test-status-sos')).to_have_text('Incident Created')
            expect(card.get_by_role('button',name='Run SOS Test',exact=True)).to_be_enabled();assert counts()==before
            record('Reset and reload preserve incident IDs without deleting or duplicating SQLite records',before)
            context.close()

            for behavior,label in [('accepted','API accepted'),('failed','Failed'),('unknown','Acceptance unknown')]:
                context,page,card=page_for(telegram='test',behavior=behavior)
                expect(card.get_by_test_id('test-summary-telegram')).to_have_text('Configured')
                start=client.get('/__test__/transport').json()['calls']
                card.get_by_role('button',name='Run SOS Test',exact=True).click()
                expect(card.get_by_test_id('test-sos-notification')).to_have_text(label)
                if behavior=='accepted':expect(page.get_by_test_id('scenario-notification-state')).to_contain_text('API Accepted')
                expect(card.get_by_role('button',name='Run SOS Test',exact=True)).to_be_enabled()
                expect(card.get_by_test_id('test-summary-sos')).to_have_text('Passed')
                assert card.get_by_text('Receipt confirmed',exact=True).count()==0
                assert client.get('/__test__/transport').json()['calls']==start+1
                card.get_by_role('button',name='Run SOS Test',exact=True).click()
                expect(card.get_by_role('button',name='Run SOS Test',exact=True)).to_be_enabled()
                assert client.get('/__test__/transport').json()['calls']==start+(2 if behavior=='accepted' else 1)
                assert page.evaluate('window.captureCalls')==0
                page.screenshot(path=str(OUT/(behavior+'.png')),full_page=True)
                record('Notification rendering '+behavior+'; explicit new test separated from uncertain retry',{'label':label,'transport':'MOCKED; real backend queue/SQLite'})
                context.close()
            context,page,card=page_for()
            page.route('**/sensors/observations',lambda route:route.fulfill(status=503,content_type='application/json',body='{"detail":"Injected backend outage"}'))
            card.get_by_role('button',name='Run Acoustic Test',exact=True).click()
            expect(card.get_by_test_id('test-status-acoustic')).to_have_text('Failed')
            expect(card.get_by_test_id('test-summary-acoustic')).to_have_text('Failed')
            record('Rejected acoustic delivery renders Failed','Injected HTTP 503; no fabricated pass')
            assert page.get_by_test_id('private-monitoring-view').locator('video,audio,img').count()==0
            assert client.get('/__test__/transport').json()['all_test_recipient_only']
            record('Privacy restrictions and test-recipient isolation retained','No capture; metadata only; no external Telegram')
            context.close();browser.close()
    except Exception as exc:
        rows.append(dict(test='Private test action browser integration',status='FAIL',actual=str(exc),trace=traceback.format_exc()));raise
    finally:
        (OUT/'browser-results.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
        client.close()
        for proc,log in reversed(children):
            proc.terminate()
            try:proc.wait(timeout=8)
            except subprocess.TimeoutExpired:proc.kill();proc.wait()
            log.close()
