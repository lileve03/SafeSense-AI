import {IncidentTime} from '../../lib/incidentTime';
import {notificationStateLabel} from '../../lib/notificationState';
import React, {useEffect,useRef,useState} from 'react';
import {IncidentMedia} from './IncidentMedia';
import {api,post} from '../../lib/api';
import {useSafeSenseApp} from '../../context/SafeSenseContext';
export function IncidentEvidence({id,view='all',onUpdated}:{id:string;view?:'all'|'evidence'|'notifications';onUpdated?:()=>void|Promise<void>}) {
  const [report,setReport]=useState<any>(null),[configuration,setConfiguration]=useState<any>(null),[error,setError]=useState('');
  const [selectedMedia,setSelectedMedia]=useState('');
  const {checkFastApiConnection}=useSafeSenseApp();
  const [sending,setSending]=useState(false);
  const sendingRef=useRef(false);
  async function notify(test:boolean,receipt=false) {
    if(sendingRef.current)return;
    sendingRef.current=true;setSending(true);setError('');
    try {
      const outcome=await post(`/incidents/${id}/${receipt?'verify-test-receipt':test?'notify-test':'notify'}`,{});
      if(receipt && outcome.delivery_state!=='RECEIPT_CONFIRMED')setError(outcome.state||'Receipt remains unconfirmed');
      setReport(await api(`/incidents/${id}/report`));
      await checkFastApiConnection();
      await onUpdated?.();
    }catch(e){setError(String(e));}
    finally{sendingRef.current=false;setSending(false);}
  }
  useEffect(()=>{
    let alive=true;
    setReport(null);setError('');setSelectedMedia('');
    const refresh=()=>Promise.allSettled([api(`/incidents/${id}/report`),api('/notifications/status')]).then(([result,config])=>{
      if(!alive)return;
      if(result.status==='rejected'){setError(String(result.reason));return;}
      const r=result.value;
      if(r.id!==id){setReport(null);setError('Incident report identity mismatch.');return;}
      setReport(r);setError('');setConfiguration(config.status==='fulfilled'?config.value:{status:'UNAVAILABLE',production_dispatch:false});
    });
    void refresh();const timer=setInterval(refresh,3000);
    return ()=>{alive=false;clearInterval(timer);};
  },[id]);
  const current=report?.id===id?report:null;
  const media=(current?.zone_type==='OPEN_HIDDEN'?current.evidence:[]).flatMap((e:any)=>e.evidence_media||[]);
  const unique=[...new Map<string,any>(media.map((m:any)=>[m.id,m])).values()];
  const selected=unique.find(m=>m.id===selectedMedia)||unique[0];
  return <section data-testid="incident-evidence" data-incident-id={id} className="p-4 border border-slate-200 rounded-xl space-y-3 text-xs min-w-0"><h4 className="font-bold text-sm">{view==='all'?'Incident evidence & staff notifications':view==='evidence'?'Captured evidence':'Staff notification delivery'}</h4>
    {error && <p role="alert" className="text-red-700">{error}</p>}
    {view!=='notifications' && <>
      {!current&&!error&&<p className="text-slate-500" role="status">Loading incident evidence...</p>}
      {current&&<>
        <dl className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs break-words">
          <div><dt className="text-slate-500">Incident ID</dt><dd className="font-mono break-all">{current.id}</dd></div>
          <div><dt className="text-slate-500">Incident timestamp</dt><dd><IncidentTime value={current.created_at}/></dd></div>
          <div><dt className="text-slate-500">Zone</dt><dd>{current.zone_id} / {current.zone_type}</dd></div>
          <div><dt className="text-slate-500">Processing mode</dt><dd>{current.processing_mode} / {current.source_type||'Source not recorded on incident'}</dd></div>
        </dl>
        {current.zone_type!=='OPEN_HIDDEN'?<p>Private sensor metadata only. No images, video, or speech are captured.</p>:unique.length===0&&<p>No retained video attached to this incident. Review the saved detection metadata below; no substitute recording is shown.</p>}
        {unique.length>1&&<label className="block text-xs">Saved evidence <select aria-label="Incident evidence clip" className="border border-slate-200 rounded p-2 max-w-full" value={selected?.id||''} onChange={e=>setSelectedMedia(e.target.value)}>{unique.map(m=><option key={m.id} value={m.id}>{m.model_version} / {m.camera_id||'camera not captured'} / {m.id.slice(0,8)}</option>)}</select></label>}
        {selected&&<IncidentMedia key={id+selected.id} incident={current} item={selected}/>}
        <details open={current.zone_type!=='OPEN_HIDDEN'} className="text-xs border-t border-slate-100 pt-2">
          <summary className="font-semibold cursor-pointer">Saved detection metadata ({current.evidence?.length||0})</summary>
          <div className="space-y-3 mt-2">{current.evidence?.map((observation:any)=><div key={observation.id} className="p-3 bg-slate-50 rounded-lg space-y-1 break-words">
            <p>{observation.type} / {observation.sensor_modality||observation.source} / {observation.processing_mode}</p>
            <p>Observation timestamp: <IncidentTime value={observation.timestamp}/> / Model: {observation.model_version||'Rule or SOS input'}</p>
            <p>Prediction: {observation.type} / Score: {observation.score!=null?Number(observation.score).toFixed(6):'Not provided'} / Source: {observation.source_type||'Not recorded'}</p>
            {current.zone_type==='OPEN_HIDDEN'&&<p>Camera ID: {observation.camera_id||'Not captured'}</p>}
            <p>{observation.reason}</p>
            {current.zone_type==='OPEN_HIDDEN'&&observation.evidence_reference&&<p className="font-mono text-[10px] break-all text-slate-500">Reference: {observation.evidence_reference}</p>}
          </div>)}</div>
        </details>
      </>}
    </>}
    {view!=='evidence' && <><p>Telegram: {configuration?.status || 'checking'}  /  {configuration?.production_dispatch?'Configured staff dispatch enabled; tests/replays use TEST chat only':'Staff dispatch disabled'}</p>
    {!!configuration?.missing_setup?.length && <p className="text-xs text-amber-800">Missing backend setup: {configuration.missing_setup.join(', ')}. Configure locally; never paste credentials into the dashboard.</p>}
    {!current?.notifications?.length&&<p className="text-slate-500">No notification attempt recorded.</p>}
    {current?.notifications?.map((n:any)=><div key={n.id} className="rounded-xl border border-slate-200 bg-slate-50/70 p-3 space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-2"><span className="font-semibold text-slate-800">{notificationStateLabel(n.delivery_state||n.status)}</span><span className="text-[10px] text-slate-500"><IncidentTime value={n.timestamp}/></span></div>
      <dl className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        <div><dt className="text-[10px] text-slate-500 mb-1">Recipient routing</dt><dd>{n.mode==='test'?'TEST chat route':n.mode==='staff'?'Configured staff route':'No sending route recorded'}<span className="block text-[10px] text-slate-500 mt-1">{n.assigned_staff||'Unassigned'}</span></dd></div>
        <div><dt className="text-[10px] text-slate-500 mb-1">Telegram API acceptance</dt><dd>{n.telegram_api_ok===true?'API accepted':n.telegram_api_ok===false?'API rejected':'Not evidenced'}{n.telegram_http_status!=null&&<span className="block text-[10px] text-slate-500 mt-1">HTTP {n.telegram_http_status}</span>}{n.telegram_message_id!=null&&<span className="block text-[10px] text-slate-500">Message ID: {n.telegram_message_id}</span>}</dd></div>
        <div><dt className="text-[10px] text-slate-500 mb-1">Receipt verification</dt><dd>{n.receipt_confirmed_at?<><span>Confirmed</span><span className="block text-[10px] text-slate-500 mt-1"><IncidentTime value={n.receipt_confirmed_at}/></span></>:'Not confirmed'}</dd></div>
      </dl>
      {n.error&&<p className="text-red-700 break-words">{n.error}{n.error_code!=null?` / Error code: ${n.error_code}`:''}</p>}
    </div>)}
    <button disabled={sending||!current||['RESOLVED','FALSE_ALARM'].includes(current?.status)} className="text-blue-700 underline disabled:opacity-50" onClick={()=>notify(true)}>{configuration?.test_configured && ['test','staff'].includes(configuration?.mode) ? 'Send to configured authorized TEST chat':'Preview local notification (no send)'}</button>
    {configuration?.production_dispatch && current?.is_test===false && ['LIVE CAMERA','LIVE SENSOR','LIVE SOS'].includes(current?.source_type) && !['RESOLVED','FALSE_ALARM'].includes(current?.status) && <button className="ml-3 text-blue-700 underline" disabled={sending} onClick={()=>notify(false)}>Queue assigned staff notification</button>}
    {configuration?.receipt_verification_configured && current?.notifications?.some((n:any)=>['API_ACCEPTED','UNKNOWN'].includes(n.delivery_state)&&n.mode==='test') && <button className="ml-3 text-blue-700 underline" disabled={sending} onClick={()=>notify(true,true)}>Verify authorized TEST reply and acknowledge</button>}
    <p className="text-xs text-slate-500">API acceptance is not recipient delivery. Receipt confirmation requires an authorized Telegram reply; no receipt is inferred from a dashboard click.</p>
    {current?.notifications?.at(-1)?.preview && <details className="text-xs"><summary className="font-semibold text-slate-600 cursor-pointer">Recorded notification preview</summary><pre className="whitespace-pre-wrap break-words text-[11px] bg-slate-50 p-3 rounded mt-2">{current.notifications.at(-1).preview}</pre></details>}</>}
  </section>;
}
