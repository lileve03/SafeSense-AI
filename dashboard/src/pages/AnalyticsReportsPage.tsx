import React, {useEffect, useMemo, useRef, useState} from 'react';
import {BarChart3, RefreshCw, ShieldCheck, ArrowUpRight} from 'lucide-react';
import {api} from '../lib/api';
import {download} from '../lib/reportExport';
import {buildVisualReport,visualReportPdf,printVisualReport,fingerprint,VisualReport,ReportZone} from '../lib/visualReport';
import {filteredIncidentsCsv,exportDatasetId,ExportSnapshot} from '../lib/filteredReportCsv';
import {loadReportEvidence} from '../lib/reportEvidence';
import {AnalyticsFilters, IncidentRecord, initialAnalyticsFilters, filterIncidents, summarizeIncidents, modeLabels, sourceLabels, durationLabel} from '../lib/incidentAnalytics';
import {CountChart} from '../components/analysis/CountChart';
import {IncidentReportView} from '../components/incidents/IncidentReportView';
import './analyticsReports.css';

const card='p-4 md:p-5 rounded-2xl bg-white border border-slate-200 min-w-0';
const control='block w-full mt-1 border border-slate-200 rounded-lg p-2 bg-white text-slate-900 text-xs';
const readable=(s:string)=>s.replaceAll('_',' ');
const colors:Record<string,string>={LOW:'#047857',OBSERVE:'#b45309',WARNING:'#b45309',HIGH:'#c2410c',CRITICAL:'#b91c1c'};
const eventTypes=(r:IncidentRecord)=>[...new Set((r.evidence||[]).flatMap(e=>e.type?[e.type]:[]))];

