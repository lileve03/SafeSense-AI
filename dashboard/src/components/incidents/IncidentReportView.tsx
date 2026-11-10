import {notificationStateLabel} from '../../lib/notificationState';
import React,{useEffect,useState} from 'react';
import {api,post} from '../../lib/api';
import {useSafeSenseApp} from '../../context/SafeSenseContext';
import {download,reportCsv,reportPdf,printReport} from '../../lib/reportExport';
import {IncidentTime} from '../../lib/incidentTime';
import {ShieldAlert,MapPin,Bell,Download,FileText,ScanEye,Clock3,Activity} from 'lucide-react';
import {IncidentEvidence} from './IncidentEvidence';

export function IncidentReportView({id,scope='Selected incident '+id,operational=false,onUpdated}:{id:string;scope?:string;operational?:boolean;onUpdated?:()=>void|Promise<void>}) {
  const {checkFastApiConnection,zones}=useSafeSenseApp();
  const [report,setReport]=useState<any>(null),[tab,setTab]=useState('Summary'),[error,setError]=useState('');
  const [staff,setStaff]=useState('Dashboard operator'),[note,setNote]=useState(''),[busy,setBusy]=useState(false);
  useEffect(()=>{
    let active=true;setReport(null);setError('');setTab('Summary');
    const refresh=()=>api(`/incidents/${id}/report`).then(r=>{
      if(!active)return;
      if(r.id!==id)throw new Error('Incident report identity mismatch');
      setReport(r);setError('');
    }).catch(e=>{if(active)setError(String(e));});
    void refresh();const timer=setInterval(refresh,2000);
    return()=>{active=false;clearInterval(timer);};
  },[id]);
  async function action(status:string) {
    setBusy(true);setError('');
    try {
      await post(`/incidents/${id}/${status==='ACKNOWLEDGED'?'ack':'review'}`,status==='ACKNOWLEDGED'?{staff}:{status,staff,note});
      setReport(await api(`/incidents/${id}/report`));await checkFastApiConnection();await onUpdated?.();
    } catch(e){setError(String(e));}finally{setBusy(false);}
  }
  async function exportReport(kind:'pdf'|'csv'|'print') {
    setBusy(true);setError('');
    try {
      const current=await api(`/incidents/${encodeURIComponent(id)}/report`);
      if(current.id!==id)throw new Error('Report identity mismatch');
      const generated=new Date().toISOString();
      const name='SafeSense-report-'+id.replace(/[^a-zA-Z0-9_-]/g,'_');
      if(kind==='pdf')download(reportPdf(current,scope,generated).output('blob'),name+'.pdf');
      else if(kind==='csv')download(new Blob([reportCsv(current)],{type:'text/csv;charset=utf-8'}),name+'.csv');
      else printReport(current,scope,generated);
    }catch(e){setError('Export failed: '+String(e));}finally{setBusy(false);}
  }
  if(!report||report.id!==id)return <p role="status" className="p-4 text-sm text-slate-500">{error||'Loading incident report...'}</p>;
  const closed=['RESOLVED','FALSE_ALARM'].includes(report.status);
  const observations=report.evidence||[];
  const attempts=report.notifications||[];
  const notification=notificationStateLabel(report.notification_state||attempts.at(-1)?.delivery_state||report.notification_status);
  const zone=zones.find(z=>z.id===report.zone_id)?.name||report.zone_id||'Not recorded';
  const history=[...(report.history||[])].sort((a:any,b:any)=>Date.parse(a.timestamp)-Date.parse(b.timestamp));
  const badge=report.level==='CRITICAL'?'bg-red-50 text-red-700 border-red-200':report.level==='HIGH'?'bg-orange-50 text-orange-800 border-orange-200':'bg-violet-50 text-violet-800 border-violet-200';
  const provenance=[report.source_type,report.processing_mode].filter(Boolean).join(' / ')||'Not recorded';
  return <article data-testid="incident-report" className="incident-investigation rounded-2xl border border-slate-200 bg-white overflow-hidden shadow-xs min-w-0">
    <header className="bg-[#0B1528] text-white px-4 sm:px-5 py-4 space-y-3">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-[10px] uppercase tracking-widest text-violet-200 font-semibold">Safety investigation</p>
          <h3 className="text-lg font-bold flex items-center gap-2 mt-1"><ShieldAlert className="w-5 h-5 text-violet-300 shrink-0"/>Incident Report <span className="text-violet-200 font-mono text-sm">#{id.slice(0,8)}</span></h3>
          <p className="text-xs text-slate-300 mt-1 flex flex-wrap items-center gap-x-3 gap-y-1"><span className="inline-flex items-center gap-1"><MapPin className="w-3 h-3"/>{zone}</span><IncidentTime value={report.created_at}/></p>
        </div>
        <div className="flex flex-wrap items-center gap-2"><span className={`rounded-lg border px-2 py-1 text-[10px] font-bold ${badge}`}>{report.level||'Not recorded'}</span><span className="rounded-lg border border-white/20 bg-white/10 px-2 py-1 text-[10px] font-semibold">{label(report.status)}</span></div>
      </div>
      <div className="flex flex-wrap items-center justify-between gap-2 border-t border-white/10 pt-3">
        <span className="text-[10px] font-medium text-violet-100">{report.is_test===true?'TEST / REPLAY':report.is_test===false?'NON-TEST RECORD':'TEST STATUS NOT RECORDED'}<span className="text-slate-300"> / {provenance}</span></span>
        <div className="flex flex-wrap gap-2">{([['pdf','Download PDF'],['print','Print / Save as PDF'],['csv','Download Incident CSV']] as const).filter(([kind])=>!operational||kind==='csv').map(([kind,text])=><button key={kind} disabled={busy} className="inline-flex items-center gap-1.5 rounded-lg bg-white px-3 py-2 text-[11px] font-semibold text-[#0B1528] hover:bg-violet-100 disabled:opacity-50" onClick={()=>exportReport(kind)}><Download className="w-3.5 h-3.5"/>{text}</button>)}</div>
      </div>
    </header>
    <div className="p-3 sm:p-5 space-y-4">
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5">
        <InfoCard icon={ShieldAlert} title="Risk Level" value={report.level||'Not recorded'} detail={label(report.review_status)}/>
        <InfoCard icon={MapPin} title="Location" value={zone} detail={label(report.zone_type)}/>
        <InfoCard icon={Bell} title="Notification Status" value={notification} detail={attempts.length?`${attempts.length} recorded attempt(s)`:'No notification attempt recorded'}/>
      </div>
      <div role="tablist" aria-label="Incident report sections" className="grid grid-cols-4 gap-1 p-1 rounded-xl bg-slate-100 print:hidden">{tabs.map(([name,Icon],i)=><button key={name} id={`incident-${id}-tab-${name}`} aria-controls={`incident-${id}-panel`} role="tab" tabIndex={tab===name?0:-1} aria-selected={tab===name} onKeyDown={e=>{if(['ArrowRight','ArrowLeft','Home','End'].includes(e.key)){e.preventDefault();const next=e.key==='Home'?0:e.key==='End'?3:(i+(e.key==='ArrowRight'?1:3))%4;setTab(tabs[next][0]);document.getElementById(`incident-${id}-tab-${tabs[next][0]}`)?.focus();}}} className={`flex items-center justify-center gap-1.5 px-1 sm:px-3 py-2 rounded-lg text-[11px] sm:text-xs font-semibold transition-colors ${tab===name?'bg-white text-violet-800 shadow-xs':'text-slate-500 hover:text-slate-900'}`} onClick={()=>setTab(name)}><Icon className="w-3.5 h-3.5 hidden min-[400px]:block"/>{name}</button>)}</div>
      {error&&<p role="alert" className="rounded-lg border border-red-200 bg-red-50 p-3 text-xs text-red-700">{error}</p>}
      <section role="tabpanel" id={`incident-${id}-panel`} aria-labelledby={`incident-${id}-tab-${tab}`} className="space-y-3 text-xs min-w-0">
        {tab==='Summary'&&<>
          <div className="rounded-xl border border-slate-200 p-4"><h4 className="font-bold text-sm mb-3">Incident overview</h4><dl className="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-4">
            <Field title="Incident ID"><span className="font-mono break-all">{report.id}</span></Field><Field title="Recorded at"><IncidentTime value={report.created_at}/></Field>
            <Field title="Detection source">{label(report.source)}</Field><Field title="Processing / provenance">{provenance}</Field>
            <Field title="Assigned on-duty staff">{report.assigned_staff||'No active zone assignment configured'}</Field><Field title="Current status">{label(report.status)}</Field>
          </dl></div>
          <div className="rounded-xl border border-violet-100 bg-violet-50/50 p-4"><h4 className="font-bold text-sm mb-2">Incident description</h4><p className="leading-relaxed text-slate-700">{report.reason||'No description recorded'}</p></div>
        </>}
        {tab==='Evidence'&&<IncidentEvidence id={id} view="evidence"/>}
        {tab==='Response'&&<>
          <div className="rounded-xl border border-slate-200 p-4"><h4 className="font-bold text-sm mb-3">Response coordination</h4><dl className="grid grid-cols-1 sm:grid-cols-2 gap-4"><Field title="Assigned on-duty staff">{report.assigned_staff||'No active zone assignment configured'}</Field><Field title="Current status">{label(report.status)}</Field><Field title="Acknowledged"><IncidentTime value={report.acknowledged_at}/>{report.acknowledged_by&&<span className="block text-slate-500 mt-1">{report.acknowledged_by}</span>}</Field><Field title="Resolved"><IncidentTime value={report.resolved_at}/>{report.resolved_by&&<span className="block text-slate-500 mt-1">{report.resolved_by}</span>}</Field></dl></div>
          <IncidentEvidence id={id} view="notifications" onUpdated={onUpdated}/>
          {!closed&&<div className="rounded-xl border border-slate-200 p-4 space-y-3"><h4 className="font-bold text-sm">Record response</h4><label className="block text-[11px] text-slate-500">Staff reviewing this incident<input aria-label="Report reviewing staff" className="block mt-1 w-full border border-slate-200 rounded-lg p-2 text-xs text-slate-900 focus:ring-2 focus:ring-violet-300" value={staff} onChange={e=>setStaff(e.target.value)}/></label>{!report.acknowledged_at&&<button disabled={busy||!staff.trim()} className="bg-violet-700 text-white px-3 py-2 rounded-lg font-semibold disabled:opacity-50" onClick={()=>action('ACKNOWLEDGED')}>Acknowledge incident</button>}<label className="block text-[11px] text-slate-500">Resolution / review note<textarea aria-label="Report resolution note" className="block mt-1 border border-slate-200 rounded-lg p-2 w-full text-xs text-slate-900" rows={2} value={note} onChange={e=>setNote(e.target.value)}/></label><button disabled={busy||!report.acknowledged_at||!note.trim()||!staff.trim()} className="bg-[#0B1528] text-white px-3 py-2 rounded-lg font-semibold disabled:opacity-50" onClick={()=>action('RESOLVED')}>Resolve incident</button></div>}
          <div className="rounded-xl border border-slate-200 p-4"><h4 className="font-bold text-sm mb-3">Response and audit history</h4>{!history.length?<p className="text-slate-500">No response history recorded</p>:<ol className="ml-1 border-l border-violet-200 space-y-4">{history.map((h:any,n:number)=><li key={n} className="relative pl-4"><span className="absolute -left-1 top-1 h-2 w-2 rounded-full bg-violet-500 ring-4 ring-white"/><div className="flex flex-wrap justify-between gap-1"><span className="font-semibold text-slate-800">{label(h.status)}</span><span className="text-[10px] text-slate-500"><IncidentTime value={h.timestamp}/></span></div>{h.note&&<p className="mt-1 text-slate-600 break-words">{h.note}</p>}</li>)}</ol>}</div>
        </>}
        {tab==='Analysis'&&<>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">{[['Observations',report.analysis?.observation_count],['Retained clips',report.analysis?.evidence_clip_count],['Acknowledgement',report.analysis?.acknowledgement_seconds==null?'Not measured':`${report.analysis.acknowledgement_seconds}s`],['Resolution',report.analysis?.resolution_seconds==null?'Not measured':`${report.analysis.resolution_seconds}s`]].map(([title,value])=><div key={title} className="bg-slate-50 border border-slate-200 rounded-xl p-3"><p className="text-[10px] text-slate-500">{title}</p><p className="font-bold mt-1">{value??'Not recorded'}</p></div>)}</div>
          <div className="rounded-xl border border-violet-100 bg-violet-50/50 p-4"><h4 className="font-bold text-sm mb-2">Recorded risk decision</h4><p className="leading-relaxed">{report.reason||'No risk rationale recorded'}</p></div>
          <h4 className="font-bold text-sm">Model results & provenance</h4>
          {!observations.length&&<p className="text-slate-500">No model observations recorded</p>}
          {observations.map((e:any,n:number)=><div key={e.id||n} className="rounded-xl border border-slate-200 p-4 space-y-3"><div className="flex flex-wrap items-center justify-between gap-2"><span className="font-bold">{e.model_version||'Rule / sensor input; no model version recorded'}</span><span className="rounded-md bg-violet-50 text-violet-800 px-2 py-1 text-[10px] font-semibold">{label(e.type)}</span></div><dl className="grid grid-cols-1 sm:grid-cols-2 gap-3"><Field title="Model score">{e.score==null?'Not supplied':String(e.score)}</Field><Field title="Event confidence">{e.confidence==null?'Not supplied':String(e.confidence)}</Field><Field title="Source / processing">{[e.source,e.source_type,e.processing_mode].filter(Boolean).join(' / ')||'Not recorded'}</Field><Field title="Observed at"><IncidentTime value={e.timestamp}/></Field></dl>{e.reason&&<p className="border-t border-slate-100 pt-2 text-slate-600 leading-relaxed">{e.reason}</p>}</div>)}
          {report.analysis?.limits&&<p className="text-[11px] leading-relaxed text-slate-500">{report.analysis.limits}</p>}
          {!operational&&<p className="text-[11px] text-slate-500">Dataset evaluation accuracy is available separately under Model evaluation.</p>}
        </>}
      </section>
    </div>
  </article>;
}

function label(value:unknown) { return value==null||value===''?'Not recorded':String(value).replaceAll('_',' '); }
function Field({title,children}:{title:string;children:React.ReactNode}) {return <div className="min-w-0"><dt className="text-[10px] font-medium text-slate-500 mb-1">{title}</dt><dd className="text-xs text-slate-800 break-words">{children}</dd></div>;}
function InfoCard({icon:Icon,title,value,detail}:{icon:typeof Bell;title:string;value:string;detail:string}) {return <div className="rounded-xl border border-slate-200 bg-slate-50/70 p-3 min-w-0"><p className="flex items-center gap-1.5 text-[10px] text-slate-500 font-medium"><Icon className="w-3.5 h-3.5 text-violet-600"/>{title}</p><p className="text-xs font-bold text-[#0B1528] mt-2 break-words">{value}</p><p className="text-[10px] text-slate-500 mt-1 break-words">{detail}</p></div>;}
const tabs=[['Summary',FileText],['Evidence',ScanEye],['Response',Clock3],['Analysis',Activity]] as const;
