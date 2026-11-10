import type {SensorMode, SensorObservation} from './SensorObservationPanel';
import type {RiskLevel} from '../../types/safesense';
import type {MotionAnalysis} from './motionAnalysis';
import type {TestKind,TestResult} from './privateTestWorkflow';
import {simulationVisualRisk} from './sceneTracking';

export type Position = {x:number;y:number;z:number};
export type VisualTrack = {id:string;position:Position;velocity?:Position;quality?:number};
export type TrackingFrame = {sourceMode:SensorMode;streamId:string;time:number;tracks:VisualTrack[];highlightIds?:string[];fallIds?:string[];fallProgress?:Record<string,number>;visualRisk?:RiskLevel;animateBody?:boolean;holdBodyPose?:boolean;sosGesture?:number;sosIllustrative?:boolean};
export type TrailHistory=Record<string,{time:number;position:Position}[]>;
export const SCENARIOS = {
  arrivals: 'Staggered arrivals & departures',
  crossing: 'Two tracks passing in the aisle',
  busy: 'Six simultaneous anonymous tracks',
  repeated: 'Repeated back-and-forth motion (review demo)',
  proximity: 'Sustained nearby tracks (review demo)',
  normal: 'Normal Presence · SIMULATED',
  fall_only: 'Possible Fall · SIMULATED radar only',
  fall_impact: 'Possible Fall + Acoustic Impact · SIMULATED',
  sos: 'SOS Emergency · SIMULATED help request',
} as const;
export type ScenarioId = keyof typeof SCENARIOS;
export const DURATION = 40;
const routes: [number,number][][] = [
  [[-.35,3.35],[-.35,1.4],[-1.8,.4],[-2.5,-1.8],[-1.5,-2.3],[-.5,.1],[-.35,1.5],[-.35,3.35]],
  [[.3,3.35],[.3,1.2],[.4,-.1],[2.6,-1.5],[2.8,-2.5],[.6,-.3],[.3,1.2],[.3,3.35]],
  [[-.65,3.35],[-.65,1.2],[-2.7,1.1],[-3,-1],[-2.7,-2.7],[-1.2,.2],[-.65,1.2],[-.65,3.35]],
  [[.65,3.35],[.65,1.4],[.8,-.6],[2.6,-2.6],[1.8,-2.4],[.8,-.5],[.65,1.2],[.65,3.35]],
  [[-.1,3.35],[-.1,1.5],[-1,-.8],[-1.6,-2.5],[-.7,-2.7],[-1.1,.3],[-.1,1.5],[-.1,3.35]],
  [[.1,3.35],[.1,1.4],[.1,-1.6],[1.1,-2.7],[2.8,-1.9],[.1,-.8],[.1,1.4],[.1,3.35]],
];
const crossingRoutes:[number,number][][]=[
  [[-.35,3.35],[-.35,1.2],[-2.4,-.6],[-2,-1.4],[2,-1.4],[.3,-.6],[.3,1.4],[.3,3.35]],
  [[.35,3.35],[.35,1.2],[2.5,-.5],[2.2,-.9],[-2.2,-.9],[-.4,-.4],[-.35,1.4],[-.35,3.35]],
];

// Bounded cubic paths pass through the open aisle, around the original partition.
function position(route:[number,number][], u:number):Position {
  const scaled=Math.max(0,Math.min(1,u))*(route.length-1);
  const i=Math.min(route.length-2,Math.floor(scaled)),t=scaled-i;
  const a=route[Math.max(0,i-1)],b=route[i],c=route[i+1],d=route[Math.min(route.length-1,i+2)];
  const axis=(n:number)=>.5*((2*b[n])+(-a[n]+c[n])*t+(2*a[n]-5*b[n]+4*c[n]-d[n])*t*t+(-a[n]+3*b[n]-3*c[n]+d[n])*t*t*t);
  return {x:axis(0),y:axis(1),z:.24};
}

