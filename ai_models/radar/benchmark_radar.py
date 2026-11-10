"""Offline TI IWR6843 point-cloud fall benchmark (no hardware needed).

Uses recording-level features and Leave-One-Subject-Out evaluation.
No C1001 claims; predictions are dataset recordings, not real-time fall events.
"""
import argparse
import csv
import json
import re
import time
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, confusion_matrix, precision_recall_fscore_support
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC

SUBJECTS = ('areeb', 'raffay', 'towsif')
FEATURES = ('n_points','n_frames','points_per_frame_mean','points_per_frame_std',
            'x_std','y_std','z_std','z_range','z_first_last_delta','z_centroid_std',
            'speed_abs_mean','speed_abs_max','speed_abs_std','speed_change_mean',
            'snr_mean','snr_std')

def identify(path: Path, root: Path):
    rel = str(path.relative_to(root)).replace('\\','/').lower()
    # Do not guess labels for ambiguous filenames; fail loudly instead.
    fall_words = ('frontfall', 'backfall', 'sidefall', 'front_fall','back_fall','side_fall',
                  'fall_front','fall_back','fall_side')
    nonfall_words = ('nonfall','notfall','not_fall','non_fall','bow','squat','walk','adl')
    has_nonfall = any(w in rel.replace(' ','').replace('-','_') for w in nonfall_words)
    has_fall = any(w in rel.replace(' ','').replace('-','_') for w in fall_words)
    if not has_fall and not has_nonfall:
        # 'fall' unqualified is accepted only when non-fall is absent.
        has_fall = bool(re.search(r'(^|[/_\-])fall([/_\-.]|$)', rel))
    if has_nonfall == has_fall:
        raise ValueError(f'Unclear fall/ADL label from path: {rel}')
    people = [s for s in SUBJECTS if s in rel]
    if len(people) != 1:
        raise ValueError(f'Cannot determine unique subject (Areeb, Raffay, Towsif): {rel}')
    return int(has_fall), people[0]

def get_col(df, *options):
    normalized = {re.sub(r'[^a-z0-9]','',str(c).lower()): c for c in df.columns}
    for opt in options:
        key = re.sub(r'[^a-z0-9]','',opt.lower())
        if key in normalized:
            return normalized[key]
    return None

def feature_extract(path):
    df = pd.read_csv(path)
    cols = [get_col(df,n) for n in ('frame','x','y','z','v')]
    if any(c is None for c in cols):
        raise ValueError(f'{path.name}: required frame,x,y,z,v columns absent; found {list(df.columns)}')
    frame,x,y,z,v = cols
    dat = df[[frame,x,y,z,v]].copy()
    for c in (x,y,z,v): dat[c] = pd.to_numeric(dat[c], errors='coerce')
    dat = dat.dropna(subset=[frame,x,y,z,v])
    if len(dat)<5: raise ValueError(f'{path.name}: fewer than 5 valid points')
    per = dat.groupby(frame, sort=True)
    counts = per.size().to_numpy(dtype=float)
    z_means = per[z].mean().to_numpy(dtype=float)
    speed_means = per[v].apply(lambda s: np.mean(np.abs(s.to_numpy(dtype=float)))).to_numpy()
    snr_col = get_col(df, 'snr')
    snr = pd.to_numeric(df[snr_col], errors='coerce').dropna().to_numpy() if snr_col else np.array([])
    vals = {
        'n_points':len(dat), 'n_frames':len(counts),
        'points_per_frame_mean':counts.mean(), 'points_per_frame_std':counts.std(),
        'x_std':dat[x].std(), 'y_std':dat[y].std(), 'z_std':dat[z].std(),
        'z_range':dat[z].max()-dat[z].min(),
        'z_first_last_delta':abs(z_means[-1]-z_means[0]),
        'z_centroid_std':z_means.std(),
        'speed_abs_mean':np.abs(dat[v]).mean(), 'speed_abs_max':np.abs(dat[v]).max(),
        'speed_abs_std':np.abs(dat[v]).std(),
        'speed_change_mean':np.mean(np.abs(np.diff(speed_means))) if len(speed_means)>1 else 0,
        'snr_mean':snr.mean() if len(snr) else 0, 'snr_std':snr.std() if len(snr) else 0,
    }
    return {k:float(np.nan_to_num(val)) for k,val in vals.items()}

