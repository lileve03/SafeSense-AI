"""Actual isolated HTTP + browser workflow. Never sends Telegram or touches existing services."""
from pathlib import Path
import json,os,subprocess,sys,time,traceback,shutil
import httpx

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
sys.stdout.reconfigure(encoding='utf-8')
OUT=ROOT/'runtime/audit-evidence-task4'
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

import sqlite3
ENV['SAFESENSE_EVIDENCE_DIR']=str(OUT/('evidence-'+str(int(time.time()))));evidence_dir=Path(ENV['SAFESENSE_EVIDENCE_DIR']);evidence_dir.mkdir()
with sqlite3.connect('file:'+str(ROOT/'runtime/safesense.sqlite3')+'?mode=ro',uri=True) as original, sqlite3.connect(ENV['SAFESENSE_DB_PATH']) as copied:
    original.backup(copied)
    original_incidents=[json.loads(row[0]) for row in original.execute("SELECT body FROM records WHERE kind='incident'")]
saved_existing={}
for incident in original_incidents:
    for observation in incident.get('evidence',[]):
        for media in observation.get('evidence_media',[]):
            kind='pose' if media['model_version'].startswith('yolo') else 'fight'
            if kind not in saved_existing and all((ROOT/'runtime/evidence'/(media['id']+suffix)).is_file() for suffix in ('.mp4','.json')):
                for suffix in ('.mp4','.json'):shutil.copy2(ROOT/'runtime/evidence'/(media['id']+suffix),evidence_dir/(media['id']+suffix))
                saved_existing[kind]=(incident['id'],media)
assert len(saved_existing)==2,'Need actual saved Fight and Fall clips'

def url(i,m):return A+'/monitoring/incidents/'+i+'/evidence/'+m['id']
routes=OUT/'assignment-routes-test.json'
routes.write_text(json.dumps([{'zone_id':'ZONE_STAIRCASE','staff':'Audit test responder','role':'security','active':True}]))
ENV['SAFESENSE_STAFF_ROUTES']=str(routes)
saved={}
def new_job(scenario,camera,zone,model):
    row=expect(client.post(A+'/monitoring/jobs',json={'scenario_id':scenario,'camera_id':camera,'zone_id':zone,'model':model,'authorized':True}),202)
    for _ in range(480):
        row=expect(client.get(A+'/monitoring/jobs/'+row['id']))
        if row['status']=='COMPLETED':return row['result']
        assert row['status'] in ('RUNNING','QUEUED'),row
        time.sleep(.5)
    raise AssertionError('Inference deadline')
