"""Offline UR Fall RGB-sequence baseline. Not a validated fall detector."""
import argparse, csv, json, re, statistics, time, zipfile
from pathlib import Path
import cv2
import numpy as np

PAT = re.compile(r'^(fall|adl)-(\d+)-cam0-rgb$', re.I)

def sequence_id(name):
    m = PAT.match(name)
    return (m.group(0).lower(), 1 if m.group(1).lower() == 'fall' else 0) if m else None

def discover(root):
    found = {}
    for p in root.rglob('*'):
        if p.is_dir():
            key = sequence_id(p.name)
            if key and any(p.rglob('*.png')): found[key[0]] = (p, key[1], 'dir')
        elif p.suffix.lower() == '.zip':
            key = sequence_id(p.stem)
            if key: found.setdefault(key[0], (p, key[1], 'zip'))
    return [found[k] for k in sorted(found)]

def frames(path, kind, stride):
    if kind == 'dir':
        items = sorted(path.rglob('*.png'))
        for i, p in enumerate(items[::stride]):
            img = cv2.imread(str(p))
            if img is not None: yield str(p.relative_to(path)), img
    else:
        with zipfile.ZipFile(path) as z:
            items = sorted(x for x in z.namelist() if x.lower().endswith('.png') and not x.startswith('__MACOSX'))
            for name in items[::stride]:
                a = np.frombuffer(z.read(name), dtype=np.uint8)
                img = cv2.imdecode(a, cv2.IMREAD_COLOR)
                if img is not None: yield name, img

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--data', required=True)
    p.add_argument('--output-dir', default='evaluation/outputs/yolo_pose')
    p.add_argument('--model',default='yolo11n-pose.pt')
    p.add_argument('--device',default='cpu')
    p.add_argument('--imgsz',type=int,default=640)
    p.add_argument('--stride',type=int,default=3,help='Sample every Nth source image')
    p.add_argument('--limit-sequences',type=int,default=0)
    p.add_argument('--min-confidence',type=float,default=0.25)
    a=p.parse_args()
    if a.stride<1: p.error('--stride must be >= 1')
    root=Path(a.data)
    if not root.is_dir(): p.error(f'Dataset folder missing: {root}')
    seqs=discover(root)
    if a.limit_sequences: seqs=seqs[:a.limit_sequences]
    if not seqs: p.error('No sequence folders / ZIPs matching fall-01-cam0-rgb or adl-01-cam0-rgb found')
    from ultralytics import YOLO
    model=YOLO(a.model)
    out=Path(a.output_dir);out.mkdir(parents=True,exist_ok=True)
    perframe=[]; perseq=[]
    for path,gt,kind in seqs:
        sid=path.stem if kind=='zip' else path.name
        vals=[]; elapsed=[]; positions=[]; count=0
        for fname,img in frames(path,kind,a.stride):
            tick=time.perf_counter()
            r=model.predict(img,device=a.device,imgsz=a.imgsz,conf=a.min_confidence,verbose=False)[0]
            elapsed_ms=(time.perf_counter()-tick)*1000
            elapsed.append(elapsed_ms)
            count+=1
            conf=0.0; aspect=None; center_y=None; torso_angle=None
            if r.boxes is not None and len(r.boxes)>0:
                ids=r.boxes.conf.cpu().numpy()
                i=int(np.argmax(ids))  # largest-confidence subject; no tracking
                conf=float(ids[i])
                xyxy=r.boxes.xyxy[i].cpu().numpy()
                x1,y1,x2,y2=map(float,xyxy)
                w=max(1.0,x2-x1);h=max(1.0,y2-y1)
                aspect=w/h
                center_y=((y1+y2)/2)/img.shape[0]
                if r.keypoints is not None:
                    k=r.keypoints.data[i].cpu().numpy()
                    if k.shape[0]>12:
                        sh=(k[5,:2]+k[6,:2])/2
                        hip=(k[11,:2]+k[12,:2])/2
                        if np.all(sh>0) and np.all(hip>0):
                            d=hip-sh
                            torso_angle=float(np.degrees(np.arctan2(abs(d[0]),abs(d[1])+1e-6)))
            vals.append((aspect,torso_angle))
            positions.append(center_y)
            perframe.append(dict(sequence=sid,frame=fname,gt_sequence=gt,person_conf=round(conf,5),bbox_aspect=aspect,torso_angle_from_vertical=torso_angle,person_center_y_normalized=center_y,inference_ms=round(elapsed_ms,2)))
        # Simple sequence-level pose+geometry heuristic, NOT pretrained fall classification.
        # Horizontal torso or wide bbox can occur during ADLs; use only for baseline research.
        horizontal=sum(1 for aspect,angle in vals if (aspect is not None and aspect>1.15) or (angle is not None and angle>60))
        n_detected=sum(1 for aspect,angle in vals if aspect is not None)
        fraction=horizontal/max(1,n_detected)
        # Conservative demonstration threshold; fix before examining test labels.
        pred=int(n_detected>=3 and fraction>=0.15)
        perseq.append(dict(sequence=sid,ground_truth=gt,predicted=pred,frames=count,frames_with_person=n_detected,horizontal_fraction=round(fraction,4),mean_inference_ms=round(statistics.mean(elapsed),2) if elapsed else None,source=str(path)))
        print(f'{sid}: GT={gt} pred={pred} frames={count} horizontal={fraction:.3f}')
    def write(name,rows):
        if not rows:return
        with (out/name).open('w',newline='',encoding='utf-8') as f:
            w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    write('pose_frames.csv',perframe)
    write('sequence_predictions.csv',perseq)
    tp=sum(x['ground_truth']==1 and x['predicted']==1 for x in perseq)
    fp=sum(x['ground_truth']==0 and x['predicted']==1 for x in perseq)
    fn=sum(x['ground_truth']==1 and x['predicted']==0 for x in perseq)
    tn=sum(x['ground_truth']==0 and x['predicted']==0 for x in perseq)
    pr=tp/(tp+fp) if tp+fp else None
    re=tp/(tp+fn) if tp+fn else None
    metrics=dict(sequences=len(perseq),fall_sequences=sum(x['ground_truth'] for x in perseq),adl_sequences=sum(1-x['ground_truth'] for x in perseq),TP=tp,FP=fp,FN=fn,TN=tn,precision=pr,recall=re,f1=(2*pr*re/(pr+re) if pr is not None and re is not None and pr+re>0 else None),accuracy=(tp+tn)/len(perseq),model=a.model,algorithm='fixed heuristic: >=15% wide-box / near-horizontal torso frames, minimum 3 detections',label_unit='sequence (NOT every frame)',note='Preliminary fixed-threshold non-tracking baseline; sequence label positive if any fall anywhere, not onset-annotated.' )
    (out/'metrics.json').write_text(json.dumps(metrics,indent=2),encoding='utf-8')
    print(json.dumps(metrics,indent=2));print('Saved:',out.resolve())

if __name__=='__main__':main()
