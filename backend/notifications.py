"""Opt-in Telegram delivery. Test/replay incidents can never reach staff recipients."""
import json
import os
import time
import secrets
import math
import logging
from datetime import datetime, timezone, timedelta
from urllib.request import Request, urlopen
from uuid import uuid4
from threading import Lock
from hashlib import sha256
from urllib.error import HTTPError
from backend import storage

SEND_LOCK = Lock()

def masked_chat(value):
    return ('-' if value.startswith('-') else '')+'***'+value[-4:] if value else None

def transport_kind():
    return 'real_https' if getattr(urlopen,'__module__',None)=='urllib.request' else 'test_transport'

def routes():
    path = os.getenv('SAFESENSE_STAFF_ROUTES')
    if not path:
        return []
    try:
        data = json.loads(__import__('pathlib').Path(path).read_text(encoding='utf-8-sig'))
        return [r for r in data if isinstance(r,dict) and isinstance(r.get('staff'),str) and r.get('zone_id')] if isinstance(data,list) else []
    except (OSError, ValueError):
        return []

def on_duty(route, now=None):
    if route.get('active') is not True:return False
    now=now or datetime.now(timezone.utc)
    start,end=route.get('shift_start'),route.get('shift_end')
    if not start and not end:return True  # Explicit operator-maintained active roster.
    if not start or not end:return False
    try:
        start=datetime.fromisoformat(start.replace('Z','+00:00'))
        end=datetime.fromisoformat(end.replace('Z','+00:00'))
        return bool(start.tzinfo and end.tzinfo and start<=now<end)
    except (ValueError,TypeError,AttributeError):return False

def select_route(incident):
    private=incident.get('zone_type')=='PRIVATE' or incident['zone_id']=='ZONE_TOILET_BLINDSPOT'
    test_context=os.getenv('TELEGRAM_MODE')=='test' and incident.get('is_test',True) is True and incident.get('source_type') not in ('LIVE CAMERA','LIVE SENSOR','LIVE SOS')
    eligible=[r for r in routes() if r['zone_id']==incident['zone_id'] and on_duty(r)
              and (not r.get('test_only') or test_context)
              and (not private or r.get('role') in ('teacher','duty_teacher') or (test_context and r.get('test_only') is True and r.get('role')=='test_operator'))]
    # Explicit test SOS alerts share the configured test operator across zones.
    # Live incidents still require their own zone assignment.
    if not eligible and test_context and any(e.get('type','').lower()=='sos' for e in incident.get('evidence',[])):
        eligible=[r for r in routes() if on_duty(r) and r.get('test_only') is True and r.get('role')=='test_operator']
    def priority(row):
        value=row.get('priority',100)
        return (bool(row.get('is_backup')),value if isinstance(value,(int,float)) else 100)
    return sorted(eligible,key=priority)[0] if eligible else None

def chat_for(route):
    key=route.get('chat_id_env','') if route else ''
    return os.getenv(key,'') if key.startswith('TELEGRAM_') and key.endswith('_CHAT_ID') else ''

def status():
    mode=os.getenv('TELEGRAM_MODE','disabled')
    token=bool(os.getenv('TELEGRAM_BOT_TOKEN'))
    test_ready=token and bool(os.getenv('TELEGRAM_TEST_CHAT_ID'))
    staff_enabled=mode=='staff' and os.getenv('TELEGRAM_STAFF_DISPATCH_ENABLED','').lower()=='true'
    configured=token and (test_ready if mode=='test' else any(chat_for(r) for r in routes()) if mode=='staff' else False)
    state='READY_TEST_ONLY' if mode=='test' and test_ready else 'READY_STAFF' if mode=='staff' and staff_enabled and configured else 'STAFF_DISPATCH_NOT_AUTHORIZED' if mode=='staff' and not staff_enabled else 'NOT_CONFIGURED'
    return {'mode':mode,'configured':bool(configured),'test_configured':bool(test_ready),'status':state,
            'process_id':os.getpid(),'transport_kind':transport_kind(),
            'test_recipient_masked':masked_chat(os.getenv('TELEGRAM_TEST_CHAT_ID','')),
            'test_recipient_kind':'group' if os.getenv('TELEGRAM_TEST_CHAT_ID','').startswith('-') else 'personal' if os.getenv('TELEGRAM_TEST_CHAT_ID','').isdigit() else 'unknown',
            'receipt_verification_configured':bool(test_ready and ack_users()),
            'missing_setup':[name for name,present in [('TELEGRAM_BOT_TOKEN',token),('TELEGRAM_TEST_CHAT_ID',bool(os.getenv('TELEGRAM_TEST_CHAT_ID'))),('SAFESENSE_STAFF_ROUTES/on-duty private-zone teacher assignment',bool(select_route({'zone_id':'ZONE_TOILET_BLINDSPOT'})))] if not present],
            'production_dispatch':staff_enabled,'routes':[{'zone_id':r['zone_id'],'staff':r['staff'],'role':r.get('role','staff'),
            'active':r.get('active') is True,'on_duty':on_duty(r),'is_backup':bool(r.get('is_backup')),'test_only':r.get('test_only') is True,
            'recipient_configured':bool(chat_for(r)),
            'selected_for_zone':select_route({'zone_id':r['zone_id']})==r} for r in routes()]}

