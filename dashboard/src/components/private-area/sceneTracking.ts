import type {SensorObservation} from './SensorObservationPanel';
import type {RiskLevel} from '../../types/safesense';
import type {MotionAnalysis} from './motionAnalysis';
import type {Position,ScenarioId} from './trackingPlayback';

/** Sensor X/right, Y/forward, Z/up -> Three.js X/right, Y/up, Z/forward. No rescaling or lateral offset. */
export const toRoomPoint=(p:Position)=>({x:p.x,y:p.z,z:p.y});
export const toTrackPoint=(p:{x:number;y:number;z:number}):Position=>({x:p.x,y:p.z,z:p.y});
/** Synthetic cue severity. Playback completion does not mean the safety event cleared. */
export function simulationVisualRisk(scenario:ScenarioId,time:number,analysis?:MotionAnalysis|null):RiskLevel{
  if(scenario==='sos')return time>=5?'CRITICAL':'LOW';
  // Demo review styling is independent of the uncorroborated backend assessment.
  if(scenario==='fall_only'&&time>=8)return 'HIGH';
  if(scenario==='fall_impact'&&time>=8)return time>=9.2?'HIGH':'WARNING';
  if((scenario==='proximity'||scenario==='repeated')&&analysis?.candidates.length)return 'OBSERVE';
  return 'LOW';
}
export type LabelRect={id:string;x:number;y:number;width:number;height:number};
export const rectsOverlap=(a:LabelRect,b:LabelRect,padding=3)=>a.x<b.x+b.width+padding&&a.x+a.width+padding>b.x&&a.y<b.y+b.height+padding&&a.y+a.height+padding>b.y;

export function observationVisualRisk(observation:SensorObservation|null):RiskLevel|undefined{
  if(!observation||observation.data_validity!=='VALID')return undefined;
  if(observation.source_mode==='LIVE_HARDWARE'&&observation.hardware_verified!==true)return undefined;
  if(observation.backend_assessment)return observation.backend_assessment.level;
  if(observation.sos_state==='ACTIVE')return 'CRITICAL';
  if(observation.radar_event==='fall')return 'OBSERVE';
  return observation.motion_analysis?.candidates.length?'OBSERVE':'LOW';
}
