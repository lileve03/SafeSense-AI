"""Actual Chromium animation, selection, controls, bounded-resource and idle checks.
Isolated API/database; no changes to user incidents and no external notifications.
"""
import json,math,os,shutil,socket,subprocess,tempfile,time,traceback
from pathlib import Path
import httpx
from playwright.sync_api import sync_playwright,expect

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'runtime/interactive-tracking-checks';OUT.mkdir(parents=True,exist_ok=True)
rows=[];processes=[]
def record(name,actual):
    rows.append({'test':name,'status':'PASS','actual':actual})
    print('PASS',name,json.dumps(actual)[:500],flush=True)

with tempfile.TemporaryDirectory() as temp:
    env={**os.environ,'SAFESENSE_DB_PATH':str(Path(temp)/'tracking.sqlite3'),'TELEGRAM_MODE':'disabled',
         'TELEGRAM_STAFF_DISPATCH_ENABLED':'false','SAFESENSE_API_TOKEN':'tracking-browser-test',
         'VITE_SAFESENSE_API_TOKEN':'tracking-browser-test','VITE_API_BASE_URL':'http://127.0.0.1:18830',
         'VITE_AI_BASE_URL':'http://127.0.0.1:18832'}
    try:
        for port in (18830,3001):
            with socket.socket() as probe:probe.bind(('127.0.0.1',port))
        for name,cmd,cwd,url in [
            ('backend',[str(ROOT/'.venv/Scripts/python.exe'),'-m','uvicorn','backend.main:app','--host','127.0.0.1','--port','18830'],ROOT,'http://127.0.0.1:18830/health'),
            ('frontend',[shutil.which('node'),str(ROOT/'dashboard/node_modules/vite/bin/vite.js'),'--host','127.0.0.1','--port','3001','--strictPort'],ROOT/'dashboard','http://127.0.0.1:3001')]:
            log=(OUT/(name+'.log')).open('w',encoding='utf-8')
            proc=subprocess.Popen(cmd,cwd=cwd,env=env,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
            processes.append((proc,log))
            for _ in range(100):
                if proc.poll() is not None:raise RuntimeError(name+' exited')
                try:
                    if httpx.get(url,timeout=1).status_code==200:break
                except httpx.HTTPError:pass
                time.sleep(.2)
            else:raise RuntimeError(name+' startup timeout')
        with sync_playwright() as pw:
            browser=pw.chromium.launch(headless=True,args=['--enable-unsafe-swiftshader'])
            page=browser.new_page(viewport={'width':1600,'height':1100});page.set_default_timeout(15000)
            errors=[];page.on('pageerror',lambda error:errors.append(str(error)))
            page.add_init_script("window.captureCalls=0;if(navigator.mediaDevices)navigator.mediaDevices.getUserMedia=async()=>{window.captureCalls++;throw Error('Private capture forbidden');};")
            page.goto('http://127.0.0.1:3001')
            page.locator('aside').get_by_role('button',name='Digital Twin Map',exact=True).click()
            page.locator('[data-zone-id="ZONE_TOILET_BLINDSPOT"] polygon').first.click()
            page.get_by_role('button',name='Advanced Monitoring',exact=True).click()
            source=page.get_by_test_id('normalized-sensor-panel')
            source.get_by_role('combobox',name='Source mode').select_option('SIMULATION')
            controls=page.get_by_test_id('tracking-playback-controls');expect(controls).to_be_visible()
            scene=page.get_by_test_id('private-twin-scene');renderer=page.get_by_test_id('private-three-renderer')
            expect(scene.locator('canvas')).to_be_visible()
            def stats():return json.loads(renderer.get_attribute('data-tracking'))
            def seek(value):
                controls.get_by_role('slider',name='Tracking playback time').evaluate("(el,value)=>{Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set.call(el,String(value));el.dispatchEvent(new Event('input',{bubbles:true}));el.dispatchEvent(new Event('change',{bubbles:true}));}",value)
                page.wait_for_function('(t)=>Math.abs(JSON.parse(document.querySelector(\'[data-testid="private-three-renderer"]\').dataset.tracking).time-t)<.05',arg=value)
            page.wait_for_function("!!document.querySelector('[data-testid=private-three-renderer]').dataset.tracking")
            assert stats()['active']==0
            record('Original room remains interactive; simulation starts empty and paused',stats())
            controls.get_by_role('combobox',name='Tracking scenario').select_option('busy')
            seek(12)
            s=stats();assert s['active']==6 and s['visible']==6
            assert len(s['avatars'])==6 and all(a['schematic'] and not a['poseMeasured'] and a['color'] in ('0891b2','f59e0b') for a in s['avatars'])
            expect(controls.get_by_test_id('simulated-people-count')).to_contain_text('6')
            for pair in s['pairs']:
                a=next(t for t in s['positions'] if t['id']==pair['a']);b=next(t for t in s['positions'] if t['id']==pair['b'])
                assert abs(pair['meters']-math.dist([a['x'],a['y'],a['z']],[b['x'],b['y'],b['z']]))<1e-9
            record('Six simultaneous track IDs, derived count and exact coordinate distances',s)
            controls.get_by_role('button',name='Select simulated track T03',exact=True).click()
            expect(controls.get_by_test_id('selected-track-information')).to_contain_text('T03')
            expect(controls.get_by_test_id('selected-track-information')).to_contain_text('Speed')
            page.wait_for_function("JSON.parse(document.querySelector('[data-testid=private-three-renderer]').dataset.tracking).selectedId==='T03'")
            assert stats()['selectedId']=='T03'
            record('Track ID selection highlights marker and displays position/velocity','T03 selected')
            scene.scroll_into_view_if_needed()
            target=stats()['trackPixels'][0];bounds=renderer.bounding_box()
            page.mouse.click(bounds['x']+target['x'],bounds['y']+target['y'])
            expect(controls.get_by_role('button',name='Select simulated track T01',exact=True)).to_have_attribute('aria-pressed','true')
            record('Raycast selection works directly on 3D anonymous marker','T01 selected by canvas click')
            original_camera=renderer.get_attribute('data-camera-position')
            scene.get_by_title('Zoom In',exact=True).click()
            assert renderer.get_attribute('data-camera-position')!=original_camera
            scene.get_by_title('Zoom Out',exact=True).click()
            scene.get_by_title('Reset Orbit View',exact=True).click()
            assert renderer.get_attribute('data-camera-position')==original_camera
            bounds=renderer.bounding_box();x=bounds['x']+bounds['width']*.72;y=bounds['y']+bounds['height']*.62
            page.mouse.move(x,y);page.mouse.down();page.mouse.move(x+65,y+25,steps=8);page.mouse.up()
            assert renderer.get_attribute('data-camera-position')!=original_camera
            scene.get_by_title('Reset Orbit View',exact=True).click()
            record('Orbit drag, zoom in/out and reset preserve original camera controls',original_camera)
            controls.get_by_role('button',name='Start tracking',exact=True).click()
            page.wait_for_timeout(1250);moving=stats()
            assert moving['time']>12.5 and moving['positions']!=s['positions'] and moving['trailVertices']>6
            assert any(abs(a['legSwing'])>.001 for a in moving['avatars'])
            controls.get_by_role('button',name='Pause tracking',exact=True).click()
            page.wait_for_timeout(250);paused=stats();render_before=int(renderer.get_attribute('data-render-count'))
            page.wait_for_timeout(1000);render_after=int(renderer.get_attribute('data-render-count'))
            assert stats()['time']==paused['time'] and stats()['positions']==paused['positions']
            assert render_after-render_before<=1,(render_before,render_after)
            record('Continuous movement, bounded trails, frozen pause and demand rendering',{'trailVertices':moving['trailVertices'],'pausedRenderDelta1s':render_after-render_before})
            controls.get_by_label('Motion trails',exact=True).uncheck()
            page.wait_for_timeout(100);assert stats()['trailVertices']==0
            controls.get_by_label('Schematic radar coverage',exact=True).uncheck()
            page.wait_for_timeout(100);assert not stats()['coverage']
            controls.get_by_label('Motion trails',exact=True).check();controls.get_by_label('Schematic radar coverage',exact=True).check()
            record('Motion trails and schematic radar coverage toggle independently','both toggles passed')
            controls.get_by_role('combobox',name='Tracking playback speed').select_option('4')
            seek(10);controls.get_by_role('button',name='Start tracking',exact=True).click()
            page.wait_for_timeout(1100);fast=stats();assert 13<fast['time']<17,fast['time']
            controls.get_by_role('button',name='Pause tracking',exact=True).click()
            record('Playback speed changes simulation clock','4x: '+str(round(fast['time']-10,2))+' simulated seconds / ~1.1s wall time')
            seek(39.9);assert stats()['active']==0
            controls.get_by_role('combobox',name='Tracking playback speed').select_option('1')
            controls.get_by_role('button',name='Restart tracking',exact=True).click()
            page.wait_for_timeout(100)
            controls.get_by_role('button',name='Pause tracking',exact=True).click()
            assert stats()['time']<2,stats()['time']
            controls.get_by_role('combobox',name='Tracking scenario').select_option('crossing');seek(12)
            assert stats()['active']==2
            record('Departures clear markers, restart resets clock and scenario switches clear old tracks','0 at end; 2 in crossing scenario')
            controls.get_by_role('combobox',name='Tracking scenario').select_option('busy');seek(12)
            controls.get_by_role('combobox',name='Tracking playback speed').select_option('1')
            cdp=page.context.new_cdp_session(page);cdp.send('Performance.enable')
            before={m['name']:m['value'] for m in cdp.send('Performance.getMetrics')['metrics']}
            initial=stats();count_before=int(renderer.get_attribute('data-render-count'))
            controls.get_by_role('button',name='Start tracking',exact=True).click()
            page.wait_for_timeout(3000)
            after={m['name']:m['value'] for m in cdp.send('Performance.getMetrics')['metrics']};final=stats()
            count_after=int(renderer.get_attribute('data-render-count'))
            fps=(count_after-count_before)/3
            assert 5<=fps<=32,fps
            assert final['drawCalls']<130 and final['trailVertices']<=8*32
            assert final['textures']<=initial['textures']+1 and final['geometries']<=initial['geometries']+1
            controls.get_by_role('button',name='Pause tracking',exact=True).click()
            performance_result={'fps':round(fps,2),'drawCalls':final['drawCalls'],'triangles':final['triangles'],
                'pooledGeometriesBeforeAfter':[initial['geometries'],final['geometries']],
                'texturesBeforeAfter':[initial['textures'],final['textures']],
                'lastCpuFrameMs':round(final['cpuFrameMs'],2),
                'browserTaskSecondsOver3s':round(after['TaskDuration']-before['TaskDuration'],3),
                'browserScriptSecondsOver3s':round(after['ScriptDuration']-before['ScriptDuration'],3),
                'jsHeapMiB':round(after['JSHeapUsedSize']/1024**2,2),'renderer':'headless Chromium / SwiftShader'}
            record('Actual browser performance: capped FPS and stable GPU resource counts',performance_result)
            scene.screenshot(path=str(OUT/'six-track-simulation.png'))
            future=page.evaluate('''async()=>{
              const {observationFrame,simulationFrame}=await import('/src/components/private-area/trackingPlayback.ts');
              const {AnonymousTrackingLayer}=await import('/src/components/private-area/AnonymousTrackingLayer.ts');
              const layer=new AnonymousTrackingLayer();
              const observation={source_mode:'LIVE_HARDWARE',hardware_verified:true,device_id:'TEST_FIXTURE_ONLY_NOT_PHYSICAL',timestamp:new Date().toISOString(),data_validity:'VALID',coordinate_frame:'zone_meters_x_right_y_forward_z_up',tracks:[{id:'fixture-17',position:{x:1,y:-1,z:.6},velocity:{x:.1,y:0,z:0}}]};
              layer.update(observationFrame(observation),{trails:true,selectedId:'fixture-17'});
              const valid=structuredClone(layer.stats);
              layer.update(observationFrame({...observation,data_validity:'STALE'}),{trails:true,selectedId:null});
              const stale=layer.stats.active;layer.dispose();
              const counts=[0,2,4,6,12,32,35,40].map(time=>({time,count:simulationFrame('busy',time).tracks.length}));
              let maxSpeed=0;
              for(const scenario of ['arrivals','crossing','busy'])for(let time=0;time<=40;time+=.05){
                for(const track of simulationFrame(scenario,time).tracks){
                  const {x,y}=track.position;
                  if(Math.abs(x)>3.8||Math.abs(y)>3.4)throw Error('Track outside room');
                  if(x>1.25&&x<1.75&&y>.85)throw Error('Track crosses original partition');
                  maxSpeed=Math.max(maxSpeed,Math.hypot(track.velocity.x,track.velocity.y));
                }
              }
              return {valid,stale,counts,maxSpeed};
            }''')
            assert future['valid']['positions'][0]=={'id':'fixture-17','x':1,'y':-1,'z':.6} and future['stale']==0
            assert future['valid']['avatars'][0]['legSwing']==0 and not future['valid']['avatars'][0]['poseMeasured']
            assert [r['count'] for r in future['counts'][:5]]==[0,2,4,6,6]
            assert future['counts'][-1]['count']==0
            record('Same renderer accepts normalized future track fixtures; stale tracks clear',future)
            controls.get_by_role('combobox',name='Tracking scenario').select_option('repeated');seek(14)
            readout=controls.get_by_test_id('motion-analysis-readout')
            expect(readout.get_by_test_id('motion-rule-triggers')).to_contain_text('REPEATED_BACK_AND_FORTH')
            expect(readout).to_contain_text('not proof of fighting or bullying')
            page.wait_for_function("JSON.parse(document.querySelector('[data-testid=private-three-renderer]').dataset.tracking).highlightedTrackIds.includes('T01')")
            readout.locator('summary').click();expect(readout.get_by_role('table',name='Backend motion features')).to_be_visible()
            expect(readout.get_by_test_id('backend-motion-rules')).to_contain_text('3 reversals')
            record('Backend repeated-motion candidate shows explainable features and highlights T01',stats()['highlightedTrackIds'])
            assert next(a for a in stats()['avatars'] if a['id']=='T01')['color']=='f59e0b'
            scene.screenshot(path=str(OUT/'repeated-motion-candidate.png'))
            controls.get_by_role('combobox',name='Tracking scenario').select_option('proximity');seek(12)
            expect(readout.get_by_test_id('motion-rule-triggers')).to_contain_text('PROXIMITY_DURATION')
            expect(readout.get_by_test_id('nearest-track-distance')).to_contain_text('0.60m')
            page.wait_for_function("JSON.parse(document.querySelector('[data-testid=private-three-renderer]').dataset.tracking).highlightedTrackIds.length===2")
            record('Backend proximity duration, supported nearest distance and both track highlights',stats()['highlightedTrackIds'])
            seek(0)
            expect(readout.get_by_test_id('motion-rule-triggers')).to_contain_text('No current rule candidates')
            page.wait_for_function("JSON.parse(document.querySelector('[data-testid=private-three-renderer]').dataset.tracking).highlightedTrackIds.length===0")
            record('Seeking clears prior temporal triggers and relevant-track highlights','No candidates at empty-room start')
            controls.get_by_role('combobox',name='Tracking scenario').select_option('fall_impact');seek(10)
            signals=stats()['sensorSignals'];assert signals['fall'] and signals['impact'] and not signals['sos']
            assert next(t for t in stats()['positions'] if t['id']=='T01')['z']<.3
            expect(scene).to_contain_text('SIMULATED acoustic impact')
            assert next(a for a in stats()['avatars'] if a['id']=='T01')['color']=='ef4444'
            scene.screenshot(path=str(OUT/'avatar-fall-candidate.png'))
            controls.get_by_role('combobox',name='Tracking scenario').select_option('sos');seek(6)
            assert stats()['sensorSignals']['sos'];expect(scene).to_contain_text('SIMULATED SOS direct help request')
            record('Synthetic fall height, impact and SOS fixture indicators match 3D playback','Explicitly SIMULATED; no unarmed backend events')
            source.get_by_role('combobox',name='Source mode').select_option('LIVE_HARDWARE')
            expect(source).to_contain_text('Hardware Disconnected')
            expect(controls).to_have_count(0)
            page.wait_for_timeout(150);assert stats()['active']==0
            page.set_viewport_size({'width':430,'height':950});scene.scroll_into_view_if_needed()
            expect(scene.locator('canvas')).to_be_visible()
            assert page.evaluate('document.documentElement.scrollWidth<=window.innerWidth+1')
            assert page.evaluate('window.captureCalls')==0
            assert not errors,errors
            h={'X-SafeSense-Token':'tracking-browser-test'}
            state=httpx.get('http://127.0.0.1:18830/state',headers=h).json()
            assert len(state['events'])==0 and len(state['incidents'])==0
            record('Mode isolation, responsive canvas, zero capture and zero incident side effects',{'captureCalls':0,'events':0,'incidents':0,'browserErrors':errors})
            page.set_viewport_size({'width':1600,'height':1100})
            page.get_by_role('button',name='Return to campus map',exact=True).click()
            expect(page.locator('[data-zone-id="ZONE_TOILET_BLINDSPOT"] polygon').first).to_be_visible()
            page.locator('[data-zone-id="ZONE_TOILET_BLINDSPOT"] polygon').first.click()
            expect(page.get_by_test_id('private-twin-scene').locator('canvas')).to_be_visible()
            record('Zone navigation returns to original Toilet with working avatar scene','Map → Toilet → Map → Toilet')
            browser.close()
    except Exception as error:
        rows.append({'test':'browser suite','status':'FAIL','actual':str(error),'trace':traceback.format_exc()})
        raise
    finally:
        (OUT/'results.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
        for proc,log in reversed(processes):
            proc.terminate()
            try:proc.wait(timeout=8)
            except subprocess.TimeoutExpired:proc.kill();proc.wait()
            log.close()
