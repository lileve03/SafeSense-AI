"""Real FastAPI/SQLite workflow with explicitly mocked Telegram HTTPS transport."""
from pathlib import Path
import os,sys,json,tempfile,unittest
from io import BytesIO
from unittest.mock import patch
from urllib.error import HTTPError
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from backend import main,notifications,storage
from fastapi.testclient import TestClient

class VerifiedTelegram(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.db=patch.object(storage,'DB',Path(self.temp.name)/'test.sqlite3');self.db.start()
  self.env=patch.dict(os.environ,{'TELEGRAM_MODE':'test','TELEGRAM_BOT_TOKEN':'fake-private-token','TELEGRAM_TEST_CHAT_ID':'-100123','TELEGRAM_TEST_ACK_USER_IDS':'42'});self.env.start()
  self.route={'zone_id':'ZONE_TOILET_BLINDSPOT','staff':'Authorized test teacher','role':'teacher','active':True}
  self.routes=patch.object(notifications,'routes',return_value=[self.route]);self.routes.start()
  self.sent=[];self.updates=[]
  self.transport=patch.object(notifications,'urlopen',side_effect=self.telegram);self.transport.start()
  with main._lock:main._events.clear();main._incidents.clear()
  self.client=TestClient(main.app,headers={'X-SafeSense-Token':main.TOKEN})
 def telegram(self,request,**kwargs):
  if request.full_url.endswith('/getUpdates'):return BytesIO(json.dumps({'ok':True,'result':self.updates}).encode())
  self.sent.append(json.loads(request.data));return BytesIO(b'{"ok":true,"result":{"message_id":123}}')
 def flush(self):main._notify_pool.submit(lambda:None).result(timeout=15)
 def tearDown(self):
  self.flush();self.client.close();self.transport.stop();self.routes.stop();self.env.stop();self.db.stop();self.temp.cleanup()
 def sos(self):
  r=self.client.post('/event',json={'zone':'ZONE_TOILET_BLINDSPOT','type':'sos','source':'sos_button','processing_mode':'simulation','event_id':'confirmed-test-sos'})
  self.assertEqual(r.status_code,200,r.text);self.flush();return r.json()['incident']['id']
 def report(self,id):return self.client.get('/incidents/'+id+'/report').json()
 def update(self,nonce,chat=-100123,user=42):return {'update_id':99,'message':{'chat':{'id':chat},'from':{'id':user,'is_bot':False},'text':'/safesense_ack '+nonce}}
 def nonce(self):return self.sent[-1]['text'].split('/safesense_ack ')[-1]
 def test_backend_only_test_action_is_authorized_and_idempotent(self):
  from uuid import uuid4
  body={'request_id':str(uuid4()),'authorized':True}
  result=self.client.post('/notifications/send-test',json=body)
  self.assertEqual(result.status_code,200,result.text);self.flush()
  first=result.json();self.assertEqual(first['notification']['delivery_state'],'API_ACCEPTED')
  self.assertFalse(first['receipt_verified']);self.assertEqual(len(self.sent),1)
  second=self.client.post('/notifications/send-test',json=body).json()
  self.assertTrue(second['event_deduplicated']);self.assertEqual(second['incident_id'],first['incident_id']);self.assertEqual(len(self.sent),1)
  self.assertEqual(self.sent[0]['chat_id'],'-100123')
  self.assertEqual(TestClient(main.app).post('/notifications/send-test',json=body).status_code,401)
  body['authorized']=False;self.assertEqual(self.client.post('/notifications/send-test',json=body).status_code,403)
 def test_test_action_rejects_staff_mode_and_missing_route(self):
  from uuid import uuid4
  body={'request_id':str(uuid4()),'authorized':True}
  with patch.dict(os.environ,{'TELEGRAM_MODE':'staff'}):self.assertEqual(self.client.post('/notifications/send-test',json=body).status_code,409)
  with patch.object(notifications,'routes',return_value=[]):self.assertEqual(self.client.post('/notifications/send-test',json=body).status_code,409)
  self.assertEqual(len(self.sent),0)
 def test_legacy_sent_label_is_not_api_acceptance(self):
  self.assertEqual(notifications.delivery_state({'status':'SENT'}),'UNKNOWN')
  self.assertEqual(notifications.delivery_state({'status':'SENT','telegram_api_ok':False,'telegram_message_id':123}),'UNKNOWN')
 def test_response_recipient_mismatch_is_unknown_and_never_retried(self):
  with patch.object(notifications,'urlopen',return_value=BytesIO(b'{"ok":true,"result":{"message_id":124,"chat":{"id":999}}}')) as transport:
   id=self.sos();self.assertEqual(self.report(id)['notification_state'],'UNKNOWN')
   self.client.post('/incidents/'+id+'/notify-test',json={});self.assertEqual(transport.call_count,1)
 def test_status_and_logs_only_expose_masked_recipient(self):
  status=notifications.status();self.assertEqual(status['test_recipient_masked'],'-***0123')
  self.assertNotIn('-100123',json.dumps(status));self.assertNotIn('fake-private-token',json.dumps(status))
 def test_all_zone_test_sos_uses_test_operator_fallback(self):
  self.route.update(role='test_operator',test_only=True)
  response=self.client.post('/event',json={'zone':'ZONE_CANTEEN','type':'sos','source':'simulation','processing_mode':'simulation'})
  self.assertEqual(response.status_code,200,response.text);self.flush()
  self.assertEqual(len(self.sent),1)
  self.assertIn('ZONE_CANTEEN',self.sent[0]['text'])
  self.assertIsNone(notifications.select_route({'zone_id':'ZONE_CANTEEN','is_test':False,'source_type':'LIVE SOS','evidence':[{'type':'sos'}]}))
 def test_tracking_fusion_and_sos_each_send_once(self):
  from uuid import uuid4
  body={'session_id':str(uuid4()),'time_sec':10.5,'kind':'fusion'}
  for kind in ('fusion','sos'):
   body['kind']=kind
   for repeat in range(2):
    response=self.client.post('/testing/radar-simulation/events',json=body)
    self.assertEqual(response.status_code,200,response.text);self.flush()
  self.assertEqual(len(self.sent),2)
 def test_sos_sqlite_acceptance_is_not_receipt(self):
  id=self.sos();r=self.report(id)
  self.assertEqual(r['notification_state'],'API_ACCEPTED');self.assertEqual(r['assigned_staff'],'Authorized test teacher')
  self.assertFalse(r['notifications'][-1]['receipt_confirmed']);self.assertEqual(r['status'],'NEW')
  self.assertNotIn('receipt_nonce_hash',json.dumps(r));self.assertNotIn(self.nonce(),json.dumps(r));self.assertNotIn('fake-private-token',json.dumps(r))
 def test_verified_telegram_reply_acknowledges_existing_test_incident(self):
  id=self.sos();self.updates=[self.update(self.nonce())]
  r=self.client.post('/incidents/'+id+'/verify-test-receipt',json={});self.assertEqual(r.json()['delivery_state'],'RECEIPT_CONFIRMED')
  report=self.report(id);self.assertEqual(report['status'],'ACKNOWLEDGED');self.assertEqual(report['notification_state'],'RECEIPT_CONFIRMED')
  self.assertEqual(report['acknowledged_by'],'Authorized test teacher');self.assertEqual(len(self.sent),1)
  again=self.client.post('/incidents/'+id+'/verify-test-receipt',json={}).json();self.assertEqual(r.json()['receipt_confirmed_at'],again['receipt_confirmed_at'])
 def test_wrong_chat_user_nonce_and_unsigned_request_cannot_confirm(self):
  id=self.sos();nonce=self.nonce()
  for update in [self.update(nonce,chat=-999),self.update(nonce,user=99),self.update('wrong')]:
   self.updates=[update];result=self.client.post('/incidents/'+id+'/verify-test-receipt',json={'update':self.update(nonce)}).json()
   self.assertEqual(result['state'],'RECEIPT_PENDING');self.assertEqual(self.report(id)['status'],'NEW')
  self.assertEqual(TestClient(main.app).post('/incidents/'+id+'/verify-test-receipt').status_code,401)
 def test_staff_authorization_revocation_blocks_confirmation(self):
  id=self.sos();self.updates=[self.update(self.nonce())]
  with patch.object(notifications,'routes',return_value=[]):
   self.assertEqual(self.client.post('/incidents/'+id+'/verify-test-receipt').json()['state'],'STAFF_AUTHORIZATION_CHANGED')
  self.assertEqual(self.report(id)['status'],'NEW')
 def test_duplicate_event_manual_send_and_severity_change_do_not_duplicate(self):
  id=self.sos();self.sos();self.client.post('/incidents/'+id+'/notify-test',json={})
  incident=storage.get('incident',id);incident['level']='HIGH';storage.put('incident',id,incident)
  notifications.dispatch(incident,True);self.assertEqual(len(self.sent),1)
 def test_private_payload_is_whitelisted(self):
  id=self.sos();incident=storage.get('incident',id);incident.update(id='privacy-test',reason='Student Alice raw/audio/private.wav secret-description')
  notifications.dispatch(incident,True);text=self.sent[-1]['text']
  for value in ('Student Alice','private.wav','secret-description','Authorized test teacher','View Incident','http://127.0.0.1'):self.assertNotIn(value,text)
  for value in ('Incident ID:','Zone:','Event type: sos','Source:','Timestamp:','Severity:','Status:'):self.assertIn(value,text)
 def test_unknown_timeout_never_retries(self):
  with patch.object(notifications,'urlopen',side_effect=TimeoutError('fake-private-token')) as send:
   id=self.sos();self.client.post('/incidents/'+id+'/notify-test');self.assertEqual(send.call_count,1)
  self.assertEqual(self.report(id)['notification_state'],'UNKNOWN')
 def test_authorized_reply_can_resolve_unknown_without_resending(self):
  def accepted_but_response_lost(request,**kwargs):
   self.sent.append(json.loads(request.data));raise TimeoutError('response lost')
  with patch.object(notifications,'urlopen',side_effect=accepted_but_response_lost):id=self.sos()
  self.assertEqual(self.report(id)['notification_state'],'UNKNOWN')
  self.updates=[self.update(self.nonce())]
  result=self.client.post('/incidents/'+id+'/verify-test-receipt').json()
  self.assertEqual(result['delivery_state'],'RECEIPT_CONFIRMED');self.assertNotIn('telegram_message_id',result)
  self.assertEqual(len(self.sent),1);self.assertEqual(self.report(id)['status'],'ACKNOWLEDGED')
 def test_429_safe_retry_is_bounded_to_three(self):
  payload={'ok':False,'error_code':429,'parameters':{'retry_after':0}}
  with patch.object(notifications,'urlopen',side_effect=lambda *a,**k:BytesIO(json.dumps(payload).encode())) as send:
   id=self.sos();self.client.post('/incidents/'+id+'/notify-test');self.assertEqual(send.call_count,3)
  self.assertEqual(len(self.report(id)['notifications']),3);self.assertEqual(self.report(id)['notification_state'],'FAILED')
 def test_long_retry_after_is_recorded_not_shortened(self):
  payload={'ok':False,'error_code':429,'parameters':{'retry_after':172800}}
  with patch.object(notifications,'urlopen',side_effect=lambda *a,**k:BytesIO(json.dumps(payload).encode())) as send:
   id=self.sos();self.client.post('/incidents/'+id+'/notify-test');self.assertEqual(send.call_count,1)
  self.assertIn('next_retry_at',self.report(id)['notifications'][-1])
 def test_upstream_5xx_is_unknown_not_blindly_resent(self):
  def failed(*a,**k):raise HTTPError('https://redacted',502,'Bad gateway',{},BytesIO(b'{}'))
  with patch.object(notifications,'urlopen',side_effect=failed) as send:
   id=self.sos();self.client.post('/incidents/'+id+'/notify-test');self.assertEqual(send.call_count,1)
  self.assertEqual(self.report(id)['notification_state'],'UNKNOWN')
 def test_policy_private_single_signal_waits_for_high_fusion(self):
  r=self.client.post('/event',json={'zone':'ZONE_TOILET_BLINDSPOT','type':'fall','source':'simulation','sensor_modality':'radar'});self.flush()
  self.assertEqual(self.report(r.json()['incident']['id'])['notifications'][-1]['status'],'POLICY_SUPPRESSED');self.assertEqual(len(self.sent),0)
  r=self.client.post('/event',json={'zone':'ZONE_TOILET_BLINDSPOT','type':'scream','source':'simulation','sensor_modality':'acoustic'});self.flush()
  self.assertEqual(r.json()['incident']['level'],'HIGH');self.assertEqual(len(self.sent),1)
 def test_disabled_and_missing_setup_do_not_call_telegram(self):
  with patch.dict(os.environ,{'TELEGRAM_MODE':'disabled'}):
   id=self.sos();self.assertEqual(self.report(id)['notification_state'],'DISABLED');self.assertEqual(len(self.sent),0)
  with patch.dict(os.environ,{'TELEGRAM_BOT_TOKEN':''}):self.assertIn('TELEGRAM_BOT_TOKEN',notifications.status()['missing_setup'])
 def test_authorized_test_operator_route_sends_only_test_sos(self):
  route={'zone_id':'ZONE_TOILET_BLINDSPOT','staff':'Authorized TEST recipient','role':'test_operator','test_only':True,'active':True}
  with patch.object(notifications,'routes',return_value=[route]):
   id=self.sos();self.assertEqual(self.report(id)['notification_state'],'API_ACCEPTED');self.assertEqual(len(self.sent),1)
   self.assertIsNone(notifications.select_route({'zone_id':'ZONE_TOILET_BLINDSPOT','is_test':False,'source_type':'LIVE SOS'}))
   with patch.dict(os.environ,{'TELEGRAM_MODE':'staff'}):
    self.assertIsNone(notifications.select_route({'zone_id':'ZONE_TOILET_BLINDSPOT','is_test':True}))
 def test_sqlite_claim_blocks_resend_even_without_attempt_list(self):
  id=self.sos();incident=storage.get('incident',id)
  with patch.object(storage,'all_rows',return_value=[]):notifications.dispatch(incident,True)
  self.assertEqual(len(self.sent),1)
 def test_pending_is_distinct_before_transport_runs(self):
  captured=[]
  with patch.object(main._notify_pool,'submit',side_effect=lambda fn:captured.append(fn)):
   r=self.client.post('/event',json={'zone':'ZONE_TOILET_BLINDSPOT','type':'sos','source':'sos_button','processing_mode':'simulation'})
  id=r.json()['incident']['id'];self.assertEqual(self.report(id)['notification_state'],'PENDING')
  captured[0]();self.assertEqual(self.report(id)['notification_state'],'API_ACCEPTED')
 def test_backend_secrets_are_not_in_frontend_service_environment(self):
  from scripts.start_services import service_environment
  env={'TELEGRAM_BOT_TOKEN':'fake-private-token','TELEGRAM_TEST_CHAT_ID':'-100123','SAFESENSE_INGEST_TOKEN':'server-only','VITE_API_BASE_URL':'http://local'}
  front=service_environment('dashboard',env)
  self.assertEqual(front,{'VITE_API_BASE_URL':'http://local'})
  self.assertEqual(service_environment('backend',env),env)
 def test_concurrent_dispatch_uses_persistent_claim_not_only_process_lock(self):
  from concurrent.futures import ThreadPoolExecutor
  from uuid import uuid4
  id=self.sos();incident=storage.get('incident',id);incident['id']=str(uuid4());storage.put('incident',incident['id'],incident)
  with patch.object(notifications,'urlopen',side_effect=self.telegram) as transport,ThreadPoolExecutor(max_workers=2) as pool:
   results=list(pool.map(lambda _:notifications._dispatch(incident,True),range(2)))
   self.assertEqual(transport.call_count,1)
   self.assertEqual(results[0]['id'],results[1]['id'])

if __name__=='__main__':unittest.main(verbosity=2)
