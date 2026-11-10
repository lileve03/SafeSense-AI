
from pathlib import Path
import json,time
from urllib.request import Request,urlopen
from playwright.sync_api import sync_playwright,expect
ROOT=Path(__file__).resolve().parents[1];out=ROOT/'runtime/audit-evidence-task4'
def get(base,path):
 with urlopen(Request(base+path,headers={'X-SafeSense-Token':'local-demo-only'}),timeout=10) as r:return json.load(r)
before=json.loads((out/'state-before-activation.json').read_text())['incidents']
assert get('http://127.0.0.1:8000','/state')['incidents']==before
all_media=[]
for incident in before:
 for observation in incident.get('evidence',[]):
  for media in observation.get('evidence_media',[]):
   manifest=get('http://127.0.0.1:8001','/monitoring/incidents/'+incident['id']+'/evidence/'+media['id']+'/metadata')
   assert manifest['incident_id']==incident['id'] and manifest['original_available']
   all_media.append({'incident':incident['id'],'evidence':media['id'],'model':media['model_version'],'annotated':manifest['annotated_available']})
with sync_playwright() as pw:
 browser=pw.chromium.launch(headless=True);page=browser.new_page(viewport={'width':1440,'height':1050});errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
 page.goto('http://127.0.0.1:3000');page.locator('aside').get_by_role('button',name='Incident Review',exact=True).click()
 samples=[]
 for model in ('v3','yolo11n-pose-temporal-rule-v1'):
  row=next(r for r in all_media if r['model']==model);page.get_by_placeholder('Search notes, staff, incident #...').fill(row['incident'][:8]);page.get_by_role('button',name='Audit Details',exact=True).click()
  section=page.get_by_test_id('incident-evidence');expect(section).to_have_attribute('data-incident-id',row['incident'])
  expect(section.get_by_text(row['incident'],exact=True)).to_be_visible()
  if section.get_by_label('Incident evidence clip',exact=True).count():section.get_by_label('Incident evidence clip',exact=True).select_option(row['evidence'])
  expect(section.locator('video')).to_have_attribute('data-evidence-id',row['evidence'])
  page.wait_for_function("()=>{let v=document.querySelector('[data-testid=incident-evidence] video');return v?.readyState>=2 && !v.paused && v.currentTime>.1}",timeout=20000)
  assert section.locator('video').evaluate('(v)=>v.muted && v.controls')
  samples.append(row);page.screenshot(path=str(out/('active-'+model+'.png')),full_page=True);page.get_by_role('button',name='Close',exact=True).click()
 private=next(i for i in before if i['zone_type']=='PRIVATE');page.get_by_placeholder('Search notes, staff, incident #...').fill(private['id'][:8]);page.get_by_role('button',name='Audit Details',exact=True).click()
 section=page.get_by_test_id('incident-evidence');expect(section.get_by_text('Private sensor metadata only. No images, video, or speech are captured.',exact=True)).to_be_visible();assert not section.locator('video,img,audio').count()
 page.set_viewport_size({'width':390,'height':844});assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
 assert not errors,errors
 browser.close()
assert get('http://127.0.0.1:8000','/state')['incidents']==before
result={'status':'PASS','active_incidents_preserved':len(before),'all_saved_media_verified':len(all_media),'browser_samples':samples,'private_media_elements':0,'mobile_no_overflow':True,'browser_errors':errors,'source':'Actual saved incident clips; no media/inference mocks and no new active incidents'}
(out/'activation.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
