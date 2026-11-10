"""Actual isolated HTTP + browser workflow. Never sends Telegram or touches existing services."""
from pathlib import Path
import json,os,subprocess,sys,time,traceback,shutil
import httpx

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
sys.stdout.reconfigure(encoding='utf-8')
OUT=ROOT/'runtime/visual-overlays'
OUT.mkdir(parents=True,exist_ok=True)
RESULTS=[]
ENV=os.environ.copy()
ENV.update(SAFESENSE_DB_PATH=str(OUT/('test-'+str(int(time.time()))+'.sqlite3')),
           SAFESENSE_BACKEND_URL='http://127.0.0.1:18000',TELEGRAM_MODE='disabled',
           SAFESENSE_AI_URL='http://127.0.0.1:18001',
           VITE_API_BASE_URL='http://127.0.0.1:18000',VITE_AI_BASE_URL='http://127.0.0.1:18001',SAFESENSE_DASHBOARD_URL='http://127.0.0.1:3001',
           SAFESENSE_API_TOKEN='monitoring-integration-test',VITE_SAFESENSE_API_TOKEN='monitoring-integration-test')
H={'X-SafeSense-Token':ENV['SAFESENSE_API_TOKEN']}
B='http://127.0.0.1:18000';A='http://127.0.0.1:18001'
client=httpx.Client(headers=H,timeout=20)
processes=[]

def check(name,fn):
    started=time.perf_counter()
    try:
        actual=fn();row={'test':name,'status':'PASS','actual':actual}
    except Exception as exc:
        row={'test':name,'status':'FAIL','actual':str(exc),'trace':traceback.format_exc()}
    row['seconds']=round(time.perf_counter()-started,3);RESULTS.append(row)
    (OUT/'results.json').write_text(json.dumps(RESULTS,indent=2),encoding='utf-8')
    print(row['status'],name,str(row['actual'])[:500],flush=True)

def expect(response,code=200):
    assert response.status_code==code,(response.status_code,response.text[:500])
    return response.json()

