"""Conservative recording-local IoU association; never bridges missing/ambiguous detections.
Not identity recognition or a calibrated fall classifier.
"""
from collections import deque


def overlap(a, b):
    x=max(0,min(a[2],b[2])-max(a[0],b[0]))
    y=max(0,min(a[3],b[3])-max(a[1],b[1]))
    intersection=x*y
    union=(a[2]-a[0])*(a[3]-a[1])+(b[2]-b[0])*(b[3]-b[1])-intersection
    return intersection/union if union>0 else 0


class PoseRuleTracker:
    def __init__(self):
        self.tracks={}
        self.next_id=1

    def update(self, people, postures, frame_index, fps):
        matches=[[tid for tid,t in self.tracks.items() if overlap(p['bbox_xyxy'],t['box'])>=.2] for p in people]
        counts={tid:sum(tid in candidates for candidates in matches) for tid in self.tracks}
        current={};events=[]
        for p,posture,candidates in zip(people,postures,matches):
            if len(candidates)==1 and counts[candidates[0]]==1:
                tid=candidates[0];track=self.tracks[tid]
            else:
                tid=self.next_id;self.next_id+=1
                track={'history':deque(maxlen=12),'upright':0,'state':'NORMAL','age':0}
            track['age']+=1;track['box']=p['bbox_xyxy'];track['history'].append(posture)
            if posture=='upright':track['upright']=min(12,track['upright']+1)
            horizontal=sum(v=='horizontal' for v in track['history'])
            if posture=='horizontal' and horizontal>=5 and track['state']=='NORMAL':
                track['state']='POSSIBLE FALL' if track['upright']>=3 else 'FALL CANDIDATE'
                events.append({'frame':frame_index+1,'time_sec':round(frame_index/fps,6),'track_id':tid,
                    'type':'possible_fall' if track['state']=='POSSIBLE FALL' else 'horizontal_posture_candidate',
                    'reason':'tracked_upright_to_persistent_horizontal' if track['state']=='POSSIBLE FALL' else 'persistent_horizontal_without_observed_transition',
                    'rule_state':True,'score':None})
            elif posture=='upright' and sum(v=='upright' for v in track['history'])>=3:
                track['state']='NORMAL'
            elif posture=='other' and horizontal<2 and track['state']=='FALL CANDIDATE':track['state']='NORMAL'
            p.update(track_id=tid,track_age=track['age'],tracking_method='conservative_iou_v1',
                posture=posture,fall_state=track['state'],fall_score=None,
                fall_rule_active=track['state']=='POSSIBLE FALL' and posture=='horizontal',
                fall_candidate=track['state']=='POSSIBLE FALL' and posture=='horizontal')
            current[tid]=track
        self.tracks=current
        return events
