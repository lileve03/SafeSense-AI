"""Execute actual extracted reference functions with local weights, isolated database and RAM-only PCM."""
from pathlib import Path
import sys, importlib.util, io, wave, json, hashlib
ROOT=Path(sys.argv[1]);sys.path.insert(0,str(ROOT))
import numpy as np
import tensorflow_hub as hub
import tensorflow as tf
from backend.scenario_catalog import yamnet_path
from backend.registry import raw_sensor_scenarios
from ai_models.acoustic.evaluate_fsd50k import load_audio
local=yamnet_path();assert local
original_load=hub.load
hub.load=lambda url:original_load(str(local))
spec=importlib.util.spec_from_file_location('actual_phase2_reference',Path(sys.argv[2]))
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
source=next(s for s in raw_sensor_scenarios() if s['id']=='acoustic_scream');path=ROOT/source['path']
waveform=load_audio(path,tf).numpy();buffer=io.BytesIO()
with wave.open(buffer,'wb') as w:
 w.setnchannels(1);w.setsampwidth(2);w.setframerate(16000)
 w.writeframes(np.asarray(np.clip(waveform,-1,1)*32767,dtype='<i2').tobytes())
result=module.infer_audio(buffer.getvalue(),.5);assert result['detected'] and result['scores']
peaks=module.audio_peak_events(result);assert peaks
fall=module.add_event('fall','HIGH','synthetic_radar_replay',4.9,3)
module.ACOUSTIC['results']=result
module.FUSION.update(armed=True,audio_offset=4.9-peaks[0],window=.25)
module.try_fuse();module.try_fuse()
with module.conn() as db:
 row=dict(db.execute('SELECT * FROM incidents WHERE id=?',(fall,)).fetchone())
 links=[dict(r) for r in db.execute('SELECT * FROM fusion_links')]
assert row['event_type']=='fused_fall_screaming' and len(links)==1
output={'model':result['model'],'actual_reference_score':result['max_score'],'score_windows':len(result['scores']),
 'threshold_windows':len(peaks),'raw_file_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
 'input_conversion':'existing 16kHz preprocessing, RAM-only PCM16 for strict reference WAV API',
 'local_weights_only':True,'fusion_link_count':len(links),'fusion_note':links[0]['note'],'hardware_joint_incident':False}
Path(sys.argv[3]).write_text(json.dumps(output,indent=2),encoding='utf-8')
