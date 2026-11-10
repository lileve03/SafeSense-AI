import React,{useEffect,useRef,useState,useSyncExternalStore} from 'react';
import {api,post} from '../../lib/api';
import {notificationStateLabel} from '../../lib/notificationState';
import {useSafeSenseApp} from '../../context/SafeSenseContext';
import {PRIVATE_DEMOS,deliverDemoRun,newRun,readRun,type DemoRun,type PrivateDemoId} from './privateDemoWorkflow';
import {type TrackingPlayback} from './trackingPlayback';
import type {SensorMode} from './SensorObservationPanel';

export type GuidedWorkflowState={run:DemoRun|null;report:any;started:boolean};

const LABELS:Record<PrivateDemoId,string>={normal:'Normal Presence',proximity:'Close Proximity',repetitive:'Repetitive Motion',possible_fall:'Possible Fall',fall:'Fall + Distress',sos:'SOS'};
const STEPS=['Detection','Risk Assessment','Incident','Staff Response'];

export function assertGuidedIncident(report:any,run:DemoRun) {
  if(run.workflow!=='guided'||report.id!==run.incidentId||report.is_test!==true||report.source_type!=='SIMULATION'
      ||report.processing_mode!=='simulation'||report.analysis_run_id!=='private-demo:'+run.id)
    throw Error('Automatic demo response refused: incident is outside this guided SIMULATION test run');
}

