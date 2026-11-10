import type {SensorObservation,SensorMode} from './SensorObservationPanel';
import React,{useSyncExternalStore} from 'react';
import {observationFrame,DURATION,SCENARIOS,distances,simulatedSensorState,type ScenarioId,type TrackingPlayback} from './trackingPlayback';
import {SimulationMotionAnalysis} from './SimulationMotionAnalysis';
import {PrivateDangerScenarioControls} from './PrivateDangerScenarioControls';

export function TrackingSceneSummary({playback}:{playback:TrackingPlayback}) {
  const state=useSyncExternalStore(playback.subscribe,playback.getSnapshot);
  const signals=simulatedSensorState(state.scenario,state.time);
  return <><span className="px-2 py-1 rounded-full bg-cyan-50/95 border border-cyan-200 text-cyan-900">SIMULATION people: {state.frame.tracks.length} · {state.playing?'Playing':'Paused'}</span>
    {signals.fall&&<span className="px-2 py-1 rounded-full bg-red-50 text-red-800">SIMULATED radar possible fall</span>}
    {signals.impact&&<span className="px-2 py-1 rounded-full bg-amber-50 text-amber-800">SIMULATED acoustic impact</span>}
    {signals.sos&&<span className="px-2 py-1 rounded-full bg-red-50 text-red-800">SIMULATED SOS direct help request</span>}</>;
}

export function TrackingPlaybackControls({playback,detailsOnly=false,sourceMode='SIMULATION',observation=null}:{playback:TrackingPlayback;detailsOnly?:boolean;sourceMode?:SensorMode;observation?:SensorObservation|null}) {
  const state=useSyncExternalStore(playback.subscribe,playback.getSnapshot);
  const simulated=sourceMode==='SIMULATION';
  const {tracks}=simulated?state.frame:observationFrame(observation);
  const source=simulated?'SIMULATION':sourceMode;
  const selected=tracks.find(t=>t.id===state.selectedId);
  const pairs=distances(tracks).filter(pair=>!selected||pair.a===selected.id||pair.b===selected.id);
  const content=<section data-testid="tracking-playback-controls" className="space-y-3 text-xs">
    {!detailsOnly&&<div className="flex justify-between gap-2"><h3 className="font-bold text-slate-800">Anonymous tracks</h3><strong>{tracks.length} tracks</strong></div>}
    {!detailsOnly&&<>
    <p className="text-slate-500">Anonymous schematic avatars. SIMULATION walking is illustrative, not radar-measured anatomy or poses. Recorded/live avatars use neutral poses. Schematic coverage; hardware disconnected. Basic playback does not send alerts. The separate connected test controls below explicitly arm backend test signals.</p>
    <div className="flex flex-wrap items-center gap-2">
      <label>Scenario <select aria-label="Tracking scenario" className="border rounded-lg p-1.5" value={state.scenario} onChange={e=>playback.setScenario(e.target.value as ScenarioId)}>{Object.entries(SCENARIOS).map(([id,name])=><option key={id} value={id}>{name}</option>)}</select></label>
      <label>Playback speed <select aria-label="Tracking playback speed" className="border rounded-lg p-1.5" value={state.speed} onChange={e=>playback.setSpeed(Number(e.target.value))}>{[.5,1,2,4].map(n=><option key={n} value={n}>{n}×</option>)}</select></label>
      <button className="bg-blue-600 text-white rounded-lg px-3 py-1.5" onClick={state.playing?playback.pause:playback.start}>{state.playing?'Pause tracking':'Start tracking'}</button>
      <button className="border rounded-lg px-3 py-1.5" onClick={playback.restart}>Restart tracking</button>
    </div>
    </>}
    <div className="flex items-center gap-3"><input disabled={!simulated} aria-label="Tracking playback time" className="flex-1 min-w-0" type="range" min="0" max={DURATION} step=".1" value={state.time} onChange={e=>playback.seek(Number(e.target.value))}/><span className="tabular-nums" data-testid="tracking-playback-time">{state.time.toFixed(1)} / {DURATION}s</span></div>
    <div className="flex flex-wrap items-center gap-3"><label><input type="checkbox" checked={state.trails} onChange={e=>playback.setTrails(e.target.checked)}/> Motion trails</label><label><input type="checkbox" checked={state.coverage} onChange={e=>playback.setCoverage(e.target.checked)}/> Radar coverage</label><span>{state.playing?'Playing':state.time>=DURATION?'Completed':'Paused'} · Select a marker to inspect</span></div>
    <div className="flex flex-wrap gap-1.5" aria-label="Select simulated track">{tracks.map(track=><button key={track.id} aria-pressed={state.selectedId===track.id} aria-label={`Select ${simulated?'simulated':'observed'} track ${track.id}`} className={`border rounded-lg px-2 py-1 ${state.selectedId===track.id?'bg-cyan-100 border-cyan-600':'bg-slate-50'}`} onClick={()=>playback.select(track.id)}>{simulated?'SIM':'TRACK'} {track.id}</button>)}</div>
    <div data-testid="selected-track-information" data-frame-time={simulated?state.time:observation?.timestamp||''} className="rounded-lg bg-slate-50 p-2 text-slate-700">
      {selected?<><strong>{source} - {selected.id}</strong> · x {selected.position.x.toFixed(2)}m, y {selected.position.y.toFixed(2)}m, Height (z) {selected.position.z.toFixed(2)}m<br/>
        {selected.velocity&&Object.values(selected.velocity).every(Number.isFinite)?<>Speed {Math.hypot(selected.velocity.x,selected.velocity.y,selected.velocity.z).toFixed(2)}m/s - vx {selected.velocity.x.toFixed(2)} / vy {selected.velocity.y.toFixed(2)} / vz {selected.velocity.z.toFixed(2)}m/s - {Math.hypot(selected.velocity.x,selected.velocity.y,selected.velocity.z)>.03?'Moving':'Stationary'}</>:'Velocity unavailable'}</>:
        state.selectedId?`${source} - ${state.selectedId} is unavailable; select an active track.`:'Select an anonymous marker or track ID to inspect its movement.'}
    </div>
    <p data-testid="simulation-distances" className="text-slate-600">{source} distances (supplied 3D coordinate separation): {pairs.length?pairs.slice(0,5).map(p=>`${p.a} ↔ ${p.b}: ${p.meters.toFixed(2)}m`).join(' · '):'At least two active tracks required'}</p>
    {simulated&&<SimulationMotionAnalysis playback={playback}/>}
    {!detailsOnly&&<PrivateDangerScenarioControls playback={playback}/>}
  </section>;
  return detailsOnly?<details data-testid="private-track-details" className="rounded-2xl bg-white px-4 py-3 text-xs shadow-sm shadow-slate-200/40">
    <summary className="cursor-pointer font-semibold text-slate-600">Track details & display <span data-testid="simulated-people-count" className="ml-2 font-normal text-slate-400">{tracks.length} tracks</span></summary>
    <div className="mt-3">{content}</div>
  </details>:<div className="rounded-xl bg-white p-3">{content}</div>;
}
