import test from 'node:test';
import assert from 'node:assert/strict';
import {TrackingPlayback} from '../dashboard/src/components/private-area/trackingPlayback';

function fall(){const p=new TrackingPlayback();p.setScenario('fall_impact');p.bindGuidedRun('current');return p;}
test('Fall risk and pose survive completion, pause/resume and seek to the final frame',()=>{
  const p=fall();p.seek(10);p.updateGuidedAssessment('fall_impact','current',{level:'HIGH',reason:'Corroborated'}, {id:'incident',status:'NEW'});
  p.start();p.pause();assert.equal(p.getSnapshot().playbackStatus,'Paused');assert.equal(p.getSnapshot().visual.risk,'HIGH');
  p.start();p.tick(performance.now()+50000,true);
  assert.equal(p.getSnapshot().playbackStatus,'Completed');assert.equal(p.getSnapshot().visual.risk,'HIGH');
  assert.equal(p.frame().tracks.length,2);assert.equal(p.frame().fallProgress?.T01,1);
  p.seek(40);assert.equal(p.getSnapshot().visual.risk,'HIGH');assert.equal(p.frame().fallProgress?.T01,1);
});
test('Acknowledgement and resolution cannot override timestamp-driven simulation risk',()=>{
  const p=fall();p.seek(40);
  p.updateGuidedAssessment('fall_impact','current',{level:'HIGH',reason:'Corroborated'},{id:'current-incident',status:'ACKNOWLEDGED'});
  assert.equal(p.getSnapshot().visual.risk,'HIGH');
  p.updateGuidedAssessment('fall_impact','other',{level:'CRITICAL',reason:'Unrelated'},{id:'old',status:'RESOLVED'});
  assert.equal(p.getSnapshot().visual.risk,'HIGH');assert.equal(p.getSnapshot().visual.incidentId,'current-incident');
  p.updateGuidedAssessment('fall_impact','current',{level:'HIGH',reason:'Corroborated'},{id:'current-incident',status:'RESOLVED'});
  assert.equal(p.getSnapshot().visual.risk,'HIGH');assert.equal(p.frame().visualRisk,'HIGH');
  assert.equal(p.getSnapshot().visual.incidentStatus,'RESOLVED');
  assert.equal(p.frame().fallProgress?.T01,1); // No invented recovery movement.
});
test('Restart and scenario change reset the visual epoch without mutating incident records',()=>{
  const p=fall();p.seek(40);const epoch=p.getSnapshot().visual.epoch;
  const incident={id:'historical',status:'NEW'};
  p.updateGuidedAssessment('fall_impact','current',{level:'HIGH',reason:'Corroborated'},incident);
  p.restart();assert.notEqual(p.getSnapshot().visual.epoch,epoch);assert.equal(p.getSnapshot().visual.risk,'LOW');assert.equal(p.getSnapshot().visual.fallProgress,0);
  p.setScenario('normal');p.bindGuidedRun('normal');
  p.updateGuidedAssessment('fall_impact','current',{level:'CRITICAL',reason:'Old'},incident);
  assert.equal(p.getSnapshot().visual.risk,'LOW');assert.equal(p.getSnapshot().visual.incidentId,undefined);
  assert.deepEqual(incident,{id:'historical',status:'NEW'});
});
test('Seeking to the end before a backend assessment preserves the illustrative fall risk',()=>{
  const p=fall();p.seek(40);assert.equal(p.getSnapshot().visual.risk,'HIGH');
  assert.equal(p.getSnapshot().playbackStatus,'Completed');assert.equal(p.frame().tracks.length,2);
});

test('Resolved replay can seek backward and forward independently of backend assessment',()=>{
  const p=fall();p.updateGuidedAssessment('fall_impact','current',{level:'LOW',reason:'Historical backend result'},{id:'resolved',status:'RESOLVED'});
  p.seek(0);assert.equal(p.getSnapshot().visual.risk,'LOW');assert.equal(p.frame().fallProgress?.T01,0);
  p.seek(8.6);assert.equal(p.getSnapshot().visual.risk,'WARNING');assert.ok(p.frame().fallProgress!.T01>0&&p.frame().fallProgress!.T01<1);
  p.seek(40);assert.equal(p.getSnapshot().visual.risk,'HIGH');assert.equal(p.observation().radar_event,'fall');assert.ok(p.observation().acoustic_events?.length);
  assert.equal(p.getSnapshot().visual.assessment?.level,'LOW');assert.equal(p.getSnapshot().visual.incidentStatus,'RESOLVED');
  p.seek(0);assert.equal(p.frame().fallProgress?.T01,0);assert.equal(p.getSnapshot().visual.risk,'LOW');
});

test('Possible Fall holds red review visuals independently of OBSERVE and resolution until explicit reset',()=>{
  const p=new TrackingPlayback();p.setScenario('fall_only');p.bindGuidedRun('review');p.seek(12);
  p.updateGuidedAssessment('fall_only','review',{level:'OBSERVE',reason:'Uncorroborated fall'},{id:'review',status:'RESOLVED'});
  assert.equal(p.getSnapshot().visual.risk,'HIGH');assert.equal(p.getSnapshot().visual.assessment?.level,'OBSERVE');
  p.seek(40);assert.equal(p.getSnapshot().visual.risk,'HIGH');assert.equal(p.frame().fallProgress?.T01,1);
  p.start();p.pause();assert.equal(p.getSnapshot().visual.risk,'HIGH');
  p.seek(0);assert.equal(p.getSnapshot().visual.risk,'HIGH');assert.equal(p.frame().fallProgress?.T01,1);
  p.restart();assert.equal(p.getSnapshot().visual.risk,'LOW');assert.equal(p.frame().fallProgress?.T01,0);
  p.seek(12);p.resetTest();assert.equal(p.getSnapshot().visual.risk,'LOW');
  p.setScenario('fall_only');p.seek(12);p.setScenario('normal');assert.equal(p.getSnapshot().visual.risk,'LOW');
});
