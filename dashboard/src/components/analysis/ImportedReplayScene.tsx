import React,{useEffect,useRef,useState} from 'react';
import * as THREE from 'three';
import {OrbitControls} from 'three/addons/controls/OrbitControls.js';
import {SyntheticFrame} from '../../lib/importedReplay';

// Adapted room/OrbitControls and radar RingGeometry patterns from threejs_test.
// Only the explicitly synthetic lab supplies coordinates; no production sensor data.
export function ImportedReplayScene({frame,time}:{frame:SyntheticFrame|null;time:number}){
 const mount=useRef<HTMLDivElement>(null),current=useRef({frame,time});current.current={frame,time};
 const [error,setError]=useState('');
 useEffect(()=>{
  const element=mount.current;if(!element)return;
  let renderer:THREE.WebGLRenderer;
  try{renderer=new THREE.WebGLRenderer({antialias:true});}catch{setError('3D unavailable; the supplied synthetic track table remains usable.');return;}
  renderer.setPixelRatio(Math.min(window.devicePixelRatio||1,1.5));element.appendChild(renderer.domElement);
  renderer.domElement.setAttribute('aria-label','Synthetic geometric archive replay; no camera feed');
  const scene=new THREE.Scene();scene.background=new THREE.Color(0xf1f5f9);
  const camera=new THREE.PerspectiveCamera(40,1,.1,100);camera.position.set(8.5,6,2.5);
  const controls=new OrbitControls(camera,renderer.domElement);controls.target.set(0,.8,0);controls.enableDamping=true;controls.minDistance=5;controls.maxDistance=40;
  scene.add(new THREE.AmbientLight(0xffffff,2));const light=new THREE.DirectionalLight(0xffffff,2);light.position.set(5,9,6);scene.add(light);
  const floor=new THREE.Mesh(new THREE.BoxGeometry(8,.1,6),new THREE.MeshStandardMaterial({color:0xe2e8f0}));floor.position.y=-.06;scene.add(floor);
  const grid=new THREE.GridHelper(8,16,0x94a3b8,0xcbd5e1);grid.scale.z=.75;scene.add(grid);
  const wallMaterial=new THREE.MeshStandardMaterial({color:0xffffff,transparent:true,opacity:.3,side:THREE.DoubleSide});
  const back=new THREE.Mesh(new THREE.PlaneGeometry(8,3),wallMaterial);back.position.set(0,1.5,-3);scene.add(back);
  const side=new THREE.Mesh(new THREE.PlaneGeometry(6,3),wallMaterial);side.rotation.y=Math.PI/2;side.position.set(-4,1.5,0);scene.add(side);
  const radar=new THREE.Mesh(new THREE.BoxGeometry(.45,.28,.12),new THREE.MeshStandardMaterial({color:0x0f766e}));radar.position.set(0,2.4,-2.9);scene.add(radar);
  const rings=Array.from({length:3},()=>{const ring=new THREE.Mesh(new THREE.RingGeometry(.3,.34,64),new THREE.MeshBasicMaterial({color:0x14b8a6,transparent:true,opacity:.5,side:THREE.DoubleSide,depthWrite:false}));ring.rotation.x=-Math.PI/2;ring.position.set(0,.03,-2.2);scene.add(ring);return ring;});
  const markers=new Map<number,{group:THREE.Group;body:THREE.Mesh;head:THREE.Mesh;material:THREE.MeshStandardMaterial}>();
  const observer=new ResizeObserver(()=>{
   const width=Math.max(1,element.clientWidth),height=Math.max(1,element.clientHeight);renderer.setSize(width,height);camera.aspect=width/height;
   // Fit the schematic room on narrow screens without moving supplied tracks.
   const direction=camera.position.clone().sub(controls.target).normalize();
   const right=new THREE.Vector3().crossVectors(new THREE.Vector3(0,1,0),direction).normalize();
   const up=new THREE.Vector3().crossVectors(direction,right),tangent=Math.tan(THREE.MathUtils.degToRad(camera.fov/2));let distance=5;
   for(const x of [-4,4])for(const y of [0,3])for(const z of [-3,3]){
    const point=new THREE.Vector3(x,y,z).sub(controls.target),depth=point.dot(direction);
    distance=Math.max(distance,depth+Math.abs(point.dot(right))/(tangent*camera.aspect),depth+Math.abs(point.dot(up))/tangent);
   }
   camera.position.copy(direction.multiplyScalar(distance*1.06)).add(controls.target);camera.updateProjectionMatrix();
  });observer.observe(element);
  let handle=0;
  const draw=()=>{
   const snapshot=current.current;markers.forEach(marker=>marker.group.visible=false);
   snapshot.frame?.tracks.forEach(track=>{
    let marker=markers.get(track.id);
    if(!marker){const material=new THREE.MeshStandardMaterial({color:0x0f766e}),group=new THREE.Group();const body=new THREE.Mesh(new THREE.CylinderGeometry(.13,.16,1,10),material),head=new THREE.Mesh(new THREE.SphereGeometry(.13,12,10),material);group.add(body,head);scene.add(group);marker={group,body,head,material};markers.set(track.id,marker);}
    marker.group.visible=true;marker.group.position.set(track.x-4,0,track.z-3);
    const height=Math.max(.05,track.height-.25);marker.body.scale.y=height;marker.body.position.y=height/2;marker.head.position.y=Math.max(.13,track.height-.13);
    marker.material.color.setHex(track.height<.7?0xef4444:0x0f766e);
   });
   rings.forEach((ring,index)=>{const cycle=(snapshot.time*.7+index*.33)%1;ring.scale.set(1+cycle*7,1+cycle*7,1);ring.material.opacity=.55*(1-cycle);});
   controls.update();renderer.render(scene,camera);handle=requestAnimationFrame(draw);
  };draw();
  return()=>{cancelAnimationFrame(handle);observer.disconnect();controls.dispose();const geometries=new Set<THREE.BufferGeometry>(),materials=new Set<THREE.Material>();scene.traverse(node=>{if(node instanceof THREE.Mesh||node instanceof THREE.LineSegments){geometries.add(node.geometry);for(const material of Array.isArray(node.material)?node.material:[node.material])materials.add(material);}});geometries.forEach(g=>g.dispose());materials.forEach(m=>m.dispose());renderer.dispose();renderer.domElement.remove();};
 },[]);
 return <div className="space-y-2"><div ref={mount} data-testid="imported-replay-scene" data-frame-time={frame?.time??''} data-track-count={frame?.tracks.length??0} className="h-[360px] sm:h-[420px] rounded-xl overflow-hidden border border-slate-200"/>{error&&<p role="status" className="text-amber-800 text-sm">{error}</p>}<p className="text-xs text-slate-500">Drag to orbit, scroll to zoom. Room and scan rings are illustrative. Red means a supplied low-height simulation marker, not a model-confirmed fall.</p></div>;
}
