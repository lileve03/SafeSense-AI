"""Explicit opt-in real browser SOS test; sends ONE authorized Telegram test message."""
import argparse,json,os,sys,time
from pathlib import Path
import httpx
from playwright.sync_api import sync_playwright,expect
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts.start_services import load_local_environment

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--send-live',action='store_true');args=parser.parse_args()
    if not args.send_live:raise SystemExit('No message sent. --send-live explicitly authorizes one new TEST SOS.')
    load_local_environment();out=ROOT/'runtime/sos-scene-live';out.mkdir(parents=True,exist_ok=True)
    base=os.getenv('SAFESENSE_BACKEND_URL','http://127.0.0.1:8000')
    client=httpx.Client(base_url=base,headers={'X-SafeSense-Token':os.getenv('SAFESENSE_API_TOKEN','local-demo-only')},timeout=15)
    config=client.get('/notifications/status').json()
    assert config['mode']=='test' and config['transport_kind']=='real_https' and config['test_configured'] and not config['production_dispatch']
    rows=[];evidence={'recipient_masked':config['test_recipient_masked'],'mode':config['mode'],'receipt_verified':False,'tests':rows}
    def record(name,actual):
        rows.append({'test':name,'status':'PASS','actual':actual});print('PASS',name,flush=True)
        (out/'results.json').write_text(json.dumps(evidence,indent=2),encoding='utf-8')
    try:
        with sync_playwright() as pw:
            browser=pw.chromium.launch(headless=True,args=['--enable-unsafe-swiftshader'])
            page=browser.new_page(viewport={'width':1600,'height':1600});page.set_default_timeout(25000)
            errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
            page.goto('http://127.0.0.1:3000');page.locator('aside').get_by_role('button',name='Digital Twin Map',exact=True).click()
            page.locator('[data-zone-id="ZONE_TOILET_BLINDSPOT"] polygon').first.click()
            guide=page.get_by_test_id('guided-private-demo');renderer=page.get_by_test_id('private-three-renderer')
            def stats():return json.loads(renderer.get_attribute('data-tracking'))
            guide.get_by_role('combobox',name='Guided scenario').select_option('sos')
            page.wait_for_function('JSON.parse(document.querySelector("[data-testid=private-three-renderer]").dataset.tracking).active===1')
            start=stats()['sourcePositions'][0];assert stats()['sosIllustrative']
            expect(page.get_by_test_id('sos-illustrative-label')).to_be_visible()
            panel=page.get_by_test_id('private-status-panel')
            expect(panel.locator('dl > div').filter(has_text='People Count').locator('dd')).to_have_text('1')
            page.screenshot(path=str(out/'sos-start.png'),full_page=True)
            record('SOS selected from an empty prior scene has one labeled synthetic humanoid',start)
            guide.get_by_role('button',name='Start guided demo',exact=True).click()
            page.wait_for_function('JSON.parse(document.querySelector("[data-testid=private-three-renderer]").dataset.tracking).time>=2')
            guide.get_by_role('button',name='Pause guided demo',exact=True).click()
            approach=stats();assert approach['sourcePositions'][0]!=start
            page.screenshot(path=str(out/'sos-approach.png'),full_page=True)
            record('Same humanoid visibly approaches the wall SOS device',approach['sourcePositions'])
            details=page.get_by_test_id('private-track-details');details.locator(':scope > summary').click()
            slider=page.get_by_role('slider',name='Tracking playback time',exact=True);slider.fill('5');details.locator(':scope > summary').click()
            page.wait_for_function('(()=>{const s=JSON.parse(document.querySelector("[data-testid=private-three-renderer]").dataset.tracking);return s.visualRisk==="CRITICAL"&&s.sosGesture>.9&&s.active===1&&s.sosDeviceEmission>0})()')
            gesture=stats();assert abs(gesture['avatars'][0]['armSwing'])>2
            assert gesture['riskAccent']==gesture['coverageColor']=='fb3148'
            expect(page.get_by_test_id('private-sos-status')).to_have_text('Active')
            page.screenshot(path=str(out/'sos-press-critical.png'),full_page=True)
            record('Illustrative arm press, red device, CRITICAL room and synchronized count',{'gesture':gesture['sosGesture'],'arm':gesture['avatars'][0]['armSwing'],'count':gesture['active']})
            expect(guide.get_by_test_id('backend-scenario-assessment')).to_contain_text('CRITICAL')
            page.wait_for_function('!!JSON.parse(document.querySelector("[data-testid=private-three-renderer]").dataset.tracking).incidentId')
            identifier=stats()['incidentId'];evidence['incident_id']=identifier
            for _ in range(25):
                report=client.get('/incidents/'+identifier+'/report').json()
                if report['notification_state']!='PENDING':break
                time.sleep(.3)
            n=report['notifications'][-1]
            assert report['source_type']=='SIMULATION' and report['is_test'] is True and report['level']=='CRITICAL'
            assert {e['type'] for e in report['evidence']}=={'sos'}
            assert n['telegram_http_status']==200 and n['telegram_api_ok'] is True and n['telegram_recipient_matches'] is True
            assert n['transport_kind']=='real_https' and n['recipient_masked']==config['test_recipient_masked'] and len(report['notifications'])==1
            assert not n['receipt_confirmed']
            evidence.update(message_id=n['telegram_message_id'],telegram_http_status=n['telegram_http_status'],telegram_api_ok=n['telegram_api_ok'],accepted_at=n['api_accepted_at'],recipient_matches=True,notification_attempts=1)
            expect(guide.get_by_test_id('scenario-notification-state')).to_contain_text('API Accepted')
            record('Fresh exact SQLite incident sent once through REAL Telegram HTTPS',{'incident_id':identifier,'message_id':n['telegram_message_id'],'recipient':n['recipient_masked'],'accepted_at':n['api_accepted_at'],'receipt_verified':False})
            response=client.post('/incidents/'+identifier+'/ack',json={'staff':'AUTOMATED SOS integration TEST acknowledgement (not a human arrival)'})
            response.raise_for_status();expect(page.get_by_test_id('scenario-response-status')).to_have_text('ACKNOWLEDGED')
            assert stats()['visualRisk']=='CRITICAL' and stats()['active']==1
            record('Explicit test acknowledgement persists without clearing CRITICAL or the person','ACKNOWLEDGED')
            details.locator(':scope > summary').click();slider.fill('40');details.locator(':scope > summary').click()
            assert stats()['active']==1 and stats()['visualRisk']=='CRITICAL' and stats()['sosGesture']==0
            page.screenshot(path=str(out/'sos-completed.png'),full_page=True)
            guide.get_by_role('button',name='Restart guided demo',exact=True).click()
            guide.get_by_role('button',name='Pause guided demo',exact=True).click()
            details.locator(':scope > summary').click();slider.fill('40');details.locator(':scope > summary').click()
            after=client.get('/incidents/'+identifier+'/report').json()
            assert len(after['notifications'])==1 and after['notifications'][0]['telegram_message_id']==n['telegram_message_id']
            assert stats()['incidentId']==identifier and stats()['active']==1
            record('Completion, pause, seek and restart preserve the person and never resend',{'incident_id':identifier,'notification_attempts':1})
            for mode in ['RECORDED_REPLAY','LIVE_HARDWARE']:
                guide.get_by_role('combobox',name='Source mode').select_option(mode)
                page.wait_for_function('JSON.parse(document.querySelector("[data-testid=private-three-renderer]").dataset.tracking).active===0')
                assert not stats()['sosIllustrative']
                record(mode+' does not inherit the synthetic SOS person','zero invented tracks')
            assert not errors and page.locator('canvas').count()==1
            record('Original single Three.js canvas and no browser errors',errors)
            browser.close()
    except Exception as exc:
        rows.append({'test':'Live SOS integration','status':'FAIL','actual':type(exc).__name__+': '+str(exc)})
        raise
    finally:
        (out/'results.json').write_text(json.dumps(evidence,indent=2),encoding='utf-8');client.close()

if __name__=='__main__':main()
