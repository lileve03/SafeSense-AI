"""Read-only diagnosis: actual stored inference reused verbatim; no AI jobs/events submitted."""
from pathlib import Path
import json,time
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'runtime/overlay-diagnosis'
with sync_playwright() as pw:
    browser=pw.chromium.launch(headless=True);page=browser.new_page(viewport={'width':1500,'height':1050})
    def jobs(route):
        body=route.request.post_data_json
        camera=body.get('camera_id');saved=OUT/(str(camera)+'.json')
        if saved.is_file():route.fulfill(status=202,json=json.loads(saved.read_text(encoding='utf-8')))
        else:route.fulfill(status=409,json={'detail':'Read-only diagnosis refuses uncaptured inference'})
    page.route('**/monitoring/jobs',jobs)
    page.route('**/monitoring/jobs/release',lambda r:r.fulfill(status=200,json={'status':'released'}))
    page.goto('http://127.0.0.1:3000');page.locator('aside').get_by_role('button',name='Live Monitoring',exact=True).click()
    panel=page.get_by_test_id('camera-monitoring');rows=[]
    for name,camera in [('School Entrance','CAM_ENTRANCE'),('School Hall','CAM_HALL')]:
        panel.get_by_role('button',name=name+' '+camera+' RECORDED REAL VIDEO',exact=True).click()
        panel.get_by_test_id('fight-video-overlay').wait_for(state='visible',timeout=20000)
        page.wait_for_function("()=>{const v=document.querySelector('[data-testid=camera-monitoring] video');return v.readyState>=2&&!v.paused&&v.currentTime>.5}")
        video=panel.locator('video').first;video.evaluate('v=>v.pause()')
        page.wait_for_timeout(100)
        row={'camera':camera,'time':video.evaluate('v=>v.currentTime'),'boxes':panel.get_by_test_id('person-box').count(),'bones':panel.get_by_test_id('pose-bone').count(),'frame':panel.get_by_test_id('video-detection-overlay').get_attribute('data-frame-index'),'video_dimensions':video.evaluate('v=>[v.videoWidth,v.videoHeight]'),'svg_dimensions':panel.get_by_test_id('pose-overlay').evaluate('s=>({viewBox:s.getAttribute("viewBox"),width:s.clientWidth,height:s.clientHeight})')}
        rows.append(row);page.screenshot(path=str(OUT/(camera+'-before.png')),full_page=True)
    (OUT/'running-browser-before.json').write_text(json.dumps(rows,indent=2),encoding='utf-8');print(json.dumps(rows));browser.close()
