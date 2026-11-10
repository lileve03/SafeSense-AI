"""Normalized, metadata-only acquisition boundary. No physical driver is installed."""
from datetime import datetime, timezone
from enum import Enum
import hashlib
from typing import Literal
from uuid import uuid4

from fastapi import Header, HTTPException
from pydantic import BaseModel, ConfigDict, Field, AwareDatetime, model_validator
from backend import storage
from backend.track_motion import ANALYZER, MotionAnalyzer, RULES, RULE_VERSION, empty_analysis
from dataclasses import asdict


class Mode(str, Enum):
    SIMULATION = 'SIMULATION'
    RECORDED_REPLAY = 'RECORDED_REPLAY'
    LIVE_HARDWARE = 'LIVE_HARDWARE'


class Strict(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False)


class Vector(Strict):
    x: float
    y: float
    z: float


class Track(Strict):
    id: str = Field(min_length=1, max_length=80)
    position: Vector | None = None
    velocity: Vector | None = None
    quality: float | None = Field(default=None, ge=0, le=1)
    snr_db: float | None = None


class AcousticEvent(Strict):
    kind: Literal['scream', 'impact', 'normal_acoustic']
    confidence: float = Field(ge=0, le=1)


class Observation(Strict):
    schema_version: Literal[1] = 1
    observation_id: str = Field(default_factory=lambda: str(uuid4()), max_length=80, min_length=1)
    source_mode: Mode
    device_id: str = Field(min_length=1, max_length=80)
    zone_id: str = Field(min_length=1, max_length=80)
    timestamp: AwareDatetime
    timestamp_basis: Literal['CAPTURE_TIME', 'REPLAY_EVENT_TIME'] = 'CAPTURE_TIME'
    tracking_session_id: str | None = Field(default=None,min_length=1,max_length=80)
    data_validity: Literal['VALID', 'INVALID', 'STALE', 'UNAVAILABLE']
    validity_reason: str | None = Field(default=None, max_length=500)
    coordinate_frame: Literal['zone_meters_x_right_y_forward_z_up'] | None = None
    tracks: list[Track] | None = Field(default=None, max_length=128)
    point_cloud: list[Vector] | None = Field(default=None, max_length=4096)
    acoustic_events: list[AcousticEvent] | None = Field(default=None, max_length=32)
    sos_state: Literal['ACTIVE', 'INACTIVE', 'UNKNOWN'] = 'UNKNOWN'
    radar_event: Literal['presence', 'normal_motion', 'rapid_motion', 'fall'] | None = None
    confidence: float = Field(default=1, ge=0, le=1)
    evidence_reference: str | None = Field(default=None, max_length=500)

    @model_validator(mode='after')
    def spatial_contract(self):
        if (self.point_cloud or any(t.position or t.velocity for t in self.tracks or [])) and not self.coordinate_frame:
            raise ValueError('Spatial data requires a calibrated zone coordinate frame')
        ids = [t.id for t in self.tracks or []]
        if len(ids) != len(set(ids)):
            raise ValueError('Track IDs must be unique within an observation')
        kinds=[e.kind for e in self.acoustic_events or []]
        if len(kinds) != len(set(kinds)):
            raise ValueError('Acoustic event classes must be unique within an observation')
        return self


class SimulationAdapter:
    def normalize(self, observation):
        if observation.source_mode != Mode.SIMULATION:
            raise HTTPException(422, 'Simulation adapter requires SIMULATION')
        return observation


class RecordedAdapter:
    """Only existing server-owned event evidence, never browser-authored measurements."""
    def from_event(self, event):
        if event.get('source_type') != 'RECORDED SENSOR REPLAY' and event.get('processing_mode') != 'recorded_sensor_replay':
            raise HTTPException(422, 'Event is not recorded sensor evidence')
        if event['source'] not in ('radar', 'yamnet'):
            raise HTTPException(422, 'Only radar/acoustic metadata is supported')
        return Observation(
            observation_id='replay-'+hashlib.sha256(event['id'].encode()).hexdigest(),
            source_mode=Mode.RECORDED_REPLAY, device_id='recorded-'+event['source'],
            zone_id=event['zone_id'], timestamp=event['timestamp'], timestamp_basis='REPLAY_EVENT_TIME', data_validity='VALID',
            validity_reason='Recorded classification; acquisition time and spatial measurements unavailable',
            radar_event=event['type'] if event['source']=='radar' else None,
            acoustic_events=[AcousticEvent(kind=event['type'], confidence=event['confidence'])] if event['source']=='yamnet' else None,
            confidence=event['confidence'], evidence_reference=event.get('evidence_reference'))


