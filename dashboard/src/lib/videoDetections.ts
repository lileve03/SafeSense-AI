export type PosePoint={x:number;y:number;confidence:number|null};
export type PosePerson={bbox_xyxy:number[];confidence:number;keypoints:PosePoint[];fight_participant?:boolean;participant_score?:number|null;interaction_track_id?:number;participant_evidence?:{heuristic_version?:string;pair_track_ids?:number[];interaction_hits?:number;reciprocal_hits?:Record<string,number>};fall_candidate?:boolean;track_id?:number;track_age?:number;tracking_method?:string;fall_rule_active?:boolean;fall_state?:string;fall_score?:number|null};
export type PoseFrame={frame_index:number;time_sec:number;persons:PosePerson[];fall_state?:string;posture?:string;rule_person_index?:number|null;fall_score?:number|null};
// Select the latest timestamp at or before the decoded video time. Never stretch
// a stale detection over missing frames or beyond the analyzed recording.
export function playbackPoseFrame(result:any,time:number):PoseFrame|null {
 const frames:PoseFrame[]=result?.pose_frames||[];
 const fps=Number(result?.annotation_alignment?.fps);
 if(!frames.length||!Number.isFinite(time)||time<0||!(fps>0))return null;
 // Allow only sub-frame timestamp quantization/decoder jitter, never a whole
 // missing frame or arbitrary nearest-neighbour extrapolation.
 const interval=1/fps,tolerance=Math.min(.002,interval*.05);
 let lo=0,hi=frames.length-1,index=-1;
 while(lo<=hi){const mid=(lo+hi)>>>1;if(frames[mid].time_sec<=time+tolerance){index=mid;lo=mid+1;}else hi=mid-1;}
 const frame=frames[index];
 return frame&&time-frame.time_sec<interval+tolerance?frame:null;
}
export const poseEdges=[[0,1],[0,2],[1,3],[2,4],[5,6],[5,7],[7,9],[6,8],[8,10],[5,11],[6,12],[11,12],[11,13],[13,15],[12,14],[14,16]];
export const visiblePoint=(p:PosePoint|undefined):p is PosePoint=>!!p&&Number.isFinite(p.x)&&Number.isFinite(p.y)&&(p.confidence??0)>=0.5;

// Legacy frame-local candidates cannot establish a person's temporal fall transition.
export function supportedFall(p:PosePerson):boolean {
 return Number.isInteger(p.track_id)&&Number(p.track_id)>0&&Number(p.track_age)>=8&&p.tracking_method==='conservative_iou_v1'&&p.fall_rule_active===true&&p.fall_state==='POSSIBLE FALL';
}

// Verified API emits score and its identical compatibility alias violence_score.
// Prefer the canonical field; never convert strings, missing values or NaN to zero.
export function fightClassifierScore(result:any):number|null {
 for(const value of [result?.score,result?.violence_score])if(typeof value==='number'&&Number.isFinite(value)&&value>=0&&value<=1)return value;
 return null;
}

export function supportedFightParticipant(p:PosePerson,result:any):boolean {
 const evidence=p.participant_evidence;
 const classifiers=result?.model_results||[result];
 const positive=classifiers.some((r:any)=>['v2','v3'].includes(r.model_version)&&r.candidate_detected===true&&fightClassifierScore(r)!==null);
 return positive&&result?.participant_heuristic?.enabled===true&&result.participant_heuristic.version==='pose-interaction-v1'
  &&p.fight_participant===true&&Number.isInteger(p.interaction_track_id)&&Number(p.interaction_track_id)>0
  &&typeof p.participant_score==='number'&&Number.isFinite(p.participant_score)&&p.participant_score>=0&&p.participant_score<=1
  &&evidence?.heuristic_version==='pose-interaction-v1'&&evidence.pair_track_ids?.length===2
  &&evidence.pair_track_ids.includes(p.interaction_track_id!)&&Number(evidence.interaction_hits)>=3
  &&evidence.pair_track_ids.every(id=>Number(evidence.reciprocal_hits?.[String(id)])>=2);
}
