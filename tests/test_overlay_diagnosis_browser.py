"""Actual isolated HTTP + browser workflow. Never sends Telegram or touches existing services."""
from pathlib import Path
import json,os,subprocess,sys,time,traceback,shutil
import httpx

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
sys.stdout.reconfigure(encoding='utf-8')
OUT=ROOT/'runtime/overlay-diagnosis/fresh'
OUT.mkdir(parents=True,exist_ok=True)
RESULTS=[]
ENV=os.environ.copy()
ENV.update(SAFESENSE_DB_PATH=str(OUT/('test-'+str(int(time.time()))+'.sqlite3')),
           SAFESENSE_BACKEND_URL='http://127.0.0.1:18000',TELEGRAM_MODE='disabled',
           SAFESENSE_AI_URL='http://127.0.0.1:18001',
           VITE_API_BASE_URL='http://127.0.0.1:18000',VITE_AI_BASE_URL='http://127.0.0.1:18001',SAFESENSE_DASHBOARD_URL='http://127.0.0.1:3001',
           SAFESENSE_API_TOKEN='monitoring-integration-test',VITE_SAFESENSE_API_TOKEN='monitoring-integration-test')
ENV.update(SAFESENSE_EVIDENCE_DIR=str(OUT/'evidence'),SAFESENSE_ANNOTATION_DIR=str(OUT/'annotations'),SAFESENSE_ANALYSIS_CACHE_DIR=str(OUT/'cache'),SAFESENSE_PRECOMPUTE_ON_START='false')
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
try:
    start('backend',[sys.executable,'-m','uvicorn','backend.main:app','--host','127.0.0.1','--port','18000'],B+'/health')
    start('inference',[sys.executable,'-m','uvicorn','fight_api:app','--host','127.0.0.1','--port','18001'],A+'/health')
    start('frontend',[shutil.which('node'),str(ROOT/'dashboard/node_modules/vite/bin/vite.js'),'--host','127.0.0.1','--port','3001','--strictPort'],'http://127.0.0.1:3001',ROOT/'dashboard')
    from playwright.sync_api import sync_playwright,expect as browser_expect
    from backend.registry import source
    import cv2,numpy as np
    from ultralytics import YOLO
    with sync_playwright() as pw:
        browser=pw.chromium.launch(headless=True);page=browser.new_page(viewport={'width':1500,'height':1050});page.set_default_timeout(20000)
        errors=[];page.on('pageerror',lambda e:errors.append(str(e)));completed={}
        def response(r):
            if '/monitoring/jobs' in r.url and r.status in (200,202):
                try:
                    row=r.json()
                    if row.get('status')=='COMPLETED':completed[row['camera_id']]=row
                except Exception:pass
        page.on('response',response)
        page.goto('http://127.0.0.1:3001');page.locator('aside').get_by_role('button',name='Live Monitoring',exact=True).click()
        panel=page.get_by_test_id('camera-monitoring');video=panel.locator('video').first
        def camera(name,identifier,scenario):
            began=time.perf_counter()
            panel.get_by_role('button',name=name+' '+identifier+' RECORDED REAL VIDEO',exact=True).click()
            browser_expect(video).to_have_attribute('data-camera-id',identifier)
            browser_expect(panel.get_by_test_id('video-detection-overlay')).to_have_attribute('data-camera-id',identifier)
            assert panel.get_by_test_id('person-box').count()==0,'Old camera boxes persisted'
            page.wait_for_function("()=>{const v=document.querySelector('[data-testid=camera-monitoring] video');return v.readyState>=2&&!v.paused&&v.currentTime>0.1}")
            browser_expect(panel.get_by_test_id('fight-video-overlay')).to_be_visible(timeout=240000)
            row=completed[identifier];r=row['result'];saved[scenario]=r
            (OUT/(identifier+'-inference.json')).write_text(json.dumps(row),encoding='utf-8')
            page.wait_for_function("()=>{const v=document.querySelector('[data-testid=camera-monitoring] video');return !v.paused&&document.querySelectorAll('[data-testid=camera-monitoring] [data-testid=pose-bone]').length>0}")
            first=video.evaluate('v=>v.currentTime');first_frame=panel.get_by_test_id('video-detection-overlay').get_attribute('data-frame-index')
            page.wait_for_timeout(180)
            second=video.evaluate('v=>v.currentTime');second_frame=panel.get_by_test_id('video-detection-overlay').get_attribute('data-frame-index')
            assert second>first and second_frame!=first_frame
            playback_ms=round((time.perf_counter()-began)*1000,2)
            video.evaluate('v=>v.pause()');page.wait_for_timeout(70)
            video.locator('..').screenshot(path=str(OUT/(identifier+'-actual-playback.png')))
            geometry=panel.get_by_test_id('pose-overlay').evaluate("s=>{const v=s.parentElement.parentElement.querySelector('video'),box=s.querySelector('[data-testid=person-box]'),m=s.getScreenCTM(),r=v.getBoundingClientRect(),b=box.getBoundingClientRect();const scale=Math.min(r.width/v.videoWidth,r.height/v.videoHeight);return {video:[v.videoWidth,v.videoHeight],viewBox:s.getAttribute('viewBox'),transform:[m.a,m.d],scale,box:[b.x,b.y],expected:[r.x+(r.width-v.videoWidth*scale)/2+Number(box.getAttribute('x'))*scale,r.y+(r.height-v.videoHeight*scale)/2+Number(box.getAttribute('y'))*scale]};}")
            assert np.allclose(geometry['box'],geometry['expected'],atol=1),geometry
            assert np.allclose(geometry['transform'],[geometry['scale']]*2,atol=.001),geometry
            (OUT/(identifier+'-playback-proof.json')).write_text(json.dumps({'first_pose_playback_observed_ms':playback_ms,'playing_times':[first,second],'pose_frame_indices':[first_frame,second_frame],'geometry':geometry},indent=2),encoding='utf-8')
            assert '/monitoring/sources/'+scenario+'?' in video.get_attribute('src'),'Dynamic overlays must use the original recording without duplicate baked skeletons'
            assert r['camera_id']==identifier and not r['model_errors']
            pose=next(m for m in r['model_results'] if m['model_version'].startswith('yolo'))
            assert len(r['pose_frames'])==pose['processed_frames']==r['annotation_alignment']['frame_count']
            for i,f in enumerate(r['pose_frames']):
                assert f['frame_index']==i and abs(f['time_sec']-i/r['annotation_alignment']['fps'])<1e-6
                assert f['fall_score'] is None and f['fall_state'] in ('NORMAL','POSSIBLE FALL','FALL CANDIDATE')
                for j,p in enumerate(f['persons']):
                    assert len(p['bbox_xyxy'])==4 and len(p['keypoints'])==17
                    assert p['fall_candidate']==(p['fall_rule_active'] and p['fall_state']=='POSSIBLE FALL' and p['posture']=='horizontal')
                    if p['fall_candidate']:assert p['track_id']>0 and p['track_age']>=8 and p['fall_score'] is None
            samples=[f for f in r['pose_frames'] if f['persons'] and any(k['confidence'] and k['confidence']>=.5 for p in f['persons'] for k in p['keypoints'])]
            assert samples,'Actual recording has no confident pose sample'
            seen=[]
            for f in [samples[len(samples)//4],samples[len(samples)//2],samples[-2]]:
                target=f['time_sec']+.001
                video.evaluate('(v,t)=>{v.pause();v.currentTime=t}',target)
                page.wait_for_function("i=>document.querySelector('[data-testid=video-detection-overlay]').dataset.frameIndex===String(i)",arg=f['frame_index'])
                boxes=panel.get_by_test_id('person-box');assert boxes.count()==len(f['persons'])
                for idx,p in enumerate(f['persons']):
                    attrs=boxes.nth(idx).evaluate('(e)=>[e.getAttribute("x"),e.getAttribute("y"),e.getAttribute("width"),e.getAttribute("height")].map(Number)')
                    x1,y1,x2,y2=p['bbox_xyxy'];assert np.allclose(attrs,[x1,y1,x2-x1,y2-y1])
                assert panel.get_by_test_id('pose-bone').count()>0
                assert panel.get_by_test_id('frame-detections').get_attribute('data-frame-index')==str(f['frame_index'])
                seen.append(f['frame_index'])
            f=samples[len(samples)//2];_,path=source(scenario);cap=cv2.VideoCapture(str(path));cap.set(cv2.CAP_PROP_POS_FRAMES,f['frame_index']);ok,image=cap.read();cap.release();assert ok
            pred=YOLO(str(ROOT/'yolo11n-pose.pt')).predict(image,device='cpu',conf=.25,imgsz=640,verbose=False)[0]
            assert len(pred.boxes)==len(f['persons'])
            for person,box in zip(f['persons'],pred.boxes.xyxy.cpu().tolist()):assert np.allclose(person['bbox_xyxy'],box,atol=.001)
            fight=next(m for m in r['model_results'] if m['model_version'] in ('v2','v3'))
            assert fight['prediction'] in panel.get_by_test_id('fight-timeline-result').inner_text()
            assert f"{fight['score']:.4f}" in panel.get_by_test_id('fight-video-overlay').inner_text()
            assert not fight.get('pose_frames') and not fight.get('events')
            page.screenshot(path=str(OUT/(identifier+'.png')),full_page=True)
            panel.get_by_role('button',name='Replay',exact=True).click();page.wait_for_function("()=>{const v=document.querySelector('[data-testid=camera-monitoring] video');return !v.paused&&v.currentTime>.1&&v.currentTime<1}")
            video.evaluate('(v)=>v.pause()')
            return {'camera':identifier,'scenario':scenario,'frames':len(r['pose_frames']),'nonempty_pose_frames':sum(bool(f['persons']) for f in r['pose_frames']),'person_detection_instances':sum(len(f['persons']) for f in r['pose_frames']),'actual_playback_ms':playback_ms,'persons':max(len(f['persons']) for f in samples),'seek_frames':seen,'fall_candidates':pose['candidate_frames'],'fight_label':fight['prediction'],'fight_score':fight['score'],'autoplay':True,'independent_YOLO_match':True}
        check('School Entrance actual recording: boxes, skeletons, scores, seeks and replay',lambda:camera('School Entrance','CAM_ENTRANCE','adl_01'))
        check('School Hall actual recording: boxes, skeletons, scores, seeks and replay',lambda:camera('School Hall','CAM_HALL','adl_02'))
        def fall_box():
            r=camera_job('fall','CAM_STAIRCASE','ZONE_STAIRCASE')['result']
            saved['fall']=r
            candidates=[f for f in r['pose_frames'] if any(p['fall_candidate'] for p in f['persons'])];assert candidates
            panel.get_by_role('button',name='Staircase CAM_STAIRCASE RECORDED REAL VIDEO',exact=True).click()
            browser_expect(panel.get_by_test_id('fight-video-overlay')).to_be_visible(timeout=240000)
            f=candidates[len(candidates)//2];video.evaluate('(v,t)=>{v.pause();v.currentTime=t}',f['time_sec']+.001)
            page.wait_for_function("i=>document.querySelector('[data-testid=video-detection-overlay]').dataset.frameIndex===String(i)",arg=f['frame_index'])
            candidate=panel.locator('[data-fall-candidate=true]');assert candidate.count()==1
            browser_expect(candidate.locator('text')).to_contain_text('POSSIBLE FALL');browser_expect(candidate.locator('text')).to_contain_text('binary rule ACTIVE')
            assert candidate.locator('rect').first.get_attribute('stroke')=='#ef4444'
            page.screenshot(path=str(OUT/'actual-fall-overlay.png'),full_page=True)
            return {'real_candidate_frame':f['frame_index'],'colored_box':True,'score':'person confidence only; fall score unavailable'}
        check('Actual fall recording: colored rule box and truthful confidence',fall_box)
        def airtlab():
            r=camera_job('conflict','CAM_CORRIDOR_A','ZONE_CORRIDOR_A')['result'];saved['conflict']=r
            panel.get_by_role('button',name='Corridor A CAM_CORRIDOR_A RECORDED REAL VIDEO',exact=True).click()
            browser_expect(panel.get_by_test_id('fight-video-overlay')).to_be_visible(timeout=240000)
            fight=next(m for m in r['model_results'] if m['model_version']=='v3')
            banner=panel.get_by_test_id('fight-video-overlay')
            assert fight['candidate_detected'] and 'POSSIBLE FIGHT' in banner.inner_text()
            assert 'uncalibrated' in banner.inner_text() and f"{fight['score']:.4f}" in banner.inner_text()
            assert not panel.locator('[data-fighter]').count()
            page.screenshot(path=str(OUT/'actual-airtlab-fight.png'),full_page=True)
            return {'model':fight['model_version'],'score':fight['score'],'whole_video_banner':True,'fighter_boxes':0,'frames':len(r['pose_frames'])}
        check('Actual AIRTLab positive fight banner, genuine score and no fighter localization',airtlab)
        def switch():
            for name in ['School Entrance CAM_ENTRANCE RECORDED REAL VIDEO','School Hall CAM_HALL RECORDED REAL VIDEO']:
                panel.get_by_role('button',name=name,exact=True).click()
            browser_expect(video).to_have_attribute('data-camera-id','CAM_HALL')
            browser_expect(panel.get_by_test_id('fight-video-overlay')).to_be_visible(timeout=240000)
            assert panel.get_by_test_id('video-detection-overlay').get_attribute('data-camera-id')=='CAM_HALL'
            assert completed['CAM_HALL']['result']['camera_id']=='CAM_HALL'
            page.set_viewport_size({'width':390,'height':844});page.wait_for_timeout(300)
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
            page.screenshot(path=str(OUT/'mobile-overlay.png'),full_page=True)
            return {'rapid_switch':'CAM_HALL','no_overflow':True,'browser_errors':errors}
        check('Rapid camera switching and mobile layout',switch)
        def v2():
            r=job('adl_01','v2','ZONE_ENTRANCE')['result'];assert 0<=r['score']<=1 and r['prediction'];assert not r.get('pose_frames') and not r.get('events')
            return {'label':r['prediction'],'score':r['score'],'whole_clip_only':True}
        check('Actual V2 output remains whole-clip classification',v2)
        def evidence_integration():
            r=saved['fall'];pose=next(m for m in r['model_results'] if m['model_version'].startswith('yolo'))
            delivery=pose['event_delivery'];assert delivery.get('incident_id'),delivery
            incident=expect(client.get(B+'/incidents/'+delivery['incident_id']+'/report'))
            assert incident['zone_id']=='ZONE_STAIRCASE' and incident['evidence']
            media=pose['evidence_media'];assert media
            for item in media:
                assert client.get(A+item['url'],headers={'Range':'bytes=0-1023'}).status_code==206
                manifest=expect(client.get(A+'/monitoring/incidents/'+incident['id']+'/evidence/'+item['id']+'/metadata'))
                overlay=manifest['overlay_result'];assert overlay['analysis_id']==pose['analysis_id'] and overlay['input_sha256']==pose['input_sha256']
                assert any(p['fall_rule_active'] for f in overlay['pose_frames'] for p in f['persons'])
            page.locator('aside').get_by_role('button',name='Digital Twin Map',exact=True).click()
            browser_expect(page.locator('main')).to_be_visible()
            page.locator('aside').get_by_role('button',name='Alerts',exact=True).click()
            browser_expect(page.locator('main')).to_be_visible()
            return {'incident':incident['id'],'zone':incident['zone_id'],'retained_evidence':len(media),'alerts_and_digital_twin_navigation':True}
        check('Actual fall evidence and incident delivery, Alerts and Digital Twin preserved',evidence_integration)
        def cached_replay():
            began=time.perf_counter()
            row=expect(client.post(A+'/monitoring/jobs',json={'scenario_id':'fall','camera_id':'CAM_STAIRCASE','zone_id':'ZONE_STAIRCASE','model':'all','authorized':True}),202)
            assert row.get('cache_hit') and row['status']=='COMPLETED'
            result=row['result'];assert result['pose_frames']==saved['fall']['pose_frames']
            elapsed_ms=round((time.perf_counter()-began)*1000,2)
            private=client.post(A+'/monitoring/jobs',json={'scenario_id':'fall','camera_id':'CAM_STAIRCASE','zone_id':'ZONE_TOILET_BLINDSPOT','model':'all','authorized':True})
            assert private.status_code==403
            return {'request_ms':elapsed_ms,'cache_tier':row.get('cache_tier'),'frames':len(result['pose_frames']),'exact_cached_results':True,'private_media_rejected':403}
        check('Genuine cached replay returns exact frame metadata without inference; private video refused',cached_replay)
        def audits():
            page.set_viewport_size({'width':1500,'height':1050})
            page.locator('aside').get_by_role('button',name='Incident Review',exact=True).click()
            inspected=[]
            for scenario in ('fall','conflict'):
                result=saved[scenario]
                output=next(m for m in result['model_results'] if (m['model_version'].startswith('yolo') if scenario=='fall' else m['model_version']=='v3'))
                identifier=output['event_delivery']['incident_id'];item=output['evidence_media'][0]
                page.get_by_placeholder('Search notes, staff, incident #...').fill(identifier[:8])
                page.get_by_role('button',name='Audit Details',exact=True).click()
                section=page.get_by_test_id('incident-evidence');browser_expect(section).to_have_attribute('data-incident-id',identifier)
                clip=section.locator('video');browser_expect(clip).to_have_attribute('data-variant','original')
                page.wait_for_function("()=>{const v=document.querySelector('[data-testid=incident-evidence] video');return v?.readyState>=2&&!v.paused}")
                if scenario=='fall':
                    frame=next(f for f in result['pose_frames'] if any(p['fall_rule_active'] for p in f['persons']))
                    clip.evaluate('(v,t)=>{v.pause();v.currentTime=t}',frame['time_sec']-item['start_sec']+.001)
                    page.wait_for_function("()=>{const v=document.querySelector('[data-testid=incident-evidence] video');return v?.readyState>=2&&!v.seeking&&v.paused}")
                    browser_expect(section.locator('[data-fall-candidate=true]')).to_be_visible()
                    clip.scroll_into_view_if_needed()
                    clip.screenshot(path=str(OUT/'fall-audit-genuine-overlay.png'))
                    section.get_by_role('button',name='Show annotated clip',exact=True).click()
                    browser_expect(clip).to_have_attribute('data-variant','annotated')
                    assert section.get_by_test_id('video-detection-overlay').count()==0
                else:
                    browser_expect(section.get_by_test_id('fight-video-overlay')).to_contain_text('POSSIBLE FIGHT')
                    assert section.get_by_test_id('person-box').count()==0
                    page.screenshot(path=str(OUT/'fight-audit-genuine-overlay.png'),full_page=True)
                inspected.append({'incident':identifier,'scenario':scenario,'matching_analysis':output['analysis_id']})
                page.get_by_role('button',name='Close',exact=True).click()
            return inspected
        check('Audit Details plays matching fall and fight evidence with genuine synchronized overlays',audits)
        def alias_and_fallback():
            row=expect(client.post(A+'/monitoring/jobs',json={'scenario_id':'adl_02','camera_id':' School Hall ','zone_id':'ZONE_SCHOOL_HALL','model':'all','authorized':True}),202)
            assert row.get('cache_hit') and row['result']['camera_id']=='CAM_HALL'
            assert client.post(A+'/monitoring/jobs',json={'scenario_id':'adl_02','camera_id':'unknown hall','zone_id':'ZONE_SCHOOL_HALL','model':'all','authorized':True}).status_code==422
            fallback=browser.new_page(viewport={'width':1500,'height':1050})
            fallback.add_init_script("Object.defineProperty(HTMLVideoElement.prototype,'requestVideoFrameCallback',{value:undefined});")
            fallback.goto('http://127.0.0.1:3001');fallback.locator('aside').get_by_role('button',name='Live Monitoring',exact=True).click()
            cp=fallback.get_by_test_id('camera-monitoring');cp.get_by_role('button',name='School Entrance CAM_ENTRANCE RECORDED REAL VIDEO',exact=True).click()
            browser_expect(cp.get_by_test_id('pose-overlay')).to_be_visible()
            fallback.wait_for_function("()=>document.querySelectorAll('[data-testid=pose-bone]').length>0")
            current=cp.get_by_test_id('video-detection-overlay').get_attribute('data-frame-index');fallback.wait_for_timeout(180)
            later=cp.get_by_test_id('video-detection-overlay').get_attribute('data-frame-index');assert current!=later
            cp.locator('video').evaluate('v=>v.pause()');cp.locator('video').locator('..').screenshot(path=str(OUT/'fallback-playback.png'))
            fallback.close()
            return {'registered_alias_normalized':'CAM_HALL','unknown_identity_rejected':422,'without_rVFC_frames':[current,later],'fallback_pose_visible':True}
        check('Shared registry normalization stays fail-closed; browser playback works without rVFC',alias_and_fallback)
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
print(json.dumps({'passed':sum(r['status']=='PASS' for r in RESULTS),'failed':sum(r['status']=='FAIL' for r in RESULTS)}),flush=True)
sys.exit(any(r['status']=='FAIL' for r in RESULTS))
