"""Local SafeSense Phase 2 replay lab. Synthetic data, never deploy as a public emergency endpoint."""
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse
import json, sqlite3, time, threading, os
ROOT=Path(__file__).resolve().parent
DB=ROOT/'incidents.db'
FRAMES=json.loads((ROOT/'test_twin.json').read_text())
CANDIDATES=json.loads((ROOT/'test_events.json').read_text())
DURATION=FRAMES[-1]['time']
LOCK=threading.RLock()
CLOCK={'running':False,'position':0.,'started':0.,'speed':1.,'emitted':set()}

def conn():
 c=sqlite3.connect(DB, timeout=10); c.row_factory=sqlite3.Row; return c
with conn() as c:
 c.execute('CREATE TABLE IF NOT EXISTS incidents (id INTEGER PRIMARY KEY AUTOINCREMENT, event_type TEXT NOT NULL, severity TEXT NOT NULL, source TEXT NOT NULL, zone TEXT NOT NULL, position REAL, person_id TEXT, acknowledged INTEGER DEFAULT 0, created_at TEXT DEFAULT CURRENT_TIMESTAMP)')

def add_event(typ,sev,source,position=None,person=None,zone='toilet'):
 with conn() as c:
  cur=c.execute('INSERT INTO incidents (event_type,severity,source,zone,position,person_id) VALUES (?,?,?,?,?,?)',(typ,sev,source,zone,position,str(person) if person is not None else None))
  return cur.lastrowid

def update_clock():
 if CLOCK['running']:
  pos=min(DURATION, CLOCK['position']+(time.monotonic()-CLOCK['started'])*CLOCK['speed'])
  for i,e in enumerate(CANDIDATES):
   if i not in CLOCK['emitted'] and float(e['time'])<=pos:
    add_event('fall','HIGH','synthetic_radar_replay',e['time'],e.get('person_id'))
    CLOCK['emitted'].add(i)
  if pos>=DURATION:
   CLOCK['running']=False;CLOCK['position']=DURATION
  return pos
 return CLOCK['position']

def state():
 with LOCK:
  pos=update_clock(); lo=0; hi=len(FRAMES)-1
  while lo<hi:
   mid=(lo+hi+1)//2
   if FRAMES[mid]['time']<=pos:lo=mid
   else:hi=mid-1
  frame=FRAMES[lo]
  with conn() as c:
   events=[dict(row) for row in c.execute('SELECT * FROM incidents ORDER BY id DESC LIMIT 60')]
  return {'time':round(pos,2),'duration':DURATION,'running':CLOCK['running'],'tracks':frame['tracks'],'count':len(frame['tracks']),'incidents':events,'source':'synthetic_point_cloud','deployment_ready':False}
class Handler(BaseHTTPRequestHandler):
 def log_message(self,*args):pass
 def send(self,data,code=200):
  raw=json.dumps(data,ensure_ascii=False).encode();self.send_response(code);self.send_header('Content-Type','application/json; charset=utf-8');self.send_header('Content-Length',str(len(raw)));self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(raw)
 def do_GET(self):
  path=urlparse(self.path).path
  if path=='/state':return self.send(state())
  if path=='/health':return self.send({'ok':True,'mode':'offline_synthetic_replay','duration':DURATION})
  if path in ['/','/index.html']:
   raw=(ROOT/'index.html').read_bytes();self.send_response(200);self.send_header('Content-Type','text/html; charset=utf-8');self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw);return
  self.send({'error':'not found'},404)
 def do_POST(self):
  path=urlparse(self.path).path
  try:
   size=int(self.headers.get('Content-Length','0'))
   if size>16384:raise ValueError('payload too large')
   data=json.loads(self.rfile.read(size) or b'{}')
   if not isinstance(data,dict):raise ValueError('JSON object expected')
   with LOCK:
    if path=='/replay/start':
     update_clock(); CLOCK['running']=True; CLOCK['started']=time.monotonic();return self.send(state())
    if path=='/replay/pause':
     CLOCK['position']=update_clock();CLOCK['running']=False;return self.send(state())
    if path=='/replay/reset':
     CLOCK.update({'running':False,'position':0.,'started':0.,'emitted':set()});return self.send(state())
    if path=='/replay/seek':
     pos=float(data.get('time',0))
     if not 0<=pos<=DURATION:raise ValueError('Invalid replay time')
     CLOCK['position']=pos;CLOCK['started']=time.monotonic()
     # Seeking does NOT insert historical incidents. Replay crossing inserts events.
     return self.send(state())
    if path=='/event':
     if data.get('event_type')!='sos' or data.get('source')!='sos_button':raise ValueError('Only explicit SOS button test events accepted')
     id=add_event('sos','CRITICAL','sos_button',update_clock())
     return self.send({'ok':True,'incident_id':id},201)
    if path.startswith('/incidents/') and path.endswith('/ack'):
     try:id=int(path.split('/')[2])
     except ValueError:raise ValueError('Invalid id')
     with conn() as c:cur=c.execute('UPDATE incidents SET acknowledged=1 WHERE id=?',(id,))
     if not cur.rowcount:return self.send({'error':'Unknown incident'},404)
     return self.send({'ok':True,'id':id})
    if path=='/incidents/clear':
     with conn() as c:c.execute('DELETE FROM incidents')
     return self.send({'ok':True})
   return self.send({'error':'not found'},404)
  except (ValueError,TypeError,json.JSONDecodeError) as e:self.send({'error':str(e)},400)
if __name__=='__main__':
 port=int(os.environ.get('PORT','8765')); print(f'SafeSense local test: http://127.0.0.1:{port}',flush=True);ThreadingHTTPServer(('127.0.0.1',port),Handler).serve_forever()
