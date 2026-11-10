"""SafeSense AI Phase 3: zone-aware simulation-first safety risk engine.

Local proof of concept: SQLite persistence and opt-in test notifications; no production identity provider or emergency dispatch.
Incoming source labels are self-reported and NOT proof of actual sensor ingestion.
"""
from collections import deque
from datetime import datetime, timezone
from threading import RLock
from typing import Literal
from uuid import uuid4, UUID
import math
import hashlib
import time
import os
import csv
import json
from pathlib import Path
import secrets

from fastapi import FastAPI, HTTPException, Header, Request
from fastapi.responses import JSONResponse, FileResponse
from scripts.start_services import load_local_environment
# Direct uvicorn startup must load the same backend-only configuration as the launcher.
load_local_environment()
from backend import storage, registry, notifications
from backend.overview_insights import unique_overview_incidents
from concurrent.futures import ThreadPoolExecutor
from threading import BoundedSemaphore
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, AwareDatetime

EventType = Literal['presence', 'normal_motion', 'normal_acoustic', 'rapid_motion', 'fall', 'scream', 'impact', 'sos', 'possible_conflict']
EventSource = Literal['simulation', 'yamnet', 'radar', 'vision', 'sos_button']
ZoneType = Literal['PRIVATE', 'OPEN_HIDDEN']

class EventIn(BaseModel):
    zone: str = Field(min_length=1, max_length=80)
    type: EventType
    confidence: float = Field(default=1.0, ge=0, le=1)
    source: EventSource = 'simulation'
    sensor_modality: Literal['radar', 'acoustic', 'vision', 'sos'] | None = None
    processing_mode: Literal['real_model', 'recorded_sensor_replay', 'simulation'] = 'simulation'
    event_id: str | None = Field(default=None, max_length=100)
    score: float | None = Field(default=None, ge=0, le=1)
    model_version: str | None = Field(default=None, max_length=100)
    evidence_reference: str | None = Field(default=None, max_length=500)
    evidence_media: list[dict] = Field(default_factory=list, max_length=8)
    camera_id: str | None = Field(default=None, max_length=80)
    is_test: bool = True
    source_type: Literal['LIVE CAMERA','LIVE SENSOR','LIVE SOS','RECORDED REAL VIDEO','RECORDED SENSOR REPLAY','SENSOR METADATA','SIMULATION'] | None = None
    analysis_run_id: str | None = Field(default=None,max_length=100)
    observed_at: AwareDatetime | None = None

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
ZONES['ZONE_SCHOOL_HALL'] = {'name':'School Hall','type':'OPEN_HIDDEN','allowed_sources':('simulation','vision','yamnet','radar','sos_button')}
ZONE_ALIASES = {
    'School Hall': 'ZONE_SCHOOL_HALL', 'ZONE_HALL': 'ZONE_SCHOOL_HALL',
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
    allow_headers=['Content-Type', 'X-SafeSense-Token'],
)

_lock = RLock()
_events = deque(maxlen=500)
_incidents = []
FUSION_WINDOW_SECONDS = max(0.1, float(os.getenv('SAFESENSE_FUSION_WINDOW_SECONDS', '5')))
MIN_CONF = min(1.0,max(0.0,float(os.getenv('SAFESENSE_MIN_CONF', '0.5'))))
TOKEN = os.getenv('SAFESENSE_API_TOKEN', 'local-demo-only')
INGEST_TOKEN = os.getenv('SAFESENSE_INGEST_TOKEN','')
COOLDOWN_SECONDS = float(os.getenv('SAFESENSE_COOLDOWN_SECONDS', '15'))
ROOT = Path(__file__).resolve().parent.parent
_notify_pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix='staff-notifications')
_notify_slots = BoundedSemaphore(8)
for _row in storage.all_rows('event')[-500:]:
    _events.append({**_row, '_monotonic': float('-inf')})
for _row in storage.all_rows('incident'):
    _incidents.append({**_row, '_monotonic': float('-inf')})

def persist():
    storage.snapshot(_events, _incidents)

def record_notification_result(incident_id,result):
    with _lock:
        current=next((i for i in _incidents if i['id']==incident_id),None)
        if not current:return
        current['notification_status']=result['status']
        current['notification_state']=notifications.delivery_state(result)
        if result.get('assigned_staff'):current['assigned_staff']=result['assigned_staff']
        if not any(h.get('notification_id')==result['id'] and h.get('status')=='NOTIFICATION_'+result['status'] and h.get('delivery_state',notifications.delivery_state({'status':result['status']}))==notifications.delivery_state(result) for h in current['history']):
            current['history'].append({'timestamp':result['timestamp'],'status':'NOTIFICATION_'+result['status'],'delivery_state':notifications.delivery_state(result),
                'notification_id':result['id'],'note':f"{result['mode']} / {result.get('assigned_staff') or 'unassigned'}"})
        persist()