def dispatch(incident, force_test=False):
    with SEND_LOCK:
        return _dispatch(incident,force_test)

def delivery_state(row):
    if row.get('receipt_confirmed_at'):return 'RECEIPT_CONFIRMED'
    if row.get('status')=='SENT' and not (row.get('telegram_api_ok') is True and type(row.get('telegram_message_id')) is int and row['telegram_message_id']>0):
        return 'UNKNOWN'
    return {'SENT':'API_ACCEPTED','SENDING':'PENDING','PREVIEW':'DISABLED','NOT_CONFIGURED':'DISABLED',
            'NO_ACTIVE_ASSIGNMENT':'DISABLED','STAFF_DISPATCH_NOT_AUTHORIZED':'DISABLED',
            'POLICY_SUPPRESSED':'DISABLED','CANCELLED_CLOSED':'DISABLED','DELIVERY_UNKNOWN':'UNKNOWN'}.get(row.get('status'),row.get('status','PENDING'))


def public_result(row):
    return {**{k:v for k,v in row.items() if k not in ('recipient_key','receipt_nonce_hash')},
            'delivery_state':delivery_state(row),'receipt_confirmed':bool(row.get('receipt_confirmed_at'))}


def ack_users():
    return {value.strip() for value in os.getenv('TELEGRAM_TEST_ACK_USER_IDS','').split(',') if value.strip().isdigit()}


def eligible(incident):
    if incident.get('level')=='CRITICAL':return True
    if incident.get('zone_type')=='PRIVATE' or incident['zone_id']=='ZONE_TOILET_BLINDSPOT':
        return incident.get('level')=='HIGH'
    order=['LOW','OBSERVE','WARNING','HIGH','CRITICAL']
    minimum=os.getenv('TELEGRAM_PUBLIC_AI_MIN_SEVERITY','OBSERVE')
    return incident.get('source')=='vision' and order.index(incident.get('level','LOW'))>=order.index(minimum if minimum in order else 'HIGH')


