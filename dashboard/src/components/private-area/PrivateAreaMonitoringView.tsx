import {RISK_PALETTE} from './riskAnimation';
import {observationVisualRisk} from './sceneTracking';
import {GuidedPrivateDemo, type GuidedWorkflowState} from './GuidedPrivateDemo';
import {TrackingPlayback, simulatedSensorState, testSensorState, distances} from './trackingPlayback';
import {TrackingPlaybackControls} from './TrackingPlaybackControls';
import {PrivateTestActions,type PrivateTestActionsHandle} from './PrivateTestActions';
import {SensorObservationPanel, type SensorMode, type SensorObservation} from './SensorObservationPanel';
import { SensorEventPanel } from '../analysis/SensorEventPanel';
import React, { useState, useMemo, useRef, useEffect, useSyncExternalStore } from 'react';
import { useSafeSenseApp } from '../../context/SafeSenseContext';
import { PrivateAreaDigitalTwin3D } from './PrivateAreaDigitalTwin3D';
import { RiskLevel } from '../../types/safesense';
import {Lock,EyeOff,AlertTriangle} from 'lucide-react';

export const PrivateAreaMonitoringView: React.FC = () => {
  const {
    zones,
    selectedZoneId,
    setSelectedZoneId,
    alerts,
    setSelectedAlertId,
    timeline,
    sensorEvents,
    checkFastApiConnection,
    setIsLiveMode,
    acknowledgeAlert,
    fastApiStatus,
    closePrivateAreaMonitoring,
    setActivePage,
  } = useSafeSenseApp();

  const [playback]=useState(()=>new TrackingPlayback());
  const tracking=useSyncExternalStore(playback.subscribe,playback.getSnapshot);
  const signals={...simulatedSensorState(tracking.scenario,tracking.time),sos:tracking.scenario==='sos'&&tracking.visual.triggered};
  useEffect(()=>()=>playback.pause(),[playback]);
  const [sensorMode,setSensorMode]=useState<SensorMode>('SIMULATION');
  const [workflow,setWorkflow]=useState<GuidedWorkflowState>({run:null,report:null,started:false});
  const [normalizedObservation,setNormalizedObservation]=useState<SensorObservation|null>(null);
  const [selectedLogId, setSelectedLogId] = useState<string | null>(null);
  const [showLiveSosModal, setShowLiveSosModal] = useState<boolean>(false);
  const [isAckLoading, setIsAckLoading] = useState<boolean>(false);
  const [sosSending,setSosSending]=useState(false);
  const testActions=useRef<PrivateTestActionsHandle|null>(null);
  const activeTest=tracking.test;
  const testSelection=activeTest?.result;
  const viewMode=activeTest?.sourceMode||sensorMode;
  const sceneObservation=activeTest?activeTest.result.recordedObservation||null:normalizedObservation;
  const testSignals=testSensorState(activeTest,tracking.time);

  // Fallback to selected zone or default to Blind Spot
  const currentZone = useMemo(
    () => zones.find((z) => z.id === selectedZoneId) || zones.find((z) => z.id === 'ZONE_TOILET_BLINDSPOT') || zones[0],
    [zones, selectedZoneId]
  );


  // Active alert for this zone
  const activeAlert = useMemo(
    () => viewMode==='SIMULATION' ? alerts.find(a=>a.id===tracking.visual.incidentId&&!['resolved','false_alarm'].includes(a.status)) :
      alerts.filter(
        (a) =>
          a.zoneId === currentZone?.id &&
          a.status !== 'resolved' &&
          a.status !== 'false_alarm'
      ).sort((a,b) => b.riskScore - a.riskScore)[0],
    [alerts, currentZone, viewMode, tracking.visual.incidentId]
  );

  const backendRisk=activeTest?testSelection?.risk:viewMode==='SIMULATION'?tracking.visual.assessment?.level:sceneObservation?.source_mode===viewMode&&sceneObservation.data_validity==='VALID'?sceneObservation.backend_assessment?.level:undefined;
  const riskLevel:RiskLevel=viewMode==='SIMULATION'?tracking.visual.risk
    : activeTest?tracking.visual.risk:observationVisualRisk(sceneObservation?.source_mode===viewMode?sceneObservation:null)||'LOW';

  // Relevant timeline events for this zone
  const zoneTimeline = useMemo(
    () =>
      timeline.filter(
        (t) =>
          t.zoneId === currentZone?.id
      ),
    [timeline, currentZone]
  );

  const zoneObservations = sensorEvents.filter(event => event.zone_id === currentZone.id);
  const radarObservation = zoneObservations.find(event => event.source === 'radar' || event.sensor_modality === 'radar');
  const acousticObservation = zoneObservations.find(event => event.source === 'yamnet' || event.sensor_modality === 'acoustic');
  const validObservation=sceneObservation?.source_mode===viewMode&&sceneObservation.data_validity==='VALID'?sceneObservation:null;
  const acousticSignal = activeTest ? testSignals.acoustic||(testSelection?.status==='Running'?'Pending':'Quiet') : viewMode!=='SIMULATION' ? validObservation?.acoustic_events?.[0]?.kind : signals.impact?'SIMULATED impact':'No simulated event';
  const motionSignal = viewMode!=='SIMULATION' ? validObservation?.radar_event : tracking.frame.tracks.some(t=>t.velocity&&Math.hypot(t.velocity.x,t.velocity.y,t.velocity.z)>.03)?'Moving':'Stationary';
  const fallSignal = activeTest ? testSignals.fall : viewMode!=='SIMULATION' ? validObservation?.radar_event === 'fall' : tracking.visual.fallProgress>0;
  const sourceLabel = (mode?: string) => mode === 'simulation' ? 'SIMULATION'
    : mode === 'recorded_sensor_replay' ? 'RECORDED SENSOR REPLAY'
    : mode === 'real_model' ? 'MODEL OUTPUT · hardware not verified' : 'NO SENSOR DATA';
  // Acknowledge handler
  const handleAcknowledge = async (alertId: string) => {
    setIsAckLoading(true);
    try {
      await acknowledgeAlert(alertId);
    } finally {
      setIsAckLoading(false);
    }
  };

  const handleSosTrigger=()=>setShowLiveSosModal(true);
  const handleConfirmLiveTestSos=async()=>{
    setShowLiveSosModal(false);setSosSending(true);
    try{await testActions.current?.run('sos');}finally{setSosSending(false);}
  };

  const linkedId=testSelection?.incidentId||(viewMode==='SIMULATION'&&workflow.started?workflow.run?.incidentId:validObservation?.backend_assessment?.incident_id||activeAlert?.id);
  const linkedAlert=alerts.find(alert=>alert.id===linkedId);
  const linkedReport=workflow.report?.id===linkedId?workflow.report:null;
  const observedAssessment=validObservation?.backend_assessment?.incident_id===linkedId?validObservation?.backend_assessment:undefined;
  const linkedStatus=(testSelection?.incidentId===linkedId?testSelection?.incidentStatus:undefined)||linkedReport?.status||observedAssessment?.status||linkedAlert?.status.toUpperCase()||(linkedId?'Pending':'Not escalated');
  const linkedReason=(testSelection?.incidentId===linkedId?testSelection?.reason:undefined)||linkedReport?.reason||observedAssessment?.reason||linkedAlert?.reason;
  const linkedClosed=['RESOLVED','FALSE_ALARM'].includes(linkedStatus);
  const count=viewMode==='SIMULATION'?tracking.frame.tracks.length:validObservation?.tracks?.length;
  const separation=viewMode==='SIMULATION'?distances(tracking.frame.tracks)[0]?.meters:validObservation?.motion_analysis?.nearest_pair?.distance_m;
  const available=activeTest?!!testSelection?.risk:viewMode==='SIMULATION'||!!validObservation;
  const radarAvailability=viewMode==='SIMULATION'?'Active':viewMode==='LIVE_HARDWARE'&&!validObservation?'Disconnected':validObservation&&(validObservation.radar_event||validObservation.tracks?.length||validObservation.point_cloud?.length)?'Active':'Missing';
  const shortAcoustic=acousticSignal?.replace('SIMULATED ','').replace('No simulated event','Quiet').replace('normal_acoustic','Background')||'Unavailable';
  const riskColor='#'+RISK_PALETTE[riskLevel].toString(16).padStart(6,'0');
  const card='rounded-2xl bg-white p-4 shadow-sm shadow-slate-200/40';
  const activityTime=(value:string)=>Number.isFinite(Date.parse(value))?new Date(value).toLocaleTimeString([],{hour:'2-digit',minute:'2-digit',second:'2-digit',hour12:false}):value;
  const openMap=()=>{closePrivateAreaMonitoring();setActivePage('digital_twin');};

  return (
    <div className="space-y-4" data-testid="private-monitoring-view">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <div><p className="text-[10px] font-bold uppercase tracking-[.18em] text-slate-400">Private Area</p><h1 className="text-xl font-extrabold text-slate-900">{currentZone.name}</h1></div>
        <nav className="flex gap-4 text-xs font-semibold text-slate-500" aria-label="Private area navigation">
          <button onClick={()=>{closePrivateAreaMonitoring();setActivePage('overview');}}>School overview</button>
          <button className="text-blue-700" onClick={openMap}>Return to campus map</button>
        </nav>
      </header>

      <GuidedPrivateDemo playback={playback} enabled={viewMode==='SIMULATION'&&!activeTest} sourceMode={viewMode} notificationOverride={testSelection?.notification} onWorkflow={setWorkflow}
        inputControls={<label className="flex items-center gap-2 text-slate-500">Input Source <select aria-label="Source mode" value={viewMode} disabled={!!activeTest} className="h-9 rounded-lg bg-slate-50 px-2 text-slate-900 ring-1 ring-slate-200" onChange={e=>{playback.pause();setSensorMode(e.target.value as SensorMode);setNormalizedObservation(null);setIsLiveMode(true);}}>
          <option value="SIMULATION">Simulation</option><option value="RECORDED_REPLAY">Replay</option><option value="LIVE_HARDWARE">Hardware</option>
        </select></label>}
        sosControl={<button onClick={handleSosTrigger} aria-label="ACTIVATE SOS EMERGENCY" title="Create an authorized TEST help request" className="h-9 rounded-lg bg-rose-600 px-4 text-xs font-bold text-white hover:bg-rose-700">SOS Test</button>}/>

      <PrivateTestActions key={currentZone.id} ref={testActions} zoneId={currentZone.id} playback={playback}/>

      <div data-testid="private-area-columns" className="grid grid-cols-1 gap-4 lg:grid-cols-[minmax(160px,2fr)_minmax(0,6fr)_minmax(220px,2.5fr)] items-start">
        <aside data-testid="private-zone-panel" className="min-w-0 space-y-4">
          <section className={card}>
            <div className="mb-3 flex items-center gap-2 text-xs font-bold text-slate-900"><Lock className="h-4 w-4 text-rose-500"/>Zone info</div>
            <span title="No cameras, speech recording or identifiable reconstruction. Bodies are schematic avatars." className="inline-flex items-center gap-1.5 rounded-md bg-rose-50 px-2 py-1 text-[10px] font-bold text-rose-700"><EyeOff className="h-3 w-3"/>Private · No CCTV</span>
            <dl className="mt-4 space-y-3 text-xs">
              <div><dt className="text-slate-400">Coverage</dt><dd className="mt-1 font-semibold text-slate-700">Toilet / blind spot</dd></div>
              <div><dt className="text-slate-400">Sensor inputs</dt><dd className="mt-1 text-slate-700">mmWave · YAMNet · SOS</dd></div>
              <div><dt className="text-slate-400">Privacy</dt><dd className="mt-1 text-slate-700">Anonymous metadata only</dd></div>
            </dl>
          </section>
          <section className={card}>
            <h2 className="mb-3 text-xs font-bold text-slate-900">Monitored zones</h2>
            <div className="space-y-1">{zones.map(z=><button key={z.id} aria-current={z.id===currentZone.id?'location':undefined} onClick={()=>{setSelectedZoneId(z.id);if(!z.isPrivate)closePrivateAreaMonitoring();}} className={`flex w-full items-center justify-between gap-2 rounded-lg px-2.5 py-2.5 text-left text-xs transition-colors ${z.id===currentZone.id?'bg-blue-50 font-bold text-blue-800':'text-slate-600 hover:bg-slate-50'}`}>
              <span className="truncate">{z.name}</span><span title={z.level} className="h-1.5 w-1.5 shrink-0 rounded-full" style={{backgroundColor:'#'+RISK_PALETTE[z.level].toString(16).padStart(6,'0')}}/>
            </button>)}</div>
            <button onClick={openMap} className="mt-3 text-xs font-semibold text-blue-700">Full school map →</button>
          </section>
        </aside>

        <section aria-label="3D room" data-testid="private-scene-panel" className="order-first min-w-0 space-y-3 lg:order-none">
          <PrivateAreaDigitalTwin3D key={currentZone.id} playback={playback} observation={validObservation} level={riskLevel}
            riskScore={currentZone.riskScore} incidentLevel={activeAlert?.level} hasVisualData={available}
            fallDetected={fallSignal} motionLevel={motionSignal} interpersonalDistance={separation} occupants={count||0}
            acousticEvent={acousticSignal} presenceIndicated={viewMode!=='LIVE_HARDWARE'&&validObservation?.radar_event==='presence'}
            radarObserved={activeTest?testSignals.radar:!!validObservation?.radar_event} observationTimestamp={validObservation?.timestamp}
            sosActive={activeTest?testSignals.sos:viewMode==='SIMULATION'?signals.sos:validObservation?.sos_state==='ACTIVE'} processingLabel={viewMode}
            onIncidentClick={linkedId?()=>setSelectedAlertId(linkedId):undefined} isSimulated={viewMode==='SIMULATION'}/>
          {viewMode==='SIMULATION'&&tracking.scenario==='sos'&&<p data-testid="sos-illustrative-label" className="text-[10px] text-slate-500">Simulated SOS person / press - illustrative, not radar attribution</p>}
          <TrackingPlaybackControls playback={playback} detailsOnly sourceMode={viewMode} observation={validObservation}/>
        </section>

        <aside data-testid="private-status-panel" className="min-w-0 space-y-4">
          <section className={card}>
            <div className="flex items-center justify-between gap-2"><h2 className="text-xs font-bold text-slate-900">Sensor Status</h2><span title="Backend connection; does not verify physical hardware" className={`h-2 w-2 rounded-full ${fastApiStatus==='connected'?'bg-emerald-500':'bg-slate-300'}`}/></div>
            <div className="my-4 rounded-xl bg-slate-50 px-3 py-3" data-testid="private-risk-status" data-alert-policy="scenario-timestamp-independent-of-incident" data-playback-status={tracking.playbackStatus} data-incident-status={tracking.visual.incidentStatus||'NONE'} data-radar-availability={radarAvailability} title={activeTest?'Backend test assessment':viewMode==='SIMULATION'?'Simulated scenario risk; independent of backend response':'Actual recorded backend assessment'}>
              <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">{viewMode==='SIMULATION'?'Scenario Risk':'Observation Risk'}</span>
              <div className="mt-1 flex items-center gap-2"><span className="h-2 w-2 rounded-full" style={{backgroundColor:riskColor}}/><strong className="text-xl tracking-tight text-slate-900">{available?riskLevel:'Unavailable'}</strong></div>
              {viewMode==='SIMULATION'&&tracking.scenario==='fall_only'&&riskLevel==='HIGH'&&<p className="mt-1 text-xs font-semibold text-red-700">Possible Fall - Review Required</p>}
            </div>
            <dl className="space-y-3 text-xs">
              {[
                ['Actual Backend Assessment',backendRisk||'Unavailable','Backend result only; independent of the simulated scenario.'],
                ['Incident Status',linkedStatus,'Persisted incident response; does not control simulation visuals.'],
                ['Radar Status',radarAvailability==='Active'?'Active':radarAvailability==='Disconnected'?'Disconnected':'Unavailable','Sensor availability is independent of scenario risk.'],
                ['People Count',count==null?'Unavailable':String(count),'Synthetic tracks in Simulation; recorded labels alone cannot provide a people count.'],
                ['Separation Distance',separation==null?'—':`${separation.toFixed(2)} m`,'Distance between supplied track points; not measured anatomy.'],
                ['Fall Status',!available?'Unavailable':fallSignal?(viewMode==='SIMULATION'&&tracking.scenario!=='fall_only'?'Simulated fall':'Possible Fall'):'No flag','A fall signal requires human review.'],
                ['Acoustic Status',viewMode==='SIMULATION'&&signals.impact?'Simulated distress':shortAcoustic,'Non-speech event classification only.'],
                ['SOS Status',activeTest?(testSignals.sos?'Active':'Inactive'):viewMode==='SIMULATION'?(signals.sos?'Active':'Inactive'):validObservation?.sos_state||'Unavailable','Direct help request; independent of model confidence.'],
              ].map(([label,value,hint])=><div key={label} className="flex items-center justify-between gap-3" title={hint}><dt className="text-slate-500">{label}</dt><dd data-testid={label==='SOS Status'?'private-sos-status':undefined} className="max-w-[55%] truncate font-semibold capitalize text-slate-800">{value}</dd></div>)}
            </dl>
          </section>
          <section className={card} data-testid="linked-incident-card">
            <div className="flex items-center justify-between gap-2"><h2 className="text-xs font-bold text-slate-900">Linked Incident</h2>{linkedId&&<span className="font-mono text-[10px] text-slate-400">#{linkedId.slice(0,8)}</span>}</div>
            <div className="mt-3 space-y-2 text-xs" data-testid="scenario-incident-status">
              <p data-testid="scenario-response-status" className={`font-bold ${linkedClosed?'text-emerald-700':'text-slate-800'}`}>{linkedStatus}</p>
              <p className="line-clamp-2 text-slate-500" title={linkedReason}>{linkedId?(linkedReason||'Awaiting backend report'):'No escalation required'}</p>
              {linkedReport?.acknowledged_at&&<p className="text-[10px] text-slate-400" title={linkedReport.acknowledged_by}>{linkedReport.acknowledged_by?.includes('SIMULATED')?'Demo responder · simulated':'Staff acknowledgement recorded'}</p>}
            </div>
            <button disabled={!linkedId} onClick={()=>linkedId&&setSelectedAlertId(linkedId)} className="mt-4 w-full rounded-lg bg-blue-700 px-3 py-2 text-xs font-semibold text-white disabled:bg-slate-100 disabled:text-slate-400">Open Incident</button>
            {linkedId&&!linkedClosed&&!linkedReport?.acknowledged_at&&linkedAlert?.status==='new'&&<button onClick={()=>handleAcknowledge(linkedId)} disabled={isAckLoading} className="mt-2 w-full py-1 text-xs font-semibold text-blue-700 disabled:opacity-50">{isAckLoading?'Acknowledging...':'Acknowledge Incident'}</button>}
            <button onClick={()=>setActivePage('alerts')} className="mt-3 w-full text-xs text-slate-500">All alerts →</button>
          </section>
        </aside>
      </div>

      <section className={card} data-testid="private-event-timeline">
        <div className="mb-3 flex items-center justify-between"><h2 className="text-xs font-bold text-slate-900">Recent activity</h2><span className="text-[10px] text-slate-400">{zoneTimeline.length} events</span></div>
        {!zoneTimeline.length?<p className="text-xs text-slate-400">No activity yet</p>:<div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-3">{zoneTimeline.slice(0,6).map(item=><button key={item.id} onClick={()=>setSelectedLogId(selectedLogId===item.id?null:item.id)} aria-expanded={selectedLogId===item.id} className="rounded-xl bg-slate-50 px-3 py-2.5 text-left">
          <div className="flex items-center justify-between gap-2"><span className="text-[10px] font-bold" style={{color:'#'+RISK_PALETTE[item.level].toString(16).padStart(6,'0')}}>{item.level}</span><time title={item.time} className="text-[10px] text-slate-400">{activityTime(item.time)}</time></div>
          <p title={item.description} className={`mt-1 text-xs text-slate-700 ${selectedLogId===item.id?'':'truncate'}`}>{selectedLogId===item.id?item.description:item.description.split('|')[0].trim()}</p>
        </button>)}</div>}
        {zoneTimeline.length>6&&<details className="mt-3 text-xs"><summary className="cursor-pointer font-semibold text-slate-500">Earlier activity</summary><div className="mt-2 max-h-48 space-y-2 overflow-auto">{zoneTimeline.slice(6).map(item=><p key={item.id} className="flex gap-3 rounded-lg bg-slate-50 p-2"><time className="shrink-0 text-slate-400">{item.time}</time><span>{item.description}</span></p>)}</div></details>}
      </section>

      <details className="rounded-2xl bg-white px-4 py-3 text-xs shadow-sm shadow-slate-200/40" data-testid="private-technical-details">
        <summary className="cursor-pointer font-semibold text-slate-500">Technical Details</summary>
        <div className="mt-3 space-y-3">
          <details data-testid="private-sensor-provenance"><summary className="cursor-pointer font-semibold text-slate-700">Sensor provenance & recorded inputs</summary>
            <div className="mt-3 space-y-2 text-slate-500"><p>Metadata only. Hardware, calibration and acquisition timing are unverified.</p>
              <SensorObservationPanel sharedSimulation hideModeSelector zoneId={currentZone.id} mode={viewMode} onMode={setSensorMode} onObservation={setNormalizedObservation}/>
              {viewMode==='SIMULATION'&&<p>Tracks and poses are synthetic; no physical sensor measurements.</p>}
              {viewMode!=='SIMULATION'&&<details><summary className="cursor-pointer font-semibold">Saved prediction replay</summary><SensorEventPanel zoneId={currentZone.id} privateOnly autoOpenIncident={false} replayOnly/></details>}
              {([['Radar',radarObservation],['Acoustic',acousticObservation]] as const).map(([name,event])=>event&&<div key={name} className="rounded-lg bg-slate-50 p-2"><strong>{name}</strong> · {sourceLabel(event.processing_mode)} · {event.model_version||'No model'} · score {event.score==null?'—':event.score.toFixed(5)}<p className="mt-1 break-all text-[10px]">{event.timestamp} · {event.evidence_reference||'No evidence reference'}</p></div>)}
            </div>
          </details>
          <details><summary className="cursor-pointer font-semibold text-slate-700">Backend rules</summary><div className="mt-2 space-y-2 text-slate-500">
            <p>Fusion requires matching zone, source mode, run and time window. Candidate incidents require review.</p>
            <p data-testid="recorded-backend-reason">{validObservation?.backend_assessment?.reason||workflow.run?.assessment?.reason||'Awaiting backend assessment'}</p>
            <p data-testid="actual-incident-severity">Persisted severity: {linkedReport?.level||linkedAlert?.level||'No linked incident'}. Scene risk follows the current scenario.</p>
          </div></details>
          <details><summary className="cursor-pointer font-semibold text-slate-700">Scene & privacy</summary><p className="mt-2 text-slate-500">Schematic bodies and coverage; track coordinates are not measured skeletons. No private video, speech recording or identifiable reconstruction. Recorded labels provide no fabricated positions or synchronized fusion.</p></details>
        </div>
      </details>
      {/* Authorized Live Mode SOS Activation Confirmation Modal */}
      {showLiveSosModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-xs p-4 animate-in fade-in duration-150">
          <div className="w-full max-w-md bg-white rounded-2xl border border-rose-200 shadow-2xl p-5 space-y-4">
            <div className="flex items-center gap-3">
              <div className="p-2.5 rounded-xl bg-rose-100 text-[#EF4444]">
                <AlertTriangle className="w-6 h-6" />
              </div>
              <div>
                <h3 className="font-extrabold text-base text-[#0F172A]">
                  Authorize Prototype SOS Test
                </h3>
                <p className="text-xs text-[#64748B]">Oakridge Academy • SafeSense Incident Engine</p>
              </div>
            </div>

            <div className="p-3 rounded-xl bg-slate-50 border border-slate-200 text-xs text-[#0F172A] space-y-1.5">
              <p className="font-semibold text-rose-700">
                Prototype SOS test — no emergency dispatch
              </p>
              <p className="text-[#64748B] leading-snug">
                This records a backend test SOS and may notify the authorized Telegram TEST chat when configured. It has no physical dispatch integration.
                Are you authorizing this prototype emergency trigger test for <strong>{currentZone.name}</strong>?
              </p>
            </div>

            <div className="flex items-center justify-end gap-2.5 pt-2">
              <button
                onClick={() => setShowLiveSosModal(false)}
                disabled={sosSending}
                className="px-4 py-2 rounded-xl bg-slate-100 hover:bg-slate-200 text-[#0F172A] font-bold text-xs transition-colors cursor-pointer"
              >
                Cancel
              </button>
              <button
                onClick={handleConfirmLiveTestSos}
                disabled={sosSending}
                className="px-4 py-2 rounded-xl bg-[#EF4444] hover:bg-red-700 text-white font-bold text-xs transition-all shadow-xs cursor-pointer"
              >
                Confirm Test Broadcast
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
