import {jsPDF} from 'jspdf';
import {AnalyticsFilters,IncidentRecord,summarizeIncidents,durationLabel,modeLabels} from './incidentAnalytics';

export type ReportZone={id:string;name:string;zone_type?:string};
export type EvidencePreview={incidentId:string;zoneId:string;label:string;mode:string;image?:string;sourceTime?:string;note:string};
export type ReportSnapshot={records:IncidentRecord[];zones:ReportZone[];filters:AnalyticsFilters;snapshotAt:string;generatedAt:string;stale:boolean;evidence:EvidencePreview[]};
type Shape=
 |{kind:'rect';x:number;y:number;w:number;h:number;fill:string;stroke?:string}
 |{kind:'text';x:number;y:number;value:string;size:number;color:string;bold?:boolean}
 |{kind:'line';points:number[][];color:string;width:number;closed?:boolean;fill?:string}
 |{kind:'circle';x:number;y:number;r:number;fill:string}
 |{kind:'image';x:number;y:number;w:number;h:number;data:string;incidentId:string};
export type VisualReport={pages:Shape[][];snapshot:ReportSnapshot;fingerprint:string};
const navy='#10243e',blue='#2563eb',ink='#172b46',muted='#526580',border='#dce5f0',light='#f2f6fb';
const palette=['#2563eb','#0891b2','#7c3aed','#f59e0b','#10b981','#e11d48','#475569','#9333ea'];
const severity:Record<string,string>={LOW:'#059669',OBSERVE:'#ca8a04',WARNING:'#d97706',HIGH:'#ea580c',CRITICAL:'#dc2626'};
const clean=(s:unknown)=>String(s??'No data').replaceAll('_',' ').replace(/[^\x20-\x7E]/g,' ');
const events=(r:IncidentRecord)=>[...new Set((r.evidence||[]).flatMap(e=>e.type?[e.type]:[]))];
export function fingerprint(value:unknown){let hash=2166136261;for(const c of JSON.stringify(value))hash=Math.imul(hash^c.charCodeAt(0),16777619);return (hash>>>0).toString(16).padStart(8,'0');}

