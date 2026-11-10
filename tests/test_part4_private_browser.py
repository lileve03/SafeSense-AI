"""Real Chromium + FastAPI + SQLite; synthetic scenarios, no external dispatch."""
import json, os, shutil, subprocess, sys, tempfile, time, traceback
from pathlib import Path
import httpx
from playwright.sync_api import sync_playwright, expect

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
OUT=ROOT/'runtime/part4-private';OUT.mkdir(parents=True,exist_ok=True)
B='http://127.0.0.1:18830';D='http://127.0.0.1:3001';TOKEN='part4-browser'
rows=[];children=[]
def record(name,actual):
    rows.append(dict(test=name,status='PASS',actual=actual));print('PASS',name,flush=True)
    (OUT/'browser-results.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')

with tempfile.TemporaryDirectory() as temp:
    env={**os.environ,'SAFESENSE_DB_PATH':str(Path(temp)/'part4.sqlite3'),'TELEGRAM_MODE':'disabled',
         'TELEGRAM_STAFF_DISPATCH_ENABLED':'false','SAFESENSE_API_TOKEN':TOKEN,
         'VITE_SAFESENSE_API_TOKEN':TOKEN,'VITE_API_BASE_URL':B,'VITE_AI_BASE_URL':'http://127.0.0.1:18832'}
    client=httpx.Client(base_url=B,headers={'X-SafeSense-Token':TOKEN},timeout=10)
    try:
        for name,cmd,cwd,url in [
            ('backend',[str(ROOT/'.venv/Scripts/python.exe'),'-m','uvicorn','backend.main:app','--host','127.0.0.1','--port','18830'],ROOT,B+'/health'),
            ('frontend',[shutil.which('node'),str(ROOT/'dashboard/node_modules/vite/bin/vite.js'),'--host','127.0.0.1','--port','3001','--strictPort'],ROOT/'dashboard',D)]:
            log=(OUT/(name+'.log')).open('w',encoding='utf-8')
            process=subprocess.Popen(cmd,cwd=cwd,env=env,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
            children.append((process,log))
            for _ in range(150):
                if process.poll() is not None:raise RuntimeError(name+' exited')
                try:
                    if httpx.get(url,timeout=1).status_code==200:break
                except httpx.HTTPError:pass
                time.sleep(.2)
            else:raise RuntimeError(name+' startup timeout')
        with sync_playwright() as pw:
            browser=pw.chromium.launch(headless=True,args=['--enable-unsafe-swiftshader'])
            page=browser.new_page(viewport={'width':1600,'height':1100});page.set_default_timeout(25000)
            errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
            page.add_init_script("window.captureCalls=0;if(navigator.mediaDevices)navigator.mediaDevices.getUserMedia=async()=>{window.captureCalls++;throw Error('Capture forbidden')}")
            page.goto(D)
            def enter():
                page.locator('aside').get_by_role('button',name='Digital Twin Map',exact=True).click()
                if page.get_by_test_id('private-monitoring-view').count()==0:
                    page.locator('[data-zone-id="ZONE_TOILET_BLINDSPOT"] polygon').first.click()
                return page.get_by_test_id('guided-private-demo')
            guide=enter();renderer=page.get_by_test_id('private-three-renderer')
            expect(page.get_by_test_id('private-twin-scene').locator('canvas')).to_be_visible()
            assert guide.get_by_role('combobox',name='Guided scenario').locator('option').count()==6
            assert page.locator('canvas').count()==1
            record('Six scenarios in one original Three.js room',6)
            root=page.get_by_test_id('private-monitoring-view')
            assert not page.get_by_test_id('private-technical-details').evaluate('(e)=>e.open')
            assert not page.get_by_test_id('private-track-details').evaluate('(e)=>e.open')
            assert not guide.get_by_test_id('guided-workflow-details').evaluate('(e)=>e.open')
            toolbar=page.get_by_test_id('private-demo-toolbar')
            controls=[toolbar.get_by_role('combobox',name=name) for name in ('Source mode','Guided scenario','Guided playback speed')]
            controls += [toolbar.get_by_role('button',name=name,exact=True) for name in ('Start guided demo','Restart guided demo','ACTIVATE SOS EMERGENCY')]
            ys=[control.bounding_box()['y'] for control in controls]
            assert max(ys)-min(ys)<3,ys
            left=page.get_by_test_id('private-zone-panel').bounding_box()
            center=page.get_by_test_id('private-scene-panel').bounding_box()
            right=page.get_by_test_id('private-status-panel').bounding_box()
            assert left['x']<center['x']<right['x'] and center['width']>max(left['width'],right['width'])
            page.screenshot(path=str(OUT/'private-ui-desktop.png'),full_page=True)
            record('Compact single-row toolbar, dominant center column and collapsed details',{'toolbar_y':ys,'column_widths':[left['width'],center['width'],right['width']]})
            for demo,level in [('normal','LOW'),('proximity','LOW'),('repetitive','OBSERVE'),('possible_fall','OBSERVE'),('fall','HIGH'),('sos','CRITICAL')]:
                guide.get_by_role('combobox',name='Guided scenario').select_option(demo)
                guide.get_by_role('combobox',name='Guided playback speed').select_option('2')
                before=client.get('/state').json();before_ids={i['id'] for i in before['incidents']}
                guide.get_by_role('button',name='Start guided demo',exact=True).click()
                expect(guide.get_by_test_id('backend-scenario-assessment')).to_contain_text(level,timeout=25000)
                page.wait_for_function('(risk)=>JSON.parse(document.querySelector("[data-testid=private-three-renderer]").dataset.tracking).visualRisk===risk',arg='HIGH' if demo=='possible_fall' else level)
                guide.get_by_role('button',name='Pause guided demo',exact=True).click()
                snapshot=client.get('/state').json();added=[i for i in snapshot['incidents'] if i['id'] not in before_ids]
                print('SCENARIO',demo,guide.get_by_test_id('guided-demo-progress').text_content(),flush=True)
                assert len(added)==(0 if level=='LOW' else 1),(demo,added)
                expect(page.get_by_test_id('private-risk-status')).to_contain_text('HIGH' if demo=='possible_fall' else level)
                expect(page.get_by_test_id('private-risk-status')).to_have_attribute('title','Simulated scenario risk; independent of backend response')
                page.wait_for_function('(risk)=>JSON.parse(document.querySelector("[data-testid=private-three-renderer]").dataset.tracking).visualRisk===risk',arg='HIGH' if demo=='possible_fall' else level)
                stats=json.loads(renderer.get_attribute('data-tracking'))
                assert len(stats['labelRects'])<=2,stats['labelRects']
                if demo=='fall':
                    page.screenshot(path=str(OUT/'private-ui-fall.png'),full_page=True)
                    page.get_by_role('button',name='Open Incident',exact=True).click()
                    expect(page.get_by_role('button',name='Close',exact=True)).to_be_visible()
                    page.get_by_role('button',name='Close',exact=True).click()
                    track_details=page.get_by_test_id('private-track-details')
                    track_details.locator(':scope > summary').click()
                    page.get_by_role('checkbox',name='Motion trails',exact=True).uncheck()
                    page.get_by_role('checkbox',name='Motion trails',exact=True).check()
                    page.get_by_role('checkbox',name='Radar coverage',exact=True).uncheck()
                    page.get_by_role('checkbox',name='Radar coverage',exact=True).check()
                    page.get_by_role('button',name='Select simulated track T02',exact=True).click()
                    expect(page.get_by_test_id('selected-track-information')).to_contain_text('T02')
                    track_details.locator(':scope > summary').click()
                    page.get_by_title('Toggle sensor labels',exact=True).click()
                    page.get_by_role('button',name='Inspect acoustic sensor',exact=True).click()
                    page.wait_for_timeout(300)
                    label_stats=json.loads(renderer.get_attribute('data-tracking'))
                    sensor_labels=[r for r in label_stats['reservedLabelRects'] if r['id'].startswith('sensor:')]
                    assert len(sensor_labels)==1 and sensor_labels[0]['id']=='sensor:acoustic'
                    assert len(label_stats['labelRects'])+len(sensor_labels)<=2
                    page.get_by_title('Toggle sensor labels',exact=True).click()
                    page.get_by_role('button',name='Inspect acoustic sensor',exact=True).click()
                    record('Open Incident and expandable track/display controls retain their actions','Modal, trails, coverage and track selection')
                event=snapshot['events'][0];assert event['observed_at'] and event['is_test'] and event['source_type']=='SIMULATION'
                assert event['processing_mode']=='simulation' and event['score'] is None
                identifier=added[0]['id'] if added else None
                record(demo+' scenario risk and backend result are displayed independently',{'risk':level,'incident':identifier})
                if identifier:
                    page.get_by_role('button',name='Return to campus map',exact=True).click()
                    zone=page.locator('[data-zone-id="ZONE_TOILET_BLINDSPOT"]')
                    expect(zone).to_have_attribute('data-risk-level',level)
                    assert identifier in next(z for z in client.get('/zones').json() if z['id']=='ZONE_TOILET_BLINDSPOT')['active_incident_ids']
                    guide=enter()
                    guide.get_by_role('combobox',name='Guided scenario').select_option(demo)
                    record(demo+' Digital Twin Map shares canonical active incident',identifier)
                # Polling and restart replay exactly the same durable run.
                counts=(len(snapshot['events']),len(snapshot['incidents']))
                guide.get_by_role('button',name='Restart guided demo',exact=True).click()
                page.wait_for_timeout(400)
                guide.get_by_role('button',name='Pause guided demo',exact=True).click()
                after=client.get('/state').json();assert counts==(len(after['events']),len(after['incidents']))
                expect(page.get_by_test_id('private-risk-status')).to_contain_text('LOW')
                record(demo+' pause/restart prevents duplicates and historical risk override',counts)
                if not identifier:continue
                expect(guide.get_by_test_id('scenario-notification-state')).to_contain_text('Sending disabled')
                assert client.post('/incidents/'+identifier+'/ack',json={'staff':'Part 4 human test operator'}).status_code==200
                expect(page.get_by_test_id('scenario-response-status')).to_have_text('ACKNOWLEDGED')
                assert client.post('/incidents/'+identifier+'/review',json={'status':'VERIFIED','staff':'Part 4 human test operator','note':'Synthetic exercise reviewed'}).status_code==200
                assert client.post('/incidents/'+identifier+'/review',json={'status':'RESOLVED','staff':'Part 4 human test operator','note':'Test response complete'}).status_code==200
                expect(page.get_by_test_id('scenario-response-status')).to_have_text('RESOLVED')
                report=client.get('/incidents/'+identifier+'/report').json();assert report['notification_state']=='DISABLED'
                import sqlite3
                with sqlite3.connect(Path(temp)/'part4.sqlite3') as db:
                    saved=json.loads(db.execute("SELECT body FROM records WHERE kind='incident' AND id=?",(identifier,)).fetchone()[0])
                db.close()
                assert saved['status']=='RESOLVED' and saved['acknowledged_by']=='Part 4 human test operator'
                page.locator('aside').get_by_role('button',name='Alerts',exact=True).click()
                expect(page.get_by_text('#'+identifier[:8],exact=True).first).to_be_visible()
                page.locator('aside').get_by_role('button',name='Incident Review',exact=True).click()
                expect(page.get_by_text('#'+identifier[:8],exact=True).first).to_be_visible()
                guide=enter()
                record(demo+' staff response synchronized with SQLite, Alerts and Review',identifier)
            # Source modes reuse the room and cannot carry over synthetic people.
            selector=guide.get_by_role('combobox',name='Source mode')
            selector.select_option('LIVE_HARDWARE')
            expect(page.get_by_test_id('private-twin-scene')).to_have_attribute('data-positioned-occupants','0')
            expect(page.get_by_test_id('private-risk-status')).to_contain_text('Unavailable')
            record('LIVE_HARDWARE rejects fabricated occupancy','Hardware disconnected; zero positioned people')
            selector.select_option('RECORDED_REPLAY')
            page.get_by_test_id('private-technical-details').locator(':scope > summary').click()
            page.get_by_test_id('private-sensor-provenance').locator(':scope > summary').click()
            assert page.get_by_test_id('normalized-sensor-panel').count()==1
            recorded=page.get_by_test_id('recorded-private-evidence')
            for source_id in ('radar_raw_fall','acoustic_scream'):
                recorded.get_by_role('combobox',name='Recorded private evidence input').select_option(source_id)
                recorded.get_by_role('button',name='Run actual registered inference',exact=True).click()
                expect(recorded.get_by_test_id('recorded-evidence-result')).to_contain_text('COMPLETED',timeout=200000)
                expect(recorded.get_by_test_id('recorded-evidence-result')).to_contain_text('Actual model score')
                run=next(r for r in client.get('/testing/runs').json() if r['scenario_id']==source_id)
                result=client.get('/testing/runs/'+run['id']).json()['result']
                assert result['output_origin']=='fresh_raw_input_inference' and len(result['input_sha256'])==64
                expect(page.get_by_test_id('private-twin-scene')).to_have_attribute('data-positioned-occupants','0')
                expect(page.get_by_test_id('private-risk-status')).to_contain_text('OBSERVE')
                expect(page.get_by_test_id('scenario-response-status')).to_have_text('NEW')
                expect(page.get_by_test_id('recorded-backend-reason')).to_contain_text('single unverified safety signal')
                record(source_id+' fresh inference through real browser controls',{'score':result['score'],'model':result['model_version'],'event':result['event_delivery']['event_id']})
            assert not errors,errors
            assert page.evaluate('window.captureCalls')==0
            assert page.get_by_test_id('private-monitoring-view').locator('video,audio,img').count()==0
            page.get_by_test_id('private-technical-details').locator(':scope > summary').click()
            page.set_viewport_size({'width':1280,'height':1000})
            page.wait_for_timeout(300)
            widths=[page.get_by_test_id(name).bounding_box()['width'] for name in ('private-zone-panel','private-scene-panel','private-status-panel')]
            assert widths[1]>max(widths[0],widths[2]),widths
            assert root.evaluate('(e)=>e.scrollWidth<=e.clientWidth+1')
            record('Laptop layout retains three columns without overflow',widths)
            page.set_viewport_size({'width':768,'height':1000})
            page.wait_for_timeout(300)
            assert root.evaluate('(e)=>e.scrollWidth<=e.clientWidth+1')
            root.evaluate('(e)=>e.closest("main").scrollTo(0,0)')
            page.screenshot(path=str(OUT/'private-ui-tablet.png'),full_page=True)
            record('Small-screen layout wraps controls without overflow','Room appears first')
            page.set_viewport_size({'width':1600,'height':1100})
            page.screenshot(path=str(OUT/'part4-room.png'),full_page=True)
            record('No private capture, media elements or browser errors',{'capture_calls':0,'errors':errors})
            browser.close()
    except Exception as exc:
        rows.append(dict(test='Part 4 browser integration',status='FAIL',actual=str(exc),trace=traceback.format_exc()))
        raise
    finally:
        (OUT/'browser-results.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
        client.close()
        for process,log in reversed(children):
            process.terminate()
            try:process.wait(timeout=8)
            except subprocess.TimeoutExpired:process.kill();process.wait()
            log.close()
