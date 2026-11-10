import {RiskTransition,RISK_PALETTE,RISK_LABEL_COLORS} from './riskAnimation';
import type {RiskLevel} from '../../types/safesense';
import {toRoomPoint,toTrackPoint,rectsOverlap,type LabelRect} from './sceneTracking';
import * as THREE from 'three';
import {createSensorTextSprite} from './sensorTextSprite';
import {distances,type Position,type TrackingFrame,type TrailHistory} from './trackingPlayback';
import {createAnonymousPersonAvatar} from './AnonymousPersonAvatar';

const CAPACITY=128, TRAIL_POINTS=32;
function text(sprite:THREE.Sprite,value:string) {
  if(sprite.userData.text===value&&sprite.userData.drawnColor===sprite.userData.labelColor)return;
  sprite.userData.text=value;
  sprite.userData.drawnColor=sprite.userData.labelColor;
  const map=sprite.material.map!;
  const canvas=map.image as HTMLCanvasElement,ctx=canvas.getContext('2d')!;
  ctx.clearRect(0,0,320,80);ctx.fillStyle='rgba(255,255,255,.95)';ctx.fillRect(0,0,320,80);
  ctx.fillStyle=sprite.userData.labelColor||'#0f172a';ctx.font=value.length>12?'bold 32px sans-serif':'bold 44px sans-serif';ctx.textAlign='center';ctx.textBaseline='middle';
  ctx.fillText(value,160,40,310);map.needsUpdate=true;
}