// One page scene is rendered as vector PDF primitives and as printable SVG.
// Neither export captures dashboard screenshots or independently recomputes its data.
export function buildVisualReport(snapshot:ReportSnapshot):VisualReport{
 const {records,zones,filters}=snapshot,stats=summarizeIncidents(records);
 const pages:Shape[][]=[];let page:Shape[]=[];
 const measure=new jsPDF({unit:'mm',format:'a4'});
 const zone=(id:string)=>zones.find(z=>z.id===id)?.name||id;
 const rect=(x:number,y:number,w:number,h:number,fill:string,stroke?:string)=>page.push({kind:'rect',x,y,w,h,fill,stroke});
 const text=(value:unknown,x:number,y:number,size=10,color=ink,bold=false)=>page.push({kind:'text',x,y,value:clean(value),size,color,bold});
 const line=(points:number[][],color=border,width=.3,closed=false,fill?:string)=>page.push({kind:'line',points,color,width,closed,fill});
 function split(value:unknown,width:number,size=9,bold=false){
  measure.setFont('helvetica',bold?'bold':'normal');measure.setFontSize(size);
  return measure.splitTextToSize(clean(value),width) as string[];
 }
 function shortened(value:unknown,width:number,size=9,bold=false){
  const full=clean(value);measure.setFont('helvetica',bold?'bold':'normal');measure.setFontSize(size);
  if(measure.getTextWidth(full)<=width)return full;
  let short=full;while(short&&measure.getTextWidth(short+'...')>width)short=short.slice(0,-1);
  return short+'...';
 }
 function wrap(value:unknown,x:number,y:number,width:number,size=9,color=ink,bold=false,maxLines=Infinity){
  const lines=split(value,width,size,bold);
  const visible=lines.slice(0,maxLines);
  if(lines.length>maxLines&&visible.length)visible[visible.length-1]=shortened(visible[visible.length-1]+'...',width,size,bold);
  visible.forEach((s,i)=>text(s,x,y+i*size*.352778*1.25,size,color,bold));
  return visible.length*size*.352778*1.25;
 }
 function newPage(title:string,cover=false){
  page=[];pages.push(page);rect(0,0,210,297,'#ffffff');rect(0,0,210,cover?49:34,navy);
  text('SAFESENSE AI',14,cover?14:12,cover?11:9,'#67e8f9',true);
  text(title,14,cover?29:23,cover?24:17,'#ffffff',true);
  if(cover)text('ANALYTICS & REPORTS  /  OPERATIONAL INTELLIGENCE',14,40,9,'#dbeafe');
 }
 function box(title:string,note:string,x:number,y:number,w:number,h:number){
  rect(x,y,w,h,'#ffffff',border);text(title,x+5,y+8,11,ink,true);wrap(note,x+5,y+14,w-10,7.6,muted);
 }
 function bars(title:string,note:string,items:{key:string;count:number}[],x:number,y:number,w:number,h:number,color?:(key:string)=>string){
  box(title,note,x,y,w,h);
  if(!items.length){text('No data',x+5,y+34,13,muted);return;}
  const top=y+23,left=x+58,right=x+w-15,max=Math.max(...items.map(r=>r.count)),available=h-29;let offset=0;
  items.forEach(r=>{const height=Math.max(7,Math.min(10,split(r.key,49,8).length)*8*.352778*1.25+2),cy=top+offset;wrap(r.key,x+5,cy+3,49,8,ink,false,10);rect(left,cy,Math.max(.3,(right-left)*r.count/max),Math.min(5,height-2),color?.(r.key)||blue);text(r.count,right+3,cy+3.5,8,ink,true);offset+=height;});
 }
 const range=filters.range==='custom'?`${filters.from||'Start'} to ${filters.to||'Present'} UTC`:({all:'All dates',today:'Today (UTC)','7days':'Last 7 days (UTC)','30days':'Last 30 days (UTC)'}[filters.range]||filters.range);
 const labels=[`Dates: ${range}`,`Zone: ${filters.zone==='all'?'All zones':zone(filters.zone)}`,`Severity: ${filters.severity==='all'?'All':filters.severity}`,`Event: ${filters.eventType&&filters.eventType!=='all'?filters.eventType:'All types'}`,`Mode: ${filters.mode==='all'?'All modes':modeLabels[filters.mode]||filters.mode}`];
 if(filters.status!=='all')labels.push(`Status: ${filters.status}`);
 if(filters.source!=='all')labels.push(`Source: ${filters.source}`);
 if(filters.ack!=='all')labels.push(`Acknowledgement: ${filters.ack}`);
 newPage('Campus Safety Report',true);
 const scopeText=labels.join('  |  '),longScope=split(scopeText,182,8.5).length>3;
 wrap(longScope?`${records.length} selected incidents | Full filter scope on following page`:scopeText,14,58,182,8.5,ink);
 text(`Snapshot: ${snapshot.snapshotAt||'Not recorded'}  |  Generated: ${snapshot.generatedAt}`,14,76,7,muted);
 if(snapshot.stale)text('LAST SUCCESSFUL SNAPSHOT - backend refresh unavailable',14,81,7,'#b45309',true);
 const kpis=[['Total Incidents',stats.total,'Saved incident IDs'],['High Risk',records.filter(r=>['HIGH','CRITICAL'].includes(r.level)).length,'High + critical'],['SOS',records.filter(r=>r.source==='sos_button'||events(r).some(t=>t.toLowerCase()==='sos')).length,'Incidents with SOS input'],['Pending Review',records.filter(r=>r.review_status==='pending_human_review').length,'Awaiting human review'],['Resolved',stats.resolved,'Resolved outcome'],['Average Response Time',stats.meanAck===null?'No data':durationLabel(stats.meanAck),`${stats.ackSamples} acknowledgement samples`]] as const;
 kpis.forEach(([label,value,note],i)=>{const x=14+(i%3)*62,y=85+Math.floor(i/3)*26;rect(x,y,58,23,navy);text(label,x+4,y+6,8,'#cbdcf3');text(records.length?value:'No data',x+4,y+15,19,'#ffffff',true);text(note,x+4,y+20,7.5,'#cbdcf3');});
 box('Incident Trend',`UTC creation date${stats.undated?` | ${stats.undated} undated incidents excluded`:''}`,14,142,182,62);
 if(!stats.trend.length)text('No data',19,179,13,muted);
 else{
  const rows=stats.trend,max=Math.ceil(Math.max(1,...rows.map(r=>r.count))/3)*3,x1=28,x2=186,y1=165,y2=192;
  for(let i=0;i<=3;i++){const y=y2-i*(y2-y1)/3;line([[x1,y],[x2,y]],border,.2);text(Math.round(max*i/3),18,y+1,7,muted);}
  const points=rows.map((r,i)=>[rows.length===1?(x1+x2)/2:x1+(Date.parse(rows[i].key)-Date.parse(rows[0].key))*(x2-x1)/Math.max(1,Date.parse(rows[rows.length-1].key)-Date.parse(rows[0].key)),y2-r.count/max*(y2-y1)]);
  if(points.length>1)line(points,blue,.8);
  points.forEach(([x,y])=>page.push({kind:'circle',x,y,r:1,fill:blue}));
  const indices=[...new Set([0,Math.floor((rows.length-1)/2),rows.length-1])];
  indices.forEach(i=>{const x=points[i][0];text(rows[i].key,Math.min(x2-17,Math.max(x1-5,x-7)),199,7.5,muted);});
 }
 box('Incident Types','Counts per incident per type; multi-type incidents may overlap.',14,211,182,65);
 if(!stats.types.length)text('No data',19,247,13,muted);
 else{
  const sorted=[...stats.types].sort((a,b)=>b.count-a.count),items=sorted.length>7?[...sorted.slice(0,6),{key:'Other types',count:sorted.slice(6).reduce((n,r)=>n+r.count,0)}]:sorted;
  const sum=items.reduce((n,r)=>n+r.count,0),cx=43,cy=250,r=18,inner=10;let angle=-Math.PI/2;
  items.forEach((item,i)=>{const end=angle+item.count/sum*Math.PI*2,steps=Math.max(3,Math.ceil((end-angle)*20)),points:number[][]=[];
   for(let j=0;j<=steps;j++){const a=angle+(end-angle)*j/steps;points.push([cx+Math.cos(a)*r,cy+Math.sin(a)*r]);}
   for(let j=steps;j>=0;j--){const a=angle+(end-angle)*j/steps;points.push([cx+Math.cos(a)*inner,cy+Math.sin(a)*inner]);}
   line(points,palette[i],.05,true,palette[i]);rect(75,232+i*5.3,2.3,2.3,palette[i]);text(`${shortened(item.key,97,8)}  ${item.count}`,80,234+i*5.3,8,ink);angle=end;
  });
  text(sum,cx-3,cy+1,11,ink,true);text('type counts',cx-9,cy+5,7,muted);
 }
 if(longScope){newPage('Report Filter Scope');wrap(scopeText,14,45,182,9,ink);}
 const blocks=[{title:'Incidents by Zone',note:'Saved incident locations',rows:stats.zones.map(r=>({...r,key:zone(r.key)}))},{title:'Severity Distribution',note:'Recorded priority levels',rows:stats.severity,color:(s:string)=>severity[s]||blue},{title:'Response / Resolution Status',note:`${stats.acknowledged} acknowledged by timestamp | ${stats.resolved} resolved`,rows:stats.statuses}];
 let blockIndex=0;
 for(const block of blocks){
  const chunks:typeof block.rows[]=[];let chunk:typeof block.rows=[],used=0;
  for(const row of block.rows){const needed=Math.max(7,Math.min(10,split(row.key,49,8).length)*8*.352778*1.25+2);if(chunk.length&&used+needed>41){chunks.push(chunk);chunk=[];used=0;}chunk.push(row);used+=needed;}
  if(chunk.length||!chunks.length)chunks.push(chunk);
  for(const [i,chunk] of chunks.entries()){
   if(blockIndex%3===0)newPage('Incident Distribution');
   bars(block.title+(chunks.length>1?` (${i+1}/${chunks.length})`:''),block.note,chunk,14,44+(blockIndex%3)*78,182,70,block.color);blockIndex++;
  }
 }
 newPage('Permitted Incident Evidence');
 wrap('Representative frames from retained public-area incident clips. Private areas and unknown zones: metadata only.',14,43,182,8.5,muted);
 const previews=snapshot.evidence.filter(e=>records.some(r=>r.id===e.incidentId)).slice(0,4).map(e=>{
  const record=records.find(r=>r.id===e.incidentId)!;
  const permitted=record.zone_id===e.zoneId&&record.zone_type==='OPEN_HIDDEN'&&zones.some(z=>z.id===record.zone_id&&z.zone_type==='OPEN_HIDDEN');
  return permitted?{...e,image:e.image?.startsWith('data:image/jpeg;base64,')?e.image:undefined}:{...e,image:undefined,note:'Private / unknown zone: sensor metadata only'};
 });
 if(!previews.length){box('No data','No permitted retained evidence is available for this selection.',14,58,182,42);}
 previews.forEach((e,i)=>{
  const x=14+(i%2)*94,y=58+Math.floor(i/2)*99;
  rect(x,y,88,92,'#ffffff',border);wrap(`#${e.incidentId.slice(0,8)} - ${zone(e.zoneId)}`,x+3,y+7,82,8.5,ink,true,2);
  if(e.image)page.push({kind:'image',x:x+3,y:y+15,w:82,h:46.125,data:e.image,incidentId:e.incidentId});
  else{rect(x+3,y+15,82,46.125,light);wrap(e.note,x+7,y+31,73,9,muted);}
  wrap(e.label,x+3,y+67,82,8,ink,true,2);wrap(e.mode,x+3,y+76,82,7.5,muted,false,2);
  wrap(e.image?`Retained frame at source ${e.sourceTime||'unavailable'}s`:'Sensor metadata / no video thumbnail',x+3,y+87,82,7,muted);
 });
 const modes=stats.modes.map(m=>`${modeLabels[m.key]||m.key}: ${m.count}`).join(' | ')||'No data';
 wrap(modes,14,256,182,8,muted);
 wrap('Evidence follows retained files and current zone permissions; no recording is substituted. Response = creation to acknowledgement; missing or negative intervals excluded.',14,267,182,7.5,muted);
 const columns=[27,25,29,27,21,29,24],titles=['Incident / UTC','Zone','Event Types','Processing Mode','Severity','Status','Review'];
 let y=0;
 function tablePage(){newPage('Incident Records');text(`${records.length} incidents in the filtered snapshot`,14,43,9,muted);y=50;rect(14,y,182,9,navy);let x=14;titles.forEach((s,i)=>{text(s,x+2,y+5.5,7.6,'#ffffff',true);x+=columns[i];});y+=9;}
 tablePage();
 if(!records.length)text('No data',16,y+12,12,muted);
 records.forEach((record,index)=>{
  const mode=record.processing_mode==='recorded_sensor_replay'?'Recorded replay':modeLabels[record.processing_mode||'']||record.processing_mode||'Not recorded';
  const cells=[`#${record.id.slice(0,8)}\n${record.created_at?.replace('T',' ').replace(/Z$/,'').slice(0,19)||'No data'}`,zone(record.zone_id),events(record).join(', ')||'No data',mode,record.level,record.status,record.review_status||'Not recorded'];
  measure.setFont('helvetica','normal');measure.setFontSize(8);
  const lines=cells.map((s,i)=>measure.splitTextToSize(clean(s).replace(/ {2,}/g,' '),columns[i]-4) as string[]);
  const rowHeight=Math.max(13,...lines.map(v=>v.length*3.5+4));
  if(y+rowHeight>277&&rowHeight<=218)tablePage();
  const lineCount=Math.max(...lines.map(cell=>cell.length));let consumed=0;
  while(consumed<lineCount){
   if(277-y<13)tablePage();
   const capacity=Math.max(1,Math.floor((277-y-4)/3.5)),take=Math.min(capacity,lineCount-consumed),height=Math.max(13,take*3.5+4);
   rect(14,y,182,height,index%2===0?light:'#ffffff');let x=14;
   lines.forEach((cell,i)=>{const part=cell.slice(consumed,consumed+take);if(consumed&&i===0&&!part.length)part.push(`#${record.id.slice(0,8)} (cont.)`);part.forEach((s,j)=>text(s,x+2,y+4+j*3.5,8,i===4?severity[record.level]||ink:ink));x+=columns[i];});
   y+=height;consumed+=take;if(consumed<lineCount)tablePage();
  }
 });

 const id=fingerprint({records,filters,zones,snapshotAt:snapshot.snapshotAt});
 pages.forEach((p,i)=>{page=p;line([[14,284],[196,284]],border,.3);text(`SafeSense AI | Filtered operational report | ${id}`,14,290,7,muted);text(`${i+1} / ${pages.length}`,184,290,7,muted);});
 return {pages,snapshot,fingerprint:id};
}

