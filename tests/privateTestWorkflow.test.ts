import test from 'node:test';
import assert from 'node:assert/strict';
import {applySosReport,prepareExplicitTest,emptyTests,notificationView,resetTests,runPrivateTest,telegramConfigured,testSummary,type TestSession,type TestIO} from '../dashboard/src/components/private-area/privateTestWorkflow';

const fresh=():TestSession=>({id:'11111111-1111-4111-8111-111111111111',zoneId:'ZONE_TOILET_BLINDSPOT',results:emptyTests()});
function fixture(notification='DISABLED'){
  const bodies:any[]=[],incidents=new Map<string,string>();
  const io:TestIO={sleep:async()=>{},get:async path=>{
    if(path==='/testing/scenarios')return [];
    if(path.startsWith('/incidents/'))return {id:path.split('/')[2],is_test:true,level:'CRITICAL',status:'NEW',reason:'TEST help request',notification_state:notification,notifications:['API_ACCEPTED','SENT'].includes(notification)?[{telegram_api_ok:true,telegram_message_id:123,api_accepted_at:'2026-11-03T00:00:00Z'}]:[]};
    throw Error(path);
  },post:async(path,body:any)=>{
    assert.equal(path,'/sensors/observations');bodies.push(body);
    const group=body.tracking_session_id;
    if(!incidents.has(group))incidents.set(group,'incident-'+incidents.size);
    const id=incidents.get(group);
    const signals=[...(body.radar_event?[body.radar_event]:[]),...(body.acoustic_events||[]).map((e:any)=>e.kind),...(body.sos_state==='ACTIVE'?['sos']:[])];
    return {events:signals.map((type:string,index:number)=>({event:{id:group+':'+type,type,zone_id:body.zone_id,analysis_run_id:group,source_type:'SIMULATION',processing_mode:'simulation',is_test:true,level:type==='sos'?'CRITICAL':signals.length===2&&index===1?'HIGH':'OBSERVE',reason:'Backend rule'},
      incident:{id,level:type==='sos'?'CRITICAL':signals.length===2&&index===1?'HIGH':'OBSERVE',status:'NEW'}}))};
  }};
  return {io,bodies,incidents};
}
test('Acoustic fallback uses explicit metadata-only simulation and actual backend response',async()=>{
  const f=fixture();const states:string[]=[];
  const result=await runPrivateTest('acoustic',fresh(),f.io,s=>states.push(s.results.acoustic.status));
  assert.equal(result.results.acoustic.source,'SIMULATED ACOUSTIC TEST');
  assert.equal(result.results.acoustic.detected,'scream');assert.equal(result.results.acoustic.status,'Passed');
  assert.deepEqual(f.bodies[0].acoustic_events,[{kind:'scream',confidence:1}]);
  assert.equal(f.bodies[0].source_mode,'SIMULATION');assert.equal(f.bodies[0].tracks,undefined);
  assert.ok(states.includes('Running'));assert.equal(testSummary('acoustic',result.results.acoustic),'Passed');
});
test('Retries and reset retain signal IDs; reset never deletes incidents',async()=>{
  const f=fixture();const first=await runPrivateTest('fusion',fresh(),f.io,()=>{});
  const reset=resetTests(first);assert.equal(reset.results.fusion.status,'Not Tested');
  assert.equal(testSummary('fusion',reset.results.fusion),'Not Tested');
  const second=await runPrivateTest('fusion',reset,f.io,()=>{});
  assert.deepEqual(f.bodies[0],f.bodies[1]);assert.equal(f.incidents.size,1);
  assert.equal(second.results.fusion.incidentId,first.results.fusion.incidentId);
  assert.equal(second.results.fusion.risk,'HIGH');
});
test('Fusion cannot pass from an uncorroborated result',async()=>{
  const f=fixture();const post=f.io.post;f.io.post=async(p,b)=>{
    const value=await post(p,b);value.events.at(-1).event.level='OBSERVE';return value;
  };
  const result=await runPrivateTest('fusion',fresh(),f.io,()=>{});
  assert.equal(result.results.fusion.status,'Failed');
});
test('SOS exposes Triggered, Incident Created and API acceptance without receipt claim',async()=>{
  const f=fixture('API_ACCEPTED'),states:string[]=[];
  const result=await runPrivateTest('sos',fresh(),f.io,s=>states.push(s.results.sos.status));
  assert.ok(states.includes('Triggered'));assert.ok(states.includes('Incident Created'));
  assert.equal(result.results.sos.status,'Notification Sent');
  assert.equal(notificationView(result.results.sos.notification).label,'API accepted');
  assert.equal(testSummary('sos',result.results.sos),'Passed');
});
test('Disabled notification and transport failure remain distinct from SOS creation',async()=>{
  for(const state of ['DISABLED','NOT_CONFIGURED','NO_ACTIVE_ASSIGNMENT']){
    const f=fixture(state);const result=await runPrivateTest('sos',fresh(),f.io,()=>{});
    assert.equal(notificationView(result.results.sos.notification).label,'Notification unavailable');
    assert.equal(result.results.sos.status,'Incident Created');
  }
  assert.equal(notificationView('FAILED').label,'Failed');
  assert.equal(notificationView('UNKNOWN').label,'Acceptance unknown');
});
test('Lost notification response does not fabricate delivery or another SOS',async()=>{
  const f=fixture();const get=f.io.get;f.io.get=async path=>path.startsWith('/incidents/')?Promise.reject(Error('Offline')):get(path);
  const result=await runPrivateTest('sos',fresh(),f.io,()=>{});
  assert.equal(result.results.sos.status,'Incident Created');assert.equal(result.results.sos.notification,'UNKNOWN');
  assert.equal(f.incidents.size,1);assert.equal(testSummary('sos',result.results.sos),'Passed');
});
test('Receipt confirmation requires backend receipt evidence',()=>{
  const result={status:'Incident Created' as const,incidentId:'test'};
  const report={id:'test',is_test:true,level:'CRITICAL',notification_state:'RECEIPT_CONFIRMED'};
  assert.equal(applySosReport(result,report).notification,'UNKNOWN');
  assert.equal(applySosReport(result,{...report,notifications:[{receipt_confirmed:true}]}).notification,'RECEIPT_CONFIRMED');
  assert.throws(()=>applySosReport(result,{...report,id:'other'}));
});
test('Recorded YAMNet test uses real job metadata and reuses the completed job',async()=>{
  let jobs=0,simulationWrites=0;
  const job={id:'job-one',zone_id:'ZONE_TOILET_BLINDSPOT',status:'COMPLETED',result:{output_origin:'fresh_raw_input_inference',candidate_detected:true,event_delivery:{event_id:'recorded-one'}}};
  const io:TestIO={sleep:async()=>{},get:async path=>path==='/testing/scenarios'?[{id:'acoustic_scream',zone_id:job.zone_id,ready:true,execution_kind:'fresh_inference',default_model:'YAMNet'}]:job,
    post:async path=>{
      if(path==='/testing/runs'){jobs++;return job;}
      if(path==='/sensors/observations/replay')return {observation:{source_mode:'RECORDED_REPLAY',zone_id:job.zone_id,acoustic_events:[{kind:'scream',confidence:.94}],backend_assessment:{event_id:'recorded-one',level:'OBSERVE',reason:'Single recorded signal',incident_id:'one',status:'NEW'}}};
      simulationWrites++;throw Error(path);
    }};
  const first=await runPrivateTest('acoustic',fresh(),io,()=>{});
  const second=await runPrivateTest('acoustic',resetTests(first),io,()=>{});
  assert.equal(jobs,1);assert.equal(simulationWrites,0);assert.equal(second.results.acoustic.source,'RECORDED ACOUSTIC TEST');
  assert.equal(second.results.acoustic.incidentId,'one');assert.equal(second.results.acoustic.status,'Passed');
});
test('Rejected/empty backend delivery never renders Passed',async()=>{
  const f=fixture();f.io.post=async()=>({events:[]});
  const result=await runPrivateTest('acoustic',fresh(),f.io,()=>{});
  assert.equal(result.results.acoustic.status,'Failed');assert.equal(result.results.acoustic.incidentId,undefined);
});
test('Telegram configuration never infers readiness from a missing status response',()=>{
  assert.equal(telegramConfigured(null),undefined);
  assert.equal(telegramConfigured({mode:'disabled',test_configured:true}),false);
  assert.equal(telegramConfigured({mode:'test',test_configured:true}),true);
  assert.equal(telegramConfigured({mode:'test',test_configured:false}),false);
});
test('Recorded negative detection reports none and Failed rather than inventing distress',async()=>{
  const zoneId=fresh().zoneId;
  const io:TestIO={sleep:async()=>{},get:async()=>[{id:'acoustic_scream',zone_id:zoneId,ready:true,execution_kind:'fresh_inference',default_model:'YAMNet'}],
    post:async path=>path==='/testing/runs'?{id:'negative',status:'COMPLETED',zone_id:zoneId,result:{output_origin:'fresh_raw_input_inference',candidate_detected:false,event_delivery:{event_id:'negative-event'}}}:
      {observation:{source_mode:'RECORDED_REPLAY',zone_id:zoneId,acoustic_events:[{kind:'normal_acoustic',confidence:.01}],backend_assessment:{event_id:'negative-event',level:'LOW'}}}};
  const result=await runPrivateTest('acoustic',fresh(),io,()=>{});
  assert.equal(result.results.acoustic.detected,'none');assert.equal(result.results.acoustic.status,'Failed');
});
test('A successful HTTP response with the wrong event type cannot pass an acoustic test',async()=>{
  const f=fixture(),post=f.io.post;
  f.io.post=async(path,body)=>{const value=await post(path,body);value.events[0].event.type='presence';return value;};
  const result=await runPrivateTest('acoustic',fresh(),f.io,()=>{});
  assert.equal(result.results.acoustic.status,'Failed');
});
test('A pending notification stays pending without a resend or fabricated acceptance',async()=>{
  const f=fixture('PENDING');
  const result=await runPrivateTest('sos',fresh(),f.io,()=>{});
  assert.equal(result.results.sos.status,'Incident Created');assert.equal(result.results.sos.notification,'PENDING');
  assert.equal(notificationView(result.results.sos.notification).label,'Pending');assert.equal(f.bodies.length,1);
});
test('SOS cannot pass without a canonical incident',async()=>{
  const f=fixture(),post=f.io.post;
  f.io.post=async(path,body)=>{const value=await post(path,body);value.events[0].incident=null;return value;};
  const result=await runPrivateTest('sos',fresh(),f.io,()=>{});
  assert.equal(result.results.sos.status,'Failed');assert.equal(testSummary('sos',result.results.sos),'Failed');
});

