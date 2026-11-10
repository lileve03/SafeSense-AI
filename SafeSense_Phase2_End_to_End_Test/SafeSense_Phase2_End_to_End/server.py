"""Local SafeSense Phase 2 replay lab. Synthetic data, never deploy as a public emergency endpoint."""
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse
import json, sqlite3, time, threading, os, io, csv, wave
ROOT=Path(__file__).resolve().parent
DB=ROOT/'incidents.db'
FRAMES=json.loads((ROOT/'test_twin.json').read_text())
CANDIDATES=json.loads((ROOT/'test_events.json').read_text())
DURATION=FRAMES[-1]['time']
LOCK=threading.RLock()
CLOCK={'running':False,'position':0.,'started':0.,'speed':1.,'emitted':set()}
ACOUSTIC={'state':'idle','error':None,'results':None,'model_ready':False,'threshold':0.5}
ACOUSTIC_LOCK=threading.RLock()
FUSION={'audio_offset':0.0,'window':2.0,'armed':False}

YAMNET_MODEL=None
YAMNET_CLASS=None

def conn():
 c=sqlite3.connect(DB, timeout=10); c.row_factory=sqlite3.Row; return c
with conn() as c:
 c.execute('CREATE TABLE IF NOT EXISTS incidents (id INTEGER PRIMARY KEY AUTOINCREMENT, event_type TEXT NOT NULL, severity TEXT NOT NULL, source TEXT NOT NULL, zone TEXT NOT NULL, position REAL, person_id TEXT, acknowledged INTEGER DEFAULT 0, created_at TEXT DEFAULT CURRENT_TIMESTAMP)')
 c.execute('CREATE TABLE IF NOT EXISTS fusion_links (id INTEGER PRIMARY KEY AUTOINCREMENT, incident_id INTEGER UNIQUE NOT NULL, radar_time REAL, acoustic_time REAL, delta REAL, radar_source TEXT, acoustic_source TEXT, note TEXT)')

def add_event(typ,sev,source,position=None,person=None,zone='toilet'):
 with conn() as c:
  cur=c.execute('INSERT INTO incidents (event_type,severity,source,zone,position,person_id) VALUES (?,?,?,?,?,?)',(typ,sev,source,zone,position,str(person) if person is not None else None))
  return cur.lastrowid


def infer_audio(raw, threshold):
 """Actual TF-Hub YAMNet inference. Nothing is stored. Never claims impact evaluation."""
 global YAMNET_MODEL, YAMNET_CLASS
 import numpy as np
 import tensorflow as tf
 import tensorflow_hub as hub
 with wave.open(io.BytesIO(raw), 'rb') as wav:
  if wav.getnchannels()!=1 or wav.getframerate()!=16000 or wav.getsampwidth()!=2 or wav.getcomptype()!='NONE':
   raise ValueError('Requires mono PCM 16-bit WAV at 16000 Hz (no speech recordings retained).')
  n=wav.getnframes()
  if not 1600<=n<=16000*90:raise ValueError('Audio length must be between 0.1 and 90 seconds.')
  audio=np.frombuffer(wav.readframes(n), dtype='<i2').astype(np.float32)/32768.0
 if YAMNET_MODEL is None:
  YAMNET_MODEL=hub.load('https://tfhub.dev/google/yamnet/1')
  rows=YAMNET_MODEL.class_map_path().numpy().decode('utf-8')
  with tf.io.gfile.GFile(rows) as f:
   classes=list(csv.DictReader(f))
  ids=[i for i,x in enumerate(classes) if x.get('mid')=='/m/03qc9zr' or x.get('display_name','').lower()=='screaming']
  if not ids:raise RuntimeError('Screaming class not found in YAMNet map')
  YAMNET_CLASS=ids[0]
 scores,_,_=YAMNET_MODEL(audio)
 series=scores.numpy()[:,YAMNET_CLASS]
 peak=float(np.max(series))
 # Return only scores/timestamps, not speech or source audio.
 points=[{'time':round(float(i)*0.48,2),'score':round(float(v),4)} for i,v in enumerate(series)]
 return {'label':'Potential Screaming','max_score':round(peak,4),'threshold':threshold,'detected':peak>=threshold,'scores':points,'duration':round(n/16000.,2),'model':'Google YAMNet TF-Hub v1','source':'real_audio_inference','confidence_calibrated':False}

def audio_peak_events(result):
 # Select every above-threshold window. Frame centers approximate 0.48s hops.
 return [float(x['time']) for x in result['scores'] if float(x['score'])>=float(result['threshold'])]

def try_fuse():
 """Correlate real WAV scores with synthetic Radar incident on an explicitly aligned replay clock.
 No implied real-world co-occurrence. SOS is independent and never fused.
 """
 with LOCK:
  with ACOUSTIC_LOCK:
   a=ACOUSTIC.get('results')
  if not (a and a.get('detected') and FUSION['armed']): return
  times=audio_peak_events(a)
  with conn() as c:
   falls=c.execute("SELECT id,position,source FROM incidents WHERE event_type='fall' ORDER BY id").fetchall()
   for fall in falls:
    ft=float(fall['position']); matches=[(abs(ft-(t+FUSION['audio_offset'])),t+FUSION['audio_offset']) for t in times]
    if not matches:continue
    delta,at=min(matches)
    if delta>FUSION['window']:continue
    if c.execute('SELECT 1 FROM fusion_links WHERE incident_id=?',(fall['id'],)).fetchone():continue
    c.execute("UPDATE incidents SET event_type='fused_fall_screaming',severity='HIGH',source='synthetic_radar+yamnet' WHERE id=?",(fall['id'],))
    c.execute('INSERT INTO fusion_links (incident_id,radar_time,acoustic_time,delta,radar_source,acoustic_source,note) VALUES (?,?,?,?,?,?,?)',(fall['id'],ft,at,round(delta,3),'synthetic_radar_replay','real_wav_yamnet','Aligned experimentally; independent recordings, not a verified joint incident'))

