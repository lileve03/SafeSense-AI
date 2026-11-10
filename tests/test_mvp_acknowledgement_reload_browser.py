"""Actual isolated MVP/browser integration. Notifications disabled; user DB read-only."""
from pathlib import Path
import hashlib,json,os,shutil,socket,sqlite3,subprocess,sys,time,traceback
import httpx
from playwright.sync_api import sync_playwright,expect
ROOT=Path(__file__).resolve().parents[1];sys.stdout.reconfigure(encoding='utf-8')
OUT=ROOT/'runtime/mvp-integration';OUT.mkdir(parents=True,exist_ok=True)
B='http://127.0.0.1:18770';A='http://127.0.0.1:18772';D='http://127.0.0.1:3001';TOKEN='zip-integration-test'
ENV=os.environ.copy();ENV.update(SAFESENSE_DB_PATH=str(OUT/('test-'+str(time.time_ns())+'.sqlite3')),SAFESENSE_API_TOKEN=TOKEN,VITE_SAFESENSE_API_TOKEN=TOKEN,SAFESENSE_BACKEND_URL=B,SAFESENSE_AI_URL=A,VITE_API_BASE_URL=B,VITE_AI_BASE_URL=A,TELEGRAM_MODE='disabled',SAFESENSE_PRECOMPUTE_ON_START='false',SAFESENSE_EVIDENCE_DIR=str(OUT/'evidence'),SAFESENSE_ANNOTATION_DIR=str(OUT/'annotations'),SAFESENSE_ANALYSIS_CACHE_DIR=str(OUT/'cache'))
H={'X-SafeSense-Token':TOKEN};client=httpx.Client(headers=H,timeout=10);processes=[];rows=[]
protected=['dashboard/src/pages/OverviewPage.tsx','dashboard/src/pages/AlertsPage.tsx','fight_api.py','monitoring_ai.py','backend/fight_participants.py','yolo11n-pose.pt','evaluation/outputs/fight_multiclip_v2/fight_multiclip_classifier.joblib','evaluation/outputs/fight_v3/fight_v3_classifier.joblib','dashboard/src/components/private-area/PrivateAreaDigitalTwin3D.tsx','dashboard/src/components/private-area/PrivateAreaMonitoringView.tsx','dashboard/src/pages/LiveMonitoringPage.tsx','dashboard/src/pages/AnalyticsReportsPage.tsx']
hashes={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in protected}
def original_incidents():
 with sqlite3.connect('file:'+str(ROOT/'runtime/safesense.sqlite3')+'?mode=ro',uri=True) as db:return dict(db.execute("SELECT id,body FROM records WHERE kind='incident'"))
before_original=original_incidents()
def check(name,fn):
 try:row={'test':name,'status':'PASS','actual':fn()}
 except Exception as error:row={'test':name,'status':'FAIL','actual':str(error),'trace':traceback.format_exc()}
 rows.append(row);(OUT/'results.json').write_text(json.dumps(rows,indent=2),encoding='utf-8');print(row['status'],name,str(row['actual'])[:600],flush=True)
def start(name,command,cwd,port,url):
 with socket.socket() as probe:probe.bind(('127.0.0.1',port))
 log=(OUT/(name+'.log')).open('w',encoding='utf-8');process=subprocess.Popen(command,cwd=cwd,env=ENV,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW);processes.append((process,log))
 for _ in range(180):
  if process.poll() is not None:raise RuntimeError(name+' exited')
  try:
   if httpx.get(url,timeout=1).status_code==200:return
  except httpx.HTTPError:pass
  time.sleep(.2)
 raise RuntimeError(name+' startup timeout')
def state():return client.get(B+'/state').json()
def counts():
 value=state();return len(value['events']),len(value['incidents'])
source=max(OUT.glob('test-*.sqlite3'),key=lambda p:p.stat().st_mtime);target=OUT/('reload-'+str(time.time_ns())+'.sqlite3')
with sqlite3.connect('file:'+str(source)+'?mode=ro',uri=True) as original,sqlite3.connect(target) as copied:original.backup(copied)
ENV['SAFESENSE_DB_PATH']=str(target)
try:
 start('reload-backend',[sys.executable,'-m','uvicorn','backend.main:app','--host','127.0.0.1','--port','18770'],ROOT,18770,B+'/health')
 start('reload-frontend',[shutil.which('node'),str(ROOT/'dashboard/node_modules/vite/bin/vite.js'),'--host','127.0.0.1','--port','3001','--strictPort'],ROOT/'dashboard',3001,D)
 sos=next(i for i in state()['incidents'] if i['source']=='sos_button');assert sos['status']=='ACKNOWLEDGED'
 with sync_playwright() as pw:
  browser=pw.chromium.launch(headless=True);page=browser.new_page(viewport={'width':1500,'height':1100});page.goto(D+'/#/reports')
  page.get_by_label('Report incident',exact=True).select_option(sos['id']);report=page.get_by_test_id('incident-report');expect(report).to_contain_text('ACKNOWLEDGED')
  report.get_by_role('tab',name='Response',exact=True).click();expect(report).to_contain_text('Integration test teacher (fixture)');expect(page.get_by_role('button',name='Acknowledge incident',exact=True)).to_have_count(0)
  report.screenshot(path=str(OUT/'sos-assignment-acknowledgement.png'))
  result={'status':'PASS','sos_id':sos['id'],'browser_state_after_reload':'ACKNOWLEDGED','assigned_teacher':'fixture only','acknowledged_at':sos['acknowledged_at'],'actual_telegram_delivery':'NOT TESTED'}
  (OUT/'acknowledgement-reload-results.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result));browser.close()
finally:
 for process,log in reversed(processes):
  process.terminate()
  try:process.wait(timeout=15)
  except subprocess.TimeoutExpired:process.kill();process.wait(timeout=5)
  log.close()