def queue_notification(incident):
    incident['notification_state']='PENDING'
    incident['notification_status']='PENDING'
    persist()
    request={'id':str(uuid4()),'incident_id':incident['id'],'status':'QUEUED','timestamp':utc_now()}
    storage.put('notification_request',request['id'],request)
    if not _notify_slots.acquire(blocking=False):
        request.update(status='QUEUE_FULL')
        incident.update(notification_state='FAILED',notification_status='QUEUE_FULL')
        persist()
        storage.put('notification_request',request['id'],request)
        return
    def send():
        try:
            with _lock:
                current=next((i for i in _incidents if i['id']==request['incident_id']),None)
                copied=json.loads(json.dumps(public_event(current))) if current else None
            if copied:
                result=notifications.dispatch(copied)
                record_notification_result(request['incident_id'],result)
                request.update(status='DONE',notification_id=result['id'])
            else:request.update(status='CANCELLED')
        except Exception as exc:
            request.update(status='FAILED',error=type(exc).__name__)
            with _lock:
                current=next((i for i in _incidents if i['id']==request['incident_id']),None)
                if current:
                    current.update(notification_state='FAILED',notification_status='FAILED')
                    persist()
        finally:
            try:storage.put('notification_request',request['id'],request)
            finally:_notify_slots.release()
    _notify_pool.submit(send)

@app.on_event('startup')
def recover_notifications():
    # Only resume durable work not yet attempted. SENDING/unknown deliveries are never retried.
    for request in storage.all_rows('notification_request'):
        if request['status']=='QUEUED':
            request['status']='RECOVERED'
            storage.put('notification_request',request['id'],request)
            incident=next((i for i in _incidents if i['id']==request['incident_id'] and i['status'] not in ('RESOLVED','FALSE_ALARM')),None)
            if incident:queue_notification(incident)

@app.middleware('http')
async def local_access(request: Request, call_next):
    # Protect sensitive reads and every mutation. Query tokens only for media elements.
    public = request.url.path in ('/health','/zones','/analytics/evaluations')
    media = request.url.path.startswith('/monitoring/sources/')
    token = request.headers.get('X-SafeSense-Token') or (request.query_params.get('token') if media else None)
    if request.method != 'OPTIONS' and not public and not valid_token(token):
        return JSONResponse({'detail':'Local staff access token required'},status_code=401)
    response = await call_next(request)
    response.headers['Cache-Control']='no-store'
    response.headers['Referrer-Policy']='no-referrer'
    return response


def valid_token(token):
    return bool(token) and secrets.compare_digest(token, TOKEN)


def independent(recent, left, right):
    def sensor(e):
        # Simulation can model distinct virtual modalities only when explicitly labeled.
        return e.get('sensor_modality') if e['source'] == 'simulation' else 'acoustic' if e['source']=='yamnet' else e['source']
    def compatible_time(a,b):
        if a.get('observed_at') and b.get('observed_at'):
            return abs((datetime.fromisoformat(a['observed_at'].replace('Z','+00:00'))-datetime.fromisoformat(b['observed_at'].replace('Z','+00:00'))).total_seconds())<=FUSION_WINDOW_SECONDS
        return True
    return any(a['type'] == left and b['type'] in right and sensor(a) and sensor(b)
               and sensor(a) in ('radar','vision') and sensor(b)=='acoustic'
               and compatible_time(a,b) for a in recent for b in recent)


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
        return 'CRITICAL', 'SOS help request — staff response required; no emergency-services dispatch'
    if event_type == 'possible_conflict':
        return 'OBSERVE', 'Possible Physical Conflict - Pending Review; whole-video model candidate only'
    types = {x['type'] for x in recent}
    if ZONES[zone_id]['type'] == 'PRIVATE':
        if independent(recent, 'fall', {'scream', 'impact'}):
            return 'HIGH', 'Private-area fall corroborated by acoustic event'
        if types.intersection({'fall', 'scream', 'impact', 'rapid_motion'}):
            return 'OBSERVE', 'Private-area single unverified safety signal'
        return 'LOW', 'No corroborated private-area safety signal'
    # Open-but-low-visibility public areas: vision/temporal signals, plus corroboration.
    if independent(recent, 'fall', {'impact','scream'}):
        return 'HIGH', 'Open-area possible fall corroborated by acoustic event'
    if independent(recent, 'rapid_motion', {'scream', 'impact'}):
        return 'HIGH', 'Open-area rapid motion corroborated by acoustic event; verify manually'
    if types.intersection({'rapid_motion', 'fall', 'scream', 'impact'}):
        return 'OBSERVE', 'Open-area unverified safety signal; requires verification'
    return 'LOW', 'No corroborated open-area safety signal'


