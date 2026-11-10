import type {TrackingFrame,ScenarioId} from './trackingPlayback';
import {post} from '../../lib/api';

export const PRIVATE_DEMOS={
  normal:{label:'Normal Presence',scenario:'normal',at:5,expectation:'LOW · no test incident'},
  proximity:{label:'Close Proximity',scenario:'proximity',at:9,expectation:'Motion candidate only · no automatic danger incident'},
  repetitive:{label:'Repetitive Abnormal Motion',scenario:'repeated',at:12,expectation:'OBSERVE review candidate · not verified danger'},
  possible_fall:{label:'Possible Fall',scenario:'fall_only',at:9.2,expectation:'Radar-only OBSERVE candidate · human review required'},
  fall:{label:'Fall + Distress',scenario:'fall_impact',at:9.2,expectation:'Existing fall + impact fusion · human review required'},
  sos:{label:'SOS Emergency',scenario:'sos',at:5,expectation:'Direct test help request · independent of model confidence'},
} as const satisfies Record<string,{label:string;scenario:ScenarioId;at:number;expectation:string}>;
export type PrivateDemoId=keyof typeof PRIVATE_DEMOS;
export interface DemoRun {
  id:string;demo:PrivateDemoId;complete:boolean;incidentId?:string;events:any[];observation?:Record<string,unknown>;
  workflow?:'guided';assessment?:{level:string;reason:string};
}
const prefix='safesense-private-demo-v1:';
export function readRun(demo:PrivateDemoId,workflow?:'guided'):DemoRun|null {
  try{const value=JSON.parse(sessionStorage.getItem(prefix+(workflow?workflow+':':'')+demo)||'null');return value?.demo===demo&&/^[a-f0-9-]{36}$/.test(value.id)&&Array.isArray(value.events)?value:null;}catch{return null;}
}
export function storeRun(run:DemoRun){sessionStorage.setItem(prefix+(run.workflow?run.workflow+':':'')+run.demo,JSON.stringify(run));}
export function newRun(demo:PrivateDemoId,workflow?:'guided'):DemoRun {const run={id:crypto.randomUUID(),demo,complete:false,events:[],workflow};storeRun(run);return run;}

export async function deliverDemoRun(current:DemoRun,frame:TrackingFrame,onProgress:(run:DemoRun)=>void=()=>{}) {
  let prepared=prepareRun(current,frame);
  const persist=()=>{storeRun(prepared);onProgress(prepared);};persist();
  const delivery=await post('/sensors/observations',prepared.observation);
  if(delivery.events.length!==prepared.events.length)throw Error('Backend did not accept all current scenario signals');
  for(const result of delivery.events){
    prepared={...prepared,incidentId:result.incident?.id||prepared.incidentId,
      assessment:{level:result.event.level,reason:result.event.reason}};persist();
  }
  prepared={...prepared,complete:true};persist();return prepared;
}

export function prepareRun(run:DemoRun,frame:TrackingFrame):DemoRun {
  if(run.events.length)return run;
  const group='private-demo:'+run.id,zone='ZONE_TOILET_BLINDSPOT';
  const signals=run.demo==='normal'?[['presence','radar'],['normal_acoustic','acoustic']]:run.demo==='proximity'?[['presence','radar']]
    :run.demo==='repetitive'?[['rapid_motion','radar']]:run.demo==='possible_fall'?[['fall','radar']]:run.demo==='fall'?[['fall','radar'],['impact','acoustic']]:[['sos','sos']];
  const observedAt=new Date().toISOString();
  return {...run,observation:{observation_id:'private-demo-'+run.id,source_mode:'SIMULATION',device_id:'private-demo-'+run.demo,
    zone_id:zone,tracking_session_id:group,timestamp:observedAt,timestamp_basis:'CAPTURE_TIME',
    data_validity:'VALID',coordinate_frame:'zone_meters_x_right_y_forward_z_up',tracks:frame.tracks,
    radar_event:signals.find(([,modality])=>modality==='radar')?.[0],
    acoustic_events:signals.filter(([,modality])=>modality==='acoustic').map(([kind])=>({kind,confidence:1})),
    sos_state:run.demo==='sos'?'ACTIVE':'INACTIVE',
    evidence_reference:`SIMULATED tracking snapshot; ${PRIVATE_DEMOS[run.demo].label}; synthetic offset ${frame.time.toFixed(2)}s; no hardware`},
    events:signals.map(([type,modality])=>({zone,type,source:'simulation',sensor_modality:modality,processing_mode:'simulation',
      source_type:'SIMULATION',is_test:true,score:null,model_version:null,confidence:type==='sos'?0:1,
      event_id:group+':'+type,analysis_run_id:group,observed_at:observedAt,
      evidence_reference:`SIMULATED ${PRIVATE_DEMOS[run.demo].label}; run ${run.id}; offset ${frame.time.toFixed(2)}s; ${run.demo==='sos'?'direct test help request; confidence irrelevant':'unverified review/test signal; not proof of fighting or bullying'}; no CCTV or speech recording`}))};
}
