import {IncidentTime} from '../../lib/incidentTime';
import React,{useEffect,useRef,useState} from 'react';
import {VideoDetectionOverlay} from '../analysis/VideoDetectionOverlay';
import {AI_BASE,AI_TOKEN,api} from '../../lib/api';

export function IncidentMedia({incident,item}:{incident:any;item:any}){
  const [metadata,setMetadata]=useState<any>(null),[error,setError]=useState(''),[variant,setVariant]=useState('original');
  const [time,setTime]=useState(0),[playback,setPlayback]=useState('loading'),[frameReady,setFrameReady]=useState(false);
  const video=useRef<HTMLVideoElement>(null);
  const base=`${AI_BASE}/monitoring/incidents/${encodeURIComponent(incident.id)}/evidence/${encodeURIComponent(item.id)}`;
  useEffect(()=>{
    const controller=new AbortController();let alive=true;
    setMetadata(null);setError('');setTime(0);setPlayback('loading');setFrameReady(false);
    fetch(base+'/metadata',{headers:{'X-SafeSense-Token':AI_TOKEN},signal:controller.signal}).then(async response=>{
      const data=await response.json();
      if(!response.ok)throw new Error(data.detail||`HTTP ${response.status}`);
      if(data.incident_id!==incident.id || data.id!==item.id || data.zone_id!==incident.zone_id || data.analysis_id!==item.analysis_id)throw new Error('Evidence identity does not match the selected incident.');
      await api('/monitoring/cameras',{signal:controller.signal});
      if(alive){setMetadata(data);setVariant(data.overlay_result?'original':data.annotated_available?'annotated':'original');}
    }).catch(e=>{if(alive)setError(String(e));});
    return()=>{alive=false;controller.abort();};
  },[base,incident.id,item.id]);
  useEffect(()=>{
    const element=video.current;
    if(!element)return;
    let handle=0,alive=true;
    const tick=(_:number,frame:VideoFrameCallbackMetadata)=>{if(!alive)return;setTime(frame.mediaTime);setFrameReady(true);handle=element.requestVideoFrameCallback(tick);};
    if(element.requestVideoFrameCallback)handle=element.requestVideoFrameCallback(tick);
    return()=>{alive=false;if(handle)element.cancelVideoFrameCallback(handle);};
  },[metadata,variant]);
  const available=metadata && (variant==='annotated'?metadata.annotated_available:metadata.original_available);
  const src=`${base}?variant=${variant}&token=${encodeURIComponent(AI_TOKEN)}`;
  const score=metadata?.score;
  return <article data-testid="incident-media" data-incident-id={incident.id} data-evidence-id={item.id} className="space-y-3 min-w-0">
    {error&&<p role="status" className="text-amber-800">Evidence unavailable: {error}. It may have expired, been deleted, or the media service may be offline.</p>}
    {!metadata&&!error&&<p role="status" className="text-slate-500">Loading the selected incident's retained evidence...</p>}
    {metadata&&<>
      <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-xs break-words">
        <div><dt className="text-slate-500">Camera ID</dt><dd>{metadata.camera_id||'Not captured'}</dd></div>
        <div><dt className="text-slate-500">Model version</dt><dd>{metadata.model_version||'Not recorded'}</dd></div>
        <div><dt className="text-slate-500">Prediction</dt><dd>{metadata.prediction?.replaceAll('_',' ')||'Not recorded'}</dd></div>
        <div><dt className="text-slate-500">Score / threshold</dt><dd>{score!=null?Number(score).toFixed(6):'N/A - no trained classifier score'} / {metadata.threshold??'N/A'}</dd></div>
        <div><dt className="text-slate-500">Source type</dt><dd>{metadata.source_type||'Not recorded'} / {metadata.processing_mode}</dd></div>
        <div><dt className="text-slate-500">Evidence duration</dt><dd>{metadata.duration_sec}s</dd></div>
        <div className="sm:col-span-2"><dt className="text-slate-500">Detection recorded at</dt><dd><IncidentTime value={metadata.observation_timestamp}/></dd></div>
      </dl>
      {available?<div className="relative"><video ref={video} key={src} data-evidence-id={item.id} data-variant={variant} src={src} controls autoPlay muted playsInline preload="auto" className="w-full aspect-video max-h-96 object-contain rounded-xl bg-slate-950"
        onLoadedMetadata={e=>{e.currentTarget.muted=true;void e.currentTarget.play().catch(()=>setPlayback('Autoplay blocked; use native controls.'));}}
        onLoadedData={()=>setFrameReady(true)} onSeeking={()=>setFrameReady(false)} onSeeked={e=>{setTime(e.currentTarget.currentTime);setFrameReady(true);}} onTimeUpdate={e=>{if(!e.currentTarget.requestVideoFrameCallback)setTime(e.currentTarget.currentTime);}} onPlay={()=>setPlayback('playing')} onPause={()=>setPlayback('paused')}
        onError={()=>setError('The retained clip could not be loaded or decoded')}/>{variant==='original'&&metadata.overlay_result&&<VideoDetectionOverlay result={metadata.overlay_result} time={frameReady?time+metadata.start_sec:NaN} cameraId={metadata.camera_id}/>}</div>:<p role="status" className="text-amber-800">Evidence unavailable: no retained clip exists. Incident metadata remains available.</p>}
      {available&&<div className="flex flex-wrap gap-x-4 gap-y-2 items-center text-xs">
        <span>Evidence time {time.toFixed(2)}s / {playback}</span>
        <button className="text-blue-700 underline" onClick={()=>{if(video.current){video.current.currentTime=0;void video.current.play().catch(()=>setPlayback('Use native controls to play.'));}}}>Replay evidence</button>
        <a href={src+'&download=true'} className="text-blue-700 underline" download>Download authorized evidence</a>
        {metadata.original_available&&metadata.annotated_available&&<button className="text-blue-700 underline" onClick={()=>{setVariant(variant==='annotated'?'original':'annotated');setTime(0);setError('');}}>{variant==='annotated'?'Show original clip':'Show annotated clip'}</button>}
      </div>}
      <p className="text-xs text-slate-500">{variant==='annotated'?'Saved annotated evidence / actual YOLO detections. Recording-local tracks where supported; no fighter identification.':metadata.overlay_result?'Matching retained analysis overlays / recorded inference, not live. Binary fall rule; participant scores are a separate uncalibrated pose heuristic, not classifier scores.':metadata.annotation_note}</p>
      <p className="text-xs text-slate-500">Source interval {metadata.start_sec}s to {metadata.end_sec}s. {metadata.time_scope==='candidate_rule_timestamp'?`Experimental pose-rule signal at source time ${metadata.event_time_sec}s.`:'Whole-video classification; any interaction timestamps and person candidates come from the separate pose heuristic, not classifier localization.'} Retention: {metadata.retention_days} days.</p>
    </>}
  </article>;
}
