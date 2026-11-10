"""Acquisition boundary tests; isolated SQLite, no model download or staff delivery."""
import os
import sys
import tempfile
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
TEMP=tempfile.TemporaryDirectory()
os.environ.update(SAFESENSE_DB_PATH=str(Path(TEMP.name)/'observations.sqlite3'), TELEGRAM_MODE='disabled', TELEGRAM_STAFF_DISPATCH_ENABLED='false')
from backend import main, storage
from fastapi.testclient import TestClient
from uuid import uuid4


class ObservationTests(unittest.TestCase):
    def setUp(self):
        self.client=TestClient(main.app,headers={'X-SafeSense-Token':main.TOKEN})
        self.body=dict(observation_id=str(uuid4()),source_mode='SIMULATION',device_id='test-radar',zone_id='ZONE_TOILET_BLINDSPOT',
                       timestamp=datetime.now(timezone.utc).isoformat(),data_validity='VALID')

    def send(self, **changes):
        return self.client.post('/sensors/observations',json={**self.body,**changes})

    def test_authentication(self):
        self.assertEqual(TestClient(main.app).get('/sensors/observations/status').status_code,401)

    def test_hardware_cannot_be_forged(self):
        self.assertEqual(self.send(source_mode='LIVE_HARDWARE').status_code,503)
        self.assertEqual(self.send(hardware_verified=True).status_code,422)
        self.assertEqual(self.client.get('/sensors/observations/status').json()['hardware']['label'],'Hardware Disconnected')

    def test_schema_and_spatial_validation(self):
        for extra in ({'point_cloud':[{'x':1,'y':2,'z':3}]},{'timestamp':'2026-01-01T00:00:00'},
                      {'audio':'private'},{'confidence':2},{'zone_id':'ZONE_CORRIDOR_A'}):
            self.assertEqual(self.send(**extra).status_code,422)
        r=self.send(coordinate_frame='zone_meters_x_right_y_forward_z_up',tracks=[{'id':'A','position':{'x':1,'y':2,'z':.5},'velocity':{'x':0,'y':0,'z':0},'quality':.8}])
        self.assertEqual(r.status_code,200,r.text)
        self.assertEqual(r.json()['observation']['tracks'][0]['position']['z'],.5)

    def test_invalid_stale_never_escalate(self):
        for extra in ({'data_validity':'INVALID'},{'timestamp':(datetime.now(timezone.utc)-timedelta(seconds=60)).isoformat()}):
            self.body['observation_id']=str(uuid4())
            r=self.send(radar_event='fall',sos_state='ACTIVE',**extra)
            self.assertEqual(r.status_code,200,r.text);self.assertEqual(r.json()['events'],[])

    def test_fusion_sos_dedup_and_persistence(self):
        before={r['id'] for r in storage.all_rows('incident')}
        extra=dict(radar_event='fall',acoustic_events=[{'kind':'scream','confidence':1}])
        r=self.send(**extra);self.assertEqual(r.status_code,200,r.text)
        self.assertEqual(r.json()['events'][-1]['event']['level'],'HIGH')
        repeat=self.send(**extra).json();self.assertTrue(repeat['events'][0]['deduplicated'])
        self.assertIsNotNone(storage.get('sensor_observation',self.body['observation_id']))
        self.assertEqual(self.send(device_id='changed').status_code,409)
        self.body['observation_id']=str(uuid4())
        sos=self.send(sos_state='ACTIVE').json()['events'][0]['incident']
        self.assertEqual(sos['level'],'CRITICAL');self.assertTrue(sos['is_test'])
        self.assertTrue(before.issubset({r['id'] for r in storage.all_rows('incident')}))

    def test_recorded_adapter_uses_existing_evidence_without_positions(self):
        r=self.client.post('/sensors/replay',json={'zone':self.body['zone_id'],'sensor':'radar','index':0})
        self.assertEqual(r.status_code,200,r.text)
        event=r.json()['event']
        replay=self.client.post('/sensors/observations/replay',json={'event_id':event['id']})
        self.assertEqual(replay.status_code,200,replay.text)
        o=replay.json()['observation'];self.assertEqual(o['source_mode'],'RECORDED_REPLAY')
        self.assertIsNone(o['tracks']);self.assertIsNone(o['point_cloud'])
        self.assertEqual(self.send(source_mode='RECORDED_REPLAY').status_code,422)
        latest=self.client.get('/sensors/observations',params={'zone_id':self.body['zone_id'],'source_mode':'RECORDED_REPLAY'}).json()
        self.assertEqual(latest['observation']['observation_id'],o['observation_id'])
        self.assertEqual(latest['observation']['backend_assessment']['event_id'],event['id'])
        self.assertEqual(latest['observation']['backend_assessment']['level'],r.json()['incident']['level'])

    def test_reject_duplicate_tracks_unknown_modes_and_bad_numbers(self):
        for extra in ({'tracks':[{'id':'A'},{'id':'A'}]}, {'source_mode':'CONNECTED'},
                      {'tracks':[{'id':'A','quality':1.1}]}, {'point_cloud':[{'x':'NaN','y':0,'z':0}],'coordinate_frame':'zone_meters_x_right_y_forward_z_up'},
                      {'acoustic_events':[{'kind':'scream','confidence':1},{'kind':'scream','confidence':.5}]}):
            self.assertEqual(self.send(**extra).status_code,422)

    def test_existing_incident_records_unchanged_and_no_invalid_id_reuse(self):
        sentinel={'id':'retained-incident','history':[{'status':'ACKNOWLEDGED'}]}
        storage.put('incident',sentinel['id'],sentinel)
        self.assertEqual(self.send(data_validity='INVALID').status_code,200)
        self.assertEqual(self.send(data_validity='VALID').status_code,409)
        self.assertEqual(storage.get('incident',sentinel['id']),sentinel)

if __name__=='__main__':unittest.main(verbosity=2)