def _dispatch(incident,force_test=False):
    # Recheck persisted closure before retrying a queued snapshot.
    incident=storage.get('incident',incident['id']) or incident
    previous=[r for r in storage.all_rows('notification') if r['incident_id']==incident['id']]
    test=force_test or incident.get('is_test',True) or incident.get('processing_mode')!='real_model' or incident.get('source_type') not in ('LIVE CAMERA','LIVE SENSOR','LIVE SOS')
    mode='test' if test or os.getenv('TELEGRAM_MODE')=='test' else 'staff'
    route=select_route(incident)
    recipient=os.getenv('TELEGRAM_TEST_CHAT_ID','') if mode=='test' else chat_for(route)
    recipient_key=sha256(recipient.encode()).hexdigest() if recipient else None
    same=[r for r in previous if r.get('mode')==mode and r.get('recipient_key') in (None,recipient_key)]
    protected=next((r for r in reversed(same) if r['status'] in ('SENT','SENDING','DELIVERY_UNKNOWN')),None)
    if protected:return protected
    failed=sum(r['status']=='FAILED' for r in same)
    if failed>=3:return same[-1]
    row={'id':str(uuid4()),'incident_id':incident['id'],'timestamp':datetime.now(timezone.utc).isoformat(),
         'assigned_staff':route.get('staff') if route else None,'assigned_role':route.get('role') if route else None,
         'priority':incident['level'],'mode':mode,'recipient_key':recipient_key,'status':'PREVIEW',
         'recipient_masked':masked_chat(recipient),'transport_kind':transport_kind()}
    # Only allow-listed operational fields leave the backend. No names, free-form
    # reason/review text, raw sensor records, filenames, audio or private imagery.
    event_types=sorted({e.get('type') for e in incident.get('evidence',[]) if e.get('type') in ('presence','normal_motion','normal_acoustic','rapid_motion','fall','scream','impact','sos','possible_conflict')})
    text=(('SAFESENSE TEST INCIDENT' if mode=='test' else 'SAFESENSE STAFF ALERT')+' - REVIEW REQUIRED\n'
          f"Incident ID: {incident['id']}\nZone: {incident['zone_id']}\nEvent type: {', '.join(event_types) or 'Safety event'}\n"
          f"Source: {incident.get('source','unverified')} / {incident['processing_mode']} / {incident.get('source_type') or 'unverified'}\n"
          f"Timestamp: {incident['created_at']}\nSeverity: {incident['level']}\nStatus: {incident.get('status','NEW')}\n"
          'Evidence: metadata only; no private images, audio or personal details\n'
          'Action: Review and acknowledge in the authenticated SafeSense dashboard.')
    nonce=secrets.token_urlsafe(24) if mode=='test' and ack_users() else None
    row['preview']=text+('\nReceipt reply: /safesense_ack [one-time code]' if nonce else '')
    if nonce:
        row['receipt_nonce_hash']=sha256(nonce.encode()).hexdigest()
        text+='\nTo confirm receipt and acknowledge: /safesense_ack '+nonce
    cfg=status()
    if incident.get('status') in ('RESOLVED','FALSE_ALARM'):row['status']='CANCELLED_CLOSED'
    elif cfg['mode'] not in ('test','staff'):row['status']='DISABLED'
    elif mode=='staff' and not cfg['production_dispatch']:row['status']='STAFF_DISPATCH_NOT_AUTHORIZED'
    elif not os.getenv('TELEGRAM_BOT_TOKEN') or not recipient:row['status']='NOT_CONFIGURED'
    elif not route:row['status']='NO_ACTIVE_ASSIGNMENT'
    elif not force_test and not eligible(incident):row['status']='POLICY_SUPPRESSED'
    else:
        claim_id=sha256(json.dumps([incident['id'],mode,recipient_key]).encode()).hexdigest()
        # Cross-process SQLite claim: persist intent before network I/O. A crash
        # or ambiguous timeout cannot cause automatic duplicate transmission.
        with storage.connection() as db:
            db.execute('BEGIN IMMEDIATE')
            old=db.execute('SELECT body FROM records WHERE kind=? AND id=?',('notification_claim',claim_id)).fetchone()
            claim=json.loads(old[0]) if old else None
            if claim:
                saved=db.execute('SELECT body FROM records WHERE kind=? AND id=?',('notification',claim['notification_id'])).fetchone()
                if claim['status'] in ('SENT','SENDING','DELIVERY_UNKNOWN') or claim['attempts']>=3:return json.loads(saved[0])
                if claim.get('next_retry_at') and datetime.fromisoformat(claim['next_retry_at'])>datetime.now(timezone.utc):return json.loads(saved[0])
            attempts=claim['attempts']+1 if claim else failed+1
            row.update(status='SENDING',attempt=attempts)
            claim={'notification_id':row['id'],'status':'SENDING','attempts':attempts}
            db.execute('INSERT OR REPLACE INTO records VALUES (?,?,?)',('notification_claim',claim_id,json.dumps(claim)))
            db.execute('INSERT OR REPLACE INTO records VALUES (?,?,?)',('notification',row['id'],json.dumps(row)))
        retry_after=None
        def rejected(payload,code):
            nonlocal retry_after
            row.update(status='FAILED',error='Telegram explicitly rejected request',error_code=code)
            value=payload.get('parameters',{}).get('retry_after') if isinstance(payload,dict) else None
            if code==429 and isinstance(value,(int,float)) and not isinstance(value,bool) and math.isfinite(value) and value>=0:retry_after=float(value)
        try:
            request=Request('https://api.telegram.org/bot'+os.environ['TELEGRAM_BOT_TOKEN']+'/sendMessage',
                            data=json.dumps({'chat_id':recipient,'text':text}).encode(),headers={'Content-Type':'application/json'},method='POST')
            with urlopen(request,timeout=8) as response:
                row['telegram_http_status']=getattr(response,'status',None)
                result=json.load(response)
            row['telegram_api_ok']=result.get('ok') is True
            returned_chat=result.get('result',{}).get('chat',{}).get('id') if isinstance(result.get('result'),dict) else None
            row['telegram_recipient_matches']=str(returned_chat)==recipient if returned_chat is not None else None
            if result.get('ok') is False:rejected(result,result.get('error_code'))
            elif returned_chat is not None and str(returned_chat)!=recipient:row.update(status='DELIVERY_UNKNOWN',error='Telegram response recipient mismatch; acceptance for authorized chat unverified')
            elif result.get('ok') is True and type(result.get('result',{}).get('message_id')) is int and result['result']['message_id']>0:
                row.update(status='SENT',telegram_message_id=result['result']['message_id'],api_accepted_at=datetime.now(timezone.utc).isoformat())
            else:row.update(status='DELIVERY_UNKNOWN',error='Invalid Telegram response; acceptance unverified')
        except HTTPError as exc:
            row['telegram_http_status']=exc.code
            row['telegram_api_ok']=False
            try:payload=json.loads(exc.read(65536))
            except (ValueError,OSError):payload={}
            if exc.code>=500:row.update(status='DELIVERY_UNKNOWN',error='Telegram upstream error; acceptance unverified',error_code=exc.code)
            else:rejected(payload,exc.code)
            exc.close()
        except Exception as exc:row.update(status='DELIVERY_UNKNOWN',error=type(exc).__name__)
        claim.update(status=row['status'])
        if retry_after is not None:
            try:next_retry=datetime.now(timezone.utc)+timedelta(seconds=retry_after)
            except OverflowError:next_retry=datetime.max.replace(tzinfo=timezone.utc)
            row['next_retry_at']=next_retry.isoformat()
            claim['next_retry_at']=row['next_retry_at']
        storage.put('notification',row['id'],row);storage.put('notification_claim',claim_id,claim)
        logging.getLogger('uvicorn.error').info('Telegram attempt recipient=%s message_id=%s state=%s',row['recipient_masked'],row.get('telegram_message_id'),delivery_state(row))
        # Only definite 429 rejection is retried automatically. Long delays are
        # durable and require a later explicit retry; never truncate retry_after.
        if retry_after is not None and retry_after<=2 and attempts<3:
            time.sleep(retry_after)
            return _dispatch(incident,force_test)
    storage.put('notification',row['id'],row)
    return row


