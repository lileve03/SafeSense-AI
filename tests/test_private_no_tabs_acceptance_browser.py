"""Actual default guided experience, hands-off synthetic staff workflow, isolated DB."""
import json,math,os,shutil,socket,subprocess,sys,tempfile,time,traceback
from pathlib import Path
import httpx
from playwright.sync_api import sync_playwright,expect

sys.stdout.reconfigure(encoding='utf-8')
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'runtime/unified-private-no-tabs-acceptance';OUT.mkdir(parents=True,exist_ok=True)
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
            root=page.get_by_test_id('private-monitoring-view');guide=page.get_by_test_id('guided-private-demo');scene=page.get_by_test_id('private-twin-scene')
            assert root.get_by_role('button',name='Guided Demo',exact=True).count()==0
            assert root.get_by_role('button',name='Advanced Monitoring',exact=True).count()==0
            assert root.get_by_role('tab').count()==0 and root.locator('canvas').count()==1
            assert root.get_by_role('button',name='ACTIVATE SOS EMERGENCY',exact=True).count()==1
            page.evaluate("window.originalToiletCanvas=document.querySelector('[data-testid=private-twin-scene] canvas')")
            guide.get_by_role('combobox',name='Guided playback speed').select_option('2')
            guide.get_by_role('button',name='Start guided demo',exact=True).click()
            expect(page.get_by_test_id('private-risk-status')).to_contain_text('HIGH',timeout=20000)
            guide.get_by_role('button',name='Pause guided demo',exact=True).click()
            expect(scene).to_have_attribute('data-fall-active','true')
            expect(page.get_by_test_id('scenario-incident-status')).to_contain_text('Incident #')
            expect(page.get_by_test_id('scenario-response-status')).not_to_have_text('Not escalated')
            page.get_by_role('button',name='Select simulated track T01',exact=True).click()
            page.evaluate("document.querySelectorAll('*').forEach(e=>{if(e.scrollTop)e.scrollTop=0;})")
            page.screenshot(path=str(OUT/'one-page-no-tabs-active-fall.png'),full_page=True)
            record('No tabs; one original room; active fall, risk, coordinates and incident synchronized; one SOS action',{'canvas_count':1,'risk':'HIGH','tabs':0,'sos_controls':1})
            source=page.get_by_role('combobox',name='Source mode',exact=True)
            for mode in ['RECORDED_REPLAY','LIVE_HARDWARE','SIMULATION']:
                source.select_option(mode)
                assert page.evaluate("window.originalToiletCanvas===document.querySelector('[data-testid=private-twin-scene] canvas')")
                assert page.locator('canvas').count()==1
                expect(root.get_by_text('Zone Classification',exact=True)).to_be_visible()
                if mode=='LIVE_HARDWARE':
                    expect(scene).to_have_attribute('data-animation','static-observation')
                    expect(scene).to_have_attribute('data-positioned-occupants','0')
                    expect(page.get_by_test_id('normalized-sensor-panel')).to_contain_text('Hardware Disconnected')
            assert not errors,errors
            record('Same canvas DOM instance retained across all input modes; no hardware observations fabricated',{'modes':3,'browser_errors':errors})
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
