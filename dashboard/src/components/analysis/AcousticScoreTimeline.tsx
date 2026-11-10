import React, {useEffect, useState} from 'react';
type WindowScore={index:number;start_sec:number;end_sec:number;score:number;above_threshold:boolean};
// Adapted from Phase2 index.html plotAudio: draw genuine model scores plus the actual threshold.
export function AcousticScoreTimeline({windows,duration,threshold}:{windows:WindowScore[];duration:number;threshold:number}) {
 const [time,setTime]=useState(0),[playing,setPlaying]=useState(false);
 useEffect(()=>{setTime(0);setPlaying(false);},[windows]);
 useEffect(()=>{
  if(!playing)return;
  const start=performance.now(),origin=time;let handle=0;
  const tick=()=>{const next=Math.min(duration,origin+(performance.now()-start)/1000);setTime(next);if(next>=duration)setPlaying(false);else handle=requestAnimationFrame(tick);};
  handle=requestAnimationFrame(tick);return()=>cancelAnimationFrame(handle);
 },[playing,duration]);
 const frame=windows.filter(w=>w.start_sec<=time).at(-1)||windows[0];
 if(!frame||!(duration>0))return null;
 const points=windows.map(w=>`${20+w.start_sec/duration*600},${110-w.score*90}`).join(' ');
 return <section data-testid="acoustic-score-timeline" data-window-index={frame.index} className="rounded-xl border border-slate-200 p-3 space-y-2 text-xs">
  <h5 className="font-semibold">Recorded acoustic model windows</h5>
  <p className="text-slate-500">Non-speech class scores only. Nominal 0.48s hops / 0.96s windows; padding and overlap apply. These are not validated event times or live audio.</p>
  <svg role="img" aria-label="Actual YAMNet Screaming window scores" viewBox="0 0 640 140" className="w-full">
   <line x1="20" x2="620" y1={110-threshold*90} y2={110-threshold*90} stroke="#b45309" strokeDasharray="5 4"/>
   <polyline data-testid="acoustic-score-line" points={points} fill="none" stroke="#0f766e" strokeWidth="2"/>
   <circle cx={20+frame.start_sec/duration*600} cy={110-frame.score*90} r="4" fill={frame.above_threshold?'#dc2626':'#0f766e'}/>
   <text x="20" y="132" fontSize="11">0s</text><text x="560" y="132" fontSize="11">{duration.toFixed(2)}s</text><text x="20" y="12" fontSize="11">Score 0-1; threshold {threshold}</text>
  </svg>
  <label className="block">Recording offset: {time.toFixed(2)}s<input aria-label="Acoustic score replay offset" type="range" min="0" max={duration} step="0.01" value={time} onChange={e=>{setPlaying(false);setTime(Number(e.target.value));}} className="block w-full"/></label>
  <div className="flex flex-wrap gap-2"><button className="border rounded px-2 py-1" onClick={()=>{if(time>=duration)setTime(0);setPlaying(v=>!v);}}>{playing?'Pause score replay':'Play score replay'}</button><button className="border rounded px-2 py-1" onClick={()=>{setPlaying(false);setTime(windows.reduce((a,b)=>b.score>a.score?b:a).start_sec);}}>Inspect peak window</button></div>
  <p data-testid="acoustic-window-detail">Window {frame.index}: {frame.start_sec.toFixed(2)}-{frame.end_sec.toFixed(2)}s / score {frame.score.toFixed(6)} (uncalibrated) / {frame.above_threshold?'above threshold':'below threshold'}</p>
  <p className="text-slate-500">Replay controls change the visualization only; they never create incidents, record speech or correlate independent recordings.</p>
 </section>;
}
