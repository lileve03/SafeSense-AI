"""Fresh genuine UR Fall inference; only event transport is disabled for isolation."""
import os,sys,json,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
OUT=ROOT/'runtime/retained-overlay-check';OUT.mkdir(parents=True,exist_ok=True)
os.environ.update(SAFESENSE_EVIDENCE_DIR=str(OUT/'evidence'),SAFESENSE_ANNOTATION_DIR=str(OUT/'annotations'),TELEGRAM_MODE='disabled',SAFESENSE_API_TOKEN='retained-overlay-test')
import cv2
from fastapi import UploadFile
import fight_api
from backend.registry import source
fight_api.notify_backend=lambda *args,**kwargs:{'status':'disabled_for_isolated_media_test'}
_,path=source('fall');started=time.perf_counter()
with path.open('rb') as stream:
    result=fight_api.analyze_fall(file=UploadFile(filename=path.name,file=stream),zone_id='ZONE_STAIRCASE',authorized=True,x_safesense_token=fight_api.TOKEN)
frames=[f for f in result['pose_frames'] if any(p['fall_rule_active'] for p in f['persons'])];assert frames
frame=frames[len(frames)//2];item=result['evidence_media'][0]
assert item['annotation_analysis_id']==result['analysis_id']
cap=cv2.VideoCapture(str(OUT/'evidence'/(item['id']+'.annotated.mp4')))
cap.set(cv2.CAP_PROP_POS_MSEC,(frame['time_sec']-item['start_sec'])*1000);ok,image=cap.read();cap.release();assert ok
person=next(p for p in frame['persons'] if p['fall_rule_active']);x1,y1,x2,y2=map(int,person['bbox_xyxy'])
patch=image[max(0,y1-2):y1+3,max(0,x1):x2]
assert ((patch[:,:,2]>150)&(patch[:,:,1]<110)&(patch[:,:,0]<110)).any()
assert person['fall_score'] is None and person['track_id']>0
cv2.imwrite(str(OUT/'retained-fall-frame.png'),image)
summary={'status':'PASS','processed_frames':result['processed_frames'],'supported_red_frames':len(frames),'event':result['events'][0],'inspected_frame':frame['frame_index'],'source_time_sec':frame['time_sec'],'analysis_id':result['analysis_id'],'inference_time_sec':result['inference_time_sec'],'pose_predict_fps':result['profile']['pose_predict_fps'],'total_test_sec':round(time.perf_counter()-started,3),'event_transport':'disabled; inference and evidence encoding genuine'}
(OUT/'results.json').write_text(json.dumps(summary,indent=2),encoding='utf-8');print(json.dumps(summary))