export function AnalyticsReportsPage(){
  const [records,setRecords]=useState<IncidentRecord[]|null>(null),[zones,setZones]=useState<ReportZone[]>([]);
  const [filters,setFilters]=useState<AnalyticsFilters>({...initialAnalyticsFilters,eventType:'all'});
  const [exportBusy,setExportBusy]=useState(false),[exportError,setExportError]=useState('');
  const snapshotCache=useRef<{key:string;value:ExportSnapshot}|null>(null);
  const reportCache=useRef<{key:string;value:Promise<VisualReport>}|null>(null);
  const [metricsOpen,setMetricsOpen]=useState(false);
  const [selectedId,setSelectedId]=useState(''),[reportOpen,setReportOpen]=useState(true);
  const [error,setError]=useState(''),[zoneError,setZoneError]=useState(''),[updated,setUpdated]=useState(''),[refreshing,setRefreshing]=useState(false);
  const refresh=useRef<()=>void>(()=>{}),reportSection=useRef<HTMLElement>(null);
  useEffect(()=>{
    let active=true,revision=0,controller:AbortController|null=null;
    refresh.current=async()=>{
      const current=++revision;controller?.abort();controller=new AbortController();setRefreshing(true);
      const signal=AbortSignal.any([controller.signal,AbortSignal.timeout(10000)]);
      const [result,labels]=await Promise.allSettled([api<IncidentRecord[]>('/incidents',{signal}),api<ReportZone[]>('/zones',{signal})]);
      if(!active||current!==revision)return;
      if(result.status==='fulfilled'&&Array.isArray(result.value)){setRecords(result.value);setUpdated(new Date().toISOString());setError('');}
      else setError('Unable to refresh saved incidents.');
      if(labels.status==='fulfilled'&&Array.isArray(labels.value)){setZones(labels.value);setZoneError('');}
      else setZoneError('Zone names unavailable; recorded IDs shown.');
      setRefreshing(false);
    };
    void refresh.current();const timer=setInterval(()=>refresh.current(),15000);
    return()=>{active=false;revision++;controller?.abort();clearInterval(timer);};
  },[]);
  const invalidRange=filters.range==='custom'&&!!filters.from&&!!filters.to&&filters.from>filters.to;
  const selected=useMemo(()=>invalidRange?[]:filterIncidents(records||[],filters),[records,filters,invalidRange]);
  const stats=useMemo(()=>summarizeIncidents(selected),[selected]);
  const currentId=selected.some(r=>r.id===selectedId)?selectedId:selected[0]?.id||'';
  useEffect(()=>{if(selectedId!==currentId)setSelectedId(currentId);},[currentId,selectedId]);
  const zoneName=(id:string)=>zones.find(z=>z.id===id)?.name||id;
  const change=(key:keyof AnalyticsFilters,value:string)=>setFilters(f=>({...f,[key]:value}));
  const values=(field:'processing_mode'|'zone_id'|'source'|'level'|'status')=>[...new Set((records||[]).map(r=>r[field]||'unknown'))].sort();
  const grouped=(items:{key:string;count:number}[],name=readable)=>items.map(row=>({...row,name:name(row.key)}));
  const select=(title:string,key:keyof AnalyticsFilters,options:{key:string;name:string}[])=>
    <label className="block min-w-0 text-xs text-slate-600">{title}<select aria-label={'Analytics '+title.toLowerCase()} className={control} value={filters[key]||'all'} onChange={e=>change(key,e.target.value)}><option value="all">All</option>{options.map(o=><option key={o.key} value={o.key}>{o.name}</option>)}</select></label>;
  const kpis=[
    {id:'total',title:'Total Incidents',value:stats.total,note:'Saved incident IDs'},
    {id:'high',title:'High Risk',value:selected.filter(r=>['HIGH','CRITICAL'].includes(r.level)).length,note:'High + critical'},
    {id:'sos',title:'SOS',value:selected.filter(r=>r.source==='sos_button'||eventTypes(r).some(t=>t.toLowerCase()==='sos')).length,note:'Incidents with SOS input'},
    {id:'pending',title:'Pending Review',value:selected.filter(r=>r.review_status==='pending_human_review').length,note:'Awaiting human review'},
    {id:'resolved',title:'Resolved',value:stats.resolved,note:'Resolved outcome'},
    {id:'ack-time',title:'Average Response Time',value:durationLabel(stats.meanAck),note:`Creation → acknowledgement · ${stats.ackSamples} samples`},
  ];
  async function exportVisual(kind:'pdf'|'print'|'csv'){
    if(records===null||invalidRange)return;
    setExportBusy(true);setExportError('');
    try{
      // All three formats freeze the same current backend selection. CSV never waits for media.
      const key=fingerprint({records:selected,zones,filters,stale:!!error});
      if(snapshotCache.current?.key!==key)snapshotCache.current={key,value:structuredClone({records:selected,zones,filters,snapshotAt:updated,stale:!!error,generatedAt:new Date().toISOString()})};
      const frozen=snapshotCache.current.value;
      if(kind==='csv'){
        download(new Blob([filteredIncidentsCsv(frozen)],{type:'text/csv;charset=utf-8'}),`SafeSense-visual-report-${exportDatasetId(frozen)}.csv`);
        return;
      }
      if(reportCache.current?.key!==key){
        const generatedAt=frozen.generatedAt;
        const value=loadReportEvidence(frozen.records,frozen.zones).then(evidence=>buildVisualReport({...frozen,generatedAt,evidence}));
        reportCache.current={key,value};
      }
      const report=await reportCache.current!.value;
      if(kind==='pdf')download(visualReportPdf(report).output('blob'),`SafeSense-visual-report-${report.fingerprint}.pdf`);
      else await printVisualReport(report);
    }catch(e){reportCache.current=null;setExportError('Visual report failed: '+String(e));}
    finally{setExportBusy(false);}
  }
  function openReport(id:string){setSelectedId(id);setReportOpen(true);requestAnimationFrame(()=>reportSection.current?.scrollIntoView({behavior:'smooth',block:'start'}));}
  const scope=`Selected incident ${currentId}; filters: ${JSON.stringify(filters)}; selected records: ${selected.length}`;
  return <div className="analytics-reports space-y-5 min-w-0" data-testid="analytics-reports">
    <header className="flex flex-wrap items-center justify-between gap-4 py-1">
      <div><p className="text-[10px] font-semibold uppercase tracking-[.18em] text-cyan-700 mb-2">SafeSense / Operations Intelligence</p><h2 className="text-2xl font-bold text-slate-900 flex gap-2 items-center"><BarChart3 className="w-6 h-6 text-blue-600"/>Analytics &amp; Reports</h2><p className="text-xs text-slate-600 mt-2">Saved incidents · Evidence · Response performance</p></div>
      <div className="flex items-center gap-3"><span className="text-[10px] text-slate-600">{updated?`Snapshot ${new Date(updated).toISOString().slice(11,19)} UTC`:'Connecting to backend'}</span><button onClick={()=>refresh.current()} disabled={refreshing} className="flex items-center gap-2 rounded-xl border border-slate-200 px-3 py-2 text-xs font-semibold text-blue-600 disabled:opacity-50"><RefreshCw className={'w-4 h-4 '+(refreshing?'animate-spin':'')}/>Refresh records</button></div>
    </header>
    <section aria-label="Filtered report exports" className="flex flex-wrap items-center justify-between gap-3">
      <p className="text-xs text-slate-600">Export the filtered snapshot as visual PDF or CSV</p>
      <div className="flex flex-wrap gap-2">{(['pdf','print','csv'] as const).map(kind=><button key={kind} disabled={exportBusy||records===null||invalidRange} onClick={()=>void exportVisual(kind)} className="px-4 py-2 rounded-xl bg-blue-600 text-white text-xs font-semibold disabled:opacity-50">{kind==='pdf'?'Download PDF':kind==='print'?'Print PDF':'Download CSV'}</button>)}</div>
      {exportBusy&&<p role="status" className="text-xs text-blue-700">Preparing vector charts and permitted evidence thumbnails...</p>}
      {exportError&&<p role="alert" className="text-xs text-red-700">{exportError}</p>}
    </section>
    <section className={card+' space-y-3'} aria-label="Analytics filters">
      <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-5 gap-3">
        <label className="text-xs text-slate-600">Date range (UTC)<select aria-label="Analytics date range" value={filters.range} onChange={e=>change('range',e.target.value)} className={control}><option value="all">All dates</option><option value="today">Today</option><option value="7days">Last 7 days</option><option value="30days">Last 30 days</option><option value="custom">Custom dates</option></select></label>
        {select('Zone','zone',values('zone_id').map(key=>({key,name:zoneName(key)})))}
        {select('Severity','severity',values('level').map(key=>({key,name:key})))}
        {select('Event type','eventType',summarizeIncidents(records||[]).types.map(r=>({key:r.key,name:readable(r.key)})))}
        {select('Processing mode','mode',values('processing_mode').map(key=>({key,name:modeLabels[key]||key})))}
      </div>
      {filters.range==='custom'&&<div className="flex flex-wrap gap-3 text-xs text-slate-600"><label>From (UTC)<input aria-label="Analytics from date" type="date" className={control} value={filters.from} onChange={e=>change('from',e.target.value)}/></label><label>To (UTC)<input aria-label="Analytics to date" type="date" className={control} value={filters.to} onChange={e=>change('to',e.target.value)}/></label></div>}
      <div className="flex flex-wrap items-center justify-between gap-3 border-t border-slate-200 pt-3">
        <details className="text-xs text-slate-600"><summary className="cursor-pointer text-blue-600">Response &amp; source filters</summary><div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mt-3">{select('Status','status',values('status').map(key=>({key,name:readable(key)})))}{select('Source','source',values('source').map(key=>({key,name:sourceLabels[key]||key})))}{select('Acknowledgement','ack',[{key:'acknowledged',name:'Acknowledged'},{key:'unacknowledged',name:'No acknowledgement recorded'}])}</div></details>
        <div className="flex items-center gap-4 text-xs"><span data-testid="analytics-selection-count" className="text-slate-600">{invalidRange?'Invalid date range':`${selected.length} of ${records?.length??'—'} records`}</span><button className="text-blue-600" onClick={()=>setFilters({...initialAnalyticsFilters,eventType:'all'})}>Reset filters</button></div>
      </div>
    </section>
    {error&&<p role="alert" className="rounded-xl border border-amber-200 bg-amber-50 text-amber-800 p-4 text-sm">{error} {records?'Showing the last successful snapshot; figures may be stale.':'No statistics are available until records load.'}</p>}
    {zoneError&&<p role="status" className="text-xs text-amber-700">{zoneError}</p>}
    {records===null&&!error&&<p role="status" className="text-slate-600">Loading saved incident records…</p>}
    {invalidRange?<p role="alert" className="text-amber-700">From date must be on or before To date.</p>:records!==null&&<>
      <div className="grid grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-3">{kpis.map(k=><div key={k.id} className={card+' relative overflow-hidden'} data-testid={'analytics-kpi-'+k.id}><p className="text-[11px] font-semibold text-slate-600">{k.title}</p><p data-value className={`text-2xl md:text-3xl font-bold tabular-nums my-2 ${k.id==='high'?'text-orange-700':k.id==='resolved'?'text-emerald-700':'text-slate-900'}`}>{k.value}</p><p className="text-[10px] text-slate-500 leading-relaxed">{k.note}</p></div>)}</div>
      <div className="flex flex-wrap gap-x-5 gap-y-2 text-[11px] text-slate-600" aria-label="Data provenance">{stats.modes.map(m=><span key={m.key} className="flex items-center gap-2"><span className={`w-1.5 h-1.5 rounded-full ${m.key==='real_model'?'bg-cyan-400':m.key==='simulation'?'bg-violet-400':'bg-amber-400'}`}/>{modeLabels[m.key]||readable(m.key)} <strong className="text-slate-900">{m.count}</strong></span>)}<span>Saved tests included · Not verified emergencies</span></div>
      {!selected.length?<p role="status" className={card+' text-sm text-slate-600'}>{records.length?'No incidents match the selected filters.':'No incident records are saved yet.'}</p>:<>
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
          <CountChart id="trend" title="Incident Trend" note={`UTC creation date${stats.undated?` · ${stats.undated} undated excluded`:''}`} rows={grouped(stats.trend)} trend/>
          <CountChart id="types" title="Event Type Distribution" note="Incidents per type · Multi-type incidents may overlap" rows={grouped(stats.types)}/>
          <CountChart id="zones" title="Incidents by Zone" note="Saved incident locations" rows={grouped(stats.zones,zoneName)}/>
          <CountChart id="severity" title="Severity Distribution" note="Current incident priority" rows={grouped(stats.severity).map(r=>({...r,color:colors[r.key]}))}/>
          <CountChart id="statuses" title="Resolution Status" note="Recorded workflow outcomes" rows={grouped(stats.statuses)}/>
          <CountChart id="acknowledgements" title="Acknowledgement Status" note="Based on saved acknowledgement timestamps" rows={grouped(stats.acknowledgements)}/>
        </div>
        <section className={card+' space-y-3'} aria-label="Incident evidence preview"><div className="flex flex-wrap justify-between items-center gap-2"><h3 className="font-bold text-sm text-slate-900">Incident Evidence</h3><span className="text-[10px] text-slate-600 flex items-center gap-1"><ShieldCheck className="w-3 h-3"/>Private areas: sensor metadata only</span></div><div className="grid sm:grid-cols-2 xl:grid-cols-4 gap-3">{stats.recent.slice(0,4).map(r=><button key={r.id} onClick={()=>openReport(r.id)} className="bg-slate-50 border border-slate-200 hover:border-blue-400 rounded-xl p-3 text-left min-w-0 text-xs space-y-2"><div className="flex justify-between gap-2"><span className="font-semibold text-slate-900 truncate">{zoneName(r.zone_id)}</span><ArrowUpRight className="w-3 h-3 shrink-0 text-blue-600"/></div><p className="text-slate-600 truncate">{eventTypes(r).join(' · ')||'No observations'}</p><p className="text-[10px] text-blue-600">{modeLabels[r.processing_mode||'']||r.processing_mode||'Mode not recorded'}</p><p className="text-[10px] text-slate-500 font-mono">#{r.id.slice(0,8)} · {r.level}</p></button>)}</div><p className="text-[10px] text-slate-500">Metadata previews · Open a report for permitted retained evidence.</p></section>
        <section className={card+' space-y-3'}><div className="flex flex-wrap justify-between items-center gap-2"><h3 className="font-bold text-sm text-slate-900">Incident Records <span className="text-slate-500 font-normal">/ {selected.length}</span></h3><span className="text-[10px] text-slate-600">Select a record to review or export</span></div><div className="overflow-x-auto max-h-96"><table aria-label="Report incidents" className="w-full text-left text-xs whitespace-nowrap"><thead className="bg-slate-50 text-slate-600 sticky top-0"><tr>{['Incident / UTC','Zone','Event Type','Severity','Status','Processing Mode',''].map((title,i)=><th key={i} className="px-3 py-3 font-medium">{title}</th>)}</tr></thead><tbody>{selected.map(r=><tr key={r.id} data-incident-id={r.id} className={`border-t border-slate-200 ${r.id===currentId?'bg-blue-50':''}`}><td className="p-3"><span className="block font-mono text-slate-900">#{r.id.slice(0,8)}</span><time className="text-[10px] text-slate-500">{r.created_at?.replace('T',' ').slice(0,19)||'Not recorded'}</time></td><td className="p-3 text-slate-700">{zoneName(r.zone_id)}</td><td className="p-3 max-w-44 truncate text-slate-600" title={eventTypes(r).join(', ')}>{eventTypes(r).join(', ')||'Not recorded'}</td><td className="p-3"><span style={{color:colors[r.level]||'#94a3b8'}}>{r.level}</span></td><td className="p-3 text-slate-700">{readable(r.status)}</td><td className="p-3 text-slate-600">{modeLabels[r.processing_mode||'']||r.processing_mode||'Not recorded'}</td><td className="p-3"><button className="text-blue-600 font-semibold" onClick={()=>openReport(r.id)}>View report</button></td></tr>)}</tbody></table></div></section>
      </>}
      <section ref={reportSection} className="space-y-3 scroll-mt-4" aria-label="Selected incident report">
        <div className={card+' space-y-2'}><div className="flex flex-wrap justify-between items-center gap-2"><h3 className="text-sm font-bold text-slate-900">Incident Report &amp; Exports</h3><button className="text-xs text-blue-600" onClick={()=>setReportOpen(v=>!v)}>{reportOpen?'Collapse report':'Expand report'}</button></div><select aria-label="Report incident" className={control} value={currentId} onChange={e=>{setSelectedId(e.target.value);setReportOpen(true);}}>{!selected.length&&<option value="">No matching incidents</option>}{selected.map(r=><option key={r.id} value={r.id}>#{r.id.slice(0,8)} · {zoneName(r.zone_id)} · {r.status}</option>)}</select><p className="text-[10px] text-slate-500">The top PDF, print and CSV actions export all filtered records. Individual incident CSV remains available below.</p></div>
        {reportOpen&&currentId&&<IncidentReportView key={currentId} id={currentId} scope={scope} operational onUpdated={()=>refresh.current()}/>}
      </section>
      <details onToggle={e=>setMetricsOpen(e.currentTarget.open)} className={card+' text-xs text-slate-600'}><summary className="cursor-pointer text-blue-600">Additional operational metrics</summary><div className="flex flex-wrap gap-4 py-3"><span>Open: {stats.open}</span><span>Acknowledged: {stats.acknowledged}</span><span>Awaiting acknowledgement: {stats.awaitingAck}</span><span>Average closure: {durationLabel(stats.meanClosure)}</span><span>Reviewed false alarms: {stats.falseAlarmRate===null?'Not measured':stats.falseAlarmRate.toFixed(1)+'%'}</span></div><div className="grid xl:grid-cols-2 gap-3"><CountChart renderChart={metricsOpen} id="sources" title="Detection Sources" note="Recorded initiating source" rows={grouped(stats.sources,k=>sourceLabels[k]||k)}/><CountChart renderChart={metricsOpen} id="modes" title="Processing Modes" note="Model inference, replay and simulation" rows={grouped(stats.modes,k=>modeLabels[k]||k)}/></div></details>
      <p className="text-[10px] text-slate-500">Response time measures creation to acknowledgement, not on-site arrival. Missing or negative timestamp pairs are excluded.</p>
    </>}
  </div>;
}
