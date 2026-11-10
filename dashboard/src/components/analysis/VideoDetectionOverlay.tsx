import {sameCamera} from '../../lib/cameraRegistry';
import React from 'react';
import {playbackPoseFrame,poseEdges,visiblePoint,supportedFall,fightClassifierScore,supportedFightParticipant} from '../../lib/videoDetections';
export function VideoDetectionOverlay({result,time,cameraId}:{result:any;time:number;cameraId:string}){
 const valid=sameCamera(result?.camera_id,cameraId);
 const frame=valid?playbackPoseFrame(result,time):null;
 const alignment=result?.annotation_alignment;
 const outputs=valid?(result.model_results||[result]):[];
 const fights=outputs.filter((r:any)=>['v2','v3'].includes(r.model_version));
 return <div data-testid="video-detection-overlay" data-camera-id={cameraId} data-frame-index={frame?.frame_index??''} className="absolute inset-0 pointer-events-none">
 {frame&&alignment?.width>0&&alignment?.height>0&&<svg role="img" aria-label="Actual person boxes and pose skeletons" viewBox={`0 0 ${alignment.width} ${alignment.height}`} preserveAspectRatio="xMidYMid meet" className="absolute inset-0 w-full h-full" data-testid="pose-overlay">
 {frame.persons.map((p,index)=>{
 const [x1,y1,x2,y2]=p.bbox_xyxy;
 if(![x1,y1,x2,y2].every(Number.isFinite)||x2<=x1||y2<=y1)return null;
 const fall=supportedFall(p);
 const participant=supportedFightParticipant(p,result);
 const color=fall||participant?'#ef4444':'#22d3ee';
 const text=`${participant?`POSSIBLE FIGHT | participant score: ${p.participant_score!.toFixed(3)} (heuristic)${fall?' | POSSIBLE FALL (binary ACTIVE)':''}`:fall?'POSSIBLE FALL | binary rule ACTIVE':'Person'} | detector ${(p.confidence*100).toFixed(1)}%${participant?` | interaction track ${p.interaction_track_id}`:p.track_id?` | track ${p.track_id}`:''}`;
 const labels=participant?['POSSIBLE FIGHT',`participant score: ${p.participant_score!.toFixed(3)} | heuristic`,...(fall?['POSSIBLE FALL | binary ACTIVE']:[])]:[text];
 const font=Math.max(12,alignment.width/65),lineHeight=font+3,labelHeight=labels.length*lineHeight+4,boxY=Math.max(labelHeight,y1);
 return <g key={index} data-person-index={index} data-fall-candidate={fall} data-fight-participant={participant} data-interaction-track-id={p.interaction_track_id} data-participant-score={participant?p.participant_score:undefined} data-track-id={p.track_id}>
 <rect data-testid="person-box" x={x1} y={y1} width={x2-x1} height={y2-y1} fill="none" stroke={color} strokeWidth={3} vectorEffect="non-scaling-stroke"/>
 {poseEdges.map(([a,b])=>visiblePoint(p.keypoints[a])&&visiblePoint(p.keypoints[b])?<line key={`${a}-${b}`} data-testid="pose-bone" x1={p.keypoints[a].x} y1={p.keypoints[a].y} x2={p.keypoints[b].x} y2={p.keypoints[b].y} stroke={color} strokeWidth={2} vectorEffect="non-scaling-stroke"/>:null)}
 {p.keypoints.map((k,i)=>visiblePoint(k)?<circle key={i} cx={k.x} cy={k.y} r={Math.max(2,alignment.width/320)} fill="#f8fafc" stroke={color}/>:null)}
 <rect x={x1} y={boxY-labelHeight} width={Math.min(alignment.width-x1,Math.max(...labels.map(label=>label.length))*font*.57+8)} height={labelHeight} fill="#0f172a" opacity={0.95}/>
 {labels.map((label,i)=><text key={i} x={x1+3} y={boxY-labelHeight+font+2+i*lineHeight} fill={color} fontSize={font} fontWeight="bold">{label}</text>)}
 </g>;})}
 </svg>}
 {!!fights.length&&<div data-testid="fight-video-overlay" className="absolute top-2 left-2 right-2 flex flex-wrap gap-1 text-[10px] sm:text-xs">{fights.map((r:any)=><span key={r.model_version} className={`px-2 py-1 rounded-md text-white shadow ${r.candidate_detected?'bg-red-900/95':'bg-slate-900/90'}`}>{r.model_version.toUpperCase()} · {r.candidate_detected?'POSSIBLE FIGHT':(r.prediction?.replaceAll('_',' ')||'No conflict flag')} · classifier score {fightClassifierScore(r)!==null?fightClassifierScore(r)!.toFixed(4):'unavailable'} | uncalibrated · whole clip</span>)}</div>}
 </div>;
}
