export function notificationStateLabel(value?:string) {
 const labels:Record<string,string>={SENT:'Telegram API accepted - receipt unconfirmed',API_ACCEPTED:'Telegram API accepted - receipt unconfirmed',RECEIPT_CONFIRMED:'Receipt confirmed by authorized Telegram test user',PENDING:'Pending Telegram processing',QUEUED:'Pending Telegram processing',SENDING:'Pending Telegram processing',FAILED:'Telegram request failed',UNKNOWN:'Acceptance unknown - no automatic resend',DELIVERY_UNKNOWN:'Acceptance unknown - no automatic resend',DISABLED:'Sending disabled',NOT_CONFIGURED:'Sending disabled - configuration missing',POLICY_SUPPRESSED:'Not eligible under notification policy'};
 return labels[value||'PENDING']||value||'Pending';
}
