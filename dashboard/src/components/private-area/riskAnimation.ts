import * as THREE from 'three';
import type {RiskLevel} from '../../types/safesense';
export const RISK_PALETTE:Record<RiskLevel,number>={LOW:0x22c55e,OBSERVE:0xeab308,WARNING:0xf97316,HIGH:0xef4444,CRITICAL:0xfb3148};
export const RISK_LABEL_COLORS:Record<RiskLevel,string>={LOW:'#15803d',OBSERVE:'#854d0e',WARNING:'#9a3412',HIGH:'#b91c1c',CRITICAL:'#9f1239'};
/** Presentation-clock crossfade: simulation time or bounded replay display time. Simulation Pause/seek snap consistently. */
export class RiskTransition{
  readonly color=new THREE.Color(RISK_PALETTE.LOW);
  private target=new THREE.Color();private epoch='';private time=-Infinity;private level:RiskLevel='LOW';
  active=false;
  sample(level:RiskLevel,time:number,epoch:string,animate:boolean){
    this.target.setHex(RISK_PALETTE[level]);
    if(!animate||this.epoch!==epoch||time<this.time||!Number.isFinite(this.time))this.color.copy(this.target);
    else if(this.level===level)this.color.lerp(this.target,1-Math.exp(-Math.min(.25,Math.max(0,time-this.time))/.25));
    if(Math.abs(this.color.r-this.target.r)+Math.abs(this.color.g-this.target.g)+Math.abs(this.color.b-this.target.b)<.002)this.color.copy(this.target);
    this.active=!this.color.equals(this.target);
    this.time=time;this.epoch=epoch;this.level=level;return this.color;
  }
}
