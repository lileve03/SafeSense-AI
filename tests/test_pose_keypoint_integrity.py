"""Independently compare recorded overlay keypoints against actual YOLO inference."""
from pathlib import Path
import sys,json,sqlite3
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import cv2,numpy as np,torch
from ultralytics import YOLO
from backend.registry import source
OUT=ROOT/'runtime/live-ai-final'
db=max(OUT.glob('test-*.sqlite3'),key=lambda p:p.stat().st_mtime)
with sqlite3.connect('file:'+str(db)+'?mode=ro',uri=True) as connection:
    jobs=[json.loads(row[0]) for row in connection.execute("SELECT body FROM records WHERE kind='job' ORDER BY rowid")]
selected={}
for job in jobs:
    if job.get('status')=='COMPLETED' and job.get('result',{}).get('pose_frames'):selected[job['camera_id']]=job
model=YOLO(str(ROOT/'yolo11n-pose.pt'));torch.set_num_threads(8);rows=[]
for camera,job in selected.items():
    result=job['result'];samples=[f for f in result['pose_frames'] if f['persons']];frame=samples[len(samples)//2]
    _,path=source(job['scenario_id']);cap=cv2.VideoCapture(str(path));cap.set(cv2.CAP_PROP_POS_FRAMES,frame['frame_index']);ok,pixels=cap.read();cap.release();assert ok
    actual=model.predict(pixels,device='cpu',conf=.25,imgsz=640,verbose=False)[0]
    assert len(actual.boxes)==len(frame['persons'])
    for index,person in enumerate(frame['persons']):
        assert np.allclose(person['bbox_xyxy'],actual.boxes.xyxy[index].cpu().tolist(),atol=.001)
        assert np.allclose([[k['x'],k['y']] for k in person['keypoints']],actual.keypoints.xy[index].cpu().tolist(),atol=.001)
        assert np.allclose([k['confidence'] for k in person['keypoints']],actual.keypoints.conf[index].cpu().tolist(),atol=.000001)
    rows.append({'camera':camera,'status':'PASS','frame_index':frame['frame_index'],'persons':len(frame['persons']),'independent_boxes_and_17_keypoints':True,'source_time_sec':frame['time_sec']})
assert len(rows)==5
(OUT/'keypoint-integrity.json').write_text(json.dumps(rows,indent=2),encoding='utf-8');print(json.dumps(rows))
