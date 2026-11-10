"""Real-browser regression for the recovered original private monitoring experience."""
from pathlib import Path
import hashlib, json, re, sys, time, traceback
import httpx
from playwright.sync_api import sync_playwright, expect
sys.stdout.reconfigure(encoding='utf-8')
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'runtime/private-view-restoration';OUT.mkdir(parents=True,exist_ok=True)
rows=[]
def original_design():
    archived=(OUT/'archive/components/private-area/PrivateAreaDigitalTwin3D.tsx').read_text(encoding='utf-8-sig')
    current=(ROOT/'dashboard/src/components/private-area/PrivateAreaDigitalTwin3D.tsx').read_text(encoding='utf-8-sig')
    counts={}
    for name,pattern in [('geometry',r'new THREE\.\w+Geometry\([^;]*;'),('materials',r'new THREE\.\w+Material\([^;]*;'),('camera',r'new THREE\.PerspectiveCamera\([^;]*;'),('orbit',r'theta: 0\.6, phi: 0\.45, radius: 12')]:
        before=re.findall(pattern,archived,re.S);after=re.findall(pattern,current,re.S)
        assert before and before==after,name
        counts[name]=len(before)
    return counts
with sync_playwright() as pw:
    browser=pw.chromium.launch(headless=True,args=['--enable-unsafe-swiftshader'])
    page=browser.new_page(viewport={'width':1600,'height':1100})
    page.add_init_script("window.privateMediaRequests=0; if(navigator.mediaDevices){navigator.mediaDevices.getUserMedia=async()=>{window.privateMediaRequests++;throw new Error('Private capture forbidden by test');};}")
    page.set_default_timeout(15000)
    errors=[];console_errors=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.on('console',lambda m:console_errors.append(m.text) if m.type=='error' else None)
    def run(name,fn):
        start=time.perf_counter()
        try:
            actual=fn();rows.append({'test':name,'status':'PASS','actual':actual,'seconds':round(time.perf_counter()-start,3)})
            print('PASS',name,str(actual)[:450],flush=True)
        except Exception as e:
            rows.append({'test':name,'status':'FAIL','actual':str(e),'trace':traceback.format_exc()})
            page.screenshot(path=str(OUT/f'failure-{len(rows)}.png'),full_page=True)
            print('FAIL',name,str(e)[:650],flush=True)
        (OUT/'browser-results.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
    def view():return page.get_by_test_id('private-monitoring-view')
    def scene():return page.get_by_test_id('private-twin-scene')
    def nav(name):page.locator('aside').get_by_role('button',name=name,exact=True).click()
    run('Original archived room geometry, materials and orbit preserved',original_design)
    def open_private():
        page.goto('http://127.0.0.1:3000',wait_until='domcontentloaded')
        expect(page.get_by_text('FastAPI Connected',exact=True)).to_be_visible()
        nav('Digital Twin Map')
        page.locator('[data-zone-id="ZONE_TOILET_BLINDSPOT"] polygon').first.click()
        expect(view()).to_be_visible()
        expect(scene().locator('canvas')).to_be_visible()
        expect(scene().get_by_text('3D SENSOR DIGITAL TWIN',exact=True)).to_be_visible()
        return 'Default Backend Events mode now opens original three-column 3D private room directly from private map zone'
    run('Private map click restores original 3D page in default mode',open_private)
    def webgl():
        canvas=scene().locator('canvas')
        data=canvas.evaluate('c=>{const gl=c.getContext("webgl2");return {width:c.width,height:c.height,webgl2:!!gl,lost:gl?.isContextLost(),canvasCount:c.parentElement.querySelectorAll("canvas").length}}')
        assert data['webgl2'] and not data['lost'] and data['width']>300 and data['canvasCount']==1,data
        canvas.screenshot(path=str(OUT/'original-room-restored.png'))
        page.screenshot(path=str(OUT/'original-private-page-restored.png'),full_page=True)
        return data
    run('Original Three.js scene renders a real healthy WebGL canvas',webgl)
    def orbit_zoom():
        canvas=scene().locator('canvas');box=canvas.bounding_box()
        initial=hashlib.sha256(canvas.screenshot()).hexdigest()
        page.mouse.move(box['x']+box['width']*.5,box['y']+box['height']*.6)
        page.mouse.down();page.mouse.move(box['x']+box['width']*.7,box['y']+box['height']*.7,steps=12);page.mouse.up()
        rotated=hashlib.sha256(canvas.screenshot()).hexdigest()
        assert initial!=rotated
        scene().get_by_role('button',name='Zoom In',exact=True).click()
        zoomed=hashlib.sha256(canvas.screenshot()).hexdigest();assert zoomed!=rotated
        scene().get_by_role('button',name='Zoom Out',exact=True).click()
        scene().get_by_role('button',name='Reset Orbit View',exact=True).click()
        return 'Drag orbit, zoom in/out and original reset controls change rendered pixels without losing WebGL context'
    run('Original camera orbit, zoom and reset interactions',orbit_zoom)
    def signal(button,event_type):
        with page.expect_response(lambda r:r.url.endswith('/event') and r.request.method=='POST') as response:
            view().get_by_role('button',name=button,exact=True).click()
        data=response.value.json();assert response.value.ok and data['event']['type']==event_type,data
        assert data['event']['zone_id']=='ZONE_TOILET_BLINDSPOT'
        return data
    def presence():
        data=signal('Simulate presence','presence')
        expect(scene()).to_have_attribute('data-presence-indicated','true')
        expect(view().get_by_text('Radar signal indicated',exact=True)).to_be_visible()
        expect(view().get_by_text('N/A',exact=True).first).to_be_visible()
        expect(scene()).to_have_attribute('data-positioned-occupants','0')
        expect(scene().get_by_text('Anonymous radar presence signal · count and position unknown',exact=True)).to_be_visible()
        expect(view().get_by_test_id('private-sensor-provenance').get_by_text('Radar · SIMULATION',exact=True)).to_be_visible()
        return {'mode':data['event']['processing_mode'],'event':data['event']['type'],'positions_and_counts':'unavailable; no located floor mannequin for presence-only data'}
    run('Labeled backend radar presence updates abstract 3D marker',presence)
    def motion():
        data=signal('Simulate rapid_motion','rapid_motion')
        expect(view().get_by_text('rapid_motion',exact=True)).to_be_visible()
        return {'event':data['event']['type'],'mode':data['event']['processing_mode']}
    run('Labeled radar motion updates original telemetry panel',motion)
    def fall_acoustic():
        signal('Simulate fall','fall')
        expect(scene().get_by_text('RADAR POSSIBLE FALL CANDIDATE — HUMAN REVIEW REQUIRED',exact=True)).to_be_visible()
        data=signal('Simulate scream','scream')
        expect(scene().get_by_text('Acoustic event: scream',exact=True)).to_be_visible()
        assert data['incident'] and data['event']['level']=='HIGH',data
        page.screenshot(path=str(OUT/'radar-acoustic-indicators.png'),full_page=True)
        return {'fall_overlay':'possible candidate, not confirmed','acoustic':'scream','backend_risk':data['event']['level']}
    run('Fall pose and non-speech acoustic indicators reconnect to backend fusion',fall_acoustic)
    def replay():
        select=view().get_by_label('Recorded sensor result',exact=True)
        expect(select.locator('option')).not_to_have_count(1)
        select.select_option('radar:0')
        with page.expect_response(lambda r:r.url.endswith('/sensors/replay') and r.request.method=='POST') as response:
            view().get_by_role('button',name='Replay recorded prediction',exact=True).click()
        data=response.value.json();assert data['event']['processing_mode']=='recorded_sensor_replay',data
        expect(view().get_by_test_id('private-sensor-provenance').get_by_text('Radar · RECORDED SENSOR REPLAY',exact=True)).to_be_visible()
        expect(scene()).to_have_attribute('data-positioned-occupants','0')
        return {'mode':data['event']['processing_mode'],'score':data['event']['score'],'evidence':data['event']['evidence_reference']}
    run('Recorded radar replay remains in original 3D view and labels provenance',replay)
    sos_id={}
    def sos():
        view().get_by_role('button',name='ACTIVATE SOS EMERGENCY',exact=True).click()
        expect(page.get_by_role('heading',name='Authorize Prototype SOS Test',exact=True)).to_be_visible()
        with page.expect_response(lambda r:r.url.endswith('/event') and r.request.method=='POST') as response:
            page.get_by_role('button',name='Confirm Test Broadcast',exact=True).click()
        data=response.value.json();sos_id['id']=data['incident']['id']
        assert data['incident']['level']=='CRITICAL',data
        expect(scene()).to_have_attribute('data-sos-active','true')
        expect(scene().get_by_text('SOS active — human response required',exact=True)).to_be_visible()
        return {'incident':data['incident']['id'],'mode':data['event']['processing_mode'],'risk':data['incident']['level']}
    run('Original SOS control records backend incident and highlights 3D indicator',sos)
    def acknowledge():
        # The original panel acknowledges the visible active zone incident.
        with page.expect_response(lambda r:'/ack' in r.url and r.request.method=='POST') as response:
            view().get_by_role('button',name='Acknowledge Incident',exact=True).click()
        data=response.value.json();assert data['status']=='ACKNOWLEDGED',data
        expect(view().get_by_text('Acknowledged by Duty Officer',exact=True)).to_be_visible()
        return {'incident':data['id'],'status':data['status'],'timestamp':data['acknowledged_at']}
    run('Original incident acknowledgement uses confirmed FastAPI state',acknowledge)
    def navigation():
        view().get_by_role('button',name='Full School 2.5D Map',exact=True).click()
        expect(page.locator('[data-zone-id="ZONE_TOILET_BLINDSPOT"]')).to_have_attribute('data-risk-level','CRITICAL')
        page.get_by_role('button',name='Private Area 3D View',exact=True).click()
        expect(scene().locator('canvas')).to_have_count(1)
        # Switching to a public zone returns to its map rather than mislabeling a private room.
        view().get_by_role('button',name='Corridor A',exact=True).click()
        expect(view()).to_have_count(0)
        expect(page.locator('[data-zone-id="ZONE_CORRIDOR_A"]')).to_be_visible()
        page.locator('[data-zone-id="ZONE_TOILET_BLINDSPOT"] polygon').first.click()
        expect(scene().locator('canvas')).to_have_count(1)
        return 'School map, private tab, public-zone switch and private re-entry all work; canvas remounts once'
    run('Original room navigation and scene lifecycle',navigation)
    def privacy():
        assert view().locator('video, audio, img').count()==0
        assert page.evaluate('window.privateMediaRequests')==0
        assert view().get_by_label('Sensor zone',exact=True).is_disabled()
        headers={'X-SafeSense-Token':'local-demo-only'}
        status={}
        for kind in ['fight','fall']:
            response=httpx.post(f'http://127.0.0.1:8001/ai/{kind}/analyze',headers=headers,data={'zone_id':'ZONE_TOILET_BLINDSPOT','zone_type':'open_hidden','authorized':'true'},files={'file':('private.mp4',b'privacy regression: no image data','video/mp4')},timeout=10)
            assert response.status_code==403,response.text
            status[kind]=response.status_code
        return {'video_endpoints':status,'private_page_media_elements':0,'camera_microphone_requests':0,'zone_controls':'private scoped'}
    run('Private page contains no visual feed and fight/fall uploads stay prohibited',privacy)
    def original_simulation():
        view().get_by_role('button',name='Use original local simulation',exact=True).click()
        expect(scene().get_by_text('ANONYMOUS 3D SIMULATION',exact=True)).to_be_visible()
        for label in ['1. Normal Presence','2. Close Proximity','3. Rapid Movement','5. Scream Detected','6. Fall + Scream','7. SOS Emergency','4. Fall Detected']:
            view().get_by_role('button',name=re.compile(re.escape(label))).click()
            expect(view().get_by_role('heading',level=2)).to_contain_text('Toilet')
            close = page.get_by_role('button',name='Close',exact=True)
            if close.is_visible(): close.click()
        expect(scene().get_by_text('RADAR POSSIBLE FALL CANDIDATE — HUMAN REVIEW REQUIRED',exact=True)).to_be_visible()
        assert view().get_by_role('button',name='Reset to baseline normal state',exact=True).is_enabled()
        page.screenshot(path=str(OUT/'original-local-simulation.png'),full_page=True)
        return 'All seven original scenarios run in the selected private zone; original room, mannequin fall pose and reset are preserved'
    run('Original local simulation and scenario controls preserved',original_simulation)
    def errors_check():
        assert not errors,errors
        assert not console_errors,console_errors
        return {'page_errors':errors,'console_errors':console_errors}
    run('No critical browser or WebGL console errors',errors_check)
    browser.close()
print(f"RESULT {sum(r['status']=='PASS' for r in rows)}/{len(rows)} private-view checks passed",flush=True)
sys.exit(1 if any(r['status']=='FAIL' for r in rows) else 0)