def verify_test_receipt(incident_id):
    with SEND_LOCK:
        return _verify_test_receipt(incident_id)


def _verify_test_receipt(incident_id):
    candidates=[r for r in storage.all_rows('notification') if r['incident_id']==incident_id and r.get('mode')=='test' and r.get('status') in ('SENT','DELIVERY_UNKNOWN')]
    if not candidates:return {'state':'NOT_API_ACCEPTED'}
    row=candidates[-1]
    if row.get('receipt_confirmed_at'):return public_result(row)
    incident=storage.get('incident',incident_id)
    route=select_route(incident) if incident else None
    if not route or route['staff']!=row.get('assigned_staff'):return {'state':'STAFF_AUTHORIZATION_CHANGED'}
    if os.getenv('TELEGRAM_MODE') not in ('test','staff') or not os.getenv('TELEGRAM_BOT_TOKEN') or not ack_users() or not row.get('receipt_nonce_hash'):
        return {'state':'RECEIPT_VERIFICATION_NOT_CONFIGURED'}
    recipient=os.getenv('TELEGRAM_TEST_CHAT_ID','')
    if not recipient or sha256(recipient.encode()).hexdigest()!=row.get('recipient_key'):return {'state':'RECIPIENT_CONFIGURATION_CHANGED'}
    try:
        request=Request('https://api.telegram.org/bot'+os.environ['TELEGRAM_BOT_TOKEN']+'/getUpdates',
                        data=json.dumps({'timeout':0,'limit':100,'allowed_updates':['message']}).encode(),headers={'Content-Type':'application/json'},method='POST')
        with urlopen(request,timeout=8) as response:result=json.load(response)
        if result.get('ok') is not True:return {'state':'RECEIPT_CHECK_FAILED'}
        for update in result.get('result',[]):
            message=update.get('message',{});actor=message.get('from',{});text=message.get('text','')
            if str(message.get('chat',{}).get('id'))!=recipient or str(actor.get('id')) not in ack_users() or actor.get('is_bot') or message.get('forward_origin'):continue
            parts=text.split() if isinstance(text,str) else []
            if len(parts)!=2 or parts[0].split('@')[0]!='/safesense_ack':continue
            if not secrets.compare_digest(sha256(parts[1].encode()).hexdigest(),row['receipt_nonce_hash']):continue
            row.update(status='SENT',receipt_confirmed_at=datetime.now(timezone.utc).isoformat(),receipt_update_id=update.get('update_id'),
                       receipt_actor_key=sha256(str(actor['id']).encode()).hexdigest(),receipt_method='authenticated_bot_update_authorized_test_user_nonce')
            row.pop('receipt_nonce_hash',None);storage.put('notification',row['id'],row)
            claim_id=sha256(json.dumps([incident_id,'test',row['recipient_key']]).encode()).hexdigest()
            claim=storage.get('notification_claim',claim_id)
            if claim and claim['notification_id']==row['id']:
                claim['status']='SENT';storage.put('notification_claim',claim_id,claim)
            return public_result(row)
        return {'state':'RECEIPT_PENDING','receipt_confirmed':False}
    except Exception as exc:return {'state':'RECEIPT_CHECK_FAILED','error':type(exc).__name__}
