import React,{useEffect,useRef,useState} from 'react';
import {api,post,API_BASE,AI_BASE,AI_TOKEN} from '../../lib/api';
import {useSafeSenseApp} from '../../context/SafeSenseContext';

export function ScenarioTestingLibrary(){
  const {checkFastApiConnection,setIsLiveMode,setSelectedAlertId,setSelectedZoneId,setActivePage}=useSafeSenseApp();
  const [catalog,setCatalog]=useState<any[]>([]),[history,setHistory]=useState<any[]>([]),[selected,setSelected]=useState('conflict');
  const [model,setModel]=useState('all'),[authorized,setAuthorized]=useState(false),[run,setRun]=useState<any>(null),[error,setError]=useState('');
  const generation=useRef(0);
  useEffect(()=>{let alive=true;Promise.all([api('/testing/scenarios'),api('/testing/runs')]).then(([sources,runs])=>{if(alive){setCatalog(sources);setHistory(runs);}}).catch(e=>{if(alive)setError(String(e));});return()=>{alive=false;generation.current++;};},[]);
  useEffect(()=>{
    if(!run||!['QUEUED','RUNNING'].includes(run.status))return;
    let alive=true;const timer=setTimeout(()=>api('/testing/runs/'+run.id).then(async r=>{if(alive){setRun(r);if(!['QUEUED','RUNNING'].includes(r.status)){await checkFastApiConnection();if(alive)setHistory(await api('/testing/runs'));}}}).catch(e=>{if(alive){setError('Run status unavailable; inspect run history after the API recovers. '+String(e));setRun({...run,status:'STATUS_UNAVAILABLE'});}}),1200);
    return()=>{alive=false;clearTimeout(timer);};
  },[run,checkFastApiConnection]);
  const source=catalog.find(s=>s.id===selected);
  const fresh=catalog.filter(s=>s.execution_kind==='fresh_inference');
  function choose(id:string){generation.current++;const next=catalog.find(s=>s.id===id);setSelected(id);setModel(next?.default_model||'all');setRun(null);setError('');}
  async function start(){const current=++generation.current;setError('');try{const result=await post('/testing/runs',{scenario_id:selected,model,authorized});if(current===generation.current){setRun(result);setIsLiveMode(true);}}catch(e){if(current===generation.current)setError(String(e));}}
  async function inspect(id:string){const current=++generation.current;try{const result=await api('/testing/runs/'+id);if(current===generation.current){setSelected(result.scenario_id);setModel(result.model);setRun(result);}}catch(e){setError(String(e));}}
  const result=run?.result;
  const outputs=result?.model_results|| (result?[result]:[]);
  const busy=run&&['QUEUED','RUNNING'].includes(run.status);
  const deliveries=outputs.map((r:any)=>r.event_delivery).filter((d:any)=>d?.incident_id);
  const incidents=[...new Set<string>(deliveries.map((d:any)=>d.incident_id))];
  const media=result?.annotated_video_url ? `${AI_BASE}${result.annotated_video_url}?token=${encodeURIComponent(AI_TOKEN)}` : source?.input_type==='video'?`${API_BASE}/monitoring/sources/${source.id}?token=${encodeURIComponent(AI_TOKEN)}`:'';
  return <section id="scenario-testing" data-testid="scenario-testing-library" className="p-5 rounded-2xl bg-white border border-slate-200 space-y-4">
    <h2 className="font-bold text-xl">Scenario Testing Library</h2>
    <p className="text-sm text-slate-500">Actual local research inputs and fresh inference. Saved predictions and simulated tests remain separate below. Dataset labels never force the model output; CPU processing is offline.</p>
    {error&&<p role="alert" className="text-red-700">{error}</p>}
    <div className="flex flex-wrap gap-3"><label>Recording <select aria-label="Scenario recording" className="border border-slate-200 rounded p-2 max-w-full" value={selected} onChange={e=>choose(e.target.value)}>{fresh.map(s=><option key={s.id} value={s.id}>{s.name} · {s.ready?'ready':'unavailable'}</option>)}</select></label><label>Model <select aria-label="Scenario inference model" className="border border-slate-200 rounded p-2" value={model} onChange={e=>{generation.current++;setModel(e.target.value);setRun(null);}}>{source?.allowed_models.map((m:string)=><option key={m}>{m}</option>)}</select></label></div>
    {source&&<div className="p-3 rounded-xl bg-slate-50 text-sm space-y-1"><p>{source.dataset} · {source.source_type} · OFFLINE ANALYSIS</p><p>Dataset label: {source.ground_truth} · Demo zone: {source.zone_id}</p><p className="text-xs break-all">Actual input: {source.path}</p><p className="text-xs">{source.limitations}</p>{!source.ready&&<p role="alert" className="text-red-700">{source.unavailable_reason}. No simulated fallback.</p>}</div>}
    {media&&<div><p className="text-xs">{result?.annotated_video_url?'COMPLETED REAL POSE ANALYSIS · synchronized recorded overlay':'RECORDED RESEARCH VIDEO · source preview, not a live camera'}</p><video key={media} src={media} controls muted playsInline preload="metadata" className="w-full max-h-80 bg-slate-950 rounded-xl"/></div>}
    {source?.input_type==='audio_sample'&&<p className="text-xs">Existing research waveform is analyzed server-side only. No microphone, audio playback, speech transcription or new private-area recording.</p>}
    <label className="flex gap-2 items-center text-sm"><input aria-label="Authorize scenario research input" type="checkbox" checked={authorized} onChange={e=>setAuthorized(e.target.checked)}/>I am authorized to use these existing research recordings for offline testing.</label>
    <button disabled={!source?.ready||!authorized||busy} className="px-4 py-2 bg-blue-600 text-white rounded-xl disabled:opacity-50" onClick={start}>{busy?'Running actual inference…':'Run actual inference'}</button>
    {run&&<div aria-live="polite" className="space-y-3 text-sm"><p>Run #{run.id.slice(0,8)} · {run.status} · {run.model} · {run.wall_time_sec??'pending'} seconds</p>{run.error&&<p role="alert" className="text-red-700">{run.error}</p>}
      {outputs.map((r:any,index:number)=><div key={r.analysis_id||index} className="p-3 rounded-xl border border-slate-200 space-y-1"><h3 className="font-bold">{r.model_version}</h3><p>{r.candidate_detected?'Model candidate — human review required':'No candidate flagged'} · {r.score==null?'No trained fall-classifier score':`Actual score ${r.score.toFixed(6)} · threshold ${r.threshold}`}</p><p>{r.note}</p>{r.input_sha256&&<p className="text-xs break-all">Fresh input SHA256: {r.input_sha256}</p>}{r.n_points!=null&&<p>Radar points: {r.n_points} · Frames: {r.n_frames} · People count/positions/distances: unavailable</p>}{r.audio_duration_sec!=null&&<p>Research audio: {r.audio_duration_sec}s · {r.original_sample_rate} Hz · target: {r.target} · no speech analysis</p>}{r.training_subject_excluded&&<p>LOSO excludes dataset subject {r.training_subject_excluded} · {r.training_recordings} training recordings · model cache {r.model_cache_hit?'reused; raw input still reanalyzed':'new runtime reconstruction'}</p>}<p>Event delivery: {r.event_delivery?.status||'not applicable'}</p>{r.events?.map((event:any,n:number)=><p key={n}>{event.time_sec}s · {event.type}</p>)}{r.evidence_error&&<p className="text-red-700">{r.evidence_error}</p>}</div>)}
      {run.status==='COMPLETED'&&<><p>{run.matches_ground_truth===null?'No matching target annotation for this model':run.matches_ground_truth?'Relevant model output matches the dataset label':'Relevant model output differs from the dataset label; the result was not forced'}. Dataset clip labels are not validated incident timestamps or school performance.</p>{outputs.map((r:any,index:number)=>r.feature_extraction_status&&<p key={index} className="text-xs">{r.model_version}: {r.feature_extraction_status}</p>)}<details><summary>Dataset-label comparison by model</summary>{run.ground_truth_comparisons?.map((comparison:any,index:number)=><p key={index}>{comparison.model_version}: {comparison.expected_candidate===null?'No target annotation for this modality':`Expected candidate ${comparison.expected_candidate}; observed ${comparison.observed_candidate}; ${comparison.matches?'match':'mismatch'}`}</p>)}</details></>}
      {incidents.map(id=><button key={id} className="text-blue-700 underline mr-3" onClick={()=>setSelectedAlertId(id)}>Open actual incident #{id.slice(0,8)}</button>)}
      {incidents.length>0&&<button className="text-blue-700 underline" onClick={()=>{setSelectedZoneId(run.zone_id);setActivePage('digital_twin');}}>View incident zone on Digital Twin</button>}
    </div>}
    <details><summary className="font-bold cursor-pointer">Persistent scenario run history ({history.length})</summary><div className="space-y-2 pt-2">{history.map(r=><button key={r.id} className="block text-left text-sm text-blue-700 underline" onClick={()=>inspect(r.id)}>{r.scenario_name} · {r.model} · {r.status} · {r.submitted_at}</button>)}</div></details>
    <p className="text-xs text-slate-500">Legacy saved radar/acoustic predictions and controlled SOS/fusion/Telegram tests remain in their original labeled controls. They are not fresh model runs.</p>
  </section>;
}
