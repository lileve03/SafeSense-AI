"""Executed regression + actual-video HTTP integration checks; no training or research writes."""
from pathlib import Path
import ast
import csv
import json
import os
import subprocess
import sys
import time
import traceback
from unittest.mock import patch
import httpx
os.environ.setdefault('SAFESENSE_DB_PATH',str(Path(__file__).resolve().parents[1]/'runtime/test-results'/('legacy-'+str(time.time_ns())+'.sqlite3')))
os.environ['TELEGRAM_MODE']='disabled'
from fastapi.testclient import TestClient

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import backend.main as backend
import fight_api as ai
RESULTS=[]
OUT=ROOT/'runtime/test-results'
OUT.mkdir(parents=True,exist_ok=True)


def check(name, fn):
    started=time.perf_counter()
    try:
        actual=fn()
        RESULTS.append({'test':name,'status':'PASS','actual':actual,'seconds':round(time.perf_counter()-started,3)})
        print('PASS',name, str(actual)[:500],flush=True)
    except Exception as exc:
        RESULTS.append({'test':name,'status':'FAIL','actual':str(exc),'trace':traceback.format_exc(),'seconds':round(time.perf_counter()-started,3)})
        print('FAIL',name,str(exc),flush=True)
    (OUT/'results.json').write_text(json.dumps(RESULTS,indent=2),encoding='utf-8')


def expect(response, code):
    assert response.status_code==code, (response.status_code,response.text[:1000])
    return {'http':response.status_code,'body':response.json()}


bc=TestClient(backend.app,headers={'X-SafeSense-Token':ai.TOKEN})
ac=TestClient(ai.app)
HEAD={'X-SafeSense-Token':ai.TOKEN}
FORM={'zone_id':'ZONE_CORRIDOR_A','authorized':'true','model_version':'v3'}
def upload(data=None, name='clip.mp4', content=b'not a video', headers=HEAD):
    return ac.post('/ai/fight/analyze',data=data or FORM,files={'file':(name,content,'video/mp4')},headers=headers)

check('Python imports',lambda:{'backend':backend.app.title,'inference':ai.app.title})
check('Backend health',lambda:expect(bc.get('/health'),200))
check('Inference health and real model files',lambda:expect(ac.get('/ai/fight/health'),200))
check('Missing access authorization rejected',lambda:expect(upload(headers={}),401))
check('Unconfirmed recording authorization rejected',lambda:expect(upload({**FORM,'authorized':'false'}),403))
check('Private zone cannot be overridden by zone_type',lambda:expect(upload({**FORM,'zone_id':'ZONE_TOILET_BLINDSPOT','zone_type':'open_hidden'}),403))
check('Private fall upload rejected before pose processing',lambda:expect(ac.post('/ai/fall/analyze',data={'zone_id':'ZONE_TOILET_BLINDSPOT','authorized':'true'},files={'file':('private.mp4',b'invalid','video/mp4')},headers=HEAD),403))
check('Unknown model selection rejected',lambda:expect(upload({**FORM,'model_version':'v99'}),400))
check('Original inference import compatibility',lambda: {'same_app':__import__('backend.fight_api',fromlist=['app']).app is ai.app})
check('Unknown registered zone rejected',lambda:expect(upload({**FORM,'zone_id':'FAKE'}),422))
check('Invalid extension rejected',lambda:expect(upload(name='clip.exe'),400))
check('Invalid video bytes rejected',lambda:expect(upload(),422))
check('Empty video rejected',lambda:expect(upload(content=b''),422))
def oversized():
    # Full configured limit exercised; temporary sparse file avoids retaining a 101MB fixture.
    with __import__('tempfile').TemporaryFile() as f:
        f.truncate(ai.MAX_UPLOAD_BYTES+1); f.seek(0)
        r=ac.post('/ai/fight/analyze',data=FORM,files={'file':('large.mp4',f,'video/mp4')},headers=HEAD)
    return expect(r,413)
