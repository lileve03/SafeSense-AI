import type {RiskLevel} from '../../types/safesense';
import type {SensorObservation} from './SensorObservationPanel';

export type TestKind='acoustic'|'sos'|'fusion';
export type TestStatus='Not Tested'|'Running'|'Passed'|'Failed'|'Triggered'|'Incident Created'|'Notification Sent';
export interface TestResult {
  status:TestStatus; source?:string; detected?:string; risk?:RiskLevel; reason?:string;
  incidentId?:string; incidentStatus?:string; notification?:string; error?:string;
  observation?:Record<string,unknown>; jobId?:string;
  recordedObservation?:SensorObservation;
  notificationAcceptedAt?:string;notificationMessageId?:number;
}
export interface TestSession {id:string;zoneId:string;active?:TestKind;sosGeneration?:string;results:Record<TestKind,TestResult>}
export interface TestIO {get:(path:string)=>Promise<any>;post:(path:string,body:unknown)=>Promise<any>;sleep:(ms:number)=>Promise<void>;beforeSimulation?:()=>Promise<void>}
export const emptyTests=():Record<TestKind,TestResult>=>({acoustic:{status:'Not Tested'},sos:{status:'Not Tested'},fusion:{status:'Not Tested'}});
export const testStorageKey=(zone:string)=>'safesense-private-test-actions-v1:'+zone;

/** A deliberate new SOS click differs from polling, playback and transport retry. */
export function prepareExplicitTest(kind:TestKind,session:TestSession):TestSession {
  if(kind!=='sos'||!['API_ACCEPTED','SENT','RECEIPT_CONFIRMED'].includes(session.results.sos.notification||''))return session;
  return {...session,sosGeneration:crypto.randomUUID(),results:{...session.results,sos:{status:'Not Tested'}}};
}

export function resetTests(session:TestSession):TestSession {
  // Clear the presentation, retaining durable request IDs, observations and job IDs.
  return {...session,active:undefined,results:Object.fromEntries(Object.entries(session.results).map(([kind,result])=>
    [kind,{status:'Not Tested',observation:result.observation,jobId:result.jobId,incidentId:result.incidentId,notification:result.notification}])) as Record<TestKind,TestResult>};
}
export function testSummary(kind:TestKind,result:TestResult):string {
  if(result.status==='Not Tested')return 'Not Tested';
  if(kind==='sos'&&result.incidentId&&result.risk==='CRITICAL')return 'Passed';
  if(result.status==='Failed')return 'Failed';
  return result.status==='Passed'?'Passed':'Running';
}
export function telegramConfigured(config:any):boolean|undefined {
  if(!config)return undefined;
  return ['test','staff'].includes(config.mode)&&config.test_configured===true;
}
export function notificationView(value?:string):{label:string;tone:string} {
  if(value==='RECEIPT_CONFIRMED')return {label:'Receipt confirmed',tone:'success'};
  if(value==='API_ACCEPTED'||value==='SENT')return {label:'API accepted',tone:'success'};
  if(['DISABLED','NOT_CONFIGURED','NO_ACTIVE_ASSIGNMENT','POLICY_SUPPRESSED','STAFF_DISPATCH_NOT_AUTHORIZED','CANCELLED_CLOSED','PREVIEW'].includes(value||''))return {label:'Notification unavailable',tone:'neutral'};
  if(value==='FAILED'||value==='QUEUE_FULL')return {label:'Failed',tone:'error'};
  if(value==='UNKNOWN'||value==='DELIVERY_UNKNOWN')return {label:'Acceptance unknown',tone:'neutral'};
  return {label:value?'Pending':'Not Tested',tone:'neutral'};
}
export function applySosReport(result:TestResult,report:any):TestResult {
  if(!result.incidentId||report.id!==result.incidentId||report.is_test!==true)throw Error('Test incident identity mismatch');
  const notification=reportNotification(report);
  const accepted=report.notifications?.findLast((n:any)=>n.telegram_api_ok===true&&Number.isInteger(n.telegram_message_id)&&n.telegram_message_id>0);
  return {...result,incidentStatus:report.status,risk:report.level,reason:report.reason,notification,
    notificationAcceptedAt:accepted?.api_accepted_at,notificationMessageId:accepted?.telegram_message_id,
    status:['API_ACCEPTED','SENT','RECEIPT_CONFIRMED'].includes(notification)?'Notification Sent':'Incident Created'};
}
export function reportNotification(report:any):string {
  const state=report.notification_state||'PENDING';
  if(['API_ACCEPTED','SENT'].includes(state)&&!report.notifications?.some((n:any)=>n.telegram_api_ok===true&&Number.isInteger(n.telegram_message_id)&&n.telegram_message_id>0))return 'UNKNOWN';
  return state==='RECEIPT_CONFIRMED'&&!report.notifications?.some((n:any)=>n.receipt_confirmed===true||n.receipt_confirmed_at)?'UNKNOWN':state;
}

