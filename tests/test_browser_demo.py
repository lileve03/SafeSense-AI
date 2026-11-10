"""Browser E2E checks against the local demo. Adds labeled test incidents; does not reset history."""
from pathlib import Path
import csv
import json
import re
import sys
import time
import traceback
import httpx
import os
STAFF_HEADERS={'X-SafeSense-Token':os.getenv('SAFESENSE_API_TOKEN','local-demo-only')}
BACKEND_BASE=os.getenv('SAFESENSE_BACKEND_URL','http://127.0.0.1:8000')
FRONTEND_BASE=os.getenv('SAFESENSE_DASHBOARD_URL','http://127.0.0.1:3000')
from playwright.sync_api import sync_playwright, expect
sys.stdout.reconfigure(encoding='utf-8')
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'runtime/test-results';OUT.mkdir(parents=True,exist_ok=True)
RESULTS=[]
with (ROOT/'evaluation/outputs/fight_v3/reserved_comparison/predictions.csv').open(encoding='utf-8-sig',newline='') as f:row=next(csv.DictReader(f))
video=ROOT/'datasets'/row['path'].replace('\\','/').split('/datasets/',1)[1]

with sync_playwright() as pw:
    browser=pw.chromium.launch(headless=True)
    page=browser.new_page(viewport={'width':1440,'height':1000})
    page.set_default_timeout(12000)
    errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    def run(name,fn):
        started=time.perf_counter()
        try:
            output=fn();RESULTS.append({'test':name,'status':'PASS','actual':output,'seconds':round(time.perf_counter()-started,3)})
            print('PASS',name,str(output)[:400],flush=True)
        except Exception as e:
            RESULTS.append({'test':name,'status':'FAIL','actual':str(e),'trace':traceback.format_exc(),'seconds':round(time.perf_counter()-started,3)})
            page.screenshot(path=str(OUT/('browser-failure-'+str(len(RESULTS))+'.png')),full_page=True)
            print('FAIL',name,str(e)[:600],flush=True)
        (OUT/'browser-results.json').write_text(json.dumps(RESULTS,indent=2),encoding='utf-8')
    def nav(name):
        page.locator('aside').get_by_role('button',name=name,exact=True).click()
    def developer_tools():
        page.goto(FRONTEND_BASE+'#/developer/testing',wait_until='domcontentloaded')
        expect(page.get_by_role('heading',name='Developer / testing tools',exact=True)).to_be_visible()
    def navigation():
        page.goto(FRONTEND_BASE,wait_until='domcontentloaded')
        expect(page.get_by_text('FastAPI Connected',exact=True)).to_be_visible()
        for name in ['Overview','Live Monitoring','Digital Twin Map','Alerts','Incident Review','Analytics','Devices & Sensors','Reports','Settings']:
            nav(name);expect(page.locator('main')).not_to_be_empty()
        return 'All nine existing navigation items render; backend connected'
    run('Browser startup and all nine navigation pages',navigation)
    last={}
    def fight():
        developer_tools()
        page.get_by_label('Video upload',exact=True).set_input_files(video)
        page.get_by_label('Fight model',exact=True).select_option('v3')
        page.get_by_label('I am authorized to analyze this public-area recording.',exact=True).check()
        with page.expect_response(lambda r:r.url.endswith('/ai/fight/analyze') and r.request.method=='POST',timeout=180000) as response:
            page.get_by_role('button',name='Run real analysis',exact=True).click()
            expect(page.get_by_role('button',name='Analyzing on CPU…',exact=True)).to_be_disabled()
        data=response.value.json();last.update(data)
        assert response.value.ok,data
        expect(page.get_by_role('heading',name='Public-area Video Analysis',exact=True).locator('../..').get_by_text(re.compile('Whole-video score:'))).to_be_visible()
        assert data['event_delivery']['status']=='recorded'
        expect(page.locator('video[src^="blob:"]').first).to_be_visible()
        page.screenshot(path=str(OUT/'video-analysis.png'),full_page=True)
        return {'score':data['score'],'model':data['model_version'],'mode':data['processing_mode'],'incident':data['event_delivery']['incident_id'],'preview':'blob URL'}
    run('Browser real V3 upload, loading state, preview and result',fight)
    def ack():
        page.get_by_role('button',name='Open incident details',exact=True).click()
        page.get_by_role('button',name='Acknowledge Alert',exact=True).click()
        expect(page.get_by_role('button',name='Mark as Verified',exact=True)).to_be_visible()
        incident=next(i for i in httpx.get(BACKEND_BASE+'/incidents',headers=STAFF_HEADERS).json() if i['id']==last['event_delivery']['incident_id'])
        assert incident['status']=='ACKNOWLEDGED'
        page.get_by_role('button',name='Close',exact=True).click()
        return {'backend_status':incident['status'],'history_entries':len(incident['history'])}
    run('Browser acknowledgement persists through FastAPI',ack)
    def map_sync():
        nav('Digital Twin Map')
        zone=page.locator('[data-zone-id="ZONE_CORRIDOR_A"]')
        expect(zone).to_have_attribute('data-risk-level','OBSERVE')
        zone.click()
        expect(page.get_by_text(re.compile('Possible Physical Conflict - Pending Review')).first).to_be_visible()
        page.screenshot(path=str(OUT/'digital-twin.png'),full_page=True)
        return {'zone':'ZONE_CORRIDOR_A','risk':'OBSERVE','acknowledged_incident_still_pending_review':True}
    run('Browser Digital Twin status synchronizes with actual model event',map_sync)
    def sos():
        developer_tools();page.get_by_label('Sensor zone',exact=True).select_option('ZONE_TOILET_BLINDSPOT')
        with page.expect_response(lambda r:r.url.endswith('/event') and r.request.method=='POST') as response:
            page.get_by_role('button',name='Trigger test SOS',exact=True).click()
        data=response.value.json();assert data['incident']['level']=='CRITICAL',data
        expect(page.get_by_role('button',name='Acknowledge Alert',exact=True)).to_be_visible()
        page.get_by_role('button',name='Acknowledge Alert',exact=True).click()
        expect(page.get_by_role('button',name='Mark as Verified',exact=True)).to_be_visible()
        page.get_by_role('button',name='Close',exact=True).click()
        nav('Digital Twin Map');expect(page.locator('[data-zone-id="ZONE_TOILET_BLINDSPOT"]')).to_have_attribute('data-risk-level','CRITICAL')
        zones=httpx.get(BACKEND_BASE+'/zones').json();z=next(z for z in zones if z['id']=='ZONE_TOILET_BLINDSPOT')
        assert z['level']=='CRITICAL'
        return {'mode':data['event']['processing_mode'],'level':z['level'],'acknowledged':True}
    run('Browser SOS, incident acknowledgement and private-zone map update',sos)
    def fall():
        developer_tools();page.get_by_label('Analysis type',exact=True).select_option('fall')
        page.get_by_label('Video upload',exact=True).set_input_files(ROOT/'datasets/open_hidden/test_videos/fall-02-cam0-rgb.mp4')
        page.get_by_label('I am authorized to analyze this public-area recording.',exact=True).check()
        with page.expect_response(lambda r:r.url.endswith('/ai/fall/analyze') and r.request.method=='POST',timeout=240000) as response:
            page.get_by_role('button',name='Run real analysis',exact=True).click()
        data=response.value.json();assert response.value.ok,data
        expect(page.get_by_role('heading',name='Public-area Video Analysis',exact=True).locator('../..').get_by_text(re.compile('Experimental posture heuristic|experimental posture heuristic'))).to_be_visible()
        upload_section=page.get_by_role('heading',name='Public-area Video Analysis',exact=True).locator('../..')
        expect(upload_section.locator('video')).to_have_count(2)
        expect(page.get_by_role('link',name='Open annotated MP4',exact=True)).to_be_visible()
        assert data['annotation_playback']=='h264_browser',data
        annotated=upload_section.locator('video').nth(1)
        expect(annotated).to_be_visible()
        annotated.evaluate('(v)=>v.play()')
        expect(annotated).to_have_js_property('paused',False)
        return {'events':data['events'],'annotation_displayed':True,'actual_h264_playback':True,'latency':data['inference_time_sec']}
    run('Browser actual YOLO fall inference and annotation output',fall)
    def replay():
        select=page.get_by_label('Recorded sensor result',exact=True)
        expect(select.locator('option')).not_to_have_count(1)
        select.select_option('radar:0')
        with page.expect_response(lambda r:r.url.endswith('/sensors/replay') and r.request.method=='POST') as response:
            page.get_by_role('button',name='Replay recorded prediction',exact=True).click()
        data=response.value.json();assert data['event']['processing_mode']=='recorded_sensor_replay',data
        page.get_by_role('button',name='Close',exact=True).click()
        return {'mode':data['event']['processing_mode'],'evidence':data['event']['evidence_reference']}
    run('Browser saved radar replay and explicit provenance',replay)
    def simulated_fusion():
        page.get_by_role('button',name='Simulate radar + acoustic fusion',exact=True).click()
        expect(page.get_by_role('button',name='Acknowledge Alert',exact=True)).to_be_visible()
        incidents=httpx.get(BACKEND_BASE+'/incidents',headers=STAFF_HEADERS).json()
        incident=next(i for i in incidents if i['zone_id']=='ZONE_TOILET_BLINDSPOT' and i['level']=='HIGH' and i['processing_mode']=='simulation')
        assert {'radar','yamnet'}.issubset({e['source'] for e in incident['evidence']})
        page.get_by_role('button',name='Close',exact=True).click()
        return {'mode':incident['processing_mode'],'severity':incident['level'],'independent_simulated_modalities':True}
    run('Browser explicit simulated radar/acoustic fusion',simulated_fusion)
    def filters():
        nav('Alerts');page.get_by_label('Incident source',exact=True).select_option('vision');page.get_by_label('Incident status',exact=True).select_option('acknowledged')
        expect(page.get_by_text(re.compile('Possible Physical Conflict - Pending Review')).first).to_be_visible()
        return 'Source=vision and status=acknowledged filters retain the acknowledged real-model incident'
    run('Browser source and status filtering',filters)
    def analytics():
        nav('Analytics');expect(page.get_by_role('heading',name='Safety Analytics & Operational Metrics',exact=True)).to_be_visible()
        expect(page.get_by_role('heading',name='Saved Research Evaluations',exact=True)).to_have_count(0)
        nav('Reports');page.get_by_role('button',name='Model evaluation',exact=True).click()
        expect(page.get_by_role('heading',name='Saved Research Evaluations',exact=True)).to_be_visible()
        expect(page.get_by_text('V3',exact=True).first).to_be_visible()
        expect(page.get_by_text('0.9167',exact=True)).to_be_visible()
        nav('Analytics')
        return 'Operational Analytics has no research panel; saved V3 comparison remains in Reports / Model evaluation, F1 0.9167'
    run('Browser real evaluation metrics render',analytics)
    def report_download():
        nav('Reports')
        expect(page.get_by_test_id('incident-report')).to_be_visible()
        incident_id=page.get_by_label('Report incident',exact=True).input_value()
        actual=httpx.get(BACKEND_BASE+'/incidents/'+incident_id+'/report',headers=STAFF_HEADERS).json()
        with page.expect_download() as download:
            page.get_by_role('button',name='Download CSV',exact=True).click()
        path=Path(download.value.path())
        text=path.read_text(encoding='utf-8-sig')
        with path.open(encoding='utf-8-sig',newline='') as stream:records=list(csv.DictReader(stream))
        assert len(records)==1 and records[0]['incident_id']==incident_id
        assert records[0]['processing_mode']==actual['processing_mode']
        assert 'evidence_reference' in records[0]
        return {'download':download.value.suggested_filename,'bytes':len(text),'provenance_included':True,'selected_incident':incident_id}
    run('Browser CSV export includes processing mode and evidence',report_download)
    def mobile():
        page.set_viewport_size({'width':390,'height':844});developer_tools()
        expect(page.get_by_role('heading',name='Public-area Video Analysis',exact=True)).to_be_visible()
        page.screenshot(path=str(OUT/'mobile.png'),full_page=True)
        measure=page.evaluate('({window:innerWidth,body:document.body.scrollWidth,main:document.querySelector("main").clientWidth,scroll:document.querySelector("main").scrollWidth})')
        assert measure['body']<=measure['window']+1,measure
        return measure
    run('Browser narrow-screen navigation and upload layout',mobile)
    def no_crashes():
        assert not errors,errors
        return 'No JavaScript page errors across navigation and end-to-end workflows'
    run('Browser runtime error audit',no_crashes)
    browser.close()
print(f"RESULT {sum(r['status']=='PASS' for r in RESULTS)}/{len(RESULTS)} browser checks passed",flush=True)
sys.exit(1 if any(r['status']=='FAIL' for r in RESULTS) else 0)
