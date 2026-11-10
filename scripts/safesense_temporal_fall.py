"""SafeSense V1: experimental temporal fall-candidate detector based on YOLO11-Pose.

This is a hand-crafted temporal heuristic, not a trained fall classifier.
It screens one most-confident person per frame; it does not identify people or injuries.
"""
import argparse
import csv
from collections import deque
from pathlib import Path

import cv2
import numpy as np
from ultralytics import YOLO


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument('--source', required=True, help='Input MP4 path')
    p.add_argument('--model', default='yolo11n-pose.pt')
    p.add_argument('--output-dir', default='evaluation/outputs/temporal_fall_v1')
    p.add_argument('--device', default='cpu')
    p.add_argument('--conf', type=float, default=0.25)
    p.add_argument('--imgsz', type=int, default=640)
    p.add_argument('--window', type=int, default=12, help='Frames for posture persistence')
    p.add_argument('--min-horizontal', type=int, default=5, help='Horizontal frames within window')
    p.add_argument('--min-upright', type=int, default=3, help='Prior upright frames for transition')
    return p.parse_args()


def posture_of_person(result, frame_shape, person_index=None):
    """Return the requested person posture, or the highest-confidence person by default.

    x/y keypoint positions alone are not reliable if occluded. Require shoulder and hip
    keypoints with plausible confidences where available, otherwise fall back to box ratio.
    """
    if result.boxes is None or len(result.boxes) == 0:
        return None
    idx = int(result.boxes.conf.argmax().item()) if person_index is None else person_index
    xyxy = result.boxes.xyxy[idx].cpu().numpy().astype(float)
    x1, y1, x2, y2 = xyxy
    bw, bh = max(1., x2-x1), max(1., y2-y1)
    box_ratio = bw / bh
    center_y = (y1+y2)/2 / frame_shape[0]
    label = 'unknown'
    torso_angle = None
    if result.keypoints is not None and len(result.keypoints) > idx:
        xy = result.keypoints.xy[idx].cpu().numpy()
        kp_conf = result.keypoints.conf
        kc = kp_conf[idx].cpu().numpy() if kp_conf is not None else np.ones(len(xy))
        if len(xy) >= 13:
            shoulders = [(xy[i],kc[i]) for i in (5,6) if kc[i]>=0.35 and np.all(np.isfinite(xy[i]))]
            hips = [(xy[i],kc[i]) for i in (11,12) if kc[i]>=0.35 and np.all(np.isfinite(xy[i]))]
            if shoulders and hips:
                shoulder = np.mean([item[0] for item in shoulders], axis=0)
                hip = np.mean([item[0] for item in hips], axis=0)
                dx = abs(float(shoulder[0]-hip[0]))
                dy = abs(float(shoulder[1]-hip[1]))
                torso_angle = float(np.degrees(np.arctan2(dy, max(dx,1e-6))))
                # angle close to 0: horizontal torso, close to 90: upright torso
                if torso_angle < 40 and box_ratio > 0.85:
                    label = 'horizontal'
                elif torso_angle > 58 and box_ratio < 1.1:
                    label = 'upright'
                else:
                    label = 'other'
    if label == 'unknown':
        if box_ratio > 1.25:
            label = 'horizontal'
        elif box_ratio < 0.65:
            label = 'upright'
        else:
            label = 'other'
    return {
        'person_conf': float(result.boxes.conf[idx].item()),
        'box_ratio': float(box_ratio),
        'center_y': float(center_y),
        'torso_angle': torso_angle,
        'posture': label,
    }


