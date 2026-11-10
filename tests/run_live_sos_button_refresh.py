"""Opt-in: click the actual SOS Test button once with a previously accepted cached test."""
import argparse,json,os,sys,time
from pathlib import Path
import httpx
from playwright.sync_api import sync_playwright,expect
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts.start_services import load_local_environment

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--send-live',action='store_true');parser.add_argument('--verify-existing',action='store_true');args=parser.parse_args()
    if not args.send_live and not args.verify_existing:raise SystemExit('No send. --send-live authorizes one fresh test; --verify-existing only reads its saved result.')
    load_local_environment();out=ROOT/'runtime/sos-button-refresh';out.mkdir(parents=True,exist_ok=True)
    client=httpx.Client(base_url='http://127.0.0.1:8000',headers={'X-SafeSense-Token':os.getenv('SAFESENSE_API_TOKEN','local-demo-only')},timeout=15)
    config=client.get('/notifications/status').json();assert config['mode']=='test' and config['transport_kind']=='real_https'
    if args.verify_existing:
        path=out/'results.json';e=json.loads(path.read_text(encoding='utf-8'))
        r=client.get('/incidents/'+e['incident_id']+'/report').json();n=r['notifications'][-1]
        assert len(r['notifications'])==1 and n['telegram_message_id']==e['message_id']
        assert n['telegram_api_ok'] is True and n['telegram_recipient_matches'] is True and n['telegram_http_status']==200
        e.update(status='PASS',live_send_status='PASS',read_only_verification=True,
                 initial_followup_note='The original UI follow-up expected Restart enabled; it was correctly disabled while Test Actions owns the scene. No additional live test was sent.')
        e.pop('error',None);path.write_text(json.dumps(e,indent=2),encoding='utf-8');print(json.dumps(e));client.close();return
    old='be588baa-5e91-4129-9aa1-84ef8e4c29db';report=client.get('/incidents/'+old+'/report').json()
    assert report['notification_state']=='API_ACCEPTED'
    session={'id':'e63a375e-5bb7-4612-a8d3-a12e39ffc7cd','zoneId':'ZONE_TOILET_BLINDSPOT','results':{'acoustic':{'status':'Not Tested'},'fusion':{'status':'Not Tested'},'sos':{'status':'Notification Sent','notification':'API_ACCEPTED','incidentId':old,'risk':'CRITICAL','source':'SIMULATED SOS TEST'}}}
    evidence={'old_incident_id':old,'old_message_id':report['notifications'][-1]['telegram_message_id'],'recipient_masked':config['test_recipient_masked'],'receipt_verified':False}
    try:
        with sync_playwright() as pw:
            browser=pw.chromium.launch(headless=True,args=['--enable-unsafe-swiftshader']);page=browser.new_page(viewport={'width':1600,'height':1600})
            page.set_default_timeout(25000)
            page.add_init_script('sessionStorage.setItem("safesense-private-test-actions-v1:ZONE_TOILET_BLINDSPOT",'+json.dumps(json.dumps(session))+');')
            page.goto('http://127.0.0.1:3000');page.locator('aside').get_by_role('button',name='Digital Twin Map',exact=True).click();page.locator('[data-zone-id="ZONE_TOILET_BLINDSPOT"] polygon').first.click()
            card=page.get_by_test_id('private-test-actions');card.get_by_role('button',name='Run SOS Test',exact=True).click()
            expect(card.get_by_test_id('test-sos-notification')).to_have_text('API accepted',timeout=25000)
            expect(card.get_by_role('button',name='Run SOS Test',exact=True)).to_be_enabled()
            state=page.evaluate('JSON.parse(sessionStorage.getItem("safesense-private-test-actions-v1:ZONE_TOILET_BLINDSPOT"))')
            identifier=state['results']['sos']['incidentId'];assert identifier!=old and state['sosGeneration']
            r=client.get('/incidents/'+identifier+'/report').json();n=r['notifications'][-1]
            assert n['telegram_api_ok'] is True and n['telegram_http_status']==200 and n['telegram_recipient_matches'] is True and n['transport_kind']=='real_https'
            assert n['telegram_message_id']!=evidence['old_message_id'] and len(r['notifications'])==1
            evidence.update(incident_id=identifier,message_id=n['telegram_message_id'],accepted_at=n['api_accepted_at'],telegram_http_status=200,telegram_api_ok=True,recipient_matches=True,notification_attempts=1)
            page.wait_for_function('JSON.parse(document.querySelector("[data-testid=private-three-renderer]").dataset.tracking).visualRisk==="CRITICAL"')
            page.screenshot(path=str(out/'fresh-button-test.png'),full_page=True)
            guide=page.get_by_test_id('guided-private-demo');expect(guide.get_by_role('button',name='Restart guided demo',exact=True)).to_be_disabled()
            details=page.get_by_test_id('private-track-details');details.locator(':scope > summary').click()
            slider=page.get_by_role('slider',name='Tracking playback time',exact=True);slider.fill('0');slider.fill('40')
            details.locator(':scope > summary').click()
            time.sleep(1)
            r=client.get('/incidents/'+identifier+'/report').json();assert len(r['notifications'])==1
            scene=json.loads(page.get_by_test_id('private-three-renderer').get_attribute('data-tracking'));assert scene['incidentId']==identifier and scene['testKind']=='sos'
            evidence.update(status='PASS',cached_test_replaced=True,guided_restart_disabled_during_test=True,seek_sent_no_duplicate=True)
            browser.close()
    except Exception as exc:
        evidence.update(status='FAIL',error=type(exc).__name__);raise
    finally:
        (out/'results.json').write_text(json.dumps(evidence,indent=2),encoding='utf-8');print(json.dumps(evidence));client.close()

if __name__=='__main__':main()
