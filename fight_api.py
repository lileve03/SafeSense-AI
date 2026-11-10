"""CPU-only offline inference. Run from project root: python -m uvicorn fight_api:app --port 8001."""
from pathlib import Path
from functools import lru_cache
from tempfile import NamedTemporaryFile
from threading import Lock
from collections import OrderedDict, deque
from uuid import uuid4
import hashlib
import json
import os
import time
import shutil
import subprocess
from urllib.request import Request, urlopen
from urllib.error import URLError

import cv2
import joblib
import numpy as np
import torch
from fastapi import FastAPI, UploadFile, File, Form, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from torchvision.models.video import r3d_18, R3D_18_Weights
from backend.main import ZONES
from backend.cpu_profile import stage, memory_sample

PROJECT_ROOT = Path(__file__).resolve().parent
MODEL_CONFIG = {
    'v2': {'path': PROJECT_ROOT / 'evaluation/outputs/fight_multiclip_v2/fight_multiclip_classifier.joblib', 'threshold': .4},
    'v3': {'path': PROJECT_ROOT / 'evaluation/outputs/fight_v3/fight_v3_classifier.joblib', 'threshold': .7},
}
MAX_UPLOAD_BYTES = 100 * 1024 * 1024
MAX_FRAMES = 3600
MAX_PIXELS = 1920 * 1080
MAX_SECONDS = 120
ALLOWED_EXTENSIONS = {'.mp4', '.avi', '.mpg', '.mpeg'}
TOKEN = os.getenv('SAFESENSE_API_TOKEN', 'local-demo-only')
BACKEND_URL = os.getenv('SAFESENSE_BACKEND_URL', 'http://127.0.0.1:8000')
OUTPUT_DIR = Path(os.getenv('SAFESENSE_ANNOTATION_DIR',str(PROJECT_ROOT/'runtime/annotations')))
inference_lock = Lock()
CPU_THREADS=max(1,min(int(os.getenv('SAFESENSE_CPU_THREADS','4')),os.cpu_count() or 1))
POSE_THREADS=max(1,min(int(os.getenv('SAFESENSE_POSE_THREADS','8')),os.cpu_count() or 1))
POSE_IMAGE_SIZE=max(320,min(960,round(int(os.getenv('SAFESENSE_POSE_IMG_SIZE','640'))/32)*32))
torch.set_num_threads(CPU_THREADS)
cv2.setNumThreads(1)
video_scan_cache=OrderedDict()
feature_cache = OrderedDict()
artifacts = {}
app = FastAPI(title='SafeSense offline AI inference', version='2.0.0')
app.add_middleware(CORSMiddleware, allow_origins=['http://localhost:3000','http://127.0.0.1:3000','http://localhost:3001','http://127.0.0.1:3001','http://localhost:5173','http://127.0.0.1:5173'], allow_methods=['GET','POST'], allow_headers=['Content-Type','X-SafeSense-Token'])


def authorize(token):
    import secrets
    if not token or not secrets.compare_digest(token, TOKEN):
        raise HTTPException(401, 'Missing or invalid local demo access token')


def validate_zone(zone_id, authorized):
    if zone_id not in ZONES:
        raise HTTPException(422, 'Unknown zone; select a registered public zone')
    if ZONES[zone_id]['type'] != 'OPEN_HIDDEN':
        raise HTTPException(403, 'Video is prohibited in private areas')
    if not authorized:
        raise HTTPException(403, 'Confirm that you are authorized to analyze this public-area video')


@lru_cache(maxsize=1)
def get_extractor():
    weights = R3D_18_Weights.DEFAULT
    # Fail clearly offline instead of attempting an implicit network download.
    checkpoint = Path(torch.hub.get_dir()) / 'checkpoints' / Path(weights.url).name
    if not checkpoint.is_file():
        raise FileNotFoundError('Pretrained R3D-18 checkpoint missing from Torch cache; see README')
    model = r3d_18(weights=weights).cpu().eval()
    model.fc = torch.nn.Identity()
    torch.set_num_threads(CPU_THREADS)
    return model, weights.transforms()


