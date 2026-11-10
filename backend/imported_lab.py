"""Read-only, validated synthetic archive data. No inference, clock or incident writes."""
from functools import lru_cache
from pathlib import Path
import hashlib
import json
import math
from fastapi import HTTPException

DATA=Path(__file__).resolve().parent/'data/imported_phase2'

def number(value):
    return isinstance(value,(int,float)) and not isinstance(value,bool) and math.isfinite(value)

def validate(frames,events):
    if not isinstance(frames,list) or not 2<=len(frames)<=1000:raise ValueError('Invalid frame count')
    previous=-1
    for frame in frames:
        timestamp=frame.get('time')
        if not number(timestamp) or not previous<timestamp<=120:raise ValueError('Invalid replay timestamp')
        previous=timestamp
        tracks=frame.get('tracks');ids=set()
        if not isinstance(tracks,list) or len(tracks)>16:raise ValueError('Invalid synthetic tracks')
        for track in tracks:
            identifier=track.get('id')
            if type(identifier) is not int or identifier<1 or identifier in ids:raise ValueError('Invalid track identity')
            ids.add(identifier)
            for key,maximum in [('x',8),('z',6),('height',3)]:
                if not number(track.get(key)) or not 0<=track[key]<=maximum:raise ValueError('Track outside synthetic room')
    if frames[0]['time']!=0:raise ValueError('Replay must start at zero')
    if not isinstance(events,list) or len(events)>100:raise ValueError('Invalid annotation list')
    for event in events:
        if not number(event.get('time')) or not 0<=event['time']<=previous or event.get('verified') is not False:raise ValueError('Invalid synthetic annotation')
        if event.get('type')!='SUSPECTED FALL' or type(event.get('person_id')) is not int:raise ValueError('Unsupported archive annotation')
        frame=max((f for f in frames if f['time']<=event['time']),key=lambda f:f['time'])
        if event['person_id'] not in [t['id'] for t in frame['tracks']]:raise ValueError('Annotation has no corresponding synthetic track')

@lru_cache(maxsize=1)
def dataset():
    provenance=json.loads((DATA/'provenance.json').read_text(encoding='utf-8'))
    raw=(DATA/'test_twin.json').read_bytes();annotations=(DATA/'test_events.json').read_bytes()
    if hashlib.sha256(raw).hexdigest()!=provenance['frame_sha256'] or hashlib.sha256(annotations).hexdigest()!=provenance['event_sha256']:raise ValueError('Imported archive data checksum mismatch')
    frames=json.loads(raw);events=json.loads(annotations);validate(frames,events)
    return {'id':'phase2-synthetic-lab','duration_sec':frames[-1]['time'],'frames':frames,'annotations':events,
            'room':{'width':8,'depth':6,'units':'synthetic layout units, not measured meters'},'provenance':provenance}

def install(app):
    # Existing main-app middleware authenticates this /testing read, like other labs.
    @app.get('/testing/imported-lab')
    def imported_replay():
        try:return dataset()
        except (OSError,ValueError,KeyError,TypeError) as error:raise HTTPException(503,'Imported synthetic replay is unavailable or failed validation') from error
