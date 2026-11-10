"""Isolated synthetic multi-target workflow. Never claims point-cloud person detection."""
from functools import lru_cache
import math
from uuid import UUID
from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field
from typing import Literal

def analyze(frames):
    """Compute transparent temporal rules from explicit synthetic identities/coordinates."""
    history={};output=[]
    for frame in frames:
        time=frame['time_sec'];tracks=[]
        for point in frame['tracks']:
            previous=history.setdefault(point['id'],[])
            velocity=0.0 if not previous else (point['x']-previous[-1]['x'])/(time-previous[-1]['time'])
            previous.append({**point,'time':time,'vx':velocity})
            recent=[p for p in previous if time-4<=p['time']<=time]
            signs=[1 if p['vx']>.25 else -1 for p in recent if abs(p['vx'])>.25]
            reversals=sum(a!=b for a,b in zip(signs,signs[1:]))
            low=[p for p in previous if time-.5<=p['time']<=time]
            upright=any(p['height']>=1.1 for p in previous if time-4<=p['time']<time)
            fall=upright and len(low)>=5 and all(p['height']<=.4 for p in low)
            tracks.append({**point,'vx':round(velocity,4),'reversals_4s':reversals,
                           'repeated_motion':reversals>=3,'possible_fall':fall})
        pairs=[]
        for i,a in enumerate(tracks):
            for b in tracks[i+1:]:
                distance=math.hypot(a['x']-b['x'],a['y']-b['y'])
                pairs.append({'ids':[a['id'],b['id']],'distance':round(distance,4),'close':distance<1.0})
        acoustic=10<=time<=13;sos=18<=time<=20
        anyfall=any(p['possible_fall'] for p in tracks)
        level='CRITICAL' if sos else 'HIGH' if anyfall and acoustic else 'OBSERVE' if anyfall or any(p['repeated_motion'] for p in tracks) else 'LOW'
        output.append({'time_sec':time,'source':'SIMULATION','tracks':tracks,'count':len(tracks),
                       'pairs':pairs,'acoustic_distress':acoustic,'sos_active':sos,'level':level})
    return output

@lru_cache(maxsize=1)
def dataset():
    frames=[]
    for i in range(241):
        time=round(i/10,1)
        frames.append({'time_sec':time,'tracks':[
            {'id':'SIM-1','x':round(-.8+.8*math.sin(math.pi*time),4) if time<8 else -.8,
             'y':0.0,'height':1.4 if time<8 else round(max(.3,1.4-(time-8)*1.1),4)},
            {'id':'SIM-2','x':.65,'y':.15,'height':1.4},
            {'id':'SIM-3','x':-2.0,'y':round(1.8+.2*math.sin(time/2),4),'height':1.4}]})
    return {'id':'isolated-radar-multitarget-v1','source':'SIMULATION','duration_sec':24,'sample_hz':10,
            'units':'synthetic meters, not measured','hardware_verified':False,'frames':analyze(frames),
            'rules':{'close_distance':1.0,'repeated_reversals':3,'motion_window_sec':4,
                     'fall':'Prior upright height >=1.1, then height <=0.4 sustained >=0.5s; synthetic demonstration only'},
            'note':'Scripted anonymous identities and coordinates. Not a radar detector, trained tracker, measured occupancy or hardware replay.'}

class RecordIn(BaseModel):
    model_config=ConfigDict(extra='forbid')
    session_id:UUID
    time_sec:float=Field(ge=0,le=24,allow_inf_nan=False)
    kind:Literal['radar','fusion','sos']

def install(app):
    @app.get('/testing/radar-simulation')
    def preview():return dataset()

    @app.post('/testing/radar-simulation/events')
    def record(body:RecordIn):
        from backend.main import EventIn,create_event,TOKEN
        frame=dataset()['frames'][min(240,int(body.time_sec*10+1e-6))]
        fall=any(t['possible_fall'] for t in frame['tracks'])
        motion=any(t['repeated_motion'] for t in frame['tracks'])
        if body.kind=='fusion' and not(fall and frame['acoustic_distress']):
            raise HTTPException(422,'This synthetic frame does not contain both fall and acoustic distress')
        group='radar-sim:'+str(body.session_id)
        types=[('sos','sos')] if body.kind=='sos' else [('fall' if fall else 'rapid_motion' if motion else 'presence','radar')]
        if body.kind=='fusion':types.append(('scream','acoustic'))
        result=None
        for kind,modality in types:
            result=create_event(EventIn(zone='ZONE_TOILET_BLINDSPOT',type=kind,source='simulation',sensor_modality=modality,
                processing_mode='simulation',source_type='SIMULATION',is_test=True,
                event_id=f'{group}:{kind}',analysis_run_id=group,score=None,model_version=None,
                evidence_reference=f'isolated-radar-multitarget-v1;SIMULATION ONLY;synthetic_offset={frame["time_sec"]};session={body.session_id}'),TOKEN)
        return {**result,'simulation_frame':frame,'note':'Explicit synthetic test only; no physical acquisition or emergency dispatch'}
