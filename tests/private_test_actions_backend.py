"""Isolated browser fixture: real APIs/SQLite/models; fake Telegram HTTPS only."""
import json, os, time
from io import BytesIO
from pathlib import Path
from fastapi import Body
from backend import notifications
from backend.main import app

calls=[]
behavior='accepted'
original_model_path=os.environ.get('SAFESENSE_YAMNET_PATH')
def transport(request,**kwargs):
    assert request.full_url.endswith('/sendMessage')
    payload=json.loads(request.data)
    assert payload['chat_id']==os.environ['TELEGRAM_TEST_CHAT_ID']
    assert 'SAFESENSE TEST INCIDENT' in payload['text']
    calls.append({'test_recipient_only':True})
    time.sleep(.4)
    if behavior=='unknown':raise TimeoutError('Injected ambiguous transport timeout')
    if behavior=='failed':return BytesIO(b'{"ok":false,"error_code":400,"description":"Injected explicit rejection"}')
    return BytesIO(b'{"ok":true,"result":{"message_id":701}}')
notifications.urlopen=transport

@app.post('/__test__/configuration')
def configure(body:dict=Body(...)):
    global behavior
    behavior=body.get('behavior','accepted')
    os.environ['TELEGRAM_MODE']=body.get('telegram_mode','disabled')
    if body.get('acoustic_available',True):
        if original_model_path:os.environ['SAFESENSE_YAMNET_PATH']=original_model_path
        else:os.environ.pop('SAFESENSE_YAMNET_PATH',None)
    else:os.environ['SAFESENSE_YAMNET_PATH']=str(Path(__file__).resolve().parents[1]/'runtime/absent-acoustic-test-model')
    return {'transport_calls':len(calls),'transport':'MOCKED; no external delivery'}

@app.get('/__test__/transport')
def transport_state():return {'calls':len(calls),'all_test_recipient_only':all(c['test_recipient_only'] for c in calls),'transport':'MOCKED'}
