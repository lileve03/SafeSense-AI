"""Explicit opt-in test-chat send through the running backend; never staff dispatch."""
from pathlib import Path
import argparse,json,os,sys
from uuid import uuid4
from urllib.request import Request,urlopen
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.start_services import load_local_environment

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--send-test',action='store_true',help='Explicitly authorize one simulated incident notification to TELEGRAM_TEST_CHAT_ID only')
    parser.add_argument('--verify-receipt',action='store_true',help='Check the authorized Telegram reply and acknowledge its existing test incident')
    parser.add_argument('--incident-id',help='Existing incident ID for receipt verification')
    parser.add_argument('--request-id',help='UUID to reuse when retrying the same authorized test')
    args=parser.parse_args();load_local_environment()
    base=os.getenv('SAFESENSE_BACKEND_URL','http://127.0.0.1:8000')
    headers={'X-SafeSense-Token':os.getenv('SAFESENSE_API_TOKEN','local-demo-only'),'Content-Type':'application/json'}
    def api(path,body=None):
        request=Request(base+path,headers=headers,data=json.dumps(body).encode() if body is not None else None)
        with urlopen(request,timeout=20) as response:return json.load(response)
    status=api('/notifications/status')
    print(json.dumps({'mode':status['mode'],'status':status['status'],'test_configured':status['test_configured']}))
    if args.verify_receipt:
        if not args.incident_id:raise SystemExit('--incident-id is required')
        result=api('/incidents/'+args.incident_id+'/verify-test-receipt',{})
        report=api('/incidents/'+args.incident_id+'/report')
        evidence={'incident_id':args.incident_id,'delivery_state':result.get('delivery_state') or result.get('state'),'receipt_confirmed_at':result.get('receipt_confirmed_at'),'incident_status':report['status'],'acknowledged_at':report.get('acknowledged_at')}
        output=ROOT/'runtime/telegram-integration';output.mkdir(parents=True,exist_ok=True)
        (output/'real-receipt-results.json').write_text(json.dumps(evidence,indent=2),encoding='utf-8')
        print(json.dumps(evidence))
        return
    if not args.send_test:
        print('No message sent. Configure authorized test chat and run again with --send-test.');return
    if status['mode']!='test' or not status['test_configured'] or status.get('transport_kind')!='real_https':
        raise SystemExit('Running backend must be in configured TEST mode using real HTTPS; no send attempted.')
    identifier=args.request_id or str(uuid4())
    output=ROOT/'runtime/telegram-integration';output.mkdir(parents=True,exist_ok=True)
    evidence={'request_id':identifier,'recipient_masked':status.get('test_recipient_masked'),'receipt_confirmed':False}
    # Save the idempotency key before I/O; an interrupted run can retry this UUID.
    target=output/'real-test-results.json';target.write_text(json.dumps(evidence,indent=2),encoding='utf-8')
    result=api('/notifications/send-test',{'request_id':identifier,'authorized':True})
    delivery=result['notification']
    evidence.update(incident_id=result['incident_id'],event_deduplicated=result['event_deduplicated'],
        delivery_state=delivery.get('delivery_state'),telegram_http_status=delivery.get('telegram_http_status'),
        telegram_api_ok=delivery.get('telegram_api_ok'),telegram_message_id=delivery.get('telegram_message_id'),
        recipient_matches=delivery.get('telegram_recipient_matches'),transport_kind=delivery.get('transport_kind'),
        api_accepted_at=delivery.get('api_accepted_at'),error=delivery.get('error'),error_code=delivery.get('error_code'),
        receipt_confirmed=delivery.get('receipt_confirmed',False))
    target.write_text(json.dumps(evidence,indent=2),encoding='utf-8');print(json.dumps(evidence))
    if evidence['delivery_state']!='API_ACCEPTED' or evidence['telegram_api_ok'] is not True or evidence['recipient_matches'] is not True:
        raise SystemExit('Authorized recipient API acceptance was not verified. No automatic resend was attempted.')
    print('Real Telegram API accepted the TEST message for the configured recipient; recipient receipt is NOT independently confirmed.')

if __name__=='__main__':main()