@app.get('/health')
def health():
    return {'status': 'online', 'mode': 'EXPLICIT_PROCESSING_MODES', 'time': utc_now(),
            'version': '2.0.0', 'note': 'Prototype only; no real emergency dispatch'}


def zone_status(zone_id):
    with _lock:
        active = [i for i in _incidents if i['zone_id'] == zone_id and i['status'] not in ('RESOLVED', 'FALSE_ALARM')]
        order = ['LOW','OBSERVE','WARNING','HIGH','CRITICAL']
        level = max((i['level'] for i in active), key=order.index, default='LOW')
        last = next((e for e in reversed(_events) if e['zone_id'] == zone_id), None)
        return {'level':level, 'active_incident_ids':[i['id'] for i in active],
                'last_event_timestamp':last['timestamp'] if last else None,
                'hardware_status':'unavailable'}


@app.get('/settings')
def settings_snapshot():
    """Authenticated read-only runtime configuration; no model or policy mutation."""
    return {'fusion_window_seconds': FUSION_WINDOW_SECONDS,
            'cooldown_seconds': COOLDOWN_SECONDS, 'minimum_event_confidence': MIN_CONF,
            'private_zone_vision_allowed': False, 'sos_policy': 'CRITICAL'}


@app.get('/zones')
def zones():
    return [{'id': zone_id, 'name': v['name'], 'zone_type': v['type'],
             'allowed_sources': list(v['allowed_sources']), **zone_status(zone_id)} for zone_id, v in ZONES.items()]


@app.get('/state')
def state():
    with _lock:
        return {'mode': 'EXPLICIT_PROCESSING_MODES', 'updated_at': utc_now(),
                'events': [public_event(e) for e in list(_events)[-40:]][::-1],
                'incidents': [public_event(i) for i in _incidents][::-1]}


