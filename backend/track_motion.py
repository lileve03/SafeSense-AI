"""Explainable anonymous-track rules. No aggression classifier or accuracy claims."""
from collections import OrderedDict, deque
from dataclasses import asdict, dataclass
from datetime import datetime
import math
from threading import RLock
import time

FRAME = 'zone_meters_x_right_y_forward_z_up'
NOTICE = 'Proximity and repeated motion are review candidates, not proof of fighting or bullying.'


@dataclass(frozen=True)
class MotionRules:
    proximity_distance_m: float = 0.8
    proximity_duration_seconds: float = 3.0
    window_seconds: float = 8.0
    min_observation_span_seconds: float = 4.0
    min_reversals: int = 3
    reversal_angle_degrees: float = 150.0
    min_leg_displacement_m: float = 0.35
    min_leg_duration_seconds: float = 0.2
    min_motion_speed_mps: float = 0.2
    min_path_length_m: float = 2.0
    max_net_path_ratio: float = 0.5
    max_gap_seconds: float = 0.75
    min_sample_interval_seconds: float = 0.05
    min_quality: float = 0.3
    max_plausible_speed_mps: float = 6.0
    max_position_jump_m: float = 2.0
    max_abs_coordinate_m: float = 1000.0
    max_history_samples: int = 256

    def __post_init__(self):
        if any(not math.isfinite(v) or v <= 0 for k,v in asdict(self).items() if k != 'min_quality'):
            raise ValueError('Motion rule values must be finite and positive')
        if not 0 <= self.min_quality <= 1 or not 90 < self.reversal_angle_degrees <= 180:
            raise ValueError('Invalid quality or reversal angle')
        if self.min_observation_span_seconds > self.window_seconds or self.max_net_path_ratio > 1:
            raise ValueError('Invalid motion window or displacement ratio')
        if self.min_sample_interval_seconds >= self.max_gap_seconds:
            raise ValueError('Sample interval must be smaller than the continuity gap')
        if not isinstance(self.min_reversals,int) or not isinstance(self.max_history_samples,int) or self.min_reversals < 1 or self.max_history_samples < 3:
            raise ValueError('Invalid sample/reversal counts')


# Deployment rule configuration is owned here, not supplied by dashboard sliders.
RULES = MotionRules()
RULE_VERSION = 'anonymous-track-motion-v1'


def vector(value):
    if not isinstance(value, dict): return None
    values = [value.get(axis) for axis in ('x','y','z')]
    if any(isinstance(v,bool) or not isinstance(v,(float,int)) or not math.isfinite(v) for v in values): return None
    return tuple(float(v) for v in values)


def pairwise_distances(tracks):
    """Euclidean 3D distances only for supplied finite xyz positions."""
    located = [(t['id'],vector(t.get('position'))) for t in tracks]
    located = [(identifier,p) for identifier,p in located if p is not None]
    return sorted([{'track_ids':[a,b], 'distance_m':distance}
                   for i,(a,pa) in enumerate(located) for b,pb in located[i+1:]
                   if math.isfinite(distance:=math.dist(pa,pb))],key=lambda p:p['distance_m'])


def _xyz(v): return dict(zip(('x','y','z'),v)) if v is not None else None


def _angle(a,b):
    # Horizontal direction: vertical centroid/fall motion is not back-and-forth travel.
    na,nb=math.hypot(*a[:2]),math.hypot(*b[:2])
    if na == 0 or nb == 0: return None
    return math.degrees(math.acos(max(-1,min(1,(a[0]*b[0]+a[1]*b[1])/(na*nb)))))


def empty_analysis(reason, mode=None):
    return {'rule_version':RULE_VERSION,'source_mode':mode,'status':'UNAVAILABLE','reason':reason,
            'notice':NOTICE,'rules':asdict(RULES),'nearest_pair':None,'pairs':[],'tracks':[],
            'candidates':[],'highlighted_track_ids':[],'temporal_supported':False,'dropped_track_ids':[]}


