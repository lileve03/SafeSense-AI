"""Local prerequisites and one source registry for scenario testing. No model imports."""
from pathlib import Path
import os,tempfile
from backend import registry

ROOT=registry.ROOT

def yamnet_path():
    explicit=os.getenv('SAFESENSE_YAMNET_PATH')
    if explicit:
        path=Path(explicit)
        return path if (path/'saved_model.pb').is_file() and (path/'assets/yamnet_class_map.csv').is_file() else None
    roots=[]
    cache=Path(os.getenv('TFHUB_CACHE_DIR',str(Path(tempfile.gettempdir())/'tfhub_modules')))
    if cache.is_dir():roots.extend(p.parent for p in cache.glob('*/saved_model.pb'))
    for path in roots:
        if (path/'saved_model.pb').is_file() and (path/'assets/yamnet_class_map.csv').is_file():return path
    return None

def catalog():
    rows=[]
    for original in registry.scenarios():
        row={**original}
        fresh=row['input_type'] in ('video','radar_recording','audio_sample')
        row['execution_kind']='fresh_inference' if fresh else 'saved_prediction_replay' if row['input_type']=='sensor_metadata' else 'controlled_test'
        row['allowed_models']=['all','v2','v3','pose'] if row['input_type']=='video' else ['SVM_RBF','RandomForest'] if row['input_type']=='radar_recording' else ['YAMNet'] if row['input_type']=='audio_sample' else []
        row['default_model']='all' if row.get('kind')=='fight' else row.get('model')
        missing=[]
        if not row['available']:missing.append('Registered input file missing')
        if row['input_type']=='radar_recording':
            if not (ROOT/'.venv-radar/Scripts/python.exe').is_file():missing.append('Radar environment missing')
            if not (ROOT/'evaluation/outputs/radar_route_a/radar_features.csv').is_file():missing.append('Existing LOSO feature table missing')
        if row['input_type']=='audio_sample':
            if not (ROOT/'.venv-acoustic/Scripts/python.exe').is_file():missing.append('Acoustic environment missing')
            if not yamnet_path():missing.append('Local YAMNet model cache missing; no implicit download')
        row['ready']=not missing
        row['unavailable_reason']='; '.join(missing) or None
        rows.append(row)
    return rows

def selected(identifier):
    return next((s for s in catalog() if s['id']==identifier),None)
