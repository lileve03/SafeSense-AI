import * as THREE from 'three';
import {mergeGeometries} from 'three/addons/utils/BufferGeometryUtils.js';

// Shared smooth silhouettes: no clothes, faces, joint seams, hands/boots or textures.
function surface(points:number[][],segments=18){
  const curve=new THREE.CatmullRomCurve3(points.map(([r,y])=>new THREE.Vector3(r,y,0)),false,'centripetal');
  return new THREE.LatheGeometry(curve.getPoints(18).map(p=>new THREE.Vector2(Math.max(0,p.x),p.y)),segments);
}
const sphere=new THREE.SphereGeometry(.18,20,14).translate(0,1.55,0);
const neck=new THREE.CapsuleGeometry(.065,.07,4,12).translate(0,1.355,0);
const headNeckGeometry=mergeGeometries([sphere,neck]);sphere.dispose();neck.dispose();
const torsoGeometry=surface([
  [0,.64],[.12,.655],[.185,.71],[.20,.82],[.202,.96],
  [.224,1.105],[.231,1.19],[.21,1.265],[.13,1.31],[0,1.335],
],20).scale(1,1,.78);
function roundedLimb(radius:number,length:number){
  return surface([[0,0],[radius*.65,-.018],[radius,-.075],[radius*.98,-length*.4],
    [radius*.86,-length+.075],[radius*.55,-length+.018],[0,-length]],12).scale(1,1,.94);
}
// Continuous arms and legs have round ends and a gentle taper, not exposed joints.
const legGeometry=roundedLimb(.09,.69).translate(0,.28,0);
const armGeometry=roundedLimb(.075,.59).translate(0,.25,0);
const anchorGeometry=new THREE.SphereGeometry(.20,8,6);

/** Reference-style faceless human. All body motion is schematic, never a radar skeleton. */
export function createAnonymousPersonAvatar(){
  const group=new THREE.Group(),upperBody=new THREE.Group();group.add(upperBody);
  const material=new THREE.MeshStandardMaterial({color:0x22c55e,roughness:.86,metalness:0,depthTest:true});
  const head=new THREE.Mesh(headNeckGeometry,material),body=new THREE.Mesh(torsoGeometry,material);
  upperBody.add(head,body);
  const knees:THREE.Group[]=[],elbows:THREE.Group[]=[],meshes:THREE.Mesh[]=[head,body];
  const legs=[-.12,.12].map(x=>{
    const hip=new THREE.Group();hip.position.set(x,.72,0);
    const flex=new THREE.Group();flex.position.y=-.28;
    const leg=new THREE.Mesh(legGeometry,material);flex.add(leg);hip.add(flex);group.add(hip);
    knees.push(flex);meshes.push(leg);return hip;
  });
  const arms=[-.285,.285].map((x,i)=>{
    const shoulder=new THREE.Group();shoulder.position.set(x,1.23,0);shoulder.rotation.z=i?-.035:.035;
    const flex=new THREE.Group();flex.position.y=-.25;
    const arm=new THREE.Mesh(armGeometry,material);flex.add(arm);shoulder.add(flex);upperBody.add(shoulder);
    elbows.push(flex);meshes.push(arm);return shoulder;
  });
  const anchor=new THREE.Mesh(anchorGeometry,new THREE.MeshBasicMaterial({transparent:true,opacity:0,depthWrite:false}));
  group.add(anchor);meshes.push(anchor);
  meshes.forEach(mesh=>{mesh.renderOrder=3;mesh.castShadow=false;});
  return {group,upperBody,material,legs,arms,knees,elbows,meshes};
}