class HardwareAdapter:
    """Fail-closed extension point. A client flag or API token cannot verify hardware."""
    def status(self):
        return {'connected': False, 'verified': False, 'label': 'Hardware Disconnected',
                'reason': 'No physical driver, device identity, heartbeat or calibration verified'}

    def normalize(self, observation):
        raise HTTPException(503, 'Hardware Disconnected: physical adapter has not been commissioned')


hardware = HardwareAdapter()


def save(observation):
    with storage.LOCK:
        return _save_locked(observation)


def _save_locked(observation):
    import json
    body = observation.model_dump(mode='json')
    fingerprint=hashlib.sha256(json.dumps(body,sort_keys=True).encode()).hexdigest()
    body['payload_sha256']=fingerprint
    body['received_at'] = datetime.now(timezone.utc).isoformat()
    body['hardware_verified'] = False
    # Preserve capture validity, but do not allow old/future data into current fusion.
    age = (datetime.now(timezone.utc)-observation.timestamp).total_seconds()
    if observation.source_mode != Mode.RECORDED_REPLAY and observation.data_validity=='VALID' and not -5 <= age <= 10:
        body['data_validity']='STALE'
        body['validity_reason']='Observation outside current ingestion window (-5 to 10 seconds)'
    previous = storage.get('sensor_observation', observation.observation_id)
    if previous:
        # Preserve retry compatibility for observations saved before this optional
        # session field was introduced. No existing payload/incident is rewritten.
        legacy_match=False
        if 'tracking_session_id' not in previous and observation.tracking_session_id is None:
            legacy_input={k:v for k,v in observation.model_dump(mode='json').items() if k!='tracking_session_id'}
            legacy_match=previous.get('payload_sha256')==hashlib.sha256(json.dumps(legacy_input,sort_keys=True).encode()).hexdigest()
        if previous.get('payload_sha256') != fingerprint and not legacy_match:
            raise HTTPException(409, 'Observation ID already belongs to different data')
        return previous
    body['motion_analysis']=ANALYZER.process(body)
    storage.put('sensor_observation', observation.observation_id, body)
    return body


class ReplayRequest(Strict):
    event_id: str = Field(min_length=1, max_length=100)


class MotionPreview(Strict):
    observations: list[Observation] = Field(min_length=1,max_length=121)


