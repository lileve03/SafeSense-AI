import os,sys,time,unittest,math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
OUT=ROOT/'runtime/radar-tracking-tests';OUT.mkdir(parents=True,exist_ok=True)
os.environ.update(SAFESENSE_DB_PATH=str(OUT/('unit-'+str(time.time_ns())+'.sqlite3')),TELEGRAM_MODE='disabled')
from backend.radar_simulation import dataset
from backend import main,storage
from fastapi.testclient import TestClient
from uuid import uuid4
class TrackingSimulationTests(unittest.TestCase):
 def setUp(self):self.client=TestClient(main.app,headers={'X-SafeSense-Token':main.TOKEN})
 def test_source_count_distances_and_temporal_rules(self):
  data=dataset();self.assertEqual(data['source'],'SIMULATION');self.assertFalse(data['hardware_verified'])
  self.assertEqual(len(data['frames']),241)
  for f in data['frames']:
   self.assertEqual(f['count'],3);self.assertEqual(len({t['id'] for t in f['tracks']}),3)
   for p in f['pairs']:
    a,b=[next(t for t in f['tracks'] if t['id']==id) for id in p['ids']]
    self.assertAlmostEqual(p['distance'],math.hypot(a['x']-b['x'],a['y']-b['y']),places=3)
  self.assertTrue(data['frames'][35]['tracks'][0]['repeated_motion'])
  self.assertTrue(data['frames'][105]['tracks'][0]['possible_fall']);self.assertEqual(data['frames'][105]['level'],'HIGH')
 def test_readonly_preview_does_not_create_measurements(self):
  before=len(storage.all_rows('event'));response=self.client.get('/testing/radar-simulation')
  self.assertEqual(response.status_code,200);self.assertEqual(len(storage.all_rows('event')),before)
  self.assertEqual(TestClient(main.app).get('/testing/radar-simulation').status_code,401)
 def test_fusion_dedup_sos_and_sqlite(self):
  session=str(uuid4());body={'session_id':session,'time_sec':10.5,'kind':'fusion'}
  response=self.client.post('/testing/radar-simulation/events',json=body);self.assertEqual(response.status_code,200,response.text)
  result=response.json();self.assertEqual(result['incident']['level'],'HIGH')
  self.assertTrue(result['incident']['is_test']);self.assertEqual(result['incident']['processing_mode'],'simulation')
  self.assertTrue(all(e['score'] is None and not e['evidence_media'] for e in result['incident']['evidence']))
  repeat=self.client.post('/testing/radar-simulation/events',json=body).json();self.assertTrue(repeat['deduplicated']);self.assertEqual(result['incident']['id'],repeat['incident']['id'])
  sos=self.client.post('/testing/radar-simulation/events',json={**body,'kind':'sos'}).json();self.assertEqual(sos['incident']['level'],'CRITICAL');self.assertIsNotNone(storage.get('incident',sos['incident']['id']))
 def test_cannot_submit_real_or_arbitrary_coordinates(self):
  base={'session_id':str(uuid4()),'time_sec':0,'kind':'fusion'}
  self.assertEqual(self.client.post('/testing/radar-simulation/events',json=base).status_code,422)
  for extra in ({'source':'LIVE SENSOR'},{'positions':[]},{'processing_mode':'real_model'},{'camera_id':'private-cctv'}):
   self.assertEqual(self.client.post('/testing/radar-simulation/events',json={**base,'kind':'sos',**extra}).status_code,422)
if __name__=='__main__':unittest.main(verbosity=2)