export function GuidedPrivateDemo({playback,enabled=true,inputControls,sosControl,sourceMode='SIMULATION',notificationOverride,onWorkflow}:{playback:TrackingPlayback;enabled?:boolean;inputControls?:React.ReactNode;sosControl?:React.ReactNode;sourceMode?:SensorMode;notificationOverride?:string;onWorkflow?:(value:GuidedWorkflowState)=>void}) {
  const {setIsLiveMode,checkFastApiConnection}=useSafeSenseApp();
  const state=useSyncExternalStore(playback.subscribe,playback.getSnapshot);
  const [demo,setDemo]=useState<PrivateDemoId>('fall');
  const [run,setRun]=useState<DemoRun|null>(()=>readRun('fall','guided'));
  const [started,setStarted]=useState(false),[busy,setBusy]=useState(false),[error,setError]=useState('');
  const [report,setReport]=useState<any>(null);
  const flight=useRef(false),mounted=useRef(true),revision=useRef(0);
  const selected=PRIVATE_DEMOS[demo];
  useEffect(()=>{onWorkflow?.({run,report,started});},[run,report,started,onWorkflow]);
  useEffect(()=>{if(!enabled&&!playback.getSnapshot().test)playback.pause();},[enabled,playback]);
  useEffect(()=>{if(started&&!state.test&&state.scenario!==selected.scenario)setStarted(false);},[started,state.test,state.scenario,selected.scenario]);
  useEffect(()=>{if(state.test){
    const id=state.test.kind==='fusion'?'fall':state.test.kind==='sos'?'sos':'normal';
    setDemo(id);setRun(readRun(id,'guided'));setReport(null);setStarted(false);revision.current++;
  }},[state.test?.kind]);
  useEffect(()=>{mounted.current=true;playback.setScenario('fall_impact');setIsLiveMode(true);return()=>{mounted.current=false;playback.pause();};},[playback,setIsLiveMode]);
  const persist=(value:DemoRun)=>{if(mounted.current)setRun(value);};
  useEffect(()=>{
    if(!run?.incidentId){setReport(null);return;}
    let cancelled=false;
    const refresh=async()=>{
      if(flight.current||playback.getSnapshot().test)return;
      const version=++revision.current;
      try{
        const value=await api(`/incidents/${run.incidentId}/report`);assertGuidedIncident(value,run);
        if(!cancelled&&version===revision.current&&!flight.current){setReport(value);setError('');}
      }catch(e){if(!cancelled&&!playback.getSnapshot().test){setError('Backend status unavailable: '+String(e));playback.pause();}}
    };
    void refresh();const timer=window.setInterval(refresh,1000);
    return()=>{cancelled=true;window.clearInterval(timer);};
  },[run?.incidentId,playback]);

  async function perform(work:()=>Promise<void>){
    if(flight.current)return;flight.current=true;revision.current++;setBusy(true);setError('');
    try{if(playback.getSnapshot().test)return;await work();await checkFastApiConnection();}
    catch(e){if(mounted.current&&!playback.getSnapshot().test){setError(String(e)+' · Paused; Start retries the same test record.');playback.pause();}}
    finally{flight.current=false;if(mounted.current)setBusy(false);}
  }
  useEffect(()=>{
    if(!enabled||state.test||!started||!run||error||flight.current||document.hidden||(!state.playing&&state.time<40)||state.scenario!==selected.scenario)return;
    const triggerAt=demo==='sos'?0:demo==='normal'?8:selected.at;
    if(!run.complete&&state.time>=triggerAt){
      if(demo==='proximity'&&!state.motionAnalysis?.candidates.some(c=>c.rule==='PROXIMITY_DURATION'))return;
      if(demo==='repetitive'&&!state.motionAnalysis?.candidates.some(c=>c.rule==='REPEATED_BACK_AND_FORTH'))return;
      void perform(async()=>{await deliverDemoRun(readRun(demo,'guided')||run,playback.frame(),persist);});return;
    }
    if(!run.incidentId||!report||report.id!==run.incidentId||['RESOLVED','FALSE_ALARM'].includes(report.status))return;
    if(state.time>=20&&!report.acknowledged_at){
      void perform(async()=>{
        const latest=await api(`/incidents/${run.incidentId}/report`);assertGuidedIncident(latest,run);
        if(!playback.getSnapshot().test&&!['RESOLVED','FALSE_ALARM'].includes(latest.status))await post(`/incidents/${run.incidentId}/ack`,{staff:'SIMULATED DEMO responder (not a human acknowledgement)'});
        if(mounted.current)setReport(await api(`/incidents/${run.incidentId}/report`));
      });return;
    }

  },[started,run,state.time,state.playing,state.scenario,state.motionAnalysis,report,error,demo,enabled]);

  function start(){
    if(!enabled)return;
    if(playback.getSnapshot().test){playback.start();return;}
    setError('');setIsLiveMode(true);
    if(!started){const value=readRun(demo,'guided')||newRun(demo,'guided');setRun(value);setStarted(true);if(playback.getSnapshot().scenario!==selected.scenario)playback.setScenario(selected.scenario);playback.bindGuidedRun(value.id);}
    playback.start();void checkFastApiConnection();
  }
  function restart(){
    if(!enabled)return;
    if(playback.getSnapshot().test){playback.restart();return;}
    const value=readRun(demo,'guided')||newRun(demo,'guided');
    setError('');setRun(value);setStarted(true);setIsLiveMode(true);
    playback.setScenario(selected.scenario);playback.bindGuidedRun(value.id);playback.start();
  }
  useEffect(()=>{
    if(!started||!run||state.test||state.scenario!==selected.scenario)return;
    playback.updateGuidedAssessment(selected.scenario,run.id,run.assessment as {level:import('../../types/safesense').RiskLevel;reason:string}|undefined,
      run.incidentId?{id:run.incidentId,status:report?.id===run.incidentId?report.status:undefined}:undefined);
  },[started,run,report,state.scenario,state.test,playback]);
  const closed=!!report&&['RESOLVED','FALSE_ALARM'].includes(report.status);
  const complete=started&&state.playbackStatus==='Completed';
  const triggerAt=demo==='sos'?0:demo==='normal'?8:selected.at;
  const phase=state.time<4?0:(!run?.complete||state.time<Math.min(triggerAt,8))?1:state.time<20||(run.incidentId&&!report?.acknowledged_at&&!closed)?2:3;
  const risk=report?.level||run?.assessment?.level;
  const notification=notificationOverride||report?.notification_state||report?.notifications?.at(-1)?.delivery_state||report?.notifications?.at(-1)?.status;
  const compactNotification=notification==='DISABLED'?'Sending disabled':notification==='API_ACCEPTED'||notification==='SENT'?'API Accepted':notification==='FAILED'?'Failed':notification==='PENDING'?'Pending':notification?notificationStateLabel(notification):'Not requested';
  return <section data-testid="guided-private-demo" className="rounded-2xl bg-white px-4 py-3 shadow-sm shadow-slate-200/40">
    <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
      <h2 className="text-xs font-bold text-slate-900">Scenario Controls</h2>
      <div className="flex flex-wrap items-center gap-2 text-[10px] font-semibold">
        <span title="Avatars and signals are illustrative in Simulation; recorded results use registered inputs." className="rounded-md bg-blue-50 px-2 py-1 text-blue-700">{sourceMode==='SIMULATION'?'Simulation':sourceMode==='RECORDED_REPLAY'?'Replay':'Hardware'}</span>
        <span title="No device connection or calibration has been verified" className="rounded-md bg-slate-100 px-2 py-1 text-slate-500">Hardware · Offline</span>
        <span data-testid="scenario-notification-state" title={`${notification?notificationStateLabel(notification):'No notification requested'}. Last accepted: ${report?.notifications?.at(-1)?.api_accepted_at||'unavailable'}; message ID: ${report?.notifications?.at(-1)?.telegram_message_id||'unavailable'}. Replay reuses this incident; it does not resend.`} className="rounded-md bg-slate-100 px-2 py-1 text-slate-500">Notification · {compactNotification}</span>
        <span data-testid="guided-demo-progress" className="ml-1 tabular-nums text-slate-400">{state.time.toFixed(1)} / 40s · {complete?'Completed':state.playbackStatus==='Playing'?'Playing':started?'Paused':'Ready'}</span>
      </div>
    </div>
    <div data-testid="private-demo-toolbar" className="flex flex-wrap items-center gap-x-3 gap-y-2 text-xs">
      {inputControls}
      <fieldset disabled={!enabled} className="contents disabled:opacity-50">
        <label className="flex min-w-0 items-center gap-2 text-slate-500">Scenario <select aria-label="Guided scenario" disabled={busy} className="h-9 max-w-full rounded-lg bg-slate-50 px-2 text-slate-900 ring-1 ring-slate-200 disabled:opacity-40" value={demo} onChange={e=>{
          const id=e.target.value as PrivateDemoId;playback.pause();setDemo(id);setRun(readRun(id,'guided'));setReport(null);setStarted(false);setError('');playback.setScenario(PRIVATE_DEMOS[id].scenario);
        }}>{Object.entries(LABELS).map(([id,label])=><option key={id} value={id}>{label}</option>)}</select></label>
        <button aria-label={state.playing?'Pause guided demo':'Start guided demo'} title="Play the selected test workflow" className="h-9 rounded-lg bg-blue-700 px-4 font-semibold text-white disabled:opacity-40" onClick={state.playing?playback.pause:start}>{state.playing?'Pause':'Play'}</button>
        <button aria-label="Restart guided demo" title="Replay the same test record without duplicate incidents" disabled={busy} className="h-9 rounded-lg px-2 font-semibold text-slate-600 hover:bg-slate-50 disabled:opacity-40" onClick={restart}>Restart</button>
        <label className="flex items-center gap-2 text-slate-500">Speed <select aria-label="Guided playback speed" className="h-9 rounded-lg bg-slate-50 px-2 text-slate-900 ring-1 ring-slate-200 disabled:opacity-40" value={state.speed} onChange={e=>playback.setSpeed(Number(e.target.value))}>{[1,2,4].map(speed=><option key={speed} value={speed}>{speed}×</option>)}</select></label>
      </fieldset>
      <div className="ml-auto">{sosControl}</div>
    </div>
    {error&&<p role="alert" className="mt-3 rounded-lg bg-rose-50 p-2 text-xs text-rose-800">{error}</p>}
    <details data-testid="guided-workflow-details" className="mt-3 text-[11px] text-slate-500">
      <summary className="cursor-pointer">Demo workflow</summary>
      <div className="mt-3 space-y-3">
        <ol className="grid grid-cols-2 gap-2 md:grid-cols-4" aria-label="Guided workflow stages">{STEPS.map((step,index)=><li key={step} aria-current={index===phase?'step':undefined} className={`rounded-lg px-3 py-2 ${index===phase?'bg-blue-50 text-blue-800':'bg-slate-50'}`}><span className="font-semibold">{index+1}. {step}</span><p className="mt-1">{index===0?'Synthetic metadata':index===1?risk||'Backend rules':index===2?run?.incidentId?'Test incident':run?.complete?'Not required':'Conditional':closed?'Resolved':report?.acknowledged_at?'Demo acknowledged':'Demo responder'}</p></li>)}</ol>
        <p data-testid="backend-scenario-assessment">Backend assessment: {run?.assessment?`${run.assessment.level} · ${run.assessment.reason}`:'Awaiting scenario signals'}</p>
        <p data-testid="guided-narration">Demo acknowledgement is simulated. Scenario visuals follow playback time. Incident response is separate; completion holds the final scene.</p>
        <button disabled={busy||!enabled} className="font-semibold text-blue-700 disabled:opacity-40" onClick={()=>{playback.pause();playback.setScenario(selected.scenario);setRun(newRun(demo,'guided'));setReport(null);setStarted(false);setError('');}}>Prepare new guided exercise</button>
      </div>
    </details>
  </section>;
}
