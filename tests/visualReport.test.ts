import test from 'node:test';
import assert from 'node:assert/strict';
import {buildVisualReport,visualReportPdf,visualReportHtml,ReportSnapshot} from '../dashboard/src/lib/visualReport.ts';
import {initialAnalyticsFilters} from '../dashboard/src/lib/incidentAnalytics.ts';
const snapshot:ReportSnapshot={records:[],zones:[],filters:initialAnalyticsFilters,snapshotAt:'2026-10-29T00:00:00Z',generatedAt:'2026-10-29T00:00:00Z',stale:false,evidence:[]};
test('empty selection says No data and both renderers consume the same A4 pages',()=>{
 const r=buildVisualReport(snapshot),pdf=visualReportPdf(r),html=visualReportHtml(r);
 assert.equal(pdf.getNumberOfPages(),r.pages.length);
 assert.equal((html.match(/class="report-sheet"/g)||[]).length,r.pages.length);
 assert.ok(html.includes('No data'));assert.ok(html.includes('width:210mm;height:297mm'));
 assert.ok(!html.includes('<button'));assert.ok(!html.includes('<aside'));
});
test('private and unknown-zone images never enter either output',()=>{
 for(const zoneType of ['PRIVATE',undefined]){
  const r=buildVisualReport({...snapshot,records:[{id:'private',zone_id:'private',zone_type:zoneType,status:'NEW',level:'HIGH',evidence:[]}],zones:[{id:'private',name:'Private',zone_type:zoneType}],evidence:[{incidentId:'private',zoneId:'private',label:'SOS',mode:'Simulation',note:'no media',image:'data:image/jpeg;base64,SECRET_PRIVATE_IMAGE'}]});
  assert.equal(r.pages.flat().filter(s=>s.kind==='image').length,0);
  assert.ok(!visualReportHtml(r).includes('SECRET_PRIVATE_IMAGE'));assert.ok(!visualReportPdf(r).output().includes('SECRET_PRIVATE_IMAGE'));
 }
});
test('large datasets paginate without clipping primitives or omitting incident rows',()=>{
 const records=Array.from({length:90},(_,i)=>({id:'incident-'+i,zone_id:'zone'+i,zone_type:'OPEN_HIDDEN',created_at:'2026-10-29T10:00:00Z',status:'NEW',level:'OBSERVE',evidence:[{type:'fall'}],processing_mode:'recorded_sensor_replay',review_status:'pending_human_review'}));
 const r=buildVisualReport({...snapshot,records});
 assert.ok(r.pages.length>8);
 const labels=r.pages.flat().filter(s=>s.kind==='text').map(s=>s.value);
 for(const shape of r.pages.flat()){
  if('x' in shape)assert.ok(shape.x>=0&&shape.x<=210);
  if('y' in shape)assert.ok(shape.y>=0&&shape.y<=297);
  if(shape.kind==='rect'||shape.kind==='image'){assert.ok(shape.x+shape.w<=210.01);assert.ok(shape.y+shape.h<=297.01);}
 }
 assert.equal(labels.filter(s=>s.includes('#incident')).length,90);
 assert.equal(visualReportPdf(r).getNumberOfPages(),r.pages.length);
});
