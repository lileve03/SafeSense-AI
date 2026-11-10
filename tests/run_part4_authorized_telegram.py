"""Explicit manual integration check: sends one TEST SOS to configured test chat only."""
import json, os, sys, time
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
OUT=ROOT/'runtime/part4-private';OUT.mkdir(parents=True,exist_ok=True)
os.environ.update(SAFESENSE_DB_PATH=str(OUT/('telegram-'+str(time.time_ns())+'.sqlite3')),
                  TELEGRAM_MODE='test',TELEGRAM_STAFF_DISPATCH_ENABLED='false')
from backend import main, notifications, storage
from fastapi.testclient import TestClient

if '--send-authorized-test' not in sys.argv:raise SystemExit('Explicit --send-authorized-test required')
cfg=notifications.status()
if not cfg['test_configured']:
    result=dict(status='NOT_RUN',reason='Authorized Telegram test credentials are not configured')
else:
    with TestClient(main.app,headers={'X-SafeSense-Token':main.TOKEN}) as client:
        identifier=str(uuid4());group='private-demo:'+identifier
        body=dict(observation_id='part4-telegram-'+identifier,source_mode='SIMULATION',device_id='part4-authorized-test',
                  zone_id='ZONE_TOILET_BLINDSPOT',tracking_session_id=group,timestamp=datetime.now(timezone.utc).isoformat(),
                  data_validity='VALID',sos_state='ACTIVE',evidence_reference='SIMULATED authorized Part 4 Telegram test; no hardware emergency')
        response=client.post('/sensors/observations',json=body);response.raise_for_status()
        incident=response.json()['events'][0]['incident']['id']
        main._notify_pool.submit(lambda:None).result(timeout=30)
        report=client.get('/incidents/'+incident+'/report').json()
        retry=client.post('/sensors/observations',json=body);retry.raise_for_status()
        assert retry.json()['events'][0]['deduplicated']
        attempts=storage.all_rows('notification')
        assert len(attempts)==1 and attempts[0]['mode']=='test'
        result=dict(status='PASS' if report['notification_state']=='API_ACCEPTED' else 'FAIL',
                    incident_id=incident,notification_state=report['notification_state'],
                    notification_status=report['notification_status'],test_recipient_only=True,
                    receipt_verified=False,attempts=len(attempts))
        client.post('/incidents/'+incident+'/ack',json={'staff':'Part 4 authorized test operator'})
        client.post('/incidents/'+incident+'/review',json={'status':'RESOLVED','staff':'Part 4 authorized test operator',
                    'note':'Integration request completed; Telegram acceptance is distinct from recipient receipt.'})
(OUT/'telegram-result.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result,indent=2))
sys.exit(result['status']=='FAIL')
