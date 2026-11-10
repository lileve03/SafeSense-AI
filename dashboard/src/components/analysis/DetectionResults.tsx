import React, { useState, useEffect } from 'react';
import {IncidentMedia} from '../incidents/IncidentMedia';
import {playbackPoseFrame} from '../../lib/videoDetections';
import { cameraAnalysisVersions } from '../../lib/cameraAnalysisContract';
import { AI_BASE, AI_TOKEN } from '../../lib/api';

type Props = { fightBaseline?: string; job: any; model: string; time: number; annotated: boolean; onSeek: (time: number) => void; onIncident: (id: string) => void };
const link = (url: string) => `${AI_BASE}${url}?token=${encodeURIComponent(AI_TOKEN)}`;
export function DetectionResults({job, model, fightBaseline, time, annotated, onSeek, onIncident}: Props) {
  const [preview,setPreview]=useState<any>(null);
  const [previewError,setPreviewError]=useState('');
  useEffect(()=>{setPreview(null);setPreviewError('');},[job?.camera_id,job?.id]);
  const result=job?.result;
  const outputs=result?.model_results || (result?[result]:[]);
  const expected=cameraAnalysisVersions(job,model,fightBaseline);
  const frame=playbackPoseFrame(result,time);
  const evidence=outputs.flatMap((r:any)=>(r.evidence_media||[]).map((m:any)=>({...m,model:r.model_version,incident_id:r.event_delivery?.incident_id})));
  return <aside aria-label="Detection Results" className="monitoring-results min-w-0 space-y-2">
    <div className="p-3 bg-white rounded-xl border border-slate-200 space-y-2" aria-live="polite">
      <div className="flex flex-wrap justify-between gap-2"><h3 className="font-bold text-sm text-[#0B1528]">AI Detection Results</h3><span className="text-xs text-slate-500">{job?.status||'Not started'}</span></div>
      {expected.map(name=>{
        const r=outputs.find((o:any)=>o.model_version===name);
        const failure=result?.model_errors?.find((f:any)=>f.model===(name.startsWith('yolo')?'pose':name));
        const pose=name.startsWith('yolo');
        return <div key={name} data-model={name} className="border-t border-slate-100 pt-2 text-xs space-y-1">
          <strong className="text-xs">{pose?'Fall':'Fight'} / <span>{name}</span></strong>
          <p>Prediction: {r?(r.candidate_detected?(pose?(r.events?.some((event:any)=>event.type==='possible_fall')?'Possible Fall - binary rule, human review required':'Horizontal posture candidate - transition unconfirmed'):'Possible Physical Conflict - human review required'):(pose?'No fall candidate':'No fight candidate')):failure?'Failed':job?.status||'Not started'}</p>
          <dl className="grid grid-cols-2 gap-x-3 gap-y-1 text-slate-600">
            <dt>{pose?'Fall-rule score':'Classifier score (uncalibrated)'}</dt><dd>{r?.score!=null?r.score.toFixed(6):pose?'N/A - binary rule':'Pending'}</dd>
            <dt>Threshold</dt><dd>{r?.threshold??(pose && result?.person_confidence_threshold!=null?`${result.person_confidence_threshold} (person)`:'N/A')}</dd>
            <dt>Inference</dt><dd>{failure?'FAILED':r?'COMPLETED':job?.status||'IDLE'}</dd>
            <dt>Latency</dt><dd>{r?.inference_time_sec!=null?`${r.inference_time_sec}s`:'Pending'}</dd>
          </dl>
          {!pose&&r?.prediction&&<p>Model label: {r.prediction}</p>}
          {r?.feature_extraction_status&&<details><summary className="cursor-pointer text-slate-500">Analysis details</summary><p>{r.feature_extraction_status}</p></details>}
          {failure&&<p role="alert" className="text-red-700">{failure.error}</p>}
          {r?.event_delivery?.incident_id&&<button className="text-blue-700 underline" onClick={()=>onIncident(r.event_delivery.incident_id)}>Open {name} incident</button>}
          {r?.evidence_error&&<p role="alert" className="text-red-700">{r.evidence_error}</p>}
        </div>;
      })}
      <details className="text-[10px] text-slate-500"><summary className="cursor-pointer">Model limitations</summary>      <p className="text-[10px] leading-relaxed mt-2 text-slate-500">V2/V3 classify the whole video. Red person fight candidates use a separate experimental pose-interaction heuristic; its participant score is not the V2/V3 classifier score or a calibrated probability. Exact classifier fight times are unavailable. YOLO fall signals use an experimental per-track posture rule, not a trained fall classifier. Recording-local IoU tracks reset on missing or ambiguous matches; red fall boxes require an observed upright-to-horizontal transition. Binary rule states have no numeric fall score. Classifier scores are uncalibrated.</p></details>
      {result?.event_delivery?.incident_id&&<button className="text-sm text-blue-700 underline" onClick={()=>onIncident(result.event_delivery.incident_id)}>Review camera incident and evidence</button>}
      {job?.error&&<p role="alert" className="text-red-700 text-sm">{job.error}</p>}
    </div>
    <div data-testid="frame-detections" data-frame-index={frame?.frame_index??''} className="min-w-0 max-h-64 overflow-auto p-3 bg-white border border-slate-200 rounded-xl text-xs space-y-2">
      <h4 className="font-semibold">Playback detections</h4>
      {frame?<><p>Frame {frame.frame_index} / {frame.time_sec.toFixed(3)}s / {frame.persons.length} person detections</p>
        {!frame.persons.length&&<p>No person detected in this frame.</p>}
        {frame.persons.map((person:any,index:number)=><div key={index} className="space-y-1">
          <p>Detection {index+1} (frame-local): confidence {person.confidence.toFixed(3)} / {person.keypoints.filter((p:any)=>p.confidence>=.5).length} keypoints at confidence 0.5 or higher</p>
          <details><summary className="cursor-pointer text-slate-500">Coordinates in source pixels</summary><p>Box: {person.bbox_xyxy.join(', ')}</p><div className="max-h-32 overflow-auto">{person.keypoints.map((point:any,k:number)=><p key={k}>Keypoint {k}: ({point.x}, {point.y}), confidence {point.confidence??'unavailable'}</p>)}</div></details>
        </div>)}</>:<p className="text-slate-500">Frame-aligned person boxes, skeletons and keypoints appear after YOLO finishes. The recording remains playable.</p>}
    </div>
    <div className="p-3 bg-white border border-slate-200 rounded-xl text-xs space-y-2">
      <h4 className="font-semibold">Event Timeline</h4>
      {outputs.filter((r:any)=>['v2','v3'].includes(r.model_version)).map((r:any)=><p key={r.model_version} data-testid="fight-timeline-result">{r.model_version.toUpperCase()} / whole clip (0-{r.video_duration_sec}s) / {r.prediction||'Prediction unavailable'} / score {r.score?.toFixed(6)??'unavailable'}</p>)}
      <div aria-label="Detection timeline" className="flex flex-wrap gap-2">{[...(result?.events||[]),...(result?.participant_events||[])].sort((a:any,b:any)=>a.time_sec-b.time_sec).map((event:any,index:number)=><button key={index} className="border border-blue-200 rounded-lg p-2 text-blue-700 text-left" onClick={()=>onSeek(event.time_sec)}>{event.time_sec}s / {event.type}{event.track_id?` / track ${event.track_id}`:''}{event.track_ids?` / interaction tracks ${event.track_ids.join(', ')} / heuristic ${event.participant_score.toFixed(3)}`:''}</button>)}</div>
      {!result?.events?.length&&!result?.participant_events?.length&&<p className="text-slate-500">No timestamped pose events available. Fight scores apply to the whole clip.</p>}
    </div>
    <div className="min-w-0 p-3 bg-white border border-slate-200 rounded-xl text-xs space-y-2">
      <h4 className="font-semibold">Evidence Preview</h4>
      {!evidence.length&&<p className="text-slate-500">No captured evidence available for this analysis.</p>}
      {evidence.map((item:any)=><div key={item.id} className="border-t border-slate-100 pt-2 space-y-1">
        <p>{item.model} / {item.start_sec}s to {item.end_sec}s / {item.time_scope==='candidate_rule_timestamp'?'Pose candidate window':'Whole analyzed clip; fight time unavailable'}</p>
        <div className="flex flex-wrap gap-3"><button className="text-blue-700 underline" onClick={()=>{setPreviewError('');setPreview(item);}}>Preview {item.model} evidence</button><a href={link(item.url)} target="_blank" rel="noreferrer" className="text-blue-700 underline">Open captured clip</a></div>
      </div>)}
      {previewError&&<p role="alert" className="text-red-700">{previewError}</p>}
      {preview&&<div><div className="flex justify-between"><p>{preview.model} captured evidence</p><button className="text-blue-700 underline" onClick={()=>setPreview(null)}>Close preview</button></div>{preview.incident_id?<IncidentMedia incident={{id:preview.incident_id,zone_id:preview.zone_id}} item={preview}/>:<video key={preview.id} src={link(preview.url)} controls muted playsInline preload="metadata" className="w-full max-h-48 bg-slate-950 rounded-lg" onError={()=>{setPreview(null);setPreviewError('Captured clip is unavailable or expired. Incident metadata remains available.');}}/>}</div>}
    </div>
  </aside>;
}
