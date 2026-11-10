import React, { useEffect, useState } from 'react';
import { api, AI_BASE } from '../../lib/api';
export function OperationalStatistics() {
  const [data,setData]=useState<any>(null),[error,setError]=useState('');
  useEffect(()=>{let active=true;const refresh=()=>api('/analytics/incidents').then(r=>{if(active)setData(r);}).catch(e=>{if(active)setError(String(e));});void refresh();const timer=setInterval(refresh,3000);return()=>{active=false;clearInterval(timer);};},[]);
  return <section className="p-5 bg-white rounded-2xl border border-slate-200 space-y-3"><h3 className="font-bold">Operational incident statistics</h3>{error&&<p role="alert">{error}</p>}{data&&<><p className="text-sm">{data.candidates} candidate incidents · {data.false_alerts_reviewed} reviewed false alerts · Mean acknowledgement: {data.mean_acknowledgement_seconds===null?'not measured':`${data.mean_acknowledgement_seconds.toFixed(1)} seconds`}</p><div className="flex flex-wrap gap-3 text-sm">{Object.entries(data.by_source).map(([source,count])=><span key={source} className="p-2 bg-slate-50 rounded border">{source}: {String(count)}</span>)}</div><p className="text-xs">{data.note}</p></>}</section>;
}
export function ResearchMetrics() {
  const [data,setData]=useState<any[]>([]); const [error,setError]=useState('');
  useEffect(()=>{api<any[]>('/analytics/evaluations').then(setData).catch(e=>setError(String(e)));},[]);
  return <section className="p-5 bg-white rounded-2xl border border-slate-200 space-y-4"><h3 className="font-bold">Saved Research Evaluations</h3><p className="text-sm">These are repository evaluation artifacts, not verified real-world school performance. Confusion counts: TN / FP / FN / TP. Fall rules remain experimental; impact evaluation is unavailable.</p>{error && <p role="alert">{error}</p>}{data.map(d=><div key={d.path}><p className="text-sm font-semibold">{d.scope}</p><p className="text-xs text-slate-500">{d.path}</p><div className="overflow-x-auto"><table className="text-xs w-full my-2"><thead><tr>{Object.keys(d.rows[0]||{}).map(k=><th className="border p-2 text-left" key={k}>{k}</th>)}</tr></thead><tbody>{d.rows.map((row: any,i: number)=><tr key={i}>{Object.entries(row).map(([k,v])=><td className="border p-2" key={k}>{String(v)}</td>)}</tr>)}</tbody></table></div></div>)}</section>;
}

export function ServiceEvidenceStatus() {
  const [status,setStatus]=useState('Checking AI service…'); const [insights,setInsights]=useState<any[]>([]);
  useEffect(()=>{let active=true; async function refresh(){
    try { const r=await fetch(AI_BASE+'/health',{signal:AbortSignal.timeout(3000)}); if(!r.ok) throw new Error(); const h=await r.json(); if(active)setStatus(`AI connected · CPU · ${h.models.filter((m: any)=>m.available).map((m: any)=>m.version).join(', ')} classifier files available`); } catch {if(active)setStatus('AI service offline (8001)');}
    try {const rows=await api<any[]>('/insights');if(active)setInsights(rows);} catch {if(active)setInsights([]);}
  } refresh(); const timer=setInterval(refresh,10000);return()=>{active=false;clearInterval(timer);};},[]);
  return <section className="p-4 bg-white border border-slate-200 rounded-xl space-y-2 text-sm"><p>{status}</p><h3 className="font-semibold">Evidence-based Safety Insights</h3>{insights.length===0?<p>No active incident evidence available.</p>:insights.slice(0,4).map(i=><p key={i.incident_id}>{i.summary}</p>)}</section>;
}
