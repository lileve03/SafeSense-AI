"""Isolated normalized ingestion/preview API integration, no physical devices."""
import os,sys,tempfile,unittest,json,hashlib
from pathlib import Path
from datetime import datetime,timedelta,timezone
from uuid import uuid4
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
TEMP=tempfile.TemporaryDirectory()
os.environ.update(SAFESENSE_DB_PATH=str(Path(TEMP.name)/'motion.sqlite3'),TELEGRAM_MODE='disabled',TELEGRAM_STAFF_DISPATCH_ENABLED='false')
from backend import main,storage
from fastapi.testclient import TestClient

class MotionAPITests(unittest.TestCase):
    def setUp(self):
        self.client=TestClient(main.app,headers={'X-SafeSense-Token':main.TOKEN})
        self.session=str(uuid4());self.base=datetime.now(timezone.utc)-timedelta(seconds=4)
    def body(self,t,mode='SIMULATION'):
        return dict(observation_id=str(uuid4()),source_mode=mode,device_id='motion-api-test',zone_id='ZONE_TOILET_BLINDSPOT',
                    tracking_session_id=self.session,timestamp=(self.base+timedelta(seconds=t)).isoformat(),timestamp_basis='CAPTURE_TIME',
                    data_validity='VALID',coordinate_frame='zone_meters_x_right_y_forward_z_up',
                    tracks=[{'id':'A','position':{'x':0,'y':0,'z':.2}},{'id':'B','position':{'x':.6,'y':0,'z':.2}}])
    def test_preview_runs_backend_rules_without_persistence_or_incidents(self):
        before=[len(storage.all_rows(kind)) for kind in ('sensor_observation','event','incident')]
        response=self.client.post('/sensors/motion/preview',json={'observations':[self.body(i/10) for i in range(41)]})
        self.assertEqual(response.status_code,200,response.text);data=response.json()
        self.assertEqual(data['analysis']['candidates'][0]['rule'],'PROXIMITY_DURATION')
        self.assertEqual(before,[len(storage.all_rows(kind)) for kind in ('sensor_observation','event','incident')])
        self.assertFalse(data['persisted'])
    def test_preview_cannot_forge_live_recorded_sources_or_frontend_rule_overrides(self):
        for mode in ('LIVE_HARDWARE','RECORDED_REPLAY'):
            self.assertEqual(self.client.post('/sensors/motion/preview',json={'observations':[self.body(0,mode)]}).status_code,422)
        self.assertEqual(self.client.post('/sensors/motion/preview',json={'observations':[self.body(0)],'rules':{'min_reversals':1}}).status_code,422)
        self.assertEqual(TestClient(main.app).get('/sensors/motion/rules').status_code,401)
        self.assertEqual(self.client.get('/sensors/motion/rules').json()['rules']['proximity_duration_seconds'],3)
    def test_normalized_ingestion_persists_analysis_without_escalating_motion_candidates(self):
        before=len(storage.all_rows('incident'))
        for i in range(41):
            body=self.body(i/10)
            response=self.client.post('/sensors/observations',json=body)
            self.assertEqual(response.status_code,200,response.text)
        data=response.json();self.assertEqual(data['observation']['motion_analysis']['highlighted_track_ids'],['A','B'])
        saved=storage.get('sensor_observation',body['observation_id'])
        self.assertEqual(saved['motion_analysis'],data['observation']['motion_analysis'])
        self.assertEqual(before,len(storage.all_rows('incident')));self.assertEqual(data['events'],[])
        repeat=self.client.post('/sensors/observations',json=body).json()
        self.assertEqual(repeat['observation']['motion_analysis'],saved['motion_analysis'])
    def test_replay_classification_remains_spatially_unavailable_and_hardware_disconnected(self):
        recorded=self.client.post('/sensors/replay',json={'zone':'ZONE_TOILET_BLINDSPOT','sensor':'radar','index':0})
        self.assertEqual(recorded.status_code,200,recorded.text)
        rows=storage.all_rows('sensor_observation');row=next(o for o in rows if o['source_mode']=='RECORDED_REPLAY')
        self.assertIsNone(row['motion_analysis']['nearest_pair']);self.assertFalse(row['motion_analysis']['candidates'])
        self.assertEqual(self.client.post('/sensors/observations',json=self.body(0,'LIVE_HARDWARE')).status_code,503)
    def test_mixed_session_preview_is_rejected(self):
        a=self.body(0);b=self.body(.1);b['tracking_session_id']='other-session'
        self.assertEqual(self.client.post('/sensors/motion/preview',json={'observations':[a,b]}).status_code,422)

    def test_preupgrade_observation_ids_remain_retry_compatible(self):
        from backend.sensor_observations import Observation,save
        observation=Observation(**{**self.body(0),'tracking_session_id':None})
        legacy={k:v for k,v in observation.model_dump(mode='json').items() if k!='tracking_session_id'}
        legacy['payload_sha256']=hashlib.sha256(json.dumps(legacy,sort_keys=True).encode()).hexdigest()
        storage.put('sensor_observation',observation.observation_id,legacy)
        self.assertEqual(save(observation),legacy)
        changed=observation.model_copy(update={'device_id':'changed'})
        self.assertEqual(self.client.post('/sensors/observations',json=changed.model_dump(mode='json')).status_code,409)

if __name__=='__main__':unittest.main(verbosity=2)