@lru_cache(maxsize=2)
def get_classifier(version):
    path = MODEL_CONFIG[version]['path']
    if not path.is_file():
        raise FileNotFoundError(f'{version} classifier unavailable')
    classifier = joblib.load(path)
    if classifier.n_features_in_ != 1536 or list(classifier.classes_) != [0, 1]:
        raise ValueError('Classifier feature/class contract does not match training')
    return classifier


def sample_indices(count):
    bounds = np.linspace(0, count, 4).astype(int)
    return [np.linspace(min(bounds[i], count-1), max(min(bounds[i],count-1)+1,bounds[i+1])-1,16).astype(int) for i in range(3)]


def scan_video(path):
    """Count actual decodable frames without retaining a full video in RAM."""
    cap = cv2.VideoCapture(str(path))
    count = 0
    started = time.monotonic()
    try:
        if not cap.isOpened():
            raise ValueError('Cannot decode this video')
        fps = cap.get(cv2.CAP_PROP_FPS)
        if not np.isfinite(fps) or not 0 < fps <= 120:
            raise ValueError('Invalid or unsupported video FPS')
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            count += 1
            if frame.shape[0]*frame.shape[1] > MAX_PIXELS:
                raise ValueError('Video exceeds 1920x1080 pixel budget')
            if count > MAX_FRAMES or count/fps > MAX_SECONDS or time.monotonic()-started > 45:
                raise ValueError('Video exceeds decode budget: 120 seconds / 3600 frames')
        if count < 1:
            raise ValueError('No decodable video frames')
        return count, fps
    finally:
        cap.release()


def validated_scan(path,digest,profile):
    hit=digest in video_scan_cache
    profile['decode_scan_cache_hit']=hit
    if hit:video_scan_cache.move_to_end(digest);return video_scan_cache[digest]
    result=scan_video(path);video_scan_cache[digest]=result
    while len(video_scan_cache)>16:video_scan_cache.popitem(last=False)
    return result


def extract_features(path, count, profile=None):
    profile=profile if profile is not None else {}
    with stage(profile,'r3d_model_load_sec'):
        model, preprocess = get_extractor()
    indices = sample_indices(count)
    wanted = set(np.concatenate(indices).tolist())
    selected = {}
    cap = cv2.VideoCapture(str(path))
    decode_started=time.perf_counter()
    try:
        for i in range(count):
            ok=cap.grab()
            if not ok:raise ValueError('Video changed or decode failed on second pass')
            if i in wanted:
                ok,frame=cap.retrieve()
                if not ok:raise ValueError('Selected sample could not be decoded')
                # Same RGB frames, uint8 tensor, transforms and frame indices as V2/V3 training.
                selected[i] = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        profile['sample_decode_sec']=round(time.perf_counter()-decode_started,6)
        features = []
        with torch.inference_mode():
            for ids in indices:
                with stage(profile,'preprocess_sec'):
                    frames = torch.from_numpy(np.stack([selected[int(i)] for i in ids])).permute(0,3,1,2)
                    inputs=preprocess(frames).unsqueeze(0)
                with stage(profile,'r3d_inference_sec'):
                    features.append(model(inputs).squeeze().numpy())
        result = np.concatenate(features).astype(np.float32).reshape(1,1536)
        if not np.isfinite(result).all():
            raise ValueError('Nonfinite extracted features')
        return result
    finally:
        cap.release()


