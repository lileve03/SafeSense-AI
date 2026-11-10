import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {importedFrameAt,SyntheticFrame} from '../dashboard/src/lib/importedReplay.ts';
const frames:SyntheticFrame[]=JSON.parse(readFileSync(new URL('../backend/data/imported_phase2/test_twin.json',import.meta.url),'utf8'));
test('actual imported timestamps select supplied frames through seeks without interpolation',()=>{
 assert.equal(importedFrameAt(frames,4.95),frames[49]);
 assert.equal(importedFrameAt(frames,12),frames[120]);
 assert.equal(importedFrameAt(frames,0),frames[0]);
 assert.equal(importedFrameAt(frames,1),frames[10]);
 for(const value of [-1,NaN,12.1])assert.equal(importedFrameAt(frames,value),null);
 assert.equal(importedFrameAt([],0),null);
});
