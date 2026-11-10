"""Measure service startup separately from replay using the completed isolated benchmark namespace."""
from pathlib import Path
import json,os,sys,time,sqlite3,subprocess
import httpx,psutil
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'runtime/cpu-visualization/optimized'
first=json.loads((OUT/'performance.json').read_text())[0]['id'];database=None;rows=[]
for candidate in OUT.glob('test-*.sqlite3'):
 with sqlite3.connect('file:'+str(candidate)+'?mode=ro',uri=True) as db:
  if db.execute("SELECT 1 FROM records WHERE kind='job' AND id=?",(first,)).fetchone():
   database=candidate;rows=[json.loads(r[0]) for r in db.execute("SELECT body FROM records WHERE kind='job'")];break
assert database
prepared=next(r for r in reversed(rows) if r.get('result',{}).get('evidence_media'))
media=prepared['result']['evidence_media'][0]['id'];evidence=next(OUT.glob('evidence-*/'+media+'.json')).parent
artifact=prepared['result']['annotated_video_url'].rsplit('/',1)[-1];annotations=next(OUT.glob('annotations-*/'+artifact+'.mp4')).parent
ENV={**os.environ,'SAFESENSE_DB_PATH':str(database),'SAFESENSE_EVIDENCE_DIR':str(evidence),'SAFESENSE_ANNOTATION_DIR':str(annotations),'SAFESENSE_ANALYSIS_CACHE_DIR':str(OUT/'analysis-cache'),'SAFESENSE_API_TOKEN':'monitoring-integration-test','SAFESENSE_BACKEND_URL':'http://127.0.0.1:18140','TELEGRAM_MODE':'disabled'}
base='http://127.0.0.1:18142';log=(OUT/'startup-only.log').open('w');started=time.perf_counter();process=subprocess.Popen([sys.executable,'-m','uvicorn','fight_api:app','--host','127.0.0.1','--port','18142'],cwd=ROOT,env=ENV,stdout=log,stderr=subprocess.STDOUT,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
try:
 with httpx.Client(timeout=15,headers={'X-SafeSense-Token':ENV['SAFESENSE_API_TOKEN']}) as client:
  for _ in range(200):
   if process.poll() is not None:raise RuntimeError('Service exited')
   try:
    if client.get(base+'/health').status_code==200:break
   except httpx.HTTPError:pass
   time.sleep(.1)
  else:raise RuntimeError('Startup timeout')
  boot=time.perf_counter()-started;requested=time.perf_counter()
  response=client.post(base+'/monitoring/jobs',json={'scenario_id':'adl_02','camera_id':'CAM_HALL','zone_id':'ZONE_SCHOOL_HALL','model':'all','authorized':True});response.raise_for_status();row=response.json();elapsed=time.perf_counter()-requested
  assert row['cache_hit'] and row['cache_tier']=='disk'
  tree=[psutil.Process(process.pid),*psutil.Process(process.pid).children(recursive=True)];rss=sum(p.memory_info().rss for p in tree)/1048576
  result={'startup_to_healthy_sec':round(boot,3),'first_disk_cache_API_ms':round(elapsed*1000,2),'cache_hit':True,'cache_tier':row['cache_tier'],'job_id':row['id'],'current_process_tree_RSS_MB':round(rss,1),'scope':'Service import/startup separated from API replay; no fresh inference performed'}
  (OUT/'restart-startup.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
finally:
 process.terminate();process.wait(timeout=10);log.close()