check('Actual 100 MB upload limit',oversized)
def missing_model():
    ai.get_classifier.cache_clear()
    with patch.dict(ai.MODEL_CONFIG,{'v3':{'path':ROOT/'runtime/absent.joblib','threshold':.7}}):
        result=expect(upload(),503)
    ai.get_classifier.cache_clear()
    return result
check('Missing classifier handling',missing_model)
def busy():
    ai.inference_lock.acquire()
    try:return expect(upload(),429)
    finally:ai.inference_lock.release()
check('Concurrent inference rejected',busy)
check('Private vision event rejected',lambda:expect(bc.post('/event',json={'zone':'ZONE_TOILET_BLINDSPOT','type':'fall','source':'vision'}),422))
check('Private simulated vision modality rejected',lambda:expect(bc.post('/event',json={'zone':'ZONE_TOILET_BLINDSPOT','type':'fall','source':'simulation','sensor_modality':'vision'}),422))
check('Untrusted real-model provenance rejected',lambda:expect(bc.post('/event',json={'zone':'ZONE_CORRIDOR_A','type':'possible_conflict','source':'vision','processing_mode':'real_model'},headers={'X-SafeSense-Token':''}),401))

def fusion():
    bc.post('/reset')
    zone='ZONE_TOILET_BLINDSPOT'
    a=bc.post('/event',json={'zone':zone,'type':'fall','source':'radar','processing_mode':'simulation'}).json()
    b=bc.post('/event',json={'zone':zone,'type':'scream','source':'yamnet','processing_mode':'simulation'}).json()
    assert a['event']['level']=='OBSERVE',a
    assert b['event']['level']=='HIGH',b
    assert a['incident']['id']==b['incident']['id']
    assert len(b['incident']['evidence'])==2
    return {'single':a['event']['level'],'fused':b['event']['level'],'incident_count':len(bc.get('/incidents').json())}
check('Independent permitted signals fuse and cooldown deduplicates',fusion)
def correlation():
    bc.post('/reset')
    for kind in ['fall','rapid_motion']:
        r=bc.post('/event',json={'zone':'ZONE_CORRIDOR_A','type':kind,'source':'vision','processing_mode':'real_model'},headers=HEAD).json()
    assert r['event']['level']=='OBSERVE',r
    return r['event']['reason']
check('Correlated camera predictions do not corroborate',correlation)
def modes():
    bc.post('/reset')
    bc.post('/event',json={'zone':'ZONE_CORRIDOR_A','type':'fall','source':'vision','processing_mode':'real_model'},headers=HEAD)
    r=bc.post('/event',json={'zone':'ZONE_CORRIDOR_A','type':'scream','source':'yamnet','processing_mode':'simulation'}).json()
    assert r['event']['level']=='OBSERVE',r
    return r['event']['reason']
check('Simulation cannot corroborate real-model observation',modes)
def dedup():
    bc.post('/reset')
    payload={'event_id':'stable-real-analysis','zone':'ZONE_CORRIDOR_A','type':'possible_conflict','source':'vision','processing_mode':'real_model','score':.42,'confidence':.42,'model_version':'v2'}
    a=bc.post('/event',json=payload,headers=HEAD).json()
    b=bc.post('/event',json=payload,headers=HEAD).json()
    assert a['event']['level']=='OBSERVE' and a['incident'],a
    assert b['deduplicated'] and len(bc.get('/incidents').json())==1,b
    return {'severity':a['incident']['level'],'score':.42,'duplicate_suppressed':True}
