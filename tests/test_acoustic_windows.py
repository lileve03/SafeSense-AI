import unittest
from backend.acoustic_windows import score_windows

class AcousticWindowTests(unittest.TestCase):
 def test_genuine_values_hops_threshold_and_clipped_last_window(self):
  result=score_windows([.1,.7,.3],.5,1.1)
  self.assertEqual([p['score'] for p in result['score_windows']],[.1,.7,.3])
  self.assertEqual([p['start_sec'] for p in result['score_windows']],[0,.48,.96])
  self.assertEqual(result['score_windows'][-1]['end_sec'],1.1)
  self.assertEqual(result['above_threshold_windows'],1)
  self.assertIn('not_validated_event_times',result['window_time_scope'])
 def test_invalid_outputs_fail_instead_of_fabricating_scores(self):
  for values,threshold,duration in [([], .5,1),([float('nan')],.5,1),([1.1],.5,1),([.2],2,1),([.2],.5,0)]:
   with self.assertRaises(ValueError):score_windows(values,threshold,duration)
 def test_padded_windows_do_not_claim_offsets_after_recording_end(self):
  result=score_windows([.2,.4,.9],.5,.6)
  self.assertEqual(len(result['score_windows']),2)
  self.assertTrue(all(p['end_sec']<=.6 for p in result['score_windows']))

if __name__=='__main__':unittest.main()
