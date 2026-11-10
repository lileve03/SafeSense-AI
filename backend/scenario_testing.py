"""Persistent bounded file-only scenario testing, separate from simulated controls."""
from concurrent.futures import ThreadPoolExecutor
from threading import BoundedSemaphore,Lock
from datetime import datetime,timezone
from uuid import uuid4
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.error import HTTPError
import json,os,subprocess,time,hashlib,math
from fastapi import HTTPException
from pydantic import BaseModel,ConfigDict
from backend import scenario_catalog,storage

ROOT=Path(__file__).resolve().parents[1]
OUTPUT=ROOT/'runtime/scenario-tests'
POOL=ThreadPoolExecutor(max_workers=1,thread_name_prefix='scenario-testing')
SLOTS=BoundedSemaphore(3)
LOCK=Lock()
ACTIVE={}

def now():return datetime.now(timezone.utc).isoformat()

class RunIn(BaseModel):
    model_config=ConfigDict(extra='forbid')
    scenario_id:str
    model:str
    authorized:bool=False

def ai(path,body=None):
    base=os.getenv('SAFESENSE_AI_URL','http://127.0.0.1:8001').rstrip('/')
    request=Request(base+path,data=json.dumps(body).encode() if body is not None else None,
                    headers={'Content-Type':'application/json','X-SafeSense-Token':os.getenv('SAFESENSE_API_TOKEN','local-demo-only')})
    try:
        with urlopen(request,timeout=12) as response:return json.load(response)
    except HTTPError as exc:
        raise RuntimeError(f'Inference service rejected the scenario (HTTP {exc.code})') from exc

def video(source,model):
    job=ai('/monitoring/jobs',{'scenario_id':source['id'],'zone_id':source['zone_id'],'model':model,'authorized':True})
    deadline=time.monotonic()+300
    while time.monotonic()<deadline:
        job=ai('/monitoring/jobs/'+job['id'])
        if job['status']=='COMPLETED':return {**job['result'],'output_origin':'fresh_model_execution','inference_job_id':job['id']}
        if job['status'] not in ('QUEUED','RUNNING'):raise RuntimeError(job.get('error','Inference job '+job['status']))
        time.sleep(.5)
    raise TimeoutError('Scenario exceeded the 300-second video job budget')