@app.post('/event')
def create_event(event: EventIn, x_safesense_token: str | None = Header(None), x_safesense_ingest_token: str | None = Header(None)):
    zone_id = canonical_zone(event.zone)
    cfg = ZONES[zone_id]
    if cfg['type']=='PRIVATE' and event.source_type in ('LIVE CAMERA','RECORDED REAL VIDEO'):
        raise HTTPException(403,'Private zones prohibit camera provenance and video')
    if cfg['type'] == 'PRIVATE' and event.evidence_media:
        raise HTTPException(403, 'Private zones accept sensor metadata only; video/image evidence prohibited')
    for media in event.evidence_media:
        try:
            identifier=media['id']
            valid=str(UUID(identifier))==identifier and media['url']=='/monitoring/evidence/'+identifier and media['zone_id']==zone_id
            valid=valid and isinstance(media['model_version'],str)
            for key in ('start_sec','end_sec','duration_sec'):
                valid=valid and isinstance(media[key],(int,float)) and math.isfinite(media[key]) and media[key]>=0
            valid=valid and media['end_sec']>=media['start_sec']
            if not valid:raise ValueError()
        except (KeyError,ValueError,TypeError,AttributeError):
            raise HTTPException(422,'Evidence must reference a valid retained clip in the same zone')
    if cfg['type'] == 'PRIVATE' and event.sensor_modality == 'vision':
        raise HTTPException(422, 'Vision modality is prohibited in PRIVATE areas, including simulation')
    if event.source not in cfg['allowed_sources']:
        raise HTTPException(status_code=422, detail=f'{event.source} source is prohibited in {cfg["type"]} area')
    if event.type == 'sos' and event.source not in ('simulation', 'sos_button'):
        raise HTTPException(status_code=422, detail='SOS must originate from simulation or sos_button')
    if event.source == 'vision' and event.type in ('scream', 'impact','normal_acoustic'):
        raise HTTPException(status_code=422, detail='Vision source cannot report an acoustic event')
    if event.source == 'yamnet' and event.type not in ('scream', 'impact','normal_acoustic'):
        raise HTTPException(status_code=422, detail='YAMNet source supports only acoustic event types in this prototype')
    if event.source == 'radar' and event.type in ('scream', 'impact','normal_acoustic'):
        raise HTTPException(status_code=422, detail='Radar cannot report an acoustic event')

    if event.processing_mode == 'real_model' and not valid_token(x_safesense_token):
        raise HTTPException(401, 'Trusted inference token required for real-model events')
    if event.type == 'possible_conflict' and event.source != 'vision':
        raise HTTPException(422, 'Physical conflict candidate must originate from vision')
    if event.processing_mode == 'real_model' and event.source == 'simulation':
        raise HTTPException(422, 'Simulation cannot be labeled real_model')
    if event.processing_mode == 'recorded_sensor_replay' and not valid_token(x_safesense_token):
        raise HTTPException(401, 'Replay must use the recorded replay API')
    test_event=event.is_test or event.processing_mode!='real_model' or event.source_type not in ('LIVE CAMERA','LIVE SENSOR','LIVE SOS')
    if not test_event and (not INGEST_TOKEN or not isinstance(x_safesense_ingest_token,str) or not secrets.compare_digest(x_safesense_ingest_token,INGEST_TOKEN)):
        raise HTTPException(403,'Verified live-source ingestion credential required; dashboard credentials cannot authorize staff delivery')
    now = time.monotonic()
    # Explicit connected-demo runs are idempotent across retries, cooldown expiry
    # and restarts. This changes aggregation only, never the fusion time window.
    connected_demo = (cfg['type']=='PRIVATE' and test_event and event.source=='simulation'
                      and event.processing_mode=='simulation' and event.source_type=='SIMULATION'
                      and bool(event.analysis_run_id) and event.analysis_run_id.startswith('private-demo:'))
    with _lock:
        if event.event_id:
            previous = next((e for e in _events if e['id'] == event.event_id), None) or storage.get('event', event.event_id)
            if previous:
                incident = next((i for i in _incidents if event.event_id in i.get('event_ids', [])), None)
                return {'event': public_event(previous), 'incident': public_event(incident) if incident else None, 'deduplicated': True}
        if connected_demo and any(i.get('analysis_run_id')==event.analysis_run_id and i['zone_id']==zone_id
                                  and i['status'] in ('RESOLVED','FALSE_ALARM') for i in _incidents):
            raise HTTPException(409,'This test run is closed; retry existing event IDs or start an explicit new test run')
        row = {**event.model_dump(mode='json'), 'id': event.event_id or str(uuid4()), 'zone_id': zone_id,
               'zone_type': cfg['type'], 'timestamp': utc_now(), '_monotonic': now,'is_test':test_event}
        _events.append(row)
        capture_current=event.observed_at is None or -5 <= (datetime.now(timezone.utc)-event.observed_at).total_seconds() <= 10
        recent = [e for e in _events if e['zone_id'] == zone_id
                  and e['_monotonic'] >= now - FUSION_WINDOW_SECONDS and e['confidence'] >= MIN_CONF
                  and e['processing_mode'] == event.processing_mode
                  and e.get('source_type') == event.source_type
                  and bool(e.get('observed_at')) == bool(event.observed_at)
                  and (not e.get('observed_at') or -5 <= (datetime.now(timezone.utc)-datetime.fromisoformat(e['observed_at'].replace('Z','+00:00'))).total_seconds() <= 10)
                  and (event.observed_at is None or abs((datetime.fromisoformat(e['observed_at'].replace('Z','+00:00'))-event.observed_at).total_seconds()) <= FUSION_WINDOW_SECONDS)
                  and e.get('is_test',True)==test_event
                  and e.get('analysis_run_id')==event.analysis_run_id
                  and (event.processing_mode != 'recorded_sensor_replay' or e['id'] == row['id'])]
        if event.type in ('sos', 'possible_conflict'):
            level, reason = assess(zone_id, event.type, recent)
        elif not capture_current:
            level, reason = 'LOW', 'Observation outside current capture window; not used for escalation'
        elif event.confidence < MIN_CONF:
            level, reason = 'LOW', 'Low-confidence observation; not used for escalation'
        else:
            level, reason = assess(zone_id, event.type, recent)
        row.update(level=level, severity=level, reason=reason, event_type=event.type, event_id=row['id'],
                   review_status='pending_human_review' if level != 'LOW' else 'not_flagged')
        incident = None
        if level != 'LOW':
            evidence = [e['id'] for e in recent]
            if row['id'] not in evidence:
                evidence.append(row['id'])
            # Coalesce overlapping observations, preserving reasons and evidence.
            incident = next((i for i in reversed(_incidents) if i['zone_id'] == zone_id
                             and i['status'] in ('NEW', 'ACKNOWLEDGED', 'DISPATCHED', 'VERIFIED')
                             and i['processing_mode'] == event.processing_mode
                             and i.get('source_type') == event.source_type
                             and i.get('is_test',True)==test_event
                             and i.get('analysis_run_id')==event.analysis_run_id
                             and event.processing_mode != 'recorded_sensor_replay'
                             and (now-i['_monotonic'] <= COOLDOWN_SECONDS or connected_demo)
                             and (i['level'] == 'CRITICAL') == (level == 'CRITICAL')), None)
            if incident:
                incident['event_ids'] = list(dict.fromkeys(incident['event_ids'] + evidence))
                if connected_demo:
                    retained={e['id']:e for e in incident.get('evidence',[])}
                    retained.update({e['id']:public_event(e) for e in _events if e['id'] in incident['event_ids']})
                    incident['evidence']=[retained[identifier] for identifier in incident['event_ids'] if identifier in retained]
                else:
                    incident['evidence'] = [public_event(e) for e in _events if e['id'] in incident['event_ids']]
                if ['LOW','OBSERVE','WARNING','HIGH','CRITICAL'].index(level) > ['LOW','OBSERVE','WARNING','HIGH','CRITICAL'].index(incident['level']):
                    incident.update(level=level, reason=reason)
                incident['updated_at'] = utc_now()
            else:
                incident = {'id': str(uuid4()), 'zone': event.zone, 'zone_id': zone_id,
                            'zone_type': cfg['type'], 'level': level, 'reason': reason,
                            'created_at': utc_now(), 'status': 'NEW', 'staff': None,
                            'source': event.source, 'processing_mode': event.processing_mode,
                            'model_version': event.model_version, 'score': event.score,
                            'is_test':test_event,
                            'source_type':event.source_type,
                            'analysis_run_id':event.analysis_run_id,
                            'review_status': 'pending_human_review',
                            'event_ids': evidence, 'evidence': [public_event(e) for e in _events if e['id'] in evidence],
                            'history': [{'timestamp': utc_now(), 'status': 'NEW', 'note': reason}],
                            '_monotonic': now}
                _incidents.append(incident)
                route = notifications.select_route(incident)
                incident['assigned_staff'] = route.get('staff') if route else None
        persist()
        if incident:
            queue_notification(incident)
        return {'event': public_event(row), 'incident': public_event(incident) if incident else None}


