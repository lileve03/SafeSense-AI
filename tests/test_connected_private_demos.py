"""Canonical endpoint tests, isolated data and disabled external notifications."""
import os,sys,tempfile,unittest,time
from pathlib import Path
from uuid import uuid4
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
TEMP=tempfile.TemporaryDirectory()
os.environ.update(SAFESENSE_DB_PATH=str(Path(TEMP.name)/'initial.sqlite3'),TELEGRAM_MODE='disabled',TELEGRAM_STAFF_DISPATCH_ENABLED='false')
from backend import main,storage,notifications
from fastapi.testclient import TestClient

class ConnectedPrivateDemoTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.db=patch.object(storage,'DB',Path(self.temp.name)/'test.sqlite3');self.db.start()
        with main._lock:main._events.clear();main._incidents.clear()
        self.client=TestClient(main.app,headers={'X-SafeSense-Token':main.TOKEN});self.group='private-demo:'+str(uuid4())
    def tearDown(self):
        main._notify_pool.submit(lambda:None).result(timeout=10)
        self.client.close();self.db.stop();self.temp.cleanup()
    def payload(self,kind,modality,group=None,**extra):
        group=group or self.group
        return dict(zone='ZONE_TOILET_BLINDSPOT',type=kind,source='simulation',sensor_modality=modality,
                    processing_mode='simulation',source_type='SIMULATION',is_test=True,score=None,model_version=None,
                    confidence=0 if kind=='sos' else 1,event_id=group+':'+kind,analysis_run_id=group,
                    evidence_reference='SIMULATED connected test; not proof of fighting or bullying; no hardware',**extra)
    def send(self,kind,modality,group=None):
        response=self.client.post('/event',json=self.payload(kind,modality,group))
        self.assertEqual(response.status_code,200,response.text);return response.json()
    def test_normal_presence_and_proximity_do_not_invent_danger_incidents(self):
        for kind,modality in [('presence','radar'),('normal_acoustic','acoustic')]:
            result=self.send(kind,modality);self.assertEqual(result['event']['level'],'LOW');self.assertIsNone(result['incident'])
        self.assertFalse(self.client.get('/incidents').json())
    def test_repetitive_motion_is_observe_not_verified_danger(self):
        result=self.send('rapid_motion','radar');incident=result['incident']
        self.assertEqual(incident['level'],'OBSERVE');self.assertEqual(incident['status'],'NEW')
        self.assertEqual(incident['review_status'],'pending_human_review');self.assertTrue(incident['is_test'])
        self.assertIsNone(incident['score']);self.assertIsNone(incident['model_version'])
    def test_fall_plus_impact_uses_existing_fusion_and_one_incident(self):
        fall=self.send('fall','radar');impact=self.send('impact','acoustic')
        self.assertEqual(fall['incident']['id'],impact['incident']['id']);self.assertEqual(impact['incident']['level'],'HIGH')
        self.assertEqual({e['type'] for e in impact['incident']['evidence']},{'fall','impact'})
        self.assertIn('corroborated',impact['incident']['reason'])
        for _ in range(3):
            self.assertTrue(self.send('fall','radar')['deduplicated']);self.assertTrue(self.send('impact','acoustic')['deduplicated'])
        self.assertEqual(len(storage.all_rows('incident')),1);self.assertEqual(len(storage.all_rows('event')),2)
    def test_delayed_same_run_aggregates_without_fabricating_fusion(self):
        first=self.send('fall','radar')
        main._events[-1]['_monotonic']=float('-inf');main._incidents[-1]['_monotonic']=float('-inf')
        second=self.send('impact','acoustic')
        self.assertEqual(first['incident']['id'],second['incident']['id']);self.assertEqual(second['incident']['level'],'OBSERVE')
        self.assertEqual(len(storage.all_rows('incident')),1);self.assertEqual(len(second['incident']['evidence']),2)
    def test_cross_run_evidence_cannot_corroborate(self):
        self.send('fall','radar');result=self.send('impact','acoustic','private-demo:'+str(uuid4()))
        self.assertEqual(result['incident']['level'],'OBSERVE');self.assertEqual(len(storage.all_rows('incident')),2)
    def test_sos_is_direct_help_even_at_zero_model_confidence(self):
        with patch.object(main,'MIN_CONF',1):result=self.send('sos','sos')
        self.assertEqual(result['incident']['level'],'CRITICAL');self.assertEqual(result['event']['confidence'],0)
        self.assertIn('help request',result['incident']['reason']);self.assertIsNone(result['incident']['score'])
    def test_timestamp_window_and_provenance_are_required_for_fusion(self):
        from datetime import datetime, timezone, timedelta
        base=datetime.now(timezone.utc)-timedelta(seconds=8)
        for offset,source_type,expected in [(8,'SIMULATION','OBSERVE'),(1,'RECORDED SENSOR REPLAY','OBSERVE'),(1,'SIMULATION','HIGH')]:
            group='private-demo:'+str(uuid4())
            first=self.payload('fall','radar',group,observed_at=base.isoformat())
            self.assertEqual(self.client.post('/event',json=first).status_code,200)
            second={**self.payload('impact','acoustic',group,observed_at=(base+timedelta(seconds=offset)).isoformat()),'source_type':source_type}
            result=self.client.post('/event',json=second)
            self.assertEqual(result.status_code,200,result.text)
            self.assertEqual(result.json()['event']['level'],expected)
    def test_acoustic_only_and_radar_only_remain_observe(self):
        for kind,modality in [('scream','acoustic'),('fall','radar')]:
            result=self.send(kind,modality,'private-demo:'+str(uuid4()))
            self.assertEqual(result['event']['level'],'OBSERVE')
    def test_expired_capture_is_saved_without_escalation(self):
        from datetime import datetime, timezone, timedelta
        body=self.payload('fall','radar',observed_at=(datetime.now(timezone.utc)-timedelta(seconds=60)).isoformat())
        result=self.client.post('/event',json=body).json()
        self.assertEqual(result['event']['level'],'LOW');self.assertIsNone(result['incident'])
    def test_wrong_modalities_and_cross_zone_cannot_fuse(self):
        self.send('fall','acoustic')
        self.assertEqual(self.send('impact','radar')['event']['level'],'OBSERVE')
        group='private-demo:'+str(uuid4());self.send('fall','radar',group)
        result=self.client.post('/event',json={**self.payload('impact','acoustic',group),'zone':'ZONE_CORRIDOR_A'}).json()
        self.assertEqual(result['event']['level'],'OBSERVE')
    def test_notification_queue_full_reports_failed(self):
        with patch.object(main._notify_slots,'acquire',return_value=False):
            identifier=self.send('sos','sos')['incident']['id']
        self.assertEqual(self.client.get('/incidents/'+identifier+'/report').json()['notification_state'],'FAILED')
    def test_normalized_scenario_is_single_ingestion_path_and_durable_retry(self):
        from datetime import datetime, timezone
        body=dict(observation_id='part4-'+str(uuid4()),source_mode='SIMULATION',device_id='part4-test',
                  zone_id='ZONE_TOILET_BLINDSPOT',tracking_session_id=self.group,timestamp=datetime.now(timezone.utc).isoformat(),
                  data_validity='VALID',radar_event='fall',acoustic_events=[dict(kind='impact',confidence=1)])
        first=self.client.post('/sensors/observations',json=body)
        self.assertEqual(first.status_code,200,first.text)
        events=first.json()['events'];identifier=events[-1]['incident']['id']
        self.assertEqual(events[-1]['event']['level'],'HIGH')
        self.assertEqual(events[0]['incident']['id'],identifier)
        self.assertEqual(len(storage.all_rows('incident')),1)
        self.assertTrue(all(e['event']['observed_at'] for e in events))
        with patch('backend.sensor_observations.datetime') as clock:
            from datetime import timedelta
            clock.now.return_value=datetime.now(timezone.utc)+timedelta(seconds=30)
            repeated=self.client.post('/sensors/observations',json=body)
        self.assertEqual(repeated.status_code,200,repeated.text)
        self.assertTrue(all(e['deduplicated'] for e in repeated.json()['events']))
        self.assertEqual(len(storage.all_rows('event')),2)
    def test_response_states_map_alerts_and_review_share_canonical_incident(self):
        identifier=self.send('sos','sos')['incident']['id']
        self.assertEqual(self.client.post('/incidents/'+identifier+'/review',json={'status':'RESOLVED','note':'premature'}).status_code,409)
        for endpoint,body,status in [('ack',{'staff':'Test reviewer'},'ACKNOWLEDGED'),
              ('review',{'status':'VERIFIED','staff':'Test reviewer','note':'Human reviewed simulation only'},'VERIFIED'),
              ('review',{'status':'RESOLVED','staff':'Test reviewer','note':'Test help response complete; no real emergency'},'RESOLVED')]:
            r=self.client.post('/incidents/'+identifier+'/'+endpoint,json=body);self.assertEqual(r.status_code,200,r.text)
            self.assertEqual(next(i for i in self.client.get('/state').json()['incidents'] if i['id']==identifier)['status'],status)
        zone=next(z for z in self.client.get('/zones').json() if z['id']=='ZONE_TOILET_BLINDSPOT')
        self.assertEqual(zone['level'],'LOW');self.assertNotIn(identifier,zone['active_incident_ids'])
        self.assertTrue(self.send('sos','sos')['deduplicated']);self.assertEqual(len(storage.all_rows('incident')),1)
        report=self.client.get('/incidents/'+identifier+'/report').json()
        self.assertEqual(report['status'],'RESOLVED');self.assertIn('VERIFIED',[h['status'] for h in report['history']])
    def test_closed_run_rejects_new_signal_but_explicit_new_run_is_allowed(self):
        identifier=self.send('fall','radar')['incident']['id']
        self.client.post('/incidents/'+identifier+'/review',json={'status':'FALSE_ALARM','note':'Closed test'})
        self.assertEqual(self.client.post('/event',json=self.payload('impact','acoustic')).status_code,409)
        self.assertTrue(self.send('fall','radar')['deduplicated'])
        self.assertNotEqual(self.send('fall','radar','private-demo:'+str(uuid4()))['incident']['id'],identifier)
    def test_disabled_telegram_status_is_observed_not_assumed_delivered(self):
        with patch.object(notifications,'urlopen') as transport:
            identifier=self.send('sos','sos')['incident']['id'];main._notify_pool.submit(lambda:None).result(timeout=10)
            report=self.client.get('/incidents/'+identifier+'/report').json();transport.assert_not_called()
        self.assertEqual(report['notification_state'],'DISABLED')
        self.assertNotIn(report['notification_state'],('API_ACCEPTED','RECEIPT_CONFIRMED'))
    def test_private_video_and_speech_metadata_remain_prohibited(self):
        for change in ({'source':'vision'},{'sensor_modality':'vision'},{'source_type':'LIVE CAMERA'},
                       {'evidence_media':[{'url':'private-video.mp4'}]},{'type':'speech'}):
            response=self.client.post('/event',json={**self.payload('fall','radar'),**change})
            self.assertIn(response.status_code,(403,422))

if __name__=='__main__':unittest.main(verbosity=2)
