"""Authorized local research sources; demo zone assignment is not recording location."""
import json
import os
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
AIR='datasets/open_hidden/fighting/raw/AIRTLab/A-Dataset-for-Automatic-Violence-Detection-in-Videos-master/violence-detection-dataset/'
SCENARIOS=[
    dict(id='conflict',name='Physical conflict · AIRTLab',path=AIR+'violent/cam1/97.mp4',kind='fight',model='v3',zone_id='ZONE_CORRIDOR_A',dataset='AIRTLab',ground_truth='violent'),
    dict(id='normal',name='Normal activity · AIRTLab',path=AIR+'non-violent/cam1/1.mp4',kind='fight',model='v3',zone_id='ZONE_CANTEEN',dataset='AIRTLab',ground_truth='non-violent'),
    dict(id='fall',name='Possible fall · UR Fall',path='datasets/open_hidden/test_videos/fall-02-cam0-rgb.mp4',kind='fall',model='pose',zone_id='ZONE_STAIRCASE',dataset='UR Fall',ground_truth='fall'),
    dict(id='conflict_cam2',name='Physical conflict · AIRTLab camera 2',path=AIR+'violent/cam2/97.mp4',kind='fight',model='all',zone_id='ZONE_CORRIDOR_A',dataset='AIRTLab',ground_truth='violent'),
    dict(id='normal_cam2',name='Normal activity · AIRTLab camera 2',path=AIR+'non-violent/cam2/1.mp4',kind='fight',model='all',zone_id='ZONE_CANTEEN',dataset='AIRTLab',ground_truth='non-violent'),
    dict(id='fall_01',name='Fall sequence 01 · UR Fall',path='datasets/open_hidden/test_videos/fall-01-cam0-rgb.mp4',kind='fall',model='pose',zone_id='ZONE_STAIRCASE',dataset='UR Fall',ground_truth='fall'),
    dict(id='adl_01',name='Daily activity 01 · UR Fall',path='datasets/open_hidden/test_videos/adl-01-cam0-rgb.mp4',kind='fall',model='pose',zone_id='ZONE_STAIRCASE',dataset='UR Fall',ground_truth='normal_activity'),
    dict(id='adl_02',name='Daily activity 02 · UR Fall',path='datasets/open_hidden/test_videos/adl-02-cam0-rgb.mp4',kind='fall',model='pose',zone_id='ZONE_STAIRCASE',dataset='UR Fall',ground_truth='normal_activity'),
]

RAW_SENSOR_SCENARIOS=[
    dict(id='radar_raw_fall',name='Fresh radar fall analysis',path='datasets/private/radar/iwr6843/mmwave-radar-fall-detection-main/GatheredData/Fall/Areeb_back_1.csv',input_type='radar_recording',kind='radar',model='SVM_RBF',dataset='TI IWR6843 recorded point cloud',ground_truth='fall',reference_score=.99329),
    dict(id='radar_raw_normal',name='Fresh radar daily-activity analysis',path='datasets/private/radar/iwr6843/mmwave-radar-fall-detection-main/GatheredData/Not/Areeb_squat_4.csv',input_type='radar_recording',kind='radar',model='SVM_RBF',dataset='TI IWR6843 recorded point cloud',ground_truth='normal_activity',reference_score=.21750),
    dict(id='acoustic_scream',name='Fresh non-speech scream analysis',path='datasets/private/audio/fsd50k/extracted/FSD50K.eval_audio/355741.wav',input_type='audio_sample',kind='acoustic',model='YAMNet',dataset='FSD50K existing research audio',ground_truth='screaming',reference_score=.9465681314468384),
    dict(id='acoustic_background',name='Fresh acoustic negative control',path='datasets/private/audio/fsd50k/extracted/FSD50K.eval_audio/37199.wav',input_type='audio_sample',kind='acoustic',model='YAMNet',dataset='FSD50K existing research audio',ground_truth='not_screaming',reference_score=.0009683079551905394),
]

def raw_sensor_scenarios():
    return [{**s,'zone_id':'ZONE_TOILET_BLINDSPOT','available':(ROOT/s['path']).is_file(),
             'source_type':'RECORDED SENSOR DATA','processing_mode':'OFFLINE ANALYSIS','expected_evidence_type':'sensor_metadata',
             'limitations':('Fresh features from raw radar CSV; existing LOSO benchmark reconstructed excluding this subject. No tracked people, occupant counts, calibrated room positions or event timing.' if s['kind']=='radar' else 'Fresh cached YAMNet inference on existing non-speech research sample. Clip-level weak labels; no microphone, waveform export, speech transcription or private recording.')}
            for s in RAW_SENSOR_SCENARIOS]