@app.post('/incidents/{incident_id}/ack')
def acknowledge(incident_id: str, ack: AckIn):
    with _lock:
        for i in _incidents:
            if i['id'] == incident_id:
                if i['status'] in ('RESOLVED','FALSE_ALARM'):
                    raise HTTPException(409,'Closed incidents cannot be acknowledged')
                if not ack.staff.strip():raise HTTPException(422,'Staff name required')
                if i.get('acknowledged_at'):return public_event(i)
                i.update(status='ACKNOWLEDGED', staff=ack.staff, acknowledged_by=ack.staff, acknowledged_at=utc_now(), review_status='under_review')
                i['history'].append({'timestamp': utc_now(), 'status': 'ACKNOWLEDGED', 'note': ack.staff})
                persist()
                return public_event(i)
    raise HTTPException(status_code=404, detail='Incident not found')


@app.post('/reset')
def reset():
    with _lock:
        _events.clear()
        _incidents.clear()
        storage.clear_demo()
    return {'status': 'reset', 'mode': 'EXPLICIT_PROCESSING_MODES'}


@app.get('/incidents')
def incidents():
    with _lock:
        return [public_event(i) for i in reversed(_incidents)]


class ReviewIn(BaseModel):
    status: Literal['DISPATCHED', 'VERIFIED', 'RESOLVED', 'FALSE_ALARM']
    staff: str = Field(default='Dashboard operator', min_length=1, max_length=80)
    note: str = Field(default='', max_length=500)


