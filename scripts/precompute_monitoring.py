"""Prepare registered recorded cameras once, sequentially, using the normal evidence/incident policy.
Use before a demo; no parallel model runs or fabricated previews. Token comes from env/.env.
"""
from pathlib import Path
import argparse,json,os,sys,time
from urllib.parse import urlparse
from urllib.request import Request,urlopen
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts.start_services import load_local_environment

def main():
    load_local_environment()
    parser=argparse.ArgumentParser(description='Precompute genuine recorded-camera analysis and browser playback')
    parser.add_argument('--backend',default=os.getenv('SAFESENSE_BACKEND_URL','http://127.0.0.1:8000'))
    parser.add_argument('--ai',default=os.getenv('SAFESENSE_AI_URL','http://127.0.0.1:8001'))
    parser.add_argument('--camera',action='append',help='Registered camera ID; defaults to all available recordings')
    parser.add_argument('--output',default=str(ROOT/'runtime/precompute-monitoring-results.json'))
    args=parser.parse_args()
    for base in (args.backend,args.ai):
        if urlparse(base).hostname not in ('localhost','127.0.0.1','::1'):parser.error('This CPU demo helper accepts local services only')
    token=os.getenv('SAFESENSE_API_TOKEN','local-demo-only');headers={'X-SafeSense-Token':token,'Content-Type':'application/json'}
    def call(base,path,data=None):
        with urlopen(Request(base.rstrip('/')+path,data=json.dumps(data).encode() if data is not None else None,headers=headers),timeout=30) as response:return json.load(response)
    cameras=call(args.backend,'/monitoring/cameras');rows=[]
    for camera in cameras:
        if args.camera and camera['camera_id'] not in args.camera:continue
        if not camera.get('available') or camera.get('stream_configured') or not camera.get('scenario'):continue
        started=time.perf_counter()
        with urlopen(Request(args.backend.rstrip('/')+'/monitoring/sources/'+camera['scenario']['id'],headers={**headers,'Range':'bytes=0-1023'}),timeout=90) as response:response.read(1024)
        row=call(args.ai,'/monitoring/jobs',{'camera_id':camera['camera_id'],'scenario_id':camera['scenario']['id'],'zone_id':camera['zone_id'],'model':'all','authorized':True})
        reused=row.get('cache_hit',False);tier=row.get('cache_tier')
        deadline=time.monotonic()+300
        while row['status'] in ('QUEUED','RUNNING') and time.monotonic()<deadline:
            time.sleep(.35);row=call(args.ai,'/monitoring/jobs/'+row['id'])
        if row['status']!='COMPLETED' or row['result'].get('model_errors'):raise RuntimeError('Analysis failed for '+camera['camera_id']+': '+str(row.get('error') or row.get('result',{}).get('model_errors')))
        result=row['result'];entry={'camera_id':camera['camera_id'],'job_id':row['id'],'cache_hit':reused,'cache_tier':tier,'elapsed_sec':round(time.perf_counter()-started,3),'original_cpu_sec':result['total_processing_sec'],'models':row['resolved_models'],'pose_frames':len(result.get('pose_frames',[])),'cache_key':row.get('cache_key')}
        rows.append(entry);print(json.dumps(entry),flush=True)
    output=Path(args.output);output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(rows,indent=2),encoding='utf-8')
    return 0
if __name__=='__main__':sys.exit(main())
