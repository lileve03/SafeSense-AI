"""Experimental interaction localization from measured poses, not classifier boxes.
Scores are deterministic heuristic strengths, never calibrated probabilities.
"""
import math
from collections import deque
from copy import deepcopy
from itertools import combinations
import numpy as np
from scipy.optimize import linear_sum_assignment
from backend.pose_tracking import overlap

VERSION='pose-interaction-v1'
CONFIG={'keypoint_confidence':.5,'min_person_confidence':.4,'tracking_gap_sec':.1,
        'max_center_distance_heights':.9,'contact_radius_heights':.3,
        'rapid_arm_heights_per_sec':1.2,'window_sec':.6,'min_hits':3,
        'min_span_sec':.1,'hold_sec':.12,'min_track_age':4,'min_reciprocal_hits':2,'min_approach_heights_per_sec':.4}

def point(person,index):
    points=person.get('keypoints',[])
    if index>=len(points):return None
    p=points[index]
    if not all(isinstance(p.get(k),(int,float)) and math.isfinite(p[k]) for k in ('x','y','confidence')) or p['confidence']<CONFIG['keypoint_confidence']:return None
    return np.array([p['x'],p['y']],dtype=float)

def height(p):return max(1.,p['bbox_xyxy'][3]-p['bbox_xyxy'][1])
def center(p):
    b=p['bbox_xyxy'];return np.array([(b[0]+b[2])/2,(b[1]+b[3])/2])

def gate(pose,fight):
    score=fight.get('score',fight.get('violence_score'));threshold=fight.get('threshold')
    return (fight.get('model_version') in ('v2','v3') and fight.get('candidate_detected') is True
        and isinstance(score,(int,float)) and math.isfinite(score) and 0<=score<=1
        and isinstance(threshold,(int,float)) and 0<=threshold<=1 and score>=threshold
        and bool(pose.get('input_sha256')) and pose['input_sha256']==fight.get('input_sha256'))

