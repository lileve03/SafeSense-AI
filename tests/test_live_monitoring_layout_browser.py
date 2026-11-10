"""Browser UI verification with actual recorded model results and original video sources.
Job submissions are replayed from genuine completed SQLite jobs to avoid new inference/incident/Telegram writes.
"""
from pathlib import Path
import sqlite3,json,hashlib,copy
from playwright.sync_api import sync_playwright,expect
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'runtime/live-monitoring-layout';OUT.mkdir(parents=True,exist_ok=True)
results=[]
def passed(name):
 results.append({'test':name,'result':'PASS'});print('PASS:',name,flush=True)
def rows():
 with sqlite3.connect('file:'+str(ROOT/'runtime/safesense.sqlite3')+'?mode=ro',uri=True) as db:return db.execute('SELECT kind,id,body FROM records ORDER BY kind,id').fetchall()
before=rows();jobs=[json.loads(body) for kind,id,body in before if kind=='job']
cameras={'CAM_CORRIDOR_A':'Corridor A','CAM_CANTEEN':'Canteen','CAM_STAIRCASE':'Staircase','CAM_ENTRANCE':'School Entrance','CAM_HALL':'School Hall'}
saved={}
for camera in cameras:
 matches=[r for r in jobs if r.get('status')=='COMPLETED' and r.get('result',{}).get('camera_id')==camera and r['result'].get('pose_frames') and not r['result'].get('model_errors')]
 assert matches,camera
 # Prefer the current two-detector camera policy when present; legacy actual outputs remain supported.
 preferred=[r for r in matches if len(r['result'].get('model_results',[]))==2]
 saved[camera]=(preferred or matches)[-1]