test('API acceptance requires Telegram ok=true and a valid message ID, not a cached label',()=>{
  const result={status:'Incident Created' as const,incidentId:'test'};
  const report={id:'test',is_test:true,level:'CRITICAL',notification_state:'API_ACCEPTED'};
  assert.equal(applySosReport(result,report).notification,'UNKNOWN');
  assert.equal(applySosReport(result,{...report,notifications:[{telegram_api_ok:false,telegram_message_id:123}]}).notification,'UNKNOWN');
  assert.equal(applySosReport(result,{...report,notifications:[{telegram_api_ok:true,telegram_message_id:123}]}).notification,'API_ACCEPTED');
});

test('A deliberate SOS click after acceptance creates a fresh incident; playback retries remain idempotent',async()=>{
  const f=fixture('API_ACCEPTED');const first=await runPrivateTest('sos',fresh(),f.io,()=>{});
  const next=prepareExplicitTest('sos',first);assert.notEqual(next,first);assert.ok(next.sosGeneration);
  const second=await runPrivateTest('sos',next,f.io,()=>{});
  assert.notEqual(first.results.sos.incidentId,second.results.sos.incidentId);assert.equal(f.incidents.size,2);
  assert.ok((f.bodies[1].tracking_session_id as string).length<=80);assert.ok((f.bodies[1].observation_id as string).length<=80);
  const retry=await runPrivateTest('sos',second,f.io,()=>{});
  assert.equal(retry.results.sos.incidentId,second.results.sos.incidentId);assert.equal(f.incidents.size,2);
  assert.notEqual(prepareExplicitTest('sos',resetTests(second)),second);
});
test('Pending or uncertain SOS sends never rotate request IDs; other tests retain identity',()=>{
  for(const notification of ['PENDING','UNKNOWN','DELIVERY_UNKNOWN',undefined]){
    const s=fresh();s.results.sos.notification=notification;assert.equal(prepareExplicitTest('sos',s),s);
  }
  const s=fresh();s.results.sos.notification='API_ACCEPTED';assert.equal(prepareExplicitTest('fusion',s),s);
});