def scenarios():
    video=[{**s,'input_type':'video','available':(ROOT/s['path']).is_file(),'source_type':'RECORDED REAL VIDEO',
             'processing_mode':'OFFLINE ANALYSIS','expected_evidence_type':'public_video',
             'limitations':'Research recording assigned to demo zone; not campus footage. Fight timing is clip-level; pose fall rule is experimental.'} for s in SCENARIOS]
    sensors=[]
    for identifier,name,path in [('radar','Private radar fall','evaluation/outputs/radar_route_a/radar_predictions.csv'),('acoustic','Private acoustic anomaly','evaluation/outputs/yamnet/yamnet_predictions.csv')]:
        sensors.append(dict(id=identifier,name=name,path=path,input_type='sensor_metadata',dataset='Saved evaluation model predictions',
                            model='SVM radar' if identifier=='radar' else 'YAMNet',zone_id='ZONE_TOILET_BLINDSPOT',ground_truth='See selected evaluation row',
                            available=(ROOT/path).is_file(),source_type='PRECOMPUTED ANALYSIS',processing_mode='recorded_sensor_replay',
                            expected_evidence_type='sensor_metadata',limitations='Saved real model output replay; no fresh sensor inference, coordinates or occupant counts. No audio/video.'))
    for identifier,name in [('sos','Private-zone test SOS'),('fusion','Controlled radar/acoustic fusion'),('telegram','Telegram TEST dispatch')]:
        sensors.append(dict(id=identifier,name=name,path=None,input_type='controlled_test',dataset='Explicit local simulation',model='SOS policy' if identifier!='fusion' else 'Transparent fusion rules',
                            zone_id='ZONE_TOILET_BLINDSPOT',ground_truth='Controlled test only',available=True,source_type='SIMULATION',processing_mode='simulation',
                            expected_evidence_type='sensor_metadata',limitations='No physical SOS switch or synchronized multi-sensor recording. Telegram sends only if TEST mode and authorized test recipient are configured.'))
    return video+raw_sensor_scenarios()+sensors

def cameras():
    rows=[dict(camera_id='CAM_CORRIDOR_A',zone_id='ZONE_CORRIDOR_A',camera_name='Corridor A',scenario_id='conflict'),
          dict(camera_id='CAM_CANTEEN',zone_id='ZONE_CANTEEN',camera_name='Canteen',scenario_id='normal'),
          dict(camera_id='CAM_STAIRCASE',zone_id='ZONE_STAIRCASE',camera_name='Staircase',scenario_id='fall'),
          dict(camera_id='CAM_ENTRANCE',zone_id='ZONE_ENTRANCE',camera_name='School Entrance',scenario_id='adl_01'),
          dict(camera_id='CAM_HALL',zone_id='ZONE_SCHOOL_HALL',camera_name='School Hall',scenario_id='adl_02')]
    # Explicit operator configuration only; never accept arbitrary URLs from API callers.
    config=os.getenv('SAFESENSE_CAMERA_REGISTRY')
    if config:
        rows=json.loads(Path(config).read_text(encoding='utf-8-sig'))
    from backend.main import ZONES
    output=[]
    for row in rows:
        if row.get('zone_id') not in ZONES or ZONES[row['zone_id']]['type']!='OPEN_HIDDEN':
            continue
        scenario=next((s for s in scenarios() if s['id']==row.get('scenario_id') and s['input_type']=='video'),None)
        live=bool(row.get('stream_url')) and row.get('authorized') is True
        output.append({**row,'stream_configured':live,'zone_type':'OPEN_HIDDEN','source_type':'LIVE CAMERA' if live else 'RECORDED REAL VIDEO',
                       'available':live or bool(scenario and scenario['available']), 'enabled_models':['v2','v3','pose'],
                       'fight_model':row.get('fight_model') or os.getenv('SAFESENSE_FIGHT_BASELINE','v3'),
                       'playback_status':'ready' if live or scenario and scenario['available'] else 'not_configured',
                       'detection_status':'idle','scenario':None if live else scenario})
    return output

def public_cameras():
    allowed={'camera_id','camera_name','aliases','zone_id','zone_type','source_type','available','enabled_models','playback_status','detection_status','scenario','scenario_id','stream_configured','fight_model'}
    return [{k:v for k,v in row.items() if k in allowed} for row in cameras()]

def source(scenario_id):
    row=next((s for s in scenarios() if s['id']==scenario_id),None)
    if not row or not row['available'] or row['input_type']!='video':
        from fastapi import HTTPException
        raise HTTPException(404,'Registered recording unavailable')
    return row, ROOT/row['path']


def canonical_camera_id(value):
    """Resolve only unambiguous IDs/names/explicit aliases from the shared registry."""
    import re
    def key(item):return re.sub(r'[\s-]+','_',item.strip().lower()) if isinstance(item,str) else ''
    wanted=key(value)
    if not wanted:return None
    ids={row['camera_id'] for row in cameras() if any(key(alias)==wanted for alias in [row['camera_id'],row.get('camera_name'),*row.get('aliases',[])])}
    return next(iter(ids)) if len(ids)==1 else None
