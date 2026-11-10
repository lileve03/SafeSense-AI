"""TEST ONLY: existing application with an explicit fake Telegram HTTPS transport."""
from pathlib import Path
import os,json
from io import BytesIO
from backend import notifications
from backend.main import app
if os.getenv('SAFESENSE_TEST_CORS_ORIGIN'):
 from fastapi.middleware.cors import CORSMiddleware
 app.add_middleware(CORSMiddleware,allow_origins=[os.environ['SAFESENSE_TEST_CORS_ORIGIN']],allow_methods=['GET','POST'],allow_headers=['Content-Type','X-SafeSense-Token'])
last_nonce=''

def fake_transport(request,**kwargs):
 global last_nonce
 if request.full_url.endswith('/sendMessage'):
  payload=json.loads(request.data)
  last_nonce=payload['text'].split('/safesense_ack ')[-1]
  return BytesIO(b'{"ok":true,"result":{"message_id":701}}')
 if request.full_url.endswith('/getUpdates'):
  updates=[]
  if Path(os.environ['SAFESENSE_TEST_RECEIPT_FLAG']).is_file():
   updates=[{'update_id':702,'message':{'chat':{'id':-100123},'from':{'id':42,'is_bot':False},'text':'/safesense_ack '+last_nonce}}]
  return BytesIO(json.dumps({'ok':True,'result':updates}).encode())
 raise RuntimeError('Unexpected request in isolated mock transport')

notifications.urlopen=fake_transport