protected=['dashboard/src/components/layout/Topbar.tsx','dashboard/src/components/layout/Sidebar.tsx','dashboard/src/context/SafeSenseContext.tsx','dashboard/src/components/analysis/VideoDetectionOverlay.tsx','dashboard/src/lib/videoDetections.ts','backend/main.py','monitoring_ai.py','fight_api.py']
hashes={n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in protected}
requests=[];errors=[]
with sync_playwright() as pw:
 browser=pw.chromium.launch(headless=True)
 page=browser.new_page(viewport={'width':1440,'height':1050})
 page.set_default_timeout(15000)
 page.on('pageerror',lambda e:errors.append(str(e)))
 def replay(route):
  request=route.request
  if request.method!='POST':route.continue_();return
  if request.url.endswith('/release'):route.fulfill(status=200,content_type='application/json',body='{}');return
  body=request.post_data_json;camera=body['camera_id'];assert body['model']=='all'
  requests.append(body)
  route.fulfill(status=200,content_type='application/json',body=json.dumps(saved[camera]))
 page.route('**/monitoring/jobs',replay);page.route('**/monitoring/jobs/release',replay)
 page.goto('http://127.0.0.1:3000',wait_until='domcontentloaded')
 header=page.locator('header').first.get_attribute('class');sidebar=page.locator('aside').first.get_attribute('class')
 page.locator('aside').first.get_by_role('button',name='Live Monitoring',exact=True).click()
 panel=page.get_by_test_id('camera-monitoring');expect(panel).to_be_visible()
 selector=panel.get_by_label('Camera selector',exact=True)
 expect(selector.get_by_role('button')).to_have_count(5)
 assert not any(text in page.locator('main').inner_text() for text in ['Authorized research recordings assigned to demo zones.','Offline CPU analysis; no live hardware verified.','Backend events'])
 assert page.locator('header').first.get_attribute('class')==header
 assert page.locator('aside').first.get_attribute('class')==sidebar
 passed('Running Live Monitoring uses the existing camera component; repeated banner/descriptions are removed')
 for camera,name in cameras.items():
  button=selector.get_by_role('button',name=name+' '+camera,exact=True);button.click()
  expect(button).to_have_attribute('aria-pressed','true')
  video=panel.locator('video').first;expect(video).to_have_attribute('data-camera-id',camera)
  page.wait_for_function("()=>{const v=document.querySelector('[data-testid=camera-monitoring] video');return v?.readyState>=2&&!v.paused&&v.currentTime>.05}")
  expect(panel.get_by_test_id('monitoring-outcome')).to_be_visible()
  expect(panel.get_by_test_id('video-detection-overlay')).to_have_attribute('data-camera-id',camera)
  assert 'monitoring/sources/' in video.get_attribute('src')
  result=saved[camera]['result']
  # Pause, seek to actual decoded-frame timestamps and compare the overlay's frame identity.
  video.evaluate('(v)=>v.pause()')
  frames=result['pose_frames'];fps=result['annotation_alignment']['fps']
  for index in [min(5,len(frames)-1),min(25,len(frames)-1)]:
   frame=frames[index];position=frame['time_sec']+.001
   video.evaluate('(v,t)=>{v.currentTime=t}',position)
   expected=str(frame['frame_index'])
   expect(panel.get_by_test_id('video-detection-overlay')).to_have_attribute('data-frame-index',expected)
   expect(panel.get_by_test_id('frame-detections')).to_have_attribute('data-frame-index',expected)
   if frame['persons']:
    expect(panel.get_by_test_id('pose-overlay')).to_be_visible()
    assert panel.get_by_test_id('person-box').count()>0
  events=sorted(result.get('events',[])+result.get('participant_events',[]),key=lambda e:e['time_sec'])
  if events:
   timeline=panel.get_by_label('Detection timeline',exact=True)
   timeline.get_by_role('button').first.click()
   assert abs(video.evaluate('(v)=>v.currentTime')-events[0]['time_sec'])<.1
  panel.get_by_role('button',name='Replay',exact=True).click()
  page.wait_for_function("()=>{const v=document.querySelector('[data-testid=camera-monitoring] video');return v&&!v.paused&&v.currentTime<2}")
  for output in result['model_results']:
   expect(panel.locator('[data-model="'+output['model_version']+'"]')).to_be_visible()
  passed(name+': original playback, camera identity, replay and synchronized actual overlay frames')
 # Restore Corridor for the requested layout screenshot and test existing incident navigation.
 selector.get_by_role('button',name='Corridor A CAM_CORRIDOR_A',exact=True).click()
 expect(panel.get_by_test_id('monitoring-outcome')).to_be_visible()
 video=panel.locator('video').first;video.evaluate('(v)=>v.pause()');video.evaluate('(v)=>{v.currentTime=1}')
 expect(panel.get_by_test_id('pose-overlay')).to_be_visible()
 for width in [1280,1440,1920]:
  page.set_viewport_size({'width':width,'height':1050})
  layout=panel.evaluate("(p)=>{const l=p.querySelector('.monitoring-player').getBoundingClientRect(),r=p.querySelector('.monitoring-results').getBoundingClientRect();return {left:l.toJSON(),right:r.toJSON(),overflow:p.scrollWidth>p.clientWidth}}")
  assert layout['left']['right']<=layout['right']['left'] and abs(layout['left']['top']-layout['right']['top'])<2,(width,layout)
  assert layout['left']['width']>layout['right']['width'] and not layout['overflow'],(width,layout)
  rects=selector.get_by_role('button').evaluate_all('(nodes)=>nodes.map(n=>n.getBoundingClientRect().toJSON())')
  assert max(r['top'] for r in rects)-min(r['top'] for r in rects)<2
  passed(f'{width}px desktop: compact horizontal selector and larger video left / results right')
 page.set_viewport_size({'width':1440,'height':1050});page.locator('main').evaluate('(m)=>{m.scrollTop=0}')
 panel.locator('.monitoring-results').evaluate('(e)=>{e.scrollTop=0}')
 page.screenshot(path=str(OUT/'live-monitoring-desktop.png'),full_page=True)
 panel.screenshot(path=str(OUT/'live-monitoring-panel.png'))
 incident=panel.locator('button').filter(has_text='Open ').filter(has_text=' incident').first
 expect(incident).to_be_visible();incident.click()
 expect(page.get_by_role('button',name='Close',exact=True)).to_be_visible();page.get_by_role('button',name='Close',exact=True).click()
 passed('Existing detection-result incident action opens and closes the original incident detail modal')
 for width in [1024,768,390]:
  page.set_viewport_size({'width':width,'height':1050})
  assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1'),width
  assert panel.evaluate('(p)=>p.scrollWidth<=p.clientWidth'),width
  geometry=panel.evaluate("p=>{const l=p.querySelector('.monitoring-player').getBoundingClientRect(),r=p.querySelector('.monitoring-results').getBoundingClientRect();return {bottom:l.bottom,top:r.top}}")
  assert geometry['top']>=geometry['bottom'],(width,geometry)
  selector.get_by_role('button',name='School Hall CAM_HALL',exact=True).click()
  expect(panel.locator('video').first).to_have_attribute('data-camera-id','CAM_HALL')
  selector.get_by_role('button',name='Corridor A CAM_CORRIDOR_A',exact=True).click()
  passed(f'{width}px responsive: stacked layout, scrollable camera cards and no overlap/overflow')
 expect(panel.get_by_test_id('monitoring-outcome')).to_be_visible()
 panel.locator('video').first.evaluate('(v)=>{v.pause();v.currentTime=1}')
 expect(panel.get_by_test_id('pose-overlay')).to_be_visible()
 page.locator('main').evaluate('(m)=>{m.scrollTop=0}')
 page.screenshot(path=str(OUT/'live-monitoring-mobile.png'),full_page=True)
 assert not errors,errors
 passed('No browser exceptions')
 page.unroute_all(behavior='wait');browser.close()
assert rows()==before,'Original SQLite records changed during read-only UI verification'
assert all(hashlib.sha256((ROOT/n).read_bytes()).hexdigest()==v for n,v in hashes.items())
passed('Header, sidebar, backend, models/overlay logic and SQLite records unchanged')
(OUT/'results.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
