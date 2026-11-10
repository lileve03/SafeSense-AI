"""Overview-only grouping of repeated recorded analyses; never changes incidents."""
import re

VIDEO_HASH=re.compile(r'^sha256:([0-9a-f]{64})(?:;|$)')

def recorded_identity(incident):
    context=(incident.get('zone_id'),incident.get('processing_mode'),incident.get('source'),incident.get('source_type'),incident.get('level'))
    evidence=incident.get('evidence') or []
    if not evidence:return None
    if incident.get('processing_mode')=='recorded_sensor_replay':
        # Exact saved evaluation row is a valid replay identity, unlike score equality.
        if not all(re.fullmatch(r'.+:row=\d+',e.get('evidence_reference') or '') for e in evidence):return None
        return context,frozenset((e.get('type'),e.get('source'),e.get('model_version'),e['evidence_reference']) for e in evidence)
    if not (incident.get('is_test') is True and incident.get('processing_mode')=='real_model'
            and incident.get('source_type')=='RECORDED REAL VIDEO'):return None
    identities=[]
    normal_observations=[]
    for event in evidence:
        match=VIDEO_HASH.match(event.get('evidence_reference') or '')
        media=event.get('evidence_media') or []
        if not match:return None
        # Combined model runs may append a negative observation without retaining
        # media. It does not change the identity of the same recorded candidates.
        if not media and event.get('type')=='normal_motion':
            normal_observations.append((event.get('camera_id'),match.group(1)))
            continue
        if not media:return None
        intervals=[]
        for item in media:
            scope=item.get('time_scope')
            if scope not in ('whole_analyzed_clip_no_validated_event_timing','candidate_rule_timestamp'):return None
            if not all(isinstance(item.get(k),(int,float)) for k in ('start_sec','end_sec')):return None
            if scope=='candidate_rule_timestamp' and not isinstance(item.get('event_time_sec'),(int,float)):return None
            intervals.append((scope,item['start_sec'],item['end_sec'],item.get('event_time_sec')))
        identities.append((event.get('type'),event.get('source'),event.get('processing_mode'),event.get('model_version'),
                           event.get('camera_id'),match.group(1),frozenset(intervals)))
    if not identities:return None
    candidate_inputs={(identity[4],identity[5]) for identity in identities}
    if any(item not in candidate_inputs for item in normal_observations):return None
    return context,frozenset(identities)

def unique_overview_incidents(incidents):
    """Input is newest-first. Retain its latest representative and provenance."""
    seen_ids=set();seen_events=set();seen_recordings=set();result=[]
    for incident in incidents:
        if incident.get('status') in ('RESOLVED','FALSE_ALARM'):continue
        identifier=incident.get('id')
        context=(incident.get('zone_id'),incident.get('processing_mode'),incident.get('source_type'))
        event_ids=frozenset(incident.get('event_ids') or [])
        event_key=(context,event_ids) if event_ids else None
        recording=recorded_identity(incident)
        duplicate=(identifier is not None and identifier in seen_ids) or (event_key is not None and event_key in seen_events) or (recording is not None and recording in seen_recordings)
        if identifier is not None:seen_ids.add(identifier)
        if event_key is not None:seen_events.add(event_key)
        if recording is not None:seen_recordings.add(recording)
        if not duplicate:result.append(incident)
    return result
