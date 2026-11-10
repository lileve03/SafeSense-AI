import test from 'node:test';
import assert from 'node:assert/strict';
import {filterIncidents,summarizeIncidents,durationLabel,initialAnalyticsFilters,IncidentRecord} from '../dashboard/src/lib/incidentAnalytics.ts';
const records:IncidentRecord[]=[
{id:'a',zone_id:'corridor',status:'RESOLVED',level:'OBSERVE',source:'vision',processing_mode:'real_model',created_at:'2026-10-20T12:00:00Z',acknowledged_at:'2026-10-20T12:00:10Z',resolved_at:'2026-10-20T12:01:00Z',evidence:[{type:'possible_conflict'},{type:'possible_conflict'}]},
{id:'b',zone_id:'private',status:'NEW',level:'HIGH',source:'radar',processing_mode:'recorded_sensor_replay',created_at:'2026-10-21T12:00:00Z',evidence:[{type:'fall'}]},
{id:'c',zone_id:'private',status:'FALSE_ALARM',level:'CRITICAL',source:'simulation',processing_mode:'simulation',created_at:'2026-10-22T12:00:00Z',resolved_at:'2026-10-22T12:00:20Z',evidence:[{type:'sos'}]},
{id:'d',zone_id:'canteen',status:'ACKNOWLEDGED',level:'OBSERVE',source:'yamnet',processing_mode:'real_model',created_at:'2026-10-23T12:00:00Z',acknowledged_at:'2026-10-23T11:59:00Z',evidence:[{type:'scream'},{type:'impact'}]},
{id:'e',zone_id:'corridor',status:'NEW',level:'OBSERVE',source:'vision',processing_mode:'real_model',created_at:'invalid',evidence:[]},
];
const filtered=(extra:object)=>filterIncidents(records,{...initialAnalyticsFilters,...extra},Date.parse('2026-10-23T15:00:00Z'));
test('Modes remain distinct, combined filters select actual intersection',()=>{
 assert.deepEqual(filtered({mode:'real_model'}).map(r=>r.id),['a','d','e']);
 assert.deepEqual(filtered({mode:'recorded_sensor_replay',zone:'private',source:'radar'}).map(r=>r.id),['b']);
 assert.equal(filtered({mode:'simulation',source:'vision'}).length,0);
});
test('Acknowledgement timestamps and closed status are separate',()=>{
 assert.deepEqual(filtered({ack:'acknowledged'}).map(r=>r.id),['a','d']);
 const s=summarizeIncidents(records);assert.equal(s.open,3);assert.equal(s.awaitingAck,2);assert.equal(s.acknowledged,2);assert.equal(s.closed,2);
});
test('Only valid nonnegative timestamp pairs contribute measured times',()=>{
 const s=summarizeIncidents(records);assert.equal(s.meanAck,10);assert.equal(s.ackSamples,1);assert.equal(s.meanClosure,40);assert.equal(s.closureSamples,2);
});
test('False alarm denominator is reviewed closed incidents',()=>{
 const s=summarizeIncidents(records);assert.equal(s.falseAlarmRate,50);assert.equal(summarizeIncidents(filtered({status:'NEW'})).falseAlarmRate,null);
});
test('Multi-type observations count each incident once per type',()=>{
 const s=summarizeIncidents(records);assert.equal(s.types.find(t=>t.key==='possible_conflict')?.count,1);assert.equal(s.types.reduce((n,t)=>n+t.count,0),6);
});
test('Source classification uses recorded source, not fall/pose text matching',()=>{
 const s=summarizeIncidents([{...records[0],evidence:[{type:'fall'}]}]);assert.deepEqual(s.sources,[{key:'vision',count:1}]);
});
test('UTC date filtering is inclusive and excludes invalid dates only for date scopes',()=>{
 assert.deepEqual(filtered({range:'custom',from:'2026-10-21',to:'2026-10-22'}).map(r=>r.id),['b','c']);
 assert.equal(filtered({range:'all'}).length,5);assert.equal(filtered({range:'7days'}).length,4);
 const offset={...records[0],created_at:'2026-10-23T00:30:00+08:00'};
 assert.equal(filterIncidents([offset],{...initialAnalyticsFilters,range:'today'},Date.parse('2026-10-23T12:00:00Z')).length,0);
});
test('Stable IDs deduplicate rows without merging equal-score or same-zone incidents',()=>{
 assert.equal(filterIncidents([...records,records[0]],initialAnalyticsFilters).length,5);
 assert.equal(filtered({source:'vision',zone:'corridor'}).length,2);
});
test('No invented trend points; unparseable creation dates are explicit',()=>{
 const s=summarizeIncidents(records);assert.equal(s.trend.length,4);assert.equal(s.undated,1);assert.equal(s.trend.reduce((n,r)=>n+r.count,0),4);
});
test('Empty records and zero-second measured response are distinct',()=>{
 const empty=summarizeIncidents([]);assert.equal(empty.total,0);assert.equal(empty.meanAck,null);assert.deepEqual(empty.severity,[]);assert.equal(durationLabel(null),'Not measured');
 const s=summarizeIncidents([{...records[0],acknowledged_at:records[0].created_at}]);assert.equal(s.meanAck,0);assert.equal(durationLabel(s.meanAck),'0.0s');
});