def run(root,out):
    csvs=sorted(root.rglob('*.csv'))
    if not csvs: raise SystemExit(f'No CSV files under {root}. Download dataset into this folder first.')
    rows=[]; skipped=[]
    for p in csvs:
        try:
            label,subject=identify(p,root)
            feat=feature_extract(p)
            rows.append({'file':str(p.relative_to(root)), 'label':label,'subject':subject,**feat})
        except Exception as e: skipped.append({'file':str(p.relative_to(root)),'reason':str(e)})
    out.mkdir(parents=True,exist_ok=True)
    pd.DataFrame(skipped,columns=['file','reason']).to_csv(out/'skipped_files.csv',index=False)
    if not rows: raise SystemExit('No labeled records. Check skipped_files.csv and filename/subject mapping.')
    df=pd.DataFrame(rows)
    df.to_csv(out/'radar_features.csv',index=False)
    print(f'Recordings accepted: {len(df)} | skipped: {len(skipped)}')
    print('Label counts:',df.label.value_counts().to_dict())
    print('Subject counts:',df.subject.value_counts().to_dict())
    if df.subject.nunique()<3:
        raise SystemExit('Need all 3 subject IDs for 3-fold LOSO. Check skipped_files.csv and source filenames.')
    if df.groupby('subject').label.nunique().min()<2:
        raise SystemExit('Every held-out subject needs both classes for meaningful evaluation.')
    preds=[]; fold_metrics=[]
    for name in ['SVM_RBF','RandomForest']:
        for held in SUBJECTS:
            train=df[df.subject!=held]; test=df[df.subject==held]
            if train.empty or test.empty: raise SystemExit(f'No samples for LOSO fold {held}')
            model=(make_pipeline(StandardScaler(),SVC(kernel='rbf',probability=True,random_state=42))
                   if name=='SVM_RBF' else RandomForestClassifier(n_estimators=200,random_state=42,class_weight='balanced'))
            start=time.perf_counter();model.fit(train[list(FEATURES)],train.label)
            train_sec=time.perf_counter()-start
            t=time.perf_counter();proba=model.predict_proba(test[list(FEATURES)])[:,list(model.classes_).index(1)]
            inference_ms=(time.perf_counter()-t)*1000/len(test)
            prediction=(proba>=0.5).astype(int)
            p,r,f,_=precision_recall_fscore_support(test.label,prediction,average='binary',zero_division=0)
            tn,fp,fn,tp=confusion_matrix(test.label,prediction,labels=[0,1]).ravel()
            fold_metrics.append(dict(model=name,held_out_subject=held,n_test=len(test),accuracy=accuracy_score(test.label,prediction),precision=p,recall=r,f1=f,TP=int(tp),FP=int(fp),FN=int(fn),TN=int(tn),train_seconds=train_sec,mean_predict_ms_per_record=inference_ms))
            for (_,item),score,pred in zip(test.iterrows(),proba,prediction):
                preds.append(dict(model=name,fold_subject=held,file=item.file,ground_truth=int(item.label),prediction=int(pred),fall_probability=round(float(score),5),data_source='TI_IWR6843_DATASET',mode='OFFLINE_EVALUATION'))
    pred_df=pd.DataFrame(preds);metric_df=pd.DataFrame(fold_metrics)
    pred_df.to_csv(out/'radar_predictions.csv',index=False)
    metric_df.to_csv(out/'radar_loso_folds.csv',index=False)
    summary=[]
    for name,part in pred_df.groupby('model'):
        p,r,f,_=precision_recall_fscore_support(part.ground_truth,part.prediction,average='binary',zero_division=0)
        tn,fp,fn,tp=confusion_matrix(part.ground_truth,part.prediction,labels=[0,1]).ravel()
        summary.append(dict(model=name,recordings=len(part),accuracy=accuracy_score(part.ground_truth,part.prediction),precision=p,recall=r,f1=f,TP=int(tp),FP=int(fp),FN=int(fn),TN=int(tn)))
    pd.DataFrame(summary).to_csv(out/'radar_loso_summary.csv',index=False)
    print('\nLOSO summary (out-of-fold predictions, real recorded radar data):')
    print(pd.DataFrame(summary).to_string(index=False))
    print(f'\nSaved: {out.resolve()}')

if __name__=='__main__':
    ap=argparse.ArgumentParser()
    ap.add_argument('--data',type=Path,required=True,help='Folder containing actual downloaded CSV files')
    ap.add_argument('--output',type=Path,default=Path('evaluation/outputs/radar_route_a'))
    a=ap.parse_args();run(a.data,a.output)
