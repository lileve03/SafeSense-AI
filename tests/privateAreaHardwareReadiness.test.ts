import test from 'node:test';
import assert from 'node:assert/strict';
import {observationFrame,simulationObservation,simulationFrame,distances,simulatedSensorState} from '../dashboard/src/components/private-area/trackingPlayback.ts';
import {notificationStateLabel} from '../dashboard/src/lib/notificationState.ts';
import type {SensorObservation} from '../dashboard/src/components/private-area/SensorObservationPanel.tsx';

const fixture=():SensorObservation=>({observation_id:'fixture',source_mode:'RECORDED_REPLAY',device_id:'TEST_ONLY',zone_id:'ZONE_TOILET_BLINDSPOT',
  timestamp:'2026-11-02T00:00:00Z',data_validity:'VALID',coordinate_frame:'zone_meters_x_right_y_forward_z_up',tracking_session_id:'session-1',sos_state:'UNKNOWN',
  tracks:[{id:'A',position:{x:0,y:0,z:.3}},{id:'B',position:{x:3,y:4,z:.3}}]});

test('valid 3D coordinates produce the exact 5m track separation',()=>{
  const frame=observationFrame(fixture());assert.equal(distances(frame.tracks)[0].meters,5);
});
test('null, absent or partial coordinates never become positions or zero distances',()=>{
  for(const tracks of [null,undefined,[{id:'A'}],[{id:'A',position:{x:1,y:2}}]]){
    const frame=observationFrame({...fixture(),tracks} as SensorObservation);assert.equal(frame.tracks.length,0);assert.deepEqual(distances(frame.tracks),[]);
  }
});
test('non-finite coordinates and ambiguous duplicate IDs are not rendered',()=>{
  assert.equal(observationFrame({...fixture(),tracks:[{id:'A',position:{x:NaN,y:0,z:0}}]}).tracks.length,0);
  assert.equal(observationFrame({...fixture(),tracks:[{id:'A',position:{x:0,y:0,z:0}},{id:'A',position:{x:1,y:0,z:0}}]}).tracks.length,0);
});
test('invalid/stale validity, uncalibrated frame and unknown timestamp hide all tracks',()=>{
  for(const patch of [{data_validity:'STALE'},{data_validity:'INVALID'},{coordinate_frame:null},{timestamp:''},{timestamp:'2026-11-02T00:00:00'}])
    assert.equal(observationFrame({...fixture(),...patch} as SensorObservation).tracks.length,0);
});
test('unverified live packets cannot render hardware tracks',()=>{
  for(const hardware_verified of [undefined,false])assert.equal(observationFrame({...fixture(),source_mode:'LIVE_HARDWARE',hardware_verified}).tracks.length,0);
  // A trusted-server verification fixture tests the future code path only.
  assert.equal(observationFrame({...fixture(),source_mode:'LIVE_HARDWARE',hardware_verified:true}).tracks.length,2);
});
test('visual stream identity isolates device, session and source mode',()=>{
  const baseline=observationFrame(fixture()).streamId;
  for(const patch of [{tracking_session_id:'session-2'},{device_id:'other'},{source_mode:'SIMULATION'}])
    assert.notEqual(observationFrame({...fixture(),...patch} as SensorObservation).streamId,baseline);
});
test('simulation emits the normalized envelope and identical anonymous coordinates',()=>{
  const observation=simulationObservation('repeated',12,'sim-session',Date.UTC(2026,10,2));
  assert.equal(observation.source_mode,'SIMULATION');assert.equal(observation.schema_version,1);
  assert.equal(observation.timestamp_basis,'CAPTURE_TIME');assert.equal(observation.timestamp,'2026-11-02T00:00:12.000Z');
  assert.deepEqual(observationFrame(observation).tracks,simulationFrame('repeated',12).tracks);
  assert.equal(observation.point_cloud,null);
});
test('all five demo paths stay continuous in position without giant frame jumps',()=>{
  for(const scenario of ['normal','proximity','repeated','fall_impact','sos'] as const){
    let previous=simulationFrame(scenario,0);
    for(let i=1;i<=4000;i++){
      const current=simulationFrame(scenario,i/100);
      for(const track of current.tracks){
        const old=previous.tracks.find(t=>t.id===track.id);
        if(old)assert.ok(Math.hypot(track.position.x-old.position.x,track.position.y-old.position.y,track.position.z-old.position.z)<.05,scenario);
      }
      previous=current;
    }
    assert.equal(previous.tracks.length,0);
  }
});
test('fall, impact and direct SOS indicators are explicitly scenario-driven',()=>{
  assert.deepEqual(simulatedSensorState('normal',12),{fall:false,impact:false,sos:false});
  assert.deepEqual(simulatedSensorState('fall_impact',10),{fall:true,impact:true,sos:false});
  assert.deepEqual(simulatedSensorState('sos',6),{fall:false,impact:false,sos:true});
});
test('Telegram labels distinguish acceptance, uncertain outcome and verified receipt',()=>{
  assert.match(notificationStateLabel('SENT'),/API accepted.*receipt unconfirmed/);
  assert.match(notificationStateLabel('API_ACCEPTED'),/receipt unconfirmed/);
  assert.match(notificationStateLabel('DELIVERY_UNKNOWN'),/unknown/);
  assert.match(notificationStateLabel('DISABLED'),/disabled/);
  assert.match(notificationStateLabel('RECEIPT_CONFIRMED'),/Receipt confirmed/);
});
