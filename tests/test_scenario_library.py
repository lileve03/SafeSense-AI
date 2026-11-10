"""Execute every fresh local scenario end to end; never send external notifications."""
from pathlib import Path
import hashlib,json,os,subprocess,sys,time,traceback,shutil
import httpx
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.stdout.reconfigure(encoding='utf-8')
from backend import registry,scenario_catalog
OUT=ROOT/'runtime/scenario-library-tests';OUT.mkdir(parents=True,exist_ok=True)
ROWS=[];PROCESSES=[];RUNS={}
ENV={**os.environ,'SAFESENSE_API_TOKEN':'scenario-library-test','TELEGRAM_MODE':'disabled','TELEGRAM_STAFF_DISPATCH_ENABLED':'false',
     'SAFESENSE_DB_PATH':str(OUT/('test-'+str(time.time_ns())+'.sqlite3')),'SAFESENSE_BACKEND_URL':'http://127.0.0.1:18100',
     'SAFESENSE_AI_URL':'http://127.0.0.1:18101','VITE_SAFESENSE_API_TOKEN':'scenario-library-test',
     'VITE_API_BASE_URL':'http://127.0.0.1:18100','VITE_AI_BASE_URL':'http://127.0.0.1:18101'}
B='http://127.0.0.1:18100';H={'X-SafeSense-Token':ENV['SAFESENSE_API_TOKEN']}
CLIENT=httpx.Client(headers=H,timeout=20)

def check(name,fn):
    started=time.perf_counter()
    try:row={'test':name,'status':'PASS','actual':fn()}
    except Exception as exc:row={'test':name,'status':'FAIL','actual':str(exc),'trace':traceback.format_exc()}
    row['seconds']=round(time.perf_counter()-started,3);ROWS.append(row)
    (OUT/'results.json').write_text(json.dumps(ROWS,indent=2),encoding='utf-8')
    print(row['status'],name,str(row['actual'])[:700],flush=True)

def expect(response,code=200):
    assert response.status_code==code,(response.status_code,response.text[:800])
    return response.json()

def start(name,command,url,cwd=ROOT):
    log=(OUT/(name+'.log')).open('w',encoding='utf-8')
    process=subprocess.Popen(command,cwd=cwd,env=ENV,stdout=log,stderr=subprocess.STDOUT,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0));PROCESSES.append((process,log))
    for _ in range(240):
        if process.poll() is not None:raise RuntimeError(name+' exited; inspect '+str(OUT/(name+'.log')))
        try:
            if httpx.get(url,timeout=1).status_code==200:return process
        except httpx.HTTPError:pass
        time.sleep(.25)
    raise TimeoutError(name+' startup timeout')

def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
IMMUTABLE=[ROOT/'yolo11n-pose.pt',ROOT/'yolo11n.pt',ROOT/'evaluation/outputs/fight_multiclip_v2/fight_multiclip_classifier.joblib',ROOT/'evaluation/outputs/fight_v3/fight_v3_classifier.joblib',ROOT/'evaluation/outputs/radar_route_a/radar_features.csv',ROOT/'evaluation/outputs/radar_route_a/radar_predictions.csv',ROOT/'evaluation/outputs/yamnet/yamnet_predictions.csv']
IMMUTABLE += [ROOT/s['path'] for s in registry.scenarios() if s['input_type'] in ('video','radar_recording','audio_sample')]
BEFORE={p.relative_to(ROOT).as_posix():digest(p) for p in IMMUTABLE}

def execute(source,model=None):
    model=model or source['default_model']
    row=expect(CLIENT.post(B+'/testing/runs',json={'scenario_id':source['id'],'model':model,'authorized':True}),202)
    deadline=time.monotonic()+320
    while time.monotonic()<deadline:
        row=expect(CLIENT.get(B+'/testing/runs/'+row['id']))
        if row['status']=='COMPLETED':return row
        assert row['status'] in ('QUEUED','RUNNING'),row
        time.sleep(.5)
    raise TimeoutError('Scenario '+source['id']+' timed out')

