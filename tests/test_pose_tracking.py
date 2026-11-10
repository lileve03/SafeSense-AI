import unittest
from backend.pose_tracking import PoseRuleTracker

class TrackingTests(unittest.TestCase):
    def run_frames(self,tracker,postures,boxes=None):
        rows=[];events=[]
        for i,posture in enumerate(postures):
            people=[{'bbox_xyxy':box} for box in (boxes or [[0,0,100,100]])]
            events+=tracker.update(people,[posture]*len(people),i,30)
            rows.append(people)
        return rows,events
    def test_transition_binary_only(self):
        rows,events=self.run_frames(PoseRuleTracker(),['upright']*3+['horizontal']*5)
        self.assertTrue(rows[-1][0]['fall_rule_active']);self.assertIsNone(rows[-1][0]['fall_score'])
        self.assertEqual(events[0]['time_sec'],round(7/30,6))
    def test_horizontal_without_transition_never_red(self):
        rows,_=self.run_frames(PoseRuleTracker(),['horizontal']*20)
        self.assertFalse(any(p['fall_rule_active'] for f in rows for p in f))
    def test_missing_and_ambiguous_reset(self):
        tracker=PoseRuleTracker();self.run_frames(tracker,['upright']*3)
        tracker.update([],[],3,30)
        rows,_=self.run_frames(tracker,['horizontal']*8)
        self.assertFalse(rows[-1][0]['fall_rule_active'])
        tracker=PoseRuleTracker();self.run_frames(tracker,['upright']*3)
        rows,_=self.run_frames(tracker,['horizontal']*8,[[0,0,100,100],[1,1,101,101]])
        self.assertFalse(any(p['fall_rule_active'] for f in rows for p in f))
    def test_other_person_does_not_inherit_transition(self):
        tracker=PoseRuleTracker();self.run_frames(tracker,['upright']*3)
        rows,_=self.run_frames(tracker,['horizontal']*8,[[200,0,300,100]])
        self.assertFalse(rows[-1][0]['fall_rule_active'])
    def test_only_supported_person_turns_red(self):
        tracker=PoseRuleTracker()
        for i in range(8):
            people=[{'bbox_xyxy':[0,0,100,100]},{'bbox_xyxy':[200,0,300,100]}]
            tracker.update(people,['upright' if i<3 else 'horizontal','upright'],i,30)
        self.assertTrue(people[0]['fall_rule_active'])
        self.assertFalse(people[1]['fall_rule_active'])
        self.assertNotEqual(people[0]['track_id'],people[1]['track_id'])
if __name__=='__main__':unittest.main()
