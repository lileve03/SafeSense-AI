from pathlib import Path
import json,time
from urllib.request import Request,urlopen
from playwright.sync_api import sync_playwright
out=Path('runtime/camera-playback-task2')
def get(path):
 with urlopen(Request('http://127.0.0.1:8000'+path,headers={'X-SafeSense-Token':'local-demo-only'}),timeout=5) as r:return json.load(r)
for n in range(60):
 try:cameras=get('/monitoring/cameras');break
 except OSError:time.sleep(.5)
assert len(cameras)==5 and all(c['available'] for c in cameras)
before=json.loads((out/'state-before-activation.json').read_text())['incidents']
assert get('/state')['incidents']==before
with sync_playwright() as pw:
 browser=pw.chromium.launch(headless=True);page=browser.new_page(viewport={'width':1500,'height':1050})
 # Production playback smoke only; actual AI was tested on isolated services.
 page.route('**/monitoring/jobs',lambda r:r.fulfill(status=503,json={'detail':'Analysis disabled for read-only playback verification'}))
 page.goto('http://127.0.0.1:3000');page.locator('aside').get_by_role('button',name='Live Monitoring',exact=True).click()
 panel=page.get_by_test_id('camera-monitoring');actual=[]
 for c in cameras:
  panel.get_by_role('button',name=c['camera_name']+' '+c['camera_id']+' '+c['source_type'],exact=True).click()
  page.wait_for_function("id=>{let v=document.querySelector('[data-testid=camera-monitoring] video');return v?.dataset.cameraId===id && v.readyState>=2 && !v.paused && v.currentTime>0.15}",arg=c['camera_id'],timeout=15000)
  result=panel.locator('video').evaluate('(v)=>({src:v.currentSrc,time:v.currentTime,width:v.videoWidth,height:v.videoHeight,muted:v.muted,controls:v.controls})')
  assert '/monitoring/sources/'+c['scenario']['id']+'?' in result['src']
  actual.append({'camera_id':c['camera_id'],'file':c['scenario']['path'],'playback':result})
 page.screenshot(path=str(out/'active-camera.png'),full_page=True);browser.close()
assert get('/state')['incidents']==before
result={'status':'PASS','url':'http://127.0.0.1:3000','feeds':actual,'incidents_preserved':len(before),'scope':'Actual active-app playback; job submissions blocked in this browser only. Real inference separately passed on isolated services.'}
(out/'activation.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result,indent=2))
