import csv
import tempfile
import unittest
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parents[1] / 'ai_models' / 'acoustic'))
from evaluate_fsd50k import split_tags, read_ground_truth, metrics

class TestPipeline(unittest.TestCase):
    def test_mid_list(self):
        self.assertEqual(split_tags('/m/a,/m/b'), {'/m/a','/m/b'})
    def test_read_labels(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'eval.csv'
            with p.open('w', newline='') as f:
                w=csv.writer(f); w.writerow(['fname','labels','mids']); w.writerow(['123','Screaming,Speech','/m/a,/m/b'])
            self.assertEqual(list(read_ground_truth(p))[0][1], {'/m/a','/m/b'})
    def test_metrics(self):
        self.assertEqual(metrics([1,1,0,0],[1,0,1,0])['TP'],1)

if __name__=='__main__': unittest.main()
