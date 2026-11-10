import React from 'react';
import { CameraMonitoringPanel } from '../components/analysis/CameraMonitoringPanel';
import { useSafeSenseApp } from '../context/SafeSenseContext';

export const LiveMonitoringPage: React.FC = () => {
  const { sensorEvents, zones, setSelectedZoneId, setActivePage } = useSafeSenseApp();
  const recent = [...sensorEvents].sort((a,b)=>b.timestamp.localeCompare(a.timestamp)).slice(0,6);
  return <div className="space-y-3 min-w-0">
    <CameraMonitoringPanel />
    <section aria-label="Recent Events" className="p-3 bg-white border border-slate-200 rounded-2xl space-y-3">
      <h2 className="font-bold text-sm">Recent Events</h2>
      {!recent.length && <p className="text-sm text-slate-500">No recorded events available. Camera analysis results appear above when completed.</p>}
      <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-2">{recent.map(event=>{
        return <article key={event.id} className="p-3 border border-slate-200 rounded-xl text-xs space-y-1 min-w-0">
          <p className="font-semibold">{event.type} / {zones.find(z=>z.id===event.zone_id)?.name||event.zone_id}</p>
          <p className="text-xs text-slate-500">{event.processing_mode} / {event.model_version||event.source}</p>
          <time className="text-xs" dateTime={event.timestamp}>{new Date(event.timestamp).toLocaleString()}</time>
          <button className="block text-blue-700 underline" onClick={()=>{setSelectedZoneId(event.zone_id);setActivePage('digital_twin');}}>View zone</button>
        </article>;
      })}</div>
    </section>

  </div>;
};
