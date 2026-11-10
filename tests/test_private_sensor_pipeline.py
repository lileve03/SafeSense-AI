"""Real file inference and isolated SQLite private sensor integration."""
import os,sys,time,json,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
OUT=ROOT/'runtime/private-sensor-pipeline';OUT.mkdir(parents=True,exist_ok=True)
os.environ.update(SAFESENSE_DB_PATH=str(OUT/('test-'+str(time.time_ns())+'.sqlite3')),TELEGRAM_MODE='disabled',TELEGRAM_STAFF_DISPATCH_ENABLED='false')
from fastapi.testclient import TestClient
from backend import main,scenario_catalog,scenario_testing,storage
C=TestClient(main.app,headers={'X-SafeSense-Token':main.TOKEN})
ZONE='ZONE_TOILET_BLINDSPOT';RESULTS=[]
class Pipeline(unittest.TestCase):
 def test_01_recorded_real_models(self):
  for identifier in ('radar_raw_fall','radar_raw_normal','acoustic_scream','acoustic_background'):
   source=scenario_catalog.selected(identifier);started=time.perf_counter()
   result=scenario_testing.sensor(source,source['default_model'],'private-test-'+identifier+'-'+str(time.time_ns()))
   self.assertEqual(result['output_origin'],'fresh_raw_input_inference')
   delivery=result['event_delivery'];event=storage.get('event',delivery['event_id'])
   self.assertEqual(event['processing_mode'],'real_model');self.assertTrue(event['is_test'])
   self.assertEqual(event['source_type'],'RECORDED SENSOR REPLAY');self.assertFalse(event['evidence_media'])
   self.assertEqual(event['score'],result['score'])
   if delivery['incident_id']:self.assertEqual(storage.get('incident',delivery['incident_id'])['level'],'OBSERVE')
   elapsed=round(time.perf_counter()-started,3)
   if identifier=='radar_raw_fall':
    again=scenario_testing.sensor(source,source['default_model'],'private-test-repeat-'+str(time.time_ns()))
    self.assertTrue(again['event_delivery']['deduplicated']);self.assertEqual(again['event_delivery']['incident_id'],delivery['incident_id'])
   RESULTS.append({'input':identifier,'score':result['score'],'candidate':result['candidate_detected'],'inference_sec':result.get('inference_time_sec'),'wall_sec':elapsed,'event_id':delivery['event_id'],'n_points':result.get('n_points'),'n_frames':result.get('n_frames')})
 def test_02_saved_replay_durable_dedup(self):
  body={'zone':ZONE,'sensor':'radar','index':0}
  a=C.post('/sensors/replay',json=body);self.assertEqual(a.status_code,200,a.text);a=a.json()
  main._events.clear()
  b=C.post('/sensors/replay',json=body).json();self.assertTrue(b['deduplicated']);self.assertEqual(a['incident']['id'],b['incident']['id'])
  negative=C.post('/sensors/replay',json={'zone':ZONE,'sensor':'acoustic','index':0}).json()
  self.assertEqual(negative['event']['type'],'normal_acoustic');self.assertIsNone(negative['incident'])
 def test_03_explainable_fusion_and_sos(self):
  run='fusion-'+str(time.time_ns())
  def send(kind,source):
   r=C.post('/event',json={'zone':ZONE,'type':kind,'source':source,'processing_mode':'simulation','analysis_run_id':run});self.assertEqual(r.status_code,200,r.text);return r.json()
  a=send('fall','radar');self.assertEqual(a['event']['level'],'OBSERVE')
  b=send('scream','yamnet');self.assertEqual(b['event']['level'],'HIGH');self.assertTrue(b['event']['reason']);self.assertIsNotNone(storage.get('incident',b['incident']['id']))
  c=send('sos','sos_button');self.assertEqual(c['event']['level'],'CRITICAL')
 def test_04_private_rejection(self):
  base={'zone':ZONE,'type':'fall','source':'radar','processing_mode':'simulation'}
  for extra in ({'source':'vision'},{'sensor_modality':'vision'},{'source_type':'LIVE CAMERA'},{'evidence_media':[{'url':'cctv.jpg'}]}):
   self.assertIn(C.post('/event',json={**base,**extra}).status_code,(403,422))
  self.assertEqual(C.post('/event',json={**base,'type':'speech','source':'yamnet'}).status_code,422)
if __name__=='__main__':
 suite=unittest.defaultTestLoader.loadTestsFromTestCase(Pipeline)
 result=unittest.TextTestRunner(verbosity=2).run(suite)
 (OUT/'results.json').write_text(json.dumps({'tests':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'recordings':RESULTS},indent=2),encoding='utf-8')
 sys.exit(not result.wasSuccessful())
