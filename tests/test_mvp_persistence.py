"""Reload the actual end-to-end test SQLite snapshot in a fresh FastAPI process."""
from pathlib import Path
import os,sys,sqlite3,subprocess,time,json,hashlib
import httpx
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'runtime/mvp-integration'
source=max(OUT.glob('test-*.sqlite3'),key=lambda p:p.stat().st_mtime)
target=OUT/('persistence-'+str(time.time_ns())+'.sqlite3')
with sqlite3.connect('file:'+str(source)+'?mode=ro',uri=True) as original,sqlite3.connect(target) as copied:original.backup(copied)
def snapshot():
 with sqlite3.connect(target) as db:return {(k,i):hashlib.sha256(b.encode()).hexdigest() for k,i,b in db.execute('SELECT kind,id,body FROM records')}
before=snapshot();env={**os.environ,'SAFESENSE_DB_PATH':str(target),'SAFESENSE_API_TOKEN':'mvp-persistence','TELEGRAM_MODE':'disabled'}
headers={'X-SafeSense-Token':'mvp-persistence'};log=(OUT/'persistence-backend.log').open('w',encoding='utf-8')
process=subprocess.Popen([sys.executable,'-m','uvicorn','backend.main:app','--host','127.0.0.1','--port','18774'],cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
try:
 for _ in range(100):
  try:
   response=httpx.get('http://127.0.0.1:18774/health',timeout=1)
   if response.status_code==200:break
  except httpx.HTTPError:pass
  time.sleep(.2)
 client=httpx.Client(base_url='http://127.0.0.1:18774',headers=headers,timeout=10)
 state=client.get('/state').json();sos=next(i for i in state['incidents'] if i['source']=='sos_button')
 report=client.get('/incidents/'+sos['id']+'/report').json()
 assert report['status']=='ACKNOWLEDGED' and report['acknowledged_at'] and report['acknowledged_by']=='Integration test teacher (fixture)'
 assert report['assigned_staff']=='Integration test teacher (fixture)'
 assert all(not e['evidence_media'] for i in state['incidents'] if i['zone_type']=='PRIVATE' for e in i['evidence'])
 evidence=[m for i in state['incidents'] if i['zone_type']=='OPEN_HIDDEN' for e in i['evidence'] for m in e['evidence_media']]
 assert evidence
 assert snapshot()==before
 result={'status':'PASS','records_reloaded_unchanged':len(before),'acknowledged_sos_id':sos['id'],'public_evidence_references_retained':len(evidence),'private_video_references':0,'fresh_backend_process':True}
 (OUT/'persistence-results.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result))
finally:
 process.terminate()
 try:process.wait(timeout=10)
 except subprocess.TimeoutExpired:process.kill();process.wait(timeout=5)
 log.close()