try:
    bp=start('backend',[sys.executable,'-m','uvicorn','backend.main:app','--host','127.0.0.1','--port','18000'],B+'/health')
    ap=start('inference',[sys.executable,'-m','uvicorn','fight_api:app','--host','127.0.0.1','--port','18001'],A+'/health')
    def historical():
        actual=[]
        for kind,(i,m) in saved_existing.items():
            manifest=expect(client.get(url(i,m)+'/metadata'));assert manifest['incident_id']==i and manifest['analysis_id']==m['analysis_id'] and manifest['score']==m['score']
            response=client.get(url(i,m),headers={'Range':'bytes=0-1023'});assert response.status_code==206
            actual.append({'kind':kind,'incident':i,'evidence':m['id'],'duration':manifest['duration_sec'],'annotated':manifest['annotated_available']})
        return actual
    check('Actual previously saved Fight/Fall evidence matches selected incident',historical)
    def fresh():
        saved['fight']=new_job('conflict','CAM_CORRIDOR_A','ZONE_CORRIDOR_A','v3')
        saved['pose']=new_job('fall','CAM_STAIRCASE','ZONE_STAIRCASE','pose')
        for kind,result in saved.items():
            i=result['event_delivery']['incident_id'];m=result['evidence_media'][0];manifest=expect(client.get(url(i,m)+'/metadata'))
            assert manifest['prediction'] and manifest['original_available']
            assert manifest['camera_id']==('CAM_STAIRCASE' if kind=='pose' else 'CAM_CORRIDOR_A')
            assert manifest['annotated_available']==(kind=='pose')
            if kind=='pose':
                response=client.get(url(i,m),params={'variant':'annotated'});assert response.status_code==200
                (OUT/'retained-pose.mp4').write_bytes(response.content)
                import cv2
                cap=cv2.VideoCapture(str(OUT/'retained-pose.mp4'));frames=int(cap.get(cv2.CAP_PROP_FRAME_COUNT));fps=cap.get(cv2.CAP_PROP_FPS);cap.release()
                assert abs(frames/fps-manifest['duration_sec'])<1/fps
            download=client.get(url(i,m),params={'download':'true'});assert 'attachment;' in download.headers['content-disposition']
            assert len(download.content)>1024
        return {k:{'incident':v['event_delivery']['incident_id'],'model':v['model_version'],'score':v.get('score'),'media':v['evidence_media']} for k,v in saved.items()}
    check('Real V3/Fall inference retains correct original and genuine annotated evidence, supports download',fresh)

    def legacy_recovery():
        result=saved['pose'];i=result['event_delivery']['incident_id'];m=result['evidence_media'][0]
        sidecar=evidence_dir/(m['id']+'.json');annotated=evidence_dir/(m['id']+'.annotated.mp4')
        old=json.loads(sidecar.read_text());legacy={k:v for k,v in old.items() if k not in ('annotation_analysis_id','annotation_alignment')}
        age=sidecar.stat().st_mtime;sidecar.write_text(json.dumps(legacy));os.utime(sidecar,(age,age));annotated.unlink()
        manifest=expect(client.get(url(i,m)+'/metadata'));assert manifest['annotated_available']
        assert abs(sidecar.stat().st_mtime-age)<.001
        recovered=json.loads(sidecar.read_text());tampered={**recovered,'analysis_id':saved['fight']['analysis_id']}
        try:
            sidecar.write_text(json.dumps(tampered));expect(client.get(url(i,m)+'/metadata'),409)
        finally:
            sidecar.write_text(json.dumps(recovered));os.utime(sidecar,(age,age))
        return 'Exact persisted pose analysis recovered; retention age preserved; tampered analysis identity rejected with 409'
    check('Legacy annotation recovery requires exact analysis provenance; metadata mismatch rejected',legacy_recovery)
    def binding():
        fight=saved['fight'];pose=saved['pose'];i=fight['event_delivery']['incident_id'];m=pose['evidence_media'][0]
        expect(client.get(url(i,m)+'/metadata'),404);expect(client.get(url(i,m)),404)
        private=next(x['id'] for x in original_incidents if x['zone_type']=='PRIVATE')
        expect(client.get(url(private,m)),403)
        expect(httpx.get(url(pose['event_delivery']['incident_id'],m)),401)
        return 'Wrong incident 404; private-zone access 403; missing token 401'
    check('Incident binding, private-zone denial and authorized evidence access',binding)
    def persistence():
        pose=saved['pose'];i=pose['event_delivery']['incident_id'];m=pose['evidence_media'][0]
        ap.terminate();ap.wait(timeout=10)
        start('inference-restart',[sys.executable,'-m','uvicorn','fight_api:app','--host','127.0.0.1','--port','18001'],A+'/health')
        response=client.get(url(i,m),params={'variant':'annotated'},headers={'Range':'bytes=0-1023'});assert response.status_code==206
        return 'Retained annotated evidence survives inference restart; does not require temporary artifact registration'
    check('Saved annotation survives actual service restart',persistence)
    public_empty=expect(client.post(B+'/event',json={'zone':'ZONE_ENTRANCE','type':'rapid_motion','source':'vision','processing_mode':'simulation'}))['incident']
    assert public_empty and not public_empty['evidence'][0]['evidence_media']
    private=next(i for i in original_incidents if i['zone_type']=='PRIVATE' and i['source']=='radar')
    private_sos=next(i for i in original_incidents if i['zone_type']=='PRIVATE' and i['source']=='sos_button')
    private_acoustic=expect(client.post(B+'/monitoring/scenarios/acoustic/run',json={}))['incident']
    start('frontend',[shutil.which('node'),str(ROOT/'dashboard/node_modules/vite/bin/vite.js'),'--host','127.0.0.1','--port','3001','--strictPort'],'http://127.0.0.1:3001',ROOT/'dashboard')
    from playwright.sync_api import sync_playwright,expect as browser_expect
    with sync_playwright() as pw:
        browser=pw.chromium.launch(headless=True)
        page=browser.new_page(viewport={'width':1440,'height':1050});page.set_default_timeout(20000)
        errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
        page.goto('http://127.0.0.1:3001');page.locator('aside').get_by_role('button',name='Incident Review',exact=True).click()
        def audit(identifier):
            page.get_by_placeholder('Search notes, staff, incident #...').fill(identifier[:8])
            page.get_by_role('button',name='Audit Details',exact=True).click()
            section=page.get_by_test_id('incident-evidence');browser_expect(section).to_have_attribute('data-incident-id',identifier)
            browser_expect(section.get_by_text(identifier,exact=True)).to_be_visible()
            return section
        def close():page.get_by_role('button',name='Close',exact=True).click()
        def browser_fight():
            i=saved['fight']['event_delivery']['incident_id'];m=saved['fight']['evidence_media'][0];section=audit(i)
            video=section.locator('video');browser_expect(video).to_be_visible()
            page.wait_for_function("()=>{let v=document.querySelector('[data-testid=incident-evidence] video');return v?.readyState>=2 && !v.paused && v.currentTime>.1}")
            assert video.evaluate('(v)=>v.muted && v.controls')
            browser_expect(video).to_have_attribute('data-evidence-id',m['id']);browser_expect(video).to_have_attribute('data-variant','original')
            assert f"{saved['fight']['score']:.6f}" in section.inner_text()
            assert 'No matching retained annotation' in section.inner_text()
            video.evaluate('(v)=>{v.pause();v.currentTime=1}')
            page.wait_for_function("()=>Math.abs(document.querySelector('[data-testid=incident-evidence] video').currentTime-1)<.01")
            assert video.evaluate('(v)=>v.paused')
            section.get_by_role('button',name='Replay evidence',exact=True).click()
            page.wait_for_function("()=>{let v=document.querySelector('[data-testid=incident-evidence] video');return !v.paused && v.currentTime<1}")
            with page.expect_download() as d:section.get_by_role('link',name='Download authorized evidence',exact=True).click()
            d.value.save_as(str(OUT/'browser-fight-download.mp4'));assert (OUT/'browser-fight-download.mp4').stat().st_size>1024
            page.screenshot(path=str(OUT/'fight-audit.png'),full_page=True);close()
            return {'incident':i,'autoplay_muted':True,'pause_seek_replay':True,'authorized_download':True,'no_fabricated_fight_boxes':True}
        check('Audit Details: saved Fight clip autoplays, correct score, seek/replay and download',browser_fight)
        def browser_pose():
            i=saved['pose']['event_delivery']['incident_id'];m=saved['pose']['evidence_media'][0];section=audit(i)
            video=section.locator('video');browser_expect(video).to_have_attribute('data-variant','annotated')
            page.wait_for_function("()=>{let v=document.querySelector('[data-testid=incident-evidence] video');return v?.readyState>=2 && !v.paused && v.currentTime>.1}")
            assert '/monitoring/incidents/'+i+'/evidence/'+m['id'] in video.get_attribute('src')
            assert 'N/A - no trained classifier score' in section.inner_text()
            section.get_by_role('button',name='Show original clip',exact=True).click();browser_expect(video).to_have_attribute('data-variant','original')
            section.get_by_role('button',name='Show annotated clip',exact=True).click();browser_expect(video).to_have_attribute('data-variant','annotated')
            page.wait_for_function("()=>{let v=document.querySelector('[data-testid=incident-evidence] video');return v?.readyState>=2 && !v.paused && v.currentTime>.1}")
            video.evaluate('(v)=>{v.pause();v.currentTime=2.1}')
            page.wait_for_function("()=>{let v=document.querySelector('[data-testid=incident-evidence] video');return v.readyState>=2 && !v.seeking && Math.abs(v.currentTime-2.1)<.01}")
            page.screenshot(path=str(OUT/'fall-annotated-audit.png'),full_page=True);close()
            return {'incident':i,'annotated_evidence':True,'original_toggle':True,'no_invented_fall_probability':True}
        check('Audit Details: retained Fall boxes/skeletons, genuine annotation toggle and metadata',browser_pose)
        def private_and_empty():
            section=audit(private['id']);browser_expect(section.get_by_text('Private sensor metadata only. No images, video, or speech are captured.',exact=True)).to_be_visible()
            assert section.locator('video,img,audio,a[download]').count()==0
            assert 'radar' in section.inner_text() and 'Observation timestamp:' in section.inner_text();close()
            for sensor_incident in (private_sos,private_acoustic):
                section=audit(sensor_incident['id']);browser_expect(section.get_by_text('Private sensor metadata only. No images, video, or speech are captured.',exact=True)).to_be_visible()
                assert section.locator('video,img,audio,a[download]').count()==0
                assert 'Observation timestamp:' in section.inner_text();close()
            section=audit(public_empty['id']);browser_expect(section.get_by_text('No retained video attached to this incident.',exact=False)).to_be_visible()
            assert section.locator('video,img').count()==0
            page.screenshot(path=str(OUT/'no-evidence-audit.png'),full_page=True);close()
            return {'private_radar_acoustic_SOS_metadata_only':True,'missing_evidence_message':True,'previous_incident_media_not_reused':True}
        check('Audit Details: private metadata only and useful no-evidence state',private_and_empty)
        def expiry():
            i=saved['fight']['event_delivery']['incident_id'];m=saved['fight']['evidence_media'][0]
            expect(client.post(A+m['url']+'/delete',json={}))
            expect(client.get(url(i,m)),410)
            section=audit(i);browser_expect(section.get_by_text('Evidence unavailable:',exact=False)).to_be_visible()
            assert section.locator('video').count()==0;close()
            return 'Deleted retained clip returns 410 and displays useful unavailable message without substituting a dataset source'
        check('Audit Details: expired/deleted media handling',expiry)
        def lifecycle():
            i=saved['pose']['event_delivery']['incident_id'];section=audit(i)
            page.get_by_role('button',name='Acknowledge Alert',exact=True).click()
            browser_expect(page.get_by_role('button',name='Mark as Verified',exact=True)).to_be_visible()
            report=expect(client.get(B+'/incidents/'+i+'/report'));assert report['acknowledged_at']
            page.get_by_role('button',name='Re-Dispatch Staff',exact=True).click()
            browser_expect(page.get_by_role('heading',name='Dispatch Campus Responder',exact=True)).to_be_visible()
            with page.expect_response(lambda response:response.url.endswith('/incidents/'+i+'/review') and response.request.method=='POST'):
                page.get_by_role('button',name='Assign & queue notification',exact=True).click()
            dispatched=expect(client.get(B+'/incidents/'+i+'/report'));assert dispatched['status']=='DISPATCHED' and dispatched['assigned_staff']=='Audit test responder'
            expect(client.post(B+'/incidents/'+i+'/review',json={'status':'RESOLVED','note':'Reviewed actual saved annotated fall evidence in audit test'}))
            report=expect(client.get(B+'/incidents/'+i+'/report'));assert report['status']=='RESOLVED'
            zone=next(z for z in expect(client.get(B+'/zones')) if z['id']=='ZONE_STAIRCASE');assert i not in zone['active_incident_ids']
            close();assert not errors,errors
            return {'acknowledged':True,'configured_assignment_verified':True,'resolved':True,'digital_twin_synchronized':True,'browser_errors':errors}
        check('Existing acknowledgement, resolution and Digital Twin remain functional',lifecycle)
        browser.close()
finally:
    for process,log in reversed(processes):
        if process.poll() is None:
            process.terminate()
            try:process.wait(timeout=10)
            except subprocess.TimeoutExpired:process.kill()
        log.close()
    client.close()
    with sqlite3.connect('file:'+str(ROOT/'runtime/safesense.sqlite3')+'?mode=ro',uri=True) as db:
        after=[json.loads(row[0]) for row in db.execute("SELECT body FROM records WHERE kind='incident'")]
    assert after==original_incidents,'Active incidents were changed by isolated tests'
print(json.dumps({'passed':sum(r['status']=='PASS' for r in RESULTS),'failed':sum(r['status']=='FAIL' for r in RESULTS),'active_incidents_preserved':len(original_incidents)}),flush=True)
sys.exit(any(r['status']=='FAIL' for r in RESULTS))
