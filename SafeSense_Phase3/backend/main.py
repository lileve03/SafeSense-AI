"""SafeSense AI Phase 3: zone-aware simulation-first safety risk engine.

Proof of concept ONLY: no authentication, persistent database, or real dispatch.
Incoming source labels are self-reported and NOT proof of actual sensor ingestion.
"""
from collections import deque
from datetime import datetime, timezone
from threading import RLock
from typing import Literal
from uuid import uuid4
import time

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

EventType = Literal['presence', 'normal_motion', 'rapid_motion', 'fall', 'scream', 'impact', 'sos']
EventSource = Literal['simulation', 'yamnet', 'radar', 'vision', 'sos_button']
ZoneType = Literal['PRIVATE', 'OPEN_HIDDEN']

class EventIn(BaseModel):
    zone: str = Field(min_length=1, max_length=80)
    type: EventType
    confidence: float = Field(default=1.0, ge=0, le=1)
    source: EventSource = 'simulation'

class AckIn(BaseModel):
    staff: str = Field(min_length=1, max_length=80)

# Each area is explicitly registered. A private zone never permits vision input.
ZONES = {
    'ZONE_TOILET_BLINDSPOT': {'name': 'Toilet / Privacy Blind Spot', 'type': 'PRIVATE',
                              'allowed_sources': ('simulation', 'radar', 'yamnet', 'sos_button')},
    'ZONE_CORRIDOR_A': {'name': 'Corridor A', 'type': 'OPEN_HIDDEN',
                        'allowed_sources': ('simulation', 'vision', 'yamnet', 'radar', 'sos_button')},
    'ZONE_STAIRCASE': {'name': 'Staircase', 'type': 'OPEN_HIDDEN',
                       'allowed_sources': ('simulation', 'vision', 'yamnet', 'radar', 'sos_button')},
    'ZONE_CANTEEN': {'name': 'Canteen', 'type': 'OPEN_HIDDEN',
                     'allowed_sources': ('simulation', 'vision', 'yamnet', 'radar', 'sos_button')},
    'ZONE_ENTRANCE': {'name': 'Main Entrance', 'type': 'OPEN_HIDDEN',
                      'allowed_sources': ('simulation', 'vision', 'yamnet', 'radar', 'sos_button')},
}
ZONE_ALIASES = {
    'Demo-Private-A': 'ZONE_TOILET_BLINDSPOT',
    'Toilet Block B': 'ZONE_TOILET_BLINDSPOT',
    'Toilet Entrance': 'ZONE_TOILET_BLINDSPOT',
    'Corridor A': 'ZONE_CORRIDOR_A',
    'Staircase': 'ZONE_STAIRCASE',
    'Canteen': 'ZONE_CANTEEN',
    'Main Entrance': 'ZONE_ENTRANCE',
    'School Entrance': 'ZONE_ENTRANCE',
}

app = FastAPI(title='SafeSense AI Zone-Aware Prototype', version='2.0.0')
app.add_middleware(
    CORSMiddleware,
    allow_origins=['http://localhost:3000', 'http://127.0.0.1:3000',
                   'http://localhost:3001', 'http://127.0.0.1:3001',
                   'http://localhost:5173', 'http://127.0.0.1:5173'],
    allow_credentials=False,
    allow_methods=['GET', 'POST'],
    allow_headers=['Content-Type'],
)

_lock = RLock()
_events = deque(maxlen=500)
_incidents = []
FUSION_WINDOW_SECONDS = 5.0
MIN_CONF = 0.5


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def canonical_zone(zone):
    zone_id = ZONE_ALIASES.get(zone, zone)
    if zone_id not in ZONES:
        raise HTTPException(status_code=422, detail=f'Unknown zone: {zone}')
    return zone_id


def public_event(event):
    return {k: v for k, v in event.items() if k != '_monotonic'}


