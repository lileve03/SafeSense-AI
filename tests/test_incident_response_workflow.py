"""Isolated workflow/dispatch tests. All Telegram HTTP calls are mocked."""
from pathlib import Path
import os,sys,tempfile,json,unittest
from io import BytesIO
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from backend import main,storage,notifications
from fastapi.testclient import TestClient

class IncidentWorkflow(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.db=patch.object(storage,'DB',Path(self.temp.name)/'test.sqlite3');self.db.start()
        self.env=patch.dict(os.environ,{'TELEGRAM_MODE':'test','TELEGRAM_BOT_TOKEN':'fake-test-token','TELEGRAM_TEST_CHAT_ID':'only-authorized-test-chat'});self.env.start()
        self.routes=patch.object(notifications,'routes',return_value=[{'zone_id':'ZONE_CORRIDOR_A','staff':'Duty security','role':'security','active':True},
            {'zone_id':'ZONE_TOILET_BLINDSPOT','staff':'Duty teacher','role':'teacher','active':True}]);self.routes.start()
        self.transport=patch.object(notifications,'urlopen',side_effect=lambda *a,**k:BytesIO(b'{"ok":true,"result":{"message_id":88}}'));self.sent=self.transport.start()
        self.ingest=patch.object(main,'INGEST_TOKEN','isolated-ingest-test-key');self.ingest.start()
        with main._lock:main._incidents.clear();main._events.clear()
        self.client=TestClient(main.app,headers={'X-SafeSense-Token':main.TOKEN,'X-SafeSense-Ingest-Token':'isolated-ingest-test-key'})
    def tearDown(self):
        self.flush();self.client.close();self.ingest.stop();self.transport.stop();self.routes.stop();self.env.stop();self.db.stop();self.temp.cleanup()
    def flush(self):main._notify_pool.submit(lambda:None).result(timeout=15)
    def incident(self,private=False,**extra):
        event={'zone':'ZONE_TOILET_BLINDSPOT' if private else 'ZONE_CORRIDOR_A','type':'sos' if private else 'possible_conflict',
               'source':'sos_button' if private else 'vision','processing_mode':'real_model',**extra}
        response=self.client.post('/event',json=event);self.assertEqual(response.status_code,200,response.text)
        self.flush();return response.json()['incident']['id']
    def report(self,id):return self.client.get('/incidents/'+id+'/report').json()
    def test_public_candidate_auto_notification_ack_resolve_report(self):
        identifier=self.incident(model_version='v3',score=.91,evidence_reference='test metadata fixture; actual clips tested in real integration')
        report=self.report(identifier)
        self.assertEqual(report['assigned_staff'],'Duty security');self.assertEqual(report['notifications'][-1]['status'],'SENT')
        self.assertEqual(report['notifications'][-1]['mode'],'test')
        zone=next(z for z in self.client.get('/zones').json() if z['id']=='ZONE_CORRIDOR_A');self.assertIn(identifier,zone['active_incident_ids'])
        self.assertEqual(self.client.post(f'/incidents/{identifier}/review',json={'status':'RESOLVED','note':'test'}).status_code,409)
        ack=self.client.post(f'/incidents/{identifier}/ack',json={'staff':'Review operator'}).json()
        repeat=self.client.post(f'/incidents/{identifier}/ack',json={'staff':'Other actor'}).json()
        self.assertEqual(ack['acknowledged_at'],repeat['acknowledged_at'])
        self.assertEqual(self.client.post(f'/incidents/{identifier}/review',json={'status':'RESOLVED','note':'Reviewed actual source; test completed','staff':'Review operator'}).status_code,200)
        report=self.report(identifier)
        self.assertEqual(report['status'],'RESOLVED');self.assertEqual(report['acknowledged_by'],'Review operator')
        self.assertIsNotNone(report['analysis']['resolution_seconds']);self.assertEqual(report['analysis']['model_versions'],['v3'])
        self.assertTrue(any(h['status']=='NOTIFICATION_SENT' for h in report['history']))
        self.assertEqual(report['assigned_staff'],'Duty security')
        zone=next(z for z in self.client.get('/zones').json() if z['id']=='ZONE_CORRIDOR_A');self.assertNotIn(identifier,zone['active_incident_ids'])
    def test_private_sos_assigns_teacher_without_vision(self):
        identifier=self.incident(private=True);report=self.report(identifier)
        self.assertEqual(report['assigned_staff'],'Duty teacher');self.assertEqual(report['level'],'CRITICAL')
        self.assertEqual(report['analysis']['evidence_clip_count'],0)
        self.assertEqual(json.loads(self.sent.call_args.args[0].data)['chat_id'],'only-authorized-test-chat')
    def test_terminal_state_cannot_reopen(self):
        identifier=self.incident()
        self.client.post(f'/incidents/{identifier}/review',json={'status':'FALSE_ALARM','note':'Reviewed benign'})
        self.assertEqual(self.client.post(f'/incidents/{identifier}/review',json={'status':'VERIFIED'}).status_code,409)
        self.assertEqual(self.client.post(f'/incidents/{identifier}/ack',json={'staff':'Operator'}).status_code,409)
    def test_assignment_must_match_configured_duty_staff(self):
        identifier=self.incident()
        self.assertEqual(self.client.post(f'/incidents/{identifier}/review',json={'status':'DISPATCHED','staff':'Invented responder'}).status_code,422)
    def test_recorded_and_live_provenance_cannot_coalesce(self):
        recorded=self.incident(source_type='RECORDED REAL VIDEO',is_test=False)
        live=self.incident(source_type='LIVE CAMERA',is_test=False)
        self.assertNotEqual(recorded,live)
        self.assertTrue(self.report(recorded)['is_test']);self.assertFalse(self.report(live)['is_test'])
    def test_duplicate_event_does_not_send_twice(self):
        identifier=self.incident(event_id='stable-analysis')
        again=self.incident(event_id='stable-analysis')
        self.assertEqual(identifier,again);self.assertEqual(self.sent.call_count,1)
    def test_queued_request_recovery_preserves_delivery_dedup(self):
        identifier=self.incident()
        storage.put('notification_request','recovery-fixture',{'id':'recovery-fixture','incident_id':identifier,'status':'QUEUED'})
        main.recover_notifications();self.flush();self.assertEqual(self.sent.call_count,1)
        self.assertEqual(next(r for r in storage.all_rows('notification_request') if r['id']=='recovery-fixture')['status'],'RECOVERED')
    def test_dashboard_token_cannot_forge_live_staff_delivery(self):
        response=self.client.post('/event',json={'zone':'ZONE_CORRIDOR_A','type':'possible_conflict','source':'vision','processing_mode':'real_model','source_type':'LIVE CAMERA','is_test':False},headers={'X-SafeSense-Ingest-Token':''})
        self.assertEqual(response.status_code,403);self.sent.assert_not_called()
    def test_malformed_public_evidence_is_rejected(self):
        response=self.client.post('/event',json={'zone':'ZONE_CORRIDOR_A','type':'possible_conflict','source':'vision','evidence_media':[{'url':'../../private.mp4'}]})
        self.assertEqual(response.status_code,422);self.sent.assert_not_called()
    def test_manual_test_status_synchronizes_with_incident_state(self):
        with patch.dict(os.environ,{'TELEGRAM_MODE':'disabled'}):identifier=self.incident()
        response=self.client.post(f'/incidents/{identifier}/notify-test',json={});self.assertEqual(response.json()['status'],'SENT')
        state=next(i for i in self.client.get('/state').json()['incidents'] if i['id']==identifier)
        self.assertEqual(state['notification_status'],'SENT')

if __name__=='__main__':unittest.main(verbosity=2)