def notify_backend(result, event_type, score, evidence):
    payload = {'zone':result['zone_id'], 'type':event_type, 'source':'vision',
               'confidence':score if score is not None else 1.0, 'score':score, 'model_version':result['model_version'],
               'processing_mode':'real_model', 'evidence_reference':evidence,
               'event_id':result['analysis_id']}
    payload['evidence_media']=result.get('evidence_media',[])
    from monitoring_ai import CONTEXT
    if CONTEXT.get().get('analysis_run_id'):
        payload['analysis_run_id']=CONTEXT.get()['analysis_run_id']
        result['analysis_run_id']=payload['analysis_run_id']
    payload['camera_id']=CONTEXT.get().get('camera_id')
    payload['source_type']=CONTEXT.get().get('source_type','RECORDED REAL VIDEO')
    payload['is_test']=payload['source_type']!='LIVE CAMERA'
    req = Request(BACKEND_URL+'/event', data=json.dumps(payload).encode(), headers={'Content-Type':'application/json','X-SafeSense-Token':TOKEN,'X-SafeSense-Ingest-Token':os.getenv('SAFESENSE_INGEST_TOKEN','')}, method='POST')
    try:
        with urlopen(req, timeout=8) as response:
            data = json.load(response)
        return {'status':'recorded','event_id':data['event']['id'],'incident_id':data['incident']['id'] if data.get('incident') else None}
    except (URLError, TimeoutError, OSError) as exc:
        # Preserve actual inference while making event delivery failure visible.
        return {'status':'failed','error':str(exc),'retry':'Rerun analysis after backend is available; feature cache avoids repeat extraction'}


@app.get('/health')
@app.get('/ai/fight/health')
def health():
    return {'status':'ok','overlay_contract':'pose-tracks-v2','participant_heuristic':'pose-interaction-v1','device':'cpu','processing_mode':'real_model','scope':'offline public-area analysis','models':models(), 'fall':{'weights_available':(PROJECT_ROOT/'yolo11n-pose.pt').is_file(),'status':'experimental pose + rule'}, 'access':'local demo token; no identity provider'}


@app.get('/ai/fight/models')
def models():
    return [{'version':v,'threshold':c['threshold'],'available':c['path'].is_file(),'score_type':'uncalibrated classifier score','feature_dimension':1536} for v,c in MODEL_CONFIG.items()]


def save_upload(file):
    extension = Path(file.filename or '').suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, 'Supported formats: MP4, AVI, MPG, MPEG')
    path = None
    try:
        digest = hashlib.sha256()
        with NamedTemporaryFile(delete=False, suffix=extension) as temp:
            path = Path(temp.name)
            size = 0
            while chunk := file.file.read(1024*1024):
                size += len(chunk)
                if size > MAX_UPLOAD_BYTES:
                    raise HTTPException(413,'Upload exceeds 100 MB')
                digest.update(chunk)
                temp.write(chunk)
        if size == 0:
            raise HTTPException(422,'Video is empty')
        return path, digest.hexdigest()
    except Exception:
        if path:
            path.unlink(missing_ok=True)
        raise


