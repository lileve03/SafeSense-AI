"""Actual default guided experience, hands-off synthetic staff workflow, isolated DB."""
import json,math,os,shutil,socket,subprocess,sys,tempfile,time,traceback
from pathlib import Path
import httpx
from playwright.sync_api import sync_playwright,expect

sys.stdout.reconfigure(encoding='utf-8')
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'runtime/scene-alignment/camera-checks';OUT.mkdir(parents=True,exist_ok=True)
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
        history=None
        for kind,modality in [('fall','radar'),('impact','acoustic')]:
            response=client.post('/event',json={'zone':'ZONE_TOILET_BLINDSPOT','type':kind,'source':'simulation','sensor_modality':modality,'processing_mode':'simulation','source_type':'SIMULATION','is_test':True,'confidence':1,'analysis_run_id':'private-demo:unrelated-scene-history','event_id':'unrelated-scene-'+kind})
            assert response.status_code==200,response.text
            history=response.json().get('incident')
        assert history and history['level']=='HIGH',history
        with sync_playwright() as pw:
            browser=pw.chromium.launch(headless=True,args=['--enable-unsafe-swiftshader'])
            page=browser.new_page(viewport={'width':1600,'height':1800});page.set_default_timeout(20000)
            errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
            page.goto(D);page.locator('aside').get_by_role('button',name='Digital Twin Map',exact=True).click()
            page.locator('[data-zone-id="ZONE_TOILET_BLINDSPOT"] polygon').first.click()
            guide=page.get_by_test_id('guided-private-demo');scene=page.get_by_test_id('private-twin-scene');renderer=page.get_by_test_id('private-three-renderer')
            def seek(demo,time):
                guide.get_by_role('combobox',name='Guided scenario').select_option(demo)
                slider=page.get_by_role('slider',name='Tracking playback time',exact=True);slider.focus();slider.press('Home')
                for _ in range(round(time*10)):slider.press('ArrowRight')
                page.wait_for_timeout(300)
            seek('normal',6)
            expect(page.get_by_test_id('private-risk-status')).to_contain_text('LOW')
            expect(page.get_by_test_id('actual-incident-severity')).to_contain_text('HIGH')
            assert all(a['color']=='22c55e' for a in json.loads(renderer.get_attribute('data-tracking'))['avatars'])
            page.evaluate("document.querySelectorAll('*').forEach(e=>{if(e.scrollTop)e.scrollTop=0;})")
            page.screenshot(path=str(OUT/'normal-low-actual-incident-high.png'),full_page=True)
            record('Normal green visual LOW and persisted incident HIGH remain separately visible',{'scene':'LOW','actual_incident':'HIGH'})
            seek('proximity',10)
            def validate(name):
                page.wait_for_timeout(250)
                current=json.loads(renderer.get_attribute('data-tracking'))
                def overlap(a,b):return a['x']<b['x']+b['width'] and a['x']+a['width']>b['x'] and a['y']<b['y']+b['height'] and a['y']+a['height']>b['y']
                boxes=current['labelRects'];assert len(boxes)==3,(name,boxes)
                for i,box in enumerate(boxes):assert not any(overlap(box,other) for other in boxes[i+1:]+current['reservedLabelRects']+current['bodyRects']),(name,box)
                assert page.locator('canvas').count()==1
                record('Collision-free labels after '+name,{'labels':boxes,'canvas_count':1})
            validate('default framing')
            guide.get_by_role('combobox',name='Guided playback speed').select_option('4')
            guide.get_by_role('button',name='Start guided demo',exact=True).click()
            clock=page.wait_for_function("()=>{const r=Number(document.querySelector('[data-testid=private-three-renderer]').dataset.renderFrameTime),u=Number(document.querySelector('[data-testid=selected-track-information]').dataset.frameTime);return r>=3.5&&Math.abs(r-u)<1e-8?{renderer_time:r,telemetry_time:u}:false;}").json_value()
            assert clock['renderer_time']==clock['telemetry_time']
            record('Moving telemetry and renderer publish the identical frame time',clock)
            guide.get_by_role('button',name='Pause guided demo',exact=True).click()
            page.wait_for_timeout(250)
            assert abs(float(renderer.get_attribute('data-render-frame-time'))-float(page.get_by_test_id('selected-track-information').get_attribute('data-frame-time')))<1e-8
            scene.get_by_title('Zoom In',exact=True).click();validate('zoom')
            scene.scroll_into_view_if_needed();bounds=scene.locator('canvas').bounding_box()
            page.mouse.move(bounds['x']+bounds['width']*.65,bounds['y']+bounds['height']*.65);page.mouse.down();page.mouse.move(bounds['x']+bounds['width']*.65+70,bounds['y']+bounds['height']*.65+15,steps=8);page.mouse.up()
            validate('orbit')
            scene.screenshot(path=str(OUT/'orbited-labels.png'))
            scene.get_by_title('Reset Orbit View',exact=True).click()
            page.set_viewport_size({'width':430,'height':1300});scene.scroll_into_view_if_needed();validate('430px viewport')
            scene.screenshot(path=str(OUT/'mobile-labels.png'))
            assert not errors,errors
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
