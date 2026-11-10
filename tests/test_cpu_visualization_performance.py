"""Actual isolated HTTP + browser workflow. Never sends Telegram or touches existing services."""
from pathlib import Path
import json,os,subprocess,sys,time,traceback,shutil
import httpx

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
sys.stdout.reconfigure(encoding='utf-8')
MODE='baseline' if '--baseline' in sys.argv else 'optimized'
OUT=ROOT/'runtime/cpu-visualization'/MODE
OUT.mkdir(parents=True,exist_ok=True)
RESULTS=[]
ENV=os.environ.copy()
ENV.update(SAFESENSE_DB_PATH=str(OUT/('test-'+str(int(time.time()))+'.sqlite3')),
           SAFESENSE_BACKEND_URL='http://127.0.0.1:18140',TELEGRAM_MODE='disabled',
           SAFESENSE_AI_URL='http://127.0.0.1:18141',
           VITE_API_BASE_URL='http://127.0.0.1:18140',VITE_AI_BASE_URL='http://127.0.0.1:18141',SAFESENSE_DASHBOARD_URL='http://127.0.0.1:3001',
           SAFESENSE_API_TOKEN='monitoring-integration-test',VITE_SAFESENSE_API_TOKEN='monitoring-integration-test')
H={'X-SafeSense-Token':ENV['SAFESENSE_API_TOKEN']}
B='http://127.0.0.1:18140';A='http://127.0.0.1:18141'
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
ENV['SAFESENSE_EVIDENCE_DIR']=str(OUT/('evidence-'+str(time.time_ns())))
ENV['SAFESENSE_ANALYSIS_CACHE_DIR']=str(OUT/'analysis-cache')
ENV['SAFESENSE_PRECOMPUTE_ON_START']='false'
ENV['SAFESENSE_ANNOTATION_DIR']=str(OUT/('annotations-'+str(time.time_ns())))
try:
    start('backend',[sys.executable,'-m','uvicorn','backend.main:app','--host','127.0.0.1','--port','18140'],B+'/health')
    ai_command=[sys.executable,'-m','uvicorn','fight_api:app','--host','127.0.0.1','--port','18141']
    service=start('inference',ai_command,A+'/health')
    start('frontend',[shutil.which('node'),str(ROOT/'dashboard/node_modules/vite/bin/vite.js'),'--host','127.0.0.1','--port','3001','--strictPort'],'http://127.0.0.1:3001',ROOT/'dashboard')
    from playwright.sync_api import sync_playwright,expect as be
    measurements=[];completed={};errors=[]
    with sync_playwright() as pw:
        browser=pw.chromium.launch(headless=True);page=browser.new_page(viewport={'width':1500,'height':1050});page.set_default_timeout(20000)
        page.on('pageerror',lambda e:errors.append(str(e)))
        def response(r):
            if '/monitoring/jobs' in r.url and r.status in (200,202):
                try:
                    row=r.json()
                    if row.get('status')=='COMPLETED':completed[row['camera_id']]=row
                except Exception:pass
        page.on('response',response)
        page.goto('http://127.0.0.1:3001');page.locator('aside').get_by_role('button',name='Live Monitoring',exact=True).click();panel=page.get_by_test_id('camera-monitoring')
        def choose(name,camera,kind):
            completed.pop(camera,None)
            page.evaluate("""()=>{window.__videoReady=null;window.__cameraClicked=performance.now();const once=e=>{if(e.target.tagName==='VIDEO'&&e.target.closest('[data-testid=camera-monitoring]')){document.removeEventListener('playing',once,true);const done=()=>{window.__videoReady=performance.now()-window.__cameraClicked};if(e.target.requestVideoFrameCallback)e.target.requestVideoFrameCallback(done);else done();}};document.addEventListener('playing',once,true);} """)
            started=time.perf_counter();panel.get_by_role('button',name=name+' '+camera+' RECORDED REAL VIDEO',exact=True).click()
            page.wait_for_function('()=>window.__videoReady!==null',timeout=20000);video_ms=page.evaluate('window.__videoReady')
            be(panel.get_by_test_id('fight-video-overlay')).to_be_visible(timeout=240000)
            for _ in range(100):
                if camera in completed:break
                page.wait_for_timeout(20)
            row=completed[camera];result=row['result'];elapsed=(time.perf_counter()-started)*1000
            assert result['camera_id']==camera and not result['model_errors']
            assert len(result['model_results'])==2 and result['model_results'][0]['model_version']=='v3'
            assert any(f['persons'] for f in result['pose_frames'])
            for f in result['pose_frames']:assert abs(f['time_sec']-f['frame_index']/result['annotation_alignment']['fps'])<1e-6
            sample={'camera':camera,'kind':kind,'video_first_decoded_frame_ms':round(video_ms,2),'click_to_analysis_render_ms':round(elapsed,2),'cache_hit':row.get('cache_hit',False),'cache_tier':row.get('cache_tier'),'original_processing_sec':result['total_processing_sec'],'models':[{key:m.get(key) for key in ['model_version','score','inference_time_sec','inference_fps','profile']} for m in result['model_results']],'queue_delay_sec':result['queue_delay_sec'],'id':row['id'],'pose_frames':len(result['pose_frames']),'server_lookup_sec':row.get('request_lookup_sec'),'frontend_timings':panel.get_by_test_id('monitoring-timing').text_content() if MODE!='baseline' else 'Not instrumented in baseline'}
            measurements.append(sample);(OUT/'performance.json').write_text(json.dumps(measurements,indent=2));print(json.dumps({k:v for k,v in sample.items() if k!='models'}),flush=True)
            if kind!='cold' and MODE!='baseline':assert row.get('cache_hit') or row.get('deduplicated'),row
            return row
        entrance=choose('School Entrance','CAM_ENTRANCE','cold')
        hall=choose('School Hall','CAM_HALL','cold')
        before=expect(client.get(B+'/state'))
        warm=choose('School Entrance','CAM_ENTRANCE','memory_cached');assert warm['id']==entrance['id']
        # Simulate a genuine service restart; recordings and the isolated SQLite store remain.
        service.terminate();service.wait(timeout=10);service=start('inference-restarted',ai_command,A+'/health')
        restarted=choose('School Hall','CAM_HALL','after_service_restart')
        if MODE!='baseline':
            assert restarted['id']==hall['id'] and restarted.get('cache_tier')=='disk'
            after=expect(client.get(B+'/state'));assert len(after['events'])==len(before['events']) and len(after['incidents'])==len(before['incidents'])
        if MODE!='baseline':
            # Warm every registered recording sequentially, then verify a pure-cache repeat.
            command=[sys.executable,str(ROOT/'scripts/precompute_monitoring.py'),'--backend',B,'--ai',A]
            first=subprocess.run(command+['--output',str(OUT/'precompute-all.json')],env=ENV,cwd=ROOT,capture_output=True,text=True,timeout=240);assert first.returncode==0,first.stderr
            before=expect(client.get(B+'/state'))
            second=subprocess.run(command+['--output',str(OUT/'precompute-all-repeated.json')],env=ENV,cwd=ROOT,capture_output=True,text=True,timeout=60);assert second.returncode==0,second.stderr
            rows=json.loads((OUT/'precompute-all-repeated.json').read_text());assert len(rows)==5 and all(r['cache_hit'] and len(r['models'])==2 for r in rows),rows
            after=expect(client.get(B+'/state'));assert len(after['events'])==len(before['events']) and len(after['incidents'])==len(before['incidents'])
            corridor=next(r for r in rows if r['camera_id']=='CAM_CORRIDOR_A');prepared=expect(client.get(A+'/monitoring/jobs/'+corridor['job_id']))['result'];assert prepared['evidence_media'] and prepared['event_delivery']['incident_id']
            incident=expect(client.get(B+'/incidents/'+prepared['event_delivery']['incident_id']+'/report'));assert incident['zone_id']=='ZONE_CORRIDOR_A'
            media=prepared['evidence_media'][0];assert client.get(A+media['url'],headers={'Range':'bytes=0-1023'}).status_code==206
            # Stale selection cannot supersede the newest camera, even on a cache hit.
            cams=expect(client.get(B+'/monitoring/cameras'));hall_camera=next(c for c in cams if c['camera_id']=='CAM_HALL')
            payload={'scenario_id':hall_camera['scenario_id'],'camera_id':'CAM_HALL','zone_id':hall_camera['zone_id'],'model':'all','authorized':True,'client_id':'sequence-check','selection_seq':20}
            assert expect(client.post(A+'/monitoring/jobs',json=payload),202)['cache_hit'];assert client.post(A+'/monitoring/jobs',json={**payload,'selection_seq':19}).status_code==409
            assert client.post(A+'/monitoring/jobs',json={**payload,'zone_id':'ZONE_TOILET_BLINDSPOT'}).status_code==403
            (OUT/'integration-results.json').write_text(json.dumps({'status':'PASS','cameras_precomputed':5,'repeat_all_cache_hits':True,'duplicate_events':False,'evidence_clip_seekable':True,'incident_preserved':True,'stale_selection_rejected':True,'private_video_rejected':True},indent=2))
            print('PASS all five genuine recording caches, unchanged events on replay, evidence/incident and private/stale-selection checks',flush=True)
            # Exercise real running + obsolete queued work without cancelling the active CPU model.
            def forced(camera,sequence,owner='queue-switch'):
                return expect(client.post(A+'/monitoring/jobs',json={'scenario_id':camera['scenario_id'],'camera_id':camera['camera_id'],'zone_id':camera['zone_id'],'model':'all','authorized':True,'force':True,'client_id':owner,'selection_seq':sequence}),202)
            first_camera=next(c for c in cams if c['camera_id']=='CAM_CORRIDOR_A');old_camera=next(c for c in cams if c['camera_id']=='CAM_ENTRANCE')
            active=forced(first_camera,1)
            for _ in range(200):
                active_row=expect(client.get(A+'/monitoring/jobs/'+active['id']))
                if active_row['status']=='RUNNING':break
                time.sleep(.03)
            assert active_row['status']=='RUNNING'
            duplicate=forced(first_camera,1,'second-viewer');assert duplicate['id']==active['id'] and duplicate['deduplicated']
            obsolete=forced(old_camera,2);latest=forced(hall_camera,3)
            assert expect(client.get(A+'/monitoring/jobs/'+obsolete['id']))['status']=='CANCELLED'
            for accepted in (active,latest):
                for _ in range(600):
                    done=expect(client.get(A+'/monitoring/jobs/'+accepted['id']))
                    if done['status']=='COMPLETED':break
                    assert done['status'] in ('QUEUED','RUNNING'),done
                    time.sleep(.1)
                assert done['status']=='COMPLETED'
            (OUT/'queue-switch-results.json').write_text(json.dumps({'status':'PASS','active_duplicate_same_job':True,'obsolete_queued_cancelled':True,'running_job_not_interrupted':True,'latest_camera_completed':True},indent=2))
            print('PASS actual CPU job coalescing and safe queued camera-switch cancellation',flush=True)

        page.screenshot(path=str(OUT/'cached-monitoring.png'),full_page=True)
        assert not errors,errors;browser.close()
    print('PASS real CPU profiling, playback, pose timestamps and cached camera replay',flush=True)
finally:
    for process,log in reversed(processes):
        if process.poll() is None:
            process.terminate()
            try:process.wait(timeout=10)
            except subprocess.TimeoutExpired:process.kill()
        log.close()
    client.close()
