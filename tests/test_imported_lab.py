import json,os,time,unittest
from copy import deepcopy
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'runtime/imported-lab-tests';OUT.mkdir(parents=True,exist_ok=True)
os.environ.update(SAFESENSE_DB_PATH=str(OUT/('unit-'+str(time.time_ns())+'.sqlite3')),TELEGRAM_MODE='disabled',SAFESENSE_API_TOKEN='imported-lab-test')
from fastapi.testclient import TestClient
from backend.main import app
from backend.imported_lab import dataset,validate

class ImportedLabTests(unittest.TestCase):
 def test_actual_supplied_frames_validate(self):
  data=dataset();self.assertEqual(len(data['frames']),121);self.assertEqual(data['duration_sec'],12)
  self.assertEqual(data['provenance']['processing_mode'],'simulation');self.assertEqual(data['annotations'][0]['time'],4.9)
  self.assertTrue(all(len(f['tracks'])==5 for f in data['frames']))
 def test_invalid_coordinates_ids_and_time_fail_closed(self):
  for mutation in ['nan','outside','duplicate','backward']:
   data=deepcopy(dataset());frames=data['frames']
   if mutation=='nan':frames[0]['tracks'][0]['x']=float('nan')
   if mutation=='outside':frames[0]['tracks'][0]['z']=10
   if mutation=='duplicate':frames[0]['tracks'][1]['id']=1
   if mutation=='backward':frames[1]['time']=0
   with self.assertRaises(ValueError):validate(frames,data['annotations'])
 def test_annotation_requires_corresponding_synthetic_track(self):
  data=deepcopy(dataset());data['annotations'][0]['person_id']=99
  with self.assertRaises(ValueError):validate(data['frames'],data['annotations'])
 def test_existing_fusion_keeps_distinct_simulated_modalities_and_no_model_score(self):
  with TestClient(app) as client:
   headers={'X-SafeSense-Token':'imported-lab-test'}
   base={'zone':'ZONE_TOILET_BLINDSPOT','source':'simulation','processing_mode':'simulation','source_type':'SIMULATION','is_test':True,'score':None,'analysis_run_id':'zip-fusion-regression-'+str(time.time_ns())}
   first=client.post('/event',headers=headers,json={**base,'type':'fall','sensor_modality':'radar'}).json()
   second=client.post('/event',headers=headers,json={**base,'type':'scream','sensor_modality':'acoustic'}).json()
   self.assertEqual(first['event']['level'],'OBSERVE');self.assertEqual(second['event']['level'],'HIGH')
   self.assertIsNone(second['event']['score']);self.assertTrue(second['event']['is_test'])
   self.assertEqual(second['event']['evidence_media'],[])
 def test_endpoint_is_authenticated_read_only_and_no_incident_side_effects(self):
  with TestClient(app) as client:
   self.assertEqual(client.get('/testing/imported-lab').status_code,401)
   headers={'X-SafeSense-Token':'imported-lab-test'}
   before=client.get('/state',headers=headers).json()
   response=client.get('/testing/imported-lab',headers=headers);self.assertEqual(response.status_code,200)
   self.assertEqual(client.post('/testing/imported-lab',headers=headers,json={}).status_code,405)
   self.assertEqual(client.post('/testing/imported-lab/clear',headers=headers,json={}).status_code,404)
   after=client.get('/state',headers=headers).json()
   self.assertEqual(len(before['events']),len(after['events']));self.assertEqual(len(before['incidents']),len(after['incidents']))
   self.assertNotIn('C:\\Users',response.text);self.assertNotIn('audio',response.json()['frames'][0])
if __name__=='__main__':unittest.main()
