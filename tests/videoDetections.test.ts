import test from 'node:test';
import assert from 'node:assert/strict';
import {playbackPoseFrame,visiblePoint,supportedFall,fightClassifierScore,supportedFightParticipant} from '../dashboard/src/lib/videoDetections.ts';
const result={annotation_alignment:{fps:10},pose_frames:[{frame_index:0,time_sec:0,persons:[]},{frame_index:1,time_sec:.1,persons:[]},{frame_index:3,time_sec:.3,persons:[]}]};
test('decoded timestamps select the actual frame and handle seeks backward',()=>{
 assert.equal(playbackPoseFrame(result,.15)?.frame_index,1);
 assert.equal(playbackPoseFrame(result,.31)?.frame_index,3);
 assert.equal(playbackPoseFrame(result,.02)?.frame_index,0);
});
test('missing, invalid and expired data never stretch old detections',()=>{
 for(const t of [-1,NaN,.25,.5])assert.equal(playbackPoseFrame(result,t),null);
 assert.equal(playbackPoseFrame(null,.1),null);
 assert.equal(playbackPoseFrame({...result,annotation_alignment:{fps:0}},.1),null);
});
test('only confident finite keypoints form a visible skeleton',()=>{
 assert.equal(visiblePoint({x:1,y:2,confidence:.5}),true);
 for(const point of [undefined,{x:1,y:2,confidence:null},{x:1,y:2,confidence:.1},{x:NaN,y:2,confidence:1}])assert.equal(visiblePoint(point),false);
});

test('red fall requires supported tracked binary transition, never legacy flags',()=>{
 const p:any={fall_candidate:true,fall_rule_active:true,fall_state:'POSSIBLE FALL',track_id:1,track_age:8,tracking_method:'conservative_iou_v1'};
 assert.equal(supportedFall(p),true);
 for(const delta of [{track_id:undefined},{track_age:1},{tracking_method:undefined},{fall_state:'FALL CANDIDATE'},{fall_rule_active:false}])assert.equal(supportedFall({...p,...delta}),false);
});

test('small decoder quantization near a genuine frame boundary is tolerated',()=>{
 assert.equal(playbackPoseFrame(result,.0999)?.frame_index,1);
 assert.equal(playbackPoseFrame(result,.2999)?.frame_index,3);
 assert.equal(playbackPoseFrame(result,.25),null);
 assert.equal(playbackPoseFrame(result,.405),null);
});
test('verified fight score alias is finite numeric and never fabricates zero',()=>{
 assert.equal(fightClassifierScore({score:.8,violence_score:.9}),.8);
 assert.equal(fightClassifierScore({violence_score:.9}),.9);
 for(const value of [undefined,{}, {score:NaN},{score:'0.9'},{score:2}])assert.equal(fightClassifierScore(value),null);
});

test('participant red requires separate positive interaction provenance and score',()=>{
 const result:any={participant_heuristic:{enabled:true,version:'pose-interaction-v1'},model_results:[{model_version:'v3',candidate_detected:true,score:.9}]};
 const p:any={fight_participant:true,participant_score:.65,interaction_track_id:1,participant_evidence:{heuristic_version:'pose-interaction-v1',pair_track_ids:[1,2],interaction_hits:4,reciprocal_hits:{'1':2,'2':2}}};
 assert.equal(supportedFightParticipant(p,result),true);
 for(const change of [{participant_score:null},{participant_score:NaN},{participant_evidence:undefined},{interaction_track_id:9},{fight_participant:false}])assert.equal(supportedFightParticipant({...p,...change},result),false);
 assert.equal(supportedFightParticipant(p,{...result,participant_heuristic:undefined}),false);
 assert.equal(supportedFightParticipant(p,{...result,model_results:[{model_version:'v3',candidate_detected:false,score:.1}]}),false);
});
