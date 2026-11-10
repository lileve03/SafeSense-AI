import React, { useEffect, useRef, useState } from 'react';
import { AI_BASE, AI_TOKEN } from '../../lib/api';
import { useSafeSenseApp } from '../../context/SafeSenseContext';

export function VideoAnalysisPanel() {
  const { zones, setIsLiveMode, checkFastApiConnection, setSelectedZoneId, setSelectedAlertId } = useSafeSenseApp();
  const [zoneId, setZoneId] = useState('ZONE_CORRIDOR_A');
  const [model, setModel] = useState('v3');
  const [kind, setKind] = useState('fight');
  const [authorized, setAuthorized] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [result, setResult] = useState<any>(null);
  const [health, setHealth] = useState('Checking AI service…');
  const [available, setAvailable] = useState<string[]>([]);
  const request = useRef<AbortController | null>(null);
  useEffect(() => {
    let active = true;
    fetch(AI_BASE+'/ai/fight/models', {signal: AbortSignal.timeout(5000)}).then(async r => {
      if (!r.ok) throw new Error('AI service unavailable');
      const models = await r.json();
      if (active) { setAvailable(models.filter((m: any) => m.available).map((m: any) => m.version)); setHealth('AI service connected · CPU · offline analysis'); }
    }).catch(() => { if (active) setHealth('AI service offline — start port 8001'); });
    return () => { active = false; request.current?.abort(); };
  }, []);
  useEffect(() => {
    setResult(null); setError('');
    if (!file) { setPreview(''); return; }
    const url = URL.createObjectURL(file); setPreview(url);
    return () => URL.revokeObjectURL(url);
  }, [file]);
  async function analyze() {
    if (!file) return;
    setResult(null); setError('');
    if (file.size > 100*1024*1024) { setError('Upload limit is 100 MB'); return; }
    setBusy(true);
    const controller = new AbortController(); request.current = controller;
    const timeout = setTimeout(() => controller.abort(), 240000);
    try {
      const form = new FormData(); form.set('file',file); form.set('zone_id',zoneId);
      form.set('authorized', String(authorized)); form.set('model_version',model);
      const response = await fetch(`${AI_BASE}/ai/${kind}/analyze`, {method:'POST',body:form,headers:{'X-SafeSense-Token':AI_TOKEN}, signal:controller.signal});
      const data = await response.json();
      if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : `HTTP ${response.status}`);
      setResult(data); setIsLiveMode(true); setSelectedZoneId(zoneId); await checkFastApiConnection();
    } catch (e) { setError(e instanceof Error ? e.message : String(e)); }
    finally { clearTimeout(timeout); setBusy(false); request.current=null; }
  }
  return <section className="p-5 rounded-2xl bg-white border border-slate-200 space-y-4">
    <div><h3 className="font-bold text-lg">Public-area Video Analysis</h3><p className="text-xs text-slate-500">{health}</p></div>
    <p className="text-sm">Use authorized public-area recordings only. Private zones reject video. Scores are uncalibrated model outputs; candidates require human review.</p>
    <div className="flex flex-wrap gap-3">
      <label className="text-sm">Zone <select aria-label="Analysis zone" disabled={busy} value={zoneId} onChange={e=>{setZoneId(e.target.value);setResult(null);}} className="border rounded p-2 ml-2">{zones.filter(z=>!z.isPrivate).map(z=><option key={z.id} value={z.id}>{z.name}</option>)}</select></label>
      <label className="text-sm">Analysis <select aria-label="Analysis type" disabled={busy} value={kind} onChange={e=>{setKind(e.target.value);setResult(null);}} className="border rounded p-2 ml-2"><option value="fight">Possible physical conflict</option><option value="fall">YOLO11-Pose · Experimental fall rule</option></select></label>
      {kind==='fight' && <label className="text-sm">Model <select aria-label="Fight model" disabled={busy} value={model} onChange={e=>{setModel(e.target.value);setResult(null);}} className="border rounded p-2 ml-2"><option value="v2">V2 · threshold 0.4</option><option value="v3">V3 · threshold 0.7</option></select></label>}
    </div>
    <p className="text-xs text-slate-500">Available classifier files: {available.join(', ') || 'none reported'}. Maximum 100 MB, 120 seconds, 3600 frames and 1920×1080. Fall analysis has a 180-second processing budget.</p>
    <input aria-label="Video upload" type="file" accept=".mp4,.avi,.mpg,.mpeg" disabled={busy} onChange={e=>setFile(e.target.files?.[0] || null)} />
    <label className="flex items-center gap-2 text-sm"><input type="checkbox" disabled={busy} checked={authorized} onChange={e=>setAuthorized(e.target.checked)} />I am authorized to analyze this public-area recording.</label>
    <button disabled={busy || !authorized || !file} onClick={analyze} className="bg-blue-600 text-white rounded-xl px-4 py-2 disabled:opacity-50">{busy ? 'Analyzing on CPU…' : 'Run real analysis'}</button>
    {busy && <p role="status" className="text-sm">Processing the selected recording. Playback is independent; analysis does not follow the playhead.</p>}
    {error && <p role="alert" className="text-red-700">{error}</p>}
    {preview && <video key={preview} src={preview} controls preload="metadata" className="w-full max-w-xl rounded-xl bg-slate-950" />}
    {result && <div className="p-4 rounded-xl bg-slate-50 space-y-2 text-sm" aria-live="polite">
      <h4 className="font-bold">{result.candidate_detected ? 'Possible incident — human review required' : 'No candidate flagged; safety is not guaranteed'}</h4>
      <p>Model: {result.model_version} · Mode: {result.processing_mode} · Review: {result.review_status}</p>
      {kind==='fight' && <p>Whole-video score: {result.score.toFixed(6)} · Threshold: {result.threshold} · Class: {result.prediction}</p>}
      <p>Video: {result.video_duration_sec}s · Processing: {result.inference_time_sec}s</p>
      <p>{result.note}</p>
      {result.events?.map((e: any,i: number)=><p key={i}>{e.time_sec}s · {e.type} · {e.reason}</p>)}
      <p className={result.event_delivery.status==='failed' ? 'text-red-700' : ''}>Backend event: {result.event_delivery.status} {result.event_delivery.error || ''}</p>
      {result.event_delivery.incident_id && <button className="text-blue-700 underline" onClick={()=>setSelectedAlertId(result.event_delivery.incident_id)}>Open incident details</button>}
      {result.annotated_video_url && <div><p>Actual pose boxes and skeletons. {result.encoding_note}.</p><video src={`${AI_BASE}${result.annotated_video_url}?token=${encodeURIComponent(AI_TOKEN)}`} controls className="w-full max-w-xl bg-slate-950 rounded-xl" /><a className="text-blue-700 underline" href={`${AI_BASE}${result.annotated_video_url}?token=${encodeURIComponent(AI_TOKEN)}`} target="_blank" rel="noreferrer">Open annotated MP4</a></div>}
    </div>}
  </section>;
}
