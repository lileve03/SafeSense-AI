import socket
from pathlib import Path
import subprocess,time,json,hashlib,sys,os
for port in [18000, 18001, 18100, 18101, 18020, 3001]:
 try:
  connection=socket.create_connection(('127.0.0.1',port),timeout=.5)
 except OSError:continue
 else:
  connection.close();raise RuntimeError(f'Test port {port} is already in use; refusing to reuse an existing service')
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'runtime/dashboard-amendments';OUT.mkdir(parents=True,exist_ok=True)
files=[p for folder in ['dashboard/src','backend'] for p in (ROOT/folder).rglob('*') if p.is_file() and '__pycache__' not in str(p)]
(OUT/'source-before.json').write_text(json.dumps({str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files},indent=2))
python=str(ROOT/'.venv-vision/Scripts/python.exe');rows=[]
suites=['test_camera_playback.py','test_detection_monitoring.py','test_audit_evidence.py','test_real_monitoring.py','test_scenario_library.py','test_analytics_browser.py','test_reports_exports.py','run_unit_checks.py']
commands=[(s,[python,str(ROOT/'tests'/s)]) for s in suites]
commands += [('backend-unit-safety',[python,'-m','unittest','discover','-s','tests','-p','test_notification_safety.py','-v']),('backend-response',[python,'-m','unittest','discover','-s','tests','-p','test_incident_response_workflow.py','-v']),('overview-unit',[python,'-m','unittest','discover','-s','tests','-p','test_overview_insights.py','-v']),('legacy-api',[python,str(ROOT/'tests/test_integration_demo.py')])]
for name,command in commands:
 print('START',name,flush=True);started=time.time()
 with (OUT/(name+'.log')).open('w',encoding='utf-8') as log:
  result=subprocess.run(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,env={**os.environ,'PYTHONPATH':str(ROOT),'TELEGRAM_MODE':'disabled','TELEGRAM_STAFF_DISPATCH_ENABLED':'false'},creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
 row={'suite':name,'exit_code':result.returncode,'status':'PASS' if result.returncode==0 else 'FAIL','seconds':round(time.time()-started,2),'log':str(OUT/(name+'.log'))};rows.append(row)
 (OUT/'suite-results.json').write_text(json.dumps(rows,indent=2));print(row,flush=True)
print('COMPLETE',flush=True)

sys.exit(1 if any(row['exit_code'] for row in rows) else 0)
