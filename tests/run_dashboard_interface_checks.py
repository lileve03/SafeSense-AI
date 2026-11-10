import socket
from pathlib import Path
import os,subprocess,sqlite3,time,json,sys
from urllib.request import Request,urlopen
for port in [8000, 8001, 3000]:
 try:
  connection=socket.create_connection(('127.0.0.1',port),timeout=.5)
 except OSError:continue
 else:
  connection.close();raise RuntimeError(f'Test port {port} is already in use; refusing to reuse an existing service')
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'runtime/dashboard-amendments';PROCS=[];RESULTS=[]
ENV={**os.environ,'SAFESENSE_DB_PATH':str(OUT/('interface-'+str(time.time_ns())+'.sqlite3')),'SAFESENSE_API_TOKEN':'local-demo-only','VITE_SAFESENSE_API_TOKEN':'local-demo-only','VITE_API_BASE_URL':'http://127.0.0.1:8000','VITE_AI_BASE_URL':'http://127.0.0.1:8001','SAFESENSE_BACKEND_URL':'http://127.0.0.1:8000','TELEGRAM_MODE':'disabled','TELEGRAM_STAFF_DISPATCH_ENABLED':'false','PYTHONPATH':str(ROOT)}
with sqlite3.connect('file:'+str(ROOT/'runtime/safesense.sqlite3')+'?mode=ro',uri=True) as src,sqlite3.connect(ENV['SAFESENSE_DB_PATH']) as dst:src.backup(dst)
def get(base,path):
 with urlopen(Request(base+path,headers={'X-SafeSense-Token':'local-demo-only'}),timeout=30) as r:return r.status,json.load(r)
def start(name,cmd,cwd,url):
 log=(OUT/(name+'.log')).open('w',encoding='utf-8');p=subprocess.Popen(cmd,cwd=cwd,env=ENV,stdout=log,stderr=subprocess.STDOUT,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0));PROCS.append((p,log))
 for _ in range(240):
  if p.poll() is not None:raise RuntimeError(name+' exited')
  try:
   with urlopen(url,timeout=1) as r:
    if r.status==200:return
  except OSError:pass
  time.sleep(.25)
 raise RuntimeError(name+' startup timeout')
try:
 python=str(ROOT/'.venv-vision/Scripts/python.exe')
 start('interface-backend',[python,'-m','uvicorn','backend.main:app','--host','127.0.0.1','--port','8000'],ROOT,'http://127.0.0.1:8000/health')
 start('interface-ai',[python,'-m','uvicorn','fight_api:app','--host','127.0.0.1','--port','8001'],ROOT,'http://127.0.0.1:8001/health')
 start('interface-frontend',['node',str(ROOT/'dashboard/node_modules/vite/bin/vite.js'),'--host','127.0.0.1','--port','3000','--strictPort'],ROOT/'dashboard','http://127.0.0.1:3000')
 for suite in ['test_overview_duplicates_browser.py','test_camera_unavailable.py','test_private_monitoring_restore.py']:
  print('START',suite,flush=True)
  with (OUT/(suite+'.log')).open('w',encoding='utf-8') as log:run=subprocess.run([python,str(ROOT/'tests'/suite)],env=ENV,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
  row={'suite':suite,'exit_code':run.returncode,'status':'PASS' if run.returncode==0 else 'FAIL'};RESULTS.append(row);print(row,flush=True)
  (OUT/'interface-results.json').write_text(json.dumps(RESULTS,indent=2))
 apis=[]
 for base in ['http://127.0.0.1:8000','http://127.0.0.1:8001']:
  _,schema=get(base,'/openapi.json')
  for path,methods in schema['paths'].items():
   if 'get' in methods and '{' not in path:
    try:status,data=get(base,path);apis.append({'base':base,'path':path,'status':status,'result':'PASS'})
    except Exception as e:apis.append({'base':base,'path':path,'result':'FAIL','error':str(e)})
 _,cams=get('http://127.0.0.1:8000','/monitoring/cameras')
 (OUT/'verified-camera-registry.json').write_text(json.dumps(cams,indent=2))
 (OUT/'api-smoke.json').write_text(json.dumps(apis,indent=2));print('API smoke',len(apis),'routes',flush=True)
finally:
 for p,log in reversed(PROCS):
  if p.poll() is None:p.terminate();p.wait(timeout=20)
  log.close()

sys.exit(1 if any(row['exit_code'] for row in RESULTS) or any(row['result']=='FAIL' for row in apis) else 0)
