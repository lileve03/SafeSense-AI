"""One-off safe migration of the existing local demo's in-memory records."""
from pathlib import Path
from urllib.request import Request,urlopen
from datetime import datetime,timezone
import sys,json,os
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from backend import storage

def main():
    request=Request('http://127.0.0.1:8000/state',headers={'X-SafeSense-Token':os.getenv('SAFESENSE_API_TOKEN','local-demo-only')})
    with urlopen(request,timeout=5) as response:state=json.load(response)
    events=list(reversed(state['events']))
    incidents=list(reversed(state['incidents']))
    output=ROOT/'runtime/session-backups'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ.json')
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(state,indent=2),encoding='utf-8')
    storage.snapshot(events,incidents)
    print(json.dumps({'backup':str(output),'events':len(events),'incidents':len(incidents),'database':str(storage.DB)}))

if __name__=='__main__':main()
