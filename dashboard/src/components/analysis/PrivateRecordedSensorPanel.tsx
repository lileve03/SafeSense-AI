import {AcousticScoreTimeline} from './AcousticScoreTimeline';
import React, { useEffect, useRef, useState } from 'react';
import { api, post } from '../../lib/api';
import { useSafeSenseApp } from '../../context/SafeSenseContext';

export function PrivateRecordedSensorPanel({ zoneId }: { zoneId: string }) {
  const { checkFastApiConnection, setIsLiveMode } = useSafeSenseApp();
  const [sources, setSources] = useState<any[]>([]);
  const [selected, setSelected] = useState('');
  const [authorized, setAuthorized] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');
  const [result, setResult] = useState<any>(null);
  const running = useRef(false);
  const mounted = useRef(true);
  useEffect(() => {
    mounted.current = true;
    api<any[]>('/testing/scenarios').then(rows => {
      if (mounted.current) setSources(rows.filter(s => s.zone_id === zoneId && ['radar_recording', 'audio_sample'].includes(s.input_type) && s.execution_kind === 'fresh_inference'));
    }).catch(e => { if (mounted.current) setMessage(String(e)); });
    return () => { mounted.current = false; };
  }, [zoneId]);
  async function run() {
    const source = sources.find(s => s.id === selected);
    if (!source || !authorized || running.current) return;
    running.current = true; setBusy(true); setResult(null); setMessage('Preparing recorded sensor analysis');
    try {
      let row = await post('/testing/runs', { scenario_id: source.id, model: source.default_model, authorized: true });
      const deadline = Date.now() + 210000;
      while (['QUEUED', 'RUNNING'].includes(row.status)) {
        if (!mounted.current) return;
        if (Date.now() > deadline) throw new Error('Analysis is still running; inspect Scenario Testing history.');
        setMessage(`${row.status}: recorded input, not live hardware`);
        await new Promise(resolve => setTimeout(resolve, 1000));
        row = await api<any>(`/testing/runs/${row.id}`);
      }
      if (row.status !== 'COMPLETED') throw new Error(row.error || row.status);
      if (!mounted.current) return;
      setResult(row.result);
      setMessage(row.result.event_delivery?.deduplicated ? 'Already recorded: original incident retained.' : 'Recorded model output synchronized to incidents and sensor observations.');
      setIsLiveMode(true); await checkFastApiConnection();
    } catch (e) { if (mounted.current) setMessage(String(e)); }
    finally { running.current = false; if (mounted.current) setBusy(false); }
  }
  return <div className="border-t border-slate-200 pt-3 space-y-2">
    <h4 className="font-semibold">Analyze recorded sensor input</h4>
    <p className="text-xs text-slate-500">Fresh local inference on registered research files. No microphone, CCTV, speech recording or live hardware. Independent recordings cannot establish synchronized fusion.</p>
    <select aria-label="Raw sensor recording" disabled={busy} value={selected} onChange={e => { setSelected(e.target.value); setResult(null); }} className="border rounded p-2 max-w-full"><option value="">Choose radar or non-speech acoustic recording</option>{sources.map(s => <option key={s.id} value={s.id} disabled={!s.ready}>{s.name} - {s.default_model}</option>)}</select>
    <label className="flex gap-2 text-xs"><input type="checkbox" checked={authorized} disabled={busy} onChange={e => setAuthorized(e.target.checked)} />Use authorized offline research input</label>
    <button disabled={busy || !authorized || !selected} onClick={run} className="rounded bg-teal-700 text-white px-3 py-2 disabled:opacity-50">Analyze recording</button>
    {message && <p role="status" className="text-xs">{message}</p>}
    {result && <dl className="text-xs space-y-1"><div>Model: {result.model_version}</div><div>Model score (uncalibrated): {result.score ?? 'Unavailable'}</div><div>Candidate: {result.candidate_detected ? 'Yes' : 'No'}; scope: recording only</div><div className="break-all">Input SHA-256: {result.input_sha256}</div><div>Occupant count, position and distance: unavailable</div></dl>}
    {result?.score_windows?.length>0 && <AcousticScoreTimeline windows={result.score_windows} duration={result.audio_duration_sec} threshold={result.threshold}/>}
  </div>;
}