@app.post('/ai/fight/analyze')
def analyze_fight(file: UploadFile=File(...), model_version: str=Form('v3'), zone_id: str=Form(...), authorized: bool=Form(False), zone_type: str=Form('open_hidden'), x_safesense_token: str|None=Header(None)):
    path = None
    acquired = False
    try:
        authorize(x_safesense_token)
        validate_zone(zone_id,authorized)
        if zone_type.lower() != 'open_hidden':
            raise HTTPException(403,'Private-area video prohibited')
        if model_version not in MODEL_CONFIG:
            raise HTTPException(400,'Select model v2 or v3')
        acquired = inference_lock.acquire(blocking=False)
        if not acquired:
            raise HTTPException(429,'AI service busy; retry when current analysis finishes')
        started = time.perf_counter()
        profile={}
        with stage(profile,'classifier_load_sec'):
            classifier = get_classifier(model_version)
        with stage(profile,'upload_copy_hash_sec'):
            path, digest = save_upload(file)
        cached = digest in feature_cache
        if cached:
            feature, count, fps = feature_cache[digest]
            feature_cache.move_to_end(digest)
        else:
            with stage(profile,'decode_scan_sec'):
                count, fps = validated_scan(path,digest,profile)
            feature = extract_features(path,count,profile)
            feature_cache[digest] = (feature,count,fps)
            while len(feature_cache) > 16:
                feature_cache.popitem(last=False)
        with stage(profile,'classifier_sec'):
            score = float(classifier.predict_proba(feature)[0,1])
        threshold = MODEL_CONFIG[model_version]['threshold']
        detected = score >= threshold
        result = {'status':'success','analysis_id':str(uuid4()),'zone_id':zone_id,'zone_type':'OPEN_HIDDEN','model_version':model_version,
                  'input_sha256':digest,'prediction':'possible_physical_conflict' if detected else 'no_conflict_flag','violence_score':score,'score':score,'threshold':threshold,
                  'candidate_detected':bool(detected),'review_status':'pending_human_review' if detected else 'not_flagged',
                  'video_duration_sec':round(count/fps,3),'inference_time_sec':round(time.perf_counter()-started,3),
                  'device':'cpu','processing_mode':'real_model','feature_cache_hit':cached,'profile':profile,
                  'note':'Whole-video uncalibrated classifier score; no frame-level timing or automatic emergency escalation.'}
        from monitoring_ai import capture
        with stage(profile,'evidence_capture_sec'):
            result['evidence_media']=capture(result,path)
        result['video_fps']=fps
        result['sampled_frames']=48
        result['inference_fps']=0 if cached else round(48/max(.001,result['inference_time_sec']),3)
        result['feature_extraction_status']='cached features; no frame inference this run' if cached else '48 frame samples extracted this run'
        result['frame_skipping']='48 training-compatible frame samples; no temporal localization'
        result['dropped_frames']=None
        with stage(profile,'event_delivery_sec'):
            result['event_delivery'] = notify_backend(result,'possible_conflict' if detected else 'normal_motion',score,'sha256:'+digest)
        profile['total_wall_sec']=round(time.perf_counter()-started,6);profile['cpu_threads']=torch.get_num_threads();profile.update(memory_sample())
        return result
    except HTTPException:
        raise
    except FileNotFoundError as exc:
        raise HTTPException(503,str(exc)) from exc
    except (ValueError, cv2.error) as exc:
        raise HTTPException(422,str(exc)) from exc
    except Exception as exc:
        raise HTTPException(503,f'Inference unavailable ({type(exc).__name__}): {exc}') from exc
    finally:
        file.file.close()
        if path:
            path.unlink(missing_ok=True)
        if acquired:
            inference_lock.release()


@lru_cache(maxsize=1)
def get_pose():
    from ultralytics import YOLO
    path = PROJECT_ROOT/'yolo11n-pose.pt'
    if not path.is_file():
        raise FileNotFoundError('YOLO11n-Pose weights missing')
    return YOLO(str(path))


