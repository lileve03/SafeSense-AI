"""Deterministic rules and false-trigger tests. No model accuracy is evaluated."""
import sys,math,unittest
from pathlib import Path
from datetime import datetime,timedelta,timezone
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from backend.track_motion import MotionAnalyzer,MotionRules,pairwise_distances

BASE=datetime(2026,1,1,tzinfo=timezone.utc)
def track(identifier='A',p=(0,0,0),**extra):
    return {'id':identifier,'position':dict(zip(('x','y','z'),p)) if p is not None else None,**extra}
def observation(t,tracks=None,**extra):
    return {'source_mode':'SIMULATION','device_id':'radar-a','zone_id':'ZONE_TOILET_BLINDSPOT',
            'tracking_session_id':'session-a','timestamp':(BASE+timedelta(seconds=t)).isoformat(),
            'timestamp_basis':'CAPTURE_TIME','coordinate_frame':'zone_meters_x_right_y_forward_z_up',
            'data_validity':'VALID','tracks':tracks if tracks is not None else [track()],**extra}
def feed(analyzer,fn,duration=8,start=0,**extra):
    result=None
    for i in range(round(duration*10)+1):
        t=start+i/10;result=analyzer.process(observation(t,fn(t),**extra))
    return result
def pacing(t):return [track(p=(.8*math.sin(math.pi*t),0,0))]