class MotionAnalyzer:
    """Bounded session-scoped state. Restart intentionally starts a new warm-up window."""
    def __init__(self,rules=RULES):
        self.rules=rules
        self.streams=OrderedDict()
        self.lock=RLock()

    def _features(self,identifier,history):
        r=self.rules
        latest=history[-1]
        def velocity(index):
            sample=history[index]
            if sample[2] is not None: return sample[2],'reported'
            if index < 1: return None,'unavailable'
            previous=history[index-1];dt=sample[0]-previous[0]
            return tuple((a-b)/dt for a,b in zip(sample[1],previous[1])),'position_delta'
        v,origin=velocity(len(history)-1)
        previous,previous_origin=velocity(len(history)-2) if len(history)>1 else (None,None)
        acceleration=None
        if v is not None and previous is not None and origin==previous_origin:
            acceleration=tuple((a-b)/(latest[0]-history[-2][0]) for a,b in zip(v,previous))
        direction_change=_angle(previous,v) if previous is not None and v is not None and min(math.hypot(*v[:2]),math.hypot(*previous[:2]))>=r.min_motion_speed_mps else None
        # Build meaningful displacement legs. Jitter and reported velocity sign noise
        # cannot manufacture reversals without actual sustained coordinate travel.
        anchor=history[0];last_leg=None;reversals=0;legs=0
        for sample in list(history)[1:]:
            dt=sample[0]-anchor[0]
            delta=tuple(a-b for a,b in zip(sample[1],anchor[1]))
            displacement=math.hypot(*delta[:2])
            if dt>=r.min_leg_duration_seconds and displacement>=r.min_leg_displacement_m and displacement/dt>=r.min_motion_speed_mps:
                if last_leg is not None and _angle(last_leg,delta)>=r.reversal_angle_degrees: reversals+=1
                last_leg=delta;anchor=sample;legs+=1
        path=sum(math.hypot(a[1][0]-b[1][0],a[1][1]-b[1][1]) for a,b in zip(history,list(history)[1:]))
        net=math.hypot(latest[1][0]-history[0][1][0],latest[1][1]-history[0][1][1])
        span=latest[0]-history[0][0]
        ratio=net/path if path>0 else None
        candidate=(span>=r.min_observation_span_seconds and reversals>=r.min_reversals
                   and path>=r.min_path_length_m and ratio is not None and ratio<=r.max_net_path_ratio)
        return {'id':identifier,'feature_timestamp_seconds':latest[0],'sample_count':len(history),'observed_span_seconds':span,
                'velocity_mps':_xyz(v),'velocity_origin':origin,'speed_mps':math.sqrt(sum(c*c for c in v)) if v is not None else None,
                'acceleration_mps2':_xyz(acceleration),'acceleration_magnitude_mps2':math.sqrt(sum(c*c for c in acceleration)) if acceleration is not None else None,
                'heading_degrees':math.degrees(math.atan2(v[1],v[0])) if v is not None and math.hypot(*v[:2])>=r.min_motion_speed_mps else None,
                'direction_change_degrees':direction_change,'meaningful_legs':legs,'reversals_in_window':reversals,
                'path_length_m':path,'net_displacement_m':net,'net_path_ratio':ratio,'repeated_motion_candidate':candidate}

    def process(self,observation):
        with self.lock: return self._process(observation)

    def _process(self,o):
        r=self.rules;mode=o.get('source_mode')
        key=tuple(o.get(k) for k in ('source_mode','device_id','zone_id','tracking_session_id'))
        now=time.monotonic()
        for old in list(self.streams):
            if now-self.streams[old]['received']>60: self.streams.pop(old)
        state=self.streams.setdefault(key,{'last':None,'histories':{},'pairs':{},'received':now})
        state['received']=now;self.streams.move_to_end(key)
        while len(self.streams)>64:self.streams.popitem(last=False)
        def unavailable(reason):
            state['histories'].clear();state['pairs'].clear();state['last']=None
            result=empty_analysis(reason,mode);result['rules']=asdict(r);return result
        if o.get('data_validity')!='VALID':return unavailable('Observation is not VALID; temporal continuity cleared')
        if o.get('coordinate_frame')!=FRAME:return unavailable('Calibrated zone coordinates unavailable; no distance or motion inference')
        try:
            timestamp=datetime.fromisoformat(o['timestamp'].replace('Z','+00:00'))
            if timestamp.tzinfo is None:raise ValueError()
            t=timestamp.timestamp()
        except (ValueError,KeyError,TypeError,AttributeError):return unavailable('Timezone-aware observation timestamp required')
        temporal=bool(o.get('tracking_session_id')) and o.get('timestamp_basis')=='CAPTURE_TIME'
        issues=[]
        if not temporal:
            state['histories'].clear();state['pairs'].clear()
            issues.append('Temporal rules require tracking_session_id and CAPTURE_TIME; instantaneous distances only')
        if state['last'] is not None:
            dt=t-state['last']
            if dt<=0:return unavailable('Non-increasing timestamps rejected; temporal continuity cleared')
            if dt>r.max_gap_seconds+1e-6:
                state['histories'].clear();state['pairs'].clear();issues.append('Observation gap exceeded continuity limit; histories restarted')
        state['last']=t
        tracks=o.get('tracks') or []
        ids=[track.get('id') for track in tracks]
        if any(not isinstance(identifier,str) or not identifier for identifier in ids) or len(ids)!=len(set(ids)):
            return unavailable('Missing or duplicate track IDs; no identity continuity inferred')
        good=[];missing=[]
        for track in tracks:
            p=vector(track.get('position'));quality=track.get('quality')
            if p is None or any(abs(v)>r.max_abs_coordinate_m for v in p) or (quality is not None and (not isinstance(quality,(int,float)) or not math.isfinite(quality) or quality<r.min_quality or quality>1)):
                missing.append(track['id']);continue
            good.append(track)
        present={track['id'] for track in good}
        dropped=set(state['histories'])-present
        for identifier in dropped:state['histories'].pop(identifier,None)
        for pair in list(state['pairs']):
            if not set(pair)<=present:state['pairs'].pop(pair)
        if missing:issues.append('Missing/non-finite/out-of-range coordinates or low quality excluded: '+', '.join(missing))
        features=[];reset_ids=set()
        for track in good:
            identifier=track['id'];p=vector(track['position']);v=vector(track.get('velocity'))
            if v is not None and math.hypot(*v)>r.max_plausible_speed_mps:
                v=None;issues.append('Implausible reported velocity ignored; coordinate deltas used where supported: '+identifier)
            history=state['histories'].setdefault(identifier,deque(maxlen=r.max_history_samples))
            if history and (math.dist(p,history[-1][1])>r.max_position_jump_m or math.dist(p,history[-1][1])/(t-history[-1][0])>r.max_plausible_speed_mps):
                history.clear();reset_ids.add(identifier);issues.append('Implausible jump / possible ID reuse: '+identifier+'; history restarted')
            if not history or t-history[-1][0]>=r.min_sample_interval_seconds-1e-6:
                history.append((t,p,v))
            while len(history)>1 and history[0][0]<t-r.window_seconds-1e-9:history.popleft()
            feature=self._features(identifier,history)
            if not temporal:feature['repeated_motion_candidate']=False
            features.append(feature)
        for pair in list(state['pairs']):
            if reset_ids.intersection(pair):state['pairs'].pop(pair)
        pairs=pairwise_distances(good);candidates=[]
        for pair in pairs:
            identity=tuple(sorted(pair['track_ids']));near=pair['distance_m']<r.proximity_distance_m
            if near and temporal:
                dwell=state['pairs'].setdefault(identity,{'start':t,'samples':0});dwell['samples']+=1
                duration=t-dwell['start']
            else:
                state['pairs'].pop(identity,None);duration=0
            candidate=temporal and near and duration+1e-6>=r.proximity_duration_seconds
            pair.update(within_threshold=near,proximity_duration_seconds=duration,proximity_candidate=candidate)
            if candidate:candidates.append({'rule':'PROXIMITY_DURATION','track_ids':pair['track_ids'],
                'reason':f'Distance {pair["distance_m"]:.2f}m < {r.proximity_distance_m}m for {duration:.2f}s >= {r.proximity_duration_seconds}s; normal conversation/queuing may satisfy this rule.'})
        for feature in features:
            if feature['repeated_motion_candidate']:
                candidates.append({'rule':'REPEATED_BACK_AND_FORTH','track_ids':[feature['id']],
                    'reason':f'{feature["reversals_in_window"]} meaningful reversals >= {r.min_reversals} within {feature["observed_span_seconds"]:.2f}s; path {feature["path_length_m"]:.2f}m, net/path {feature["net_path_ratio"]:.2f}. Repeated pacing/exercise can satisfy this rule.'})
        if not good:issues.append('No valid positioned tracks; no distances or temporal triggers supported')
        if not temporal:
            # Instantaneous features must never become a predecessor in a later
            # capture-time stream when provenance changes within the same ID scope.
            state['histories'].clear();state['pairs'].clear()
        return {'rule_version':RULE_VERSION,'source_mode':mode,'status':'AVAILABLE' if good and not issues else 'PARTIAL' if good else 'UNAVAILABLE',
                'timestamp':o['timestamp'],'tracking_session_id':o.get('tracking_session_id'),'rules':asdict(r),'notice':NOTICE,
                'reason':'; '.join(issues) if issues else 'Position-supported rule features; candidates require human review',
                'temporal_supported':temporal and bool(good),'nearest_pair':pairs[0] if pairs else None,'pairs':pairs,'tracks':features,
                'candidates':candidates,'highlighted_track_ids':sorted({identifier for c in candidates for identifier in c['track_ids']}),
                'dropped_track_ids':sorted(dropped),'excluded_track_ids':missing}


ANALYZER=MotionAnalyzer()
