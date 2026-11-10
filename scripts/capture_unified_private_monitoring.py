from pathlib import Path
import json
from playwright.sync_api import sync_playwright, expect
root=Path(__file__).resolve().parents[1]
out=root/'runtime/unified-private-monitoring-checks'
with sync_playwright() as pw:
    browser=pw.chromium.launch(headless=True,args=['--enable-unsafe-swiftshader'])
    page=browser.new_page(viewport={'width':1600,'height':1800})
    blocked=[]
    def guard(route):
        request=route.request
        if request.method in ['POST','PUT','PATCH','DELETE'] and '/sensors/motion/preview' not in request.url:
            blocked.append(request.url);route.abort()
        else:route.continue_()
    page.route('**/*',guard)
    page.goto('http://127.0.0.1:3000')
    page.locator('aside').get_by_role('button',name='Digital Twin Map',exact=True).click()
    page.locator('[data-zone-id="ZONE_TOILET_BLINDSPOT"] polygon').first.click()
    guide=page.get_by_test_id('guided-private-demo')
    guide.get_by_role('button',name='Start guided demo',exact=True).click()
    page.wait_for_function("JSON.parse(document.querySelector('[data-testid=private-three-renderer]').dataset.tracking||'{}').time>3")
    guide.get_by_role('button',name='Pause guided demo',exact=True).click()
    scene=page.get_by_test_id('private-twin-scene')
    assert page.locator('canvas').count()==1
    expect(scene).to_have_attribute('data-presence-indicated','true')
    expect(page.get_by_test_id('simulated-people-count')).to_contain_text('2')
    page.get_by_role('button',name='Select simulated track T01',exact=True).click()
    expect(page.get_by_test_id('selected-track-information')).to_contain_text('Height')
    page.evaluate("document.querySelectorAll('*').forEach(e=>{if(e.scrollTop)e.scrollTop=0;})")
    page.screenshot(path=str(out/'unified-three-column-desktop.png'),full_page=True)
    assert not blocked,blocked
    (out/'final-visual-smoke.json').write_text(json.dumps({'status':'PASS','canvas_count':1,'shared_presence':True,'tracks':2,'blocked_writes':blocked,'screenshot':'unified-three-column-desktop.png'},indent=2))
    browser.close()
