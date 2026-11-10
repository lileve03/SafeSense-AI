"""Run retained/new unit suites and save individual executed outcomes."""
from pathlib import Path
import io
import json
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'ai_models/vision'),str(ROOT/'ai_models/private_sensors')]
rows=[]
class RecordedResult(unittest.TextTestResult):
    def addSuccess(self,test):
        super().addSuccess(test);rows.append({'test':test.id(),'status':'PASS','actual':'ok'})
    def addFailure(self,test,err):
        super().addFailure(test,err);rows.append({'test':test.id(),'status':'FAIL','actual':self._exc_info_to_string(err,test)})
    def addError(self,test,err):
        super().addError(test,err);rows.append({'test':test.id(),'status':'FAIL','actual':self._exc_info_to_string(err,test)})
suite=unittest.TestSuite()
for directory,pattern in [('ai_models/vision','test_temporal_logic.py'),('ai_models/private_sensors','test_private_sensor_simulator.py'),('tests','test_evaluate_fsd50k.py'),('tests','test_privacy_adapters.py')]:
    suite.addTests(unittest.TestLoader().discover(str(ROOT/directory),pattern=pattern))
stream=io.StringIO()
result=unittest.TextTestRunner(stream=stream,verbosity=2,resultclass=RecordedResult).run(suite)
out=ROOT/'runtime/test-results';out.mkdir(parents=True,exist_ok=True)
(out/'unit-results.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
(out/'unit-output.txt').write_text(stream.getvalue(),encoding='utf-8')
print(stream.getvalue())
sys.exit(0 if result.wasSuccessful() else 1)
