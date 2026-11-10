from pathlib import Path
import json
from playwright.sync_api import sync_playwright, expect
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'runtime/settings-header-layout';OUT.mkdir(parents=True,exist_ok=True)
results=[]
def passed(name):
 results.append({'test':name,'result':'PASS'});print('PASS:',name)
with sync_playwright() as pw:
 browser=pw.chromium.launch(headless=True)
 page=browser.new_page(viewport={'width':1440,'height':1200})
 errors=[];writes=[]
 page.on('pageerror',lambda e:errors.append(str(e)))
 page.on('request',lambda r:writes.append(r.url) if r.method not in ['GET','OPTIONS'] else None)
 page.goto('http://127.0.0.1:3000',wait_until='domcontentloaded')
 page.locator('aside').get_by_role('button',name='Settings',exact=True).click()
 expect(page.get_by_role('heading',name='AI Settings',exact=True)).to_be_visible()
 expect(page.get_by_text('Backend AI & Fusion',exact=False)).to_have_count(0)
 expect(page.get_by_text('Fusion window',exact=True)).to_have_count(0)
 gap=page.get_by_role('heading',name='Simulation Risk Bands (0 - 100)',exact=True).evaluate('(e)=>e.parentElement.parentElement.parentElement.getBoundingClientRect().top - document.querySelector("main h2").parentElement.parentElement.getBoundingClientRect().bottom')
 assert 20<=gap<=28,gap
 passed('Deleted backend card leaves only the normal 24px section gap')
 page.get_by_role('button',name='Mode: Backend Events',exact=True).click()
 for width in [1280,1366,1440,1920]:
  page.set_viewport_size({'width':width,'height':1200})
  boxes=page.locator('header').evaluate("""(h)=> {
    const nodes=[h.querySelector('h1').parentElement.parentElement,h.querySelector('.dashboard-header-slogan'),h.querySelector('.dashboard-header-status'),h.querySelector('.dashboard-header-actions')];
    return {header:h.getBoundingClientRect().toJSON(),groups:nodes.map(n=>n.getBoundingClientRect().toJSON()),overflow:h.scrollWidth>h.clientWidth};
  }""")
  assert not boxes['overflow'],(width,boxes)
  groups=boxes['groups'];centers=[b['y']+b['height']/2 for b in groups]
  assert max(centers)-min(centers)<2,(width,boxes)
  assert all(groups[i]['right']<=groups[i+1]['left'] for i in range(3)),(width,boxes)
  assert boxes['header']['height']<=74,(width,boxes)
  for text in ['Safer Schools. Smarter Decisions.','Demo Engine Online','Demo Operator']:
   expect(page.locator('header').get_by_text(text,exact=True)).to_be_visible()
  passed(f'{width}px desktop: all header groups share one centered row without overlap or overflow')
 page.set_viewport_size({'width':1440,'height':1200})
 page.locator('header').get_by_role('button',name='Notifications',exact=True).click()
 expect(page.get_by_text('Alert Notifications',exact=True)).to_be_visible()
 page.locator('header').get_by_role('button',name='Notifications',exact=True).click()
 page.get_by_role('button',name='Run Demo Scenarios',exact=True).click()
 expect(page.get_by_role('heading',name='Interactive Scenario Simulator')).to_be_visible()
 page.get_by_role('heading',name='Interactive Scenario Simulator').locator('..').locator('..').locator('..').get_by_role('button').click()
 reset=page.get_by_role('button',name='Reset demonstration state',exact=True)
 expect(reset).to_be_enabled();reset.click()
 page.get_by_role('button',name='Save Settings',exact=True).click()
 expect(page.get_by_role('status').filter(has_text='Simulation preferences saved')).to_be_visible()
 page.get_by_role('button',name='Restore Defaults',exact=True).click()
 passed('Demo, Reset, Notifications, Save and Restore Defaults remain clickable and functional')
 page.get_by_role('button',name='Mode: Simulated Demo',exact=True).click()
 expect(page.get_by_role('button',name='Save Settings',exact=True)).to_be_disabled()
 page.get_by_role('button',name='Mode: Backend Events',exact=True).click()
 passed('Mode toggle preserves existing backend/simulation behavior')
 # Remount to capture the clean Settings page without temporary save feedback.
 page.locator('aside').get_by_role('button',name='Overview',exact=True).click()
 page.locator('aside').get_by_role('button',name='Settings',exact=True).click()
 page.screenshot(path=str(OUT/'settings-desktop.png'),full_page=True)
 for width in [1024,768,390]:
  page.set_viewport_size({'width':width,'height':1100})
  assert page.locator('header').evaluate('(h)=>h.scrollWidth<=h.clientWidth'),width
  rects=page.locator('header button').evaluate_all('(nodes)=>nodes.map(n=>n.getBoundingClientRect().toJSON())')
  assert all(a['right']<=b['left'] or b['right']<=a['left'] or a['bottom']<=b['top'] or b['bottom']<=a['top'] for i,a in enumerate(rects) for b in rects[i+1:]),width
  page.get_by_role('button',name='Notifications',exact=True).click()
  expect(page.get_by_text('Alert Notifications',exact=True)).to_be_visible()
  page.get_by_role('button',name='Notifications',exact=True).click()
  passed(f'{width}px responsive header: wraps without overlapping controls')
 page.screenshot(path=str(OUT/'settings-mobile.png'),full_page=True)
 assert not errors,errors
 assert not writes,writes
 passed('No browser exceptions or backend mutation requests')
 browser.close()
(OUT/'results.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
