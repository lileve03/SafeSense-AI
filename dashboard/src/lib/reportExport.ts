import { jsPDF } from 'jspdf';
import autoTable from 'jspdf-autotable';

// Only metadata is exported. Private and unknown zones never expose media references.
export function evidenceReference(report: any, evidence: any): string {
  if (report.zone_type !== 'OPEN_HIDDEN') return 'Private sensor metadata only; media excluded';
  return String(evidence.evidence_reference || evidence.id || 'No retained reference');
}
const value = (v: unknown) => v == null || v === '' ? 'Not recorded' : typeof v === 'object' ? JSON.stringify(v) : String(v);
export function reportSections(r: any): { title: string; rows: string[][] }[] {
  const evidence = r.evidence || [];
  return [
    {title:'Summary', rows:Object.entries({
      'Incident ID':r.id,'Timestamp':r.created_at,'Zone':r.zone_id,'Zone type':r.zone_type,
      'Event types':evidence.map((e:any)=>e.type).join('; '),'Severity':r.level,'Status':r.status,
      'Detection source':r.source,'Source type':r.source_type,'Processing mode':r.processing_mode,
      'Human review':r.review_status,'Reason':r.reason,'Test incident':r.is_test,
    }).map(([k,v])=>[k,value(v)])},
    {title:'Evidence',rows:evidence.length?evidence.flatMap((e:any,i:number)=>[
      [`Observation ${i+1}`,value(e.type)],['Timestamp',value(e.timestamp)],['Model',value(e.model_version)],
      ['Score',value(e.score)],['Source',value(e.source)],['Reason',value(e.reason)],['Permitted reference',evidenceReference(r,e)],
    ]):[['Evidence','No observations recorded']]},
    {title:'Response',rows:[
      ['Assigned staff',value(r.assigned_staff)],['Acknowledged at / by',`${value(r.acknowledged_at)} / ${value(r.acknowledged_by)}`],
      ['Resolved at / by',`${value(r.resolved_at)} / ${value(r.resolved_by)}`],
      ...(r.notifications||[]).map((n:any)=>['Notification',`${value(n.timestamp)} / ${value(n.status)} / ${value(n.assigned_staff)}`]),
      ...(r.history||[]).map((h:any)=>['Audit history',`${value(h.timestamp)} / ${value(h.status)} / ${value(h.note)}`]),
    ]},
    {title:'Analysis',rows:Object.entries(r.analysis||{}).map(([k,v])=>[k.replaceAll('_',' '),value(v)])},
  ];
}
export function csvCell(input: unknown): string {
  let s = input == null ? '' : String(input);
  if (/^[\s\u0000-\u001f]*[=+@-]/u.test(s) || /^[\t\r\n]/.test(s)) s = "'"+s;
  return '"'+s.replaceAll('"','""')+'"';
}
export function reportCsv(r:any):string {
  const evidence=r.evidence||[];
  const headers=['incident_id','timestamp','zone','event_type','model','score','severity','status','assigned_staff','acknowledged_at','acknowledged_by','resolved_at','resolved_by','human_review','detection_source','processing_mode','evidence_reference'];
  const row=[r.id,r.created_at,r.zone_id,evidence.map((e:any)=>e.type).join('; '),evidence.map((e:any)=>e.model_version??'').join('; '),evidence.map((e:any)=>e.score??'').join('; '),r.level,r.status,r.assigned_staff,r.acknowledged_at,r.acknowledged_by,r.resolved_at,r.resolved_by,r.review_status,r.source,r.processing_mode,evidence.map((e:any)=>evidenceReference(r,e)).join('; ')];
  return '\uFEFF'+[headers,row].map(cells=>cells.map(csvCell).join(',')).join('\r\n')+'\r\n';
}
export function download(blob:Blob,name:string) {
  const url=URL.createObjectURL(blob), link=document.createElement('a');
  link.href=url;link.download=name;document.body.append(link);link.click();link.remove();
  setTimeout(()=>URL.revokeObjectURL(url),60000);
}
export function reportPdf(r:any,scope:string,generated:string):jsPDF {
  const pdf=new jsPDF({format:'a4',unit:'mm'});
  pdf.setProperties({title:'SafeSense AI Incident Report',subject:scope});
  pdf.setFontSize(18);pdf.text('SafeSense AI Incident Report',14,20);
  autoTable(pdf,{startY:27,head:[['Report date',generated]],body:[['Scope',scope]],styles:{fontSize:10,overflow:'linebreak'},columnStyles:{0:{cellWidth:44}}});
  for(const section of reportSections(r)) {
    const end=(pdf as any).lastAutoTable.finalY;
    autoTable(pdf,{startY:end+8,head:[[section.title,'Details']],body:section.rows,
      margin:{top:15,bottom:18,left:14,right:14},styles:{fontSize:10,cellPadding:3,overflow:'linebreak'},
      headStyles:{fillColor:[37,99,235]},columnStyles:{0:{cellWidth:44}},rowPageBreak:'avoid'});
  }
  const pages=pdf.getNumberOfPages();
  for(let page=1;page<=pages;page++){pdf.setPage(page);pdf.setFontSize(9);pdf.text(`SafeSense AI | ${page} / ${pages}`,14,288);}
  return pdf;
}
const escapeHtml=(s:string)=>s.replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]!));
export function reportPrintHtml(r:any,scope:string,generated:string):string {
  return `<!doctype html><html><head><meta charset="utf-8"><title>SafeSense AI Incident Report</title><style>
    @page{size:A4;margin:15mm}*{box-sizing:border-box}body{font:11pt Arial,sans-serif;color:#0f172a;margin:0}h1{font-size:20pt}h2{font-size:14pt;break-after:avoid}table{width:100%;border-collapse:collapse;table-layout:fixed;margin-bottom:8mm}th,td{border:1px solid #cbd5e1;padding:7px;text-align:left;overflow-wrap:anywhere}th{background:#eff6ff}th:first-child,td:first-child{width:26%}thead{display:table-header-group}tr{break-inside:avoid}p{overflow-wrap:anywhere}
    </style></head><body><h1>SafeSense AI Incident Report</h1><p>Report date: ${escapeHtml(generated)}</p><p>Scope: ${escapeHtml(scope)}</p>${reportSections(r).map(s=>`<h2>${s.title}</h2><table><thead><tr><th>Field</th><th>Details</th></tr></thead><tbody>${s.rows.map(row=>`<tr>${row.map(cell=>`<td>${escapeHtml(cell)}</td>`).join('')}</tr>`).join('')}</tbody></table>`).join('')}</body></html>`;
}
export function printReport(r:any,scope:string,generated:string) {
  const frame=document.createElement('iframe');frame.title='Print SafeSense report';
  frame.style.cssText='position:fixed;width:0;height:0;border:0';
  frame.onload=()=>{const win=frame.contentWindow;if(!win)return;win.onafterprint=()=>frame.remove();win.focus();win.print();};
  frame.srcdoc=reportPrintHtml(r,scope,generated);document.body.append(frame);
}
