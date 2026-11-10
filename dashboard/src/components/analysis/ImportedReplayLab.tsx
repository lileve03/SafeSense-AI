import React,{useEffect,useRef,useState} from 'react';
import {api,post} from '../../lib/api';
import {ImportedReplay,importedFrameAt} from '../../lib/importedReplay';
import {ImportedReplayScene} from './ImportedReplayScene';
import {useSafeSenseApp} from '../../context/SafeSenseContext';

function Lab(){
 const [data,setData]=useState<ImportedReplay|null>(null),[time,setTime]=useState(0),[playing,setPlaying]=useState(false),[busy,setBusy]=useState(false),[message,setMessage]=useState(''),[error,setError]=useState(''),[confirmSos,setConfirmSos]=useState(false);
 const position=useRef(0);position.current=time;
 const session=useRef(crypto.randomUUID());
 const {checkFastApiConnection,setIsLiveMode,setSelectedAlertId}=useSafeSenseApp();
 useEffect(()=>{const controller=new AbortController();api<ImportedReplay>('/testing/imported-lab',{signal:controller.signal}).then(setData).catch(e=>{if(!controller.signal.aborted)setError(String(e));});return()=>controller.abort();},[]);
 useEffect(()=>{
  if(!playing||!data)return;
  const origin=performance.now(),start=position.current;let handle=0;
  const tick=()=>{const next=Math.min(data.duration_sec,start+(performance.now()-origin)/1000);setTime(next);if(next>=data.duration_sec)setPlaying(false);else handle=requestAnimationFrame(tick);};handle=requestAnimationFrame(tick);
  return()=>cancelAnimationFrame(handle);
 },[playing,data]);
 const frame=data?importedFrameAt(data.frames,time):null;
 async function record(kind:'fall'|'sos'){
  if(!data)return;setBusy(true);setError('');
  try{
   const annotation=data.annotations[0];
   const response=await post('/event',{zone:'ZONE_TOILET_BLINDSPOT',type:kind,source:kind==='sos'?'sos_button':'simulation',sensor_modality:kind==='sos'?'sos':'radar',processing_mode:'simulation',source_type:'SIMULATION',is_test:true,event_id:`imported-lab:${session.current}:${kind}`,analysis_run_id:session.current,score:null,model_version:null,evidence_reference:`imported_phase2;synthetic_only;sha256:${data.provenance.frame_sha256};${kind==='fall'?`archive_time=${annotation.time};synthetic_track=${annotation.person_id}`:'explicit_prototype_sos'}`});
   setIsLiveMode(true);await checkFastApiConnection();setMessage(`${response.deduplicated?'Existing':'Saved'} simulation ${kind} test; no hardware inference or emergency dispatch.`);setConfirmSos(false);
   if(response.incident)setSelectedAlertId(response.incident.id);
  }catch(e){setError(String(e));}finally{setBusy(false);}
 }
 const button='px-3 py-2 rounded-lg border border-slate-200 bg-white text-sm text-slate-900 disabled:opacity-50';
 return <div data-testid="imported-replay-lab" className="space-y-4 min-w-0">
  <p className="rounded-lg bg-amber-50 border border-amber-200 text-amber-900 p-3 text-sm font-semibold">SIMULATION ONLY — Imported synthetic archive. No radar/YAMNet inference, physical sensors, measured occupancy or private camera feed.</p>
  {error&&<p role="alert" className="text-red-700 text-sm">{error}</p>}
  {!data&&!error&&<p role="status">Loading validated synthetic frames...</p>}
  {data&&<>
   <ImportedReplayScene frame={frame} time={time}/>
   <div className="flex flex-wrap justify-between gap-3 text-sm"><strong>Replay {time.toFixed(1)} / {data.duration_sec.toFixed(1)} s</strong><span data-testid="imported-track-count">{frame?.tracks.length??0} supplied synthetic tracks</span></div>
   <input aria-label="Imported synthetic replay time" type="range" min={0} max={data.duration_sec} step={.1} value={time} onChange={e=>{setPlaying(false);setTime(Number(e.target.value));}} className="w-full"/>
   <div className="flex flex-wrap gap-2"><button className={button} onClick={()=>{if(time>=data.duration_sec)setTime(0);setPlaying(true);}}>Play synthetic replay</button><button className={button} onClick={()=>setPlaying(false)}>Pause replay</button><button className={button} onClick={()=>{setPlaying(false);setTime(0);}}>Reset replay</button></div>
   <p className="text-xs text-slate-500">Source frame {frame?.time.toFixed(1)} s. Play, seek and reset never create incidents or clear history. Coordinates below are supplied synthetic layout units, not measured meters.</p>
   <div className="overflow-x-auto"><table aria-label="Supplied synthetic tracks" className="w-full text-xs text-left"><thead><tr>{['Synthetic ID','X','Z','Height'].map(label=><th key={label} className="p-2 border-b border-slate-200">{label}</th>)}</tr></thead><tbody>{frame?.tracks.map(track=><tr key={track.id}><td className="p-2">{track.id}</td><td>{track.x}</td><td>{track.z}</td><td>{track.height}</td></tr>)}</tbody></table></div>
   <div className="p-3 rounded-xl border border-slate-200 space-y-3">
    <p className="text-sm">Supplied unverified annotation: suspected fall at {data.annotations[0].time} s, synthetic track {data.annotations[0].person_id}. No model score exists. The MVP's own rules determine any saved test incident's severity.</p>
    <div className="flex flex-wrap gap-2"><button className={button} disabled={busy||time<data.annotations[0].time} onClick={()=>void record('fall')}>Record supplied fall as simulation test</button><button className="px-3 py-2 rounded-lg bg-red-700 text-white text-sm disabled:opacity-50" disabled={busy} onClick={()=>setConfirmSos(true)}>Prototype SOS test</button></div>
    {confirmSos&&<div role="group" aria-label="Confirm imported prototype SOS" className="space-y-2"><p className="text-sm">Create a labeled simulation SOS incident only? No physical button or emergency-service dispatch is involved.</p><button className={button} disabled={busy} onClick={()=>void record('sos')}>Confirm simulation SOS</button><button className={button} disabled={busy} onClick={()=>setConfirmSos(false)}>Cancel SOS test</button></div>}
   </div>
   {message&&<p role="status" className="text-sm text-teal-800">{message}</p>}
   <details className="text-xs text-slate-500"><summary>Archive provenance and limitations</summary><p className="mt-2 break-all">SHA256: {data.provenance.frame_sha256}</p><p className="mt-2">{data.provenance.note}</p><p className="mt-2">Each opening starts a new explicit test session. Repeated recording of the same action in this session is deduplicated; resetting replay preserves saved records. No fake responder ETA or acoustic detection is imported.</p></details>
  </>}
 </div>;
}

export function ImportedReplayLab(){
 const [open,setOpen]=useState(false);
 return <section className="p-5 bg-white border border-slate-200 rounded-2xl space-y-3"><h3 className="font-bold">Imported synthetic sensor replay lab</h3><p className="text-sm text-slate-500">Phase-2 replay data with adapted Three.js room and radar-ring visualization. Kept separate from the operational Digital Twin and real sensor inference.</p><button className="text-sm text-blue-700 underline" onClick={()=>setOpen(value=>!value)}>{open?'Close imported replay lab':'Open imported replay lab'}</button>{open&&<Lab/>}</section>;
}
