import React,{useEffect,useRef,useState} from 'react';
import {api,post} from '../../lib/api';
import {useSafeSenseApp} from '../../context/SafeSenseContext';

const INPUTS=['radar_raw_normal','radar_raw_fall','acoustic_background','acoustic_scream'];
export function RecordedPrivateEvidence(){
  const {setIsLiveMode,checkFastApiConnection,setSelectedAlertId}=useSafeSenseApp();
  const [sources,setSources]=useState<any[]>([]),[selected,setSelected]=useState('radar_raw_fall');
  const [run,setRun]=useState<any>(null),[error,setError]=useState(''),[busy,setBusy]=useState(false);
  const active=useRef(true);
  useEffect(()=>{active.current=true;void api('/testing/scenarios').then(rows=>{if(active.current)setSources(rows.filter((s:any)=>INPUTS.includes(s.id)));}).catch(e=>{if(active.current)setError(String(e));});return()=>{active.current=false;};},[]);
  useEffect(()=>{
    if(!run||!['QUEUED','RUNNING'].includes(run.status))return;
    let cancelled=false;
    const timer=window.setInterval(()=>{void api('/testing/runs/'+run.id).then(value=>{
      if(!cancelled){setRun(value);if(!['QUEUED','RUNNING'].includes(value.status))void checkFastApiConnection();}
    }).catch(e=>{if(!cancelled)setError(String(e));});},1000);
    return()=>{cancelled=true;window.clearInterval(timer);};
  },[run?.id,run?.status,checkFastApiConnection]);
  const source=sources.find(s=>s.id===selected),result=run?.result;
  async function execute(){
    if(!source||busy)return;setBusy(true);setError('');setIsLiveMode(true);
    try{setRun(await post('/testing/runs',{scenario_id:source.id,model:source.default_model,authorized:true}));}
    catch(e){setError(String(e));}finally{setBusy(false);}
  }
  return <section data-testid="recorded-private-evidence" className="rounded-xl border bg-white p-3 space-y-2 text-xs">
    <h3 className="font-bold">RECORDED REPLAY · Actual radar / YAMNet inference</h3>
    <p>Registered research recordings only. Each model result is independent evidence, not a synchronized fall-plus-impact recording. The available YAMNet positive sample is a scream, not an impact. No positions, distances, private video, microphone or speech capture are fabricated.</p>
    <label>Registered recording <select aria-label="Recorded private evidence input" disabled={busy||['QUEUED','RUNNING'].includes(run?.status)} className="border p-1 rounded max-w-full" value={selected} onChange={e=>{setSelected(e.target.value);setRun(null);setError('');}}>{sources.map(s=><option key={s.id} value={s.id}>{s.name}</option>)}</select></label>
    <button className="border p-2 rounded disabled:opacity-50" disabled={busy||!source?.ready||['QUEUED','RUNNING'].includes(run?.status)} onClick={execute}>Run actual registered inference</button>
    {source&&!source.ready&&<p>{source.unavailable_reason}</p>}{error&&<p role="alert">{error}</p>}
    {run&&<div data-testid="recorded-evidence-result" className="space-y-1"><p>{run.scenario_name} · {run.status}</p>
      {run.error&&<p role="alert">{run.error}</p>}
      {result&&<><p>RECORDED model: {result.model_version} · Actual model score: {result.score==null?'Unavailable':result.score.toFixed(6)} · Candidate: {String(result.candidate_detected)} · origin: {result.output_origin}</p>
        <p className="break-all">Input checksum: {result.input_sha256}</p><p>Class score is not calibrated danger probability. Spatial tracks, distances and synchronized sensor fusion are unavailable for these recordings.</p>
        {result.event_delivery?.incident_id&&<button className="underline" onClick={()=>{setIsLiveMode(true);setSelectedAlertId(result.event_delivery.incident_id);}}>Open recorded-evidence test incident</button>}</>}
    </div>}
  </section>;
}