@app.post('/ai/fall/analyze')
def analyze_fall(file: UploadFile=File(...), zone_id: str=Form(...), authorized: bool=Form(False), x_safesense_token: str|None=Header(None)):
    path = output = None
    acquired = False
    cap = writer = None
    completed = False
    try:
        authorize(x_safesense_token)
        validate_zone(zone_id,authorized)
        acquired = inference_lock.acquire(blocking=False)
        if not acquired:
            raise HTTPException(429,'AI service busy')
        started = time.perf_counter()
        from scripts.safesense_temporal_fall import posture_of_person
        profile={}
        torch.set_num_threads(POSE_THREADS)
        with stage(profile,'pose_model_load_sec'):
            model = get_pose()
        with stage(profile,'upload_copy_hash_sec'):
            path,digest = save_upload(file)
        with stage(profile,'decode_scan_sec'):
            count,fps = validated_scan(path,digest,profile)
        OUTPUT_DIR.mkdir(parents=True,exist_ok=True)
        existing = sorted(OUTPUT_DIR.glob('*.mp4'), key=lambda p:p.stat().st_mtime)
        for stale in existing[:-9]:
            stale.unlink(missing_ok=True)
            artifacts.pop(stale.stem,None)
        artifact_id = str(uuid4())
        output = OUTPUT_DIR/(artifact_id+'.mp4')
        cap = cv2.VideoCapture(str(path))
        w,h = int(cap.get(3)),int(cap.get(4))
        writer = cv2.VideoWriter(str(output),cv2.VideoWriter_fourcc(*'mp4v'),fps,(w,h))
        if not writer.isOpened():
            raise ValueError('MP4 encoder unavailable')
        from backend.pose_tracking import PoseRuleTracker
        tracker = PoseRuleTracker()
        candidate_frames = 0
        state = 'NORMAL'
        events = []
        pose_frames = []
        for frame_no in range(1,count+1):
            with stage(profile,'pose_decode_sec'):
                ok,frame = cap.read()
            if not ok:
                raise ValueError('Fall video decode failed')
            if time.perf_counter()-started > 180:
                raise ValueError('Fall processing exceeded 180-second CPU budget; use a shorter clip')
            with stage(profile,'yolo_predict_wall_sec'):
                prediction = model.predict(frame,device='cpu',conf=.25,imgsz=POSE_IMAGE_SIZE,verbose=False)[0]
            if torch.get_num_threads()!=POSE_THREADS:torch.set_num_threads(POSE_THREADS)
            for name,ms in prediction.speed.items():profile['yolo_'+name+'_sec']=round(profile.get('yolo_'+name+'_sec',0)+ms/1000,6)
            # Preserve actual detections; conservative association is applied below.
            boxes = prediction.boxes
            points = prediction.keypoints
            people = []
            if boxes is not None:
                xyxy = boxes.xyxy.cpu().tolist()
                confidence = boxes.conf.cpu().tolist()
                coordinates = points.xy.cpu().tolist() if points is not None else []
                point_confidence = points.conf.cpu().tolist() if points is not None and points.conf is not None else []
                for index, bounds in enumerate(xyxy):
                    people.append({'bbox_xyxy':[round(v,3) for v in bounds],
                        'confidence':round(confidence[index],6),
                        'keypoints':[{'x':round(x,3),'y':round(y,3),
                            'confidence':round(point_confidence[index][k],6) if index<len(point_confidence) else None}
                            for k,(x,y) in enumerate(coordinates[index] if index<len(coordinates) else [])]})
            pose_frames.append({'frame_index':frame_no-1,'time_sec':round((frame_no-1)/fps,6),'persons':people})
            postures = [(posture_of_person(prediction,frame.shape,i) or {}).get('posture','not_detected') for i in range(len(people))]
            events.extend(tracker.update(people,postures,frame_no-1,fps))
            active = [p for p in people if p['fall_rule_active']]
            state = 'POSSIBLE FALL' if active else ('FALL CANDIDATE' if any(p['fall_state']=='FALL CANDIDATE' for p in people) else 'NORMAL')
            pose_frames[-1].update(fall_state=state,fall_score=None)
            candidate_frames += int(state!='NORMAL')
            with stage(profile,'annotation_draw_write_sec'):
                annotated=prediction.plot(boxes=False,labels=False)
                for person in people:
                    x1,y1,x2,y2=map(int,person['bbox_xyxy'])
                    red=person['fall_rule_active']
                    color=(0,0,255) if red else (255,211,34)
                    cv2.rectangle(annotated,(x1,y1),(x2,y2),color,2)
                    label=('POSSIBLE FALL | binary ACTIVE' if red else 'Person')+f" | T{person['track_id']} | detector {person['confidence']:.3f}"
                    cv2.putText(annotated,label,(max(0,x1),max(15,y1-5)),cv2.FONT_HERSHEY_SIMPLEX,.4,color,1)
                cv2.putText(annotated,'Experimental rule | '+state,(12,30),cv2.FONT_HERSHEY_SIMPLEX,.55,(0,0,255) if active else (255,211,34),2)
                writer.write(annotated)
        writer.release(); writer=None
        playback = 'mp4v_download'
        encoding_note = 'FFmpeg unavailable; download MP4V for a local player'
        encode_started=time.perf_counter()
        ffmpeg = shutil.which('ffmpeg')
        if ffmpeg:
            browser_output = output.with_suffix('.browser.mp4')
            try:
                subprocess.run([ffmpeg,'-nostdin','-v','error','-y','-i',str(output),'-an',
                    '-vf','pad=ceil(iw/2)*2:ceil(ih/2)*2','-c:v','libx264','-preset','ultrafast',
                    '-crf','23','-pix_fmt','yuv420p','-movflags','+faststart',str(browser_output)],
                    check=True,timeout=45,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,
                    creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
                browser_output.replace(output)
                playback='h264_browser'
                encoding_note='H.264 MP4; no audio track'
            except (subprocess.SubprocessError,OSError) as exc:
                encoding_note=f'Browser encoding unavailable ({type(exc).__name__}); download original MP4V'
            finally:
                browser_output.unlink(missing_ok=True)
        profile['annotation_encode_sec']=round(time.perf_counter()-encode_started,6)
        # Keep a bounded library of generated evidence, never research outputs.
        artifacts[artifact_id]=output
        while len(artifacts)>10:
            old=next(iter(artifacts)); artifacts.pop(old).unlink(missing_ok=True)
        result={'status':'success','analysis_id':str(uuid4()),'model_version':'yolo11n-pose-temporal-rule-v1','zone_id':zone_id,
                'processing_mode':'real_model','profile':profile,'experimental':True,'events':events,'candidate_frames':candidate_frames,
                'input_sha256':digest,'pose_frames':pose_frames,'tracking_available':True,'tracking_method':'conservative_iou_v1','fall_rule_version':'per-track-transition-v2','person_confidence_threshold':.25,
                'annotation_alignment':{'fps':fps,'frame_count':count,'width':w,'height':h,'start_sec':0,'frame_skipping':0},
                'candidate_detected':bool(events),'review_status':'pending_human_review' if events else 'not_flagged',
                'video_duration_sec':round(count/fps,3),'inference_time_sec':round(time.perf_counter()-started,3),
                'annotation_playback':playback,'encoding_note':encoding_note,'annotated_video_url':'/ai/fall/artifacts/'+artifact_id,'note':'Real pose inference + experimental per-track posture transition rule. Recording-local conservative IoU association; missing or ambiguous matches reset history. Binary rule, no trained fall score or identity recognition.'}
        completed = True
        from monitoring_ai import capture
        with stage(profile,'evidence_capture_sec'):
            result['evidence_media']=capture(result,path,annotated_path=output)
        result['video_fps']=fps
        result['processed_frames']=count
        result['inference_fps']=round(count/max(.001,result['inference_time_sec']),3)
        result['frame_skipping']=0
        result['dropped_frames']=0
        with stage(profile,'event_delivery_sec'):
            result['event_delivery']=notify_backend(result,'fall' if events else 'normal_motion',None,'sha256:'+digest+';annotation:'+artifact_id)
        profile['total_wall_sec']=round(time.perf_counter()-started,6);profile['pose_predict_fps']=round(count/max(.001,profile.get('yolo_predict_wall_sec',0)),3);profile['cpu_threads']=torch.get_num_threads();profile.update(memory_sample())
        return result
    except HTTPException:
        raise
    except (ValueError,cv2.error) as exc:
        raise HTTPException(422,str(exc)) from exc
    except Exception as exc:
        raise HTTPException(503,f'Fall inference unavailable: {exc}') from exc
    finally:
        if cap: cap.release()
        if writer: writer.release()
        if output and not completed: output.unlink(missing_ok=True)
        file.file.close()
        if path: path.unlink(missing_ok=True)
        if acquired: inference_lock.release()


@app.get('/ai/fall/artifacts/{artifact_id}')
def annotation(artifact_id: str, token: str='', x_safesense_token: str|None=Header(None)):
    authorize(x_safesense_token or token)
    if artifact_id not in artifacts:
        try:
            if str(__import__('uuid').UUID(artifact_id))!=artifact_id:raise ValueError()
        except ValueError:raise HTTPException(404,'Annotation unavailable')
        retained=OUTPUT_DIR/(artifact_id+'.mp4')
        if not retained.is_file():raise HTTPException(404,'Annotation unavailable (retention limit reached)')
        artifacts[artifact_id]=retained
    return FileResponse(artifacts[artifact_id],media_type='video/mp4')

from monitoring_ai import install as install_monitoring
install_monitoring(app)
