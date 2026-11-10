import {IncidentRecord} from './incidentAnalytics';
import {ReportSnapshot,ReportZone,fingerprint} from './visualReport';
import {csvCell,evidenceReference} from './reportExport';
export const filteredCsvHeaders=['Incident ID','Timestamp','Zone','Event Type','Severity','Source','Model Version','Score','Processing Mode','Review Status','Assigned Staff','Acknowledged At','Resolved At','Evidence Reference'];
export type ExportSnapshot=Omit<ReportSnapshot,'evidence'>;
export function exportDatasetId(snapshot:ExportSnapshot){
 return fingerprint({records:snapshot.records,filters:snapshot.filters,zones:snapshot.zones,snapshotAt:snapshot.snapshotAt});
}
export function filteredIncidentsCsv(snapshot:Pick<ExportSnapshot,'records'|'zones'>):string{
 const zoneName=(r:IncidentRecord)=>snapshot.zones.find(z=>z.id===r.zone_id)?.name||r.zone_id;
 const rows=snapshot.records.map(r=>{
  const evidence=r.evidence||[];
  const publicZone=r.zone_type==='OPEN_HIDDEN'&&snapshot.zones.some((z:ReportZone)=>z.id===r.zone_id&&z.zone_type==='OPEN_HIDDEN');
  return [r.id,r.created_at,zoneName(r),[...new Set(evidence.flatMap(e=>e.type?[e.type]:[]))].join('; '),r.level,r.source,
   evidence.map(e=>e.model_version??'').join('; '),evidence.map(e=>e.score??'').join('; '),r.processing_mode,r.review_status,r.assigned_staff||r.staff||'',
   r.acknowledged_at,r.resolved_at,evidence.map(e=>evidenceReference(publicZone?r:{...r,zone_type:'PRIVATE'},e)).join('; ')];
 });
 // One row per incident. Model, score and evidence-reference lists retain observation order.
 // Shared escaping protects every cell, including labels supplied by the backend.
 return '\uFEFF'+[filteredCsvHeaders,...rows].map(row=>row.map(csvCell).join(',')).join('\r\n')+'\r\n';
}