export async function runPrivateTest(kind:TestKind,session:TestSession,io:TestIO,changed:(value:TestSession)=>void):Promise<TestSession> {
  let current={...session,active:kind,results:{...session.results}};
  const patch=(value:Partial<TestResult>)=>{
    current={...current,results:{...current.results,[kind]:{...current.results[kind],...value}}};changed(current);
  };
  patch({status:kind==='sos'?'Triggered':'Running',error:undefined});
  try {
    let result=current.results[kind];
    if(kind==='acoustic'&&!result.observation){
      const catalog=await io.get('/testing/scenarios');
      const source=catalog.find((s:any)=>s.id==='acoustic_scream'&&s.zone_id===session.zoneId&&s.ready===true&&s.execution_kind==='fresh_inference');
      if(source||result.jobId){
        patch({source:'RECORDED ACOUSTIC TEST'});
        let job=result.jobId?await io.get('/testing/runs/'+result.jobId):null;
        if(job&&['FAILED','INTERRUPTED'].includes(job.status))job=null;
        if(!job){
          if(!source)throw Error('Registered acoustic input is unavailable');
          job=await io.post('/testing/runs',{scenario_id:source.id,model:source.default_model,authorized:true});
          patch({jobId:job.id});
        }
        for(let i=0;['QUEUED','RUNNING'].includes(job.status)&&i<200;i++){
          await io.sleep(1000);job=await io.get('/testing/runs/'+job.id);
        }
        if(job.status!=='COMPLETED')throw Error(job.error||'Inference still pending; retry resumes the same job');
        const actual=job.result;
        if(job.zone_id!==session.zoneId||actual?.output_origin!=='fresh_raw_input_inference'||!actual.event_delivery?.event_id)
          throw Error('Recorded inference did not return supported backend evidence');
        const replay=await io.post('/sensors/observations/replay',{event_id:actual.event_delivery.event_id});
        const observation=replay.observation,assessment=observation?.backend_assessment;
        if(observation?.source_mode!=='RECORDED_REPLAY'||observation.zone_id!==session.zoneId||assessment?.event_id!==actual.event_delivery.event_id)
          throw Error('Recorded observation identity mismatch');
        const detected=observation.acoustic_events?.find((e:any)=>['scream','impact'].includes(e.kind))?.kind||'none';
        patch({status:actual.candidate_detected&&detected!=='none'?'Passed':'Failed',detected,
          risk:assessment.level,reason:assessment.reason,incidentId:assessment.incident_id||undefined,incidentStatus:assessment.status,recordedObservation:observation});
        return current;
      }
    }
    result=current.results[kind];
    patch({source:kind==='acoustic'?'SIMULATED ACOUSTIC TEST':kind==='fusion'?'SIMULATED FUSION TEST':'SIMULATED SOS TEST'});
    await io.beforeSimulation?.();
    const requestKey=kind==='sos'&&session.sosGeneration?session.sosGeneration:session.id;
    const group='private-demo:'+requestKey+':'+kind;
    if(!result.observation){
      patch({observation:{observation_id:'private-test-'+requestKey+'-'+kind,source_mode:'SIMULATION',
        device_id:'private-test-'+kind,zone_id:session.zoneId,tracking_session_id:group,
        timestamp:new Date().toISOString(),timestamp_basis:'CAPTURE_TIME',data_validity:'VALID',
        radar_event:kind==='fusion'?'fall':undefined,
        acoustic_events:kind==='acoustic'?[{kind:'scream',confidence:1}]:kind==='fusion'?[{kind:'impact',confidence:1}]:undefined,
        sos_state:kind==='sos'?'ACTIVE':'INACTIVE',
        evidence_reference:'SIMULATED '+kind.toUpperCase()+' TEST; metadata only; no physical acquisition'}});
    }
    const delivery=await io.post('/sensors/observations',current.results[kind].observation);
    const events=delivery.events;
    const expected=kind==='acoustic'?['scream']:kind==='fusion'?['fall','impact']:['sos'];
    if(!Array.isArray(events)||events.length!==(kind==='fusion'?2:1)||events.some((e:any)=>
      e.event?.zone_id!==session.zoneId||e.event?.analysis_run_id!==group||e.event?.source_type!=='SIMULATION'||e.event?.processing_mode!=='simulation'||e.event?.is_test!==true
      ||!expected.includes(e.event?.type)||e.event?.id!==group+':'+e.event?.type)||new Set(events.map((e:any)=>e.event.type)).size!==expected.length)
      throw Error('Backend did not accept the labeled test signals');
    const last=events.at(-1),incident=last.incident;
    patch({detected:kind==='sos'?'sos':kind==='fusion'?'fall + impact':last.event.type,
      risk:last.event.level,reason:last.event.reason,incidentId:incident?.id,incidentStatus:incident?.status});
    if(kind==='sos'){
      if(!incident?.id||incident.level!=='CRITICAL')throw Error('SOS did not create a CRITICAL test incident');
      patch({status:'Incident Created',notification:'PENDING'});
      // Read status only. No manual resend and no receipt claim from API acceptance.
      for(let i=0;i<12;i++){
        const report=await io.get('/incidents/'+incident.id+'/report');
        patch(applySosReport(current.results.sos,report));
        if(!['PENDING','SENDING','QUEUED'].includes(current.results.sos.notification||''))break;
        await io.sleep(500);
      }
    }else {
      if(kind==='fusion'&&(last.event.level!=='HIGH'||!incident?.id||events.some((e:any)=>e.incident?.id!==incident.id)))
        throw Error('Backend did not corroborate this fusion test into one HIGH incident');
      patch({status:'Passed'});
    }
  }catch(error){
    const savedSos=kind==='sos'&&current.results.sos.incidentId&&current.results.sos.risk==='CRITICAL';
    patch({status:savedSos?'Incident Created':'Failed',...(savedSos?{notification:'UNKNOWN'}:{}),error:String(error)});
  }
  return current;
}