/** Bounded schematic avatar pool; no identity inference, measured skeleton or media. */
export class AnonymousTrackingLayer {
  readonly root=new THREE.Group();
  readonly targets:THREE.Object3D[]=[];
  private createSlot=(index:number)=>{
    const group=new THREE.Group();
    const avatar=createAnonymousPersonAvatar();
    avatar.group.scale.setScalar(.8);
    const label=createSensorTextSprite('');label.scale.set(1.65,.4,1);label.position.y=2+(index%3)*.20;
    label.userData.labelColor='#'+'22c55e'.padStart(6,'0');
    const ground=new THREE.Mesh(new THREE.CircleGeometry(.38,20),new THREE.MeshBasicMaterial({color:0x22c55e,transparent:true,opacity:.09,depthWrite:false,side:THREE.DoubleSide}));
    ground.rotation.x=-Math.PI/2;ground.renderOrder=1;
    this.root.add(ground);
    group.add(avatar.group,label);group.visible=false;this.root.add(group);this.targets.push(...avatar.meshes,label);
    const leader=new THREE.Line(new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(),new THREE.Vector3()]),new THREE.LineBasicMaterial({color:0x94a3b8,transparent:true,opacity:.45,depthTest:false,depthWrite:false}));
    leader.visible=false;leader.renderOrder=4;this.root.add(leader);
    const points=new Float32Array(TRAIL_POINTS*3);
    const geo=new THREE.BufferGeometry();geo.setAttribute('position',new THREE.BufferAttribute(points,3));geo.setDrawRange(0,0);
    const trail=new THREE.Line(geo,new THREE.LineBasicMaterial({color:0x22c55e,transparent:true,opacity:.55}));
    trail.frustumCulled=false;trail.visible=false;this.root.add(trail);
    return {id:'',group,avatar,label,ground,trail,leader,points,risk:new RiskTransition(),riskLevel:'LOW' as RiskLevel,lastTrails:false,phase:0,heading:0,stride:0,fallAmount:0,renderFrom:new THREE.Vector3(),renderTarget:new THREE.Vector3(),transitionAt:0,transitionDuration:0,targetScratch:new THREE.Vector3(),lastAnimationAt:performance.now(),previous:null as {time:number;position:Position}|null,history:[] as {time:number;position:Position}[]};
  };
  private slots=Array.from({length:8},(_,index)=>this.createSlot(index));
  needsAnimation=false;
  private line=new THREE.Line(new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(),new THREE.Vector3()]),
    new THREE.LineBasicMaterial({color:0x64748b,transparent:true,opacity:.75}));
  private distanceLabel=createSensorTextSprite('');
  private distanceLeader=new THREE.Line(new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(),new THREE.Vector3()]),new THREE.LineBasicMaterial({color:0x94a3b8,transparent:true,opacity:.4,depthTest:false,depthWrite:false}));
  private stream='';
  private primaryLabelId='';
  private previousTime=-Infinity;
  private lastText=-Infinity;
  private lastPair='';
  private poses=new Map<string,{fall:number;heading:number;legs:number[];arms:number[];knees:number[];elbows:number[];idle:number;twist:number;lean:number}>();
  private headings=new Map<string,number>();
  private labelOffsets=new Map<string,{dx:number;dy:number}>();
  stats={active:0,visible:0,trailVertices:0,trailSummary:[] as {id:string;count:number;firstTime:number;lastTime:number;first:Position;last:Position}[],distanceLinePoints:[] as Position[],bodyRects:[] as LabelRect[],labelRects:[] as LabelRect[],sourcePositions:[] as {id:string;x:number;y:number;z:number}[],positions:[] as {id:string;x:number;y:number;z:number}[],pairs:[] as ReturnType<typeof distances>,highlightedTrackIds:[] as string[],distanceText:'',avatars:[] as {id:string;color:string;legSwing:number;schematic:boolean;poseMeasured:boolean;pose:string;arms:number;groundColor:string;renderPosition:Position;bodyFootHeight:number;bodyScale:number;heading:number;idleOffset:number;kneeBend:number;armSwing:number;fallProgress:number;silhouette:string;riskLevel:RiskLevel;riskTarget:string;bodyPoseHeld:boolean}[]};
  constructor(){this.line.visible=false;this.distanceLabel.visible=false;this.distanceLabel.scale.set(1.8,.45,1);this.distanceLeader.visible=false;this.root.add(this.line,this.distanceLabel,this.distanceLeader);}
  update(frame:TrackingFrame,{trails,selectedId,playing=false,history,riskTime=frame.time,animateRisk=playing}:{trails:boolean;selectedId:string|null;playing?:boolean;history?:TrailHistory;riskTime?:number;animateRisk?:boolean}) {
    const now=performance.now();this.needsAnimation=false;
    const reset=frame.streamId!==this.stream||frame.time<this.previousTime||frame.time-this.previousTime>(frame.sourceMode==='SIMULATION'?1:5);
    if(reset){this.lastText=-Infinity;this.lastPair='';this.labelOffsets.clear();}
    this.stream=frame.streamId;this.previousTime=frame.time;
    while(this.slots.length<Math.min(CAPACITY,frame.tracks.length))this.slots.push(this.createSlot(this.slots.length));
    const active=frame.tracks.slice(0,CAPACITY),ids=new Set(active.map(t=>t.id));
    this.primaryLabelId=active.find(track=>track.id===selectedId)?.id||active[0]?.id||'';
    for(const slot of this.slots){if(reset||!ids.has(slot.id)){slot.history=[];slot.previous=null;slot.id='';}slot.group.visible=false;slot.leader.visible=false;slot.ground.visible=false;slot.trail.visible=false;}
    for(const track of active){
      const slot=this.slots.find(s=>s.id===track.id)||this.slots.find(s=>!s.id)!;
      slot.id=track.id;slot.group.visible=true;
      slot.avatar.meshes.forEach(mesh=>{mesh.userData.trackId=track.id;});slot.label.userData.trackId=track.id;
      const roomPoint=toRoomPoint(track.position);
      const target=slot.targetScratch.set(roomPoint.x,roomPoint.y,roomPoint.z);
      if(frame.sourceMode==='SIMULATION'||!slot.previous){slot.group.position.copy(target);slot.renderTarget.copy(target);slot.transitionDuration=0;}
      else if(!slot.renderTarget.equals(target)){
        slot.renderFrom.copy(slot.group.position);slot.renderTarget.copy(target);slot.transitionAt=now;
        slot.transitionDuration=Math.min(300,Math.max(50,(frame.time-slot.previous.time)*1000));
      }
      if(slot.transitionDuration){
        const u=Math.min(1,(now-slot.transitionAt)/slot.transitionDuration),blend=u*u*(3-2*u);
        slot.group.position.lerpVectors(slot.renderFrom,slot.renderTarget,blend);
        if(u<1)this.needsAnimation=true;else slot.transitionDuration=0;
      }
      if(history?.[track.id])slot.history=history[track.id].slice(-TRAIL_POINTS).map(point=>({time:point.time,position:{...point.position}}));
      const selected=track.id===selectedId;
      const candidate=frame.highlightIds?.includes(track.id)||false;
      const last=slot.history.at(-1);
      const previous=slot.previous;
      const dx=previous?track.position.x-previous.position.x:0,dy=previous?track.position.y-previous.position.y:0;
      const elapsed=previous?Math.max(0,frame.time-previous.time):0;
      const simulated=frame.sourceMode==='SIMULATION';
      const velocity=track.velocity;
      const speed=velocity&&Number.isFinite(velocity.x)&&Number.isFinite(velocity.y)?Math.hypot(velocity.x,velocity.y):elapsed>0?Math.hypot(dx,dy)/elapsed:0;
      const moving=speed>.03;
      const fall=frame.fallIds?.includes(track.id)||false;
      const held=frame.holdBodyPose?this.poses.get(track.id):undefined;
      const fallAmount=held?.fall??(simulated?(frame.fallProgress?.[track.id]??(fall?1:0)):(fall?1:0));
      // Pose does not independently invent severity. Closure/reset can clear the alert
      // while the last schematic fall pose remains visible.
      const risk:RiskLevel=frame.holdBodyPose||frame.visualRisk==='CRITICAL'||fallAmount>0||fall||candidate?frame.visualRisk||'LOW':'LOW';
      slot.riskLevel=risk;
      const color=slot.risk.sample(risk,riskTime,frame.streamId,animateRisk);
      if(!simulated&&animateRisk&&slot.risk.active)this.needsAnimation=true;
      slot.avatar.material.color.copy(color);slot.avatar.material.emissive.setHex(selected?0x0e7490:0);
      slot.avatar.material.emissiveIntensity=selected?.10:0;
      if(!previous){slot.phase=frame.time*2;slot.stride=moving?Math.min(1,speed):0;slot.heading=simulated&&frame.animateBody===false?this.headings.get(track.id)??0:velocity?Math.atan2(velocity.x,velocity.y):0;}
      const dt=simulated?Math.min(.1,elapsed):elapsed>0?0:Math.min(.05,Math.max(0,(now-slot.lastAnimationAt)/1000));
      slot.lastAnimationAt=now;
      const response=1-Math.exp(-9*dt);
      let turn=0;
      if(moving){
        const targetHeading=velocity?Math.atan2(velocity.x,velocity.y):Math.atan2(dx,dy);
        turn=Math.atan2(Math.sin(targetHeading-slot.heading),Math.cos(targetHeading-slot.heading));
        slot.heading+=turn*response;
      }
      if(simulated&&frame.sosIllustrative&&frame.time>=4)slot.heading=-Math.PI/2;
      if(held)slot.heading=held.heading;
      this.headings.set(track.id,slot.heading);
      if(!simulated&&previous&&moving&&Math.abs(turn)>.01&&now-slot.transitionAt<1000)this.needsAnimation=true;
      slot.avatar.group.rotation.y=slot.heading;
      slot.avatar.group.rotation.z=fallAmount*Math.PI/2;
      slot.fallAmount=fallAmount;
      // The sensor point is not a measured skeleton or foot joint. Keep its exact 3D anchor,
      // while placing the schematic body on the floor independently of sensor-centroid height.
      slot.avatar.group.position.y=.025+fallAmount*.155-slot.group.position.y;
      slot.label.position.y=fallAmount>.5?.65:2;
      slot.ground.visible=true;slot.ground.position.set(slot.group.position.x,.07,slot.group.position.z);
      slot.ground.material.color.copy(color);slot.ground.scale.set(fallAmount>0?1+fallAmount*.7:1,1+fallAmount*.2,1);
      slot.label.userData.labelColor=RISK_LABEL_COLORS[risk];
      // Only the explicit simulation clock drives breathing, gait and staged falls.
      if(simulated){
        slot.stride+=(Math.min(1,speed/1.1)*(moving?1:0)-slot.stride)*response;
        if(previous)slot.phase+=Math.hypot(dx,dy)*6.2;
      }
      const bodyMotion=simulated&&frame.animateBody!==false;
      const strength=bodyMotion?slot.stride*(1-fallAmount):0;
      const swing=Math.sin(slot.phase)*.24*strength;
      slot.avatar.legs[0].rotation.x=swing;slot.avatar.legs[1].rotation.x=-swing;
      slot.avatar.knees[0].rotation.x=Math.max(0,-Math.sin(slot.phase))*.08*strength;
      slot.avatar.knees[1].rotation.x=Math.max(0,Math.sin(slot.phase))*.08*strength;
      slot.avatar.arms[0].rotation.x=-swing*.72;slot.avatar.arms[1].rotation.x=swing*.72;
      slot.avatar.elbows.forEach(elbow=>{elbow.rotation.x=-.035*strength;});
      if(simulated&&frame.sosIllustrative){
        slot.avatar.arms[1].rotation.x=-2.4*(frame.sosGesture||0);
        slot.avatar.elbows[1].rotation.x=-.25*(frame.sosGesture||0);
      }
      const idle=bodyMotion?Math.sin(frame.time*1.7+slot.id.length)*.003*(1-fallAmount):0;
      slot.avatar.upperBody.position.y=idle+(bodyMotion?Math.abs(Math.sin(slot.phase*2))*.004*strength:0);
      slot.avatar.upperBody.rotation.y=bodyMotion?Math.sin(slot.phase)*.035*strength:0;
      slot.avatar.upperBody.rotation.z=bodyMotion?Math.max(-.035,Math.min(.035,-turn*.025))*strength:0;
      if(held){
        slot.avatar.legs.forEach((part,i)=>part.rotation.x=held.legs[i]);slot.avatar.arms.forEach((part,i)=>part.rotation.x=held.arms[i]);
        slot.avatar.knees.forEach((part,i)=>part.rotation.x=held.knees[i]);slot.avatar.elbows.forEach((part,i)=>part.rotation.x=held.elbows[i]);
        slot.avatar.upperBody.position.y=held.idle;slot.avatar.upperBody.rotation.y=held.twist;slot.avatar.upperBody.rotation.z=held.lean;
      }else if(simulated&&!frame.holdBodyPose){
        this.poses.set(track.id,{fall:fallAmount,heading:slot.heading,legs:slot.avatar.legs.map(p=>p.rotation.x),arms:slot.avatar.arms.map(p=>p.rotation.x),knees:slot.avatar.knees.map(p=>p.rotation.x),elbows:slot.avatar.elbows.map(p=>p.rotation.x),idle:slot.avatar.upperBody.position.y,twist:slot.avatar.upperBody.rotation.y,lean:slot.avatar.upperBody.rotation.z});
        if(this.poses.size>256)for(const id of this.poses.keys())if(!ids.has(id)){this.poses.delete(id);if(this.poses.size<=256)break;}
      }
      slot.previous={time:frame.time,position:{...track.position}};
      text(slot.label,frame.sosIllustrative?'SIM SOS (illustrative)':`${frame.sourceMode==='SIMULATION'?'SIM':'TRACK'} ${track.id.slice(0,8)}`);
      const changed=!last||frame.time-last.time>=.09;
      if(changed){
        slot.history.push({time:frame.time,position:{...track.position}});
        if(slot.history.length>TRAIL_POINTS)slot.history.shift();
      }
      if(trails&&(changed||history||!slot.lastTrails)){
        slot.history.forEach((point,i)=>{slot.points[i*3]=point.position.x;slot.points[i*3+1]=.065;slot.points[i*3+2]=point.position.y;});
        (slot.trail.geometry.attributes.position as THREE.BufferAttribute).needsUpdate=true;
        slot.trail.geometry.setDrawRange(0,slot.history.length);
      }
      slot.lastTrails=trails;
      slot.trail.visible=trails&&slot.history.length>1;
    }
    const displayed=active.map(track=>({...track,position:toTrackPoint(this.slots.find(s=>s.id===track.id)!.group.position)}));
    const pairs=distances(displayed),pair=pairs.find(p=>!selectedId||p.a===selectedId||p.b===selectedId);
    this.line.visible=!!pair;this.distanceLabel.visible=!!pair;
    if(!pair){text(this.distanceLabel,'');this.distanceLeader.visible=false;}
    if(pair){
      const a=displayed.find(t=>t.id===pair.a)!.position,b=displayed.find(t=>t.id===pair.b)!.position;
      const array=this.line.geometry.attributes.position as THREE.BufferAttribute;
      array.setXYZ(0,a.x,a.z,a.y);array.setXYZ(1,b.x,b.z,b.y);array.needsUpdate=true;
      this.line.geometry.computeBoundingSphere();
      this.distanceLabel.position.set((a.x+b.x)/2,Math.max(a.z,b.z)+.22,(a.y+b.y)/2);
      const pairId=pair.a+':'+pair.b;
      { // Distance text always describes this displayed frame, including Pause and seek.
        text(this.distanceLabel,`${frame.sourceMode==='SIMULATION'?'SIM':'TRACK'} ${pair.meters.toFixed(2)} m`);this.lastText=frame.time;this.lastPair=pairId;
      }
    }
    this.stats={active:frame.tracks.length,visible:active.length,trailSummary:this.slots.filter(s=>s.group.visible&&s.history.length).map(s=>({id:s.id,count:s.history.length,firstTime:s.history[0].time,lastTime:s.history.at(-1)!.time,first:s.history[0].position,last:s.history.at(-1)!.position})),distanceLinePoints:this.line.visible?[0,1].map(i=>{const p=this.line.geometry.attributes.position as THREE.BufferAttribute;return toTrackPoint({x:p.getX(i),y:p.getY(i),z:p.getZ(i)});}):[],trailVertices:this.slots.reduce((n,s)=>n+(s.trail.visible?s.history.length:0),0),
      bodyRects:this.stats.bodyRects,labelRects:this.stats.labelRects,sourcePositions:active.map(t=>({id:t.id,...t.position})),positions:displayed.map(t=>({id:t.id,...t.position})),pairs,highlightedTrackIds:active.filter(t=>frame.highlightIds?.includes(t.id)).map(t=>t.id),
      distanceText:this.distanceLabel.userData.text||'',avatars:active.map(t=>{const s=this.slots.find(s=>s.id===t.id)!;return {id:t.id,color:s.avatar.material.color.getHexString(),legSwing:s.avatar.legs[0].rotation.x,schematic:true,poseMeasured:false,pose:s.fallAmount>=.999?'lying-schematic':s.fallAmount>0?'falling-schematic':'standing-schematic',arms:s.avatar.arms.length,groundColor:s.ground.material.color.getHexString(),renderPosition:toTrackPoint(s.group.position),bodyFootHeight:s.group.position.y+s.avatar.group.position.y,bodyScale:.8,heading:s.heading,idleOffset:s.avatar.upperBody.position.y,kneeBend:s.avatar.knees[0].rotation.x,armSwing:s.avatar.arms[frame.sosIllustrative?1:0].rotation.x,fallProgress:s.fallAmount,silhouette:'smooth-reference-humanoid',riskLevel:s.riskLevel,riskTarget:RISK_PALETTE[s.riskLevel].toString(16).padStart(6,'0'),bodyPoseHeld:!!frame.holdBodyPose};})};
  }
  layoutLabels(camera:THREE.PerspectiveCamera,width:number,height:number,reserved:LabelRect[]=[],showTrackLabel=true){
    const used=[...reserved],rects:LabelRect[]=[],bodyRects:LabelRect[]=[];
    this.root.updateMatrixWorld(true);
    for(const slot of this.slots.filter(slot=>slot.group.visible)){
      const bounds=new THREE.Box3().setFromObject(slot.avatar.group);
      const points=[] as THREE.Vector3[];
      for(const x of [bounds.min.x,bounds.max.x])for(const y of [bounds.min.y,bounds.max.y])for(const z of [bounds.min.z,bounds.max.z])points.push(new THREE.Vector3(x,y,z).project(camera));
      const xs=points.map(p=>(p.x+1)*width/2),ys=points.map(p=>(1-p.y)*height/2);
      const box={id:'body:'+slot.id,x:Math.min(...xs)-3,y:Math.min(...ys)-3,width:Math.max(...xs)-Math.min(...xs)+6,height:Math.max(...ys)-Math.min(...ys)+6};
      used.push(box);bodyRects.push(box);
    }
    const place=(id:string,sprite:THREE.Sprite,anchor:THREE.Vector3,w:number,h:number,parent?:THREE.Group,leader?:THREE.Line)=>{
      const projected=anchor.clone().project(camera);
      if(projected.z<-1||projected.z>1){sprite.visible=false;return;}
      const px=(projected.x+1)*width/2,py=(1-projected.y)*height/2;
      let found:LabelRect|null=null,best=Infinity;
      for(let dy=-120;dy<=120;dy+=24)for(let dx=-160;dx<=160;dx+=20){
        const box={id,x:Math.max(7,Math.min(width-w-7,px-w/2+dx)),y:Math.max(7,Math.min(height-h-7,py-h-5+dy)),width:w,height:h};
        if(used.some(other=>rectsOverlap(box,other)))continue;
        const score=Math.hypot(box.x+w/2-px,box.y+h-py);
        if(score<best){found=box;best=score;}
      }
      const prior=this.labelOffsets.get(id);
      if(prior){
        const box={id,x:Math.max(7,Math.min(width-w-7,px+prior.dx)),y:Math.max(7,Math.min(height-h-7,py+prior.dy)),width:w,height:h};
        const score=Math.hypot(box.x+w/2-px,box.y+h-py);
        if(score<=best+14&&!used.some(other=>rectsOverlap(box,other))){found=box;best=score;}
      }
      if(!found){sprite.visible=false;if(leader)leader.visible=false;return;}
      this.labelOffsets.set(id,{dx:found.x-px,dy:found.y-py});
      used.push(found);rects.push(found);sprite.visible=true;
      const point=new THREE.Vector3((found.x+w/2)/width*2-1,1-(found.y+h/2)/height*2,projected.z).unproject(camera);
      if(leader){
        const positions=leader.geometry.attributes.position as THREE.BufferAttribute;
        positions.setXYZ(0,anchor.x,anchor.y,anchor.z);positions.setXYZ(1,point.x,point.y,point.z);positions.needsUpdate=true;
        leader.geometry.computeBoundingSphere();leader.visible=best>18;
      }
      sprite.position.copy(parent?parent.worldToLocal(point):point);
      const view=anchor.clone().applyMatrix4(camera.matrixWorldInverse);
      const unitsPerPixel=2*Math.max(.1,-view.z)*Math.tan(THREE.MathUtils.degToRad(camera.fov/2))/height;
      sprite.scale.set(w*unitsPerPixel,h*unitsPerPixel,1);
    };
    const visible=this.slots.filter(slot=>slot.group.visible).sort((a,b)=>a.id.localeCompare(b.id));
    for(const slot of visible){
      if(!showTrackLabel||slot.id!==this.primaryLabelId){slot.label.visible=false;slot.leader.visible=false;continue;}
      const anchor=new THREE.Vector3(slot.group.position.x,.025+1.45*(1-slot.fallAmount)+.5*slot.fallAmount,slot.group.position.z);
      place('track:'+slot.id,slot.label,anchor,68,21,slot.group,slot.leader);
    }
    if(this.line.visible){
      place('distance',this.distanceLabel,this.distanceLabel.position.clone(),104,22,undefined,this.distanceLeader);
    }else {this.distanceLabel.visible=false;this.distanceLeader.visible=false;}
    this.stats.labelRects=rects;this.stats.bodyRects=bodyRects;
  }
  dispose(){
    this.root.removeFromParent();
    this.root.traverse(object=>{
      const mesh=object as THREE.Mesh;mesh.geometry?.dispose();
      const materials=Array.isArray(mesh.material)?mesh.material:[mesh.material];
      materials.forEach(material=>{if(material&&'map' in material)(material as THREE.MeshBasicMaterial).map?.dispose();material?.dispose();});
    });
  }
}
