import React,{useEffect,useRef,useState,useSyncExternalStore} from 'react';
import {api,post} from '../../lib/api';
import {notificationStateLabel} from '../../lib/notificationState';
import {useSafeSenseApp} from '../../context/SafeSenseContext';
import {PRIVATE_DEMOS,newRun,deliverDemoRun,readRun,storeRun,type DemoRun,type PrivateDemoId} from './privateDemoWorkflow';
import type {TrackingPlayback} from './trackingPlayback';

export function PrivateDangerScenarioControls({playback}:{playback:TrackingPlayback}) {
  const {setIsLiveMode,checkFastApiConnection,setSelectedAlertId,setActivePage,closePrivateAreaMonitoring}=useSafeSenseApp();
  const state=useSyncExternalStore(playback.subscribe,playback.getSnapshot);
  const [demo,setDemo]=useState<PrivateDemoId>('normal');
  const [run,setRun]=useState<DemoRun|null>(()=>readRun('normal'));
  const [armed,setArmed]=useState(false),[busy,setBusy]=useState(false),[error,setError]=useState('');
  const [report,setReport]=useState<any>(null),[reportError,setReportError]=useState('');
  const [staff,setStaff]=useState('Demo review operator'),[note,setNote]=useState('');
  const inFlight=useRef(false),mounted=useRef(true);
  const reportVersion=useRef(0);
  useEffect(()=>{mounted.current=true;return()=>{mounted.current=false;};},[]);
  const persist=(value:DemoRun)=>{storeRun(value);if(mounted.current)setRun(value);};
  const selected=PRIVATE_DEMOS[demo];
  useEffect(()=>{
    if(run?.complete||run?.incidentId||armed){setIsLiveMode(true);void checkFastApiConnection();}
  },[run?.id,run?.complete,run?.incidentId,armed,setIsLiveMode,checkFastApiConnection]);
  useEffect(()=>{
    if(!run?.incidentId){setReport(null);return;}
    let cancelled=false;
    const refresh=async()=>{
      if(inFlight.current)return;
      const version=++reportVersion.current;
      try{const value=await api(`/incidents/${run.incidentId}/report`);if(value.id!==run.incidentId)throw Error('Incident identity mismatch');if(!cancelled&&version===reportVersion.current&&!inFlight.current){setReport(value);setReportError('');}}
      catch(e){if(!cancelled)setReportError('Backend status could not be refreshed: '+String(e)+'. Receipt is not assumed.');}
    };
    void refresh();const timer=window.setInterval(refresh,1500);return()=>{cancelled=true;window.clearInterval(timer);};
  },[run?.incidentId]);

  async function deliver(current:DemoRun) {
    if(inFlight.current)return;
    inFlight.current=true;setBusy(true);setError('');
    try {
      setIsLiveMode(true);
      await deliverDemoRun(current,playback.frame(),persist);await checkFastApiConnection();
    }catch(e){if(mounted.current)setError(String(e)+' · Retry uses the same event IDs; no new test run is created.');}
    finally{inFlight.current=false;if(mounted.current)setBusy(false);}
  }
  useEffect(()=>{
    if(!armed||!run||run.complete||error||inFlight.current||!state.playing||state.scenario!==selected.scenario||state.time<selected.at)return;
    if(demo==='repetitive'&&!state.motionAnalysis?.candidates.some(c=>c.rule==='REPEATED_BACK_AND_FORTH'))return;
    if(demo==='proximity'&&!state.motionAnalysis?.candidates.some(c=>c.rule==='PROXIMITY_DURATION'))return;
    void deliver(run);
  },[armed,run,state.time,state.playing,state.scenario,state.motionAnalysis,demo,error]);

  async function start(){
    const value=readRun(demo)||newRun(demo);setRun(value);setError('');setArmed(true);setIsLiveMode(true);
    playback.setScenario(selected.scenario);playback.start();await checkFastApiConnection();
  }
  async function action(status:string){
    if(!run?.incidentId||inFlight.current)return;
    inFlight.current=true;setBusy(true);setError('');setIsLiveMode(true);
    reportVersion.current++;
    try{
      await post(`/incidents/${run.incidentId}/${status==='ACKNOWLEDGED'?'ack':'review'}`,status==='ACKNOWLEDGED'?{staff}:{staff,status,note});
      setReport(await api(`/incidents/${run.incidentId}/report`));await checkFastApiConnection();
    }catch(e){setError(String(e));}finally{inFlight.current=false;setBusy(false);}
  }
  const closed=['RESOLVED','FALSE_ALARM'].includes(report?.status);
  const notification=report?.notification_state||report?.notifications?.at(-1)?.delivery_state||report?.notifications?.at(-1)?.status;
  return <section data-testid="private-danger-scenarios" className="rounded-xl border border-blue-200 bg-blue-50/30 p-3 space-y-3 text-xs">
    <h3 className="font-bold text-blue-900">Six connected private-area demos · SIMULATED TEST workflow</h3>
    <label>Demo scenario <select aria-label="Private-area demo scenario" disabled={busy} className="border rounded-lg p-1.5 max-w-full" value={demo} onChange={e=>{
      const id=e.target.value as PrivateDemoId;setDemo(id);setRun(readRun(id));setReport(null);setArmed(false);setError('');playback.setScenario(PRIVATE_DEMOS[id].scenario);
    }}>{Object.entries(PRIVATE_DEMOS).map(([id,value],i)=><option key={id} value={id}>{i+1}. {value.label}</option>)}</select></label>
    <p>{selected.expectation}. All generated tracks, distances, sensor signals and rule input confidence are <strong>SIMULATED</strong>. Model score: <strong>SIMULATED · not applicable</strong>.</p>
    <p>Playback writes test signals only after you run this connected demo. Backend events synchronize Map, Alerts and Incident Review. No CCTV, microphone or speech recording. Hardware remains disconnected.</p>
    <div className="flex flex-wrap gap-2">
      <button disabled={busy} onClick={start} className="bg-blue-700 text-white rounded-lg px-3 py-2 disabled:opacity-50">{run?.complete?'Replay same connected test':'Run connected test demo'}</button>
      <button disabled={busy} className="border rounded-lg px-3 py-2" onClick={()=>{playback.pause();setArmed(false);setError('');setReport(null);setRun(newRun(demo));}}>Prepare explicit new test run</button>
      {demo==='sos'&&<button disabled={busy} className="bg-red-700 text-white rounded-lg px-3 py-2" onClick={()=>{const value=readRun(demo)||newRun(demo);setRun(value);setArmed(true);playback.setScenario('sos');playback.seek(5);void deliver(value);}}>{run?.complete?'Replay same test SOS request':'Request test SOS help now'}</button>}
      {error&&run&&<button disabled={busy} className="underline" onClick={()=>void deliver(readRun(demo)||run)}>Retry same test request</button>}
    </div>
    {error&&<p role="alert" className="text-red-700">{error}</p>}
    <p data-testid="private-demo-progress">{run?`Run ${run.id} · ${busy?'Saving to backend':run.complete?'Test signals saved':armed?'Armed; waiting for supported playback signals':'Prepared'} · ${state.time.toFixed(1)} / 40s · ${state.time>=40?'Playback complete':'Playback incomplete'}`:'No connected test run started'}</p>
    {run?.complete&&!run.incidentId&&<p>No test incident created: {demo==='proximity'?'proximity is a motion candidate, not verified danger':'normal presence is not a danger signal'}.</p>}
    {!!run?.events.length&&<ul className="list-disc pl-4">{run.events.map(event=><li key={event.event_id}>SIMULATED {event.sensor_modality}: {event.type} · {event.type==='sos'?'direct help request; confidence not used':`SIMULATED rule confidence ${event.confidence.toFixed(2)}`} · SIMULATED model score: not applicable</li>)}</ul>}
    {run?.incidentId&&<div className="rounded-xl bg-white border p-3 space-y-2" data-testid="connected-demo-incident">
      <p>Persisted test incident <strong>#{run.incidentId.slice(0,8)}</strong> · Backend risk {report?.level||'Loading'} · <strong data-testid="demo-incident-status">{report?.status||'Loading'}</strong></p>
      <p>{report?.reason}</p><p>Simulation candidates are not verified physical danger. VERIFIED below is an explicit human test-workflow action.</p>
      <p data-testid="demo-telegram-status">Actual backend Telegram status: {notification?notificationStateLabel(notification):'Not yet verified; receipt is not assumed'}</p>
      {reportError&&<p role="alert">{reportError}</p>}
      <div className="flex flex-wrap gap-2"><button className="underline" onClick={()=>{setIsLiveMode(true);setSelectedAlertId(run.incidentId!);}}>Open test incident details</button><button className="underline" onClick={()=>{setIsLiveMode(true);setActivePage('alerts');}}>View synchronized Alerts</button><button className="underline" onClick={()=>{setIsLiveMode(true);setActivePage('incident_review');}}>View synchronized Incident Review</button><button className="underline" onClick={()=>{setIsLiveMode(true);closePrivateAreaMonitoring();}}>View synchronized Digital Twin Map</button></div>
      {!closed&&<div className="space-y-2"><label>Test reviewing staff <input aria-label="Demo reviewing staff" className="border p-1 rounded" value={staff} onChange={e=>setStaff(e.target.value)}/></label>
        <label className="block">Review / resolution note <textarea aria-label="Demo resolution note" className="border p-1 rounded w-full" value={note} onChange={e=>setNote(e.target.value)}/></label>
        <div className="flex flex-wrap gap-2"><button disabled={busy||!staff.trim()||!!report?.acknowledged_at} className="border rounded p-2 disabled:opacity-50" onClick={()=>void action('ACKNOWLEDGED')}>Acknowledge test incident</button><button disabled={busy||!staff.trim()||!report?.acknowledged_at} className="border rounded p-2 disabled:opacity-50" onClick={()=>void action('VERIFIED')}>Record human test verification</button><button disabled={busy||!staff.trim()||!note.trim()||!report?.acknowledged_at} className="border rounded p-2 disabled:opacity-50" onClick={()=>void action('RESOLVED')}>Resolve test incident</button></div>
      </div>}
    </div>}
  </section>;
}
