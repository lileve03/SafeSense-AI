import test from 'node:test';
import assert from 'node:assert/strict';
import {isAnalyticsLocation,analyticsCanonicalUrl,operatorBaseUrl} from '../dashboard/src/lib/analyticsReportsRoute.ts';
import {filterIncidents,initialAnalyticsFilters} from '../dashboard/src/lib/incidentAnalytics.ts';
test('old hash and path routes resolve to the combined page and retain query parameters',()=>{
 for(const alias of ['analytics','reports','analytics-reports']){
  for(const location of [{pathname:'/',hash:'#/'+alias,search:'?tenant=school'},{pathname:'/'+alias,hash:'',search:'?tenant=school'}]){
   assert.equal(isAnalyticsLocation(location),true);
   assert.ok(analyticsCanonicalUrl(location).endsWith('?tenant=school#/analytics-reports'));
  }
 }
 assert.equal(isAnalyticsLocation({pathname:'/reports',hash:'#/developer/testing'}),false);
 assert.equal(isAnalyticsLocation({pathname:'/',hash:''}),false);
 assert.equal(operatorBaseUrl({pathname:'/analytics-reports',search:'?tenant=school'}),'/?tenant=school');
});
test('event filters use evidence types once per incident and combine with all existing filters',()=>{
 const a={id:'a',zone_id:'public',status:'NEW',level:'HIGH',processing_mode:'real_model',evidence:[{type:'fall'},{type:'fall'},{type:'sos'}]};
 const b={...a,id:'b',zone_id:'private',processing_mode:'recorded_sensor_replay',evidence:[]};
 const records=[a,b];
 assert.deepEqual(filterIncidents(records,{...initialAnalyticsFilters,eventType:'fall'}).map(r=>r.id),['a']);
 assert.deepEqual(filterIncidents(records,{...initialAnalyticsFilters,eventType:'fall',zone:'private'}),[]);
 assert.deepEqual(filterIncidents(records,{...initialAnalyticsFilters,eventType:'Not recorded'}).map(r=>r.id),['b']);
 assert.equal(filterIncidents(records,{...initialAnalyticsFilters,eventType:'all'}).length,2);
});
