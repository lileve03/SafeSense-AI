"""Fresh-process persistence probe. Receives only an isolated test DB via stdin."""
import json,os,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
settings=json.load(sys.stdin)
os.environ.update(SAFESENSE_DB_PATH=settings['db'],TELEGRAM_MODE='disabled',TELEGRAM_STAFF_DISPATCH_ENABLED='false')
from fastapi.testclient import TestClient
from backend import main,storage
client=TestClient(main.app,headers={'X-SafeSense-Token':main.TOKEN})
def send(group,kind,modality):
    result=client.post('/event',json={'zone':'ZONE_TOILET_BLINDSPOT','type':kind,'source':'simulation','sensor_modality':modality,
       'source_type':'SIMULATION','processing_mode':'simulation','is_test':True,'score':None,'model_version':None,
       'event_id':group+':'+kind,'analysis_run_id':group,'evidence_reference':'SIMULATED isolated restart readiness fixture'})
    result.raise_for_status();return result.json()
if settings['stage']=='create':
    fall=send(settings['group'],'fall','radar');fusion=send(settings['group'],'impact','acoustic')
    client.post('/incidents/'+fusion['incident']['id']+'/ack',json={'staff':'SIMULATED restart test reviewer'}).raise_for_status()
    delayed=send(settings['delayed_group'],'fall','radar')
    main._notify_pool.submit(lambda:None).result(timeout=10)
    result={'pid':os.getpid(),'incident_id':fusion['incident']['id'],'delayed_id':delayed['incident']['id'],
            'report':client.get('/incidents/'+fusion['incident']['id']+'/report').json(),'events':len(storage.all_rows('event'))}
else:
    before=storage.get('incident',settings['incident_id'])
    repeat=[send(settings['group'],'fall','radar'),send(settings['group'],'impact','acoustic')]
    after=storage.get('incident',settings['incident_id'])
    delayed=send(settings['delayed_group'],'impact','acoustic')
    main._notify_pool.submit(lambda:None).result(timeout=10)
    result={'pid':os.getpid(),'unchanged_on_retry':before==after,'retries_deduplicated':all(r.get('deduplicated') for r in repeat),
            'incident_id':repeat[-1]['incident']['id'],'status':repeat[-1]['incident']['status'],'delayed_id':delayed['incident']['id'],
            'delayed_level':delayed['incident']['level'],'incidents':len(storage.all_rows('incident')),'events':len(storage.all_rows('event'))}
print(json.dumps(result))
