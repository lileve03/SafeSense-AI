"""SafeSense AI Phase 5 - public/open hidden area pose prototype.

This is a locally-operated demo/research tool, not a validated violence detector.
Camera frames are processed in memory; none are saved by this script.
"""
import argparse
import time
import os
from collections import deque

import cv2
import numpy as np
import requests
from ultralytics import YOLO
try:
    from .yolo_pose_temporal import authorize_zone
except ImportError:
    from yolo_pose_temporal import authorize_zone


def args_parser():
    p = argparse.ArgumentParser(description='SafeSense YOLO11-Pose camera prototype')
    p.add_argument('--camera', type=int, default=0, help='OpenCV camera index')
    p.add_argument('--zone', default='Corridor A', help='Registered OPEN_HIDDEN backend zone')
    p.add_argument('--model', default='yolo11n-pose.pt', help='Ultralytics pose checkpoint')
    p.add_argument('--api', default='http://127.0.0.1:8000', help='FastAPI base URL')
    p.add_argument('--send', action='store_true', help='Send qualified events to backend')
    p.add_argument('--threshold', type=float, default=0.14, help='Normalized center displacement / second (prototype threshold)')
    p.add_argument('--persist-seconds', type=float, default=0.9, help='How long elevated movement must persist')
    p.add_argument('--cooldown-seconds', type=float, default=8, help='Minimum time between requests')
    p.add_argument('--device', default='cpu', help='Inference device; cpu or 0 if available')
    p.add_argument('--no-display', action='store_true', help='Disable display window')
    return p.parse_args()


def main():
    a = args_parser()
    try:
        approved = authorize_zone(a.api, a.zone)
        a.zone = approved['id']
    except Exception as exc:
        raise SystemExit(f'Zone permission verification failed; camera will not start: {exc}')
    print('Loading pose model:', a.model)
    model = YOLO(a.model)
    camera = cv2.VideoCapture(a.camera, cv2.CAP_DSHOW)
    if not camera.isOpened():
        raise SystemExit(f'Cannot open webcam index {a.camera}. Try --camera 1 or check Windows privacy settings.')
    print('Camera open. Zone:', a.zone, '| mode:', 'SEND ENABLED' if a.send else 'PREVIEW ONLY')
    print('Press Q in video window or Ctrl+C to stop.')
    last_centers = {}  # track ID -> (x,y,time)
    motion_times = deque()
    last_post = 0.0
    last_log = 0.0
    try:
        while True:
            ok, frame = camera.read()
            if not ok:
                print('Camera frame unavailable; stopping')
                break
            t = time.monotonic()
            result = model.track(frame, persist=True, verbose=False, device=a.device, conf=0.4, tracker='bytetrack.yaml')[0]
            annotated = result.plot()
            height, width = frame.shape[:2]
            speeds = []
            boxes = result.boxes
            current_ids = set()
            if boxes is not None and boxes.id is not None:
                ids = boxes.id.int().cpu().tolist()
                centers = boxes.xywh.cpu().numpy()[:, :2]
                for track_id, (cx, cy) in zip(ids, centers):
                    current_ids.add(track_id)
                    nx, ny = cx / width, cy / height
                    previous = last_centers.get(track_id)
                    if previous:
                        px, py, pt = previous
                        dt = t - pt
                        if 0.05 < dt < 1.5:
                            speeds.append(float(np.hypot(nx - px, ny - py) / dt))
                    last_centers[track_id] = (nx, ny, t)
            # Remove stale tracks; don't infer individual identity.
            last_centers = {i: v for i, v in last_centers.items() if t - v[2] < 3.0}
            max_speed = max(speeds, default=0.0)
            if max_speed >= a.threshold:
                motion_times.append(t)
            while motion_times and motion_times[0] < t - a.persist_seconds:
                motion_times.popleft()
            # Require repeated recent elevated movement observations across most of the window.
            sustained = len(motion_times) >= 4 and t - motion_times[0] >= a.persist_seconds * 0.65
            if t - last_log > 2:
                last_log = t
                print(f'Persons tracked: {len(current_ids)} | motion proxy: {max_speed:.3f}/s | sustained: {sustained}')
            if sustained and t - last_post >= a.cooldown_seconds:
                last_post = t
                # Detection/pose tracking provides a movement proxy, NOT a calibrated probability.
                # confidence is an event-acceptance marker; this rule has no classifier score.
                payload = {'zone': a.zone, 'type': 'rapid_motion', 'confidence': 1.0, 'score': None, 'source': 'vision', 'processing_mode': 'real_model', 'model_version': 'YOLO11-Pose-motion-heuristic', 'evidence_reference': 'transient pose motion rule; no saved video'}
                if a.send:
                    try:
                        response = requests.post(a.api.rstrip('/') + '/event', json=payload, headers={'X-SafeSense-Token':os.getenv('SAFESENSE_API_TOKEN','local-demo-only')}, timeout=5)
                        response.raise_for_status()
                        event = response.json().get('event', {})
                        print('EVENT POSTED:', payload, '| backend level:', event.get('level'))
                    except requests.RequestException as exc:
                        print('POST FAILED:', exc)
                else:
                    print('CANDIDATE (preview; not sent): rapid_motion', payload)
                motion_times.clear()
            cv2.putText(annotated, 'OPEN_HIDDEN | YOLO POSE | ' + ('SEND' if a.send else 'PREVIEW'), (15, 28), cv2.FONT_HERSHEY_SIMPLEX, .62, (30, 220, 100), 2)
            if not a.no_display:
                cv2.imshow('SafeSense AI - Open Hidden Camera', annotated)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
    except KeyboardInterrupt:
        pass
    finally:
        camera.release()
        cv2.destroyAllWindows()
        print('Stopped. This script does not record video.')


if __name__ == '__main__':
    main()
