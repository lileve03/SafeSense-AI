"""SafeSense Phase 5B: permissioned PUBLIC/OPEN_HIDDEN camera research prototype.
No video is saved. This is NOT a validated violence or fall detector.
"""
import argparse
import time
import os
import cv2
import numpy as np
import requests
from ultralytics import YOLO
try:
    from .temporal_logic import Observation, TemporalAnalyzer
except ImportError:
    from temporal_logic import Observation, TemporalAnalyzer


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument('--zone', default='Corridor A')
    p.add_argument('--camera', type=int, default=0)
    p.add_argument('--model', default='yolo11n-pose.pt')
    p.add_argument('--api', default='http://127.0.0.1:8000')
    p.add_argument('--send', action='store_true', help='Post candidate events to local prototype API')
    p.add_argument('--device', default='cpu')
    p.add_argument('--threshold', type=float, default=.14)
    p.add_argument('--cooldown', type=float, default=8.0)
    p.add_argument('--no-display', action='store_true')
    return p.parse_args()


def authorize_zone(api, zone):
    # Fail closed: camera must only be used for a known, approved OPEN_HIDDEN zone.
    response = requests.get(api.rstrip('/') + '/zones', timeout=6)
    response.raise_for_status()
    zones = response.json()
    found = [z for z in zones if zone in (z.get('name'),z.get('id'))]
    # Backend canonical names may not equal aliases (Corridor A matches).
    if not found or found[0].get('zone_type') != 'OPEN_HIDDEN' or 'vision' not in found[0].get('allowed_sources', []):
        raise RuntimeError(f'Camera DENIED: {zone!r} not registered as OPEN_HIDDEN with vision permission')
    return found[0]


def classify_pose(xy, conf, box, height, width):
    """COCO 17-keypoint rough posture proxy; confidence and geometry gates.
    A side-on or occluded upright person can be mistaken for horizontal.
    """
    # shoulders 5,6; hips 11,12. Only use torso if all four keypoints visible.
    keys = [5,6,11,12]
    if len(xy) < 13 or any(float(conf[i]) < .55 for i in keys):
        return False, False, False
    shoulder = (xy[5]+xy[6]) / 2
    hip = (xy[11]+xy[12]) / 2
    dx, dy = abs(float(hip[0]-shoulder[0])), abs(float(hip[1]-shoulder[1]))
    torso_horiz = dx > 1.45 * max(dy, 1.0)
    torso_upright = dy > 1.15 * max(dx, 1.0)
    # constrain with person's detection box orientation; horizontal lying posture only
    bw, bh = float(box[2]), float(box[3])
    horizontal = torso_horiz and bw > 1.15*max(bh,1.0)
    upright = torso_upright and bh > 1.15*max(bw,1.0)
    return horizontal, upright, True


def main():
    a = parse_args()
    try:
        zone = authorize_zone(a.api, a.zone)
    except Exception as exc:
        raise SystemExit(f'Zone permission verification failed. Camera will NOT start. {exc}')
    print('Authorized OPEN_HIDDEN zone:', zone['id'], '|', 'SEND' if a.send else 'PREVIEW')
    model = YOLO(a.model)
    cam = cv2.VideoCapture(a.camera, cv2.CAP_DSHOW)
    if not cam.isOpened():
        raise SystemExit('Camera unavailable; try --camera 1 or check Windows privacy permissions')
    analyzer = TemporalAnalyzer(motion_threshold=a.threshold,cooldown=a.cooldown)
    last_report = 0
    print('Press Q or Ctrl+C to stop. No video frames saved.')
    try:
        while True:
            ret, frame = cam.read()
            if not ret:
                break
            now = time.monotonic()
            result = model.track(frame, persist=True, tracker='bytetrack.yaml',
                                 device=a.device, conf=.45, verbose=False)[0]
            annotated = result.plot()
            boxes = result.boxes
            pose = result.keypoints
            candidate_events = []
            if boxes is not None and boxes.id is not None and pose is not None:
                ids = boxes.id.int().cpu().tolist()
                bxywh = boxes.xywh.cpu().numpy()
                kxy = pose.xy.cpu().numpy()
                kconf = (pose.conf.cpu().numpy() if pose.conf is not None
                         else np.ones((len(kxy),17)))
                H, W = frame.shape[:2]
                for i, ident in enumerate(ids):
                    if i>=len(kxy):
                        continue
                    horizontal, upright, reliable = classify_pose(kxy[i], kconf[i], bxywh[i], H, W)
                    cx,cy = bxywh[i,:2]
                    obs = Observation(now, (float(cx/W),float(cy/H)),horizontal,upright,reliable)
                    for event_type in analyzer.update(ident,obs):
                        candidate_events.append((ident,event_type))
            analyzer.expire(now)
            for ident, event_type in candidate_events:
                print(f'CANDIDATE track {ident}: {event_type} (unverified heuristic)')
                if a.send:
                    payload = {'zone':zone['id'],'type':event_type,'confidence':1.0,'score':None,'source':'vision','processing_mode':'real_model','model_version':'YOLO11-Pose-temporal-heuristic','evidence_reference':'transient camera pose rule; no saved video'}
                    try:
                        response = requests.post(a.api.rstrip('/')+'/event',json=payload,headers={'X-SafeSense-Token':os.getenv('SAFESENSE_API_TOKEN','local-demo-only')},timeout=5)
                        response.raise_for_status()
                        print('POSTED:', response.json().get('event',{}).get('level'))
                    except requests.RequestException as exc:
                        print('POST FAILED:',exc)
            if now-last_report>2:
                last_report=now
                print('tracked persons:',0 if boxes is None or boxes.id is None else len(boxes.id),
                      '| candidates:',len(candidate_events))
            cv2.putText(annotated,'OPEN_HIDDEN | TEMPORAL POSE | '+('SEND' if a.send else 'PREVIEW'),
                        (12,28),cv2.FONT_HERSHEY_SIMPLEX,.55,(20,180,50),2)
            if not a.no_display:
                cv2.imshow('SafeSense - public zone temporal pose',annotated)
                if cv2.waitKey(1)&0xff==ord('q'):
                    break
    except KeyboardInterrupt:
        pass
    finally:
        cam.release()
        cv2.destroyAllWindows()

if __name__=='__main__':
    main()
