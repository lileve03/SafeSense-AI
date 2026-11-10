import {notificationStateLabel} from './notificationState';
import {registerCameras} from './cameraRegistry';
import { Alert, RiskLevel } from '../types/safesense';
export const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000';
export const AI_BASE = import.meta.env.VITE_AI_BASE_URL || 'http://127.0.0.1:8001';
export const AI_TOKEN = import.meta.env.VITE_SAFESENSE_API_TOKEN || 'local-demo-only';

export async function api<T = any>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(API_BASE + path, { ...init, headers: {'X-SafeSense-Token':AI_TOKEN, ...init?.headers}, signal: init?.signal || AbortSignal.timeout(10000) });
  const data = await response.json();
  if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : `HTTP ${response.status}`);
  if(path==='/monitoring/cameras'&&Array.isArray(data))registerCameras(data);
  return data;
}
export function post(path: string, body: unknown) {
  return api(path, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
}
export const severityPriority: Record<RiskLevel, number> = { LOW: 0, OBSERVE: 25, WARNING: 50, HIGH: 75, CRITICAL: 100 };
export function toAlert(i: any, zones: {id: string; name: string}[]): Alert {
  const evidence = i.evidence || [];
  return {
    id: i.id, incidentNumber: i.id.slice(0,8), zoneId: i.zone_id,
    notificationStatus: notificationStateLabel(i.notification_state||i.notification_status),
    acknowledgedAt: i.acknowledged_at,
    zoneName: zones.find(z => z.id === i.zone_id)?.name || i.zone_id,
    level: i.level, riskScore: severityPriority[i.level as RiskLevel],
    title: i.reason, reason: i.reason,
    triggerType: `${i.source} / ${i.processing_mode}`,
    explainableFactors: [ `Mode: ${i.processing_mode}`, 'Severity priority is a rule ranking, not a probability.',
      ...evidence.map((e: any) => `${e.type} (${e.source}); model ${e.model_version || 'none'}; score ${e.score ?? 'not applicable (rule/simulation)'}; evidence ${e.evidence_reference || e.id}`)],
    detectedTime: i.created_at, status: i.status.toLowerCase(), assignedStaff: i.assigned_staff || i.staff || undefined,
    triggeringSensors: [...new Set<string>(evidence.map((e: any) => e.source))],
    timeline: (i.history || []).map((h: any) => ({ time: h.timestamp, event: `${h.status}: ${h.note}` })),
    processingMode: i.processing_mode, source: i.source,
    resolutionNote: [...(i.history || [])].reverse().find((h: any)=>h.status==='RESOLVED')?.note,
    falseAlarmReason: [...(i.history || [])].reverse().find((h: any)=>h.status==='FALSE_ALARM')?.note,
  };
}
