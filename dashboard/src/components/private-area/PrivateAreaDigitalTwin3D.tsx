import {RiskTransition} from './riskAnimation';
import {type LabelRect} from './sceneTracking';
import type {SimFrame} from './RadarTrackingSimulation';
import type {SensorObservation} from './SensorObservationPanel';
import {AnonymousTrackingLayer} from './AnonymousTrackingLayer';
import {TrackingPlayback,observationFrame,simulatedSensorState,testSensorState,type TrackingFrame} from './trackingPlayback';
import {createSensorTextSprite} from './sensorTextSprite';
import React, { useEffect, useRef, useState,useSyncExternalStore } from 'react';
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { RiskLevel } from '../../types/safesense';
import { ZoomIn, ZoomOut, RotateCcw, Radio } from 'lucide-react';

interface PrivateAreaDigitalTwin3DProps {
  playback:TrackingPlayback;
  observation?: SensorObservation | null;
  level: RiskLevel;
  riskScore: number;
  incidentLevel?:RiskLevel;
  hasVisualData?:boolean;
  fallDetected?: boolean;
  motionLevel?: string;
  interpersonalDistance?: number;
  occupants?: number;
  acousticEvent?: string;
  isSimulated?: boolean;
  scenarioId?: string | null;
  presenceIndicated?: boolean;
  sosActive?: boolean;
  processingLabel?: string;
  onIncidentClick?: () => void;
  radarObserved?: boolean;
  observationTimestamp?: string;
  trackingPreview?:SimFrame|null;
}

