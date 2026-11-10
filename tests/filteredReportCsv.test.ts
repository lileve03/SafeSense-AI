import test from 'node:test';
import assert from 'node:assert/strict';
import {filteredIncidentsCsv,filteredCsvHeaders,exportDatasetId} from '../dashboard/src/lib/filteredReportCsv.ts';
import {buildVisualReport,visualReportPdf,visualReportHtml,ReportSnapshot} from '../dashboard/src/lib/visualReport.ts';
import {initialAnalyticsFilters,filterIncidents,IncidentRecord} from '../dashboard/src/lib/incidentAnalytics.ts';
const record:IncidentRecord={id:'full-incident-identifier',zone_id:'z',zone_type:'OPEN_HIDDEN',created_at:'2026-10-29T00:00:00Z',status:'ACKNOWLEDGED',level:'HIGH',source:'vision',processing_mode:'real_model',review_status:'under_review',assigned_staff:'=HYPERLINK("bad")',acknowledged_at:'2026-10-29T00:00:01Z',resolved_at:null,evidence:[{id:'observation',type:'fall',model_version:'yolo-pose',score:0,evidence_reference:'sha256:actual'},{id:'second',type:'fall',model_version:'rule',score:null,evidence_reference:'quote" and\nnewline'}]};
const snapshot:ReportSnapshot={records:[record],zones:[{id:'z',name:'北區, "Entrance"\nLevel 2',zone_type:'OPEN_HIDDEN'}],filters:initialAnalyticsFilters,snapshotAt:'2026-10-29T00:00:00Z',generatedAt:'2026-10-29T00:00:00Z',stale:false,evidence:[]};
function parse(csv:string){const out:string[][]=[];let row:string[]=[],value='',quoted=false;for(let i=1;i<csv.length;i++){const c=csv[i];if(c==='"'){if(quoted&&csv[i+1]==='"'){value+='"';i++;}else quoted=!quoted;}else if(c===','&&!quoted){row.push(value);value='';}else if(c==='\r'&&!quoted&&csv[i+1]==='\n'){row.push(value);out.push(row);row=[];value='';i++;}else value+=c;}return out;}
test('filtered CSV includes every supported field, UTF-8 and positional model/score pairs',()=>{
 const csv=filteredIncidentsCsv(snapshot),[header,row]=parse(csv);
 assert.equal(csv.charCodeAt(0),0xfeff);assert.deepEqual(header,filteredCsvHeaders);assert.equal(row.length,14);
 assert.equal(row[0],record.id);assert.equal(row[2],snapshot.zones[0].name);assert.equal(row[3],'fall');assert.equal(row[6],'yolo-pose; rule');assert.equal(row[7],'0; ');assert.equal(row[10],"'=HYPERLINK(\"bad\")");assert.equal(row[12],'');assert.equal(row[13],'sha256:actual; quote" and\nnewline');
});
test('all exported CSV cells reject spreadsheet formula prefixes, controls and quotes',()=>{
 for(const attack of ['=1',' +SUM(A1)','\tcmd','\ncmd','\rhello','@evil','-evil','\u0000=1','\uFEFF@evil']){
  const data=filteredIncidentsCsv({...snapshot,records:[{...record,id:attack,assigned_staff:attack}],zones:[{...snapshot.zones[0],name:attack}]});
  const row=parse(data)[1];assert.equal(row[0],"'"+attack);assert.equal(row[2],"'"+attack);assert.equal(row[10],"'"+attack);
 }
});
test('private and reclassified zones export no media references',()=>{
 for(const zoneType of ['PRIVATE',undefined]){
  const csv=filteredIncidentsCsv({...snapshot,zones:[{...snapshot.zones[0],zone_type:zoneType}]});assert.ok(!csv.includes('sha256:actual'));assert.ok(csv.includes('media excluded'));
 }
});
test('empty CSV is a header-only valid UTF-8 file; every format uses the same dataset ID',()=>{
 assert.deepEqual(parse(filteredIncidentsCsv({...snapshot,records:[]})),[filteredCsvHeaders]);
 const report=buildVisualReport(snapshot);assert.equal(report.fingerprint,exportDatasetId(snapshot));assert.ok(visualReportHtml(report).includes(report.fingerprint));
 assert.equal(filterIncidents([record],{...initialAnalyticsFilters,severity:'LOW'}).length,0);
});
test('long labels and 300 records paginate across vector and print layouts',()=>{
 const zoneName='Long zone label - '+('north corridor restricted perimeter walkway '.repeat(9));
 const data={...snapshot,zones:[{id:'z',name:zoneName,zone_type:'OPEN_HIDDEN'}],filters:{...initialAnalyticsFilters,zone:'z'},records:Array.from({length:300},(_,i)=>({...record,id:String(i).padStart(8,'0')+'-stress-record',assigned_staff:null,evidence:[{type:'fall'}]}))};
 const report=buildVisualReport(data);assert.ok(report.pages.length>10);assert.equal(visualReportPdf(report).getNumberOfPages(),report.pages.length);
 const text=report.pages.flat().filter(s=>s.kind==='text').map(s=>s.value).join('\n');for(let i=0;i<300;i++)assert.ok(text.includes('#'+String(i).padStart(8,'0')));
 for(const s of report.pages.flat()){if('y' in s)assert.ok(s.y>=0&&s.y<=297);if('x' in s)assert.ok(s.x>=0&&s.x<=210);if(s.kind==='rect'||s.kind==='image')assert.ok(s.y+s.h<=297.01);}
});

test('a single oversized incident row continues across A4 pages without dropping text',()=>{
 const zoneName='Oversized label '+('access corridor '.repeat(180));
 const report=buildVisualReport({...snapshot,zones:[{id:'z',name:zoneName,zone_type:'OPEN_HIDDEN'}]});
 const tablePages=report.pages.filter(p=>p.some(s=>s.kind==='text'&&s.value==='Incident Records'));
 assert.ok(tablePages.length>=2);
 assert.ok(tablePages.flat().some(s=>s.kind==='text'&&s.value.includes('(cont.)')));
 for(const shape of report.pages.flat()){if('y' in shape)assert.ok(shape.y<=297);if(shape.kind==='rect')assert.ok(shape.y+shape.h<=297.01);}
});
