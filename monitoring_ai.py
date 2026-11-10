"""Bounded offline job execution and retained real incident video evidence."""
from threading import BoundedSemaphore
from typing import Literal
from pathlib import Path
from uuid import uuid4
from datetime import datetime, timezone
import json
import os
import shutil
import subprocess
import time
from contextvars import ContextVar
from urllib.parse import urlparse

from fastapi import Header, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from starlette.datastructures import UploadFile
from backend import storage, registry
from backend.inference_queue import InferenceQueue, QueueBusy, Superseded
from backend.analysis_cache import AnalysisCache,content_hash,identity_hash,AnalysisGZipMiddleware
from backend.cpu_profile import memory_sample

ROOT=Path(__file__).resolve().parent
EVIDENCE=Path(os.getenv('SAFESENSE_EVIDENCE_DIR',str(ROOT/'runtime/evidence')))
RETENTION=max(1,int(os.getenv('SAFESENSE_EVIDENCE_RETENTION_DAYS','7')))
CONTEXT=ContextVar('analysis_context',default={})
LIVE_SLOTS=BoundedSemaphore(2)

ANALYSIS_CACHE=AnalysisCache(os.getenv('SAFESENSE_ANALYSIS_CACHE_DIR',str(ROOT/'runtime/analysis-cache')),ttl_days=max(1,min(30,int(os.getenv('SAFESENSE_ANALYSIS_CACHE_DAYS','7')))))

def cache_valid(row):
    result=row.get('result',{})
    outputs=result.get('model_results') or [result]
    if row.get('status')!='COMPLETED' or result.get('model_errors'):return False
    identity=row.get('cache_identity')
    if identity:
        if result.get('camera_id')!=identity.get('camera_id'):return False
        if result.get('zone_id')!=identity.get('zone_id'):return False
        if identity.get('source_sha256')!='live' and any(o.get('input_sha256')!=identity.get('source_sha256') for o in outputs):return False

    for output in outputs:
        delivery=output.get('event_delivery',{})
        if delivery.get('status')=='failed' or output.get('evidence_error'):return False
        # A reset/deleted backend must not receive another database's incident IDs.
        if delivery.get('event_id') and storage.get('event',delivery['event_id']) is None:return False
        if delivery.get('incident_id') and storage.get('incident',delivery['incident_id']) is None:return False
    # Optional annotated videos/evidence expire independently; their absence must
    # not discard genuine pose coordinates or rerun neural models.
    return True

QUEUE=InferenceQueue(lambda row:storage.put('job',row['id'],row),cache_valid,
                    lookup=lambda identifier:storage.get('job',identifier),completed_lookup=lambda key:ANALYSIS_CACHE.load(key))


def file_signature(path):
    path=Path(path)
    try:
        stat=path.stat()
        return str(path.resolve()),stat.st_size,stat.st_mtime_ns
    except OSError:return str(path),'missing'

def execution_models(body):
    if body.model=='all' and body.camera_id:
        camera=next((c for c in registry.cameras() if c['camera_id']==body.camera_id),{})
        baseline=camera.get('fight_model') or os.getenv('SAFESENSE_FIGHT_BASELINE','v3')
        if baseline not in ('v2','v3'):
            raise HTTPException(422,'Configured fight baseline must be v2 or v3')
        return (baseline,'pose')
    return ('v2','v3','pose') if body.model=='all' else (body.model,)