export const PrivateAreaDigitalTwin3D: React.FC<PrivateAreaDigitalTwin3DProps> = ({
  playback,
  observation=null,
  level,
  riskScore,
  incidentLevel,
  hasVisualData=true,
  fallDetected = false,
  motionLevel = 'Nominal',
  interpersonalDistance = 0.8,
  occupants = 2,
  acousticEvent,
  isSimulated = true,
  scenarioId,
  presenceIndicated = false,
  sosActive = false,
  processingLabel = 'simulation',
  onIncidentClick,
  radarObserved = false,
  observationTimestamp,
  trackingPreview=null,
}) => {
  const sceneState=useSyncExternalStore(playback.subscribe,playback.getSnapshot);
  const sceneTest=sceneState.test;
  const [selectedFixture,setSelectedFixture]=useState<'radar'|'acoustic'|'sos'|null>(null);
  const trackingLayerRef=useRef<AnonymousTrackingLayer|null>(null);
  const [showSensorLabels,setShowSensorLabels]=useState(false);
  useEffect(()=>{
    const scene=sceneRef.current;
    if(!scene || !observation || observation.data_validity!=='VALID')return;
    const group=new THREE.Group();
    const points=observation.point_cloud||[];
    const geometry=new THREE.BufferGeometry().setFromPoints(points.map(p=>new THREE.Vector3(p.x,p.z,p.y)));
    const material=new THREE.PointsMaterial({color:0x0891b2,size:.1});
    group.add(new THREE.Points(geometry,material));scene.add(group);invalidateRef.current();
    return ()=>{scene.remove(group);geometry.dispose();material.dispose();invalidateRef.current();};
  },[observation]);
  const sensorLabelsRef=useRef<THREE.Group|null>(null);
  const mountRef = useRef<HTMLDivElement>(null);
  const sceneRef = useRef<THREE.Scene | null>(null);
  const rendererRef = useRef<THREE.WebGLRenderer | null>(null);
  const cameraRef = useRef<THREE.PerspectiveCamera | null>(null);

  // Mesh refs for dynamic animation
  const avatar1Ref = useRef<THREE.Group | null>(null);
  const avatar2Ref = useRef<THREE.Group | null>(null);
  const radarConeRef = useRef<THREE.Mesh | null>(null);
  const radarWaveRef = useRef<THREE.Mesh | null>(null);
  const ambientLightRef = useRef<THREE.AmbientLight | null>(null);
  const dirLightRef = useRef<THREE.DirectionalLight | null>(null);
  const sosBoxRef = useRef<THREE.Mesh | null>(null);
  const showPresence = isSimulated ? occupants > 0 : presenceIndicated;
  const showRadar = isSimulated || radarObserved || presenceIndicated;
  const acousticActive = !!acousticEvent && (isSimulated ? /scream|impact|bump|alarm|distress/i.test(acousticEvent) : ['scream', 'impact'].includes(acousticEvent));
  const controlsRef = useRef<OrbitControls | null>(null);
  const invalidateRef = useRef<() => void>(() => {});
  const radarStatusRef = useRef<THREE.Mesh | null>(null);
  const acousticStatusRef = useRef<THREE.Mesh | null>(null);
  const dynamicRef = useRef({ isSimulated, showRadar, observation, trackingPreview, level,hasVisualData });
  dynamicRef.current = { isSimulated, showRadar, observation, trackingPreview, level,hasVisualData };
  const distanceLineRef = useRef<THREE.Line | null>(null);

  // Preserve the original camera position while using the reviewed project's touch-safe controls.
  const cameraAngleRef = useRef({ theta: -.55, phi: .72, radius: 13.5 });

  // Main Three.js Scene Setup
  useEffect(() => {
    const container = mountRef.current;
    if (!container) return;

    const width = container.clientWidth || 600;
    const height = container.clientHeight || 420;

    // 1. Scene & Camera
    const scene = new THREE.Scene();
    sceneRef.current = scene;
    scene.background = new THREE.Color(0xF8FAFC);

    const camera = new THREE.PerspectiveCamera(40, width / height, 0.1, 100);
    cameraRef.current = camera;

    const updateCameraPos = () => {
      const { theta, phi, radius } = cameraAngleRef.current;
      camera.position.x = radius * Math.sin(theta) * Math.cos(phi);
      camera.position.y = radius * Math.sin(phi);
      camera.position.z = radius * Math.cos(theta) * Math.cos(phi);
      camera.lookAt(0, 1.2, 0);
    };
    updateCameraPos();

    // 2. Renderer
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    rendererRef.current = renderer;
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.5));
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    // Room and lights are static; anonymous markers do not cast shadows.
    renderer.shadowMap.autoUpdate = false;
    renderer.shadowMap.needsUpdate = true;

    container.innerHTML = '';
    container.appendChild(renderer.domElement);
    renderer.domElement.setAttribute('aria-label', 'Private-zone abstract 3D sensor visualization');
    renderer.domElement.style.touchAction = 'none';
    const controls = new OrbitControls(camera, renderer.domElement);
    controls.target.set(0, 1.2, 0);
    controls.enablePan = false;
    controls.minDistance = 6;
    controls.maxDistance = 20;
    controls.minPolarAngle = 0.35;
    controls.maxPolarAngle = 1.42;
    controls.update();
    controls.saveState();
    controlsRef.current = controls;

    // 3. Lighting
    const ambientLight = new THREE.AmbientLight(0xE0F2FE, 1.8);
    ambientLightRef.current = ambientLight;
    scene.add(ambientLight);

    const dirLight = new THREE.DirectionalLight(0x38BDF8, 1.5);
    dirLightRef.current = dirLight;
    dirLight.position.set(8, 12, 6);
    dirLight.castShadow = true;
    dirLight.shadow.mapSize.width = 1024;
    dirLight.shadow.mapSize.height = 1024;
    scene.add(dirLight);

    const fillLight = new THREE.DirectionalLight(0xFFFFFF, 0.8);
    fillLight.position.set(-6, 8, -6);
    scene.add(fillLight);

    // 4. Room Construction (White/light-grey semi-transparent room)
    const roomGroup = new THREE.Group();
    scene.add(roomGroup);

    // Floor Plate
    const floorGeo = new THREE.BoxGeometry(8, 0.2, 7);
    const floorMat = new THREE.MeshStandardMaterial({
      color: 0xFFFFFF,
      roughness: 0.2,
      metalness: 0.05,
    });
    const floor = new THREE.Mesh(floorGeo, floorMat);
    floor.position.y = -0.1;
    floor.receiveShadow = true;
    roomGroup.add(floor);

    // Explicit risk footprint: lighting alone is washed out by the white fill light.
    // This is a schematic coverage tint, never a measured hardware range.
    const coverageMat = new THREE.MeshBasicMaterial({color:0x94a3b8,transparent:true,opacity:.22,depthWrite:false,side:THREE.DoubleSide});
    const coverageFloor = new THREE.Mesh(new THREE.CircleGeometry(3.6,64),coverageMat);
    coverageFloor.rotation.x=-Math.PI/2;
    coverageFloor.position.y=.018;
    roomGroup.add(coverageFloor);

    // Perspective Floor Grid Lines
    const gridHelper = new THREE.GridHelper(7.6, 16, 0x94A3B8, 0xE2E8F0);
    gridHelper.position.y = 0.01;
    roomGroup.add(gridHelper);

    // Semi-Transparent Walls
    const wallMat = new THREE.MeshPhysicalMaterial({
      color: 0xFFFFFF,
      transparent: true,
      opacity: 0.35,
      roughness: 0.15,
      transmission: 0.4,
      thickness: 0.5,
      side: THREE.DoubleSide,
    });

    const wallEdgeMat = new THREE.LineBasicMaterial({ color: 0xCBD5E1, linewidth: 2 });

    // Back Wall
    const backWallGeo = new THREE.PlaneGeometry(8, 4);
    const backWall = new THREE.Mesh(backWallGeo, wallMat);
    backWall.position.set(0, 2, -3.5);
    roomGroup.add(backWall);

    const backEdge = new THREE.LineSegments(new THREE.EdgesGeometry(backWallGeo), wallEdgeMat);
    backEdge.position.set(0, 2, -3.5);
    roomGroup.add(backEdge);

    // Left Wall
    const leftWallGeo = new THREE.PlaneGeometry(7, 4);
    const leftWall = new THREE.Mesh(leftWallGeo, wallMat);
    leftWall.position.set(-4, 2, 0);
    leftWall.rotation.y = Math.PI / 2;
    roomGroup.add(leftWall);

    const leftEdge = new THREE.LineSegments(new THREE.EdgesGeometry(leftWallGeo), wallEdgeMat);
    leftEdge.position.set(-4, 2, 0);
    leftEdge.rotation.y = Math.PI / 2;
    roomGroup.add(leftEdge);

    // Privacy Partition Screen (Entrance Privacy Alcove)
    const screenGeo = new THREE.BoxGeometry(0.1, 3.2, 2.5);
    const screenMat = new THREE.MeshStandardMaterial({
      color: 0xF1F5F9,
      roughness: 0.4,
    });
    const screen = new THREE.Mesh(screenGeo, screenMat);
    screen.position.set(1.5, 1.6, 2.2);
    screen.castShadow = true;
    roomGroup.add(screen);

    // Wall Mounted Hardware SOS Panic Button
    const sosBoxGeo = new THREE.BoxGeometry(0.12, 0.4, 0.3);
    const sosBoxMat = new THREE.MeshStandardMaterial({ color: 0xEF4444 });
    const sosBox = new THREE.Mesh(sosBoxGeo, sosBoxMat);
    sosBox.position.set(-3.94, 2.2, -1.5);
    roomGroup.add(sosBox);
    sosBoxRef.current = sosBox;

    // 5. Radar Coverage Visualization (60GHz mmWave Ceiling Sensor)
    const radarGroup = new THREE.Group();
    radarGroup.position.set(0, 3.9, 0);
    scene.add(radarGroup);

    // Radar Emitter Dome
    const emitterGeo = new THREE.CylinderGeometry(0.25, 0.35, 0.15, 24);
    const emitterMat = new THREE.MeshStandardMaterial({ color: 0x0F172A, metalness: 0.8 });
    const emitter = new THREE.Mesh(emitterGeo, emitterMat);
    radarGroup.add(emitter);

    // Radar Scanning Beam / Cone
    const coneGeo = new THREE.ConeGeometry(3.6, 3.9, 32, 1, true);
    const coneMat = new THREE.MeshBasicMaterial({
      color: 0x94A3B8,
      transparent: true,
      opacity: 0.10,
      depthWrite: false,
      side: THREE.DoubleSide,
      wireframe: false,
    });
    const radarCone = new THREE.Mesh(coneGeo, coneMat);
    radarCone.position.y = -1.95;
    radarConeRef.current = radarCone;
    radarGroup.add(radarCone);
    radarCone.visible = showRadar;

    // Radar Sweeping Wave Ring
    const waveGeo = new THREE.RingGeometry(0.1, 0.3, 32);
    const waveMat = new THREE.MeshBasicMaterial({
      color: 0x94A3B8,
      transparent: true,
      opacity: 0.16,
      depthWrite: false,
      side: THREE.DoubleSide,
    });
    const radarWave = new THREE.Mesh(waveGeo, waveMat);
    radarWave.rotation.x = -Math.PI / 2;
    radarWave.position.y = -3.87; // Floor projection of the configured radar sensor (world y=.03).
    radarWaveRef.current = radarWave;
    radarGroup.add(radarWave);
    radarWave.visible = showRadar;

    // Adapted from threejs_test: low-poly rings mark schematic sensor fixtures.
    // They describe source status, never a person's location or measured range.
    const statusRing = new THREE.Mesh(new THREE.RingGeometry(0.38, 0.46, 24),
      new THREE.MeshBasicMaterial({ color: 0x94A3B8, side: THREE.DoubleSide }));
    statusRing.rotation.x = Math.PI / 2;
    statusRing.position.y = -0.12;
    radarGroup.add(statusRing);
    radarStatusRef.current = statusRing;
    const acousticMarker = new THREE.Mesh(new THREE.IcosahedronGeometry(0.16, 0),
      new THREE.MeshStandardMaterial({ color: 0x64748B, roughness: 0.6 }));
    acousticMarker.position.set(-3.9, 3.35, -0.8);
    roomGroup.add(acousticMarker);
    acousticStatusRef.current = acousticMarker;
    const labels=new THREE.Group();scene.add(labels);sensorLabelsRef.current=labels;
    const fixtures=[
      {kind:'radar',text:'RADAR (schematic)',mesh:emitter,position:new THREE.Vector3(1.6,3.5,0.4)},
      {kind:'acoustic',text:'ACOUSTIC',mesh:acousticMarker,position:new THREE.Vector3(-2.8,1.1,0.8)},
      {kind:'sos',text:'SOS',mesh:sosBox,position:new THREE.Vector3(-2.8,0.65,-1.6)},
    ] as const;
    const clickTargets:THREE.Object3D[]=[];
    const annotations=new Map<string,{sprite:THREE.Sprite;line:THREE.Line;anchor:THREE.Vector3}>();
    for(const fixture of fixtures){
      const label=createSensorTextSprite(fixture.text);label.scale.set(1.1,.26,1);label.position.copy(fixture.position);
      label.userData.sensorKind=fixture.kind;fixture.mesh.userData.sensorKind=fixture.kind;
      labels.add(label);clickTargets.push(label,fixture.mesh);
      const anchor=fixture.mesh.getWorldPosition(new THREE.Vector3());
      const line=new THREE.Line(new THREE.BufferGeometry().setFromPoints([anchor,fixture.position]),
        new THREE.LineBasicMaterial({color:0x64748B,transparent:true,opacity:0.5}));
      labels.add(line);annotations.set(fixture.kind,{sprite:label,line,anchor});
      line.userData.sensorKind=fixture.kind;
    }
    const sensorHalos=new Map(fixtures.map(fixture=>{
      const halo=new THREE.Mesh(new THREE.RingGeometry(.23,.30,32),new THREE.MeshBasicMaterial({
        color:fixture.kind==='sos'?0xef4444:fixture.kind==='acoustic'?0xf59e0b:0x14b8a6,
        transparent:true,opacity:.8,depthTest:false,depthWrite:false,side:THREE.DoubleSide}));
      halo.position.copy(fixture.mesh.getWorldPosition(new THREE.Vector3()));halo.renderOrder=8;halo.visible=false;scene.add(halo);
      return [fixture.kind,halo] as const;
    }));
    const raycaster=new THREE.Raycaster();let pointerStart={x:0,y:0};
    const pointerDown=(event:PointerEvent)=>{pointerStart={x:event.clientX,y:event.clientY};};
    const pointerUp=(event:PointerEvent)=>{
      if(Math.hypot(event.clientX-pointerStart.x,event.clientY-pointerStart.y)>5)return;
      const bounds=renderer.domElement.getBoundingClientRect();
      raycaster.setFromCamera(new THREE.Vector2((event.clientX-bounds.left)/bounds.width*2-1,-(event.clientY-bounds.top)/bounds.height*2+1),camera);
      const targets=[...clickTargets.filter(target=>target.visible&&(target.parent!==labels||labels.visible)),
        ...(trackingLayerRef.current?.targets.filter(target=>{let object:THREE.Object3D|null=target;while(object){if(!object.visible)return false;object=object.parent;}return true;})||[])];
      const hit=raycaster.intersectObjects(targets,false)[0];
      if(hit?.object.userData.trackId){playback.select(hit.object.userData.trackId);setSelectedFixture(null);}
      else if(hit)setSelectedFixture(hit.object.userData.sensorKind);
    };
    renderer.domElement.addEventListener('pointerdown',pointerDown);
    renderer.domElement.addEventListener('pointerup',pointerUp);



    // 6. Anonymous Human Avatars (Pure Geometric Cylindrical Mannequins)
    // Avatar Helper: Stylized anonymous body (No faces, no clothing, completely anonymous)
    const createAnonymousAvatar = (accentColor = 0x64748B) => {
      const avatar = new THREE.Group();

      const mat = new THREE.MeshStandardMaterial({
        color: 0xF8FAFC,
        roughness: 0.3,
        metalness: 0.1,
      });

      const accentMat = new THREE.MeshStandardMaterial({
        color: accentColor,
        roughness: 0.2,
      });

      // Head (Smooth sphere with no facial features)
      const headGeo = new THREE.SphereGeometry(0.22, 24, 24);
      const head = new THREE.Mesh(headGeo, mat);
      head.position.y = 1.62;
      head.castShadow = true;
      avatar.add(head);

      // Torso
      const torsoGeo = new THREE.CylinderGeometry(0.22, 0.18, 0.7, 16);
      const torso = new THREE.Mesh(torsoGeo, mat);
      torso.position.y = 1.05;
      torso.castShadow = true;
      avatar.add(torso);

      // Chest / Spine Indicator
      const bandGeo = new THREE.CylinderGeometry(0.225, 0.225, 0.1, 16);
      const band = new THREE.Mesh(bandGeo, accentMat);
      band.position.y = 1.15;
      avatar.add(band);

      // Legs
      const legGeo = new THREE.CylinderGeometry(0.08, 0.07, 0.75, 12);
      const leftLeg = new THREE.Mesh(legGeo, mat);
      leftLeg.position.set(-0.11, 0.375, 0);
      leftLeg.castShadow = true;
      avatar.add(leftLeg);

      const rightLeg = new THREE.Mesh(legGeo, mat);
      rightLeg.position.set(0.11, 0.375, 0);
      rightLeg.castShadow = true;
      avatar.add(rightLeg);

      // Base Proximity Shadow Disc
      const shadowDiscGeo = new THREE.CircleGeometry(0.4, 24);
      const shadowDiscMat = new THREE.MeshBasicMaterial({
        color: 0x0F172A,
        transparent: true,
        opacity: 0.15,
      });
      const shadowDisc = new THREE.Mesh(shadowDiscGeo, shadowDiscMat);
      shadowDisc.rotation.x = -Math.PI / 2;
      shadowDisc.position.y = 0.02;
      avatar.add(shadowDisc);

      return avatar;
    };

    const avatar1 = createAnonymousAvatar(0x2563EB); // Lead Person
    const avatar2 = createAnonymousAvatar(0xF59E0B); // Second Person

    avatar1Ref.current = avatar1;
    avatar2Ref.current = avatar2;

    scene.add(avatar1);
    scene.add(avatar2);
    avatar1.visible = false;
    avatar2.visible = false;

    // Initial Positions
    avatar1.position.set(-0.4, 0, -0.3);
    avatar2.position.set(0.4, 0, 0.3);

    // 7. Distance Annotation Bracket Line between Avatars
    const lineMat = new THREE.LineDashedMaterial({
      color: 0x64748B,
      dashSize: 0.15,
      gapSize: 0.08,
    });
    const lineGeo = new THREE.BufferGeometry().setFromPoints([
      new THREE.Vector3(-0.4, 0.6, -0.3),
      new THREE.Vector3(0.4, 0.6, 0.3),
    ]);
    const distanceLine = new THREE.Line(lineGeo, lineMat);
    distanceLine.computeLineDistances();
    distanceLineRef.current = distanceLine;
    scene.add(distanceLine);
    distanceLine.visible = false;

    // Tracking annotations render once after the original room. They need no lighting
    // or transmission pass and remain readable behind the privacy partition.
    const trackingLayer=new AnonymousTrackingLayer();const trackingScene=new THREE.Scene();
    trackingScene.add(new THREE.HemisphereLight(0xffffff,0x64748b,2));
    trackingScene.add(trackingLayer.root);trackingLayerRef.current=trackingLayer;
    renderer.info.autoReset=false;

    // Demand rendering for recorded observations; cap illustrative simulation at 30 FPS.
    let animationFrameId = 0;
    let dirty = true;
    let lastRender = 0;
    let waveScale = 0.2;
    let lastDiagnostics=-Infinity;
    const riskTransition=new RiskTransition();
    const softLight=new THREE.Color(0xffffff);
    const unavailableColor=new THREE.Color(0x94a3b8);
    let trailEpoch='';
    const invalidate = () => {
      dirty = true;
      if (!animationFrameId) animationFrameId = requestAnimationFrame(animate);
    };
    invalidateRef.current = invalidate;
    const unsubscribePlayback=playback.subscribe(invalidate);
    const stampCamera = () => {
      container.dataset.cameraPosition = camera.position.toArray().map(n => n.toFixed(3)).join(',');
      invalidate();
    };
    controls.addEventListener('change', stampCamera);
    stampCamera();
    function animate(time: number) {
      const cpuStarted=performance.now();
      if (!container) return;
      animationFrameId = 0;
      const latest=dynamicRef.current;
      const before=playback.getSnapshot();
      const simulatedMotion = latest.isSimulated && !latest.trackingPreview && before.playing;
      const testPulse=!!before.test&&time<before.test.pulseUntil;
      if (document.hidden || (!dirty && !simulatedMotion && !testPulse && !trackingLayer.needsAnimation && !riskTransition.active)) return;
      if (time - lastRender < 1000 / 30) {
        animationFrameId = requestAnimationFrame(animate);
        return;
      }
      if(latest.isSimulated&&!latest.trackingPreview)playback.tick(time,true);
      const state=playback.getSnapshot(),capture=playback.capture(time);
      const frame:TrackingFrame=latest.isSimulated ? latest.trackingPreview ? {
        sourceMode:'SIMULATION',streamId:'legacy-isolated-simulation',time:latest.trackingPreview.time_sec,
        tracks:latest.trackingPreview.tracks.map(t=>({id:t.id,position:{x:t.x,y:t.y,z:t.height/2},velocity:{x:t.vx,y:0,z:0}})),
      }:capture.frame:observationFrame(latest.observation);
      if(latest.isSimulated&&!latest.trackingPreview)frame.highlightIds=['proximity','repeated'].includes(state.scenario)?state.motionAnalysis?.highlighted_track_ids||[]:[];
      const testSignals=testSensorState(state.test,frame.time);
      const sensorSignals=state.test?{fall:testSignals.fall,impact:testSignals.acoustic==='impact',sos:testSignals.sos,acoustic:testSignals.acoustic}
        :latest.isSimulated&&!latest.trackingPreview?{...simulatedSensorState(state.scenario,frame.time),fall:state.visual.fallProgress>=1,sos:state.scenario==='sos'&&state.visual.triggered}:null;
      if(sensorSignals){
        if(sensorSignals.fall)frame.fallIds=['T01'];
        if(sensorSignals.fall)frame.highlightIds=[...new Set([...(frame.highlightIds||[]),'T01'])];
        if(acousticStatusRef.current){
          const material=acousticStatusRef.current.material as THREE.MeshStandardMaterial;
          material.color.setHex(sensorSignals.impact?0xf59e0b:0x64748b);material.emissive.setHex(sensorSignals.impact?0x78350f:0);
        }
        if(sosBoxRef.current){
          const material=sosBoxRef.current.material as THREE.MeshStandardMaterial;
          material.emissive.setHex(sensorSignals.sos?0xef4444:0);material.emissiveIntensity=sensorSignals.sos?.65+.2*Math.sin(frame.time*4):0;
        }
      }
      const level=latest.isSimulated&&!latest.trackingPreview?state.visual.risk:latest.level;
      const visualRisk=latest.hasVisualData?level:'UNAVAILABLE';
      frame.visualRisk=latest.hasVisualData?level:undefined;
      frame.animateBody=latest.isSimulated&&state.test?.kind!=='acoustic';
      frame.holdBodyPose=false;
      const history=latest.isSimulated&&!latest.trackingPreview&&state.trails&&trailEpoch!==state.analysisEpoch?playback.recentHistory(frame.time):undefined;
      if(latest.isSimulated)trailEpoch=state.trails?state.analysisEpoch:'';
      const riskTime=latest.isSimulated?frame.time:time/1000;
      const animateRisk=latest.isSimulated?simulatedMotion:latest.observation?.data_validity==='VALID';
      trackingLayer.update(frame,{trails:state.trails,selectedId:state.selectedId,playing:simulatedMotion,history,riskTime,animateRisk});
      const accent=latest.hasVisualData?riskTransition.sample(level,riskTime,frame.streamId,animateRisk):unavailableColor;
      if(!latest.hasVisualData)riskTransition.active=false;
      ambientLight.color.copy(accent).lerp(softLight,.55);
      dirLight.color.copy(accent).lerp(softLight,.24);
      floorMat.color.copy(accent).lerp(softLight,.65);
      floorMat.emissive.copy(accent);
      floorMat.emissiveIntensity=.12;
      const radarAccent=latest.showRadar?accent:unavailableColor;
      coverageMat.color.copy(radarAccent);
      coverageMat.opacity=.26;
      coverageFloor.visible=latest.isSimulated?state.coverage:latest.showRadar;
      if(radarConeRef.current)(radarConeRef.current.material as THREE.MeshBasicMaterial).color.copy(radarAccent);
      if(radarWaveRef.current)(radarWaveRef.current.material as THREE.MeshBasicMaterial).color.copy(radarAccent);
      if(radarStatusRef.current)(radarStatusRef.current.material as THREE.MeshBasicMaterial).color.copy(radarAccent);
      const pulsePhase=(time/1000*1.6)%1;
      const pulseStrength=.65+.55*(.5+.5*Math.sin(time/1000*7));
      const testActive=!!state.test;
      const highlightedSensors=state.test&&testActive?(state.test.kind==='acoustic'?['acoustic']:state.test.kind==='fusion'?['radar',...(frame.time>=9.2?['acoustic']:[])]:['sos']):sensorSignals?.sos?['sos']:[];
      for(const [kind,halo] of sensorHalos){
        const highlighted=highlightedSensors.includes(kind);
        halo.visible=highlighted;
        halo.quaternion.copy(camera.quaternion);
        halo.scale.setScalar(testPulse?1+pulsePhase*2:1.25);
        halo.material.opacity=testPulse ? .85*(1-pulsePhase) : .45;
        if(kind==='radar')halo.material.color.copy(radarAccent);
      }
      if(state.test){
        if(acousticStatusRef.current){
          const material=acousticStatusRef.current.material as THREE.MeshStandardMaterial;
          const active=highlightedSensors.includes('acoustic');
          material.color.setHex(active?0xf59e0b:0x64748b);material.emissive.setHex(active?0xf59e0b:0);
          material.emissiveIntensity=active?(testPulse?pulseStrength:.55):0;
          acousticStatusRef.current.scale.setScalar(active&&testPulse?1+pulseStrength*.18:1);
        }
        if(sosBoxRef.current){
          const material=sosBoxRef.current.material as THREE.MeshStandardMaterial;
          material.emissive.setHex(testSignals.sos?0xef4444:0);material.emissiveIntensity=testSignals.sos?(testPulse?pulseStrength:.65):0;
        }
        if(radarStatusRef.current&&!testSignals.radar)(radarStatusRef.current.material as THREE.MeshBasicMaterial).color.setHex(0x64748b);
      }else if(acousticStatusRef.current)acousticStatusRef.current.scale.setScalar(1);
      container.parentElement!.dataset.visualRisk=visualRisk;
      container.dataset.riskAccent=accent.getHexString();
      if(radarConeRef.current)radarConeRef.current.visible=latest.isSimulated?state.coverage:latest.showRadar;
      if(radarWaveRef.current)radarWaveRef.current.visible=latest.isSimulated&&state.coverage;
      if (radarWaveRef.current && latest.isSimulated && state.coverage) {
        waveScale=1+(frame.time*.65)%10;
        radarWaveRef.current.scale.set(waveScale, waveScale, 1);
        (radarWaveRef.current.material as THREE.MeshBasicMaterial).opacity = Math.max(.16, .36 - waveScale * .016);
      }
      const bounds=renderer.domElement.getBoundingClientRect();
      for(const fixture of fixtures){
        const annotation=annotations.get(fixture.kind)!;
        annotation.sprite.position.copy(fixture.position);
        if(bounds.width<480){
          const point=fixture.position.clone().project(camera);
          point.x=Math.max(-0.6,Math.min(0.6,point.x));
          annotation.sprite.position.copy(point.unproject(camera));
        }
        const positions=annotation.line.geometry.attributes.position as THREE.BufferAttribute;
        positions.setXYZ(0,annotation.anchor.x,annotation.anchor.y,annotation.anchor.z);
        positions.setXYZ(1,annotation.sprite.position.x,annotation.sprite.position.y,annotation.sprite.position.z);
        positions.needsUpdate=true;
      }
      const reserved:LabelRect[]=Array.from(container.parentElement!.querySelectorAll<HTMLElement>('[data-scene-reserved]')).map((element,index)=>{
        const rect=element.getBoundingClientRect();return {id:'ui:'+index,x:rect.left-bounds.left,y:rect.top-bounds.top,width:rect.width,height:rect.height};
      });
      if(sensorLabelsRef.current?.visible)for(const [kind,annotation] of annotations){
        if(!annotation.sprite.visible)continue;
        const point=annotation.sprite.position.clone().project(camera);
        const view=annotation.sprite.position.clone().applyMatrix4(camera.matrixWorldInverse);
        const factor=bounds.height/(2*Math.max(.1,-view.z)*Math.tan(THREE.MathUtils.degToRad(camera.fov/2)));
        reserved.push({id:'sensor:'+kind,x:(point.x+1)/2*bounds.width-annotation.sprite.scale.x*factor/2,y:(1-point.y)/2*bounds.height-annotation.sprite.scale.y*factor/2,width:annotation.sprite.scale.x*factor,height:annotation.sprite.scale.y*factor});
      }
      trackingLayer.layoutLabels(camera,bounds.width,bounds.height,reserved,!sensorLabelsRef.current?.visible);
      renderer.info.reset();
      renderer.render(scene, camera);
      if(trackingLayer.stats.visible){
        renderer.autoClear=false;renderer.clearDepth();renderer.render(trackingScene,camera);renderer.autoClear=true;
      }
      if(time-lastDiagnostics>=180||!simulatedMotion){
        const stats=trackingLayer.stats;
        container.dataset.tracking=JSON.stringify({...stats,sourceMode:frame.sourceMode,time:frame.time,
          selectedId:state.selectedId,sensorSignals,visualRisk,riskAccent:accent.getHexString(),radarAccent:(radarWaveRef.current?.material as THREE.MeshBasicMaterial)?.color.getHexString(),ambientColor:ambientLight.color.getHexString(),sosDeviceEmission:(sosBoxRef.current?.material as THREE.MeshStandardMaterial)?.emissiveIntensity||0,
          acousticEmission:(acousticStatusRef.current?.material as THREE.MeshStandardMaterial)?.emissiveIntensity||0,
          testKind:state.test?.kind||null,testSource:state.test?.result.source||null,incidentId:state.test?.result.incidentId||state.visual.incidentId||null,notification:state.test?.result.notification||null,highlightedSensors,pulsePhase:testPulse?pulsePhase:null,
          sosIllustrative:!!frame.sosIllustrative,sosGesture:frame.sosGesture||0,playbackStatus:state.playbackStatus,scenarioVisualRisk:state.visual.risk,incidentStatus:state.visual.incidentStatus||null,visualEpoch:state.visual.epoch,radarAvailability:latest.showRadar?'Active':latest.observation?'Missing':'Disconnected',
          floorColor:floorMat.color.getHexString(),coverageColor:coverageMat.color.getHexString(),coverageOpacity:coverageMat.opacity,coneColor:coneMat.color.getHexString(),coneOpacity:coneMat.opacity,radarHaloColor:sensorHalos.get('radar')!.material.color.getHexString(),
          sensorHaloOpacity:Object.fromEntries([...sensorHalos].map(([kind,halo])=>[kind,halo.visible?halo.material.opacity:0])),
          frameTimestamp:latest.isSimulated?capture.observation.timestamp:latest.observation?.timestamp||null,reservedLabelRects:reserved,radarCenter:radarGroup.position.toArray(),scanCenter:radarWave.getWorldPosition(new THREE.Vector3()).toArray(),coverage:latest.isSimulated&&state.coverage,coveragePhase:waveScale,
          drawCalls:renderer.info.render.calls,triangles:renderer.info.render.triangles,
          cpuFrameMs:performance.now()-cpuStarted,
          geometries:renderer.info.memory.geometries,textures:renderer.info.memory.textures,
          trackPixels:stats.positions.map(p=>{const point=new THREE.Vector3(p.x,p.z,p.y).project(camera);return {id:p.id,x:(point.x+1)/2*bounds.width,y:(1-point.y)/2*bounds.height};})});
        if(latest.isSimulated&&!latest.trackingPreview)container.dataset.normalizedObservation=JSON.stringify(capture.observation);
        else delete container.dataset.normalizedObservation;
        container.parentElement!.dataset.positionedOccupants=String(stats.active);
        container.parentElement!.dataset.trackingPreview=latest.isSimulated?'SIMULATION':'off';
        lastDiagnostics=time;
      }
      container.dataset.fixturePixels=JSON.stringify(Object.fromEntries(fixtures.map(f=>{
        const point=annotations.get(f.kind)!.sprite.position.clone().project(camera);
        return [f.kind,{x:(point.x+1)/2*bounds.width,y:(1-point.y)/2*bounds.height}];
      })));

      container.dataset.renderFrameTime=String(frame.time);
      container.dataset.renderFrameTimestamp=latest.isSimulated?capture.observation.timestamp:latest.observation?.timestamp||'';
      container.dataset.renderCount = String(Number(container.dataset.renderCount || 0) + 1);
      dirty = false;
      lastRender = time;
      if ((simulatedMotion||testPulse||trackingLayer.needsAnimation||(!latest.isSimulated&&riskTransition.active))&&!animationFrameId) animationFrameId = requestAnimationFrame(animate);
    }
    const visibilityChange=()=>{if(document.hidden)playback.pause();else invalidate();};
    document.addEventListener('visibilitychange', visibilityChange);
    const domEl = renderer.domElement;

    // Resize Handler
    const handleResize = () => {
      if (!container || !rendererRef.current || !cameraRef.current) return;
      const w = Math.max(1, container.clientWidth);
      const h = Math.max(1, container.clientHeight);
      cameraRef.current.aspect = w / h;
      cameraRef.current.updateProjectionMatrix();
      rendererRef.current.setSize(w, h);
      invalidate();
    };
    window.addEventListener('resize', handleResize);
    const resizeObserver = new ResizeObserver(handleResize);
    resizeObserver.observe(container);

    return () => {
      cancelAnimationFrame(animationFrameId);
      document.removeEventListener('visibilitychange', visibilityChange);
      unsubscribePlayback();trackingLayer.dispose();trackingLayerRef.current=null;
      renderer.domElement.removeEventListener('pointerdown',pointerDown);
      renderer.domElement.removeEventListener('pointerup',pointerUp);
      controls.removeEventListener('change', stampCamera);
      controls.dispose();
      controlsRef.current = null;
      invalidateRef.current = () => {};
      window.removeEventListener('resize', handleResize);
      resizeObserver.disconnect();
      scene.traverse(object => {
        const mesh = object as THREE.Mesh;
        mesh.geometry?.dispose();
        const materials = Array.isArray(mesh.material) ? mesh.material : [mesh.material];
        materials.forEach(material => {
          if(material && 'map' in material)(material as THREE.MeshBasicMaterial).map?.dispose();
          material?.dispose();
        });
      });
      dirLight.shadow.dispose();
      renderer.dispose();
      domEl.remove();
    };
  }, []);

  useEffect(()=>{if((!isSimulated||trackingPreview)&&playback.getSnapshot().playing)playback.pause();invalidateRef.current();},[isSimulated,observation,trackingPreview,playback]);

  useEffect(()=>{
    if(sensorLabelsRef.current){
      sensorLabelsRef.current.visible=showSensorLabels;
      for(const child of sensorLabelsRef.current.children)child.visible=child.userData.sensorKind===(selectedFixture||'radar');
    }
    invalidateRef.current();
  },[showSensorLabels,selectedFixture]);

  useEffect(()=>{invalidateRef.current();},[level,hasVisualData]);

  useEffect(() => {
    // Class-only radar output cannot locate a person on the room floor.
    if (avatar1Ref.current) avatar1Ref.current.visible = false;
    if (avatar2Ref.current) avatar2Ref.current.visible = false;
    if (distanceLineRef.current) distanceLineRef.current.visible = false;
    if (radarConeRef.current) radarConeRef.current.visible = showRadar;
    if (radarWaveRef.current) radarWaveRef.current.visible = isSimulated && showRadar;
    if (acousticStatusRef.current) {
      const material = acousticStatusRef.current.material as THREE.MeshStandardMaterial;
      material.color.setHex(acousticActive ? 0xF59E0B : 0x64748B);
      material.emissive.setHex(acousticActive ? 0x78350F : 0x000000);
      material.emissiveIntensity=acousticActive ? .6 : 0;
    }
    if (sosBoxRef.current) {
      const material = sosBoxRef.current.material as THREE.MeshStandardMaterial;
      material.emissive.setHex(sosActive ? 0xEF4444 : 0x000000);
      material.emissiveIntensity = sosActive ? 1 : 0;
    }
    invalidateRef.current();
  }, [showPresence, showRadar, isSimulated, occupants, sosActive, fallDetected, acousticActive, trackingPreview]);

  // Update Avatar Poses and Distance line based on Props & Scenario State
  useEffect(() => {
    if (!avatar1Ref.current || !avatar2Ref.current) return;

    const av1 = avatar1Ref.current;
    const av2 = avatar2Ref.current;

    if (fallDetected) {
      // Scenario 4, 7, 8: Fall event -> Person 1 collapses to floor
      av1.rotation.x = Math.PI / 2;
      av1.rotation.z = 0.3;
      av1.position.set(-0.8, 0.25, 0);

      // Person 2 standing in proximity
      av2.rotation.x = 0;
      av2.rotation.z = 0;
      av2.position.set(0.2, 0, 0.2);
    } else if (interpersonalDistance && interpersonalDistance < 0.8) {
      // Close proximity
      av1.rotation.x = 0;
      av1.rotation.z = 0;
      av1.position.set(-0.3, 0, 0);

      av2.rotation.x = 0;
      av2.rotation.z = 0;
      av2.position.set(0.3, 0, 0);
    } else {
      // Normal presence
      av1.rotation.x = 0;
      av1.rotation.z = 0;
      av1.position.set(-1.2, 0, -0.4);

      av2.rotation.x = 0;
      av2.rotation.z = 0;
      av2.position.set(1.2, 0, 0.4);
    }

    // Update Distance Line
    if (distanceLineRef.current) {
      const pos1 = av1.position.clone().add(new THREE.Vector3(0, 0.8, 0));
      const pos2 = av2.position.clone().add(new THREE.Vector3(0, 0.8, 0));
      distanceLineRef.current.geometry.setFromPoints([pos1, pos2]);
      distanceLineRef.current.computeLineDistances();
    }
    invalidateRef.current();
  }, [fallDetected, interpersonalDistance, scenarioId]);

  const zoom = (factor: number) => {
    const controls = controlsRef.current;
    const camera = cameraRef.current;
    if (!controls || !camera) return;
    const offset = camera.position.clone().sub(controls.target);
    const distance = Math.max(6, Math.min(20, offset.length() * factor));
    camera.position.copy(controls.target).add(offset.setLength(distance));
    controls.update();
    invalidateRef.current();
  };
  const handleZoomIn = () => zoom(0.85);
  const handleZoomOut = () => zoom(1 / 0.85);
  const handleReset = () => { controlsRef.current?.reset(); invalidateRef.current(); };

  return (
    <div className="space-y-2">
      <div className="flex flex-wrap items-center justify-between gap-2 px-1">
        <h2 className="text-xs font-bold text-slate-800">Toilet digital twin</h2>
        {sceneTest&&<span data-testid="scene-test-source" className="text-[10px] font-semibold text-amber-700">{sceneTest.result.source||'TEST · running'}{sceneTest.result.detected?` · ${sceneTest.result.detected}`:''}</span>}
        <div data-testid="private-sensor-legend" className="flex items-center gap-1 text-[10px]">
          {(['radar','acoustic','sos'] as const).map(kind=><button key={kind} aria-pressed={selectedFixture===kind} aria-label={`Inspect ${kind} sensor`} title={kind==='radar'?'Schematic radar coverage':kind==='acoustic'?'Non-speech acoustic events':'Direct help request'} onClick={()=>setSelectedFixture(selectedFixture===kind?null:kind)} className={`rounded-full px-2.5 py-1 font-semibold transition-colors ${selectedFixture===kind?'bg-blue-100 text-blue-800':'bg-white text-slate-500 hover:bg-slate-100'}`}>{kind==='sos'?'SOS':kind==='radar'?'Radar':'Acoustic'}<span className={`ml-1.5 inline-block h-1 w-1 rounded-full ${(kind==='radar'?showRadar:kind==='acoustic'?acousticActive:sosActive)?'bg-teal-500':'bg-slate-300'}`}/></button>)}
        </div>
      </div>
      {selectedFixture&&<p data-testid="private-fixture-detail" className="px-1 text-[11px] text-slate-500">{selectedFixture==='radar'?(fallDetected?'Radar · possible fall':isSimulated?'Radar · synthetic tracks':radarObserved?'Radar · observation':'Radar · unavailable'):selectedFixture==='acoustic'?`Acoustic · ${acousticEvent||'no event'}`:sosActive?'SOS · active':'SOS · inactive'}</p>}
    <div data-testid="private-twin-scene" data-presence-indicated={showPresence} data-positioned-occupants="0" data-tracking-preview={isSimulated?'SIMULATION':'off'} data-measured-positions="unavailable" data-sensor-labels={showSensorLabels} data-selected-fixture={selectedFixture||''} data-radar-observed={radarObserved} data-acoustic-active={acousticActive} data-fall-active={fallDetected} data-animation={isSimulated ? 'illustrative-simulation' : 'static-observation'} data-sos-active={sosActive} data-visual-risk={level} data-processing-mode={isSimulated ? 'simulation' : processingLabel} className="relative w-full h-[520px] min-h-[420px] rounded-2xl overflow-hidden bg-[#F8FAFC] shadow-sm select-none">
      {/* 3D Canvas Mounting Node */}
      <div ref={mountRef} data-testid="private-three-renderer" className="relative w-full h-full cursor-grab active:cursor-grabbing" />

      <span data-testid="scene-visual-risk" className="sr-only">{hasVisualData?level:'No data'}</span>
      <div data-scene-reserved className="absolute bottom-3 right-3 flex items-center gap-1 bg-white/90 backdrop-blur-md p-1 rounded-xl border border-[#E2E8F0] shadow-sm z-10">
        <button title="Toggle sensor labels" aria-pressed={showSensorLabels} onClick={()=>setShowSensorLabels(value=>!value)} className="p-1.5 hover:bg-slate-100 rounded-lg text-slate-700"><Radio className="w-3.5 h-3.5"/></button>
        <button
          onClick={handleZoomIn}
          className="p-1.5 hover:bg-slate-100 rounded-lg text-slate-700 cursor-pointer"
          title="Zoom In"
        >
          <ZoomIn className="w-3.5 h-3.5" />
        </button>
        <button
          onClick={handleZoomOut}
          className="p-1.5 hover:bg-slate-100 rounded-lg text-slate-700 cursor-pointer"
          title="Zoom Out"
        >
          <ZoomOut className="w-3.5 h-3.5" />
        </button>
        <button
          onClick={handleReset}
          className="p-1.5 hover:bg-slate-100 rounded-lg text-slate-700 cursor-pointer"
          title="Reset Orbit View"
        >
          <RotateCcw className="w-3.5 h-3.5" />
        </button>
      </div>

      {/* Hint for dragging */}
      <div data-scene-reserved className="absolute bottom-3.5 left-4 text-[10px] text-slate-600 font-medium pointer-events-none">
        Drag to orbit · Scroll to zoom
      </div>
    </div>
    {isSimulated&&trackingPreview&&<p className="text-xs text-amber-800">Legacy isolated SIMULATION preview active. Close it below to use the interactive tracking playback.</p>}
    </div>
  );
};
