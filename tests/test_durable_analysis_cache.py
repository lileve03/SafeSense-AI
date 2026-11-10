from pathlib import Path
import tempfile,unittest,os,sys,time
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from backend.analysis_cache import AnalysisCache,content_hash,identity_hash
from backend.inference_queue import InferenceQueue
class DurableAnalysisTests(unittest.TestCase):
 def test_content_changes_invalidate_hash_even_at_same_length(self):
  with tempfile.TemporaryDirectory() as directory:
   p=Path(directory)/'source';p.write_bytes(b'first');a=content_hash(p);p.write_bytes(b'other');self.assertNotEqual(a,content_hash(p))
 def test_identity_changes_for_source_model_config_code_and_context(self):
  base={'source':'a','model':'b','config':{'threads':4},'code':'v1','namespace':'database1'}
  for name,value in [('source','changed'),('model','changed'),('config',{'threads':2}),('code','v2'),('namespace','database2')]:self.assertNotEqual(identity_hash(base),identity_hash({**base,name:value}))
 def test_restart_expiry_corruption_and_bounded_disk_cache(self):
  with tempfile.TemporaryDirectory() as directory:
   cache=AnalysisCache(directory,entries=2);key=identity_hash('actual identity');row={'id':'prepared','status':'COMPLETED','result':{'pose_frames':[{'frame_index':0,'time_sec':0,'persons':[]}]}}
   cache.save(key,row);self.assertEqual(AnalysisCache(directory).load(key),row)
   p=Path(directory)/(key+'.json.gz');os.utime(p,(time.time()-8*86400,)*2);self.assertIsNone(cache.load(key))
   p.write_bytes(b'corrupt');self.assertIsNone(cache.load(key))
   for i in range(4):cache.save(identity_hash(i),row)
   self.assertLessEqual(len(list(Path(directory).glob('*.json.gz'))),2)
 def test_disk_hit_bypasses_full_queue_without_running_models(self):
  ready={'id':'prepared','status':'COMPLETED','result':{'pose_frames':[]}};executed=[]
  queue=InferenceQueue(lambda row:None,completed_lookup=lambda key:ready if key=='ready' else None)
  row=queue.submit('ready',{'id':'new','status':'QUEUED'},lambda:executed.append(True),'viewer',1)
  self.assertTrue(row['cache_hit']);self.assertEqual(row['cache_tier'],'disk');self.assertEqual(row['id'],'prepared');self.assertEqual(executed,[])
 def test_optional_expired_annotation_does_not_invalidate_coordinates(self):
  import monitoring_ai
  row={'id':'prepared','status':'COMPLETED','result':{'annotated_video_url':'/ai/fall/artifacts/expired','pose_frames':[{'frame_index':0,'time_sec':0,'persons':[]}],'model_results':[{'event_delivery':{'status':'recorded'}}]}}
  self.assertTrue(monitoring_ai.cache_valid(row));row['result']['model_errors']=[{'model':'pose','error':'failed'}];self.assertFalse(monitoring_ai.cache_valid(row))
 def test_mismatched_source_and_camera_never_validate_as_cached_results(self):
  import monitoring_ai
  row={'status':'COMPLETED','cache_identity':{'camera_id':'camera-a','zone_id':'zone','source_sha256':'source-a'},'result':{'camera_id':'camera-a','zone_id':'zone','input_sha256':'source-a','event_delivery':{'status':'recorded'}}}
  self.assertTrue(monitoring_ai.cache_valid(row))
  row['result']['input_sha256']='source-b';self.assertFalse(monitoring_ai.cache_valid(row))
  row['result']['input_sha256']='source-a';row['result']['camera_id']='camera-b';self.assertFalse(monitoring_ai.cache_valid(row))
 def test_concurrent_identity_requests_hash_an_unchanged_file_only_once(self):
  from concurrent.futures import ThreadPoolExecutor
  import backend.analysis_cache as cache
  with tempfile.TemporaryDirectory() as directory:
   source=Path(directory)/'weights.pth';source.write_bytes(b'genuine content fixture '*(800000));cache._content_hash.cache_clear()
   original=cache.hashlib.sha256
   with patch.object(cache.hashlib,'sha256',wraps=original) as hashed:
    with ThreadPoolExecutor(max_workers=12) as pool:values=list(pool.map(lambda _:cache.content_hash(source),range(30)))
   self.assertEqual(len(set(values)),1);self.assertEqual(hashed.call_count,1)
if __name__=='__main__':unittest.main(verbosity=2)