class TrackMotionTests(unittest.TestCase):
    def test_pairwise_3d_distances_and_nearest(self):
        pairs=pairwise_distances([track('A'),track('B',(3,4,12)),track('C',(2,0,0))])
        self.assertEqual(pairs[0]['distance_m'],2)
        self.assertEqual(next(p for p in pairs if p['track_ids']==['A','B'])['distance_m'],13)

    def test_missing_nonfinite_coordinates_never_become_zero(self):
        self.assertEqual(pairwise_distances([track(),track('B',None),track('C',(math.nan,0,0))]),[])
        a=MotionAnalyzer().process(observation(0,[track(),track('B',None)]))
        self.assertIsNone(a['nearest_pair']);self.assertEqual(a['highlighted_track_ids'],[])

    def test_sustained_proximity_has_explainable_duration(self):
        a=feed(MotionAnalyzer(),lambda t:[track(),track('B',(.6,0,0))],duration=3)
        self.assertTrue(a['nearest_pair']['proximity_candidate'])
        self.assertAlmostEqual(a['nearest_pair']['proximity_duration_seconds'],3)
        self.assertEqual(a['candidates'][0]['rule'],'PROXIMITY_DURATION')
        self.assertEqual(a['highlighted_track_ids'],['A','B'])
        self.assertIn('normal conversation',a['candidates'][0]['reason'])

    def test_short_pass_is_not_sustained_proximity(self):
        analyzer=MotionAnalyzer()
        for i in range(41):
            a=analyzer.process(observation(i/10,[track(),track('B',(2-i/10,0,0))]))
            self.assertFalse(any(c['rule']=='PROXIMITY_DURATION' for c in a['candidates']))

    def test_distance_threshold_is_strict_and_duration_configurable(self):
        rules=MotionRules(proximity_distance_m=.5,proximity_duration_seconds=1)
        a=feed(MotionAnalyzer(rules),lambda t:[track(),track('B',(.5,0,0))],duration=2)
        self.assertFalse(a['nearest_pair']['proximity_candidate'])
        a=feed(MotionAnalyzer(rules),lambda t:[track(),track('B',(.49,0,0))],duration=1)
        self.assertTrue(a['nearest_pair']['proximity_candidate']);self.assertEqual(a['rules']['proximity_distance_m'],.5)

    def test_repeated_back_and_forth_uses_meaningful_spatial_legs(self):
        a=feed(MotionAnalyzer(),pacing)
        feature=a['tracks'][0]
        self.assertTrue(feature['repeated_motion_candidate'],feature)
        self.assertGreaterEqual(feature['reversals_in_window'],3)
        self.assertGreater(feature['path_length_m'],2)
        self.assertEqual(a['candidates'][0]['rule'],'REPEATED_BACK_AND_FORTH')
        self.assertIn('not proof',a['notice']);self.assertNotIn('accuracy',a)

    def test_straight_walk_is_not_repetitive_motion(self):
        a=feed(MotionAnalyzer(),lambda t:[track(p=(.4*t,0,0))])
        self.assertEqual(a['tracks'][0]['reversals_in_window'],0);self.assertFalse(a['candidates'])

    def test_single_uturn_does_not_trigger_repeated_motion(self):
        a=feed(MotionAnalyzer(),lambda t:[track(p=(.5*t if t<=4 else 4-.5*t,0,0))])
        self.assertLess(a['tracks'][0]['reversals_in_window'],3);self.assertFalse(a['candidates'])

    def test_circular_direction_changes_are_not_back_and_forth(self):
        a=feed(MotionAnalyzer(),lambda t:[track(p=(math.cos(t*math.pi/4),math.sin(t*math.pi/4),0))])
        self.assertFalse(a['candidates']);self.assertEqual(a['tracks'][0]['reversals_in_window'],0)

    def test_stationary_jitter_and_noisy_reported_velocity_do_not_trigger(self):
        a=feed(MotionAnalyzer(),lambda t:[track(p=(.02*math.sin(17*t),0,0),velocity={'x':1 if int(t*10)%2 else -1,'y':0,'z':0})])
        self.assertFalse(a['candidates']);self.assertEqual(a['tracks'][0]['meaningful_legs'],0)

    def test_velocity_acceleration_and_heading_are_explainable(self):
        a=feed(MotionAnalyzer(),lambda t:[track(p=(.5*t*t,0,0))],duration=1)
        feature=a['tracks'][0]
        self.assertEqual(feature['velocity_origin'],'position_delta')
        self.assertAlmostEqual(feature['velocity_mps']['x'],.95,places=5)
        self.assertAlmostEqual(feature['acceleration_mps2']['x'],1,places=4)
        self.assertEqual(feature['heading_degrees'],0)
        self.assertEqual(feature['direction_change_degrees'],0)

    def test_missing_coordinates_clear_history_and_proximity(self):
        analyzer=MotionAnalyzer();feed(analyzer,pacing,duration=3.8)
        a=analyzer.process(observation(3.9,[track(p=None)]));self.assertIn('A',a['dropped_track_ids'])
        a=feed(analyzer,pacing,start=4,duration=3.9)
        self.assertFalse(a['candidates']);self.assertLess(a['tracks'][0]['observed_span_seconds'],4)

    def test_dropped_track_and_id_change_do_not_transfer_history(self):
        analyzer=MotionAnalyzer();feed(analyzer,pacing,duration=3.9)
        a=feed(analyzer,lambda t:[track('new-id',(.8*math.sin(math.pi*t),0,0))],start=4,duration=3.9)
        self.assertFalse(a['candidates']);self.assertEqual([f['id'] for f in a['tracks']],['new-id'])
        analyzer.process(observation(8,[]));a=analyzer.process(observation(8.1,pacing(8.1)))
        self.assertEqual(a['tracks'][0]['sample_count'],1)

    def test_gap_restarts_dwell_and_motion_window(self):
        analyzer=MotionAnalyzer();feed(analyzer,lambda t:[track(),track('B',(.5,0,0))],duration=2)
        a=analyzer.process(observation(4,[track(),track('B',(.5,0,0))]))
        self.assertEqual(a['nearest_pair']['proximity_duration_seconds'],0)
        self.assertFalse(a['candidates']);self.assertIn('gap',a['reason'])

    def test_possible_id_reuse_jump_resets_motion_and_pair_dwell(self):
        analyzer=MotionAnalyzer();feed(analyzer,lambda t:[track(),track('B',(.5,0,0))],duration=2)
        a=analyzer.process(observation(2.1,[track(p=(5,0,0)),track('B',(5.5,0,0))]))
        self.assertFalse(a['candidates']);self.assertEqual(a['nearest_pair']['proximity_duration_seconds'],0)
        self.assertIsNone(a['tracks'][0]['acceleration_mps2']);self.assertIn('ID reuse',a['reason'])

    def test_invalid_stale_low_quality_and_uncalibrated_data_do_not_trigger(self):
        for extra in ({'data_validity':'STALE'},{'data_validity':'INVALID'},{'coordinate_frame':None},
                      {'tracks':[track(quality=.1),track('B',(.1,0,0),quality=.1)]}):
            a=MotionAnalyzer().process(observation(0,**extra))
            self.assertEqual(a['status'],'UNAVAILABLE');self.assertFalse(a['candidates']);self.assertIsNone(a['nearest_pair'])

    def test_reordered_and_duplicate_timestamps_cannot_accumulate(self):
        for time in (1,2):
            analyzer=MotionAnalyzer();feed(analyzer,lambda t:[track(),track('B',(.5,0,0))],duration=2)
            a=analyzer.process(observation(time,[track(),track('B',(.5,0,0))]))
            self.assertEqual(a['status'],'UNAVAILABLE');self.assertFalse(a['candidates'])

    def test_sources_devices_zones_and_sessions_are_isolated(self):
        for change in ({'source_mode':'RECORDED_REPLAY'},{'device_id':'other'},{'zone_id':'other'}, {'tracking_session_id':'new-session'}):
            analyzer=MotionAnalyzer();feed(analyzer,pacing,duration=3.9)
            a=analyzer.process(observation(4,pacing(4),**change))
            self.assertEqual(a['tracks'][0]['sample_count'],1);self.assertFalse(a['candidates'])

    def test_recorded_and_live_use_same_rules_only_with_supported_data(self):
        for mode in ('SIMULATION','RECORDED_REPLAY','LIVE_HARDWARE'):
            a=feed(MotionAnalyzer(),pacing,source_mode=mode)
            self.assertTrue(a['tracks'][0]['repeated_motion_candidate'])
        for extra in ({'timestamp_basis':'REPLAY_EVENT_TIME'},{'tracking_session_id':None}):
            a=feed(MotionAnalyzer(),lambda t:[track(),track('B',(.5,0,0))],**extra)
            self.assertIsNotNone(a['nearest_pair']);self.assertFalse(a['temporal_supported']);self.assertFalse(a['candidates'])

    def test_classification_only_replay_has_no_fabricated_spatial_analysis(self):
        a=MotionAnalyzer().process(observation(0,[],source_mode='RECORDED_REPLAY',timestamp_basis='REPLAY_EVENT_TIME',coordinate_frame=None))
        self.assertIsNone(a['nearest_pair']);self.assertFalse(a['tracks']);self.assertFalse(a['highlighted_track_ids'])

    def test_duplicate_ids_and_bad_rule_configuration_are_rejected(self):
        a=MotionAnalyzer().process(observation(0,[track(),track()]))
        self.assertEqual(a['status'],'UNAVAILABLE')
        for change in ({'max_gap_seconds':0},{'window_seconds':2},{'reversal_angle_degrees':45}):
            with self.assertRaises(ValueError):MotionRules(**change)

    def test_coordinate_overflow_and_implausible_velocity_are_not_rule_evidence(self):
        self.assertEqual(pairwise_distances([track('A',(1e308,0,0)),track('B',(-1e308,0,0))]),[])
        a=MotionAnalyzer().process(observation(0,[track(p=(1e308,0,0))]))
        self.assertEqual(a['status'],'UNAVAILABLE');self.assertFalse(a['candidates'])
        a=feed(MotionAnalyzer(),lambda t:[track(velocity={'x':1e308,'y':0,'z':0})],duration=1)
        self.assertEqual(a['tracks'][0]['speed_mps'],0);self.assertFalse(a['candidates'])

    def test_capture_provenance_loss_breaks_history_before_capture_resumes(self):
        analyzer=MotionAnalyzer();feed(analyzer,pacing,duration=3.8)
        analyzer.process(observation(3.9,pacing(3.9),timestamp_basis='REPLAY_EVENT_TIME'))
        a=feed(analyzer,pacing,start=4,duration=3.9)
        self.assertLess(a['tracks'][0]['observed_span_seconds'],4);self.assertFalse(a['candidates'])

if __name__=='__main__':unittest.main(verbosity=2)
