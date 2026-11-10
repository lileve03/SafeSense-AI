"""Contract tests mock transport; no external Telegram messages are sent."""
from pathlib import Path
import sys,os,json,tempfile,unittest
from unittest.mock import patch
from io import BytesIO
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from backend import notifications,storage

class TelegramSafety(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.dbpatch=patch.object(storage,'DB',Path(self.temp.name)/'test.sqlite3');self.dbpatch.start()
        self.env=patch.dict(os.environ,{'TELEGRAM_MODE':'test','TELEGRAM_BOT_TOKEN':'fake-secret-never-sent','TELEGRAM_TEST_CHAT_ID':'authorized-test-chat'},clear=False);self.env.start()
        self.routepatch=patch.object(notifications,'routes',return_value=[{'zone_id':'ZONE_TOILET_BLINDSPOT','staff':'Test duty teacher','role':'duty_teacher','active':True,'chat_id_env':'TELEGRAM_TEACHER_CHAT_ID'}]);self.routepatch.start()
        self.incident={'id':'sos-1','zone_id':'ZONE_TOILET_BLINDSPOT','level':'CRITICAL','reason':'SOS test','created_at':'2026-10-28T12:00:00+00:00','processing_mode':'simulation'}
    def tearDown(self):
        self.routepatch.stop();self.env.stop();self.dbpatch.stop();self.temp.cleanup()
    def test_only_test_recipient_and_duplicate_suppression(self):
        with patch.object(notifications,'urlopen',return_value=BytesIO(b'{"ok":true,"result":{"message_id":42}}')) as transport:
            first=notifications.dispatch(self.incident);second=notifications.dispatch(self.incident)
            self.assertEqual(first['status'],'SENT');self.assertEqual(first,second)
            self.assertEqual(transport.call_count,1)
            self.assertEqual(json.loads(transport.call_args.args[0].data)['chat_id'],'authorized-test-chat')
            self.assertNotIn('fake-secret',json.dumps(storage.all_rows('notification')))
    def test_timeout_is_unknown_and_never_automatically_retried(self):
        with patch.object(notifications,'urlopen',side_effect=TimeoutError('https://api.telegram.org/botfake-secret-never-sent')) as transport:
            row=notifications.dispatch(self.incident);notifications.dispatch(self.incident)
            self.assertEqual(row['status'],'DELIVERY_UNKNOWN');self.assertEqual(transport.call_count,1)
            self.assertNotIn('fake-secret',json.dumps(row))
    def test_production_mode_cannot_send(self):
        with patch.dict(os.environ,{'TELEGRAM_MODE':'production'}),patch.object(notifications,'urlopen') as transport:
            self.assertEqual(notifications.dispatch(self.incident)['status'],'DISABLED');transport.assert_not_called()
    def test_missing_credentials_do_not_claim_success(self):
        with patch.dict(os.environ,{'TELEGRAM_BOT_TOKEN':''}),patch.object(notifications,'urlopen') as transport:
            self.assertEqual(notifications.dispatch(self.incident)['status'],'NOT_CONFIGURED');transport.assert_not_called()
    def test_inactive_route_does_not_send(self):
        with patch.object(notifications,'routes',return_value=[]),patch.object(notifications,'urlopen') as transport:
            self.assertEqual(notifications.dispatch(self.incident)['status'],'NO_ACTIVE_ASSIGNMENT');transport.assert_not_called()

    def live(self,private=False):
        return {**self.incident,'is_test':False,'source_type':'LIVE SOS' if private else 'LIVE CAMERA','processing_mode':'real_model',
                'zone_id':'ZONE_TOILET_BLINDSPOT' if private else 'ZONE_CORRIDOR_A','zone_type':'PRIVATE' if private else 'OPEN_HIDDEN','status':'NEW'}

    def response(self,*args,**kwargs):return BytesIO(b'{"ok":true,"result":{"message_id":42}}')

    def test_authorized_live_public_alert_routes_to_configured_staff(self):
        route={'zone_id':'ZONE_CORRIDOR_A','staff':'On-duty security','role':'security','active':True,'chat_id_env':'TELEGRAM_SECURITY_CHAT_ID'}
        with patch.dict(os.environ,{'TELEGRAM_MODE':'staff','TELEGRAM_STAFF_DISPATCH_ENABLED':'true','TELEGRAM_SECURITY_CHAT_ID':'authorized-security'}),patch.object(notifications,'routes',return_value=[route]),patch.object(notifications,'urlopen',side_effect=self.response) as transport:
            result=notifications.dispatch(self.live())
            self.assertEqual(result['status'],'SENT');self.assertEqual(result['mode'],'staff')
            self.assertEqual(json.loads(transport.call_args.args[0].data)['chat_id'],'authorized-security')
            self.assertNotIn('authorized-security',json.dumps(result))

    def test_private_sos_requires_assigned_teacher_not_security(self):
        routes=[{'zone_id':'ZONE_TOILET_BLINDSPOT','staff':'Security','role':'security','active':True,'priority':1,'chat_id_env':'TELEGRAM_SECURITY_CHAT_ID'},
                {'zone_id':'ZONE_TOILET_BLINDSPOT','staff':'Duty teacher','role':'teacher','active':True,'priority':50,'chat_id_env':'TELEGRAM_TEACHER_CHAT_ID'}]
        with patch.dict(os.environ,{'TELEGRAM_MODE':'staff','TELEGRAM_STAFF_DISPATCH_ENABLED':'true','TELEGRAM_TEACHER_CHAT_ID':'assigned-teacher','TELEGRAM_SECURITY_CHAT_ID':'security'}),patch.object(notifications,'routes',return_value=routes),patch.object(notifications,'urlopen',side_effect=self.response) as transport:
            result=notifications.dispatch(self.live(private=True))
            self.assertEqual(result['assigned_staff'],'Duty teacher')
            payload=json.loads(transport.call_args.args[0].data)
            self.assertEqual(payload['chat_id'],'assigned-teacher');self.assertEqual(set(payload),{'chat_id','text'})

    def test_staff_mode_does_not_send_without_explicit_enable(self):
        with patch.dict(os.environ,{'TELEGRAM_MODE':'staff','TELEGRAM_STAFF_DISPATCH_ENABLED':'false'}),patch.object(notifications,'urlopen') as transport:
            self.assertEqual(notifications.dispatch(self.live())['status'],'STAFF_DISPATCH_NOT_AUTHORIZED');transport.assert_not_called()

    def test_recorded_real_model_cannot_reach_staff_chat(self):
        incident={**self.live(private=True),'source_type':'RECORDED REAL VIDEO','is_test':False}
        with patch.dict(os.environ,{'TELEGRAM_MODE':'staff','TELEGRAM_STAFF_DISPATCH_ENABLED':'true','TELEGRAM_TEACHER_CHAT_ID':'never-this-chat'}),patch.object(notifications,'urlopen',side_effect=self.response) as transport:
            result=notifications.dispatch(incident)
            self.assertEqual(result['mode'],'test')
            self.assertEqual(json.loads(transport.call_args.args[0].data)['chat_id'],'authorized-test-chat')

    def test_force_test_cannot_reach_staff_recipient(self):
        with patch.dict(os.environ,{'TELEGRAM_MODE':'staff','TELEGRAM_STAFF_DISPATCH_ENABLED':'true','TELEGRAM_TEACHER_CHAT_ID':'never-this-chat'}),patch.object(notifications,'urlopen',side_effect=self.response) as transport:
            result=notifications.dispatch(self.live(private=True),force_test=True)
            self.assertEqual(result['mode'],'test');self.assertEqual(json.loads(transport.call_args.args[0].data)['chat_id'],'authorized-test-chat')

    def test_no_test_chat_does_not_fall_back_to_staff(self):
        with patch.dict(os.environ,{'TELEGRAM_MODE':'staff','TELEGRAM_STAFF_DISPATCH_ENABLED':'true','TELEGRAM_TEST_CHAT_ID':'','TELEGRAM_TEACHER_CHAT_ID':'never-this-chat'}),patch.object(notifications,'urlopen') as transport:
            self.assertEqual(notifications.dispatch(self.incident)['status'],'NOT_CONFIGURED');transport.assert_not_called()

    def test_shift_expiry_selects_active_backup(self):
        routes=[{'zone_id':'ZONE_TOILET_BLINDSPOT','staff':'Expired teacher','role':'teacher','active':True,'shift_start':'2020-01-01T00:00:00Z','shift_end':'2020-01-02T00:00:00Z'},
                {'zone_id':'ZONE_TOILET_BLINDSPOT','staff':'Backup teacher','role':'teacher','active':True,'is_backup':True}]
        with patch.object(notifications,'routes',return_value=routes):self.assertEqual(notifications.select_route(self.incident)['staff'],'Backup teacher')

    def test_closed_incident_does_not_send(self):
        with patch.object(notifications,'urlopen') as transport:
            self.assertEqual(notifications.dispatch({**self.incident,'status':'RESOLVED'})['status'],'CANCELLED_CLOSED');transport.assert_not_called()

if __name__=='__main__':unittest.main(verbosity=2)
