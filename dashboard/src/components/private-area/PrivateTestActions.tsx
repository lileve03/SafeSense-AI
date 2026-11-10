import React,{forwardRef,useEffect,useImperativeHandle,useRef,useState} from 'react';
import {api} from '../../lib/api';
import {useSafeSenseApp} from '../../context/SafeSenseContext';
import {applySosReport,reportNotification,emptyTests,notificationView,resetTests,prepareExplicitTest,runPrivateTest,telegramConfigured,testStorageKey,testSummary,
  type TestKind,type TestResult,type TestSession} from './privateTestWorkflow';
import type {TrackingPlayback} from './trackingPlayback';

export type TestSelection=Pick<TestResult,'incidentId'|'incidentStatus'|'risk'|'reason'|'notification'>;
export interface PrivateTestActionsHandle {run:(kind:TestKind)=>Promise<void>}
function load(zoneId:string):TestSession {
  try{
    const saved=JSON.parse(sessionStorage.getItem(testStorageKey(zoneId))||'null');
    if(saved?.zoneId===zoneId&&/^[a-f0-9-]{36}$/.test(saved.id)&&saved.results?.acoustic&&saved.results?.sos&&saved.results?.fusion){
      for(const result of Object.values(saved.results) as TestResult[])if(['Running','Triggered'].includes(result.status)){
        result.status='Failed';result.error='Interrupted; retry resumes the saved request';
      }
      return saved;
    }
  }catch{/* Use a new isolated test session when local state is unavailable. */}
  return {id:crypto.randomUUID(),zoneId,results:emptyTests()};
}
function Chip({children,tone='neutral',testId,title}:{children:React.ReactNode;tone?:string;testId?:string;title?:string}) {
  return <span data-testid={testId} title={title} className={`inline-flex rounded-md px-2 py-1 text-[10px] font-semibold ${tone==='success'?'bg-emerald-50 text-emerald-700':tone==='error'?'bg-rose-50 text-rose-700':'bg-slate-100 text-slate-500'}`}>{children}</span>;
}
export const PrivateTestActions=forwardRef<PrivateTestActionsHandle,{zoneId:string;playback:TrackingPlayback}>(function PrivateTestActions({zoneId,playback},ref){
  const {checkFastApiConnection,setIsLiveMode,setSelectedAlertId}=useSafeSenseApp();
  const [session,setSession]=useState(()=>load(zoneId));
  const saved=useRef(session),busyRef=useRef(false),mounted=useRef(true),request=useRef<AbortController|null>(null);
  const [busy,setBusy]=useState(false),[configuration,setConfiguration]=useState<any>(null),[storageError,setStorageError]=useState('');
  const persist=(next:TestSession)=>{
    // A request must be durable before sending, so navigation/reload can retry safely.
    sessionStorage.setItem(testStorageKey(zoneId),JSON.stringify(next));saved.current=next;
    if(mounted.current)setSession(next);
  };
  const select=(next:TestSession)=>{
    const result=next.active&&next.results[next.active];
    if(mounted.current&&next.active&&result&&result.status!=='Not Tested')playback.updateTest(next.active,next.id,result);
  };
  useEffect(()=>{
    mounted.current=true;
    let cancelled=false;
    const refresh=()=>void api('/notifications/status').then(value=>{if(!cancelled)setConfiguration(value);}).catch(()=>{if(!cancelled)setConfiguration(null);});
    refresh();const timer=window.setInterval(refresh,10000);
    select(saved.current);
    return()=>{cancelled=true;mounted.current=false;request.current?.abort();window.clearInterval(timer);};
  },[zoneId]);
  useEffect(()=>{
    const kind=session.active,result=kind&&session.results[kind];
    if(!kind||!result?.incidentId||result.status==='Not Tested'||busy)return;
    let cancelled=false;
    const refresh=async()=>{
      try{
        const report=await api('/incidents/'+result.incidentId+'/report');
        if(cancelled||busyRef.current||saved.current.active!==kind||saved.current.results[kind].status==='Not Tested')return;
        if(report.id!==result.incidentId||report.is_test!==true)throw Error('Test incident identity mismatch');
        const latest=saved.current.results[kind];
        const updated=kind==='sos'?applySosReport(latest,report):{...latest,incidentStatus:report.status,notification:reportNotification(report)};
        const next={...saved.current,results:{...saved.current.results,[kind]:updated}};
        if(JSON.stringify(updated)!==JSON.stringify(latest)){persist(next);select(next);}
      }catch{/* Keep the last observed state; no notification delivery is assumed. */}
    };
    void refresh();const timer=window.setInterval(refresh,1500);
    return()=>{cancelled=true;window.clearInterval(timer);};
  },[session.active,session.active&&session.results[session.active].incidentId,session.active&&session.results[session.active].status,busy]);

  async function run(kind:TestKind){
    if(busyRef.current)return;
    busyRef.current=true;setBusy(true);setStorageError('');setIsLiveMode(true);
    playback.beginTest(kind,saved.current.id);
    const controller=new AbortController();request.current=controller;
    const signal=()=>AbortSignal.any([controller.signal,AbortSignal.timeout(10000)]);
    const get=(path:string)=>api(path,{signal:signal()});
    const post=(path:string,body:unknown)=>api(path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body),signal:signal()});
    try{
      const explicit=prepareExplicitTest(kind,saved.current);
      if(explicit!==saved.current)persist(explicit);
      const sleep=(ms:number)=>new Promise<void>((resolve,reject)=>{
        if(controller.signal.aborted){reject(Error('Test interrupted'));return;}
        const stop=()=>{window.clearTimeout(timer);reject(Error('Test interrupted'));};
        const timer=window.setTimeout(()=>{controller.signal.removeEventListener('abort',stop);resolve();},ms);
        controller.signal.addEventListener('abort',stop,{once:true});
      });
      await runPrivateTest(kind,saved.current,{get,post,sleep,beforeSimulation:async()=>{
        if(kind!=='fusion')return;
        while(playback.currentTime()<9.2){
          if(!playback.getSnapshot().playing||playback.getSnapshot().test?.kind!=='fusion')throw Error('Fusion animation paused before submission');
          await sleep(50);
        }
      }},next=>{persist(next);select(next);});
      if(mounted.current)await checkFastApiConnection();
    }catch(error){if(mounted.current)setStorageError(String(error));}
    finally{busyRef.current=false;if(mounted.current)setBusy(false);}
  }
  useImperativeHandle(ref,()=>({run}));
  const configured=telegramConfigured(configuration),active=session.active&&session.results[session.active];
  return <section data-testid="private-test-actions" className="rounded-2xl bg-white p-4 shadow-sm shadow-slate-200/40">
    <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_240px]">
      <div className="min-w-0">
        <div className="mb-3 flex items-center justify-between gap-2"><h2 className="text-xs font-bold text-slate-900">Test Actions</h2><span title="Tests control the shared room using registered recordings or labeled simulation. No physical capture." className="text-[10px] text-slate-400">TEST only</span></div>
        <div className="flex flex-wrap gap-2">
          {(['acoustic','sos','fusion'] as const).map(kind=><button key={kind} disabled={busy} onClick={()=>void run(kind)} className={`rounded-lg px-3 py-2 text-xs font-semibold disabled:opacity-40 ${kind==='sos'?'bg-rose-50 text-rose-700':'bg-blue-50 text-blue-800'}`}>Run {kind==='sos'?'SOS':kind==='acoustic'?'Acoustic':'Fusion'} Test</button>)}
          <button disabled={busy} title="Reset room and status chips; saved incidents and retry IDs are retained" onClick={()=>{try{const next=resetTests(saved.current);persist(next);playback.resetTest();setStorageError('');}catch(error){setStorageError(String(error));}}} className="rounded-lg px-3 py-2 text-xs font-semibold text-slate-500 disabled:opacity-40">Reset Test State</button>
        </div>
        <div className="mt-3 grid gap-2 sm:grid-cols-3">
          {(['acoustic','sos','fusion'] as const).map(kind=>{
            const result=session.results[kind],summary=testSummary(kind,result),notification=notificationView(result.notification);
            return <div key={kind} data-testid={'test-result-'+kind} className="min-w-0 space-y-1.5 text-[10px]">
              <div className="flex flex-wrap items-center gap-1.5"><strong className="text-slate-600">{kind==='sos'?'SOS':kind==='acoustic'?'Acoustic':'Fusion'}</strong>
                <Chip testId={'test-status-'+kind} tone={summary==='Failed'?'error':summary==='Passed'?'success':'neutral'}>{kind==='sos'&&result.status==='Notification Sent'?'Incident Created':result.status}</Chip>
              </div>
              {result.status!=='Not Tested'&&<>
                {result.source&&<p data-testid={'test-source-'+kind} className="font-semibold text-slate-400">{result.source}</p>}
                <div className="flex flex-wrap gap-1">{result.detected&&<Chip testId={'test-detected-'+kind}>{result.detected}</Chip>}{result.risk&&<Chip testId={'test-risk-'+kind} title={result.reason}>{result.risk}</Chip>}</div>
                <div className="flex flex-wrap items-center gap-2">
                  {result.incidentId&&<Chip testId={'test-'+kind+'-notification'} tone={notification.tone} title={`Last API acceptance: ${result.notificationAcceptedAt||'unavailable'}; message ID: ${result.notificationMessageId||'unavailable'}. Playback and request retries reuse this incident. A deliberate SOS Test click after acceptance starts a fresh test. Receipt is unverified unless separately confirmed.`}>{notification.label}</Chip>}
                  {result.incidentId&&<button data-testid={'test-incident-'+kind} className="font-semibold text-blue-700" onClick={()=>setSelectedAlertId(result.incidentId!)}>Open Incident #{result.incidentId.slice(0,8)}</button>}
                </div>
                {result.error&&<p role="alert" title={result.error} className="line-clamp-2 text-rose-700">{result.error}</p>}
              </>}
            </div>;
          })}
        </div>
        {storageError&&<p role="alert" className="mt-2 text-xs text-rose-700">{storageError}</p>}
      </div>
      <div data-testid="private-test-summary" className="rounded-xl bg-slate-50 p-3">
        <h3 className="mb-2 text-xs font-bold text-slate-700">Test Summary</h3>
        <dl className="grid grid-cols-2 gap-x-3 gap-y-2 text-[10px]">
          {(['acoustic','sos','fusion'] as const).map(kind=><div key={kind} className="flex items-center justify-between gap-2"><dt className="capitalize text-slate-500">{kind==='sos'?'SOS':kind}</dt><dd data-testid={'test-summary-'+kind} title={kind==='sos'?'Passed confirms TEST incident creation. API acceptance and recipient receipt are separate.':undefined} className="font-semibold text-slate-700">{testSummary(kind,session.results[kind])}</dd></div>)}
          <div className="flex items-center justify-between gap-2"><dt className="text-slate-500">Telegram</dt><dd data-testid="test-summary-telegram" title="Test credentials must be enabled; sending also requires an eligible recipient route" className="font-semibold text-slate-700">{configured===undefined?'Unknown':configured?'Configured':'Not Configured'}</dd></div>
        </dl>
        {active?.reason&&<p title={active.reason} className="mt-3 line-clamp-2 text-[10px] text-slate-400">{active.reason}</p>}
      </div>
    </div>
  </section>;
});

