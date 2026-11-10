import test from 'node:test';
import assert from 'node:assert/strict';
import {TrackingPlayback,testSensorState} from '../dashboard/src/components/private-area/trackingPlayback';

test('Acoustic test takes ownership, removes synthetic occupancy and never starts human motion',()=>{
  const playback=new TrackingPlayback();playback.setScenario('fall_impact');playback.seek(7);playback.start();
  playback.beginTest('acoustic','one');
  assert.equal(playback.getSnapshot().playing,false);assert.equal(playback.frame().tracks.length,0);
  playback.updateTest('acoustic','one',{status:'Passed',source:'RECORDED ACOUSTIC TEST',detected:'scream',risk:'OBSERVE'});
  assert.equal(playback.getSnapshot().test?.sourceMode,'RECORDED_REPLAY');
  assert.equal(testSensorState(playback.getSnapshot().test,0).acoustic,'scream');
});
test('Fusion uses the existing fall path and holds the impact pose instead of looping',()=>{
  const playback=new TrackingPlayback();playback.beginTest('fusion','one');
  assert.equal(playback.getSnapshot().scenario,'fall_impact');assert.equal(playback.getSnapshot().playing,true);
  const before=playback.frame().tracks[0].position.z;
  playback.seek(9.3);const after=playback.frame().tracks[0].position.z;
  assert.ok(after<before);assert.equal(testSensorState(playback.getSnapshot().test,9.3).acoustic,'impact');
  playback.start();playback.tick(performance.now()+10000,true);
  assert.equal(playback.getSnapshot().time,12);assert.equal(playback.getSnapshot().playing,false);
});
test('SOS supplies one illustrative track even from an empty frame; reset preserves result history',()=>{
  const playback=new TrackingPlayback();playback.beginTest('fusion','one');playback.seek(10);
  playback.setScenario('normal');playback.seek(0);assert.equal(playback.frame().tracks.length,0);
  playback.beginTest('sos','one');assert.equal(playback.frame().tracks.length,1);assert.equal(playback.frame().sosIllustrative,true);
  const start=playback.frame().tracks[0].position;playback.seek(5);assert.notDeepEqual(playback.frame().tracks[0].position,start);assert.ok(playback.frame().sosGesture!>0);
  playback.seek(40);assert.equal(playback.frame().tracks.length,1);
  assert.equal(testSensorState(playback.getSnapshot().test,5).sos,true);
  const result={status:'Incident Created' as const,source:'SIMULATED SOS TEST',risk:'CRITICAL' as const,incidentId:'saved'};
  playback.updateTest('sos','one',result);playback.resetTest();
  assert.equal(playback.getSnapshot().test,null);assert.equal(playback.frame().tracks.length,0);
  assert.equal(playback.getSnapshot().playing,false);assert.equal(result.incidentId,'saved');
});
test('Historical polls and other runs cannot take visual ownership',()=>{
  const playback=new TrackingPlayback();
  const result={status:'Passed' as const,risk:'HIGH' as const};
  playback.updateTest('fusion','old',result);assert.equal(playback.getSnapshot().test,null);
  playback.beginTest('acoustic','current');playback.updateTest('fusion','old',result);
  assert.equal(playback.getSnapshot().test?.kind,'acoustic');assert.equal(playback.getSnapshot().test?.result.risk,undefined);
  playback.updateTest('acoustic','current',{status:'Running',risk:'HIGH',detected:'scream',incidentId:'previous'});
  assert.equal(playback.getSnapshot().test?.result.risk,undefined);assert.equal(playback.getSnapshot().test?.result.detected,undefined);
});
