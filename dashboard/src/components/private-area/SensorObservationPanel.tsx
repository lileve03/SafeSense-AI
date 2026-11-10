import React, {useEffect, useRef, useState} from 'react';
import {api, post} from '../../lib/api';
import type {MotionAnalysis} from './motionAnalysis';
import {MotionAnalysisReadout} from './MotionAnalysisReadout';
import {RecordedPrivateEvidence} from './RecordedPrivateEvidence';

export type SensorMode = 'SIMULATION' | 'RECORDED_REPLAY' | 'LIVE_HARDWARE';
export interface SensorObservation {
  backend_assessment?:{event_id:string;incident_id?:string|null;level:import('../../types/safesense').RiskLevel;reason:string;status?:string|null};
  hardware_verified?:boolean;
  schema_version?:1;tracking_session_id?:string;timestamp_basis?:'CAPTURE_TIME'|'REPLAY_EVENT_TIME';confidence?:number;
  observation_id: string; source_mode: SensorMode; device_id: string; zone_id: string;
  timestamp: string; data_validity: string; validity_reason?: string;
  coordinate_frame?: 'zone_meters_x_right_y_forward_z_up' | null;
  motion_analysis?:MotionAnalysis;
  tracks?: {id:string; position?:{x:number;y:number;z:number}; velocity?:{x:number;y:number;z:number}; quality?:number}[] | null;
  point_cloud?: {x:number;y:number;z:number}[] | null;
  acoustic_events?: {kind:string;confidence:number}[] | null;
  sos_state: string; radar_event?: string;
  evidence_reference?:string;
}

export function SensorObservationPanel({zoneId,mode,onMode,onObservation,sharedSimulation=false,hideModeSelector=false}:{zoneId:string;mode:SensorMode;onMode:(mode:SensorMode)=>void;onObservation:(o:SensorObservation|null)=>void;sharedSimulation?:boolean;hideModeSelector?:boolean}) {
  const [reading,setReading]=useState<SensorObservation|null>(null);
  const [error,setError]=useState('');
  const [eventId,setEventId]=useState('');
  const generation=useRef(0);
  useEffect(()=>{
    let cancelled=false;
    setReading(null);onObservation(null);
    if(sharedSimulation&&mode==='SIMULATION')return;
    const refresh=async()=>{
      try {
        const result=await api(`/sensors/observations?zone_id=${encodeURIComponent(zoneId)}&source_mode=${mode}`);
        const candidate=result.observation as SensorObservation|null;
        const reading=candidate&&candidate.zone_id===zoneId&&candidate.source_mode===mode
          &&(mode!=='LIVE_HARDWARE'||(candidate.hardware_verified===true&&result.hardware?.verified===true&&result.hardware?.connected===true))?candidate:null;
        if(!cancelled){setReading(reading);onObservation(reading);setError('');}
      } catch(e){if(!cancelled){setError(String(e));setReading(null);onObservation(null);}}
    };
    void refresh();const timer=window.setInterval(refresh,3000);
    return ()=>{cancelled=true;generation.current++;window.clearInterval(timer);};
  },[zoneId,mode,onObservation,sharedSimulation]);
  const replay=async()=>{
    const requestGeneration=generation.current;
    try {const result=await post('/sensors/observations/replay',{event_id:eventId});if(requestGeneration===generation.current){setReading(result.observation);onObservation(result.observation);setError('');}}
    catch(e){if(requestGeneration===generation.current)setError(String(e));}
  };
  const simulate=async()=>{
    const requestGeneration=generation.current;
    try {
      const result=await post('/sensors/observations',{source_mode:'SIMULATION',device_id:'simulated-radar-acoustic',zone_id:zoneId,
        timestamp:new Date().toISOString(),data_validity:'VALID',radar_event:'fall',
        acoustic_events:[{kind:'scream',confidence:1}],sos_state:'INACTIVE',
        validity_reason:'Explicit synthetic fusion test; no measured tracks or positions'});
      if(requestGeneration===generation.current){setReading(result.observation);onObservation(result.observation);setError('');}
    }catch(e){if(requestGeneration===generation.current)setError(String(e));}
  };
  if(sharedSimulation&&mode==='SIMULATION'&&hideModeSelector)return null;
  return <section className="p-4 rounded-xl border border-slate-200 bg-white space-y-2 text-xs" data-testid="normalized-sensor-panel">
    <h3 className="font-bold">Sensor observation interface</h3>
    {!hideModeSelector&&<label>Source mode <select className="border rounded p-1" value={mode} onChange={e=>onMode(e.target.value as SensorMode)}>
      <option value="SIMULATION">SIMULATION</option><option value="RECORDED_REPLAY">RECORDED_REPLAY</option><option value="LIVE_HARDWARE">LIVE_HARDWARE</option>
    </select></label>}
    <p className="font-bold text-amber-700">Hardware Disconnected</p>
    <p>No physical device, heartbeat or calibration has been verified.</p>
    {mode==='SIMULATION'&&!sharedSimulation&&<button className="underline" onClick={simulate}>Submit simulated fall + scream observation</button>}
    {mode==='RECORDED_REPLAY'&&<div className="flex gap-2"><input aria-label="Recorded sensor event ID" className="border rounded p-1 min-w-0 flex-1" placeholder="Persisted radar/acoustic event ID" value={eventId} onChange={e=>setEventId(e.target.value)}/><button className="underline" onClick={replay} disabled={!eventId}>Load recorded observation</button></div>}
    {error&&<p role="alert">{error}</p>}
    {!(sharedSimulation&&mode==='SIMULATION')&&(reading?<><p>{reading.device_id} · {reading.data_validity} · {reading.timestamp}</p><p>{reading.validity_reason}</p>
      <p>Tracks: {reading.tracks==null?'Unavailable':reading.tracks.length+' anonymous tracks (not a verified people count)'} · Point cloud: {reading.point_cloud==null?'Unavailable':reading.point_cloud.length+' points'} · Nearest distance: {reading.motion_analysis?.nearest_pair?`${reading.motion_analysis.nearest_pair.distance_m.toFixed(2)}m (track points)`:'Unavailable'}</p>
      <p>Radar: {reading.radar_event||'Unavailable'} · Acoustic: {reading.acoustic_events?.map(e=>e.kind).join(', ')||'Unavailable'} · SOS: {reading.sos_state}</p></>:<p>No observation available for this mode. Count, positions and distance unavailable.</p>)}
    {mode!=='SIMULATION'&&<MotionAnalysisReadout analysis={reading?.motion_analysis} sourceMode={mode}/>}
    {mode==='RECORDED_REPLAY'&&<RecordedPrivateEvidence/>}
  </section>;
}
