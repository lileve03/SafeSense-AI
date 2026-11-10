"""Automatic policy/provenance tests; no neural inference or external notification."""
from pathlib import Path
import copy
import json
import os
import sys
import tempfile
import unittest
from io import BytesIO
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fastapi import HTTPException
from fastapi.testclient import TestClient
from pydantic import ValidationError
from monitoring_ai import JobIn, execution_models, job_key, CONTEXT
from backend import main, storage
import fight_api


class AutomaticPolicy(unittest.TestCase):
    def test_wire_contract_accepts_exactly_four_supported_values(self):
        schema=JobIn.model_json_schema()['properties']['model']
        self.assertEqual(set(schema['enum']),{'all','v2','v3','pose'})
        for mode in schema['enum']:
            self.assertEqual(JobIn(zone_id='ZONE_CORRIDOR_A',model=mode).model,mode)
        with self.assertRaises(ValidationError):JobIn(zone_id='ZONE_CORRIDOR_A',model='auto')

    def test_default_all_camera_selects_one_v3_classifier_and_pose(self):
        with patch.dict(os.environ, {'SAFESENSE_FIGHT_BASELINE': 'v3'}), patch('backend.registry.cameras', return_value=[]):
            body = JobIn(zone_id='ZONE_CORRIDOR_A', camera_id='camera', authorized=True)
            self.assertEqual(body.model, 'all')
            self.assertEqual(execution_models(body), ('v3', 'pose'))

    def test_configured_v2_camera_overrides_global_v3_without_comparison_run(self):
        with patch.dict(os.environ, {'SAFESENSE_FIGHT_BASELINE': 'v3'}), patch('backend.registry.cameras', return_value=[{'camera_id':'camera','fight_model':'v2'}]):
            body = JobIn(zone_id='ZONE_CORRIDOR_A', camera_id='camera')
            self.assertEqual(execution_models(body), ('v2', 'pose'))

    def test_invalid_policy_does_not_silently_choose_a_model(self):
        with patch.dict(os.environ, {'SAFESENSE_FIGHT_BASELINE':'invalid'}), patch('backend.registry.cameras', return_value=[]):
            with self.assertRaises(HTTPException):
                execution_models(JobIn(zone_id='ZONE_CORRIDOR_A',camera_id='camera'))

    def test_baseline_configuration_changes_invalidate_the_completed_cache_key(self):
        with tempfile.TemporaryDirectory() as tmp, patch('backend.registry.cameras', return_value=[]):
            path=Path(tmp)/'recording.mp4';path.write_bytes(b'cache identity fixture, not model input')
            body=JobIn(zone_id='ZONE_CORRIDOR_A',camera_id='camera')
            with patch.dict(os.environ, {'SAFESENSE_FIGHT_BASELINE':'v3'}):v3=job_key(body,path)
            with patch.dict(os.environ, {'SAFESENSE_FIGHT_BASELINE':'v2'}):v2=job_key(body,path)
            self.assertNotEqual(v2,v3)

    def test_legacy_comparison_and_individual_models_remain_available(self):
        self.assertEqual(execution_models(JobIn(zone_id='ZONE_CORRIDOR_A',model='all')),('v2','v3','pose'))
        self.assertEqual(execution_models(JobIn(zone_id='ZONE_CORRIDOR_A',model='v2')),('v2',))

    def test_auto_run_provenance_reaches_event_ingestion_and_audit_result(self):
        marker=CONTEXT.set({'analysis_run_id':'automatic-job','camera_id':'CAM_CANTEEN'})
        result={'zone_id':'ZONE_CANTEEN','analysis_id':'observation','model_version':'v3'}
        try:
            with patch.object(fight_api,'urlopen',return_value=BytesIO(b'{"event":{"id":"observation"},"incident":null}')) as transport:
                delivery=fight_api.notify_backend(result,'normal_motion',.1,'hash fixture')
            payload=json.loads(transport.call_args.args[0].data)
            self.assertEqual(payload['analysis_run_id'],'automatic-job')
            self.assertEqual(result['analysis_run_id'],'automatic-job')
            self.assertIsNone(delivery['incident_id'])
        finally:CONTEXT.reset(marker)

    def test_normal_run_does_not_inherit_another_recordings_fall(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(storage,'DB',Path(tmp)/'test.sqlite3'), patch.dict(os.environ,{'TELEGRAM_MODE':'disabled'}):
            before_events=copy.deepcopy(main._events);before_incidents=copy.deepcopy(main._incidents)
            try:
                main._events.clear();main._incidents.clear()
                with TestClient(main.app,headers={'X-SafeSense-Token':main.TOKEN}) as client:
                    base={'zone':'ZONE_CANTEEN','source':'vision','processing_mode':'real_model','source_type':'RECORDED REAL VIDEO','is_test':True}
                    previous=client.post('/event',json={**base,'type':'fall','analysis_run_id':'previous-recording'}).json()
                    self.assertIsNotNone(previous['incident'])
                    normal=client.post('/event',json={**base,'type':'normal_motion','analysis_run_id':'new-automatic-job'}).json()
                    self.assertIsNone(normal['incident'])
                    self.assertEqual(normal['event']['level'],'LOW')
                    self.assertEqual(len(client.get('/incidents').json()),1)
                main._notify_pool.submit(lambda:None).result(timeout=15)
            finally:
                main._events.clear();main._events.extend(before_events);main._incidents[:]=before_incidents


if __name__=='__main__':unittest.main(verbosity=2)
