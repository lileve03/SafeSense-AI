"""Isolated CPU monitoring/cache regressions; external notification transports are mocked."""
from pathlib import Path
import json,os,sys,time,unittest
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'runtime/cpu-visualization';OUT.mkdir(parents=True,exist_ok=True)
os.environ.update(SAFESENSE_DB_PATH=str(OUT/('regression-'+str(time.time_ns())+'.sqlite3')),TELEGRAM_MODE='disabled',SAFESENSE_ANALYSIS_CACHE_DIR=str(OUT/'unit-cache'),SAFESENSE_EVIDENCE_DIR=str(OUT/'unit-evidence'))
sys.path.insert(0,str(ROOT));rows=[]
class Results(unittest.TextTestResult):
 def addSuccess(self,test):super().addSuccess(test);rows.append({'test':test.id(),'status':'PASS'})
 def addFailure(self,test,err):super().addFailure(test,err);rows.append({'test':test.id(),'status':'FAIL','reason':self._exc_info_to_string(err,test)})
 def addError(self,test,err):super().addError(test,err);rows.append({'test':test.id(),'status':'FAIL','reason':self._exc_info_to_string(err,test)})
suite=unittest.TestSuite()
for pattern in ['test_inference_queue.py','test_automatic_monitoring.py','test_durable_analysis_cache.py','test_privacy_adapters.py','test_incident_response_workflow.py','test_notification_safety.py','test_overview_insights.py']:
 suite.addTests(unittest.defaultTestLoader.discover(str(ROOT/'tests'),pattern=pattern))
with (OUT/'backend-tests.log').open('w',encoding='utf-8') as stream:result=unittest.TextTestRunner(stream=stream,verbosity=2,resultclass=Results).run(suite)
(OUT/'backend-results.json').write_text(json.dumps(rows,indent=2));print(json.dumps({'tests':result.testsRun,'failures':len(result.failures),'errors':len(result.errors)}));sys.exit(not result.wasSuccessful())