export function simulationFrame(scenario:ScenarioId,time:number):TrackingFrame {
  if(scenario==='normal'){
    const frame=simulationFrame('arrivals',time);return {...frame,streamId:'simulation:normal',tracks:frame.tracks.slice(0,1)};
  }
  if(scenario==='sos'){
    const u=Math.max(0,Math.min(1,time/4)),ease=u*u*(3-2*u),rate=time>0&&time<4?6*u*(1-u)/4:0;
    const gesture=time>=4.3&&time<=5.7?Math.sin((time-4.3)/1.4*Math.PI):0;
    return {sourceMode:'SIMULATION',streamId:'simulation:sos',time,sosIllustrative:true,sosGesture:gesture,
      tracks:[{id:'SOS01',position:{x:-1.1-2.35*ease,y:.7-2.2*ease,z:1.2},velocity:{x:-2.35*rate,y:-2.2*rate,z:0}}]};
  }
  if(scenario==='fall_only'||scenario==='fall_impact'){
    const frame=motionScenario('proximity',Math.min(time,12));
    const tracks=frame.tracks.map((track,i)=>{
      const u=Math.max(0,Math.min(1,(time-8)/1.2)),s=u*u*(3-2*u);
      return i===0&&(scenario==='fall_only'||scenario==='fall_impact')?{...track,position:{...track.position,z:1.2-s},velocity:{...track.velocity!,z:time>=8&&time<9.2?-6*u*(1-u)/1.2:0}}:track;
    });
    return {...frame,streamId:'simulation:'+scenario,tracks};
  }
  if(scenario==='repeated'||scenario==='proximity')return motionScenario(scenario,time);
  const count=scenario==='busy'?6:scenario==='crossing'?2:4;
  const tracks:VisualTrack[]=[];
  for(let i=0;i<count;i++){
    const enter=scenario==='busy'?1+i*.9:scenario==='crossing'?1+i*.5:1+i*2;
    const leave=scenario==='busy'?32+i:26+i*3;
    if(time<enter || time>=leave)continue;
    const route=scenario==='crossing'?crossingRoutes[i]:routes[i];const duration=leave-enter;
    const at=(t:number)=>position(route,(t-enter)/duration);
    const p=at(time),a=at(Math.max(enter,time-.01)),b=at(Math.min(leave,time+.01));
    const dt=Math.min(leave,time+.01)-Math.max(enter,time-.01);
    tracks.push({id:`T${String(i+1).padStart(2,'0')}`,position:p,
      velocity:{x:(b.x-a.x)/dt,y:(b.y-a.y)/dt,z:0}});
  }
  return {sourceMode:'SIMULATION',streamId:'simulation:'+scenario,time,tracks};
}

export function simulatedSensorState(scenario:ScenarioId,time:number) {
  return {fall:(scenario==='fall_only'||scenario==='fall_impact')&&time>=9.2,
    impact:scenario==='fall_impact'&&time>=9.2,
    sos:scenario==='sos'&&time>=5};
}

/** The same envelope accepted by the future physical adapter; every value here is synthetic. */
export function simulationObservation(scenario:ScenarioId,time:number,sessionId:string,anchorMs:number):SensorObservation {
  const frame=simulationFrame(scenario,time),signals=simulatedSensorState(scenario,time);
  return {schema_version:1,observation_id:sessionId+':'+time.toFixed(3),source_mode:'SIMULATION',
    device_id:'simulation-'+scenario,zone_id:'ZONE_TOILET_BLINDSPOT',tracking_session_id:sessionId,
    timestamp:new Date(anchorMs+time*1000).toISOString(),timestamp_basis:'CAPTURE_TIME',data_validity:'VALID',
    validity_reason:'SIMULATED DEMO; synthetic capture clock, tracks and sensor metadata; no hardware measurements',
    coordinate_frame:'zone_meters_x_right_y_forward_z_up',tracks:frame.tracks,point_cloud:null,
    radar_event:signals.fall?'fall':frame.tracks.length?'presence':undefined,
    acoustic_events:signals.impact?[{kind:'impact',confidence:1}]:null,sos_state:signals.sos?'ACTIVE':'INACTIVE',
    confidence:1,evidence_reference:'SIMULATED DEMO; no CCTV, speech recording or physical acquisition'};
}

function motionScenario(scenario:'repeated'|'proximity',time:number):TrackingFrame {
  const tracks:VisualTrack[]=[];
  for(let i=0;i<2;i++){
    const enter=1+i,leave=37+i;
    if(time<enter||time>=leave)continue;
    const entry={x:i?.3:-.3,y:3.35,z:.24};
    const target=scenario==='proximity'?{x:i?-.2:-.8,y:-.8,z:.24}:{x:i?-2.6:-.8,y:i?.4:-1.2,z:.24};
    const blend=(a:Position,b:Position,u:number)=>{
      const v=Math.max(0,Math.min(1,u)),s=v*v*(3-2*v);
      return {x:a.x+(b.x-a.x)*s,y:a.y+(b.y-a.y)*s,z:.24};
    };
    const at=(t:number):Position=>{
      if(t<5)return blend(entry,target,(t-enter)/(5-enter));
      if(t>=33)return blend(target,entry,(t-33)/(leave-33));
      return scenario==='repeated'&&i===0?{...target,x:target.x+.65*Math.sin(Math.PI*(t-5))}:target;
    };
    const a=at(Math.max(enter,time-.01)),b=at(Math.min(leave,time+.01)),dt=Math.min(leave,time+.01)-Math.max(enter,time-.01);
    tracks.push({id:`T0${i+1}`,position:at(time),velocity:{x:(b.x-a.x)/dt,y:(b.y-a.y)/dt,z:0}});
  }
  return {sourceMode:'SIMULATION',streamId:'simulation:'+scenario,time,tracks};
}

