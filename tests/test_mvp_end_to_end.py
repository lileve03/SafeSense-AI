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
# A fixture roster proves assignment logic; it is not an actual teacher or external recipient.
roster=OUT/'fixture-staff-routes.json';roster.write_text(json.dumps([{'zone_id':'ZONE_TOILET_BLINDSPOT','staff':'Integration test teacher (fixture)','role':'duty_teacher','active':True}]),encoding='utf-8')
ENV['SAFESENSE_STAFF_ROUTES']=str(roster)
ENV['SAFESENSE_ANALYSIS_CACHE_DIR']=str(OUT/('cold-cache-'+str(time.time_ns())))
measurements=[];completed={};jobs={};sos_id=None
try:
 start('backend',[sys.executable,'-m','uvicorn','backend.main:app','--host','127.0.0.1','--port','18770'],ROOT,18770,B+'/health')
 start('inference',[sys.executable,'-m','uvicorn','fight_api:app','--host','127.0.0.1','--port','18772'],ROOT,18772,A+'/health')
 start('frontend',[shutil.which('node'),str(ROOT/'dashboard/node_modules/vite/bin/vite.js'),'--host','127.0.0.1','--port','3001','--strictPort'],ROOT/'dashboard',3001,D)
 with sync_playwright() as pw:
  browser=pw.chromium.launch(headless=True,args=['--enable-unsafe-swiftshader']);page=browser.new_page(viewport={'width':1500,'height':1100});page.set_default_timeout(25000);errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
  def response(r):
   if '/monitoring/jobs' in r.url and r.status in (200,202):
    try:
     row=r.json()
     if row.get('status')=='COMPLETED':completed[row['camera_id']]=row
    except Exception:pass
  page.on('response',response)
  page.goto(D);page.locator('aside').get_by_role('button',name='Live Monitoring',exact=True).click()
  panel=page.get_by_test_id('camera-monitoring');video=panel.locator('video').first
  cameras=client.get(B+'/monitoring/cameras').json()
  def camera(c,cached=False):
   page.evaluate("""()=>{window.mvpStart=performance.now();window.mvpVideo=null;window.mvpOverlay=null;window.mvpObserver?.disconnect();window.mvpObserver=new MutationObserver(()=>{const v=document.querySelector('[data-testid=camera-monitoring] video');if(window.mvpVideo===null&&v?.readyState>=2&&!v.paused&&v.currentTime>0.05)window.mvpVideo=performance.now()-window.mvpStart;if(window.mvpOverlay===null&&document.querySelector('[data-testid=camera-monitoring] [data-testid=person-box]'))window.mvpOverlay=performance.now()-window.mvpStart;});window.mvpObserver.observe(document.querySelector('[data-testid=camera-monitoring]'),{childList:true,subtree:true,attributes:true});}""")
   panel.get_by_role('button',name=c['camera_name']+' '+c['camera_id']+' '+c['source_type'],exact=True).click()
   expect(video).to_have_attribute('data-camera-id',c['camera_id'])
   page.wait_for_function("()=>{const v=document.querySelector('[data-testid=camera-monitoring] video');return v?.readyState>=2&&!v.paused&&v.currentTime>.1}")
   expect(panel.get_by_test_id('fight-video-overlay')).to_be_visible(timeout=300000)
   row=completed[c['camera_id']];result=row['result'];jobs[c['camera_id']]=row
   assert row['status']=='COMPLETED' and not result['model_errors']
   assert len(result['model_results'])==2 and row['resolved_models']==[c['fight_model'],'pose']
   assert bool(row.get('cache_hit'))==cached,(row.get('cache_hit'),cached)
   frames=result['pose_frames'];samples=[f for f in frames if f['persons']];assert samples
   f=samples[len(samples)//2]
   fallframes=[f for f in frames if any(p.get('fall_candidate') for p in f['persons'])]
   if c['camera_id']=='CAM_STAIRCASE':
    assert fallframes;f=fallframes[len(fallframes)//2]
   video.evaluate('(v,t)=>{v.pause();v.currentTime=t}',f['time_sec']+.001)
   expect(panel.get_by_test_id('video-detection-overlay')).to_have_attribute('data-frame-index',str(f['frame_index']))
   expect(panel.get_by_test_id('person-box')).to_have_count(len(f['persons']));assert panel.get_by_test_id('pose-bone').count()>0
   for n,p in enumerate(f['persons']):
    coords=panel.get_by_test_id('person-box').nth(n).evaluate('(e)=>[e.getAttribute("x"),e.getAttribute("y"),e.getAttribute("width"),e.getAttribute("height")].map(Number)')
    x1,y1,x2,y2=p['bbox_xyxy'];assert all(abs(a-b)<.001 for a,b in zip(coords,[x1,y1,x2-x1,y2-y1]))
   if c['camera_id']=='CAM_STAIRCASE':assert panel.locator('[data-fall-candidate=true] [data-testid=person-box]').first.get_attribute('stroke')=='#ef4444'
   fight=next(m for m in result['model_results'] if m['model_version'] in ('v2','v3'))
   assert not fight.get('pose_frames') and not fight.get('person_boxes')
   for p in f['persons']:
    if p.get('fight_participant'):assert p.get('interaction_track_id') and p.get('participant_score') is not None
   for output in result['model_results']:
    delivery=output['event_delivery']
    if output['candidate_detected']:
     identifier=delivery['incident_id'];assert identifier
     report=client.get(B+'/incidents/'+identifier+'/report').json();assert report['zone_id']==c['zone_id'] and report['zone_type']=='OPEN_HIDDEN'
     assert any(e['camera_id']==c['camera_id'] for e in report['evidence'])
     zone=next(z for z in client.get(B+'/zones').json() if z['id']==c['zone_id']);assert identifier in zone['active_incident_ids']
     assert output['evidence_media']
     for media in output['evidence_media']:
      metadata=client.get(A+'/monitoring/incidents/'+identifier+'/evidence/'+media['id']+'/metadata').json();assert metadata['camera_id']==c['camera_id']
      assert client.get(A+media['url'],headers={'Range':'bytes=0-511'}).status_code==206
   item={'camera':c['camera_id'],'cached':cached,'video_ms':page.evaluate('window.mvpVideo'),'first_box_ms':page.evaluate('window.mvpOverlay'),'cpu_sec':result['total_processing_sec'],'frames':len(frames),'person_detections':sum(len(f['persons']) for f in frames),'fight_score':fight['score'],'fight_version':fight['model_version'],'fall_candidate_frames':len(fallframes)}
   measurements.append(item);(OUT/'performance.json').write_text(json.dumps(measurements,indent=2),encoding='utf-8')
   panel.screenshot(path=str(OUT/(c['camera_id']+('-cached' if cached else '-cold')+'.png')))
   return item
  for c in cameras:check('Public camera autoplay genuine Fight + Fall evidence and incident: '+c['camera_id'],lambda c=c:camera(c))
  for c in (cameras[0],cameras[-1]):check('Cached synchronized camera replay: '+c['camera_id'],lambda c=c:camera(c,True))
  def public_twin():
   c=next(c for c in cameras if c['camera_id']=='CAM_CORRIDOR_A');row=jobs[c['camera_id']];identifier=next(m['event_delivery']['incident_id'] for m in row['result']['model_results'] if m['candidate_detected'])
   page.locator('aside').get_by_role('button',name='Digital Twin Map',exact=True).click();expect(page.locator('[data-zone-id="'+c['zone_id']+'"]')).to_have_attribute('data-risk-level','OBSERVE')
   page.screenshot(path=str(OUT/'public-digital-twin.png'))
   return {'incident_id':identifier,'map_risk':'OBSERVE'}
  check('Public incident reaches existing Digital Twin shared state',public_twin)
  page.locator('[data-zone-id="ZONE_TOILET_BLINDSPOT"] polygon').first.click();scene=page.get_by_test_id('private-twin-scene')
  def private():
   expect(scene.locator('canvas')).to_be_visible();expect(scene).to_have_attribute('data-positioned-occupants','0')
   page.get_by_label('Raw sensor recording',exact=True).select_option('radar_raw_fall');page.get_by_label('Use authorized offline research input').check();page.get_by_role('button',name='Analyze recording',exact=True).click();expect(page.get_by_text('Model: SVM_RBF-LOSO-reconstructed',exact=True)).to_be_visible(timeout=90000)
   page.get_by_label('Raw sensor recording',exact=True).select_option('acoustic_scream');page.get_by_role('button',name='Analyze recording',exact=True).click();expect(page.get_by_text('Model: YAMNet-pretrained-local-cache',exact=True)).to_be_visible(timeout=90000)
   expect(scene).to_have_attribute('data-acoustic-active','true');expect(scene).to_have_attribute('data-positioned-occupants','0')
   real=[i for i in state()['incidents'] if i['zone_id']=='ZONE_TOILET_BLINDSPOT' and i['processing_mode']=='real_model'];assert len(real)==2 and all(i['level']=='OBSERVE' for i in real)
   page.get_by_role('button',name='Simulate radar + acoustic fusion',exact=True).click()
   for _ in range(100):
    fusion=[i for i in state()['incidents'] if i['zone_id']=='ZONE_TOILET_BLINDSPOT' and i['level']=='HIGH' and i['processing_mode']=='simulation']
    if fusion:break
    page.wait_for_timeout(100)
   assert fusion;assert {'radar','yamnet'} <= {e['source'] for e in fusion[-1]['evidence']}
   assert not page.get_by_test_id('private-monitoring-view').locator('video,img,audio').count()
   scene.screenshot(path=str(OUT/'private-sensor-fusion.png'))
   return {'raw_recordings':2,'unrelated_recordings_fused':False,'fusion':'HIGH labeled simulation','incident_id':fusion[-1]['id']}
  check('Toilet original room to real sensor inference / labeled fusion / same SQLite incidents',private)
  def sos():
   global sos_id
   page.get_by_role('button',name='ACTIVATE SOS EMERGENCY',exact=True).click()
   submitted=[]
   def fail_after_commit(route):
    payload=route.request.post_data_json
    if payload.get('type')=='sos':
     submitted.append(payload);response=route.fetch();assert response.status==200
     route.fulfill(status=503,content_type='application/json',body=json.dumps({'detail':'TEST: response lost after actual backend commit'}))
    else:route.continue_()
   page.route(B+'/event',fail_after_commit)
   page.get_by_role('button',name='Confirm Test Broadcast',exact=True).click()
   expect(page.get_by_text('Authorize Prototype SOS Test',exact=True)).to_be_visible()
   page.wait_for_function("()=>document.body.innerText.includes('Retry retains the same request ID')")
   before=counts();page.unroute(B+'/event',fail_after_commit)
   with page.expect_response(lambda r:r.url==B+'/event' and r.request.method=='POST') as response:page.get_by_role('button',name='Confirm Test Broadcast',exact=True).click()
   delivered=response.value.json();assert delivered['deduplicated'] and delivered['event']['id']==submitted[0]['event_id'];assert counts()==before
   sos_id=delivered['incident']['id'];expect(scene).to_have_attribute('data-sos-active','true');report=client.get(B+'/incidents/'+sos_id+'/report').json()
   assert report['assigned_staff']=='Integration test teacher (fixture)' and report['level']=='CRITICAL' and report['zone_type']=='PRIVATE';assert not any(e['evidence_media'] for e in report['evidence'])
   scene.get_by_test_id('private-incident-indicator').click();expect(page.get_by_test_id('incident-evidence')).to_have_attribute('data-incident-id',sos_id)
   page.get_by_role('button',name='Preview local notification (no send)',exact=True).click();expect(page.get_by_test_id('incident-evidence')).to_contain_text('DISABLED')
   page.get_by_role('button',name='Close',exact=True).click()
   page.locator('aside').get_by_role('button',name='Analytics & Reports',exact=True).click();page.get_by_label('Report incident',exact=True).select_option(sos_id)
   report_ui=page.get_by_test_id('incident-report');report_ui.get_by_role('tab',name='Response',exact=True).click();page.get_by_label('Report reviewing staff',exact=True).fill('Integration test teacher (fixture)');page.get_by_role('button',name='Acknowledge incident',exact=True).click()
   for _ in range(100):
    report=client.get(B+'/incidents/'+sos_id+'/report').json()
    if report['status']=='ACKNOWLEDGED':break
    page.wait_for_timeout(100)
   assert report['acknowledged_by']=='Integration test teacher (fixture)' and report['assigned_staff']=='Integration test teacher (fixture)'
   expect(report_ui).to_contain_text('ACKNOWLEDGED')
   expect(page.get_by_role('button',name='Acknowledge incident',exact=True)).to_have_count(0)
   page.screenshot(path=str(OUT/'sos-assignment-acknowledgement.png'))
   return {'incident_id':sos_id,'assigned_teacher':'fixture only','retry_same_event':True,'acknowledged_by':report['acknowledged_by'],'telegram':'DISABLED - no external message sent'}
  check('Confirmed private SOS / idempotent retry / fixture teacher / notification preview / browser acknowledgement',sos)
  def reports_states():
   expect(page.get_by_test_id('analytics-reports')).to_be_visible();expect(page.get_by_test_id('incident-report')).to_contain_text('ACKNOWLEDGED')
   with page.expect_download() as downloaded:page.get_by_role('button',name='Download CSV',exact=True).click()
   downloaded.value.save_as(str(OUT/'filtered-incidents.csv'))
   import csv
   exported=list(csv.DictReader((OUT/'filtered-incidents.csv').open(encoding='utf-8-sig')))
   sos_export=next(r for r in exported if r['Incident ID']==sos_id)
   assert sos_export['Acknowledged At'] and sos_export['Review Status']=='under_review',sos_export
   for path in ('/#/analytics','/#/reports'):
    page.goto(D+path);expect(page.get_by_test_id('analytics-reports')).to_be_visible()
   page.locator('aside').get_by_role('button',name='Alerts',exact=True).click();expect(page.locator('main').get_by_text(sos_id[:8],exact=False).first).to_be_visible()
   assert all(i['zone_type']=='PRIVATE' and not any(e['evidence_media'] for e in i['evidence']) for i in state()['incidents'] if i['zone_id']=='ZONE_TOILET_BLINDSPOT')
   assert original_incidents()==before_original and all(hashlib.sha256((ROOT/n).read_bytes()).hexdigest()==d for n,d in hashes.items())
   assert not errors,errors
   return {'csv_contains_acknowledged_sos':True,'old_routes':True,'alerts_same_id':True,'original_incidents_unchanged':len(before_original),'protected_files':len(hashes),'browser_errors':errors}
  check('Shared state reports CSV legacy routes Alerts privacy and original feature preservation',reports_states)
  browser.close()
finally:
 for process,log in reversed(processes):
  process.terminate()
  try:process.wait(timeout=15)
  except subprocess.TimeoutExpired:process.kill();process.wait(timeout=5)
  log.close()
sys.exit(any(r['status']=='FAIL' for r in rows))
