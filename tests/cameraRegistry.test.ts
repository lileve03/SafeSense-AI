import test from 'node:test';
import assert from 'node:assert/strict';
import {registerCameras,canonicalCameraId,sameCamera} from '../dashboard/src/lib/cameraRegistry.ts';
test('only unambiguous identities from shared registry match',()=>{
 registerCameras([{camera_id:'CAM_ENTRANCE',camera_name:'School Entrance',aliases:['Entrance camera']},{camera_id:'CAM_HALL',camera_name:'School Hall'}]);
 for(const name of ['CAM_ENTRANCE',' cam-entrance ','School Entrance','Entrance camera'])assert.equal(canonicalCameraId(name),'CAM_ENTRANCE');
 assert.equal(sameCamera('cam hall','CAM_HALL'),true);
 for(const name of [null,'','UNKNOWN','ZONE_ENTRANCE','adl_01'])assert.equal(canonicalCameraId(name),null);
 assert.equal(sameCamera('CAM_HALL','CAM_ENTRANCE'),false);
 assert.equal(sameCamera(undefined,undefined),false);
 registerCameras([{camera_id:'A',aliases:['shared']},{camera_id:'B',aliases:['shared']}]);
 assert.equal(canonicalCameraId('shared'),null);
});
