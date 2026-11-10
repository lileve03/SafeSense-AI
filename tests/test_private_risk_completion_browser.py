"""Real Chromium/FastAPI/SQLite completion policy; external notifications disabled."""
import base64,json,os,shutil,sqlite3,subprocess,sys,tempfile,time,traceback
from pathlib import Path
import httpx
from playwright.sync_api import sync_playwright,expect

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'runtime/private-risk-completion';OUT.mkdir(parents=True,exist_ok=True)
B='http://127.0.0.1:18830';D='http://127.0.0.1:3001';TOKEN='risk-completion-browser'
rows=[];children=[]
def record(name,actual):
    rows.append(dict(test=name,status='PASS',actual=actual));print('PASS',name,flush=True)
    (OUT/'results.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')

with tempfile.TemporaryDirectory() as temp:
    dbpath=Path(temp)/'risk.sqlite3'
    env={**os.environ,'SAFESENSE_DB_PATH':str(dbpath),'TELEGRAM_MODE':'disabled','TELEGRAM_STAFF_DISPATCH_ENABLED':'false',
         'SAFESENSE_API_TOKEN':TOKEN,'VITE_SAFESENSE_API_TOKEN':TOKEN,'VITE_API_BASE_URL':B,'VITE_AI_BASE_URL':'http://127.0.0.1:18832'}
    client=httpx.Client(base_url=B,headers={'X-SafeSense-Token':TOKEN},timeout=10)
    try:
        for name,cmd,cwd,url in [
            ('backend',[str(ROOT/'.venv/Scripts/python.exe'),'-m','uvicorn','backend.main:app','--host','127.0.0.1','--port','18830'],ROOT,B+'/health'),
            ('frontend',[shutil.which('node'),str(ROOT/'dashboard/node_modules/vite/bin/vite.js'),'--host','127.0.0.1','--port','3001','--strictPort'],ROOT/'dashboard',D)]:
            log=(OUT/(name+'.log')).open('w',encoding='utf-8')
            child=subprocess.Popen(cmd,cwd=cwd,env=env,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW);children.append((child,log))
            for _ in range(150):
                if child.poll() is not None:raise RuntimeError(name+' exited')
                try:
                    if httpx.get(url,timeout=1).status_code==200:break
                except httpx.HTTPError:pass
                time.sleep(.2)
            else:raise RuntimeError(name+' startup timeout')
        historical=client.post('/event',json={'zone':'ZONE_TOILET_BLINDSPOT','type':'sos','source':'simulation','sensor_modality':'sos',
            'source_type':'SIMULATION','processing_mode':'simulation','is_test':True,'event_id':'unrelated-old-sos','analysis_run_id':'unrelated-old-run'}).json()['incident']['id']
        with sync_playwright() as pw:
            browser=pw.chromium.launch(headless=True,args=['--enable-unsafe-swiftshader'])
            page=browser.new_page(viewport={'width':1600,'height':1600});page.set_default_timeout(25000)
            errors=[];review_requests=[];page.on('pageerror',lambda e:errors.append(str(e)))
            page.on('request',lambda r:review_requests.append(r.url) if r.method=='POST' and r.url.endswith('/review') else None)
            page.goto(D);page.locator('aside').get_by_role('button',name='Digital Twin Map',exact=True).click()
            page.locator('[data-zone-id="ZONE_TOILET_BLINDSPOT"] polygon').first.click()
            guide=page.get_by_test_id('guided-private-demo');renderer=page.get_by_test_id('private-three-renderer')
            def stats():return json.loads(renderer.get_attribute('data-tracking'))
            def visible_red(name):
                scene=stats()
                assert scene['coverageColor']==scene['coneColor']==scene['radarHaloColor']==scene['riskAccent']=='ef4444',scene
                assert scene['coneOpacity']>=.1 and scene['coverageOpacity']>=.2
                # Inspect the actual Chromium screenshot, not just material uniforms.
                encoded=base64.b64encode(renderer.screenshot()).decode()
                pixels=page.evaluate('''async encoded=>{
                    const image=await createImageBitmap(await (await fetch('data:image/png;base64,'+encoded)).blob());
                    const canvas=new OffscreenCanvas(image.width,image.height),ctx=canvas.getContext('2d');ctx.drawImage(image,0,0);
                    const data=ctx.getImageData(0,0,image.width,image.height).data;let red=0,green=0;
                    for(let i=0;i<data.length;i+=4){const r=data[i],g=data[i+1],b=data[i+2];
                      if(r>g*1.25&&r>b*1.25&&r>120)red++;
                      if(g>r*1.25&&g>b*1.25&&g>120)green++;}
                    return {red,green};
                }''',encoded)
                assert pixels['red']>10000 and pixels['red']>pixels['green']*5,pixels
                record(name,pixels)
            def wait_high():
                page.wait_for_function('(()=>{const s=JSON.parse(document.querySelector("[data-testid=private-three-renderer]").dataset.tracking);const a=s.avatars.find(a=>a.id==="T01");return s.visualRisk==="HIGH"&&s.radarAccent==="ef4444"&&s.riskAccent==="ef4444"&&a?.color==="ef4444"&&a.groundColor==="ef4444"&&a.fallProgress===1})()')
                expect(page.get_by_test_id('private-risk-status')).to_contain_text('HIGH')
            def counts():
                state=client.get('/state').json();return len(state['events']),len(state['incidents'])
            expect(page.get_by_test_id('private-status-panel').locator('dl > div').filter(has_text='Actual Backend Assessment')).to_contain_text('Unavailable')
            record('Absent backend assessment is unavailable independently of scenario risk','Unavailable; no result fabricated')
            guide.get_by_role('combobox',name='Guided scenario').select_option('fall')
            guide.get_by_role('combobox',name='Guided playback speed').select_option('2')
            guide.get_by_role('button',name='Start guided demo',exact=True).click()
            expect(guide.get_by_test_id('backend-scenario-assessment')).to_contain_text('HIGH',timeout=25000)
            page.wait_for_function('JSON.parse(document.querySelector("[data-testid=private-three-renderer]").dataset.tracking).time>=13')
            guide.get_by_role('button',name='Pause guided demo',exact=True).click();wait_high()
            before=stats();identifier=before['incidentId'];assert identifier and identifier!=historical
            report=client.get('/incidents/'+identifier+'/report').json();assert report['level']=='HIGH' and report['status']=='NEW'
            assert {e['type'] for e in report['evidence']}=={'fall','impact'}
            page.screenshot(path=str(OUT/'before-completion.png'),full_page=True)
            visible_red('Rendered floor and coverage pixels are visibly red before completion')
            record('Fall creates the matching HIGH incident; room/radar/avatar/ground are consistently red before completion',{'id':identifier,'status':report['status'],'colors':{k:before[k] for k in ('visualRisk','riskAccent','radarAccent','ambientColor')}})
            paused=stats()['time'];page.wait_for_timeout(500);assert stats()['time']==paused
            assert stats()['playbackStatus']=='Paused';wait_high()
            record('Pause retains risk, pose and coordinates',{'time':paused,'fall':1})
            response=client.post('/incidents/'+identifier+'/ack',json={'staff':'Risk completion test operator'});response.raise_for_status()
            expect(page.get_by_test_id('scenario-response-status')).to_have_text('ACKNOWLEDGED');wait_high()
            record('Acknowledgement does not resolve or turn the scene green','ACKNOWLEDGED / HIGH')
            guide.get_by_role('combobox',name='Guided playback speed').select_option('4')
            guide.get_by_role('button',name='Start guided demo',exact=True).click()
            expect(guide.get_by_test_id('guided-demo-progress')).to_contain_text('Completed',timeout=25000)
            wait_high();after=stats()
            assert after['time']==40 and after['playbackStatus']=='Completed'
            assert after['positions']==before['positions'] and after['active']==2
            assert after['ambientColor']==before['ambientColor']
            report=client.get('/incidents/'+identifier+'/report').json()
            assert report['status']=='ACKNOWLEDGED' and not review_requests
            page.screenshot(path=str(OUT/'after-completion.png'),full_page=True)
            visible_red('Rendered floor and coverage pixels remain red after completion')
            record('Natural playback completion holds HIGH, fall pose and identical red accents; no automatic resolution',{'time':40,'id':identifier,'incident_status':report['status'],'risk':after['visualRisk'],'avatar':after['avatars'][0]['color'],'radar':after['radarAccent']})
            details=page.get_by_test_id('private-track-details');details.locator(':scope > summary').click()
            slider=page.get_by_role('slider',name='Tracking playback time',exact=True);slider.focus();slider.press('End')
            wait_high();assert stats()['time']==40;details.locator(':scope > summary').click()
            record('Seek to the last frame retains HIGH and the completed fall pose','Completed / HIGH')
            before_restart=counts()
            guide.get_by_role('button',name='Restart guided demo',exact=True).click()
            guide.get_by_role('button',name='Pause guided demo',exact=True).click()
            expect(page.get_by_test_id('private-risk-status')).to_contain_text('LOW')
            assert stats()['visualEpoch']!=before['visualEpoch'] and all(a['fallProgress']==0 for a in stats()['avatars'])
            assert counts()==before_restart and client.get('/incidents/'+identifier+'/report').json()['status']=='ACKNOWLEDGED'
            page.screenshot(path=str(OUT/'restarted.png'),full_page=True)
            record('Restart resets visual epoch and pose while leaving historical incident untouched',before_restart)
            guide.get_by_role('combobox',name='Guided scenario').select_option('normal')
            guide.get_by_role('button',name='Start guided demo',exact=True).click()
            expect(guide.get_by_test_id('backend-scenario-assessment')).to_contain_text('LOW')
            guide.get_by_role('button',name='Pause guided demo',exact=True).click()
            expect(page.get_by_test_id('private-risk-status')).to_contain_text('LOW')
            assert stats()['visualRisk']=='LOW' and all(a['riskLevel']=='LOW' for a in stats()['avatars'])
            assert client.get('/incidents/'+historical+'/report').json()['level']=='CRITICAL'
            assert client.get('/incidents/'+identifier+'/report').json()['level']=='HIGH'
            page.screenshot(path=str(OUT/'normal-presence.png'),full_page=True)
            record('Normal Presence ignores unrelated CRITICAL and historical HIGH incidents','LOW; historical records retained')
            assert stats()['coverageColor']==stats()['coneColor']=='22c55e'
            for demo,assessment,level,color in [('possible_fall','OBSERVE','HIGH','ef4444'),('sos','CRITICAL','CRITICAL','fb3148')]:
                guide.get_by_role('combobox',name='Guided scenario').select_option(demo)
                guide.get_by_role('combobox',name='Guided playback speed').select_option('4')
                guide.get_by_role('button',name='Start guided demo',exact=True).click()
                expect(guide.get_by_test_id('backend-scenario-assessment')).to_contain_text(assessment)
                # SOS backend creation is immediate; its visual cue occurs at t=5.
                # Wait for the scenario clock rather than using HTTP completion as its phase.
                page.wait_for_function('(risk)=>JSON.parse(document.querySelector("[data-testid=private-three-renderer]").dataset.tracking).visualRisk===risk',arg=level)
                guide.get_by_role('button',name='Pause guided demo',exact=True).click()
                page.wait_for_function('(color)=>{const s=JSON.parse(document.querySelector("[data-testid=private-three-renderer]").dataset.tracking);return s.coverageColor===color&&s.coneColor===color&&s.radarHaloColor===color}',arg=color)
                assert stats()['visualRisk']==level
                page.screenshot(path=str(OUT/(demo+'-lighting.png')),full_page=True)
                record(demo+' visual risk is separate from backend assessment',{'risk':level,'backend':assessment,'color':color,'incident':stats()['incidentId']})
                if demo=='possible_fall':
                    panel=page.get_by_test_id('private-status-panel')
                    expect(panel).to_contain_text('Possible Fall - Review Required')
                    expect(panel.locator('dl > div').filter(has_text='Fall Status').locator('dd')).to_have_text('Possible Fall')
                    expect(panel.locator('dl > div').filter(has_text='Acoustic Status').locator('dd')).to_have_text('Quiet')
                    expect(page.get_by_test_id('private-sos-status')).to_have_text('Inactive')
                    old_counts=counts()
                    guide.get_by_role('button',name='Start guided demo',exact=True).click()
                    expect(guide.get_by_test_id('guided-demo-progress')).to_contain_text('Completed',timeout=25000)
                    wait_high();visible_red('Possible Fall completion holds red avatar, ground, room and radar')
                    page.screenshot(path=str(OUT/'possible-fall-completed.png'),full_page=True)
                    guide.get_by_role('button',name='Restart guided demo',exact=True).click()
                    guide.get_by_role('button',name='Pause guided demo',exact=True).click()
                    assert stats()['visualRisk']=='LOW' and all(a['fallProgress']==0 for a in stats()['avatars'])
                    record('Possible Fall Restart clears only visual review state',counts())
                    details.locator(':scope > summary').click();slider.fill('40');details.locator(':scope > summary').click();wait_high()
                    page.get_by_role('button',name='Reset Test State',exact=True).click()
                    page.wait_for_function('JSON.parse(document.querySelector("[data-testid=private-three-renderer]").dataset.tracking).visualRisk==="LOW"')
                    assert counts()==old_counts
                    record('Reset Test State clears Possible Fall review without deleting incidents',old_counts)
                    guide.get_by_role('combobox',name='Guided scenario').select_option('possible_fall')
                    details.locator(':scope > summary').click();slider.fill('40');details.locator(':scope > summary').click();wait_high()
                    guide.get_by_role('combobox',name='Guided scenario').select_option('normal')
                    page.wait_for_function('JSON.parse(document.querySelector("[data-testid=private-three-renderer]").dataset.tracking).coverageColor==="22c55e"')
                    assert stats()['visualRisk']=='LOW' and all(a['fallProgress']==0 for a in stats()['avatars'])
                    page.screenshot(path=str(OUT/'possible-fall-to-normal.png'),full_page=True)
                    record('Switch Possible Fall to Normal Presence restores green','LOW / 22c55e')
            guide.get_by_role('combobox',name='Guided scenario').select_option('fall')
            guide.get_by_role('button',name='Start guided demo',exact=True).click()
            details.locator(':scope > summary').click();slider.focus();slider.press('End');details.locator(':scope > summary').click()
            wait_high()
            response=client.post('/incidents/'+identifier+'/review',json={'status':'RESOLVED','staff':'Risk completion test operator','note':'Explicit completion of the simulated response; no hardware arrival asserted.'});response.raise_for_status()
            expect(page.get_by_test_id('scenario-response-status')).to_have_text('RESOLVED')
            wait_high()
            with sqlite3.connect(dbpath) as db:
                saved=json.loads(db.execute("SELECT body FROM records WHERE kind='incident' AND id=?",(identifier,)).fetchone()[0])
            db.close();assert saved['status']=='RESOLVED' and saved['acknowledged_by']=='Risk completion test operator'
            page.screenshot(path=str(OUT/'explicitly-resolved.png'),full_page=True)
            record('Linked resolution updates SQLite but cannot cancel simulated HIGH visuals','RESOLVED / HIGH')
            page.screenshot(path=str(OUT/'resolved-history-high.png'),full_page=True)
            guide.get_by_role('button',name='Restart guided demo',exact=True).click()
            guide.get_by_role('button',name='Pause guided demo',exact=True).click()
            expect(page.get_by_test_id('scenario-response-status')).to_have_text('RESOLVED')
            assert stats()['visualRisk']=='LOW' and stats()['avatars'][0]['fallProgress']==0
            page.screenshot(path=str(OUT/'resolved-replay-start.png'),full_page=True)
            details.locator(':scope > summary').click();slider.fill('8.6');details.locator(':scope > summary').click()
            page.wait_for_function('JSON.parse(document.querySelector("[data-testid=private-three-renderer]").dataset.tracking).visualRisk==="WARNING"')
            assert 0<stats()['avatars'][0]['fallProgress']<1
            page.screenshot(path=str(OUT/'resolved-replay-falling.png'),full_page=True)
            details.locator(':scope > summary').click();slider.fill('40');details.locator(':scope > summary').click()
            wait_high();visible_red('Resolved cached replay retains red completion visuals')
            expect(page.get_by_test_id('private-status-panel')).to_contain_text('Simulated distress')
            expect(page.get_by_test_id('private-status-panel')).to_contain_text('Simulated fall')
            expect(page.get_by_test_id('private-status-panel')).to_contain_text('Actual Backend Assessment')
            page.screenshot(path=str(OUT/'resolved-replay-completed.png'),full_page=True)
            assert client.get('/incidents/'+identifier+'/report').json()['status']=='RESOLVED'
            record('Restart and seek of resolved history show start, falling and HIGH completion without modifying incident','LOW / WARNING / HIGH; RESOLVED unchanged')
            guide.get_by_role('combobox',name='Source mode').select_option('LIVE_HARDWARE')
            expect(page.get_by_test_id('private-risk-status')).to_contain_text('Unavailable')
            page.wait_for_function('JSON.parse(document.querySelector("[data-testid=private-three-renderer]").dataset.tracking).visualRisk==="UNAVAILABLE"')
            assert stats()['radarAccent']=='94a3b8'
            guide.get_by_role('combobox',name='Source mode').select_option('RECORDED_REPLAY')
            expect(page.get_by_test_id('private-risk-status')).to_have_attribute('data-radar-availability','Missing')
            expect(page.get_by_test_id('private-status-panel').locator('dl > div').filter(has_text='Radar Status')).to_contain_text('Unavailable')
            page.screenshot(path=str(OUT/'radar-unavailable.png'),full_page=True)
            record('Disconnected or missing radar is unavailable/neutral rather than Normal/green','UNAVAILABLE / 94a3b8')
            assert not errors,errors;assert page.locator('canvas').count()==1
            record('Existing single canvas retained with no browser errors',errors)
            browser.close()
    except Exception as exc:
        rows.append(dict(test='Risk completion browser integration',status='FAIL',actual=str(exc),trace=traceback.format_exc()));raise
    finally:
        (OUT/'results.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
        client.close()
        for child,log in reversed(children):
            child.terminate()
            try:child.wait(timeout=8)
            except subprocess.TimeoutExpired:child.kill();child.wait()
            log.close()
