from pathlib import Path
import sys,json,os,tempfile
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from playwright.sync_api import sync_playwright,expect
out=ROOT/'runtime/settings-check';out.mkdir(parents=True,exist_ok=True)
results=[]
def passed(name):results.append({'test':name,'result':'PASS'});print('PASS:',name)
with tempfile.TemporaryDirectory() as tmp:
 os.environ['SAFESENSE_DB_PATH']=str(Path(tmp)/'settings.sqlite3')
 from backend import main
 import threading,time,uvicorn
 from urllib.request import Request,urlopen
 from urllib.error import HTTPError
 server=uvicorn.Server(uvicorn.Config(main.app,host='127.0.0.1',port=8019,log_level='error'))
 threading.Thread(target=server.run,daemon=True).start()
 for _ in range(100):
  if server.started:break
  time.sleep(.05)
 class Client:
  def request(self,path,headers=None,method='GET'):
   try:r=urlopen(Request('http://127.0.0.1:8019'+path,headers=headers or {},method=method))
   except HTTPError as e:r=e
   class Response:
    status_code=r.code
    def json(self):return json.loads(r.read())
   return Response()
  def get(self,path,headers=None):return self.request(path,headers)
  def post(self,path,headers=None,json=None):return self.request(path,headers,'POST')
 client=Client()
 assert client.get('/settings').status_code==401
 headers={'X-SafeSense-Token':main.TOKEN}
 response=client.get('/settings',headers=headers);assert response.status_code==200
 config=response.json();assert config['fusion_window_seconds']==main.FUSION_WINDOW_SECONDS
 assert config['minimum_event_confidence']==main.MIN_CONF
 assert client.post('/settings',headers=headers,json={}).status_code==405
 assert 'vision' not in main.ZONES['ZONE_TOILET_BLINDSPOT']['allowed_sources']
 passed('Authenticated read-only runtime configuration and fixed private-zone policy')
 with sync_playwright() as pw:
  browser=pw.chromium.launch(headless=True)
  page=browser.new_page(viewport={'width':1440,'height':1000});errors=[];writes=[]
  page.on('pageerror',lambda e:errors.append(str(e)))
  page.on('request',lambda r:writes.append(r.url) if r.method not in ('GET','OPTIONS') else None)
  page.route('**/settings',lambda r:r.fulfill(status=200,content_type='application/json',body=json.dumps(client.get('/settings',headers=headers).json())))
  page.goto('http://127.0.0.1:3017',wait_until='domcontentloaded')
  def settings():page.locator('aside').get_by_role('button',name='Settings',exact=True).click();expect(page.get_by_role('heading',name='AI Settings',exact=True)).to_be_visible()
  settings()
  expect(page.get_by_text('Backend Connected \u00b7 Physical Hardware Connected: Not verified',exact=True)).to_be_visible()
  expect(page.get_by_role('button',name='Save Settings')).to_be_disabled()
  for slider in page.get_by_role('slider').all():expect(slider).to_be_disabled()
  assert not any(c in page.locator('main').inner_text() for c in ['\u00c3','\u00c2','\ufffd'])
  passed('Backend mode locks simulation controls; connection labels and UTF-8 render correctly')
  page.get_by_role('button',name='Mode: Backend Events',exact=True).click()
  slider=page.get_by_role('slider',name='Simulation Low risk ceiling',exact=True)
  slider.fill('35');page.get_by_role('checkbox').uncheck()
  page.get_by_role('button',name='Save Settings',exact=True).click()
  expect(page.get_by_role('status').filter(has_text='Simulation preferences saved')).to_be_visible()
  stored=page.evaluate("JSON.parse(localStorage.getItem('safesense_settings'))")
  assert stored['thresholds']['low']==35 and stored['audioAlerts']==False and stored['privacyStrictRadarOnly']==True
  page.reload();settings();page.get_by_role('button',name='Mode: Backend Events',exact=True).click()
  expect(page.get_by_role('slider',name='Simulation Low risk ceiling',exact=True)).to_have_value('35')
  expect(page.get_by_role('checkbox')).not_to_be_checked()
  passed('Save persists simulation bands and audio across reload')
  page.get_by_role('button',name='Restore Defaults',exact=True).click()
  stored=page.evaluate("JSON.parse(localStorage.getItem('safesense_settings'))")
  assert stored['thresholds']=={'low':24,'observe':49,'warning':74,'high':94,'critical':100} and stored['audioAlerts']
  page.reload();settings();expect(page.get_by_role('slider').first).to_have_value('24');expect(page.get_by_role('checkbox')).to_be_checked()
  passed('Restore Defaults immediately saves defaults and survives reload')
  page.get_by_role('button',name='Mode: Backend Events',exact=True).click()
  page.get_by_role('slider',name='Simulation Observe ceiling',exact=True).fill('60')
  page.get_by_role('button',name='Save Settings',exact=True).click()
  # Exercise the same context action used by the scenario runner, then inspect rendered context state.
  context_js = """() => {
    const node = document.getElementById('root');
    const container = node[Object.keys(node).find(k => k.startsWith('__reactContainer'))];
    const find = fiber => {
      if (!fiber) return null;
      if (fiber.memoizedProps?.value?.runScenario) return fiber.memoizedProps.value;
      return find(fiber.child) || find(fiber.sibling);
    };
    return find(container.stateNode.current);
  }"""
  page.evaluate('(' + context_js + ')().runScenario("SCENARIO_4_RAPID_APPROACH")')
  page.wait_for_timeout(100)
  assert page.evaluate('(' + context_js + ')().zones.find(z => z.id === "ZONE_CORRIDOR_A").level') == 'OBSERVE'
  page.evaluate('(' + context_js + ')().runScenario("SCENARIO_8_SOS_EMERGENCY")')
  page.wait_for_timeout(100)
  assert page.evaluate('(' + context_js + ')().alerts[0].level') == 'CRITICAL'
  passed('Saved simulation bands affect new scenario classification; SOS remains Critical')
  # Close the SOS incident modal before testing the Settings save button.
  page.keyboard.press('Escape')
  page.evaluate('(' + context_js + ')().setSelectedAlertId(null)')
  page.evaluate("() => { Storage.prototype.setItem = () => { throw new DOMException('Blocked', 'SecurityError'); }; }")
  page.get_by_role('button',name='Save Settings',exact=True).click()
  expect(page.get_by_role('status').filter(has_text='Could not save preferences')).to_be_visible()
  passed('Storage failure displays error instead of claiming success')
  page.reload();settings()
  page.screenshot(path=str(out/'settings-desktop.png'),full_page=True)
  assert not writes,writes
  assert not errors,errors
  passed('Settings makes no backend writes and raises no browser exceptions')
  page.unroute('**/settings');page.route('**/settings',lambda r:r.fulfill(status=503,content_type='application/json',body='{}'))
  page.reload();settings();expect(page.get_by_text('Backend settings unavailable.',exact=False)).to_be_visible()
  passed('Unavailable backend shows no fabricated configuration values')
  page.set_viewport_size({'width':390,'height':844});page.screenshot(path=str(out/'settings-mobile.png'),full_page=True)
  assert page.locator('main').evaluate('(e)=>e.scrollWidth <= e.clientWidth')
  passed('Mobile Settings has no horizontal overflow')
  browser.close()
(out/'results.json').write_text(json.dumps(results,indent=2),encoding='utf-8')