try:
    backend=start('backend',[sys.executable,'-m','uvicorn','backend.main:app','--host','127.0.0.1','--port','18100'],B+'/health')
    start('inference',[sys.executable,'-m','uvicorn','fight_api:app','--host','127.0.0.1','--port','18101'],'http://127.0.0.1:18101/health')
    catalog=expect(CLIENT.get(B+'/testing/scenarios'));fresh=[s for s in catalog if s['execution_kind']=='fresh_inference']
    def sources():
        assert len(catalog)==17 and len(fresh)==12
        assert all(s['ready'] for s in fresh),[(s['id'],s['unavailable_reason']) for s in fresh]
        assert {s['execution_kind'] for s in catalog}=={'fresh_inference','saved_prediction_replay','controlled_test'}
        return {'registry':len(catalog),'fresh_inputs':len(fresh),'video':sum(s['input_type']=='video' for s in fresh),'raw_sensor':sum(s['input_type']!='video' for s in fresh)}
    check('Audit registered inputs and distinguish fresh/replay/simulation',sources)
    for source in fresh:
        def actual(source=source):
            row=execute(source);RUNS[source['id']]=row;result=row['result']
            if source['input_type']!='video':
                assert result['output_origin']=='fresh_raw_input_inference'
                assert result['input_sha256']==BEFORE[source['path']]
                assert abs(result['score']-source['reference_score'])<1e-4,(result['score'],source['reference_score'])
                assert result['event_delivery']['status']=='recorded'
                if result['candidate_detected']:
                    incident=expect(CLIENT.get(B+'/incidents/'+result['event_delivery']['incident_id']+'/report'))
                    assert incident['level']=='OBSERVE',incident
                    assert not any(e.get('evidence_media') for e in incident['evidence'])
                    assert incident['evidence'][0]['analysis_run_id']==row['id']
                if source['kind']=='radar':assert result['training_subject_excluded']=='areeb' and result['n_points']>0
            else:
                for output in result.get('model_results',[result]):
                    assert output['event_delivery']['status']=='recorded'
                    if output['candidate_detected']:assert output['evidence_media'],output
            return {'run_id':row['id'],'input':source['path'],'model':row['model'],'score':result.get('score'),'candidate':result['candidate_detected'],'matches_dataset_label':row['matches_ground_truth'],'comparisons':row['ground_truth_comparisons'],'seconds':row['wall_time_sec']}
        check('Fresh inference: '+source['id'],actual)
    def radar_forest():
        import csv
        source=next(s for s in fresh if s['id']=='radar_raw_fall')
        row=execute(source,'RandomForest');result=row['result']
        reference=next(r for r in csv.DictReader((ROOT/'evaluation/outputs/radar_route_a/radar_predictions.csv').open(encoding='utf-8-sig')) if r['model']=='RandomForest' and r['file'].replace('\\','/').endswith('Fall/Areeb_back_1.csv'))
        assert abs(result['score']-float(reference['fall_probability']))<1e-4
        return {'model':result['model_version'],'actual_score':result['score'],'saved_reference':reference['fall_probability'],'held_out_subject':result['training_subject_excluded']}
    check('Fresh raw radar RandomForest benchmark route',radar_forest)
    def negative_controls():
        for identifier in ('normal','normal_cam2','adl_01','adl_02','radar_raw_normal','acoustic_background'):
            assert identifier in RUNS
            assert 'ground_truth_comparisons' in RUNS[identifier]
        radar=RUNS['radar_raw_normal']['result'];audio=RUNS['acoustic_background']['result']
        assert 0<radar['score']<1 and 0<audio['score']<1
        return 'Actual scores and mismatches are retained; no normal/fall/scream prediction is forced'
    check('Negative controls retain genuine classifier output',negative_controls)
    def safeguards():
        expect(httpx.get(B+'/testing/scenarios'),401)
        expect(CLIENT.post(B+'/testing/runs',json={'scenario_id':'../../secret','model':'v3','authorized':True}),404)
        expect(CLIENT.post(B+'/testing/runs',json={'scenario_id':'conflict','model':'v3','authorized':False}),403)
        expect(CLIENT.post(B+'/testing/runs',json={'scenario_id':'acoustic_scream','model':'v3','authorized':True}),422)
        expect(CLIENT.post(B+'/testing/runs',json={'scenario_id':'conflict','model':'v3','authorized':True,'zone_id':'ZONE_TOILET_BLINDSPOT'}),422)
        expect(CLIENT.post(B+'/testing/runs',json={'scenario_id':'radar','model':'SVM_RBF','authorized':True}),422)
        expect(CLIENT.get(B+'/monitoring/sources/acoustic_scream'),404)
        from unittest.mock import patch
        with patch.dict(os.environ,{'SAFESENSE_YAMNET_PATH':str(OUT/'missing-yamnet')}):
            missing=scenario_catalog.selected('acoustic_scream');assert not missing['ready'] and 'cache missing' in missing['unavailable_reason']
        return 'Unauthorized inputs, path injection, modality mismatch, private-video override and raw acoustic streaming blocked; missing model reported without simulated fallback'
    check('Privacy, input validation and missing-model failures',safeguards)
    def unrelated():
        radar=RUNS['radar_raw_fall']['result']['event_delivery']['incident_id'];audio=RUNS['acoustic_scream']['result']['event_delivery']['incident_id']
        assert radar!=audio
        for identifier in (radar,audio):assert expect(CLIENT.get(B+'/incidents/'+identifier+'/report'))['level']=='OBSERVE'
        return 'Independent dataset recordings never become a corroborated HIGH incident'
    check('Unrelated radar/acoustic recordings cannot cross-fuse',unrelated)
    def persistence():
        before=expect(CLIENT.get(B+'/testing/runs'))
        backend.terminate();backend.wait(timeout=10)
        start('backend-restarted',[sys.executable,'-m','uvicorn','backend.main:app','--host','127.0.0.1','--port','18100'],B+'/health')
        after=expect(CLIENT.get(B+'/testing/runs'));assert {r['id'] for r in before}=={r['id'] for r in after}
        return {'persisted_runs':len(after)}
    check('Scenario history persists across backend restart',persistence)
    start('dashboard',[shutil.which('node'),str(ROOT/'dashboard/node_modules/vite/bin/vite.js'),'--host','127.0.0.1','--port','3001','--strictPort'],'http://127.0.0.1:3001',ROOT/'dashboard')
    from playwright.sync_api import sync_playwright,expect as browser_expect
    with sync_playwright() as pw:
        browser=pw.chromium.launch(headless=True);page=browser.new_page(viewport={'width':1550,'height':1100});page.set_default_timeout(20000)
        errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
        def browser_run():
            page.goto('http://127.0.0.1:3001/#/developer/testing',wait_until='domcontentloaded');browser_expect(page.get_by_text('FastAPI Connected',exact=True)).to_be_visible()
            panel=page.get_by_test_id('scenario-testing-library');browser_expect(panel).to_be_visible()
            panel.get_by_label('Scenario recording',exact=True).select_option('radar_raw_fall')
            panel.get_by_label('Authorize scenario research input',exact=True).check()
            panel.get_by_role('button',name='Run actual inference',exact=True).click()
            browser_expect(panel.get_by_text('SVM_RBF-LOSO-reconstructed',exact=True)).to_be_visible(timeout=180000)
            browser_expect(panel.get_by_text('Actual score 0.993291 · threshold 0.5',exact=False)).to_be_visible()
            assert panel.locator('video,audio,img').count()==0
            page.screenshot(path=str(OUT/'fresh-radar-library.png'),full_page=True)
            panel.get_by_role('button',name=__import__('re').compile('Open actual incident')).first.click()
            browser_expect(page.get_by_text('Private sensor metadata only. No images, video, or speech are captured.',exact=True)).to_be_visible()
            page.get_by_role('button',name='Close',exact=True).click()
            panel.get_by_label('Scenario recording',exact=True).select_option('conflict')
            browser_expect(panel.locator('video')).to_be_visible()
            assert not errors,errors
            return 'UI runs raw radar model, shows true score/provenance and opens its actual sensor-only incident; real public video preview remains available'
        check('Browser fresh scenario inference and incident integration',browser_run)
        browser.close()
    def preservation():
        after={p.relative_to(ROOT).as_posix():digest(p) for p in IMMUTABLE}
        assert BEFORE==after
        (OUT/'preserved-artifacts.json').write_text(json.dumps(after,indent=2),encoding='utf-8')
        return {'unchanged_source_and_model_artifacts':len(after)}
    check('Existing datasets, trained models and research results unchanged',preservation)
finally:
    for process,log in reversed(PROCESSES):
        if process.poll() is None:
            process.terminate()
            try:process.wait(timeout=10)
            except subprocess.TimeoutExpired:process.kill()
        log.close()
    CLIENT.close()
print(json.dumps({'passed':sum(r['status']=='PASS' for r in ROWS),'failed':sum(r['status']=='FAIL' for r in ROWS)}),flush=True)
sys.exit(any(r['status']=='FAIL' for r in ROWS))