def assess(zone_id, event_type, recent):
    """Risk rules are transparent and intentionally conservative.

    HIGH requires corroboration by distinct event types, not merely rapid motion.
    This is NOT a validated classifier of violence or bullying.
    """
    if event_type == 'sos':
        return 'CRITICAL', 'SOS activated (prototype test; no emergency dispatch)'
    types = {x['type'] for x in recent}
    if ZONES[zone_id]['type'] == 'PRIVATE':
        if 'fall' in types and ('scream' in types or 'impact' in types):
            return 'HIGH', 'Private-area fall corroborated by acoustic event'
        if types.intersection({'fall', 'scream', 'impact', 'rapid_motion'}):
            return 'OBSERVE', 'Private-area single unverified safety signal'
        return 'LOW', 'No corroborated private-area safety signal'
    # Open-but-low-visibility public areas: vision/temporal signals, plus corroboration.
    if 'fall' in types and ('impact' in types or 'scream' in types):
        return 'HIGH', 'Open-area possible fall corroborated by acoustic event'
    if 'rapid_motion' in types and ('impact' in types or 'scream' in types):
        return 'HIGH', 'Open-area rapid motion corroborated by acoustic event; verify manually'
    if types.intersection({'rapid_motion', 'fall', 'scream', 'impact'}):
        return 'OBSERVE', 'Open-area unverified safety signal; requires verification'
    return 'LOW', 'No corroborated open-area safety signal'


@app.get('/health')
def health():
    return {'status': 'online', 'mode': 'SIMULATION_FIRST', 'time': utc_now(),
            'version': '2.0.0', 'note': 'Prototype only; no real emergency dispatch'}


@app.get('/zones')
def zones():
    return [{'id': zone_id, 'name': v['name'], 'zone_type': v['type'],
             'allowed_sources': list(v['allowed_sources'])} for zone_id, v in ZONES.items()]


@app.get('/state')
def state():
    with _lock:
        return {'mode': 'SIMULATION_FIRST', 'updated_at': utc_now(),
                'events': [public_event(e) for e in list(_events)[-40:]][::-1],
                'incidents': [dict(i) for i in _incidents[-30:]][::-1]}


@app.post('/event')
def create_event(event: EventIn):
    zone_id = canonical_zone(event.zone)
    cfg = ZONES[zone_id]
    if event.source not in cfg['allowed_sources']:
        raise HTTPException(status_code=422, detail=f'{event.source} source is prohibited in {cfg["type"]} area')
    if event.type == 'sos' and event.source not in ('simulation', 'sos_button'):
        raise HTTPException(status_code=422, detail='SOS must originate from simulation or sos_button')
    if event.source == 'vision' and event.type in ('scream', 'impact'):
        raise HTTPException(status_code=422, detail='Vision source cannot report an acoustic event')
    if event.source == 'yamnet' and event.type not in ('scream', 'impact'):
        raise HTTPException(status_code=422, detail='YAMNet source supports only acoustic event types in this prototype')
    if event.source == 'radar' and event.type in ('scream', 'impact'):
        raise HTTPException(status_code=422, detail='Radar cannot report an acoustic event')

    now = time.monotonic()
    with _lock:
        row = {**event.model_dump(), 'id': str(uuid4()), 'zone_id': zone_id,
               'zone_type': cfg['type'], 'timestamp': utc_now(), '_monotonic': now}
        _events.append(row)
        recent = [e for e in _events if e['zone_id'] == zone_id
                  and e['_monotonic'] >= now - FUSION_WINDOW_SECONDS and e['confidence'] >= MIN_CONF]
        if event.confidence < MIN_CONF:
            level, reason = 'LOW', 'Low-confidence observation; not used for escalation'
        else:
            level, reason = assess(zone_id, event.type, recent)
        row.update(level=level, reason=reason)
        incident = None
        if level in ('HIGH', 'CRITICAL'):
            incident = {'id': str(uuid4()), 'zone': event.zone, 'zone_id': zone_id,
                        'zone_type': cfg['type'], 'level': level, 'reason': reason,
                        'created_at': utc_now(), 'status': 'NEW', 'staff': None,
                        'source': event.source, 'is_test': True}
            _incidents.append(incident)
        return {'event': public_event(row), 'incident': dict(incident) if incident else None}


@app.post('/incidents/{incident_id}/ack')
def acknowledge(incident_id: str, ack: AckIn):
    with _lock:
        for i in _incidents:
            if i['id'] == incident_id:
                i.update(status='ACKNOWLEDGED', staff=ack.staff, acknowledged_at=utc_now())
                return dict(i)
    raise HTTPException(status_code=404, detail='Incident not found')


@app.post('/reset')
def reset():
    with _lock:
        _events.clear()
        _incidents.clear()
    return {'status': 'reset', 'mode': 'SIMULATION_FIRST'}
