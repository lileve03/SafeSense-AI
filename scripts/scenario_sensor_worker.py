"""Fresh file-only sensor inference in the retained dedicated environments."""
from pathlib import Path
import argparse,hashlib,json,os,sys,time
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from backend import registry

def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def radar(source,path,model_name):
    import joblib,pandas as pd,sklearn
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler
    from sklearn.svm import SVC
    from sklearn.ensemble import RandomForestClassifier
    from ai_models.radar.benchmark_radar import feature_extract,identify,FEATURES
    _,subject=identify(path,ROOT/'datasets/private/radar/iwr6843')
    table=ROOT/'evaluation/outputs/radar_route_a/radar_features.csv'
    table_hash=digest(table)
    data=pd.read_csv(table);training=data[data.subject!=subject]
    if training.empty or training.label.nunique()!=2:raise ValueError('Existing LOSO training fold is unavailable')
    features=feature_extract(path)  # Always read raw points; never return a saved prediction.
    cache=ROOT/'runtime/scenario-model-cache';cache.mkdir(parents=True,exist_ok=True)
    artifact=cache/f'{model_name}-{subject}-{table_hash[:16]}-{sklearn.__version__}.joblib'
    cached=artifact.is_file();fit_started=time.perf_counter()
    if cached:model=joblib.load(artifact)
    else:
        model=make_pipeline(StandardScaler(),SVC(kernel='rbf',probability=True,random_state=42)) if model_name=='SVM_RBF' else RandomForestClassifier(n_estimators=200,random_state=42,class_weight='balanced')
        model.fit(training[list(FEATURES)],training.label)
        joblib.dump(model,artifact)
    setup_sec=time.perf_counter()-fit_started
    frame=pd.DataFrame([[features[k] for k in FEATURES]],columns=list(FEATURES))
    started=time.perf_counter();score=float(model.predict_proba(frame)[0,list(model.classes_).index(1)])
    return {'model_version':f'{model_name}-LOSO-reconstructed','score':score,'threshold':.5,'candidate_detected':score>=.5,
            'prediction':'possible_fall' if score>=.5 else 'no_fall_flag','inference_time_sec':round(time.perf_counter()-started,6),
            'features':features,'n_points':int(features['n_points']),'n_frames':int(features['n_frames']),
            'training_subject_excluded':subject,'training_recordings':len(training),'training_feature_sha256':table_hash,
            'model_setup_sec':round(setup_sec,6),'model_cache_hit':cached,
            'note':'Existing LOSO benchmark reconstructed from its saved training feature table, excluding this recording subject. Fresh features and prediction from raw CSV. Radar points are not people; no occupant count, room positions, person tracking or validated fall timestamp.'}

def acoustic(source,path):
    import numpy as np,soundfile as sf
    from backend.scenario_catalog import yamnet_path
    from ai_models.acoustic.evaluate_fsd50k import load_yamnet,load_audio
    model_path=yamnet_path()
    if not model_path:raise FileNotFoundError('Local YAMNet cache unavailable; automatic model downloads are disabled')
    info=sf.info(str(path))
    if not 0<info.duration<=120 or info.channels>8 or path.stat().st_size>30*1024*1024:raise ValueError('Research audio exceeds 120-second / 30 MiB / 8-channel budget')
    model,mapping,tf=load_yamnet(str(model_path))
    target=next(r for r in mapping if r['display_name']=='Screaming')
    waveform=load_audio(path,tf)
    started=time.perf_counter();scores,_,_=model(waveform)
    from backend.acoustic_windows import score_windows
    series=scores.numpy()[:,int(target['index'])]
    score=float(np.max(series))
    windows=score_windows(series,.5,info.duration)
    return {**windows,'model_version':'YAMNet-pretrained-local-cache','score':score,'threshold':.5,'candidate_detected':score>=.5,
            'prediction':'scream_candidate' if score>=.5 else 'no_scream_flag','inference_time_sec':round(time.perf_counter()-started,6),
            'audio_duration_sec':round(info.duration,6),'original_sample_rate':info.samplerate,'target':'Screaming','target_mid':target['mid'],
            'model_sha256':digest(model_path/'saved_model.pb'),'model_cache_hit':True,
            'note':'Fresh YAMNet waveform inference using the existing cached pretrained model and evaluation preprocessing. Maximum clip-level Screaming score, not calibrated probability or validated event timestamp. No microphone, speech recognition, waveform export or new audio recording.'}

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--scenario',required=True);parser.add_argument('--model',required=True);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    source=next((s for s in registry.raw_sensor_scenarios() if s['id']==args.scenario),None)
    if not source or not source['available']:raise FileNotFoundError('Registered raw sensor recording unavailable')
    allowed=['SVM_RBF','RandomForest'] if source['kind']=='radar' else ['YAMNet']
    if args.model not in allowed:raise ValueError('Unsupported model for registered sensor modality')
    path=(ROOT/source['path']).resolve()
    if not path.is_relative_to((ROOT/'datasets').resolve()):raise ValueError('Source must stay in the authorized dataset tree')
    output=args.output.resolve()
    if not output.is_relative_to((ROOT/'runtime/scenario-tests').resolve()):raise ValueError('Result must stay in runtime/scenario-tests')
    started=time.perf_counter()
    result=radar(source,path,args.model) if source['kind']=='radar' else acoustic(source,path)
    result.update(scenario_id=source['id'],input_path=source['path'],input_sha256=digest(path),
                  processing_mode='real_model',source_type='RECORDED SENSOR DATA',output_origin='fresh_raw_input_inference',
                  time_scope='recording_level_no_validated_event_timestamp',total_worker_sec=round(time.perf_counter()-started,6))
    output.write_text(json.dumps(result,allow_nan=False),encoding='utf-8')
    print(json.dumps({'scenario':source['id'],'model':result['model_version'],'score':result['score'],'candidate':result['candidate_detected']}),flush=True)

if __name__=='__main__':main()