def cache_identity(body,path,versions=None):
    from fight_api import MODEL_CONFIG,CPU_THREADS,POSE_THREADS,POSE_IMAGE_SIZE
    import torch
    from torchvision.models.video import R3D_18_Weights
    from importlib.metadata import version
    versions=versions or execution_models(body)
    checkpoint=Path(torch.hub.get_dir())/'checkpoints'/Path(R3D_18_Weights.DEFAULT.url).name
    return {'schema':'recorded-camera-v3','camera_id':body.camera_id,'scenario_id':body.scenario_id,'zone_id':body.zone_id,
            'mode':body.model,'models':list(versions),'source_sha256':content_hash(path) if path else 'live',
            'pose_weights_sha256':content_hash(ROOT/'yolo11n-pose.pt') if 'pose' in versions else None,
            'r3d_weights_sha256':content_hash(checkpoint) if any(v!='pose' for v in versions) else None,
            'classifiers':{v:{'sha256':content_hash(MODEL_CONFIG[v]['path']),'threshold':MODEL_CONFIG[v]['threshold']} for v in versions if v!='pose'},
            'code':{name:content_hash(ROOT/name) for name in ['fight_api.py','monitoring_ai.py','scripts/safesense_temporal_fall.py','backend/pose_tracking.py','backend/fight_participants.py']},
            'versions':{name:version(name) for name in ['torch','torchvision','ultralytics','scikit-learn','scipy']},
            'config':{'pose_imgsz':POSE_IMAGE_SIZE,'pose_conf':.25,'pose_stride':1,'cpu_threads':CPU_THREADS,'pose_threads':POSE_THREADS,'fight_sampling':'3x16-training-compatible-v1',
                      'evidence_pre':os.getenv('SAFESENSE_EVIDENCE_PRE_SECONDS','5'),'evidence_post':os.getenv('SAFESENSE_EVIDENCE_POST_SECONDS','5')},
            'namespace':identity_hash({'database':str(storage.DB.resolve()),'evidence':str(EVIDENCE.resolve()),'annotations':str(Path(os.getenv('SAFESENSE_ANNOTATION_DIR',str(ROOT/'runtime/annotations'))).resolve())})}

def job_key(body,path,versions=None):
    return identity_hash(cache_identity(body,path,versions))

_LOADED_SIGNATURES={}
def prepare_models(identity):
    import fight_api as ai
    import torch
    values={'pose':identity['pose_weights_sha256'],'extractor':identity['r3d_weights_sha256'],**{v:c['sha256'] for v,c in identity['classifiers'].items()}}
    for kind,digest in values.items():
        if digest is None:continue
        previous=_LOADED_SIGNATURES.get(kind)
        if previous is not None and previous!=digest:
            if kind=='pose':ai.get_pose.cache_clear()
            elif kind=='extractor':ai.get_extractor.cache_clear();ai.feature_cache.clear()
            else:ai.get_classifier.cache_clear()
        _LOADED_SIGNATURES[kind]=digest
    torch.set_num_threads(ai.CPU_THREADS)



def live_camera(camera_id):
    row=next((c for c in registry.cameras() if c['camera_id']==camera_id and c['source_type']=='LIVE CAMERA'),None)
    if not row or urlparse(row.get('stream_url','')).scheme not in ('rtsp','http','https'):
        raise HTTPException(404,'Authorized RTSP/HTTP camera not configured')
    return row

def open_live(camera):
    import cv2
    cap=cv2.VideoCapture(camera['stream_url'],cv2.CAP_FFMPEG,[cv2.CAP_PROP_OPEN_TIMEOUT_MSEC,5000,cv2.CAP_PROP_READ_TIMEOUT_MSEC,5000])
    if not cap.isOpened():
        cap.release()
        raise HTTPException(503,'Configured camera unavailable; check hardware and access')
    return cap

def record_live(camera):
    """Bounded 10-second sample, no continuous surveillance or unbounded frame queue."""
    import cv2
    from tempfile import NamedTemporaryFile
    cap=open_live(camera)
    writer=None
    with NamedTemporaryFile(suffix='.mp4',delete=False) as f:path=Path(f.name)
    try:
        fps=cap.get(cv2.CAP_PROP_FPS)
        fps=fps if 1<=fps<=60 else 15
        started=time.monotonic();count=0
        while count<min(600,int(fps*10)) and time.monotonic()-started<15:
            ok,frame=cap.read()
            if not ok: break
            h,w=frame.shape[:2]
            if w*h>1920*1080:raise HTTPException(422,'Live frame exceeds pixel budget')
            if writer is None:
                writer=cv2.VideoWriter(str(path),cv2.VideoWriter_fourcc(*'mp4v'),fps,(w,h))
                if not writer.isOpened():raise HTTPException(503,'Live sample encoder unavailable')
            writer.write(frame);count+=1
        if not count:raise HTTPException(503,'Camera delivered no frames')
        return path
    except Exception:
        path.unlink(missing_ok=True)
        raise
    finally:
        cap.release()
        if writer:writer.release()

