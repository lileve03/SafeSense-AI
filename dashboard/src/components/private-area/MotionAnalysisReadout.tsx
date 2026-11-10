import React from 'react';
import type {MotionAnalysis} from './motionAnalysis';
const value=(n:number|null|undefined,digits=2)=>n==null?'Unavailable':n.toFixed(digits);

export function MotionAnalysisReadout({analysis,sourceMode}:{analysis?:MotionAnalysis|null;sourceMode:string}) {
  const nearest=analysis?.nearest_pair,rules=analysis?.rules;
  return <section data-testid="motion-analysis-readout" className="rounded-xl border border-violet-200 bg-violet-50/40 p-3 space-y-2 text-xs">
    <h4 className="font-bold text-violet-900">{sourceMode} · Backend proximity & motion rules</h4>
    <p data-testid="nearest-track-distance"><strong>Nearest tracked-person distance (anonymous tracks): </strong>{nearest?`${value(nearest.distance_m)}m · ${nearest.track_ids.join(' / ')} · within-threshold duration ${value(nearest.proximity_duration_seconds)}s`:'Unavailable; requires two valid, calibrated track positions.'}</p>
    <p>{analysis?.reason||'No supported motion analysis available.'}</p>
    <p className="font-semibold">{analysis?.notice||'Proximity and repeated motion are review candidates, not proof of fighting or bullying.'}</p>
    {rules&&<p data-testid="backend-motion-rules">Backend rules: distance &lt; {rules.proximity_distance_m}m continuously ≥ {rules.proximity_duration_seconds}s; repeated motion ≥ {rules.min_reversals} reversals in {rules.window_seconds}s, observed span ≥ {rules.min_observation_span_seconds}s, meaningful leg ≥ {rules.min_leg_displacement_m}m, path ≥ {rules.min_path_length_m}m and net/path ≤ {rules.max_net_path_ratio}. Continuity gap ≤ {rules.max_gap_seconds}s.</p>}
    <div data-testid="motion-rule-triggers" className="space-y-1">{analysis?.candidates.length?analysis.candidates.map((candidate,i)=><p key={candidate.rule+i} className="rounded-lg border border-fuchsia-200 bg-fuchsia-50 p-2"><strong>REVIEW CANDIDATE · {candidate.rule} · {candidate.track_ids.join(' / ')}</strong><br/>{candidate.reason}</p>):<p>No current rule candidates. Missing data does not establish safety or absence.</p>}</div>
    {!!analysis?.tracks.length&&<details><summary className="cursor-pointer font-semibold">Explainable motion features ({analysis.tracks.length} tracks)</summary><div className="overflow-x-auto"><table className="w-full text-left mt-2" aria-label="Backend motion features"><thead><tr>{['Track','Speed m/s','Acceleration m/s²','Heading / turn °','Reversals','Span / samples','Path m'].map(label=><th key={label} className="pr-3 py-1 whitespace-nowrap">{label}</th>)}</tr></thead><tbody>{analysis.tracks.map(track=><tr key={track.id}><td className="pr-3 py-1">{track.id}</td><td className="pr-3">{value(track.speed_mps)}<br/><span className="text-[10px] text-slate-500">{track.velocity_origin}</span></td><td className="pr-3">{value(track.acceleration_magnitude_mps2)}</td><td className="pr-3">{value(track.heading_degrees,1)} / {value(track.direction_change_degrees,1)}</td><td className="pr-3">{track.reversals_in_window}</td><td className="pr-3 whitespace-nowrap">{value(track.observed_span_seconds,1)}s / {track.sample_count}</td><td>{value(track.path_length_m)}</td></tr>)}</tbody></table></div></details>}
    {!!analysis?.highlighted_track_ids.length&&<p>Amber schematic avatars mark supported motion-review candidates; red marks a supported fall indication. Proximity does not establish violence; body poses are not measured.</p>}
    {analysis?.timestamp&&<p className="text-[10px] text-slate-500">Analysis frame: {analysis.timestamp} · {analysis.rule_version} · Features are rules/estimates, not ML confidence or accuracy.</p>}
  </section>;
}