export function observationFrame(observation:SensorObservation|null):TrackingFrame {
  const timestamp=observation?Date.parse(observation.timestamp):NaN;
  const timestampValid=Number.isFinite(timestamp)&&/(Z|[+-]\d{2}:\d{2})$/i.test(observation?.timestamp||'');
  const mode=observation?.source_mode||'LIVE_HARDWARE';
  const valid=observation?.data_validity==='VALID'&&timestampValid&&observation.coordinate_frame==='zone_meters_x_right_y_forward_z_up'
    &&(mode!=='LIVE_HARDWARE'||observation.hardware_verified===true);
  const tracks=Array.isArray(observation?.tracks)?observation.tracks:[];
  const ids=new Map<string,number>();tracks.forEach(track=>{if(track&&typeof track.id==='string')ids.set(track.id,(ids.get(track.id)||0)+1);});
  return {sourceMode:mode,streamId:mode+':'+(observation?.device_id||'disconnected')+':'+(observation?.tracking_session_id||''),
    time:timestampValid?timestamp/1000:0,
    tracks:valid?tracks.flatMap(t=>t&&typeof t.id==='string'&&t.id.length>0&&ids.get(t.id)===1&&t.position
      &&['x','y','z'].every(axis=>Number.isFinite(t.position![axis as keyof Position]))
      &&!observation.motion_analysis?.excluded_track_ids?.includes(t.id)?[{...t,position:t.position}]:[]):[],
    fallIds:valid&&observation.radar_event==='fall'?tracks.length===1?[tracks[0].id]:[]:[],
    highlightIds:valid?observation.motion_analysis?.highlighted_track_ids:[]};
}

export function distances(tracks:VisualTrack[]) {
  return tracks.flatMap((a,i)=>tracks.slice(i+1).map(b=>({a:a.id,b:b.id,
    meters:Math.hypot(a.position.x-b.position.x,a.position.y-b.position.y,a.position.z-b.position.z)})))
    .sort((a,b)=>a.meters-b.meters);
}

export type PlaybackSnapshot = {
  scenario:ScenarioId;time:number;playing:boolean;speed:number;trails:boolean;coverage:boolean;
  selectedId:string|null;frame:TrackingFrame;
  motionAnalysis:MotionAnalysis|null;analysisEpoch:string;
  test:TestPlayback|null;
  playbackStatus:'Playing'|'Paused'|'Completed';
  visual:ScenarioVisualState;
};
export type ScenarioVisualState={epoch:string;risk:RiskLevel;fallProgress:number;triggered:boolean;runId?:string;
  assessment?:{level:RiskLevel;reason:string};incidentId?:string;incidentStatus?:string};
const freshVisual=(runId?:string):ScenarioVisualState=>({epoch:crypto.randomUUID(),risk:'LOW',fallProgress:0,triggered:false,runId});
export const incidentClosed=(status?:string)=>status==='RESOLVED'||status==='FALSE_ALARM';
function scenarioTrigger(scenario:ScenarioId){return scenario==='normal'?8:scenario==='repeated'?12:scenario==='proximity'?9:scenario==='sos'?5:9.2;}
export type TestPlayback={kind:TestKind;requestId:string;result:TestResult;sourceMode:SensorMode;pulseUntil:number};
export function testSensorState(test:TestPlayback|null,time:number){
  // Response status never cancels a currently selected test visualization.
  return {radar:!!test&&test.kind==='fusion',
    fall:!!test&&test.kind==='fusion'&&time>=9.2,
    acoustic:test?(test.kind==='acoustic'?['scream','impact'].includes(test.result.detected||'')?test.result.detected:undefined:test.kind==='fusion'&&time>=9.2?'impact':undefined):undefined,
    sos:!!test&&test.kind==='sos'};
}

