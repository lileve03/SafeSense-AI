import React, { useEffect, useState } from 'react';
import { ScenarioTestingLibrary } from '../components/analysis/ScenarioTestingLibrary';
import { VideoAnalysisPanel } from '../components/analysis/VideoAnalysisPanel';
import { SensorEventPanel } from '../components/analysis/SensorEventPanel';
import { ImportedReplayLab } from '../components/analysis/ImportedReplayLab';
import { useSafeSenseApp } from '../context/SafeSenseContext';
import { api, post } from '../lib/api';

function SavedScenarioTests() {
  const { setIsLiveMode, setSelectedZoneId, setSelectedAlertId, checkFastApiConnection } = useSafeSenseApp();
  const [sources, setSources] = useState<any[]>([]);
  const [busy, setBusy] = useState(false), [error, setError] = useState('');
  useEffect(() => {
    let alive = true;
    api<any[]>('/monitoring/scenarios').then(rows => { if (alive) setSources(rows); }).catch(e => { if (alive) setError(String(e)); });
    return () => { alive = false; };
  }, []);
  async function run(source: any) {
    setBusy(true); setError('');
    try {
      const data = await post(`/monitoring/scenarios/${source.id}/run`, {});
      setIsLiveMode(true); setSelectedZoneId(source.zone_id); await checkFastApiConnection();
      if (data.incident) setSelectedAlertId(data.incident.id);
    } catch (e) { setError(String(e)); } finally { setBusy(false); }
  }
  return <section className="p-5 bg-white border border-slate-200 rounded-2xl space-y-3">
    <h3 className="font-bold">Saved predictions &amp; controlled tests</h3>
    {error && <p role="alert" className="text-red-700">{error}</p>}
    {sources.filter(source => ['sensor_metadata', 'controlled_test'].includes(source.input_type)).map(source => <div className="p-3 border border-slate-200 rounded-xl space-y-1" key={source.id}>
      <strong>{source.name}</strong>
      <p className="text-xs text-slate-500">{source.dataset} / {source.source_type} / {source.processing_mode}</p>
      <p className="text-xs">{source.limitations}</p>
      <button disabled={busy || !source.available} className="text-sm text-blue-700 underline disabled:opacity-50" onClick={() => run(source)}>{source.processing_mode === 'simulation' ? 'Run explicitly labeled test' : 'Replay saved model prediction'}</button>
    </div>)}
  </section>;
}

export function DeveloperTestingPage() {
  const { setActivePage } = useSafeSenseApp();
  return <div data-testid="developer-testing-page" className="space-y-5 min-w-0">
    <header className="p-5 bg-white border border-slate-200 rounded-2xl space-y-2">
      <h2 className="text-xl font-bold">Developer / testing tools</h2>
      <p className="text-sm text-slate-500">Research recordings, model evaluation inputs and explicitly labeled prototype tests.</p>
      <button className="text-sm text-blue-700 underline" onClick={() => setActivePage('live_monitoring')}>Return to Live Monitoring</button>
    </header>
    <ImportedReplayLab />
    <ScenarioTestingLibrary />
    <VideoAnalysisPanel />
    <SensorEventPanel />
    <SavedScenarioTests />
  </div>;
}
