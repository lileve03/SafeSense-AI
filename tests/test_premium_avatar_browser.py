"""Actual default guided experience, hands-off synthetic staff workflow, isolated DB."""
import json,math,os,shutil,socket,subprocess,sys,tempfile,time,traceback
from pathlib import Path
import httpx
from playwright.sync_api import sync_playwright,expect

sys.stdout.reconfigure(encoding='utf-8')
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'runtime/premium-avatars/checks';OUT.mkdir(parents=True,exist_ok=True)
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
            page=browser.new_page(viewport={'width':1600,'height':1800});page.set_default_timeout(20000)
            errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
            page.goto(D);page.locator('aside').get_by_role('button',name='Digital Twin Map',exact=True).click()
            page.locator('[data-zone-id="ZONE_TOILET_BLINDSPOT"] polygon').first.click()
            guide=page.get_by_test_id('guided-private-demo');scene=page.get_by_test_id('private-twin-scene');renderer=page.get_by_test_id('private-three-renderer')
            assert page.locator('canvas').count()==1
            assert page.get_by_role('button',name='Guided Demo',exact=True).count()==0
            assert page.get_by_role('button',name='Advanced Monitoring',exact=True).count()==0
            page.evaluate("window.originalCanvas=document.querySelector('[data-testid=private-twin-scene] canvas')")
            def stats():return json.loads(renderer.get_attribute('data-tracking'))
            guide.get_by_role('combobox',name='Guided playback speed').select_option('4')
            for demo,at in [('normal',6),('proximity',10),('repetitive',13),('fall',10)]:
                guide.get_by_role('combobox',name='Guided scenario').select_option(demo)
                guide.get_by_role('button',name='Start guided demo',exact=True).click()
                page.wait_for_function("t=>JSON.parse(document.querySelector('[data-testid=private-three-renderer]').dataset.tracking||'{}').time>=t",arg=at)
                if demo in ['proximity','repetitive']:
                    page.wait_for_function("JSON.parse(document.querySelector('[data-testid=private-three-renderer]').dataset.tracking).highlightedTrackIds.length>0")
                if demo in ['normal','repetitive']:
                    moving_before=stats()['positions'];page.wait_for_timeout(150);moving_after=stats()['positions']
                    assert moving_before!=moving_after,(demo,moving_before,moving_after)
                guide.get_by_role('button',name='Pause guided demo',exact=True).click()
                page.wait_for_timeout(250)
                current=stats();assert current['active']==current['visible']==len(current['avatars'])>0
                assert all(a['arms']==2 and a['poseMeasured']==False for a in current['avatars'])
                if demo=='normal':assert all(a['color']=='22c55e' and a['pose']=='standing-schematic' for a in current['avatars'])
                if demo in ['proximity','repetitive']:assert any(a['color']=='eab308' for a in current['avatars'])
                if demo=='proximity':assert abs(current['pairs'][0]['meters']-.6)<.01
                if demo=='repetitive':expect(page.get_by_test_id('motion-rule-triggers')).to_contain_text('REPEATED_BACK_AND_FORTH')
                if demo=='fall':
                    fallen=next(a for a in current['avatars'] if a['id']=='T01');assert fallen['pose']=='lying-schematic' and fallen['color']=='ef4444'
                    expect(scene).to_have_attribute('data-fall-active','true')
                    expect(page.get_by_test_id('scenario-incident-status')).to_contain_text('Incident #')
                page.get_by_role('button',name='Select simulated track T01',exact=True).click()
                expect(page.get_by_test_id('selected-track-information')).to_contain_text('Height')
                expect(page.get_by_test_id('selected-track-information')).to_contain_text('Speed')
                assert all(a['groundColor']==a['color'] for a in current['avatars'])
                assert page.evaluate("window.originalCanvas===document.querySelector('[data-testid=private-twin-scene] canvas')")
                assert current['trailVertices']>0
                if current['pairs']:assert f"{current['pairs'][0]['meters']:.2f}m" in current['distanceText'].replace(' ',''),current['distanceText']
                count=int(renderer.get_attribute('data-render-count'));page.wait_for_timeout(600)
                idle=int(renderer.get_attribute('data-render-count'))-count;assert idle<=1,idle
                page.evaluate("document.querySelectorAll('*').forEach(e=>{if(e.scrollTop)e.scrollTop=0;})")
                page.screenshot(path=str(OUT/(demo+'-page.png')),full_page=True)
                scene.screenshot(path=str(OUT/(demo+'-room.png')))
                record('Reference humanoids in '+demo,{'avatars':current['avatars'],'distance':current['pairs'],'triangles':current['triangles'],'drawCalls':current['drawCalls'],'idleRenderDelta':idle})
            guide.get_by_role('combobox',name='Guided scenario').select_option('normal')
            guide.get_by_role('combobox',name='Guided scenario').select_option('fall')
            slider=page.get_by_role('slider',name='Tracking playback time',exact=True);slider.focus();slider.press('Home')
            for _ in range(86):slider.press('ArrowRight')
            page.wait_for_timeout(250)
            falling=next(a for a in stats()['avatars'] if a['id']=='T01')
            assert 0<falling['fallProgress']<1 and falling['pose']=='falling-schematic',falling
            scene.screenshot(path=str(OUT/'fall-transition-room.png'))
            record('Actual room supports a staged explicitly simulated fall',falling)
            animation=page.evaluate("""async()=>{
                const {AnonymousTrackingLayer}=await import('/src/components/private-area/AnonymousTrackingLayer.ts');
                const layer=new AnonymousTrackingLayer(),options={trails:true,selectedId:null};
                const frame=(time,x,y,vx,vy,progress)=>({sourceMode:'SIMULATION',streamId:'explicit-animation-fixture',time,tracks:[{id:'A',position:{x,y,z:.24},velocity:{x:vx,y:vy,z:0}},{id:'B',position:{x:x+2,y,z:.24},velocity:{x:vx,y:vy,z:0}}],...(progress==null?{}:{fallProgress:{A:progress}})});
                for(let i=0;i<=30;i++)layer.update(frame(i/30,0,i/30,0,1),options);
                const walk=structuredClone(layer.stats);
                for(let i=1;i<=45;i++)layer.update(frame(1+i/30,0,1,0,0),options);
                const idle1=structuredClone(layer.stats);
                for(let i=46;i<=60;i++)layer.update(frame(1+i/30,0,1,0,0),options);
                const idle2=structuredClone(layer.stats);
                layer.update(frame(3+1/30,1/30,1,1,0),options);const firstTurn=layer.stats.avatars[0].heading;
                for(let i=2;i<=30;i++)layer.update(frame(3+i/30,i/30,1,1,0),options);
                const lastTurn=layer.stats.avatars[0].heading;
                const progress=[.2,.5,1].map((p,i)=>{layer.update(frame(4+(i+1)/30,1,1,0,0,p),options);return layer.stats.avatars[0].fallProgress;});
                const paused=structuredClone(layer.stats.avatars);layer.update(frame(4+3/30,1,1,0,0,1),options);
                const pauseFrozen=JSON.stringify(paused)===JSON.stringify(layer.stats.avatars);
                layer.update({sourceMode:'RECORDED_REPLAY',streamId:'recorded-position-fixture',time:1,tracks:[{id:'A',position:{x:0,y:0,z:.24},velocity:{x:1,y:0,z:0}}]},options);
                const recorded=structuredClone(layer.stats.avatars[0]);
                layer.update({sourceMode:'SIMULATION',streamId:'capacity-fixture',time:1,tracks:Array.from({length:12},(_,i)=>({id:'P'+i,position:{x:i*.1,y:0,z:.24}}))},options);
                const visible=layer.stats.visible;layer.dispose();return {walk,idle1,idle2,firstTurn,lastTurn,progress,pauseFrozen,recorded,visible};
            }""")
            assert animation['walk']['visible']==2
            assert any(abs(a['legSwing'])>.01 and abs(a['armSwing']+.72*a['legSwing'])<1e-6 for a in animation['walk']['avatars'])
            assert animation['idle1']['positions']==animation['idle2']['positions']
            assert animation['idle1']['avatars'][0]['idleOffset']!=animation['idle2']['avatars'][0]['idleOffset']
            assert abs(animation['idle2']['avatars'][0]['legSwing'])<.001
            assert 0<animation['firstTurn']<.6 and abs(animation['lastTurn']-math.pi/2)<.01
            assert animation['progress']==[.2,.5,1] and animation['pauseFrozen']
            assert animation['recorded']['legSwing']==animation['recorded']['armSwing']==animation['recorded']['idleOffset']==0
            assert animation['visible']==12
            record('Coordinated walking, stationary idle, smooth turning, fall progression, pause and neutral measured-track poses',{'first_turn':animation['firstTurn'],'final_turn':animation['lastTurn'],'fall_progress':animation['progress'],'pause_frozen':True,'valid_tracks':12,'recorded_body_animation':False})
            # Deterministic browser fixtures verify input contracts; these are not real hardware/recording observations.
            contract=page.evaluate("""async()=>{
                const {observationFrame}=await import('/src/components/private-area/trackingPlayback.ts');
                const {AnonymousTrackingLayer}=await import('/src/components/private-area/AnonymousTrackingLayer.ts');
                const base={observation_id:'browser-fixture',source_mode:'RECORDED_REPLAY',device_id:'TEST FIXTURE',tracking_session_id:'fixture',timestamp:'2026-11-03T00:00:00Z',coordinate_frame:'zone_meters_x_right_y_forward_z_up',data_validity:'VALID',radar_event:'presence',tracks:[{id:'A',position:{x:0,y:0,z:.2}}]};
                const plain=observationFrame(base),fall=observationFrame({...base,radar_event:'fall'}),ambiguous=observationFrame({...base,radar_event:'fall',tracks:[...base.tracks,{id:'B',position:{x:2,y:0,z:.2}}]});
                const noSpatial=observationFrame({...base,tracks:null,radar_event:'fall'}),invalid=observationFrame({...base,data_validity:'INVALID'}),hardware=observationFrame({...base,source_mode:'LIVE_HARDWARE'});
                const layer=new AnonymousTrackingLayer(),options={trails:true,selectedId:null};layer.update(plain,options);
                layer.update({...plain,time:plain.time+.2,tracks:[{id:'A',position:{x:1,y:0,z:.2}}]},options);
                await new Promise(r=>setTimeout(r,90));layer.update({...plain,time:plain.time+.2,tracks:[{id:'A',position:{x:1,y:0,z:.2}}]},options);
                const mid=layer.stats.avatars[0].renderPosition.x;
                await new Promise(r=>setTimeout(r,220));layer.update({...plain,time:plain.time+.2,tracks:[{id:'A',position:{x:1,y:0,z:.2}}]},options);
                const end=layer.stats.avatars[0].renderPosition.x;
                const neutral=layer.stats.avatars[0].pose;
                layer.update(fall,options);const fallen=layer.stats.avatars[0].pose;
                layer.dispose();return {plain:plain.fallIds,fall:fall.fallIds,ambiguous:ambiguous.fallIds,noSpatial:noSpatial.tracks.length,invalid:invalid.tracks.length,hardware:hardware.tracks.length,mid,end,neutral,fallen};
            }""")
            assert contract['plain']==[] and contract['fall']==['A'] and contract['ambiguous']==[]
            assert contract['noSpatial']==contract['invalid']==contract['hardware']==0
            assert 0<contract['mid']<1 and contract['end']==1 and contract['neutral']=='standing-schematic' and contract['fallen']=='lying-schematic',contract
            record('Validated replay interpolation and fall gating; no invented hardware people or poses',contract)
            fixture={'schema_version':1,'observation_id':'browser-fixture-only','device_id':'SYNTHETIC CONTRACT FIXTURE','zone_id':'ZONE_TOILET_BLINDSPOT','source_mode':'RECORDED_REPLAY','timestamp':'2026-11-03T00:00:00Z','data_validity':'VALID','coordinate_frame':'zone_meters_x_right_y_forward_z_up','tracking_session_id':'fixture','radar_event':'presence','sos_state':'UNKNOWN','tracks':[{'id':'FIXTURE-A','position':{'x':-1,'y':.5,'z':.3}}],'validity_reason':'Synthetic browser fixture, not an actual recording or hardware observation'}
            def observation_fixture(route):
                if 'source_mode=RECORDED_REPLAY' in route.request.url:route.fulfill(json={'observation':fixture})
                else:route.continue_()
            page.route('**/sensors/observations?**',observation_fixture)
            page.get_by_role('combobox',name='Source mode',exact=True).select_option('RECORDED_REPLAY')
            page.get_by_role('button',name='Select observed track FIXTURE-A',exact=True).click()
            expect(page.get_by_test_id('selected-track-information')).to_contain_text('RECORDED_REPLAY')
            expect(page.get_by_test_id('selected-track-information')).to_contain_text('Velocity unavailable')
            assert page.locator('canvas').count()==1
            record('Active-source track detail labels and missing velocity remain truthful',{'input':'SYNTHETIC browser contract fixture','velocity':'Unavailable','canvas_count':1})
            assert not errors,errors
            record('One room, no view tabs, zero browser errors',{'canvas_count':page.locator('canvas').count(),'browser_errors':errors})
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