export function visualReportPdf(report:VisualReport){
 const pdf=new jsPDF({format:'a4',unit:'mm',compress:true});
 pdf.setProperties({title:'SafeSense AI - Visual Operational Report',subject:`Filtered dataset ${report.fingerprint}`,keywords:'SafeSense visual report, vector charts, '+report.fingerprint});
 report.pages.forEach((page,index)=>{
  if(index)pdf.addPage();
  page.forEach(item=>{
   if(item.kind==='rect'){pdf.setFillColor(item.fill);if(item.stroke){pdf.setDrawColor(item.stroke);pdf.setLineWidth(.25);}pdf.rect(item.x,item.y,item.w,item.h,item.stroke?'FD':'F');}
   else if(item.kind==='text'){pdf.setFont('helvetica',item.bold?'bold':'normal');pdf.setFontSize(item.size);pdf.setTextColor(item.color);pdf.text(item.value,item.x,item.y);}
   else if(item.kind==='circle'){pdf.setFillColor(item.fill);pdf.circle(item.x,item.y,item.r,'F');}
   else if(item.kind==='image')pdf.addImage(item.data,'JPEG',item.x,item.y,item.w,item.h,undefined,'FAST');
   else if(item.points.length>1){pdf.setDrawColor(item.color);pdf.setLineWidth(item.width);if(item.fill)pdf.setFillColor(item.fill);const [first,...rest]=item.points;let previous=first;const deltas=rest.map(point=>{const delta=[point[0]-previous[0],point[1]-previous[1]];previous=point;return delta;});pdf.lines(deltas,first[0],first[1],[1,1],item.fill?'F':'S',!!item.closed);}
  });
 });
 return pdf;
}
const escape=(value:unknown)=>String(value).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]!));
export function visualReportHtml(report:VisualReport){
 const shape=(s:Shape)=>{
  if(s.kind==='rect')return `<rect x="${s.x}" y="${s.y}" width="${s.w}" height="${s.h}" fill="${s.fill}" stroke="${s.stroke||'none'}" stroke-width=".25"/>`;
  if(s.kind==='text')return `<text x="${s.x}" y="${s.y}" fill="${s.color}" font-family="Arial,Helvetica,sans-serif" font-size="${s.size*25.4/72}" font-weight="${s.bold?'700':'400'}">${escape(s.value)}</text>`;
  if(s.kind==='circle')return `<circle cx="${s.x}" cy="${s.y}" r="${s.r}" fill="${s.fill}"/>`;
  if(s.kind==='image')return `<image data-incident-id="${escape(s.incidentId)}" x="${s.x}" y="${s.y}" width="${s.w}" height="${s.h}" href="${s.data}"/>`;
  return `<${s.closed?'polygon':'polyline'} points="${s.points.map(p=>p.join(',')).join(' ')}" fill="${s.fill||'none'}" stroke="${s.color}" stroke-width="${s.width}"/>`;
 };
 return `<!doctype html><html><head><meta charset="utf-8"><title>SafeSense AI Visual Report</title><style>@page{size:A4;margin:0}*{box-sizing:border-box}html,body{margin:0;padding:0;background:white}.report-sheet{width:210mm;height:297mm;break-after:page;overflow:hidden}.report-sheet:last-child{break-after:auto}.report-sheet svg{display:block;width:210mm;height:297mm}body{-webkit-print-color-adjust:exact;print-color-adjust:exact}</style></head><body data-report-id="${report.fingerprint}">${report.pages.map((p,i)=>`<section class="report-sheet" aria-label="Report page ${i+1}"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 210 297" role="img" aria-label="SafeSense visual report page ${i+1}">${p.map(shape).join('')}</svg></section>`).join('')}</body></html>`;
}
export function printVisualReport(report:VisualReport){
 return new Promise<void>((resolve,reject)=>{
  const frame=document.createElement('iframe');frame.title='Print SafeSense visual report';frame.style.cssText='position:fixed;width:0;height:0;border:0';
  frame.onload=async()=>{try{const win=frame.contentWindow;if(!win)throw Error('Print document unavailable');await win.document.fonts.ready;await Promise.all(Array.from(win.document.querySelectorAll('image')).map(async node=>{const image=new Image();image.src=node.getAttribute('href')||'';await image.decode();}));win.onafterprint=()=>frame.remove();win.focus();win.print();resolve();}catch(e){frame.remove();reject(e);}};
  frame.srcdoc=visualReportHtml(report);document.body.append(frame);
 });
}