check('V2 above-threshold score below .5 still records review candidate; event-id dedup',dedup)
def workflow():
    r=bc.post('/event',json={'zone':'ZONE_TOILET_BLINDSPOT','type':'sos','source':'sos_button','processing_mode':'simulation'}).json()
    i=r['incident']; assert i['level']=='CRITICAL'
    ack=bc.post('/incidents/'+i['id']+'/ack',json={'staff':'Test operator'}).json()
    assert ack['status']=='ACKNOWLEDGED' and ack['acknowledged_at']
    done=bc.post('/incidents/'+i['id']+'/review',json={'status':'RESOLVED','note':'Test reviewed'}).json()
    assert done['status']=='RESOLVED' and len([h for h in done['history'] if not h['status'].startswith('NOTIFICATION_')])==3
    zone=next(z for z in bc.get('/zones').json() if z['id']=='ZONE_TOILET_BLINDSPOT')
    assert zone['level']=='LOW' and not zone['active_incident_ids'],zone
    return {'sos':i['level'],'ack':ack['status'],'final':done['status'],'history':done['history']}
check('SOS creation, acknowledgement, review and timestamps',workflow)
check('All existing dashboard zones registered',lambda: {'hall_public': next(z for z in bc.get('/zones').json() if z['id']=='ZONE_SCHOOL_HALL')['zone_type']})
check('Real saved research metrics',lambda:{'files':len(bc.get('/analytics/evaluations').json())})
def replay():
    options=bc.get('/sensors/replay').json()
    samples=[next(o for o in options if o['sensor']==sensor and o['candidate']) for sensor in ['radar','acoustic']]
    output=[]
    for o in samples:
        result=bc.post('/sensors/replay',json={'zone':'ZONE_TOILET_BLINDSPOT','sensor':o['sensor'],'index':o['index']})
        assert result.status_code==200,result.text
        event=result.json()['event']
        assert event['processing_mode']=='recorded_sensor_replay'
        assert event['level']=='OBSERVE',event
        output.append({k:event[k] for k in ['type','processing_mode','score','evidence_reference']})
    return output
check('Saved radar/acoustic replay; unrelated recordings do not corroborate',replay)
def indices():
    import numpy as np
    for n in [1,2,3,7,16,17,33,100,3600]:
        bounds=np.linspace(0,n,4).astype(int)
        reference=[]
        for i in range(3):
            start=min(bounds[i],n-1);end=max(start+1,bounds[i+1]);reference.append(np.linspace(start,end-1,16).astype(int))
        assert np.array_equal(reference,ai.sample_indices(n))
    return 'Exact training sample indices verified for short/long clips'
check('V2/V3 temporal sampling equivalence',indices)