def process_audio(raw,threshold):
 try:
  out=infer_audio(raw,threshold)
  if out['detected']:
   out['incident_id']=add_event('potential_screaming','OBSERVE','yamnet_audio_test',None,None)
  with ACOUSTIC_LOCK:ACOUSTIC.update({'state':'complete','results':out,'error':None,'model_ready':True})
  try_fuse()
 except Exception as exc:
  with ACOUSTIC_LOCK:ACOUSTIC.update({'state':'error','results':None,'error':str(exc),'model_ready':False})

def update_clock():
 if CLOCK['running']:
  pos=min(DURATION, CLOCK['position']+(time.monotonic()-CLOCK['started'])*CLOCK['speed'])
  for i,e in enumerate(CANDIDATES):
   if i not in CLOCK['emitted'] and float(e['time'])<=pos:
    add_event('fall','HIGH','synthetic_radar_replay',e['time'],e.get('person_id'))
    CLOCK['emitted'].add(i)
    try_fuse()
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
   links={row['incident_id']:dict(row) for row in c.execute('SELECT * FROM fusion_links')}
   for e in events:e['fusion_evidence']=links.get(e['id'])
  return {'time':round(pos,2),'duration':DURATION,'running':CLOCK['running'],'tracks':frame['tracks'],'count':len(frame['tracks']),'incidents':events,'source':'synthetic_point_cloud','deployment_ready':False,'acoustic':dict(ACOUSTIC),'fusion':dict(FUSION),'sensors':{'radar':{'status':'replaying' if CLOCK['running'] else 'paused','source':'synthetic_radar_tracks','count':len(frame['tracks'])},'acoustic':{'status':ACOUSTIC['state'],'source':'yamnet_test_audio'},'sos':{'status':'ready','source':'manual_local_button'}}}
class Handler(BaseHTTPRequestHandler):
 def log_message(self,*args):pass
 def send(self,data,code=200):
  raw=json.dumps(data,ensure_ascii=False).encode();self.send_response(code);self.send_header('Content-Type','application/json; charset=utf-8');self.send_header('Content-Length',str(len(raw)));self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(raw)
 def do_GET(self):
  path=urlparse(self.path).path
  if path=='/state':return self.send(state())
  if path=='/health':return self.send({'ok':True,'mode':'offline_synthetic_replay','duration':DURATION,'yamnet_installed':__import__('importlib').util.find_spec('tensorflow') is not None and __import__('importlib').util.find_spec('tensorflow_hub') is not None})
  if path in ['/','/index.html']:
   raw=(ROOT/'index.html').read_bytes();self.send_response(200);self.send_header('Content-Type','text/html; charset=utf-8');self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw);return
  self.send({'error':'not found'},404)
 def do_POST(self):
  path=urlparse(self.path).path
  if path=='/acoustic/analyze':
   try:
    size=int(self.headers.get('Content-Length','0'))
    if not 44<=size<=12_000_000:raise ValueError('WAV must be 44 bytes to 12 MB')
    threshold=float(self.headers.get('X-Yamnet-Threshold','0.5'))
    if not 0.05<=threshold<=0.95:raise ValueError('Threshold must be 0.05..0.95')
    with ACOUSTIC_LOCK:
     if ACOUSTIC['state']=='processing':return self.send({'error':'Acoustic inference in progress'},409)
     ACOUSTIC.update({'state':'processing','results':None,'error':None,'threshold':threshold})
    raw=self.rfile.read(size)
    with wave.open(io.BytesIO(raw),'rb') as w:
     if w.getnchannels()!=1 or w.getframerate()!=16000 or w.getsampwidth()!=2 or w.getcomptype()!='NONE':
      raise ValueError('Use mono, 16 kHz, 16-bit PCM WAV')
     if not 0.1<=w.getnframes()/16000<=90:raise ValueError('Audio duration 0.1..90s only')
    threading.Thread(target=process_audio,args=(raw,threshold),daemon=True).start()
    return self.send({'ok':True,'state':'processing','note':'Inference uses real TF-Hub YAMNet; first run may download weights.'},202)
   except Exception as exc:
    with ACOUSTIC_LOCK:ACOUSTIC.update({'state':'error','error':str(exc)})
    return self.send({'error':str(exc)},400)
  try:
   size=int(self.headers.get('Content-Length','0'))
   if size>16384:raise ValueError('payload too large')
   data=json.loads(self.rfile.read(size) or b'{}')
   if not isinstance(data,dict):raise ValueError('JSON object expected')
   with LOCK:
    if path=='/fusion/config':
     offset=float(data.get('audio_offset',0));window=float(data.get('window',2))
     if not -90<=offset<=90 or not .25<=window<=10:raise ValueError('Offset -90..90 seconds; window 0.25..10 seconds')
     FUSION.update({'audio_offset':offset,'window':window,'armed':bool(data.get('armed',False))})
     try_fuse()
     return self.send(state())
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
     with conn() as c:
      c.execute('DELETE FROM fusion_links'); c.execute('DELETE FROM incidents')
     return self.send({'ok':True})
   return self.send({'error':'not found'},404)
  except (ValueError,TypeError,json.JSONDecodeError) as e:self.send({'error':str(e)},400)
if __name__=='__main__':
 port=int(os.environ.get('PORT','8765')); print(f'SafeSense local test: http://127.0.0.1:{port}',flush=True);ThreadingHTTPServer(('127.0.0.1',port),Handler).serve_forever()