// The render loop publishes the same timestamped frame used by the scene (capped at 30 Hz).
export class TrackingPlayback {
  private listeners=new Set<()=>void>();
  private baseTime=0;
  private started=performance.now();
  private lastPublish=0;
  private observationAnchor=Date.now();
  private snapshot:PlaybackSnapshot={scenario:'arrivals',time:0,playing:false,speed:1,trails:true,coverage:true,
    selectedId:null,frame:simulationFrame('arrivals',0),motionAnalysis:null,analysisEpoch:crypto.randomUUID(),test:null,playbackStatus:'Paused',visual:freshVisual()};
  getSnapshot=()=>this.snapshot;
  subscribe=(fn:()=>void)=>{this.listeners.add(fn);return ()=>{this.listeners.delete(fn);};};
  currentTime(now=performance.now()) {return Math.min(DURATION,this.baseTime+(this.snapshot.playing?(now-this.started)/1000*this.snapshot.speed:0));}
  observation(now=performance.now()) {
    const observation=simulationObservation(this.snapshot.scenario,this.currentTime(now),this.snapshot.analysisEpoch,this.observationAnchor);
    const frame=this.viewFrame(this.snapshot.scenario,this.currentTime(now));
    return {...observation,tracks:frame.tracks,
      radar_event:this.snapshot.visual.fallProgress>=1?'fall':observation.radar_event,
      acoustic_events:observation.acoustic_events,
      sos_state:this.snapshot.scenario==='sos'&&this.snapshot.visual.triggered?'ACTIVE':observation.sos_state};
  }
  private viewFrame(scenario:ScenarioId,time:number){
    const visual=this.snapshot.visual,isFall=scenario==='fall_only'||scenario==='fall_impact';
    const poseTime=isFall&&visual.fallProgress>0?Math.max(time,8+visual.fallProgress*1.2):time;
    const frame=simulationFrame(scenario,poseTime);
    return {...frame,time,tracks:frame.tracks,
      visualRisk:visual.risk,fallProgress:isFall?{T01:visual.fallProgress*visual.fallProgress*(3-2*visual.fallProgress)}:undefined,
      fallIds:isFall&&visual.fallProgress>=1?['T01']:[]};
  }
  recentHistory(time=this.currentTime()):TrailHistory{
    const history:TrailHistory={};
    for(let i=31;i>=0;i--){
      const sample=time-i*.1;if(sample<0)continue;
      for(const track of (this.snapshot.scenario==='sos'?this.viewFrame(this.snapshot.scenario,sample):simulationFrame(this.snapshot.scenario,sample)).tracks){
        (history[track.id]??=[]).push({time:sample,position:{...track.position}});
      }
    }
    return history;
  }
  capture(now=performance.now()) {
    const observation=this.observation(now);
    const view=this.viewFrame(this.snapshot.scenario,this.currentTime(now));
    return {observation,frame:{...observationFrame(observation),time:this.currentTime(now),visualRisk:view.visualRisk,fallProgress:view.fallProgress,fallIds:view.fallIds,sosGesture:view.sosGesture,sosIllustrative:view.sosIllustrative}};
  }
  frame(now=performance.now()) {return this.capture(now).frame;}
  tick(now:number,renderFrame=false) {
    if(!this.snapshot.playing&&this.snapshot.time===this.currentTime(now))return;
    if(!renderFrame&&now-this.lastPublish<1000/30)return;
    this.lastPublish=now;
    const holdAt=this.snapshot.test?.kind==='sos'?7:12;
    const hold=!!this.snapshot.test&&['fusion','sos'].includes(this.snapshot.test.kind)&&this.currentTime(now)>=holdAt;
    const time=hold?holdAt:this.currentTime(now);
    this.snapshot={...this.snapshot,time,playing:hold||time>=DURATION?false:this.snapshot.playing};
    if(hold)this.baseTime=holdAt;
    if(time>=DURATION)this.baseTime=DURATION;
    this.deriveVisual();
    this.listeners.forEach(fn=>fn());
  }
  private change(patch:Partial<PlaybackSnapshot>,time=this.currentTime()) {
    this.baseTime=time;this.started=performance.now();
    this.snapshot={...this.snapshot,...patch,time};
    this.deriveVisual();
    this.listeners.forEach(fn=>fn());
  }
  start=()=>{
    const ended=this.currentTime()>=DURATION;
    this.change({playing:true,...(ended&&this.snapshot.scenario!=='fall_only'?{motionAnalysis:null,analysisEpoch:crypto.randomUUID(),visual:{...freshVisual(this.snapshot.visual.runId),assessment:this.snapshot.visual.assessment,incidentId:this.snapshot.visual.incidentId,incidentStatus:this.snapshot.visual.incidentStatus}}:{})},ended?0:this.currentTime());
  };
  pause=()=>this.change({playing:false});
  restart=()=>this.change({playing:true,selectedId:null,motionAnalysis:null,analysisEpoch:crypto.randomUUID(),visual:freshVisual(this.snapshot.visual.runId)},0);
  seek=(time:number)=>this.change({playing:false,motionAnalysis:null,analysisEpoch:crypto.randomUUID()},Math.max(0,Math.min(DURATION,time)));
  setSpeed=(speed:number)=>this.change({speed});
  setScenario=(scenario:ScenarioId)=>{
    this.change({scenario,playing:false,selectedId:null,motionAnalysis:null,analysisEpoch:crypto.randomUUID(),visual:freshVisual(),test:null},0);
  };
  setTrails=(trails:boolean)=>this.change({trails});
  setCoverage=(coverage:boolean)=>this.change({coverage});
  select=(selectedId:string|null)=>this.change({selectedId});
  setMotionAnalysis=(motionAnalysis:MotionAnalysis|null)=>{this.snapshot={...this.snapshot,motionAnalysis};this.deriveVisual();this.listeners.forEach(fn=>fn());};
  bindGuidedRun=(runId:string)=>this.change({visual:{...this.snapshot.visual,runId}});
  updateGuidedAssessment=(scenario:ScenarioId,runId:string,assessment:ScenarioVisualState['assessment'],incident?:{id:string;status?:string})=>{
    if(this.snapshot.test||this.snapshot.scenario!==scenario||this.snapshot.visual.runId!==runId)return;
    const visual={...this.snapshot.visual,assessment:assessment||this.snapshot.visual.assessment,
      incidentId:incident?.id||this.snapshot.visual.incidentId,incidentStatus:incident?.status||this.snapshot.visual.incidentStatus};
    if(JSON.stringify(visual)!==JSON.stringify(this.snapshot.visual))this.change({visual});
  };
  private deriveVisual(){
    const state=this.snapshot,previous=state.visual;
    const isFall=state.scenario==='fall_only'||state.scenario==='fall_impact';
    const fallProgress=isFall?Math.max(state.scenario==='fall_only'?previous.fallProgress:0,Math.max(0,Math.min(1,(state.time-8)/1.2))):0;
    const triggered=state.time>=scenarioTrigger(state.scenario);
    const status=state.test?.result.incidentStatus||previous.incidentStatus;
    // Scenario presentation and persisted response are independent domains.
    // Replaying a cached/resolved run must not turn a simulated fall green.
    const risk:RiskLevel=state.test?.kind==='acoustic'
      ?state.test.result.risk||'LOW'
      :state.scenario==='fall_only'&&previous.risk==='HIGH'?'HIGH':simulationVisualRisk(state.scenario,state.time,state.motionAnalysis);
    this.snapshot={...state,playbackStatus:state.time>=DURATION?'Completed':state.playing?'Playing':'Paused',
      visual:{...previous,risk,fallProgress,triggered,incidentId:state.test?.result.incidentId||previous.incidentId,incidentStatus:status}};
    this.snapshot={...this.snapshot,frame:this.viewFrame(state.scenario,state.time)};
  }
  beginTest=(kind:TestKind,requestId:string)=>{
    this.pause();
    this.setScenario(kind==='fusion'?'fall_impact':kind==='sos'?'sos':'normal');
    const test:TestPlayback={kind,requestId,result:{status:kind==='sos'?'Triggered':'Running'},
      sourceMode:kind==='acoustic'?'RECORDED_REPLAY':'SIMULATION',pulseUntil:performance.now()+8000};
    this.change({test,playing:kind!=='acoustic',speed:1},kind==='fusion'?6:0);
  };
  updateTest=(kind:TestKind,requestId:string,result:TestResult)=>{
    const test=this.snapshot.test;
    if(!test||test.kind!==kind||test.requestId!==requestId)return;
    if(['Running','Triggered'].includes(result.status))result={...result,risk:undefined,detected:undefined,incidentId:undefined,notification:undefined,recordedObservation:undefined};
    const changed=test.result.detected!==result.detected||test.result.risk!==result.risk;
    this.change({test:{...test,result,sourceMode:result.source?.startsWith('SIMULATED')?'SIMULATION':test.sourceMode,
      pulseUntil:changed?performance.now()+10000:test.pulseUntil}});
  };
  resetTest=()=>{
    this.pause();this.setScenario('normal');this.change({test:null,playing:false},0);
  };
}
