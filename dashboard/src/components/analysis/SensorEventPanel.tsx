import {sosNotificationOutcome} from '../../lib/sosNotificationOutcome';
import { PrivateRecordedSensorPanel } from './PrivateRecordedSensorPanel';
import React, { useEffect, useRef, useState } from 'react';
import { api, post } from '../../lib/api';
import { useSafeSenseApp } from '../../context/SafeSenseContext';

export function SensorEventPanel({ zoneId, privateOnly = false, autoOpenIncident = true, replayOnly = false }: {
  zoneId?: string; privateOnly?: boolean; autoOpenIncident?: boolean; replayOnly?: boolean;
} = {}) {
  const { zones, checkFastApiConnection, setIsLiveMode, setSelectedZoneId, setSelectedAlertId } = useSafeSenseApp();
  const [zone, setZone] = useState(zoneId || 'ZONE_TOILET_BLINDSPOT');
  const [options, setOptions] = useState<any[]>([]);
  const [selected, setSelected] = useState('');
  const [message, setMessage] = useState('');
  const [busy, setBusy] = useState(false);
  const sending = useRef(false);
  useEffect(() => { if (zoneId) setZone(zoneId); }, [zoneId]);
  useEffect(()=>{ api<any[]>('/sensors/replay').then(setOptions).catch(e=>setMessage(String(e))); },[]);
  async function send(path: string, body: any) {
    if (sending.current) return;
    sending.current = true;
    setBusy(true); setMessage('');
    try {
      let result: any;
      for (const payload of (Array.isArray(body) ? body : [body])) result = await post(path,payload);
      setIsLiveMode(true); setSelectedZoneId(zone);
      await checkFastApiConnection();
      setMessage(result.deduplicated ? 'Already recorded: showing the original incident and observation timestamp.' : result.event ? `${result.event.processing_mode} · ${result.event.type} · ${result.event.level}: ${result.event.reason}` : result.note || result.status);
      if(result.event?.type==='sos'&&result.incident?.id)setMessage((await sosNotificationOutcome(result.incident.id)).message);
      if (result.incident && autoOpenIncident) setSelectedAlertId(result.incident.id);
    } catch(e) { setMessage(String(e)); } finally { sending.current = false; setBusy(false); }
  }
  return <section className="p-5 rounded-2xl bg-white border border-slate-200 space-y-3">
    <h3 className="font-bold">Sensor Replay & SOS Demo</h3>
    <p className="text-sm">No physical hardware is connected. Replay uses saved TI IWR6843 / YAMNet evaluation predictions, not new live measurements. Private areas use metadata only: no cameras, audio recording or transcription.</p>
    <label className="text-sm">Zone <select aria-label="Sensor zone" disabled={busy || !!zoneId} value={zone} onChange={e=>setZone(e.target.value)} className="border p-2 rounded ml-2">{zones.filter(z=>!privateOnly || z.isPrivate).map(z=><option key={z.id} value={z.id}>{z.name} ({z.isPrivate?'Private':'Public'})</option>)}</select></label>
    <div className="flex flex-wrap gap-2"><select aria-label="Recorded sensor result" disabled={busy} value={selected} onChange={e=>setSelected(e.target.value)} className="border p-2 rounded max-w-full"><option value="">Choose saved recording prediction</option>{options.map(o=><option key={`${o.sensor}:${o.index}`} value={`${o.sensor}:${o.index}`}>{o.sensor} · {o.model} · {o.label} · {o.candidate?'candidate':'not flagged'}</option>)}</select><button className="bg-teal-700 text-white rounded px-3 py-2 disabled:opacity-50" disabled={busy || !selected} onClick={()=>{const [sensor,index]=selected.split(':');send('/sensors/replay',{zone,sensor,index:Number(index)});}}>Replay recorded prediction</button></div>
    {!replayOnly&&<div className="flex flex-wrap gap-2"><button disabled={busy} className="border border-teal-600 text-teal-800 rounded px-3 py-2 text-sm" onClick={()=>send('/event',[{zone,type:'fall',source:'radar',confidence:.95,processing_mode:'simulation'},{zone,type:'scream',source:'yamnet',confidence:.95,processing_mode:'simulation'}])}>Simulate radar + acoustic fusion</button>{(privateOnly ? [['presence','radar'],['normal_motion','radar'],['rapid_motion','radar'],['fall','radar'],['scream','yamnet'],['impact','yamnet']] : [['fall','radar'],['scream','yamnet'],['impact','yamnet']]).map(([type,source])=><button key={type} disabled={busy} className="border rounded px-3 py-2 text-sm" onClick={()=>send('/event',{zone,type,source,confidence:.95,processing_mode:'simulation'})}>Simulate {type}</button>)}<button disabled={busy} className="bg-red-700 text-white rounded px-3 py-2" onClick={()=>send('/event',{zone,type:'sos',source:'sos_button',confidence:1,processing_mode:'simulation'})}>Trigger test SOS</button></div>}
    <p className="text-xs text-slate-500">Fusion combines independent sources in the same zone and processing mode within 5 seconds. Use simulated radar fall + simulated acoustic scream to demonstrate fusion. Dataset replays are unrelated recordings, not evidence of a real shared incident. Test SOS immediately creates a Critical incident; no emergency dispatch occurs.</p>
    {privateOnly && <PrivateRecordedSensorPanel key={zone} zoneId={zone} />}
    {message && <p role="status" className="text-sm">{message}</p>}
  </section>;
}
