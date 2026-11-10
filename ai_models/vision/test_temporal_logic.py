import unittest
from temporal_logic import Observation,TemporalAnalyzer

class TestTemporal(unittest.TestCase):
    def test_normal_stays_quiet(self):
        a=TemporalAnalyzer()
        out=[]
        for i in range(30):
            out+=a.update(1,Observation(i*.1,(.4,.5),False,True,True))
        self.assertEqual(out,[])

    def test_upright_to_horizontal_candidate(self):
        a=TemporalAnalyzer()
        out=[]
        for i in range(12):
            t=i*.1
            out+=a.update(1,Observation(t,(.4,.5),i>=7,i<7,True))
        self.assertIn('fall',out)

    def test_horizontal_without_transition_not_fall(self):
        a=TemporalAnalyzer()
        out=[]
        for i in range(15):
            out+=a.update(1,Observation(i*.1,(.4,.5),True,False,True))
        self.assertNotIn('fall',out)

    def test_sustained_motion_candidate(self):
        a=TemporalAnalyzer(motion_threshold=.14)
        out=[]
        for i in range(12):
            out+=a.update(1,Observation(i*.1,(.25+i*.025,.5),False,True,True))
        self.assertIn('rapid_motion',out)

if __name__=='__main__':unittest.main()
