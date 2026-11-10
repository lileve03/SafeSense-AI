"""Incident-bound retained evidence. Never substitutes a recording or another analysis."""
from pathlib import Path
from uuid import UUID, uuid4
import json
import math
import os
import shutil
import subprocess
from threading import Lock
from fastapi import HTTPException
from backend import storage

ROOT=Path(__file__).resolve().parents[1]
EVIDENCE=Path(os.getenv('SAFESENSE_EVIDENCE_DIR',str(ROOT/'runtime/evidence')))
LOCK=Lock()

def uuid(value):
    try:
        if str(UUID(value))!=value:raise ValueError()
    except (ValueError,TypeError,AttributeError):raise HTTPException(404,'Evidence not found')

def annotate(path,output,start,end):
    ffmpeg=shutil.which('ffmpeg')
    if not ffmpeg or not path.is_file():return False
    temporary=output.with_name(output.stem+'-'+str(uuid4())+'.tmp.mp4')
    try:
        subprocess.run([ffmpeg,'-nostdin','-v','error','-y','-ss',str(start),'-i',str(path),'-t',str(end-start),
            '-an','-vf','pad=ceil(iw/2)*2:ceil(ih/2)*2','-c:v','libx264','-preset','ultrafast',
            '-pix_fmt','yuv420p','-movflags','+faststart',str(temporary)],check=True,timeout=50,
            stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        temporary.replace(output)
        return True
    except (OSError,subprocess.SubprocessError):return False
    finally:temporary.unlink(missing_ok=True)

def matching_output(metadata):
    # Legacy recovery requires the exact analysis ID, zone and model. Similar scores are irrelevant.
    for job in reversed(storage.all_rows('job')):
        result=job.get('result') or {}
        for output in result.get('model_results',[result]):
            if (output.get('analysis_id')==metadata.get('analysis_id') and
                output.get('zone_id')==metadata.get('zone_id') and
                output.get('model_version')==metadata.get('model_version')):
                return output
    return {}

def resolve(incident_id,evidence_id,recover=True):
    uuid(incident_id);uuid(evidence_id)
    incident=next((i for i in storage.all_rows('incident') if i['id']==incident_id),None)
    if not incident:raise HTTPException(404,'Incident not found')
    from backend.main import ZONES
    if incident.get('zone_type')!='OPEN_HIDDEN' or ZONES.get(incident.get('zone_id'),{}).get('type')!='OPEN_HIDDEN':
        raise HTTPException(403,'Private incidents permit sensor metadata only')
    matches=[(e,m) for e in incident.get('evidence',[]) for m in e.get('evidence_media',[]) if m.get('id')==evidence_id]
    if not matches:raise HTTPException(404,'Evidence does not belong to this incident')
    observation,reference=matches[0]
    sidecar=EVIDENCE/(evidence_id+'.json')
    try:metadata=json.loads(sidecar.read_text(encoding='utf-8'))
    except (OSError,ValueError):raise HTTPException(410,'Evidence metadata expired or unavailable')
    for field in ('id','zone_id','analysis_id','model_version','camera_id','score','source_type','start_sec','end_sec','duration_sec'):
        if metadata.get(field)!=reference.get(field):raise HTTPException(409,'Evidence identity does not match the selected incident')
    if metadata.get('zone_id')!=incident['zone_id'] or metadata.get('analysis_id')!=observation.get('id') or metadata.get('model_version')!=observation.get('model_version'):
        raise HTTPException(409,'Evidence analysis does not match the selected incident')
    if any(field in observation and observation[field] is not None and metadata.get(field)!=observation[field] for field in ('camera_id','score','source_type')):
        raise HTTPException(409,'Evidence detection metadata does not match the selected incident')
    for key in ('start_sec','end_sec','duration_sec'):
        if not isinstance(metadata.get(key),(int,float)) or not math.isfinite(metadata[key]) or metadata[key]<0:
            raise HTTPException(409,'Evidence timing metadata is invalid')
    if metadata['end_sec']<=metadata['start_sec']:raise HTTPException(409,'Evidence interval is invalid')
    original=EVIDENCE/(evidence_id+'.mp4')
    annotated=EVIDENCE/(evidence_id+'.annotated.mp4')
    output=matching_output(metadata) if recover else {}
    # A retained derivative is trusted only when explicitly registered by capture/recovery.
    registered=metadata.get('annotation_analysis_id')==metadata['analysis_id']
    if recover and original.is_file() and not registered and output.get('annotated_video_url'):
        url=output['annotated_video_url'];artifact=url.removeprefix('/ai/fall/artifacts/')
        try:uuid(artifact)
        except HTTPException:artifact=''
        alignment=output.get('annotation_alignment') or {}
        source_hash=output.get('input_sha256')
        provenance=observation.get('evidence_reference') or ''
        if artifact and source_hash and ('sha256:'+source_hash) in provenance and alignment.get('frame_skipping')==0:
            with LOCK:
                if annotate(Path(os.getenv('SAFESENSE_ANNOTATION_DIR',str(ROOT/'runtime/annotations')))/(artifact+'.mp4'),annotated,metadata['start_sec'],metadata['end_sec']):
                    metadata['annotation_analysis_id']=metadata['analysis_id']
                    metadata['annotation_alignment']=alignment
                    # Keep original retention age; recovery never extends evidence lifetime.
                    age=sidecar.stat().st_mtime
                    sidecar.write_text(json.dumps(metadata),encoding='utf-8')
                    os.utime(sidecar,(age,age));os.utime(annotated,(original.stat().st_atime,original.stat().st_mtime))
                    registered=True
    manifest={**metadata,'incident_id':incident_id,'incident_timestamp':incident['created_at'],
        'observation_timestamp':observation.get('timestamp'),'prediction':metadata.get('prediction') or output.get('prediction') or observation.get('type'),
        'threshold':metadata.get('threshold',output.get('threshold')),
        'processing_mode':observation.get('processing_mode'),'source_type':metadata.get('source_type') or observation.get('source_type'),
        'original_available':original.is_file(),'annotated_available':registered and annotated.is_file(),
        'annotation_note':'Actual retained YOLO detections; recording-local tracks where supported. No fighter localization.' if registered and annotated.is_file() else 'No matching retained annotation available. Original evidence has no invented overlays.'}
    overlay_path=EVIDENCE/(evidence_id+'.overlays.json')
    if metadata.get('overlay_analysis_id')==metadata['analysis_id'] and overlay_path.is_file():
        try:overlay=json.loads(overlay_path.read_text(encoding='utf-8'))
        except (OSError,ValueError):overlay={}
        if overlay.get('analysis_id')==metadata['analysis_id'] and overlay.get('input_sha256')==metadata.get('input_sha256') and overlay.get('camera_id')==metadata.get('camera_id'):
            manifest['overlay_result']=overlay
    if metadata.get('model_version') in ('v2','v3'):
        manifest.setdefault('overlay_result',{'camera_id':metadata.get('camera_id')})['model_results']=[{'model_version':metadata['model_version'],'score':metadata.get('score'),'prediction':manifest['prediction'],'candidate_detected':metadata.get('candidate_detected',isinstance(metadata.get('score'),(int,float)) and isinstance(manifest.get('threshold'),(int,float)) and metadata['score']>=manifest['threshold'])}]
    return manifest,original,annotated


def thumbnail(incident_id, evidence_id):
    """A representative frame of this incident's retained public clip, never a substitute."""
    import cv2
    import numpy as np
    metadata, original, _ = resolve(incident_id, evidence_id, recover=False)
    if not original.is_file():
        raise HTTPException(410, 'Retained evidence unavailable')
    cap = cv2.VideoCapture(str(original))
    try:
        if not cap.isOpened():
            raise HTTPException(410, 'Retained evidence cannot be decoded')
        duration = metadata['duration_sec']
        event = metadata.get('event_time_sec')
        offset = event - metadata['start_sec'] if isinstance(event, (int, float)) and math.isfinite(event) else duration / 2
        offset = min(max(0, duration - .05), max(0, offset))
        cap.set(cv2.CAP_PROP_POS_MSEC, offset * 1000)
        ok, frame = cap.read()
        if not ok:
            raise HTTPException(410, 'Evidence frame unavailable')
        height, width = frame.shape[:2]
        scale = min(960 / width, 540 / height)
        image = cv2.resize(frame, (max(1, round(width * scale)), max(1, round(height * scale))))
        canvas = np.full((540, 960, 3), (40, 23, 12), dtype=np.uint8)
        top, left = (540 - image.shape[0]) // 2, (960 - image.shape[1]) // 2
        canvas[top:top + image.shape[0], left:left + image.shape[1]] = image
        ok, encoded = cv2.imencode('.jpg', canvas, [cv2.IMWRITE_JPEG_QUALITY, 92])
        if not ok:
            raise HTTPException(503, 'Thumbnail encoding unavailable')
        return encoded.tobytes(), round(metadata['start_sec'] + offset, 3)
    finally:
        cap.release()