def sensor(source,model,identifier):
    OUTPUT.mkdir(parents=True,exist_ok=True)
    output=OUTPUT/(identifier+'.json');log=OUTPUT/(identifier+'.log')
    environment=ROOT/('.venv-radar' if source['kind']=='radar' else '.venv-acoustic')/'Scripts/python.exe'
    env=os.environ.copy();env.update(CUDA_VISIBLE_DEVICES='-1',TF_CPP_MIN_LOG_LEVEL='2',OMP_NUM_THREADS='2',TF_NUM_INTRAOP_THREADS='2',TF_NUM_INTEROP_THREADS='2')
    with log.open('w',encoding='utf-8') as stream:
        try:
            process=subprocess.run([str(environment),str(ROOT/'scripts/scenario_sensor_worker.py'),'--scenario',source['id'],'--model',model,'--output',str(output)],
                cwd=ROOT,env=env,stdout=stream,stderr=subprocess.STDOUT,timeout=180,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        except subprocess.TimeoutExpired as exc:raise TimeoutError('Sensor worker exceeded 180-second budget; no simulated fallback') from exc
    if process.returncode or not output.is_file():raise RuntimeError('Fresh sensor inference failed; inspect runtime/scenario-tests/'+identifier+'.log')
    if output.stat().st_size>2*1024*1024:raise RuntimeError('Sensor result exceeds metadata budget')
    result=json.loads(output.read_text(encoding='utf-8'))
    from backend.main import create_event,EventIn,TOKEN
    score=result.get('score')
    if isinstance(score,bool) or not isinstance(score,(int,float)) or not math.isfinite(score) or not 0 <= score <= 1:
        raise RuntimeError('Sensor model returned an invalid score; no event generated')
    actual_sha=hashlib.sha256((ROOT/source['path']).read_bytes()).hexdigest()
    if result.get('input_sha256') != actual_sha:
        raise RuntimeError('Sensor input checksum mismatch; no event generated')
    fingerprint={k:result.get(k) for k in ('input_sha256','model_version','model_sha256','training_feature_sha256','training_subject_excluded','threshold')}
    fingerprint.update(zone=source['zone_id'],model=model)
    event_identifier='recorded-model-'+hashlib.sha256(json.dumps(fingerprint,sort_keys=True).encode()).hexdigest()
    kind=('fall' if result['candidate_detected'] else 'normal_motion') if source['kind']=='radar' else ('scream' if result['candidate_detected'] else 'normal_acoustic')
    delivery=create_event(EventIn(zone=source['zone_id'],type=kind,source='radar' if source['kind']=='radar' else 'yamnet',
        processing_mode='real_model',is_test=True,source_type='RECORDED SENSOR REPLAY',confidence=result['score'],score=result['score'],
        event_id=event_identifier,analysis_run_id=identifier,model_version=result['model_version'],
        evidence_reference=f"scenario_run:{identifier}; raw:{source['path']}; sha256:{result['input_sha256']}"),TOKEN)
    from backend.sensor_observations import RecordedAdapter, save
    save(RecordedAdapter().from_event(delivery['event']))
    result['event_delivery']={'status':'recorded','deduplicated':delivery.get('deduplicated',False),'event_id':delivery['event']['id'],'incident_id':delivery['incident']['id'] if delivery.get('incident') else None}
    return result

def install(app):
    @app.get('/testing/scenarios')
    def catalog():return scenario_catalog.catalog()

    @app.post('/testing/runs',status_code=202)
    def submit(body:RunIn):
        source=scenario_catalog.selected(body.scenario_id)
        if not source:raise HTTPException(404,'Unknown registered scenario')
        if source['execution_kind']!='fresh_inference':raise HTTPException(422,'Saved predictions and simulation use their explicitly labeled legacy controls, not fresh inference')
        if not body.authorized:raise HTTPException(403,'Confirm authorized offline research input')
        if body.model not in source['allowed_models']:raise HTTPException(422,'Model does not support this registered modality')
        if not source['ready']:raise HTTPException(503,source['unavailable_reason'])
        key=(body.scenario_id,body.model)
        with LOCK:
            if key in ACTIVE:return ACTIVE[key]
            if not SLOTS.acquire(blocking=False):raise HTTPException(429,'Scenario queue full: one running, two waiting')
            row={'id':str(uuid4()),'scenario_id':source['id'],'scenario_name':source['name'],'zone_id':source['zone_id'],
                 'input_type':source['input_type'],'source_type':source['source_type'],'model':body.model,'status':'QUEUED',
                 'ground_truth':source['ground_truth'],'submitted_at':now(),'is_test':True}
            storage.put('scenario_run',row['id'],row);ACTIVE[key]=row
        def work():
            started=time.perf_counter()
            try:
                row.update(status='RUNNING',started_at=now());storage.put('scenario_run',row['id'],row)
                result=video(source,body.model) if source['input_type']=='video' else sensor(source,body.model,row['id'])
                comparisons=[]
                for output in result.get('model_results',[result]):
                    version=output['model_version']
                    relevant=source['input_type']!='video' or source['dataset']=='AIRTLab' and version in ('v2','v3') or source['dataset']=='UR Fall' and version.startswith('yolo')
                    expected=source['ground_truth'] in ('violent','fall','screaming') if relevant else None
                    comparisons.append({'model_version':version,'expected_candidate':expected,'observed_candidate':output['candidate_detected'],
                                        'matches':bool(output['candidate_detected'])==expected if relevant else None})
                graded=[c['matches'] for c in comparisons if c['matches'] is not None]
                row.update(status='COMPLETED',result=result,ground_truth_comparisons=comparisons,matches_ground_truth=all(graded) if graded else None)
            except Exception as exc:
                row.update(status='FAILED',error=str(exc) if isinstance(exc,(RuntimeError,TimeoutError)) else type(exc).__name__)
            finally:
                row.update(finished_at=now(),wall_time_sec=round(time.perf_counter()-started,3))
                try:storage.put('scenario_run',row['id'],row)
                finally:
                    with LOCK:ACTIVE.pop(key,None)
                    SLOTS.release()
        try:POOL.submit(work)
        except RuntimeError:
            with LOCK:ACTIVE.pop(key,None)
            SLOTS.release();row.update(status='FAILED',error='Scenario worker unavailable');storage.put('scenario_run',row['id'],row)
        return row

    def current(row):
        with LOCK:active=any(r['id']==row['id'] for r in ACTIVE.values())
        if row['status'] in ('QUEUED','RUNNING') and not active:
            row.update(status='INTERRUPTED',error='Backend restarted; rerun explicitly. No fabricated result.')
        return row

    @app.get('/testing/runs')
    def history():return [{k:v for k,v in current(r).items() if k!='result'} for r in storage.all_rows('scenario_run')[-20:][::-1]]

    @app.get('/testing/runs/{identifier}')
    def detail(identifier:str):
        row=next((r for r in storage.all_rows('scenario_run') if r['id']==identifier),None)
        if not row:raise HTTPException(404,'Scenario run not found')
        return current(row)
