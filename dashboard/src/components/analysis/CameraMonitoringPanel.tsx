import {Camera, Play, RotateCcw, Activity} from 'lucide-react';
import './cameraMonitoring.css';
import {sameCamera} from '../../lib/cameraRegistry';
import React, { useEffect, useRef, useState } from 'react';
import { api, API_BASE, AI_BASE, AI_TOKEN } from '../../lib/api';
import { CAMERA_ANALYSIS_MODE, cameraAnalysisLabel } from '../../lib/cameraAnalysisContract';
import { VideoDetectionOverlay } from './VideoDetectionOverlay';
import { DetectionResults } from './DetectionResults';
import { useSafeSenseApp } from '../../context/SafeSenseContext';

class AiError extends Error {
  constructor(message:string,public status:number,public retryAfter=2){super(message);}
}
async function ai(path:string, body?:unknown, signal?:AbortSignal) {
  const started=performance.now();
  const response=await fetch(AI_BASE+path,{method:body ? 'POST':'GET',headers:{'X-SafeSense-Token':AI_TOKEN,'Content-Type':'application/json'},body:body ? JSON.stringify(body):undefined,signal:signal?AbortSignal.any([signal,AbortSignal.timeout(12000)]):AbortSignal.timeout(12000)});
  const bodyText=await response.text(),parseStarted=performance.now();
  const data=JSON.parse(bodyText);
  data.client_timing={request_ms:performance.now()-started,json_parse_ms:performance.now()-parseStarted,decoded_chars:bodyText.length};
  if (!response.ok) throw new AiError(typeof data.detail==='string'?data.detail:data.detail?.message||`HTTP ${response.status}`,response.status,Number(response.headers.get('Retry-After'))||2);
  return data;
}
export function CameraMonitoringPanel() {
  const {selectedZoneId,setSelectedZoneId,setSelectedAlertId,setIsLiveMode,checkFastApiConnection}=useSafeSenseApp();
  const [cameras,setCameras]=useState<any[]>([]);
  const [selected,setSelected]=useState<any>(null);
  const model=CAMERA_ANALYSIS_MODE;
  const [job,setJob]=useState<any>(null),[error,setError]=useState(''),[time,setTime]=useState(0),[playback,setPlayback]=useState('loading');
  const clickedAt=useRef(0);
  const [timing,setTiming]=useState<{videoMs?:number;analysisMs?:number;paintMs?:number;parseMs?:number;requestMs?:number}>({});
  const clientId=useRef(globalThis.crypto?.randomUUID?.()||`camera-${Date.now()}-${Math.random().toString(36).slice(2)}`);
  const submission=useRef<AbortController|null>(null),retryTimer=useRef<ReturnType<typeof setTimeout>|null>(null);
  const handoff=useRef<{time:number;paused:boolean;rate:number}|null>(null);
  const video=useRef<HTMLVideoElement>(null),lastZone=useRef(''),generation=useRef(0);
  useEffect(()=>{
    let alive=true;
    api('/monitoring/cameras').then(c=>{if(alive)setCameras(c);}).catch(e=>{if(alive)setError(String(e));});
    return ()=>{
      alive=false;generation.current++;submission.current?.abort();
      if(retryTimer.current)clearTimeout(retryTimer.current);
      void fetch(AI_BASE+'/monitoring/jobs/release',{method:'POST',keepalive:true,headers:{'X-SafeSense-Token':AI_TOKEN,'Content-Type':'application/json'},body:JSON.stringify({client_id:clientId.current,selection_seq:generation.current})}).catch(()=>{});
    };
  },[]);
  function clearSubmission() {
    submission.current?.abort();
    if(retryTimer.current)clearTimeout(retryTimer.current);
  }
  function run(source:any, cameraId?:string) {
    clearSubmission();
    const current=++generation.current,controller=new AbortController();submission.current=controller;
    setJob({status:'WAITING',model});setError('');
    const camera=cameras.find(c=>c.camera_id===cameraId);
    const request={scenario_id:source.id,zone_id:camera?.zone_id||source.zone_id,model,authorized:true,camera_id:cameraId,client_id:clientId.current,selection_seq:current,force:false};
    let playbackWait=0;
    async function attempt(count:number) {
      if(current!==generation.current || controller.signal.aborted)return;
      if(video.current && video.current.readyState<2 && playbackWait++<20){retryTimer.current=setTimeout(()=>void attempt(count),50);return;}
      try {
        const data=await ai('/monitoring/jobs',request,controller.signal);
        if(current===generation.current){
          if(data.result?.annotated_video_url && !data.result?.pose_frames?.length && video.current && video.current.readyState>=2){const v=video.current;handoff.current={time:v.ended?0:v.currentTime,paused:v.paused&&!v.ended,rate:v.playbackRate};}
          setTiming(t=>({...t,analysisMs:performance.now()-clickedAt.current,parseMs:data.client_timing?.json_parse_ms,requestMs:data.client_timing?.request_ms}));
          setJob(data);setIsLiveMode(true);
          if(data.status==='COMPLETED')void checkFastApiConnection();
        }
      } catch(e) {
        if(current!==generation.current || controller.signal.aborted)return;
        const transient=!(e instanceof AiError)||[429,500,502,503,504].includes(e.status);
        if(transient && count<8){
          setJob({status:'WAITING',model});
          const delay=Math.min(15000,Math.max(e instanceof AiError?e.retryAfter*1000:2000,2000*2**count))+Math.random()*250;
          retryTimer.current=setTimeout(()=>void attempt(count+1),delay);
        }else if(transient){setJob({status:'RETRY_REQUIRED',model});}
        else if(e instanceof AiError && e.status===409){setJob({status:'CANCELLED',model});}
        else {setJob({status:'FAILED',model});setError(String(e));}
      }
    }
    // Camera playback mounts immediately; a brief debounce coalesces rapid clicks.
    retryTimer.current=setTimeout(()=>void attempt(0),80);
  }
  function open(camera:any,analyze=true) {
    // A same-camera click keeps the existing video element, so metadata will not
    // fire again. Resume it explicitly inside the user's click gesture.
    if(selected?.camera_id===camera.camera_id && video.current){
      const element=video.current;
      element.muted=true;
      if(element.readyState>=1)element.currentTime=0;
      void element.play().catch(()=>setPlayback('autoplay blocked; use native controls'));
    }
    if(analyze && selected?.camera_id===camera.camera_id && ['WAITING','QUEUED','RUNNING'].includes(job?.status))return;
    clearSubmission();clickedAt.current=performance.now();setTiming({});
    lastZone.current=camera.zone_id;setSelectedZoneId(camera.zone_id);
    generation.current++;handoff.current=null;setError('');setJob(null);setTime(0);setPlayback('loading');setSelected(camera);
    if(camera.scenario && camera.available){if(analyze)run(camera.scenario,camera.camera_id);}
    else if(camera.stream_configured){if(analyze)run({zone_id:camera.zone_id},camera.camera_id);}
    if(!analyze || !camera.available)void ai('/monitoring/jobs/release',{client_id:clientId.current,selection_seq:generation.current}).catch(()=>{});
  }
  useEffect(()=>{
    // Inspect Zone navigation uses the same cached/automatic Fight + Pose/Fall path as camera clicks.
    if(cameras.length && selectedZoneId && lastZone.current!==selectedZoneId){lastZone.current=selectedZoneId;const camera=cameras.find(c=>c.zone_id===selectedZoneId);if(camera)open(camera,true);}
  },[cameras,selectedZoneId]);
  useEffect(()=>{
    if(!job || !['QUEUED','RUNNING'].includes(job.status)) return;
    let alive=true;
    const current=generation.current;
    const timer=setTimeout(()=>ai('/monitoring/jobs/'+job.id).then(data=>{
      if(alive && current===generation.current){
        if(data.result?.annotated_video_url && !data.result?.pose_frames?.length && !job.result?.annotated_video_url && video.current && video.current.readyState>=2){const v=video.current;handoff.current={time:v.ended?0:v.currentTime,paused:v.paused&&!v.ended,rate:v.playbackRate};}
        if(data.status==='COMPLETED')setTiming(t=>({...t,analysisMs:performance.now()-clickedAt.current,parseMs:data.client_timing?.json_parse_ms,requestMs:data.client_timing?.request_ms}));
        setJob({...data,pollFailures:0});if(data.status==='COMPLETED')void checkFastApiConnection();}
    }).catch(e=>{if(alive && current===generation.current){if((job.pollFailures||0)<8)setJob({...job,pollFailures:(job.pollFailures||0)+1});else setJob({...job,status:'RETRY_REQUIRED'});}}),Math.min(8000,(job.status==='QUEUED'?650:350)*2**(job.pollFailures||0)));
    return ()=>{alive=false;clearTimeout(timer);};
  },[job,checkFastApiConnection]);
  const result=selected && sameCamera(job?.result?.camera_id,selected.camera_id) ? job.result : null;
  const media=selected?.scenario ? `${API_BASE}/monitoring/sources/${selected.scenario.id}?token=${encodeURIComponent(AI_TOKEN)}`:'';
  const annotated=result?.annotated_video_url;
  const dynamicOverlay=!!(media && result?.pose_frames?.length && result?.annotation_alignment?.width && result?.annotation_alignment?.height);
  const source=dynamicOverlay ? media : annotated ? `${AI_BASE}${annotated}?token=${encodeURIComponent(AI_TOKEN)}`:media;
  useEffect(()=>{
    const element=video.current;
    if(!element)return;
    if(!element.requestVideoFrameCallback){
      let active=true,handle=0;
      const tick=()=>{if(!active)return;if(!element.seeking&&element.readyState>=2&&!element.paused)setTime(element.currentTime);handle=requestAnimationFrame(tick);};
      handle=requestAnimationFrame(tick);
      return()=>{active=false;cancelAnimationFrame(handle);};
    }
    let active=true,handle=0;
    const tick:VideoFrameRequestCallback=(_now,metadata)=>{if(active){setTime(metadata.mediaTime);handle=element.requestVideoFrameCallback(tick);}};
    handle=element.requestVideoFrameCallback(tick);
    return()=>{active=false;element.cancelVideoFrameCallback(handle);};
  },[source,selected?.camera_id]);
  useEffect(()=>{
    // Retain the existing automatic replay when short recordings finish before CPU analysis.
    const element=video.current;
    if(dynamicOverlay && element?.ended){element.currentTime=0;setTime(0);void element.play().catch(()=>setPlayback('autoplay blocked; use native controls'));}
  },[dynamicOverlay,job?.id]);
  useEffect(()=>{
    if(!result)return;
    const handle=requestAnimationFrame(()=>setTiming(t=>({...t,paintMs:performance.now()-clickedAt.current})));
    return()=>cancelAnimationFrame(handle);
  },[job?.id,!!result]);
  function metadata(element:HTMLVideoElement){
    element.muted=true;
    const previous=handoff.current;handoff.current=null;
    if(previous){element.currentTime=Math.min(previous.time,element.duration);element.playbackRate=previous.rate;setTime(element.currentTime);if(previous.paused){element.pause();setPlayback('paused');return;}}
    void element.play().catch(()=>setPlayback('autoplay blocked; use native controls'));
  }
  return <section data-testid="camera-monitoring" className="camera-monitoring space-y-3 min-w-0">
    <div className="flex items-center justify-between gap-3"><h2 className="font-bold text-lg text-[#0B1528] flex items-center gap-2"><Camera className="w-5 h-5 text-violet-600"/>Campus Camera Feeds</h2><span className="text-[10px] font-semibold rounded-full px-2.5 py-1 bg-violet-50 text-violet-700 border border-violet-100">{selected?.stream_configured?'Live Camera':'Recorded Video'}</span></div>
    <div aria-label="Camera selector" className="camera-selector">{cameras.map(camera=><button key={camera.camera_id} aria-pressed={selected?.camera_id===camera.camera_id} title={camera.available ? 'Open video and run existing models':'No authorized video source configured'} onClick={()=>open(camera)} className={`camera-selector-card flex items-center gap-2.5 text-left px-3 py-2.5 rounded-xl border transition-colors focus-visible:outline-2 focus-visible:outline-violet-500 ${selected?.camera_id===camera.camera_id ? 'border-violet-500 bg-violet-50 shadow-xs':'border-slate-200 bg-white hover:border-violet-300'}`}>
      <span className={`w-8 h-8 shrink-0 rounded-lg flex items-center justify-center ${selected?.camera_id===camera.camera_id?'bg-violet-600 text-white':'bg-slate-100 text-slate-500'}`}><Camera className="w-4 h-4"/></span><span className="min-w-0"><strong className="block text-xs text-[#0B1528]">{camera.camera_name}</strong><span className="text-[10px] block text-slate-500 mt-0.5">{camera.camera_id}</span></span>
    </button>)}</div>
    {error && <p role="alert" className="text-red-700">{error}</p>}
    {selected && <div className="monitoring-workspace">
      <div className="monitoring-player min-w-0 bg-white border border-slate-200 rounded-2xl overflow-hidden">
        <div className="flex flex-wrap items-center justify-between gap-2 px-3 py-2.5 border-b border-slate-100"><h3 className="font-bold text-sm text-[#0B1528]">{selected.camera_name}</h3><span className="inline-flex items-center gap-1.5 text-[10px] text-slate-500"><Activity className="w-3 h-3 text-violet-500"/>{job?.status || 'Idle'}</span></div>
      {(!media || !selected.available) && !selected.stream_configured && <p>No recording configured.</p>}
      {selected.stream_configured && <><img alt="Authorized live public camera preview" src={`${AI_BASE}/monitoring/live/${selected.camera_id}?token=${encodeURIComponent(AI_TOKEN)}`} className="w-full rounded-xl" onError={()=>setError('Live camera unavailable; check authorized hardware configuration.')} /><p className="text-xs">LIVE CAMERA preview · bounded 120-second session. Analysis uses a separate bounded 10-second sample; continuous real-time detection and pre-trigger buffering are not validated.</p></>}
      {source && selected.available && <><div className="monitoring-video relative w-full aspect-video bg-slate-950 overflow-hidden"><video ref={video} key={selected.camera_id+source} data-camera-id={selected.camera_id} src={source} controls autoPlay muted playsInline preload="auto" className="absolute inset-0 w-full h-full object-contain bg-slate-950 rounded-xl" onLoadedData={()=>setTiming(t=>({...t,videoMs:performance.now()-clickedAt.current}))} onLoadedMetadata={e=>metadata(e.currentTarget)} onSeeked={e=>setTime(e.currentTarget.currentTime)} onTimeUpdate={e=>{if(!e.currentTarget.requestVideoFrameCallback)setTime(e.currentTarget.currentTime);}} onPlay={()=>setPlayback('playing')} onPause={()=>setPlayback('paused')} onWaiting={()=>setPlayback('buffering')} onError={()=>setError('Video unavailable or unsupported. Check registered source and API connection.')} />
      <VideoDetectionOverlay result={result} time={time} cameraId={selected.camera_id}/></div>
      <div className="px-3 py-2.5 flex flex-wrap items-center justify-between gap-2 border-t border-slate-100 text-[11px]">
        <span className="text-slate-500 font-mono">{time.toFixed(2)}s <span className="font-sans">/ {playback}</span></span>
        <button className="inline-flex items-center gap-1.5 font-semibold text-violet-700 hover:text-violet-900" onClick={()=>{if(video.current){video.current.currentTime=0;void video.current.play().catch(()=>setPlayback('autoplay blocked; use Play'));}}}><RotateCcw className="w-3.5 h-3.5"/>Replay</button>
      </div></>}
      <div className="px-3 pb-3 space-y-2">
        {['WAITING','QUEUED','RUNNING'].includes(job?.status)&&<p role="status" className="text-xs text-slate-500">Preparing analysis; playback is available.</p>}
        {job?.status==='RETRY_REQUIRED'&&<p role="status" className="text-xs text-amber-800">AI service unavailable. Select this camera again to retry.</p>}
        {result&&<p data-testid="monitoring-outcome" className={`text-xs font-semibold rounded-lg px-3 py-2 ${result.model_errors?.length?'bg-amber-50 text-amber-800':result.candidate_detected?'bg-red-50 text-red-800':'bg-emerald-50 text-emerald-800'}`}>{result.model_errors?.length?'Analysis incomplete - detector unavailable.':result.candidate_detected?'Candidate detected - human review required.':'No Fight or Fall candidate detected.'}</p>}
        <details className="text-[10px] text-slate-500"><summary className="cursor-pointer">Source & analysis details</summary><div className="mt-2 space-y-2 break-words">
          <p>{selected.camera_id} / {selected.zone_id} / {selected.source_type}</p>
          {result&&<p data-testid="analysis-origin">{cameraAnalysisLabel(job,selected.fight_model)} / {job?.cache_hit||job?.deduplicated?'Cached':'Fresh'} / {result.total_processing_sec}s</p>}
          <div data-testid="monitoring-timing"><p>Video ready: {timing.videoMs?.toFixed(1)??'pending'} ms / Results loaded: {timing.analysisMs?.toFixed(1)??'pending'} ms / Overlay commit: {timing.paintMs?.toFixed(1)??'pending'} ms / JSON parse: {timing.parseMs?.toFixed(1)??'pending'} ms</p>{result&&<p>CPU run: {result.total_processing_sec}s / Queue: {result.queue_delay_sec}s / Cache: {job?.cache_tier||'fresh run'}</p>}</div>
          {selected.scenario&&<p className="break-all">{selected.scenario.dataset} / {selected.scenario.path}</p>}
        </div></details>
      </div>
      </div><DetectionResults key={selected.camera_id+(job?.id||'')} job={job} model={job?.model||model} fightBaseline={selected.fight_model} time={time} annotated={!!annotated} onSeek={position=>{if(video.current){video.current.currentTime=position;setTime(position);}}} onIncident={setSelectedAlertId}/>
    </div>}
    {!selected&&<div className="monitoring-workspace"><div className="aspect-video rounded-2xl bg-[#0B1528] text-slate-300 flex flex-col items-center justify-center gap-3"><Play className="w-8 h-8 text-violet-300"/><p className="text-sm">Select a camera to view its video</p></div><DetectionResults job={null} model={model} time={0} annotated={false} onSeek={()=>{}} onIncident={setSelectedAlertId}/></div>}
  </section>;
}