@app.post('/incidents/{incident_id}/review')
def review(incident_id: str, action: ReviewIn):
    with _lock:
        incident = next((i for i in _incidents if i['id'] == incident_id), None)
        if incident is None:
            raise HTTPException(404, 'Incident not found')
        if incident['status'] in ('RESOLVED','FALSE_ALARM'):
            if action.status==incident['status']:return public_event(incident)
            raise HTTPException(409,'Closed incident cannot be reopened by a review action')
        if action.status in ('VERIFIED','RESOLVED') and not incident.get('acknowledged_at'):
            raise HTTPException(409,'Acknowledge the incident before verification or resolution')
        if action.status=='RESOLVED' and not action.note.strip():raise HTTPException(422,'Resolution note required')
        if action.status=='DISPATCHED':
            route=notifications.select_route(incident)
            if not route or route['staff']!=action.staff:raise HTTPException(422,'Select the configured on-duty zone assignment')
            incident['assigned_staff']=route['staff']
        incident.update(status=action.status, staff=action.staff, updated_at=utc_now(), review_status='human_reviewed')
        if action.status in ('RESOLVED','FALSE_ALARM'):
            incident['resolved_at']=utc_now()
            incident['resolved_by']=action.staff
        incident['history'].append({'timestamp': utc_now(), 'status': action.status, 'note': action.note or action.staff})
        persist()
        if action.status == 'DISPATCHED': queue_notification(incident)
        return public_event(incident)


@app.get('/insights')
def insights():
    with _lock:
        return [{'incident_id':i['id'], 'summary':f"{i['reason']} in {ZONES[i['zone_id']]['name']}. "
                 + (f"Model {i['model_version']}; uncalibrated score {i['score']:.4f}. " if i.get('score') is not None else '')
                 + f"Processing mode: {i['processing_mode']}. Status: {i['status']}. Human review required."}
                for i in unique_overview_incidents(reversed(_incidents))]


@app.get('/analytics/evaluations')
def evaluations():
    specs = [
        ('fight_v3/reserved_comparison/comparison.csv','Reserved comparison; AIRTLab held-out + Peliculas reserved; research only'),
        ('fight_multiclip_v2/validation_comparison.csv','Validation used for V2 selection; not an independent test'),
        ('fight_v3/validation_metrics.csv','V3 development validation used for selection'),
        ('radar_route_a/radar_loso_summary.csv','TI IWR6843 leave-one-subject-out recording evaluation; not C1001 hardware'),
    ]
    results = []
    for rel,scope in specs:
        path=ROOT/'evaluation/outputs'/rel
        if path.is_file():
            with path.open(encoding='utf-8-sig',newline='') as f:
                results.append({'path':'evaluation/outputs/'+rel,'scope':scope,'rows':list(csv.DictReader(f))})
    for rel,scope in [('yamnet/yamnet_metrics.json','FSD50K screaming weak clip labels; impacts not evaluated'),
                      ('yolo_pose/metrics.json','Only four sequences; fixed pose heuristic, not temporal fall validation')]:
        path=ROOT/'evaluation/outputs'/rel
        if path.is_file():
            results.append({'path':'evaluation/outputs/'+rel,'scope':scope,'rows':[json.loads(path.read_text(encoding='utf-8-sig'))]})
    return results


REPLAY_FILES = {
    'radar': ROOT/'evaluation/outputs/radar_route_a/radar_predictions.csv',
    'acoustic': ROOT/'evaluation/outputs/yamnet/yamnet_predictions.csv',
}


@app.get('/sensors/replay')
def replay_options():
    options=[]
    for kind,path in REPLAY_FILES.items():
        if not path.is_file():
            continue
        with path.open(encoding='utf-8-sig',newline='') as f:
            for index,row in enumerate(csv.DictReader(f)):
                predicted = row.get('prediction',row.get('predicted','0')) == '1'
                if len([o for o in options if o['sensor']==kind]) >= 16:
                    break
                # Include positive saved predictions for a reproducible candidate demo.
                if predicted or index < 3:
                    options.append({'sensor':kind,'index':index,'label':row.get('file',row.get('filename','')),
                                    'candidate':predicted,'model':row.get('model','YAMNet')})
    return options


class ReplayIn(BaseModel):
    zone: str
    sensor: Literal['radar','acoustic']
    index: int = Field(ge=0,le=20000)