processes=[]
def launch(module,port,python=sys.executable):
    log=(OUT/(module.replace('.','_')+'.log')).open('w',encoding='utf-8')
    env={**os.environ,'SAFESENSE_BACKEND_URL':'http://127.0.0.1:18000'}
    proc=subprocess.Popen([str(python),'-m','uvicorn',module+':app','--host','127.0.0.1','--port',str(port)],cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    processes.append((proc,log))
    for _ in range(180):
        if proc.poll() is not None:raise RuntimeError('Server exited: '+(OUT/(module.replace('.','_')+'.log')).read_text())
        try:
            response=httpx.get(f'http://127.0.0.1:{port}/health',timeout=1)
            if response.status_code==200:return {'port':port,'health':response.json()}
        except httpx.HTTPError:pass
        time.sleep(.25)
    raise RuntimeError('Server startup timeout')

try:
    check('Original backend environment FastAPI HTTP startup',lambda:launch('backend.main',18000,ROOT/'.venv/Scripts/python.exe'))
    check('Vision environment FastAPI HTTP startup',lambda:launch('fight_api',18001))
    manifest=ROOT/'evaluation/outputs/fight_v3/reserved_comparison/predictions.csv'
    with manifest.open(encoding='utf-8-sig',newline='') as f: row=next(csv.DictReader(f))
    # Remap saved research path under current root; no machine-specific paths in code.
    rel=row['path'].replace('\\','/').split('/datasets/',1)[1]
    video=ROOT/'datasets'/rel
    real_results={}
    def real_fight(version):
        with video.open('rb') as f:
            response=httpx.post('http://127.0.0.1:18001/ai/fight/analyze',data={**FORM,'model_version':version},files={'file':(video.name,f,'video/mp4')},headers=HEAD,timeout=180)
        data=expect(response,200)['body']; real_results[version]=data
        assert data['event_delivery']['status']=='recorded',data
        assert abs(data['score']-float(row[version+'_score']))<1e-5,(data['score'],row[version+'_score'])
        assert data['candidate_detected'] and data['event_delivery']['incident_id'],data
        return {'video':str(video.relative_to(ROOT)),'score':data['score'],'saved_reference_score':row[version+'_score'],'latency':data['inference_time_sec'],'feature_cache_hit':data['feature_cache_hit'],'incident':data['event_delivery']}
    check('V2 real MP4 HTTP inference and saved research score equivalence',lambda:real_fight('v2'))
    check('V3 real MP4 HTTP inference and saved research score equivalence',lambda:real_fight('v3'))
    def real_incident():
        state=httpx.get('http://127.0.0.1:18000/state',headers=HEAD).json()
        incident=next(i for i in state['incidents'] if i['id']==real_results['v3']['event_delivery']['incident_id'])
        assert incident['zone_id']=='ZONE_CORRIDOR_A' and incident['level']=='OBSERVE'
        evidence=incident['evidence']; assert len(evidence)==2,evidence
        result=httpx.post('http://127.0.0.1:18000/incidents/'+incident['id']+'/ack',json={'staff':'HTTP operator'},headers=HEAD).json()
        assert result['status']=='ACKNOWLEDGED'
        return {'zone':incident['zone_id'],'severity':incident['level'],'independent_confirmation':False,'ack':result['status']}
    check('Real model event to incident and map state; V2/V3 correlated evidence retained',real_incident)
    def real_fall():
        video=ROOT/'datasets/open_hidden/test_videos/fall-02-cam0-rgb.mp4'
        with video.open('rb') as f:
            response=httpx.post('http://127.0.0.1:18001/ai/fall/analyze',data={'zone_id':'ZONE_STAIRCASE','authorized':'true'},files={'file':(video.name,f,'video/mp4')},headers=HEAD,timeout=240)
        data=expect(response,200)['body']
        assert data['event_delivery']['status']=='recorded',data
        artifact=httpx.get('http://127.0.0.1:18001'+data['annotated_video_url'],params={'token':ai.TOKEN},timeout=10)
        assert artifact.status_code==200 and len(artifact.content)>1000
        import cv2
        import tempfile
        with tempfile.NamedTemporaryFile(suffix='.mp4',delete=False) as output:
            output.write(artifact.content); path=Path(output.name)
        cap=cv2.VideoCapture(str(path));ok,frame=cap.read();frames=cap.get(cv2.CAP_PROP_FRAME_COUNT);cap.release();path.unlink()
        assert ok
        return {**data,'annotation_bytes':len(artifact.content),'annotation_frames':frames}
    check('Real YOLO11-Pose fall video, event metadata and decodable annotated MP4',real_fall)
    check('Inference CORS for existing Vite origin',lambda:{'allow_origin':httpx.options('http://127.0.0.1:18001/ai/fight/analyze',headers={'Origin':'http://localhost:3000','Access-Control-Request-Method':'POST','Access-Control-Request-Headers':'x-safesense-token'}).headers['access-control-allow-origin']})
    check('Backend CORS for dashboard',lambda:{'allow_origin':httpx.options('http://127.0.0.1:18000/event',headers={'Origin':'http://localhost:3000','Access-Control-Request-Method':'POST','Access-Control-Request-Headers':'content-type'}).headers['access-control-allow-origin']})
finally:
    for proc,log in processes:
        proc.terminate()
        try:proc.wait(timeout=10)
        except subprocess.TimeoutExpired:proc.kill()
        log.close()
    (OUT/'results.json').write_text(json.dumps(RESULTS,indent=2),encoding='utf-8')
print(f"RESULT {sum(r['status']=='PASS' for r in RESULTS)}/{len(RESULTS)} passed",flush=True)
sys.exit(1 if any(r['status']=='FAIL' for r in RESULTS) else 0)