def start(name,cmd,url,cwd=ROOT):
    log=(OUT/(name+'.log')).open('w',encoding='utf-8')
    p=subprocess.Popen(cmd,cwd=cwd,env=ENV,stdout=log,stderr=subprocess.STDOUT,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    processes.append((p,log))
    for _ in range(180):
        if p.poll() is not None:raise RuntimeError(name+' exited; see log')
        try:
            if httpx.get(url,timeout=1).status_code==200:return p
        except OSError:pass
        except httpx.HTTPError:pass
        time.sleep(.25)
    raise RuntimeError(name+' startup timed out')

def job(scenario,model,zone):
    r=expect(client.post(A+'/monitoring/jobs',json={'scenario_id':scenario,'model':model,'zone_id':zone,'authorized':True}),202)
    if scenario=='conflict' and model=='v2':
        duplicate=expect(client.post(A+'/monitoring/jobs',json={'scenario_id':scenario,'model':model,'zone_id':zone,'authorized':True}),202)
        assert duplicate['id']==r['id'],'Active identical CPU jobs must coalesce'
    deadline=time.monotonic()+240
    while time.monotonic()<deadline:
        row=expect(client.get(A+'/monitoring/jobs/'+r['id']))
        if row['status']=='COMPLETED':return row
        assert row['status'] in ('QUEUED','RUNNING'),row
        time.sleep(.5)
    raise AssertionError('Inference timed out')

saved={}
def camera_job(scenario,camera,zone):
    row=expect(client.post(A+'/monitoring/jobs',json={'scenario_id':scenario,'camera_id':camera,'zone_id':zone,'model':'all','authorized':True}),202)
    for _ in range(480):
        row=expect(client.get(A+'/monitoring/jobs/'+row['id']))
        if row['status']=='COMPLETED':return row
        assert row['status'] in ('RUNNING','QUEUED'),row
        time.sleep(.5)
    raise AssertionError('Inference deadline exceeded')

# Reuse only the most recent isolated test database and genuine retained evidence.
prior=json.loads((ROOT/'runtime/visual-overlays/results.json').read_text(encoding='utf-8'))
references=prior[-1]['actual']
ENV['SAFESENSE_DB_PATH']=str(max((ROOT/'runtime/visual-overlays').glob('test-*.sqlite3'),key=lambda p:p.stat().st_mtime))
ENV['SAFESENSE_EVIDENCE_DIR']=str(ROOT/'runtime/tracked-overlays/evidence')
ENV['SAFESENSE_ANNOTATION_DIR']=str(ROOT/'runtime/tracked-overlays/annotations')
OUT=ROOT/'runtime/audit-seek-check';OUT.mkdir(exist_ok=True)
try:
    start('backend',[sys.executable,'-m','uvicorn','backend.main:app','--host','127.0.0.1','--port','18000'],B+'/health')
    start('inference',[sys.executable,'-m','uvicorn','fight_api:app','--host','127.0.0.1','--port','18001'],A+'/health')
    start('frontend',[shutil.which('node'),str(ROOT/'dashboard/node_modules/vite/bin/vite.js'),'--host','127.0.0.1','--port','3001','--strictPort'],'http://127.0.0.1:3001',ROOT/'dashboard')
    from playwright.sync_api import sync_playwright,expect as browser_expect
    with sync_playwright() as pw:
        browser=pw.chromium.launch(headless=True);page=browser.new_page(viewport={'width':1500,'height':1050});page.set_default_timeout(20000)
        errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
        page.goto('http://127.0.0.1:3001');page.locator('aside').get_by_role('button',name='Incident Review',exact=True).click()
        def audit(ref):
            identifier=ref['incident'];report=expect(client.get(B+'/incidents/'+identifier+'/report'))
            item=next(m for observation in report['evidence'] for m in observation.get('evidence_media',[]) if m['analysis_id']==ref['matching_analysis'])
            metadata=expect(client.get(A+'/monitoring/incidents/'+identifier+'/evidence/'+item['id']+'/metadata'))
            page.get_by_placeholder('Search notes, staff, incident #...').fill(identifier[:8]);page.get_by_role('button',name='Audit Details',exact=True).click()
            section=page.get_by_test_id('incident-evidence');clip=section.locator('video')
            browser_expect(clip).to_have_attribute('data-variant','original')
            page.wait_for_function("()=>{const v=document.querySelector('[data-testid=incident-evidence] video');return v?.readyState>=2&&!v.paused}")
            inspected=[]
            if ref['scenario']=='fall':
                for index in (80,0,30,63,80):
                    source_time=index/metadata['overlay_result']['annotation_alignment']['fps']+.001
                    clip.evaluate('(v,t)=>{v.pause();v.currentTime=t}',source_time-metadata['start_sec'])
                    page.wait_for_function("()=>{const v=document.querySelector('[data-testid=incident-evidence] video');return v?.readyState>=2&&!v.seeking&&v.paused}")
                    browser_expect(section.get_by_test_id('video-detection-overlay')).to_have_attribute('data-frame-index',str(index))
                    frame=next(f for f in metadata['overlay_result']['pose_frames'] if f['frame_index']==index)
                    assert section.locator('[data-fall-candidate=true]').count()==sum(p.get('fall_rule_active',False) for p in frame['persons'])
                    inspected.append(index)
                clip.scroll_into_view_if_needed();clip.screenshot(path=str(OUT/'fall-decoded-seek.png'))
            else:
                browser_expect(section.get_by_test_id('fight-video-overlay')).to_contain_text('POSSIBLE FIGHT')
                assert section.get_by_test_id('person-box').count()==0
                clip.scroll_into_view_if_needed();section.screenshot(path=str(OUT/'fight-audit.png'))
            page.get_by_role('button',name='Close',exact=True).click()
            return {'incident':identifier,'scenario':ref['scenario'],'decoded_seek_frames':inspected,'matching_analysis':item['analysis_id']}
        for ref in references:check('Decoded evidence seeking and overlay attribution: '+ref['scenario'],lambda ref=ref:audit(ref))
        assert not errors,errors
        browser.close()
finally:
    for process,log in reversed(processes):
        if process.poll() is None:
            process.terminate()
            try:process.wait(timeout=10)
            except subprocess.TimeoutExpired:process.kill()
        log.close()
    client.close()
sys.exit(any(r['status']=='FAIL' for r in RESULTS))