def purge():
    EVIDENCE.mkdir(parents=True,exist_ok=True)
    cutoff=time.time()-RETENTION*86400
    for path in EVIDENCE.iterdir():
        if path.is_file() and path.stat().st_mtime<cutoff:
            path.unlink(missing_ok=True)

def capture(result,path,annotated_path=None):
    """Fight preserves analyzed clip; fall uses actual first candidate +/- configured seconds."""
    if not result.get('candidate_detected'):
        return []
    purge()
    ffmpeg=shutil.which('ffmpeg')
    if not ffmpeg:
        result['evidence_error']='FFmpeg unavailable; cannot create browser-compatible evidence'
        return []
    identifier=str(uuid4())
    duration=result['video_duration_sec']
    event=(result.get('events') or [{}])[0].get('time_sec')
    before=max(0,min(30,float(os.getenv('SAFESENSE_EVIDENCE_PRE_SECONDS','5'))))
    after=max(0,min(30,float(os.getenv('SAFESENSE_EVIDENCE_POST_SECONDS','5'))))
    start=max(0,event-before) if event is not None else 0
    end=min(duration,event+after) if event is not None else duration
    output=EVIDENCE/(identifier+'.mp4')
    try:
        subprocess.run([ffmpeg,'-nostdin','-v','error','-y','-ss',str(start),'-i',str(path),'-t',str(max(.05,end-start)),
                        '-an','-vf','pad=ceil(iw/2)*2:ceil(ih/2)*2','-c:v','libx264','-preset','ultrafast','-pix_fmt','yuv420p',
                        '-movflags','+faststart',str(output)],check=True,timeout=50,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,
                        creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        row={'id':identifier,'zone_id':result['zone_id'],'analysis_id':result['analysis_id'],
             'model_version':result['model_version'],'score':result.get('score'),'candidate_detected':result.get('candidate_detected'),
             'prediction':result.get('prediction') or ((result.get('events') or [{}])[0].get('type')),
             'threshold':result.get('threshold'),'input_sha256':result.get('input_sha256'),'source_type':CONTEXT.get().get('source_type','RECORDED REAL VIDEO'),
             'camera_id':CONTEXT.get().get('camera_id'),
             'time_scope':'candidate_rule_timestamp' if event is not None else 'whole_analyzed_clip_no_validated_event_timing',
             'start_sec':start,'end_sec':end,'duration_sec':round(end-start,3),'event_time_sec':event,
             'created_at':datetime.now(timezone.utc).isoformat(),'review_status':'pending_human_review',
             'url':'/monitoring/evidence/'+identifier,'retention_days':RETENTION}
        if result.get('pose_frames'):
            overlay={'analysis_id':result['analysis_id'],'input_sha256':result.get('input_sha256'),
                'camera_id':row['camera_id'],'annotation_alignment':result.get('annotation_alignment'),
                'pose_frames':[f for f in result['pose_frames'] if start-1/result['annotation_alignment']['fps']<=f['time_sec']<end],
                'events':result.get('events',[]),'tracking_available':result.get('tracking_available',False)}
            (EVIDENCE/(identifier+'.overlays.json')).write_text(json.dumps(overlay),encoding='utf-8')
            row['overlay_analysis_id']=result['analysis_id']
        if annotated_path is not None:
            from backend.incident_media import annotate
            if annotate(annotated_path,EVIDENCE/(identifier+'.annotated.mp4'),start,end):
                row['annotation_analysis_id']=result['analysis_id']
                row['annotation_alignment']=result.get('annotation_alignment')
            else:row['annotation_error']='Annotated evidence unavailable; original clip retained'
        (EVIDENCE/(identifier+'.json')).write_text(json.dumps(row),encoding='utf-8')
        return [row]
    except (OSError,subprocess.SubprocessError):
        output.unlink(missing_ok=True)
        (EVIDENCE/(identifier+'.annotated.mp4')).unlink(missing_ok=True)
        result['evidence_error']='Evidence encoding failed; candidate result retained'
        return []

def retain_interaction_overlays(result, outputs):
    """Attach actual combined analysis to its own already captured incident clips.
    No new incident/event/notification and no change to classifier evidence identity.
    """
    for output in outputs:
        for item in output.get('evidence_media',[]):
            path=EVIDENCE/(item['id']+'.json')
            try:
                metadata=json.loads(path.read_text(encoding='utf-8'))
                if any(metadata.get(k)!=output.get(k) for k in ('analysis_id','input_sha256','zone_id')):continue
                start,end=metadata['start_sec'],metadata['end_sec']
                overlay={'analysis_id':metadata['analysis_id'],'input_sha256':metadata['input_sha256'],
                    'camera_id':metadata.get('camera_id'),'annotation_alignment':result['annotation_alignment'],
                    'pose_frames':[f for f in result['pose_frames'] if start-1/result['annotation_alignment']['fps']<=f['time_sec']<end],
                    'participant_events':[e for e in result['participant_events'] if start<=e['time_sec']<end],
                    'participant_heuristic':result['participant_heuristic'],'tracking_available':True,
                    'model_results':[{k:r.get(k) for k in ('model_version','score','violence_score','threshold','candidate_detected','prediction','video_duration_sec')} for r in outputs if r['model_version'] in ('v2','v3')]}
                target=EVIDENCE/(item['id']+'.overlays.json');temporary=target.with_suffix('.tmp')
                temporary.write_text(json.dumps(overlay),encoding='utf-8');temporary.replace(target)
                metadata['overlay_analysis_id']=metadata['analysis_id']
                temporary=path.with_suffix('.tmp');temporary.write_text(json.dumps(metadata),encoding='utf-8');temporary.replace(path)
            except (OSError,ValueError,KeyError):result['participant_evidence_note']='Interaction metadata unavailable for one retained clip; original evidence preserved'


class JobIn(BaseModel):
    scenario_id: str|None=None
    zone_id: str
    model: Literal['all','v2','v3','pose']='all'
    authorized: bool=False
    camera_id: str|None=None
    client_id: str|None=Field(default=None,min_length=1,max_length=100)
    selection_seq: int=Field(default=0,ge=0)
    force: bool=False

class ReleaseIn(BaseModel):
    client_id: str=Field(min_length=1,max_length=100)
    selection_seq: int=Field(ge=0)

def install(app):
    from fight_api import authorize, validate_zone, TOKEN, analyze_fight, analyze_fall
    import asyncio
    from contextlib import asynccontextmanager
    app.add_middleware(AnalysisGZipMiddleware)
    previous_lifespan=app.router.lifespan_context
    @asynccontextmanager
    async def lifespan(application):
        async with previous_lifespan(application):
            await asyncio.to_thread(purge)
            async def cleanup():
                while True:
                    await asyncio.sleep(3600)
                    await asyncio.to_thread(purge)
            task=asyncio.create_task(cleanup())
            try:yield
            finally:
                task.cancel()
                try:await task
                except asyncio.CancelledError:pass
    app.router.lifespan_context=lifespan

    @app.post('/monitoring/jobs',status_code=202)
    def submit(body:JobIn,x_safesense_token:str|None=Header(None)):
        lookup_started=time.perf_counter()
        authorize(x_safesense_token)
        validate_zone(body.zone_id,body.authorized)
        if body.camera_id:
            canonical=registry.canonical_camera_id(body.camera_id)
            if canonical is None:raise HTTPException(422,'Unknown or ambiguous registered camera identity')
            body=body.model_copy(update={'camera_id':canonical})
        live=live_camera(body.camera_id) if body.camera_id and body.scenario_id is None else None
        if live:
            if live['zone_id']!=body.zone_id:raise HTTPException(422,'Camera/zone mismatch')
            path=None
        else:
            scenario,path=registry.source(body.scenario_id)
        if body.camera_id and not live:
            camera=next((c for c in registry.cameras() if c['camera_id']==body.camera_id),None)
            if not camera or camera['zone_id']!=body.zone_id or camera.get('scenario_id')!=body.scenario_id:
                raise HTTPException(422,'Camera/zone/source mismatch')
        automatic=body.model=='all' and body.camera_id is not None
        models=execution_models(body)
        identity=cache_identity(body,path,models)
        key=identity_hash(identity)
        row={'id':str(uuid4()),'status':'QUEUED','scenario_id':body.scenario_id,'camera_id':body.camera_id,
             'zone_id':body.zone_id,'model':body.model,'source_type':'LIVE CAMERA' if live else 'RECORDED REAL VIDEO',
             'processing_mode':'OFFLINE ANALYSIS','cache_key':key,'cache_identity':identity,'resolved_models':list(models),'submitted_at':datetime.now(timezone.utc).isoformat()}
        def work():
            current_path=path
            context_token=CONTEXT.set({'camera_id':body.camera_id,'source_type':row['source_type'],
                                       'analysis_run_id':row['id'] if automatic else None})
            started=time.perf_counter()
            try:
                row.update(status='RUNNING',started_at=datetime.now(timezone.utc).isoformat())
                storage.put('job',row['id'],row)
                prepare_models(identity)
                if live:current_path=record_live(live)
                results=[]
                errors=[]
                for selected_model in models:
                    try:
                        with current_path.open('rb') as stream:
                            upload=UploadFile(filename=current_path.name,file=stream)
                            output=analyze_fall(file=upload,zone_id=body.zone_id,authorized=True,x_safesense_token=TOKEN) if selected_model=='pose' else analyze_fight(file=upload,model_version=selected_model,zone_id=body.zone_id,authorized=True,zone_type='open_hidden',x_safesense_token=TOKEN)
                        results.append(output)
                    except Exception as exc:
                        if body.model!='all':raise
                        errors.append({'model':selected_model,'error':str(exc.detail) if isinstance(exc,HTTPException) else type(exc).__name__})
                if not results:raise HTTPException(503,'All requested models failed; check model files and inference service')
                if body.model=='all':
                    # Preserve independent model outputs: person pose is not fight localization.
                    fight=next((r for r in results if r['model_version']=='v3'),next((r for r in results if r['model_version']=='v2'),{}))
                    pose=next((r for r in results if r['model_version']=='yolo11n-pose-temporal-rule-v1'),{})
                    preferred=next((r for r in results if r.get('candidate_detected') and r.get('event_delivery',{}).get('incident_id')),results[0])
                    result={**fight,'status':'partial_success' if errors else 'success','model_version':('V2 + V3 + YOLO11-Pose' if len(models)==3 else models[0].upper()+' + YOLO11-Pose'),'model_results':results,'model_errors':errors,
                            'candidate_detected':any(r['candidate_detected'] for r in results),
                            'review_status':'pending_human_review' if any(r['candidate_detected'] for r in results) else 'not_flagged',
                            'feature_extraction_status':'Independent model runs; V2/V3 may reuse actual extracted features. See per-model measurements.',
                            'video_duration_sec':results[0]['video_duration_sec'],
                            'inference_time_sec':round(sum(r['inference_time_sec'] for r in results),3),
                            'video_fps':results[0].get('video_fps'),'inference_fps':None,
                            'frame_skipping':'See independent per-model measurements','dropped_frames':None,
                            'events':pose.get('events',[]),'annotated_video_url':pose.get('annotated_video_url'),
                            'pose_frames':pose.get('pose_frames',[]),'tracking_available':pose.get('tracking_available',False),
                            'person_confidence_threshold':pose.get('person_confidence_threshold'),
                            'annotation_alignment':pose.get('annotation_alignment'),
                            'encoding_note':pose.get('encoding_note'),
                            'event_delivery':preferred['event_delivery'],
                            'evidence_media':[m for r in results for m in r.get('evidence_media',[])],
                            'note':'Real V2/V3 whole-clip classifications plus independent YOLO person boxes/skeletons. Person boxes do not identify fighters. Fall timestamps come from the experimental pose rule; fight timing is not localized.'}
                else:result=results[0]
                if automatic:
                    result['analysis_policy']={'mode':'automatic','fight_model':models[0],'fall_model':'yolo11n-pose-temporal-rule-v1'}
                    result['analysis_run_id']=row['id']
                    result['note']='Configured fight baseline classifies the whole clip; independent YOLO person boxes and skeletons do not localize fighters. Only the experimental pose rule supplies fall candidate timestamps.'
                if body.model=='all' and pose and fight:
                    from backend.fight_participants import annotate_participants
                    interaction_started=time.perf_counter()
                    result.update(annotate_participants(pose,fight))
                    retain_interaction_overlays(result,results)
                    result['participant_processing_sec']=round(time.perf_counter()-interaction_started,6)
                    result['note']='V2/V3 classify the whole clip. Person-level red fight candidates use a separate experimental pose-interaction heuristic, not classifier localization. Scores are uncalibrated and require human review.'
                result['camera_id']=body.camera_id
                result['source_type']=row['source_type']
                result['total_processing_sec']=round(time.perf_counter()-started,3)
                result['process_memory']=memory_sample()
                result['queue_delay_sec']=round((datetime.fromisoformat(row['started_at'])-datetime.fromisoformat(row['submitted_at'])).total_seconds(),3)
                row.update(status='COMPLETED',result=result)
            except Exception as exc:
                row.update(status='FAILED',error=str(exc.detail) if isinstance(exc,HTTPException) else type(exc).__name__)
            finally:
                CONTEXT.reset(context_token)
                if live and current_path:current_path.unlink(missing_ok=True)
                row['finished_at']=datetime.now(timezone.utc).isoformat()
                if not live and row.get('status')=='COMPLETED' and cache_valid(row):
                    try:ANALYSIS_CACHE.save(key,row)
                    except OSError:row['cache_write_error']='Persistent cache unavailable; current analysis remains valid'
                storage.put('job',row['id'],row)
        try:
            response=QUEUE.submit(key,row,work,body.client_id,body.selection_seq,reuse=not live,force=body.force)
            response['request_lookup_sec']=round(time.perf_counter()-lookup_started,6)
            return response
        except QueueBusy:
            raise HTTPException(429,{'code':'CPU_BUSY','message':'AI analysis queued; waiting for CPU capacity',
                                     'retry_after_seconds':2},headers={'Retry-After':'2'})
        except Superseded:
            raise HTTPException(409,{'code':'SUPERSEDED','message':'A newer camera selection replaced this request'})

    @app.post('/monitoring/jobs/release')
    def release(body:ReleaseIn,x_safesense_token:str|None=Header(None)):
        authorize(x_safesense_token)
        try:QUEUE.release(body.client_id,body.selection_seq)
        except Superseded:pass
        return {'status':'RELEASED'}

    @app.get('/monitoring/live/{camera_id}')
    def live_preview(camera_id:str,token:str='',x_safesense_token:str|None=Header(None)):
        from fastapi.responses import StreamingResponse
        import cv2
        authorize(x_safesense_token or token)
        camera=live_camera(camera_id)
        if not LIVE_SLOTS.acquire(blocking=False):raise HTTPException(429,'Live preview limit reached')
        try:cap=open_live(camera)
        except Exception:
            LIVE_SLOTS.release()
            raise
        def frames():
            try:
                deadline=time.monotonic()+120
                while time.monotonic()<deadline:
                    ok,frame=cap.read()
                    if not ok:break
                    h,w=frame.shape[:2]
                    if w*h>1920*1080:break
                    frame=cv2.resize(frame,(640,max(1,int(h*640/w))))
                    ok,encoded=cv2.imencode('.jpg',frame,[cv2.IMWRITE_JPEG_QUALITY,70])
                    if ok:yield b'--frame\r\nContent-Type: image/jpeg\r\n\r\n'+encoded.tobytes()+b'\r\n'
                    time.sleep(.1)
            finally:
                cap.release();LIVE_SLOTS.release()
        return StreamingResponse(frames(),media_type='multipart/x-mixed-replace; boundary=frame',headers={'Cache-Control':'no-store'})

    @app.get('/monitoring/jobs/{job_id}')
    def job(job_id:str,x_safesense_token:str|None=Header(None)):
        authorize(x_safesense_token)
        row=storage.get('job',job_id)
        if row is None: raise HTTPException(404,'Job not found')
        if row['status'] in ('QUEUED','RUNNING') and not QUEUE.contains(job_id):
            row.update(status='INTERRUPTED',error='Inference service restarted; rerun explicitly')
        return row

    @app.get('/monitoring/incidents/{incident_id}/evidence/{evidence_id}/metadata')
    def incident_metadata(incident_id:str,evidence_id:str,token:str='',x_safesense_token:str|None=Header(None)):
        authorize(x_safesense_token or token)
        purge()
        from backend.incident_media import resolve
        metadata,_,_=resolve(incident_id,evidence_id)
        return metadata

    @app.get('/monitoring/incidents/{incident_id}/evidence/{evidence_id}/thumbnail')
    def incident_thumbnail(incident_id:str,evidence_id:str,token:str='',x_safesense_token:str|None=Header(None)):
        authorize(x_safesense_token or token)
        purge()
        from backend.incident_media import thumbnail
        from fastapi.responses import Response
        image, source_time = thumbnail(incident_id, evidence_id)
        return Response(image,media_type='image/jpeg',headers={
            'Cache-Control':'private, no-store','Referrer-Policy':'no-referrer',
            'X-Evidence-Frame-Sec':str(source_time),'Access-Control-Expose-Headers':'X-Evidence-Frame-Sec'})

    @app.get('/monitoring/incidents/{incident_id}/evidence/{evidence_id}')
    def incident_media(incident_id:str,evidence_id:str,variant:str='original',download:bool=False,token:str='',x_safesense_token:str|None=Header(None)):
        authorize(x_safesense_token or token)
        if variant not in ('original','annotated'):raise HTTPException(422,'Unknown evidence variant')
        purge()
        from backend.incident_media import resolve
        metadata,original,annotated=resolve(incident_id,evidence_id,recover=False)
        if variant=='annotated' and not metadata['annotated_available']:raise HTTPException(410,'Matching annotated evidence unavailable')
        path=annotated if variant=='annotated' else original
        if not path.is_file():raise HTTPException(410,'Evidence expired or unavailable')
        return FileResponse(path,media_type='video/mp4',filename=f'incident-{incident_id}-{evidence_id}-{variant}.mp4' if download else None,
            content_disposition_type='attachment' if download else 'inline',headers={'Cache-Control':'private, no-store','Referrer-Policy':'no-referrer'})

    @app.get('/monitoring/evidence/{evidence_id}')
    def evidence(evidence_id:str,token:str='',x_safesense_token:str|None=Header(None)):
        authorize(x_safesense_token or token)
        purge()
        try:
            if str(__import__('uuid').UUID(evidence_id))!=evidence_id: raise ValueError()
        except ValueError: raise HTTPException(404,'Evidence not found')
        path=EVIDENCE/(evidence_id+'.mp4')
        if not path.is_file(): raise HTTPException(410,'Evidence expired or unavailable')
        return FileResponse(path,media_type='video/mp4',headers={'Cache-Control':'private, no-store','Referrer-Policy':'no-referrer'})

    @app.post('/monitoring/evidence/{evidence_id}/delete')
    def delete_evidence(evidence_id:str,x_safesense_token:str|None=Header(None)):
        authorize(x_safesense_token)
        try:
            if str(__import__('uuid').UUID(evidence_id))!=evidence_id:raise ValueError()
        except ValueError:raise HTTPException(404,'Evidence not found')
        for suffix in ('.mp4','.annotated.mp4','.json','.overlays.json'):(EVIDENCE/(evidence_id+suffix)).unlink(missing_ok=True)
        storage.put('audit',str(uuid4()),{'action':'evidence_deleted','evidence_id':evidence_id,'timestamp':datetime.now(timezone.utc).isoformat()})
        return {'status':'deleted','evidence_id':evidence_id}