@app.post('/sensors/replay')
def replay(selection: ReplayIn):
    path=REPLAY_FILES[selection.sensor]
    if not path.is_file():
        raise HTTPException(503,'Recorded predictions unavailable')
    with path.open(encoding='utf-8-sig',newline='') as f:
        row=next((r for n,r in enumerate(csv.DictReader(f)) if n==selection.index),None)
    if row is None:
        raise HTTPException(404,'Recorded row not found')
    positive=row.get('prediction',row.get('predicted','0'))=='1'
    raw_score=row.get('fall_probability',row.get('score'))
    try:
        score=float(raw_score) if raw_score not in (None,'') else None
        if score is not None and (not math.isfinite(score) or not 0 <= score <= 1):
            raise ValueError('Invalid score')
    except (ValueError,TypeError):
        raise HTTPException(422,'Recorded prediction has an invalid model score')
    source='radar' if selection.sensor=='radar' else 'yamnet'
    kind=('fall' if positive else 'normal_motion') if source=='radar' else ('scream' if positive else 'normal_acoustic')
    digest=hashlib.sha256(path.read_bytes()).hexdigest()
    identity=json.dumps([selection.zone,selection.sensor,selection.index,digest],separators=(',',':'))
    identifier='sensor-replay-'+hashlib.sha256(identity.encode()).hexdigest()
    result=create_event(EventIn(zone=selection.zone,type=kind,source=source,confidence=1.0,
                    event_id=identifier,source_type='RECORDED SENSOR REPLAY',is_test=True,
                    score=score,model_version=row.get('model','YAMNet-FSD50K-screaming'),
                    processing_mode='recorded_sensor_replay',evidence_reference=str(path.relative_to(ROOT))+':row='+str(selection.index)+'; sha256:'+digest), TOKEN)
    result['record']=row
    from backend.sensor_observations import RecordedAdapter, save
    if result['event']['zone_id'] == 'ZONE_TOILET_BLINDSPOT':
        save(RecordedAdapter().from_event(result['event']))
    return result


@app.get('/monitoring/cameras')
def camera_registry():
    return registry.public_cameras()

@app.get('/monitoring/scenarios')
def scenario_registry():
    return registry.scenarios()

@app.get('/monitoring/sources/{scenario_id}')
def recording(scenario_id: str):
    from backend.browser_video import playback_source
    _, path = registry.source(scenario_id)
    prepared=time.perf_counter();source=playback_source(path)
    return FileResponse(source,media_type='video/mp4',headers={'X-Playback-Preparation-Ms':str(round((time.perf_counter()-prepared)*1000,3))})

@app.post('/monitoring/scenarios/{scenario_id}/run')
def run_sensor_scenario(scenario_id:str):
    zone='ZONE_TOILET_BLINDSPOT'
    if scenario_id in ('radar','acoustic'):
        option=next((r for r in replay_options() if r['sensor']==scenario_id and r['candidate']),None)
        if not option:raise HTTPException(503,'Positive saved prediction unavailable')
        return replay(ReplayIn(zone=zone,sensor=scenario_id,index=option['index']))
    if scenario_id=='fusion':
        create_event(EventIn(zone=zone,type='fall',source='simulation',sensor_modality='radar'),TOKEN)
        return create_event(EventIn(zone=zone,type='scream',source='simulation',sensor_modality='acoustic'),TOKEN)
    if scenario_id in ('sos','telegram'):
        result=create_event(EventIn(zone=zone,type='sos',source='simulation',sensor_modality='sos'),TOKEN)
        if scenario_id=='telegram':
            result['notification']=notifications.dispatch(result['incident'],force_test=True)
            record_notification_result(result['incident']['id'],result['notification'])
            result['notification']=notifications.public_result(result['notification'])
        return result
    raise HTTPException(404,'Unknown sensor scenario; use video job API for video scenarios')

@app.get('/notifications/status')
def notification_status():
    return notifications.status()

class TelegramTestIn(BaseModel):
    request_id: UUID
    authorized: bool = False

@app.post('/notifications/send-test')
def send_test_telegram(body:TelegramTestIn):
    """Explicit backend-only fresh TEST SOS; retrying request_id never resends."""
    cfg=notifications.status()
    if not body.authorized:raise HTTPException(403,'Explicit authorized test required')
    if cfg['mode']!='test' or not cfg['test_configured']:raise HTTPException(409,'Running backend must have TELEGRAM_MODE=test and an authorized test recipient')
    identifier='private-demo:telegram-test:'+str(body.request_id)
    probe={'zone_id':'ZONE_TOILET_BLINDSPOT','zone_type':'PRIVATE','is_test':True,'source_type':'SIMULATION','evidence':[{'type':'sos'}]}
    if not notifications.select_route(probe):raise HTTPException(409,'No authorized test route; no event or message created')
    result=create_event(EventIn(zone='ZONE_TOILET_BLINDSPOT',type='sos',source='simulation',sensor_modality='sos',
        processing_mode='simulation',source_type='SIMULATION',is_test=True,event_id=identifier,analysis_run_id=identifier,
        evidence_reference='Explicit backend-only authorized Telegram test; no hardware or emergency dispatch'),TOKEN)
    delivery=notify_test(result['incident']['id'])
    return {'incident_id':result['incident']['id'],'event_deduplicated':result.get('deduplicated',False),
            'notification':delivery,'receipt_verified':delivery.get('receipt_confirmed',False)}

