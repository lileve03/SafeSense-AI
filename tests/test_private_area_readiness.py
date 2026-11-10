"""Original-room, packet, persistence, CPU and notification-response readiness probes."""
import hashlib,json,math,os,re,statistics,subprocess,sys,tempfile,time,unittest
from datetime import datetime,timedelta,timezone
from io import BytesIO
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
OUT=ROOT/'runtime/private-area-hardware-readiness';OUT.mkdir(parents=True,exist_ok=True)
from backend.track_motion import MotionAnalyzer
EVIDENCE={}

class PrivateAreaReadiness(unittest.TestCase):
    def test_original_room_geometry_materials_sensors_lighting_and_camera_preserved(self):
        archived=ROOT/'runtime/private-view-restoration/archive/components/private-area/PrivateAreaDigitalTwin3D.tsx'
        current=ROOT/'dashboard/src/components/private-area/PrivateAreaDigitalTwin3D.tsx'
        old=archived.read_text(encoding='utf-8-sig');new=current.read_text(encoding='utf-8-sig')
        names='floorGeo floorMat gridHelper wallMat wallEdgeMat backWallGeo leftWallGeo screenGeo screenMat sosBoxGeo sosBoxMat emitterGeo emitterMat coneGeo coneMat waveGeo waveMat ambientLight dirLight fillLight camera'.split()
        norm=lambda s:re.sub(r'\s+','',s)
        for name in names:
            pattern=r'\bconst\s+'+name+r'\s*=[^;]+;'
            a=re.search(pattern,old);b=re.search(pattern,new)
            self.assertIsNotNone(a,name);self.assertIsNotNone(b,name);self.assertEqual(norm(a.group()),norm(b.group()),name)
        positions=['backWall','backEdge','leftWall','leftEdge','screen','sosBox','radarGroup','dirLight','fillLight']
        for name in positions:
            pattern=rf'\b{name}\.position\.set\([^;]+;'
            self.assertEqual(norm(re.search(pattern,old).group()),norm(re.search(pattern,new).group()),name)
        pose='theta: 0.6, phi: 0.45, radius: 12';self.assertIn(pose,old);self.assertIn(pose,new)
        EVIDENCE['original_room']={'declarations_matched':len(names),'placements_matched':len(positions),'initial_orbit_preserved':True,
            'archive':str(archived.relative_to(ROOT)),'archive_sha256':hashlib.sha256(archived.read_bytes()).hexdigest()}

    def test_actual_fresh_process_sqlite_persistence_and_restart_dedup(self):
        with tempfile.TemporaryDirectory(dir=OUT) as directory:
            body={'db':str(Path(directory)/'restart.sqlite3'),'group':'private-demo:'+str(uuid4()),'delayed_group':'private-demo:'+str(uuid4())}
            def worker(stage,**extra):
                result=subprocess.run([sys.executable,str(ROOT/'tests/readiness_persistence_worker.py')],cwd=ROOT,
                    input=json.dumps({**body,'stage':stage,**extra}),capture_output=True,text=True,timeout=30)
                self.assertEqual(result.returncode,0,result.stderr[-2500:]);return json.loads(result.stdout.strip().splitlines()[-1])
            first=worker('create');second=worker('reload',incident_id=first['incident_id'])
            self.assertNotEqual(first['pid'],second['pid']);self.assertEqual(first['report']['level'],'HIGH')
            self.assertEqual(first['report']['status'],'ACKNOWLEDGED');self.assertEqual(first['incident_id'],second['incident_id'])
            self.assertEqual(second['status'],'ACKNOWLEDGED');self.assertTrue(second['unchanged_on_retry']);self.assertTrue(second['retries_deduplicated'])
            self.assertEqual(second['delayed_id'],first['delayed_id']);self.assertEqual(second['delayed_level'],'OBSERVE')
            self.assertEqual(second['incidents'],2);self.assertEqual(second['events'],4)
            EVIDENCE['fresh_process_sqlite']={'different_processes':True,'same_incident_id':True,'acknowledgement_preserved':True,
                'duplicate_retry_unchanged':True,'late_impact_after_restart':'OBSERVE, not false HIGH','incidents':2,'events':4}

    def test_missing_required_packet_data_is_rejected_without_invented_values(self):
        from backend.sensor_observations import Observation
        from pydantic import ValidationError
        base={'source_mode':'SIMULATION','device_id':'packet-test','zone_id':'ZONE_TOILET_BLINDSPOT','timestamp':datetime.now(timezone.utc).isoformat(),'data_validity':'VALID'}
        for field in base:
            with self.assertRaises(ValidationError):Observation.model_validate({k:v for k,v in base.items() if k!=field})
        for patch_value in ({'tracks':[{'id':'A','position':{'x':1,'y':2}}],'coordinate_frame':'zone_meters_x_right_y_forward_z_up'},
              {'tracks':[{'id':'A','position':{'x':'NaN','y':0,'z':0}}],'coordinate_frame':'zone_meters_x_right_y_forward_z_up'},
              {'hardware_verified':True},{'audio':'forbidden'},{'transcript':'forbidden'},{'video':'forbidden'}):
            with self.assertRaises(ValidationError):Observation.model_validate({**base,**patch_value})
        self.assertIsNone(Observation.model_validate(base).tracks)
        EVIDENCE['packet_validation']={'missing_required_fields_rejected':len(base),'unknown_media_and_client_verification_flags_rejected':True,'missing_tracks':None}

    def test_current_hardware_adapter_remains_fail_closed(self):
        from backend.sensor_observations import HardwareAdapter,Observation
        from fastapi import HTTPException
        adapter=HardwareAdapter();status=adapter.status()
        self.assertFalse(status['connected']);self.assertFalse(status['verified']);self.assertEqual(status['label'],'Hardware Disconnected')
        observation=Observation(source_mode='LIVE_HARDWARE',device_id='unverified-test',zone_id='ZONE_TOILET_BLINDSPOT',timestamp=datetime.now(timezone.utc),data_validity='VALID')
        with self.assertRaises(HTTPException) as exception:adapter.normalize(observation)
        self.assertEqual(exception.exception.status_code,503)
        EVIDENCE['hardware_gate']={**status,'live_ingestion_http_status':503,'physical_hardware_tested':False}

    def test_cpu_temporal_analysis_latency_and_bounded_state(self):
        analyzer=MotionAnalyzer();base=datetime(2026,11,2,tzinfo=timezone.utc);latency=[]
        cpu_start=time.process_time();wall_start=time.perf_counter()
        for i in range(1200):
            t=i/10;tracks=[{'id':str(k),'position':{'x':.65*math.sin(math.pi*t)+k*.1,'y':k*.3,'z':.25}} for k in range(6)]
            observation={'source_mode':'SIMULATION','device_id':'cpu-fixture','zone_id':'ZONE_TOILET_BLINDSPOT','tracking_session_id':'cpu-session',
                'timestamp':(base+timedelta(seconds=t)).isoformat(),'timestamp_basis':'CAPTURE_TIME','data_validity':'VALID',
                'coordinate_frame':'zone_meters_x_right_y_forward_z_up','tracks':tracks}
            start=time.perf_counter_ns();result=analyzer.process(observation);latency.append((time.perf_counter_ns()-start)/1e6)
        cpu=time.process_time()-cpu_start;wall=time.perf_counter()-wall_start;p95=sorted(latency)[int(len(latency)*.95)-1]
        history=max(len(h) for state in analyzer.streams.values() for h in state['histories'].values())
        self.assertLess(p95,50,'Latency budget regression for six-track rule analysis on this test host')
        self.assertLessEqual(history,256);self.assertTrue(any(t['reversals_in_window']>=3 for t in result['tracks']))
        for i in range(70):analyzer.process({**observation,'tracking_session_id':'bounded-'+str(i)})
        self.assertLessEqual(len(analyzer.streams),64)
        EVIDENCE['backend_cpu']={'observations':1200,'tracks_per_observation':6,'synthetic_sample_hz':10,'wall_seconds':round(wall,4),
            'process_cpu_seconds':round(cpu,4),'mean_process_cpu_ms':round(cpu*1000/1200,4),
            'median_elapsed_ms':round(statistics.median(latency),4),'p95_elapsed_ms':round(p95,4),
            'max_history_samples':history,'stream_registry_after_70_sessions':len(analyzer.streams),
            'includes_model_inference_or_physical_acquisition':False}

    def test_telegram_response_matrix_distinguishes_acceptance_rejection_and_uncertainty(self):
        from backend import storage,notifications
        matrix=[('accepted',b'{"ok":true,"result":{"message_id":7}}','SENT','API_ACCEPTED'),
                ('rejected',b'{"ok":false,"error_code":400,"description":"fixture rejection"}','FAILED','FAILED'),
                ('missing_message_id',b'{"ok":true,"result":{}}','DELIVERY_UNKNOWN','UNKNOWN'),
                ('timeout',TimeoutError('fixture timeout'),'DELIVERY_UNKNOWN','UNKNOWN')]
        results=[]
        with (tempfile.TemporaryDirectory(dir=OUT) as directory,patch.object(storage,'DB',Path(directory)/'notifications.sqlite3'),patch.dict(os.environ,
             {'TELEGRAM_MODE':'test','TELEGRAM_BOT_TOKEN':'FAKE_TEST_TOKEN','TELEGRAM_TEST_CHAT_ID':'fixture-only','TELEGRAM_STAFF_DISPATCH_ENABLED':'false'}),
             patch.object(notifications,'select_route',return_value={'staff':'Fixture teacher','role':'teacher','active':True})):
            for name,response,status,state in matrix:
                incident={'id':'response-'+name,'zone_id':'ZONE_TOILET_BLINDSPOT','level':'CRITICAL','reason':'SIMULATED','created_at':'2026-11-02T00:00:00Z',
                    'status':'NEW','source':'simulation','source_type':'SIMULATION','processing_mode':'simulation','is_test':True,'evidence':[{'type':'sos'}]}
                effect=response if isinstance(response,Exception) else lambda *args,payload=response,**kwargs:BytesIO(payload)
                with patch.object(notifications,'urlopen',side_effect=effect) as transport:
                    value=notifications.dispatch(incident);self.assertEqual(value['status'],status,name)
                    self.assertEqual(notifications.delivery_state(value),state,name)
                    if status in ('SENT','DELIVERY_UNKNOWN'):
                        notifications.dispatch(incident);self.assertEqual(transport.call_count,1,name)
                self.assertNotEqual(notifications.delivery_state(value),'RECEIPT_CONFIRMED')
                results.append({'fixture':name,'status':status,'delivery_state':state})
        EVIDENCE['telegram_response_contract']={'mocked_transport_only':True,'external_messages_sent':0,'cases':results}

if __name__=='__main__':
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(PrivateAreaReadiness)
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    (OUT/'backend-readiness-results.json').write_text(json.dumps({'tests':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'evidence':EVIDENCE},indent=2),encoding='utf-8')
    sys.exit(not result.wasSuccessful())
