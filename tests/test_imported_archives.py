"""Execute archive copies only in an isolated lab; never import their databases/routes."""
from pathlib import Path
import json, os, shutil, socket, subprocess, sys, time, traceback
import httpx
from playwright.sync_api import sync_playwright, expect

sys.stdout.reconfigure(encoding='utf-8')
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'runtime/archive-validation';OUT.mkdir(parents=True,exist_ok=True)
RUN=OUT/str(time.time_ns());RUN.mkdir()
phase=RUN/'phase2';three=RUN/'threejs'
shutil.copytree(ROOT/'integration_sources/zip_review/phase2/SafeSense_Phase2_End_to_End',phase)
shutil.copytree(ROOT/'integration_sources/zip_review/threejs/threejs_test',three)
# Compatibility adaptation only: archived CDN 0.180.0 is not downloaded or claimed tested.
html=(three/'index.html').read_text(encoding='utf-8')
html=html.replace('https://cdn.jsdelivr.net/npm/three@0.180.0/build/three.module.js','/vendor/three.module.js').replace('https://cdn.jsdelivr.net/npm/three@0.180.0/examples/jsm/','/vendor/addons/')
(three/'index.html').write_text(html,encoding='utf-8')
(three/'vendor/addons/controls').mkdir(parents=True)
for name in ('three.module.js','three.core.js'):
    shutil.copy2(ROOT/'dashboard/node_modules/three/build'/name,three/'vendor'/name)
shutil.copy2(ROOT/'dashboard/node_modules/three/examples/jsm/controls/OrbitControls.js',three/'vendor/addons/controls/OrbitControls.js')
rows=[];processes=[]
def check(name,fn):
    try:row={'test':name,'status':'PASS','actual':fn()}
    except Exception as error:row={'test':name,'status':'FAIL','actual':str(error),'trace':traceback.format_exc()}
    rows.append(row);(OUT/'results.json').write_text(json.dumps(rows,indent=2),encoding='utf-8');print(row['status'],name,str(row['actual'])[:500],flush=True)
def start(name,command,cwd,port,health,env=None):
    with socket.socket() as probe:probe.bind(('127.0.0.1',port))
    log=(OUT/(name+'.log')).open('w',encoding='utf-8')
    process=subprocess.Popen(command,cwd=cwd,env=env,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
    processes.append((process,log))
    for _ in range(100):
        if process.poll() is not None:raise RuntimeError(name+' exited')
        try:
            if httpx.get(health,timeout=1).status_code==200:return
        except httpx.HTTPError:pass
        time.sleep(.1)
    raise RuntimeError(name+' startup timeout')
try:
    env=os.environ.copy();env['PORT']='18765'
    start('phase2',[sys.executable,'server.py'],phase,18765,'http://127.0.0.1:18765/health',env)
    start('threejs',[sys.executable,'-m','http.server','18766','--bind','127.0.0.1'],three,18766,'http://127.0.0.1:18766/')
    with httpx.Client(base_url='http://127.0.0.1:18765',timeout=5) as client:
        def phase_workflow():
            assert client.get('/health').json()['mode']=='offline_synthetic_replay'
            assert not client.get('/state').json()['incidents']
            client.post('/replay/seek',json={'time':4.8});assert not client.get('/state').json()['incidents']
            client.post('/replay/start');time.sleep(.25);state=client.get('/state').json();client.post('/replay/pause')
            assert len(state['incidents'])==1 and state['incidents'][0]['source']=='synthetic_radar_replay'
            identifier=state['incidents'][0]['id'];assert client.post(f'/incidents/{identifier}/ack').status_code==200
            assert client.post('/event',json={'event_type':'sos','source':'sos_button'}).status_code==201
            state=client.get('/state').json();assert len(state['incidents'])==2
            assert client.post('/event',json={'event_type':'fall','source':'radar'}).status_code==400
            return {'fall_inserted':True,'sos_inserted':True,'individual_ack':True,'sqlite_rows':len(state['incidents']),'real_inference':False}
        check('Phase2 isolated replay/SOS/ack persistence',phase_workflow)
        def archive_seek_defect():
            client.post('/replay/reset');before=len(client.get('/state').json()['incidents']);client.post('/replay/start');client.post('/replay/seek',json={'time':6});after=len(client.get('/state').json()['incidents']);client.post('/replay/pause')
            return {'documented_seek_no_side_effects':after==before,'confirmed_archive_defect':after>before,'rows_before':before,'rows_after':after,'decision':'Do not import its clock/event insertion implementation'}
        check('Phase2 seek side-effect diagnosis',archive_seek_defect)
    with sync_playwright() as pw:
        browser=pw.chromium.launch(headless=True,args=['--enable-unsafe-swiftshader'])
        def phase_browser():
            page=browser.new_page(viewport={'width':1400,'height':1000});page.goto('http://127.0.0.1:18765');expect(page.locator('#count')).to_have_text('5')
            assert page.locator('#twin').evaluate('c=>!!c.getContext("2d")')
            page.screenshot(path=str(OUT/'phase2-original.png'),full_page=True);page.reload();expect(page.locator('#events .event')).to_have_count(3);page.close()
            return {'canvas':'2D isometric, not Three.js','synthetic_tracks':5,'refresh_preserves_incidents':True}
        check('Phase2 actual browser visualization and refresh',phase_browser)
        def three_browser():
            page=browser.new_page(viewport={'width':1500,'height':1000});errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
            page.goto('http://127.0.0.1:18766');expect(page.locator('canvas')).to_be_visible();page.locator('#overviewToilet').click();expect(page.locator('#detailZoneName')).to_contain_text('Toilet')
            health=page.locator('canvas').evaluate('c=>{let gl=c.getContext("webgl2");return {width:c.width,height:c.height,webgl:!!gl,lost:gl?.isContextLost()}}');assert health['webgl'] and not health['lost']
            button=page.get_by_role('button',name='SOS EMERGENCY',exact=True);button.click();expect(page.get_by_role('button',name='SOS ACTIVE — RESET',exact=True)).to_be_visible()
            page.screenshot(path=str(OUT/'threejs-adapted.png'),full_page=True)
            page.locator('#detailCorridor').click();expect(page.locator('#detailZoneName')).to_contain_text('Corridor');assert not errors,errors;page.close()
            return {'local_three_version':json.loads((ROOT/'dashboard/node_modules/three/package.json').read_text())['version'],'healthy_canvas':health,'navigation_and_local_sos':True,'inference_or_backend':False,'original_cdn_version_tested':False}
        check('Three.js archive adapted to local module: actual WebGL/navigation/SOS',three_browser)
        browser.close()
finally:
    for process,log in reversed(processes):
        if process.poll() is None:
            process.terminate()
            try:process.wait(timeout=8)
            except subprocess.TimeoutExpired:process.kill()
        log.close()
sys.exit(any(r['status']=='FAIL' for r in rows))