@app.get('/incidents/{incident_id}/report')
def incident_report(incident_id:str):
    with _lock:
        incident=next((i for i in _incidents if i['id']==incident_id),None)
        if not incident: raise HTTPException(404,'Incident not found')
        attempts=[notifications.public_result(r) for r in storage.all_rows('notification') if r['incident_id']==incident_id]
        def elapsed(end):
            return round((datetime.fromisoformat(end)-datetime.fromisoformat(incident['created_at'])).total_seconds(),3) if end else None
        media=[m for e in incident['evidence'] for m in e.get('evidence_media',[])]
        return {**public_event(incident),'notification_state':notifications.delivery_state(attempts[-1]) if attempts else incident.get('notification_state','PENDING'),'notifications':attempts,
                'notification_requests':[r for r in storage.all_rows('notification_request') if r['incident_id']==incident_id],
                'analysis':{'acknowledgement_seconds':elapsed(incident.get('acknowledged_at')),'resolution_seconds':elapsed(incident.get('resolved_at')),
                'observation_count':len(incident['evidence']),'evidence_clip_count':len({m['id'] for m in media}),
                'model_versions':list(dict.fromkeys(e.get('model_version') for e in incident['evidence'] if e.get('model_version'))),
                'limits':'Model scores are not calibrated probabilities. Clip-level fight scores do not localize people or event timing; recorded sensors do not imply measured positions.'}}

@app.post('/incidents/{incident_id}/notify-test')
def notify_test(incident_id:str):
    with _lock:
        incident=next((i for i in _incidents if i['id']==incident_id),None)
        if not incident: raise HTTPException(404,'Incident not found')
        copied=json.loads(json.dumps(public_event(incident)))
    result=notifications.dispatch(copied,force_test=True)
    record_notification_result(incident_id,result)
    return notifications.public_result(result)

@app.post('/incidents/{incident_id}/verify-test-receipt')
def verify_test_receipt(incident_id:str):
    with _lock:
        incident=next((i for i in _incidents if i['id']==incident_id),None)
        if not incident:raise HTTPException(404,'Incident not found')
    result=notifications.verify_test_receipt(incident_id)
    if result.get('delivery_state')=='RECEIPT_CONFIRMED':
        record_notification_result(incident_id,result)
        route=notifications.select_route(incident)
        if incident.get('is_test',True) and route and route['staff']==result.get('assigned_staff') and incident['status'] not in ('RESOLVED','FALSE_ALARM'):
            acknowledge(incident_id,AckIn(staff=route['staff']))
    return result


@app.post('/incidents/{incident_id}/notify')
def notify_assigned_staff(incident_id:str):
    with _lock:
        incident=next((i for i in _incidents if i['id']==incident_id),None)
        if not incident:raise HTTPException(404,'Incident not found')
        queue_notification(incident)
        return {'status':'QUEUED','incident_id':incident_id}

@app.get('/analytics/incidents')
def incident_analytics():
    with _lock:
        by_source={}
        by_zone={}
        seconds=[]
        for i in _incidents:
            by_source[i['processing_mode']]=by_source.get(i['processing_mode'],0)+1
            by_zone[i['zone_id']]=by_zone.get(i['zone_id'],0)+1
            if i.get('acknowledged_at'):
                seconds.append((datetime.fromisoformat(i['acknowledged_at'])-datetime.fromisoformat(i['created_at'])).total_seconds())
        return {'candidates':len(_incidents),'by_source':by_source,'by_zone':by_zone,
                'false_alerts_reviewed':sum(i['status']=='FALSE_ALARM' for i in _incidents),
                'mean_acknowledgement_seconds':sum(seconds)/len(seconds) if seconds else None,
                'note':'Operational records, separate from research model evaluations'}

from backend.scenario_testing import install as install_scenario_testing
install_scenario_testing(app)

from backend.imported_lab import install as install_imported_lab
install_imported_lab(app)

from backend.radar_simulation import install as install_radar_simulation
install_radar_simulation(app)

from backend.sensor_observations import install as install_sensor_observations
install_sensor_observations(app)
