"""Overview identity regression tests; no model execution or database mutations."""
from pathlib import Path
import sys,unittest,copy
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from backend.overview_insights import unique_overview_incidents

def recording(identifier,**changes):
    row={'id':identifier,'zone_id':'ZONE_STAIRCASE','processing_mode':'real_model','source':'vision','source_type':'RECORDED REAL VIDEO',
         'is_test':True,'level':'OBSERVE','status':'NEW','score':.9,'event_ids':[identifier+'-event'],
         'evidence':[{'type':'fall','source':'vision','processing_mode':'real_model','model_version':'pose-v1','camera_id':'CAM_STAIRCASE',
            'evidence_reference':'sha256:'+'a'*64+';annotation:'+identifier,
            'evidence_media':[{'time_scope':'candidate_rule_timestamp','start_sec':0,'end_sec':8,'event_time_sec':3}]}]}
    row.update(changes);return row

class OverviewInsights(unittest.TestCase):
    def test_same_incident_id_only_once(self):
        first=recording('same');second=recording('same',processing_mode='simulation')
        self.assertEqual(unique_overview_incidents([first,second]),[first])
    def test_repeated_recorded_analysis_ignores_new_annotation_ids_and_scores(self):
        newest=recording('new',score=.91);old=recording('old',score=.89)
        self.assertEqual(unique_overview_incidents([newest,old]),[newest])
    def test_equal_scores_different_input_are_not_duplicates(self):
        first=recording('first');second=recording('second');second['evidence'][0]['evidence_reference']='sha256:'+'b'*64
        self.assertEqual(len(unique_overview_incidents([first,second])),2)
    def test_extra_negative_observation_does_not_repeat_same_recorded_candidate(self):
        newest=recording('new');older=recording('old');before=copy.deepcopy(older)
        normal={**copy.deepcopy(newest['evidence'][0]),'type':'normal_motion','model_version':'v3','evidence_media':[]}
        newest['evidence'].append(normal)
        self.assertEqual(unique_overview_incidents([newest,older]),[newest])
        self.assertEqual(older,before)
        normal['evidence_reference']='sha256:'+'b'*64
        self.assertEqual(len(unique_overview_incidents([newest,older])),2)
    def test_different_event_timestamps_are_retained(self):
        first=recording('first');second=recording('second');second['evidence'][0]['evidence_media'][0]['event_time_sec']=4
        self.assertEqual(len(unique_overview_incidents([first,second])),2)
    def test_different_camera_zone_and_model_are_retained(self):
        for key,value in [('camera_id','CAM_OTHER'),('model_version','other-model')]:
            first=recording('first');second=recording('second');second['evidence'][0][key]=value
            self.assertEqual(len(unique_overview_incidents([first,second])),2)
        self.assertEqual(len(unique_overview_incidents([recording('first'),recording('second',zone_id='ZONE_CORRIDOR_A')])),2)
    def test_modes_and_live_sources_remain_distinct(self):
        modes=[recording('ai'),recording('replay',processing_mode='recorded_sensor_replay'),recording('sim',processing_mode='simulation'),recording('live',source_type='LIVE CAMERA',is_test=False)]
        self.assertEqual(len(unique_overview_incidents(modes)),4)
        self.assertEqual(len(unique_overview_incidents([recording('live1',source_type='LIVE CAMERA',is_test=False),recording('live2',source_type='LIVE CAMERA',is_test=False)])),2)
    def test_separate_simulations_are_not_collapsed(self):
        self.assertEqual(len(unique_overview_incidents([recording('a',processing_mode='simulation'),recording('b',processing_mode='simulation')])),2)
    def test_precomputed_and_fresh_source_provenance_remain_distinct(self):
        self.assertEqual(len(unique_overview_incidents([recording('fresh'),recording('precomputed',source_type='PRECOMPUTED ANALYSIS')])),2)
    def test_saved_replay_uses_exact_row_identity(self):
        first=recording('a',processing_mode='recorded_sensor_replay');second=recording('b',processing_mode='recorded_sensor_replay')
        for row in (first,second):row['evidence'][0]['evidence_reference']='evaluation/predictions.csv:row=4'
        self.assertEqual(unique_overview_incidents([first,second]),[first])
        second['evidence'][0]['evidence_reference']='evaluation/predictions.csv:row=5'
        self.assertEqual(len(unique_overview_incidents([first,second])),2)
    def test_missing_provenance_does_not_guess(self):
        first=recording('a');second=recording('b')
        for row in (first,second):row['evidence'][0]['evidence_media']=[]
        self.assertEqual(len(unique_overview_incidents([first,second])),2)
    def test_full_shared_event_identity_deduplicates(self):
        first=recording('a',processing_mode='simulation');second=recording('b',processing_mode='simulation')
        second['event_ids']=first['event_ids'][:]
        self.assertEqual(unique_overview_incidents([first,second]),[first])
    def test_closed_incidents_do_not_hide_active_ones_or_mutate_records(self):
        rows=[recording('closed',status='RESOLVED'),recording('active')];before=copy.deepcopy(rows)
        self.assertEqual(unique_overview_incidents(rows),[rows[1]]);self.assertEqual(rows,before)

if __name__=='__main__':unittest.main(verbosity=2)
