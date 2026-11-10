import {api} from './api';
import {notificationStateLabel} from './notificationState';
export type SosOutcome={state:string;message:string};
export function describeSosOutcome(report:any,configuration:any):SosOutcome {
 const saved=`SOS incident #${String(report?.id||'unknown').slice(0,8)} saved in SQLite.`;
 const attempt=report?.notifications?.at(-1);
 const state=report?.notification_state||attempt?.delivery_state||attempt?.status||'PENDING';
 if(['API_ACCEPTED','SENT','RECEIPT_CONFIRMED'].includes(state))return {state:state==='SENT'?'API_ACCEPTED':state,message:`${saved} ${notificationStateLabel(state)}.`};
 if(configuration?.mode==='disabled')return {state:'DISABLED',message:`${saved} Telegram NOT SENT: backend TELEGRAM_MODE=disabled. Missing setup: ${(configuration.missing_setup||[]).join(', ')||'enable authorized test mode locally'}.`};
 if(configuration && !configuration.test_configured)return {state:'DISABLED',message:`${saved} Telegram NOT SENT: backend test credentials are missing. ${(configuration.missing_setup||[]).join(', ')}`};
 if(attempt?.status==='NO_ACTIVE_ASSIGNMENT')return {state:'DISABLED',message:`${saved} Telegram NOT SENT: no authorized on-duty teacher route is configured.`};
 if(['FAILED','UNKNOWN','DELIVERY_UNKNOWN'].includes(state))return {state,message:`${saved} ${notificationStateLabel(state)}. Review this incident's notification attempt; do not create another SOS to retry.`};
 return {state,message:`${saved} ${notificationStateLabel(state)}. Check the incident notification details; receipt is not assumed.`};
}
export async function sosNotificationOutcome(incidentId:string):Promise<SosOutcome> {
 try {
  const configuration=await api('/notifications/status');
  for(let i=0;i<8;i++){
   const report=await api(`/incidents/${encodeURIComponent(incidentId)}/report`);
   if(report.id!==incidentId)throw new Error('Incident response identity mismatch');
   const outcome=describeSosOutcome(report,configuration);
   if(!['PENDING','SENDING','QUEUED'].includes(outcome.state)||i===7)return outcome;
   await new Promise(resolve=>setTimeout(resolve,350));
  }
 }catch{return {state:'UNKNOWN',message:`SOS incident #${incidentId.slice(0,8)} was saved, but Telegram status could not be verified. Open its incident details; do not submit another SOS.`};}
 return {state:'PENDING',message:'SOS saved; Telegram processing is pending.'};
}
