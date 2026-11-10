import React,{useEffect,useRef,useState,useSyncExternalStore} from 'react';
import {api,post} from '../../lib/api';
import {simulationObservation,type TrackingPlayback} from './trackingPlayback';
import {MotionAnalysisReadout} from './MotionAnalysisReadout';

export function SimulationMotionAnalysis({playback,compact=false}:{playback:TrackingPlayback;compact?:boolean}) {
  const state=useSyncExternalStore(playback.subscribe,playback.getSnapshot);
  const bucket=Math.floor(state.time*2); // Preview at most 2 Hz, never once per render.
  const [error,setError]=useState('');
  const [windowSeconds,setWindowSeconds]=useState<number|null>(null);
  const anchor=useRef(Date.now());
  useEffect(()=>{
    let cancelled=false;
    void api('/sensors/motion/rules').then(result=>{if(!cancelled)setWindowSeconds(Math.max(result.rules.window_seconds,result.rules.proximity_duration_seconds));})
      .catch(e=>{if(!cancelled)setError(String(e));});
    return ()=>{cancelled=true;};
  },[]);
  useEffect(()=>{
    if(state.scenario==='sos'){playback.setMotionAnalysis(null);return;}
    if(windowSeconds==null)return;
    let cancelled=false;
    const end=bucket/2,start=Math.max(0,end-windowSeconds),observations=[];
    const steps=Math.min(120,Math.ceil((end-start)*10));
    // Reconstruct explicitly synthetic history for deterministic seek/pause previews.
    // Backend owns all thresholds; these are sample times, not frontend rule settings.
    for(let i=0;i<=steps;i++){
      const time=Number((steps?start+(end-start)*i/steps:end).toFixed(6));
      observations.push(simulationObservation(state.scenario,time,state.analysisEpoch,anchor.current));
    }
    void post('/sensors/motion/preview',{observations}).then(result=>{
      if(!cancelled&&playback.getSnapshot().analysisEpoch===state.analysisEpoch){playback.setMotionAnalysis(result.analysis);setWindowSeconds(Math.max(result.analysis.rules.window_seconds,result.analysis.rules.proximity_duration_seconds));setError('');}
    }).catch(e=>{if(!cancelled){playback.setMotionAnalysis(null);setError(String(e));}});
    return ()=>{cancelled=true;};
  },[bucket,state.scenario,state.analysisEpoch,windowSeconds,playback]);
  if(compact)return error?<p role="alert" className="text-xs text-rose-700">Backend motion calculation unavailable: {error}</p>:null;
  return <div>{error&&<p role="alert" className="text-xs text-rose-700">Motion analysis unavailable: {error}</p>}
    <MotionAnalysisReadout analysis={state.motionAnalysis} sourceMode="SIMULATION"/>
    <p className="text-[10px] text-slate-500 mt-1">Preview uses generated simulation history and the backend rules. Seeking rebuilds synthetic history; it does not assert a physically observed duration.</p>
  </div>;
}
