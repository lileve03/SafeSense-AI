"""Isolated backend regressions for Analytics & Reports completion."""
from pathlib import Path
import json,os,sys,time,unittest
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'runtime/analytics-reports-final';OUT.mkdir(parents=True,exist_ok=True)
os.environ.update(SAFESENSE_DB_PATH=str(OUT/('backend-regression-'+str(time.time_ns())+'.sqlite3')),TELEGRAM_MODE='disabled',TELEGRAM_STAFF_DISPATCH_ENABLED='false')
sys.path.insert(0,str(ROOT));rows=[]
class Results(unittest.TextTestResult):
 def addSuccess(self,test):super().addSuccess(test);rows.append({'test':test.id(),'status':'PASS'})
 def addFailure(self,test,err):super().addFailure(test,err);rows.append({'test':test.id(),'status':'FAIL','reason':self._exc_info_to_string(err,test)})
 def addError(self,test,err):super().addError(test,err);rows.append({'test':test.id(),'status':'FAIL','reason':self._exc_info_to_string(err,test)})
suite=unittest.TestSuite()
for pattern in ['test_incident_response_workflow.py','test_notification_safety.py','test_privacy_adapters.py','test_overview_insights.py','test_inference_queue.py','test_automatic_monitoring.py']:
 suite.addTests(unittest.defaultTestLoader.discover(str(ROOT/'tests'),pattern=pattern))
with (OUT/'backend-tests.log').open('w',encoding='utf-8') as stream:result=unittest.TextTestRunner(stream=stream,verbosity=2,resultclass=Results).run(suite)
(OUT/'backend-results.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
print(json.dumps({'tests':result.testsRun,'passed':len([r for r in rows if r['status']=='PASS']),'failures':len(result.failures),'errors':len(result.errors),'Telegram':'mocked transport only'}))
sys.exit(not result.wasSuccessful())
