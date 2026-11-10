import React,{useEffect,useRef,useState} from 'react';
import {api,post} from '../../lib/api';
import {sosNotificationOutcome} from '../../lib/sosNotificationOutcome';
import {useSafeSenseApp} from '../../context/SafeSenseContext';
export type SimTrack={id:string;x:number;y:number;height:number;vx:number;reversals_4s:number;repeated_motion:boolean;possible_fall:boolean};
export type SimFrame={time_sec:number;source:'SIMULATION';tracks:SimTrack[];count:number;pairs:{ids:string[];distance:number;close:boolean}[];acoustic_distress:boolean;sos_active:boolean;level:'LOW'|'OBSERVE'|'HIGH'|'CRITICAL'};
export function RadarTrackingSimulation({onFrame}:{onFrame:(frame:SimFrame|null)=>void}){
 const {checkFastApiConnection,setIsLiveMode,setSelectedAlertId}=useSafeSenseApp();
 const [open,setOpen]=useState(false),[data,setData]=useState<{frames:SimFrame[];duration_sec:number}|null>(null),[time,setTime]=useState(0),[playing,setPlaying]=useState(false),[busy,setBusy]=useState(false),[error,setError]=useState(''),[notice,setNotice]=useState('');
 const session=useRef(crypto.randomUUID()),sending=useRef(false),position=useRef(0);position.current=time;
 const automatic=useRef(new Set<string>());
 const frame=data?.frames[Math.min(data.frames.length-1,Math.floor(time*10+1e-6))]||null;
 useEffect(()=>{if(!open)return;const c=new AbortController();api('/testing/radar-simulation',{signal:c.signal}).then(setData).catch(e=>{if(!c.signal.aborted)setError(String(e));});return()=>c.abort();},[open]);
 useEffect(()=>{onFrame(open?frame:null);},[open,frame,onFrame]);
 useEffect(()=>{if(!playing||!data)return;const started=performance.now(),origin=position.current;let timer=setInterval(()=>{const next=Math.min(data.duration_sec,origin+(performance.now()-started)/1000);setTime(next);if(next>=data.duration_sec)setPlaying(false);},100);return()=>clearInterval(timer);},[playing,data]);
 useEffect(()=>{
  if(!playing||!frame||busy)return;
  const kind=frame.sos_active?'sos':frame.acoustic_distress&&frame.tracks.some(t=>t.possible_fall)?'fusion':null;
  if(kind&&!automatic.current.has(kind)){automatic.current.add(kind);void record(kind,true);}
 },[playing,frame,busy]);
 async function record(kind:'radar'|'fusion'|'sos',automaticSend=false){
  if(sending.current||!frame)return;sending.current=true;setBusy(true);setError('');
  try{const r=await post('/testing/radar-simulation/events',{session_id:session.current,time_sec:frame.time_sec,kind});setIsLiveMode(true);await checkFastApiConnection();if(r.incident){if(!automaticSend)setSelectedAlertId(r.incident.id);if(kind==='sos')setNotice((await sosNotificationOutcome(r.incident.id)).message);else setNotice('Simulated observation saved. Telegram status is available in incident details.');}}
  catch(e){setError(String(e));}finally{sending.current=false;setBusy(false);}
 }
 return <section className="p-4 rounded-xl border border-amber-200 bg-white space-y-3" data-testid="radar-tracking-simulation">
  <h3 className="font-bold text-sm">Multi-person radar workflow demonstration</h3>
  <p className="text-xs text-slate-600">Real recordings contain points, not verified person tracks. Occupancy, identities, room coordinates and distances remain unavailable for real sensors.</p>
  <button className="text-blue-700 underline text-sm" onClick={()=>{setOpen(v=>!v);setPlaying(false);}}>{open?'Close isolated tracking simulation':'Open isolated tracking simulation'}</button>
  {notice&&<p role="status" className="text-sm text-blue-800">{notice}</p>}
  {error&&<p role="alert" className="text-red-700 text-sm">{error}</p>}
  {open&&<><p className="p-2 rounded bg-amber-50 text-amber-900 text-xs font-bold">SIMULATION ONLY: scripted tracks and synthetic meters. Not real radar people detection or measured distances.</p>
   {frame&&<><div className="flex flex-wrap gap-4 text-xs"><strong>Simulated count: {frame.count}</strong><span>Simulated rule status: {frame.level}</span><span>Offset: {frame.time_sec.toFixed(1)}s</span></div>
    <input aria-label="Radar tracking simulation time" className="w-full" type="range" min="0" max={24} step="0.1" value={time} onChange={e=>{setPlaying(false);setTime(Number(e.target.value));}}/>
    <div className="flex flex-wrap gap-2 text-xs"><button className="border rounded p-2" onClick={()=>{if(time>=24)setTime(0);setPlaying(v=>!v);}}>{playing?'Pause tracking simulation':'Play tracking simulation'}</button><button className="border rounded p-2" onClick={()=>{setPlaying(false);setTime(0);}}>Reset tracking simulation</button><button className="border rounded p-2" onClick={()=>{setPlaying(false);setTime(3.5);}}>Repeated motion example</button><button className="border rounded p-2" onClick={()=>{setPlaying(false);setTime(10.5);}}>Fall + distress example</button></div>
    <div className="overflow-x-auto"><table className="w-full text-xs text-left" aria-label="Synthetic anonymous tracks"><thead><tr>{['Synthetic ID','X / Y / height','X velocity','Reversals (4s)','Rule'].map(x=><th key={x} className="p-1">{x}</th>)}</tr></thead><tbody>{frame.tracks.map(t=><tr key={t.id}><td className="p-1">{t.id}</td><td>{t.x.toFixed(2)} / {t.y.toFixed(2)} / {t.height.toFixed(2)}</td><td>{t.vx.toFixed(2)}</td><td>{t.reversals_4s}</td><td>{t.possible_fall?'Possible fall':t.repeated_motion?'Repeated motion':'No rule flag'}</td></tr>)}</tbody></table></div>
    <p className="text-xs">Synthetic pair distances: {frame.pairs.map(p=>`${p.ids.join(' / ')}: ${p.distance.toFixed(2)}m${p.close?' (close)':''}`).join('; ')}</p>
    <p className="text-xs">Scripted acoustic distress: {frame.acoustic_distress?'active':'inactive'}; scripted SOS: {frame.sos_active?'active':'inactive'}. Rules are demonstrations, not calibrated recognition scores.</p>
    <div className="flex flex-wrap gap-2 text-xs"><button disabled={busy} className="border rounded p-2" onClick={()=>record('radar')}>Record simulated radar observation</button><button disabled={busy||!frame.acoustic_distress||!frame.tracks.some(t=>t.possible_fall)} className="border rounded p-2 disabled:opacity-50" onClick={()=>record('fusion')}>Record simulated fall + acoustic fusion</button><button disabled={busy} className="bg-red-700 text-white rounded p-2" onClick={()=>record('sos')}>Record explicit simulation SOS</button></div>
    <p className="text-xs text-slate-500">Playback automatically records fall + distress and SOS alerts once per session and requests Telegram notifications. Seek and reset only change the preview. Explicit record actions deduplicate within this simulation session. No cameras, microphone or physical hardware are activated.</p>
   </>}
  </>}
 </section>;
}
