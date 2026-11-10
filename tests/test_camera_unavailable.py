from pathlib import Path
import os,json,tempfile,sys
sys.path.insert(0,str(Path.cwd()))
from playwright.sync_api import sync_playwright,expect
out=Path('runtime/camera-playback-task2');out.mkdir(parents=True,exist_ok=True)
with tempfile.TemporaryDirectory() as tmp:
 os.environ['SAFESENSE_DB_PATH']=str(Path(tmp)/'state.sqlite3')
 from backend.registry import cameras
 rows=cameras();missing={**rows[0],'camera_id':'CAM_MISSING','camera_name':'Missing recording','available':False,'scenario':None,'scenario_id':None,'stream_configured':False}
 with sync_playwright() as pw:
  browser=pw.chromium.launch(headless=True);page=browser.new_page()
  page.route('**/monitoring/cameras',lambda r:r.fulfill(json=[missing]))
  page.goto('http://127.0.0.1:3000');page.locator('aside').get_by_role('button',name='Live Monitoring',exact=True).click()
  panel=page.get_by_test_id('camera-monitoring');panel.get_by_role('button',name='Missing recording CAM_MISSING No recording configured.',exact=True).click()
  expect(panel.get_by_text('No recording configured.',exact=True)).to_have_count(2)
  expect(panel.locator('video')).to_have_count(0)
  browser.close()
 print('PASS unavailable camera opens explicit No recording configured.; no previous video retained')
 (out/'unavailable.json').write_text(json.dumps({'status':'PASS','scope':'Browser missing-registry metadata fixture; no media or AI results fabricated'}))
