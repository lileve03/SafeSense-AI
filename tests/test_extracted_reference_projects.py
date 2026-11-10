"""Execute only the user-named extracted references in isolated copies."""
from pathlib import Path
import os,sys,json,hashlib,shutil,subprocess,time,threading
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import httpx
from playwright.sync_api import sync_playwright,expect
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'runtime/extracted-reference-review';OUT.mkdir(parents=True,exist_ok=True)
PHASE=ROOT/'SafeSense_Phase2_End_to_End_Test/SafeSense_Phase2_End_to_End'
THREE=ROOT/'threejs_test'
files=list(PHASE.glob('*'))+list(THREE.glob('*'))
before={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files if p.is_file()}
rows=[]
def save(name,status,actual):
 row={'test':name,'status':status,'actual':actual};rows.append(row)
 (OUT/'results.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
 print(status,name,str(actual)[:600],flush=True)
frames=json.loads((PHASE/'test_twin.json').read_text(encoding='utf-8-sig'))
events=json.loads((PHASE/'test_events.json').read_text(encoding='utf-8-sig'))
(OUT/'folder-manifest.json').write_text(json.dumps({'files':before,'frames':len(frames),'duration':frames[-1]['time'],'annotations':events},indent=2),encoding='utf-8')
copy=OUT/('phase2-http-'+str(time.time_ns()));copy.mkdir()
for name in ('server.py','index.html','test_twin.json','test_events.json'):shutil.copy2(PHASE/name,copy/name)
log=(OUT/'phase2-http.log').open('w',encoding='utf-8')
process=subprocess.Popen([sys.executable,str(copy/'server.py')],cwd=copy,env={**os.environ,'PORT':'18778'},stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
try:
 for _ in range(100):
  try:
   health=httpx.get('http://127.0.0.1:18778/state',timeout=1)
   if health.status_code==200:break
  except httpx.HTTPError:pass
  time.sleep(.1)
 c=httpx.Client(base_url='http://127.0.0.1:18778',timeout=10)
 try:
  response=c.get('/health');save('Reference standalone health endpoint','PASS' if response.status_code==200 else 'FAIL',{'status':response.status_code})
 except httpx.HTTPError as exc:
  save('Reference standalone health endpoint','FAIL',{'error':type(exc).__name__,'root_cause':'importlib.util not imported by standalone server','not_imported_into_MVP':True})
 initial=c.get('/state').json()
 assert initial['source']=='synthetic_point_cloud' and not initial['deployment_ready'] and len(frames)==121
 save('Reference radar is supplied synthetic replay, not hardware inference','PASS',{'frames':len(frames),'duration':initial['duration'],'synthetic_tracks':initial['count'],'FastAPI':False})
 c.post('/replay/start',json={})
 seek=c.post('/replay/seek',json={'time':6}).json()
 side_effects=len(seek['incidents'])-len(initial['incidents'])
 save('Reference seek while playing must not insert historical incidents','FAIL' if side_effects else 'PASS',{'unexpected_incidents_added':side_effects,'not_imported_into_MVP':True})
 c.post('/replay/pause',json={})
 sos=c.post('/event',json={'event_type':'sos','source':'sos_button'});assert sos.status_code==201
 identifier=sos.json()['incident_id'];assert c.post('/incidents/'+str(identifier)+'/ack',json={}).status_code==200
 assert next(e for e in c.get('/state').json()['incidents'] if e['id']==identifier)['acknowledged']==1
 save('Actual reference SOS HTTP and SQLite acknowledgement','PASS',{'incident_id':identifier,'independent_sos':True,'only_isolated_database_written':True})
finally:
 process.terminate();process.wait(timeout=10);log.close()
audio_copy=OUT/('phase2-audio-'+str(time.time_ns()));audio_copy.mkdir()
for name in ('server.py','test_twin.json','test_events.json'):shutil.copy2(PHASE/name,audio_copy/name)
with (OUT/'reference-acoustic.log').open('w',encoding='utf-8') as stream:
 result=subprocess.run([str(ROOT/'.venv-acoustic/Scripts/python.exe'),str(ROOT/'tests/reference_acoustic_runner.py'),str(ROOT),str(audio_copy/'server.py'),str(OUT/'reference-acoustic-results.json')],cwd=ROOT,
  env={**os.environ,'CUDA_VISIBLE_DEVICES':'-1','TF_CPP_MIN_LOG_LEVEL':'2'},stdout=stream,stderr=subprocess.STDOUT,timeout=120,creationflags=subprocess.CREATE_NO_WINDOW)
assert result.returncode==0,'Inspect reference-acoustic.log'
save('Actual Phase2 infer_audio, audio_peak_events and explicit experimental fusion','PASS',json.loads((OUT/'reference-acoustic-results.json').read_text(encoding='utf-8')))
class Static(BaseHTTPRequestHandler):
 def log_message(self,*args):pass
 def do_GET(self):
  name=self.path.split('?')[0]
  if name in ('/','/index.html'):
   body=(THREE/'index.html').read_text(encoding='utf-8-sig').replace('https://cdn.jsdelivr.net/npm/three@0.180.0/build/','/vendor/').replace('https://cdn.jsdelivr.net/npm/three@0.180.0/examples/jsm/','/addons/').encode();mime='text/html'
  else:
   base=ROOT/'dashboard/node_modules/three/build' if name.startswith('/vendor/') else ROOT/'dashboard/node_modules/three/examples/jsm' if name.startswith('/addons/') else THREE
   relative=name.removeprefix('/vendor/').removeprefix('/addons/').lstrip('/');path=(base/relative).resolve()
   if not path.is_relative_to(base.resolve()) or not path.is_file():self.send_error(404);return
   body=path.read_bytes();mime='text/javascript' if path.suffix=='.js' else 'application/octet-stream'
  self.send_response(200);self.send_header('Content-Type',mime);self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
server=ThreadingHTTPServer(('127.0.0.1',18779),Static)
thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
try:
 with sync_playwright() as pw:
  browser=pw.chromium.launch(headless=True,args=['--enable-unsafe-swiftshader'])
  page=browser.new_page(viewport={'width':1400,'height':1000});errors=[]
  page.on('pageerror',lambda e:errors.append(str(e)))
  page.goto('http://127.0.0.1:18779');expect(page.locator('canvas').first).to_be_visible();page.wait_for_timeout(700)
  gl=page.locator('canvas').first.evaluate('c=>{const g=c.getContext("webgl2");return !!g&&!g.isContextLost()}')
  assert gl and not errors,errors
  buttons=page.get_by_role('button').all_text_contents();page.screenshot(path=str(OUT/'actual-reference-threejs.png'))
  save('Actual threejs_test scene renders against compatible local installed Three.js','PASS',{'WebGL':gl,'local_Three_version':'0.186.1','reference_CDN_version_not_fetched':'0.180.0','button_labels':buttons[:12],'browser_errors':errors,'no_inference_backend':True})
  browser.close()
finally:
 server.shutdown();server.server_close();thread.join(timeout=5)
assert all(hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==sha for path,sha in before.items())
save('Both extracted reference folders unchanged including original incidents.db','PASS',{'unchanged_files':len(before)})