def install(app):
    from backend.main import valid_token, ZONES, EventIn, create_event, TOKEN

    def with_backend_assessment(row):
        if not row or row['source_mode']!='RECORDED_REPLAY':return row
        from backend.main import _events, _incidents, _lock
        with _lock:
            events=list(_events);incidents=list(_incidents)
        matches=lambda event:row['observation_id']=='replay-'+hashlib.sha256(event['id'].encode()).hexdigest()
        event=next((event for event in reversed(events) if matches(event)),None)
        if event is None:event=next((event for event in storage.all_rows('event') if matches(event)),None)
        if not event:return row
        incident=next((incident for incident in reversed(incidents) if event['id'] in incident.get('event_ids',[])),None)
        closed=incident and incident['status'] in ('RESOLVED','FALSE_ALARM')
        return {**row,'backend_assessment':{'event_id':event['id'],'incident_id':incident['id'] if incident else None,
                'level':'LOW' if closed else incident['level'] if incident else event['level'],
                'reason':'Linked recorded incident closed' if closed else incident['reason'] if incident else event['reason'],
                'status':incident['status'] if incident else None}}

    def require_token(token):
        if not valid_token(token):
            raise HTTPException(401, 'Local staff access token required')

    def zone_check(zone):
        if zone not in ZONES or ZONES[zone]['type'] != 'PRIVATE':
            raise HTTPException(422, 'A registered private zone is required')

    @app.get('/sensors/observations/status')
    def status(x_safesense_token: str | None = Header(default=None)):
        require_token(x_safesense_token)
        return {'modes': [m.value for m in Mode], 'hardware': hardware.status(),
                'spatial_units': 'meters; velocity meters/second',
                'recorded_capabilities': ['radar classification', 'acoustic classification'],
                'recorded_unavailable': ['anonymous tracks', 'point clouds', 'people count', 'distance', 'capture timestamp']}

    @app.get('/sensors/observations')
    def latest(zone_id: str, source_mode: Mode, x_safesense_token: str | None = Header(default=None)):
        require_token(x_safesense_token)
        zone_check(zone_id)
        rows = [r for r in storage.all_rows('sensor_observation') if r['zone_id']==zone_id and r['source_mode']==source_mode.value]
        row = max(rows, key=lambda r:datetime.fromisoformat(r['timestamp'])) if rows else None
        if row and source_mode != Mode.RECORDED_REPLAY:
            age=(datetime.now(timezone.utc)-datetime.fromisoformat(row['timestamp'])).total_seconds()
            if age>10 and row['data_validity']=='VALID':
                row={**row,'data_validity':'STALE','validity_reason':'No fresh observation within 10 seconds',
                     'motion_analysis':empty_analysis('Current observation is stale; temporal highlights unavailable',source_mode.value)}
        if row and 'motion_analysis' not in row:
            row={**row,'motion_analysis':MotionAnalyzer().process(row)}
        return {'observation': with_backend_assessment(row), 'hardware': hardware.status()}

    @app.get('/sensors/motion/rules')
    def motion_rules(x_safesense_token: str | None = Header(default=None)):
        require_token(x_safesense_token)
        return {'rule_version':RULE_VERSION,'rules':asdict(RULES),'configuration_owner':'backend.track_motion.RULES',
                'notice':'Rule-based review candidates; no fighting/bullying verdict or ML accuracy'}

    @app.post('/sensors/motion/preview')
    def motion_preview(body:MotionPreview,x_safesense_token: str | None = Header(default=None)):
        require_token(x_safesense_token)
        keys=set();analyzer=MotionAnalyzer();result=None
        for observation in body.observations:
            zone_check(observation.zone_id)
            if observation.source_mode!=Mode.SIMULATION:
                raise HTTPException(422,'Preview accepts explicit SIMULATION only; recorded/live data must use trusted adapters')
            if not observation.tracking_session_id or observation.timestamp_basis!='CAPTURE_TIME':
                raise HTTPException(422,'Simulation preview requires one tracking session and a synthetic capture clock')
            if len(observation.tracks or [])>8 or observation.point_cloud:
                raise HTTPException(422,'Motion preview is limited to eight tracks and no point cloud')
            keys.add((observation.device_id,observation.zone_id,observation.tracking_session_id))
            if len(keys)>1:raise HTTPException(422,'One device/zone/tracking session per preview')
            result=analyzer.process(observation.model_dump(mode='json'))
        return {'analysis':result,'persisted':False,'events_created':0,'timestamp_semantics':'synthetic simulation clock'}

    @app.post('/sensors/observations')
    def ingest(observation: Observation, x_safesense_token: str | None = Header(default=None)):
        require_token(x_safesense_token)
        zone_check(observation.zone_id)
        if observation.source_mode == Mode.LIVE_HARDWARE:
            return hardware.normalize(observation)
        if observation.source_mode != Mode.SIMULATION:
            raise HTTPException(422, 'Use the recorded adapter with a persisted event ID')
        saved=save(SimulationAdapter().normalize(observation))
        results=[]
        age=(datetime.now(timezone.utc)-observation.timestamp).total_seconds()
        connected_demo=bool(observation.tracking_session_id and observation.tracking_session_id.startswith('private-demo:'))
        fresh=saved['data_validity']=='VALID' and -5 <= age <= 10
        if fresh or connected_demo:
            signals=[]
            if observation.radar_event: signals.append((observation.radar_event,'radar',observation.confidence))
            signals.extend((e.kind,'acoustic',e.confidence) for e in observation.acoustic_events or [])
            if observation.sos_state=='ACTIVE': signals.append(('sos','sos',1))
            for kind, modality, confidence in signals:
                group=observation.tracking_session_id if connected_demo else 'observation-'+hashlib.sha256(observation.observation_id.encode()).hexdigest()
                identifier=group+':'+kind if connected_demo else 'obs-'+hashlib.sha256(f'{observation.observation_id}:{modality}:{kind}'.encode()).hexdigest()
                if not fresh and not storage.get('event',identifier):
                    raise HTTPException(409,'Expired observation cannot create a new signal; prepare an explicit new test run')
                results.append(create_event(EventIn(zone=observation.zone_id,type=kind,source='simulation',
                    sensor_modality=modality,confidence=0 if connected_demo and kind=='sos' else confidence,processing_mode='simulation',is_test=True,
                    source_type='SIMULATION',analysis_run_id=group,observed_at=observation.timestamp,
                    event_id=identifier,
                    evidence_reference='SIMULATED normalized observation '+observation.observation_id), TOKEN))
        return {'observation': saved, 'events': results, 'hardware': hardware.status()}

    @app.post('/sensors/observations/replay')
    def replay(request: ReplayRequest, x_safesense_token: str | None = Header(default=None)):
        require_token(x_safesense_token)
        event=storage.get('event',request.event_id)
        if not event: raise HTTPException(404,'Recorded event not found; run existing sensor replay/inference first')
        zone_check(event['zone_id'])
        return {'observation': with_backend_assessment(save(RecordedAdapter().from_event(event))), 'hardware': hardware.status()}
