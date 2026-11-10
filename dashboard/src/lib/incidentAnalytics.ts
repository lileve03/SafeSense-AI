export type IncidentRecord = {
  id: string; zone_id: string; status: string; level: string; source?: string;
  processing_mode?: string; source_type?: string; created_at?: string;
  acknowledged_at?: string | null; resolved_at?: string | null; assigned_staff?:string|null; staff?:string|null;
  evidence?: {id?:string; type?: string; model_version?:string|null; score?:number|null; evidence_reference?:string|null; evidence_media?: {id:string; model_version?:string; camera_id?:string}[]}[]; reason?: string; review_status?: string; zone_type?: string;
};
export type AnalyticsFilters = {mode:string;zone:string;source:string;severity:string;status:string;ack:string;range:string;from:string;to:string;eventType?:string};
export const initialAnalyticsFilters:AnalyticsFilters={mode:'all',zone:'all',source:'all',severity:'all',status:'all',ack:'all',range:'all',from:'',to:''};
export const modeLabels:Record<string,string>={real_model:'Real-model events',recorded_sensor_replay:'Recorded sensor replays',simulation:'Simulations'};
export const sourceLabels:Record<string,string>={vision:'Vision',radar:'Radar',yamnet:'Acoustic (YAMNet)',sos_button:'SOS input',simulation:'Simulation source'};
export const timestamp=(value?:string|null)=>value?Date.parse(value):NaN;
export const acknowledged=(row:IncidentRecord)=>Number.isFinite(timestamp(row.acknowledged_at));
export const terminal=(row:IncidentRecord)=>['RESOLVED','FALSE_ALARM'].includes(row.status);
export function filterIncidents(records:IncidentRecord[],filters:AnalyticsFilters,now=Date.now()){
  const today=new Date(now).toISOString().slice(0,10);
  let from='',to='';
  if(filters.range==='custom'){from=filters.from;to=filters.to;}
  else if(filters.range!=='all'){
    const days=filters.range==='today'?1:filters.range==='7days'?7:30;
    from=new Date(Date.parse(today+'T00:00:00Z')-(days-1)*86400000).toISOString().slice(0,10);to=today;
  }
  const seen=new Set<string>();
  return records.filter(row=>{
    if(!row.id||seen.has(row.id))return false;
    seen.add(row.id);
    if(filters.eventType && filters.eventType!=='all' && !(row.evidence||[]).some(e=>e.type===filters.eventType) && !(filters.eventType==='Not recorded' && !(row.evidence||[]).some(e=>e.type)))return false;
    if(filters.mode!=='all'&&(row.processing_mode||'unknown')!==filters.mode)return false;
    if(filters.zone!=='all'&&row.zone_id!==filters.zone)return false;
    if(filters.source!=='all'&&(row.source||'unknown')!==filters.source)return false;
    if(filters.severity!=='all'&&row.level!==filters.severity)return false;
    if(filters.status!=='all'&&row.status!==filters.status)return false;
    if(filters.ack!=='all'&&acknowledged(row)!==(filters.ack==='acknowledged'))return false;
    if(from||to){
      const parsed=timestamp(row.created_at);if(!Number.isFinite(parsed))return false;
      const day=new Date(parsed).toISOString().slice(0,10);
      if(from&&day<from||to&&day>to)return false;
    }
    return true;
  });
}
export function counts(records:IncidentRecord[],key:(row:IncidentRecord)=>string){
  const tally=new Map<string,number>();
  records.forEach(row=>{const value=key(row);tally.set(value,(tally.get(value)||0)+1);});
  return [...tally].map(([key,count])=>({key,count}));
}
function durations(records:IncidentRecord[],field:'acknowledged_at'|'resolved_at'){
  return records.filter(row=>field!=='resolved_at'||terminal(row)).flatMap(row=>{
    const start=timestamp(row.created_at),end=timestamp(row[field]);
    return Number.isFinite(start)&&Number.isFinite(end)&&end>=start?[(end-start)/1000]:[];
  });
}
export function summarizeIncidents(records:IncidentRecord[]){
  const ackSeconds=durations(records,'acknowledged_at'),closureSeconds=durations(records,'resolved_at');
  const closed=records.filter(terminal).length;
  const falseAlarms=records.filter(row=>row.status==='FALSE_ALARM').length;
  const types=new Map<string,number>();
  records.forEach(row=>{
    const unique=new Set((row.evidence||[]).map(e=>e.type).filter((type):type is string=>!!type));
    if(!unique.size)unique.add('Not recorded');
    unique.forEach(type=>types.set(type,(types.get(type)||0)+1));
  });
  const dated=records.filter(row=>Number.isFinite(timestamp(row.created_at)));
  return {
    total:records.length,open:records.filter(row=>!terminal(row)).length,
    acknowledged:records.filter(acknowledged).length,
    awaitingAck:records.filter(row=>!terminal(row)&&!acknowledged(row)).length,
    resolved:records.filter(row=>row.status==='RESOLVED').length,falseAlarms,closed,
    falseAlarmRate:closed?falseAlarms/closed*100:null,
    meanAck:ackSeconds.length?ackSeconds.reduce((a,b)=>a+b,0)/ackSeconds.length:null,ackSamples:ackSeconds.length,
    meanClosure:closureSeconds.length?closureSeconds.reduce((a,b)=>a+b,0)/closureSeconds.length:null,closureSamples:closureSeconds.length,
    severity:counts(records,r=>r.level||'Not recorded'),zones:counts(records,r=>r.zone_id||'Not recorded'),
    sources:counts(records,r=>r.source||'unknown'),modes:counts(records,r=>r.processing_mode||'unknown'),
    statuses:counts(records,r=>r.status||'Not recorded'),
    acknowledgements:counts(records,r=>acknowledged(r)?'Acknowledged':'No acknowledgement recorded'),
    types:[...types].map(([key,count])=>({key,count})),
    trend:counts(dated,r=>new Date(timestamp(r.created_at)).toISOString().slice(0,10)).sort((a,b)=>a.key.localeCompare(b.key)),
    undated:records.length-dated.length,
    recent:[...records].sort((a,b)=>(timestamp(b.created_at)||0)-(timestamp(a.created_at)||0)).slice(0,6),
  };
}
export function durationLabel(seconds:number|null){
  if(seconds===null)return 'Not measured';
  if(seconds<60)return `${seconds.toFixed(1)}s`;
  if(seconds<3600)return `${(seconds/60).toFixed(1)} min`;
  if(seconds<86400)return `${(seconds/3600).toFixed(1)} hr`;
  return `${(seconds/86400).toFixed(1)} days`;
}
