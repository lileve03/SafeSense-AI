import {AI_BASE,AI_TOKEN} from './api';
import {IncidentRecord,modeLabels,timestamp} from './incidentAnalytics';
import {EvidencePreview,ReportZone} from './visualReport';
const dataUrl=(blob:Blob)=>new Promise<string>((resolve,reject)=>{const reader=new FileReader();reader.onload=()=>resolve(String(reader.result));reader.onerror=()=>reject(Error('Thumbnail could not be read'));reader.readAsDataURL(blob);});
export async function loadReportEvidence(records:IncidentRecord[],zones:ReportZone[]):Promise<EvidencePreview[]>{
 const ordered=[...records].sort((a,b)=>(timestamp(b.created_at)||0)-(timestamp(a.created_at)||0));
 const candidates=ordered.filter(r=>r.zone_type==='OPEN_HIDDEN'&&zones.some(z=>z.id===r.zone_id&&z.zone_type==='OPEN_HIDDEN')).flatMap(r=>{
  const media=r.evidence?.flatMap(e=>e.evidence_media||[])[0];
  return media?[{record:r,media}]:[];
 }).slice(0,8);
 const loaded=await Promise.all(candidates.map(async({record:r,media}):Promise<EvidencePreview>=>{
  const base:EvidencePreview={incidentId:r.id,zoneId:r.zone_id,label:[...new Set(r.evidence?.map(e=>e.type).filter(Boolean))].join(', ')||'Saved incident',mode:modeLabels[r.processing_mode||'']||r.processing_mode||'Mode not recorded',note:'Thumbnail unavailable: retained clip expired, missing or service offline.'};
  try{
   const response=await fetch(`${AI_BASE}/monitoring/incidents/${encodeURIComponent(r.id)}/evidence/${encodeURIComponent(media.id)}/thumbnail`,{headers:{'X-SafeSense-Token':AI_TOKEN},signal:AbortSignal.timeout(6000)});
   if(!response.ok||!response.headers.get('Content-Type')?.startsWith('image/jpeg'))return base;
   const blob=await response.blob();if(blob.size>3_000_000)return base;
   return {...base,image:await dataUrl(blob),sourceTime:response.headers.get('X-Evidence-Frame-Sec')||undefined,note:'Representative retained public-area frame'};
  }catch{return base;}
 }));
 const images=loaded.filter(e=>e.image).slice(0,4);
 if(images.length)return images;
 if(loaded.length)return loaded.slice(0,4);
 return ordered.slice(0,4).map(r=>({incidentId:r.id,zoneId:r.zone_id,label:[...new Set(r.evidence?.map(e=>e.type).filter(Boolean))].join(', ')||'Saved incident',mode:modeLabels[r.processing_mode||'']||r.processing_mode||'Mode not recorded',note:r.zone_type==='OPEN_HIDDEN'?'No retained evidence thumbnail':'Private / unknown zone: sensor metadata only'}));
}
