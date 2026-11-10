import unittest
from backend.fight_participants import annotate_participants

class ParticipantSafetyTests(unittest.TestCase):
 def setup_result(self):
  pose={'input_sha256':'actual-source','pose_frames':[{'frame_index':0,'time_sec':0,'persons':[]}]}
  fight={'input_sha256':'actual-source','model_version':'v3','score':.9,'threshold':.7,'candidate_detected':True,'video_duration_sec':1}
  return pose,fight
 def test_classifier_without_people_never_localizes(self):
  pose,fight=self.setup_result();result=annotate_participants(pose,fight)
  self.assertEqual(result['pose_frames'][0]['persons'],[]);self.assertEqual(result['participant_events'],[])
 def test_negative_classifier_and_provenance_mismatch_abstain(self):
  for change in [{'candidate_detected':False},{'score':.1},{'score':float('nan')},{'input_sha256':'other-source'},{'model_version':'unknown'}]:
   pose,fight=self.setup_result();fight.update(change)
   result=annotate_participants(pose,fight);self.assertFalse(result['participant_heuristic']['enabled'])
 def test_alone_or_missing_keypoints_cannot_form_repeated_interaction(self):
  pose,fight=self.setup_result()
  pose['pose_frames']=[{'frame_index':i,'time_sec':i/30,'persons':[{'bbox_xyxy':[0,0,100,200],'confidence':.9,'keypoints':[]}]} for i in range(20)]
  result=annotate_participants(pose,fight)
  self.assertFalse(any(p['fight_participant'] for f in result['pose_frames'] for p in f['persons']))
  self.assertNotIn('fight_participant',pose['pose_frames'][0]['persons'][0])
 def test_low_confidence_people_ignored(self):
  pose,fight=self.setup_result();pose['pose_frames'][0]['persons']=[{'bbox_xyxy':[0,0,100,200],'confidence':.1,'keypoints':[]}]
  result=annotate_participants(pose,fight);self.assertIsNone(result['pose_frames'][0]['persons'][0]['participant_score'])
if __name__=='__main__':unittest.main()