def annotate_participants(pose,fight):
    frames=deepcopy(pose.get('pose_frames',[]));tracks={};next_id=1;pairs={};events=[]
    enabled=gate(pose,fight)
    duration=fight.get('video_duration_sec',0)
    for frame in frames:
        now=frame['time_sec'];persons=frame['persons']
        for person in persons:
            person.update(fight_participant=False,participant_score=None)
        if not enabled or not 0<=now<duration:continue
        people=[p for p in persons if p.get('confidence',0)>=CONFIG['min_person_confidence'] and len(p.get('bbox_xyxy',[]))==4]
        previous={tid:t for tid,t in tracks.items() if 0<now-t['time']<=CONFIG['tracking_gap_sec']}
        ids=list(previous);cost=np.full((len(ids),len(people)),100.,dtype=float)
        for i,tid in enumerate(ids):
            old=previous[tid]['person']
            for j,p in enumerate(people):
                scale=(height(old)+height(p))/2;distance=float(np.linalg.norm(center(old)-center(p))/scale)
                shared=[np.linalg.norm(point(old,k)-point(p,k))/scale for k in range(17) if point(old,k) is not None and point(p,k) is not None]
                if distance<.45 and len(shared)>=6:
                    cost[i,j]=.45*(1-overlap(old['bbox_xyxy'],p['bbox_xyxy']))+.3*distance+.25*float(np.median(shared))
        assigned={}
        if len(ids) and len(people):
            for i,j in zip(*linear_sum_assignment(cost)):
                others=[cost[k,j] for k in range(len(ids)) if k!=i]+[cost[i,k] for k in range(len(people)) if k!=j]
                if cost[i,j]<.65 and (not others or min(others)-cost[i,j]>.06):assigned[j]=ids[i]
        current={}
        for j,p in enumerate(people):
            tid=assigned.get(j)
            if tid is None:tid=next_id;next_id+=1
            old=previous.get(tid);age=old['age']+1 if old else 1
            p.update(interaction_track_id=tid,interaction_track_age=age)
            arms=[]
            if old:
                dt=now-old['time'];scale=(height(p)+height(old['person']))/2
                for shoulder,wrist in ((5,9),(6,10)):
                    a,b,c,d=point(p,shoulder),point(p,wrist),point(old['person'],shoulder),point(old['person'],wrist)
                    if all(v is not None for v in (a,b,c,d)):
                        velocity=((b-a)-(d-c))/(scale*dt)
                        arms.append((b,velocity,float(np.linalg.norm(velocity))))
            current[tid]={'person':p,'time':now,'age':age,'arms':arms}
        close_pairs=set()
        for a,b in combinations(current,2):
            first,second=current[a],current[b];p,q=first['person'],second['person'];pair=tuple(sorted((a,b)))
            scale=(height(p)+height(q))/2;distance=float(np.linalg.norm(center(p)-center(q))/scale)
            if distance>CONFIG['max_center_distance_heights']:continue
            if min(first['age'],second['age'])<CONFIG['min_track_age']:continue
            close_pairs.add(pair)
            strength=0.;contact=None;hit_sources=set()
            for source,target in ((first,second),(second,first)):
                targets=[point(target['person'],k) for k in (0,5,6,11,12) if point(target['person'],k) is not None]
                if len(targets)<3:continue
                for wrist,velocity,speed in source['arms']:
                    if speed<CONFIG['rapid_arm_heights_per_sec']:continue
                    target_point=min(targets,key=lambda t:float(np.linalg.norm(wrist-t)))
                    delta=target_point-wrist;near=float(np.linalg.norm(delta)/scale)
                    approach=float(np.dot(velocity,delta/max(1.,float(np.linalg.norm(delta)))))
                    if near<=CONFIG['contact_radius_heights'] and approach>=CONFIG['min_approach_heights_per_sec'] and speed<=8:
                        hit_sources.add(source['person']['interaction_track_id'])
                        if speed>strength:strength=speed;contact=near
            history=pairs.setdefault(pair,{'hits':deque(),'active':False})
            if strength:history['hits'].append((now,strength,contact,hit_sources))
            while history['hits'] and now-history['hits'][0][0]>CONFIG['window_sec']:history['hits'].popleft()
            hits=history['hits']
            reciprocal=all(sum(tid in h[3] for h in hits)>=CONFIG['min_reciprocal_hits'] for tid in pair)
            supported=(reciprocal and len(hits)>=CONFIG['min_hits'] and hits[-1][0]-hits[0][0]>=CONFIG['min_span_sec'] and now-hits[-1][0]<=CONFIG['hold_sec'])
            if supported:
                proximity=max(0.,1-distance/CONFIG['max_center_distance_heights'])
                motion=min(1.,max(h[1] for h in hits)/3.)
                persistence=min(1.,len(hits)/6.)
                score=round(.35*proximity+.4*motion+.25*persistence,4)
                evidence={'heuristic_version':VERSION,'pair_track_ids':list(pair),'proximity_heights':round(distance,4),
                    'peak_arm_speed_heights_per_sec':round(max(h[1] for h in hits),4),'interaction_hits':len(hits),'reciprocal_hits':{str(tid):sum(tid in h[3] for h in hits) for tid in pair},
                    'window_start_sec':hits[0][0],'last_observed_interaction_sec':hits[-1][0],
                    'score_components':{'proximity':round(proximity,4),'arm_motion':round(motion,4),'persistence':round(persistence,4)}}
                for person in (p,q):
                    if score>(person.get('participant_score') or 0):person.update(fight_participant=True,participant_score=score,participant_evidence=evidence)
                if not history['active']:events.append({'time_sec':now,'frame_index':frame['frame_index'],'type':'possible_fight_participants','track_ids':list(pair),'participant_score':score,'heuristic_version':VERSION})
            history['active']=supported
        tracks=current
        # Never bridge identities after ambiguous/missing associations.
        pairs={pair:h for pair,h in pairs.items() if pair in close_pairs and all(tid in current for tid in pair)}
    return {'pose_frames':frames,'participant_events':events,'participant_heuristic':{'version':VERSION,'enabled':enabled,
        'score_type':'uncalibrated interaction heuristic strength; not V2/V3 score or probability',
        'classifier_version':fight.get('model_version'),'classifier_score':fight.get('score',fight.get('violence_score')),
        'classifier_window':'whole analyzed clip; no classifier-localized fight interval',
        'config':CONFIG,'limitations':'2D pose association and repeated fast near-body arm motion; not proof of aggression or participant identity'}}