def main():
    a = parse_args()
    if a.window < 2 or a.min_horizontal < 1 or a.min_horizontal > a.window:
        raise ValueError('Invalid window/min-horizontal settings')
    source = Path(a.source)
    if not source.is_file():
        raise FileNotFoundError(f'Video not found: {source}')
    out = Path(a.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    cap = cv2.VideoCapture(str(source))
    if not cap.isOpened():
        raise RuntimeError(f'Cannot open video: {source}')
    fps = cap.get(cv2.CAP_PROP_FPS)
    if not (0 < fps < 240):
        fps = 30.
    w, h = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    output_video = out / f'{source.stem}_temporal_annotated.mp4'
    video = cv2.VideoWriter(str(output_video),cv2.VideoWriter_fourcc(*'mp4v'),fps,(w,h))
    if not video.isOpened():
        raise RuntimeError('Cannot open MP4 output writer; check OpenCV codecs')
    model = YOLO(a.model)
    history = deque(maxlen=a.window)
    recent_upright = 0
    state = 'NORMAL'
    candidate_frames = 0
    rows = []
    events = []
    frame_no = 0
    no_detection = 0
    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            frame_no += 1
            result = model.predict(frame,device=a.device,conf=a.conf,imgsz=a.imgsz,verbose=False)[0]
            pose = posture_of_person(result,frame.shape)
            posture = pose['posture'] if pose else 'not_detected'
            # If no person is visible, clear history to avoid false persistence.
            if pose is None:
                no_detection += 1
                if no_detection >= 3:
                    history.clear()
                    recent_upright = 0
                    state = 'NORMAL'
            else:
                no_detection = 0
                history.append(posture)
                if posture == 'upright':
                    recent_upright = min(a.window, recent_upright + 1)
                horizontal_count = sum(x == 'horizontal' for x in history)
                if posture == 'horizontal' and horizontal_count >= a.min_horizontal:
                    if state == 'NORMAL':
                        if recent_upright >= a.min_upright:
                            state = 'POSSIBLE FALL'
                            events.append({'frame':frame_no,'time_sec':round((frame_no-1)/fps,3),'type':'possible_fall','reason':'upright_to_persistent_horizontal'})
                        else:
                            state = 'FALL CANDIDATE'
                elif posture == 'upright':
                    if state != 'NORMAL' and sum(x == 'upright' for x in history) >= a.min_upright:
                        state = 'NORMAL'
                elif posture == 'other' and horizontal_count < 2 and state == 'FALL CANDIDATE':
                    state = 'NORMAL'
            if state != 'NORMAL':
                candidate_frames += 1
            annotated = result.plot()
            color = (0,0,255) if state == 'POSSIBLE FALL' else (0,175,255) if state == 'FALL CANDIDATE' else (0,190,0)
            cv2.rectangle(annotated,(8,8),(min(w-8,510),84),(20,20,20),-1)
            cv2.putText(annotated,f'SafeSense V1 | {state}',(18,38),cv2.FONT_HERSHEY_SIMPLEX,0.72,color,2)
            cv2.putText(annotated,f'Frame {frame_no} | Pose: {posture}',(18,69),cv2.FONT_HERSHEY_SIMPLEX,0.56,(255,255,255),2)
            video.write(annotated)
            rows.append({
                'frame':frame_no,'time_sec':round((frame_no-1)/fps,3),
                'person_detected':int(pose is not None),
                'person_conf':round(pose['person_conf'],4) if pose else '',
                'posture':posture,
                'torso_angle_deg':round(pose['torso_angle'],2) if pose and pose['torso_angle'] is not None else '',
                'bbox_width_height_ratio':round(pose['box_ratio'],3) if pose else '',
                'state':state
            })
    finally:
        cap.release()
        video.release()
    csv_path = out / f'{source.stem}_frames.csv'
    with csv_path.open('w',newline='',encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f,fieldnames=['frame','time_sec','person_detected','person_conf','posture','torso_angle_deg','bbox_width_height_ratio','state'])
        writer.writeheader()
        writer.writerows(rows)
    event_path = out / f'{source.stem}_events.csv'
    with event_path.open('w',newline='',encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f,fieldnames=['frame','time_sec','type','reason'])
        writer.writeheader()
        writer.writerows(events)
    print('Done')
    print('Frames:',frame_no)
    print('Frames with non-normal state:',candidate_frames)
    print('Possible fall events:',len(events))
    print('Video:',output_video.resolve())
    print('Frame CSV:',csv_path.resolve())
    print('Events CSV:',event_path.resolve())
    print('NOTE: Experimental heuristic, not validated medical or injury detection.')

if __name__=='__main__':
    main()
