"""Verify report exports in Chromium against a read-only copy of actual incident records.
Print preview uses print media and Chromium PDF because the native dialog is unavailable headless.
"""
from pathlib import Path
from collections import Counter
from datetime import datetime,timezone
from urllib.request import Request,urlopen
import json,sqlite3,hashlib,sys,time,traceback,os,subprocess
from playwright.sync_api import sync_playwright,expect
from pypdf import PdfReader
import csv,io
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'runtime/analytics-reports-final';OUT.mkdir(parents=True,exist_ok=True)
sys.stdout.reconfigure(encoding='utf-8');RESULTS=[]

BASE='http://127.0.0.1:18020';DASH='http://127.0.0.1:3001';TOKEN='analytics-read-only-test'
DB_PATH=OUT/('snapshot-'+str(time.time_ns())+'.sqlite3')
with sqlite3.connect('file:'+str(ROOT/'runtime/safesense.sqlite3')+'?mode=ro',uri=True) as original,sqlite3.connect(DB_PATH) as copied:original.backup(copied)
ENV=os.environ.copy();ENV.update(SAFESENSE_DB_PATH=str(DB_PATH),SAFESENSE_API_TOKEN=TOKEN,VITE_SAFESENSE_API_TOKEN=TOKEN,TELEGRAM_MODE='disabled',VITE_API_BASE_URL=BASE,VITE_AI_BASE_URL='http://127.0.0.1:18021',SAFESENSE_BACKEND_URL=BASE)
processes=[]
def start_service(name,command,cwd,url):
 log=(OUT/(name+'.log')).open('w',encoding='utf-8');process=subprocess.Popen(command,cwd=cwd,env=ENV,stdout=log,stderr=subprocess.STDOUT,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0));processes.append((process,log))
 for _ in range(180):
  if process.poll() is not None:raise RuntimeError(name+' stopped')
  try:
   with urlopen(url,timeout=1) as response:
    if response.status==200:return
  except OSError:pass
  time.sleep(.2)
 raise RuntimeError(name+' timeout')
def check(name,fn):
 try:actual=fn();row={'test':name,'status':'PASS','actual':actual}
 except Exception as exc:row={'test':name,'status':'FAIL','actual':str(exc),'trace':traceback.format_exc()}
 RESULTS.append(row);(OUT/'results.json').write_text(json.dumps(RESULTS,indent=2));print(row['status'],name,str(row['actual'])[:600],flush=True)
def get(path):
 with urlopen(Request(BASE+path,headers={'X-SafeSense-Token':TOKEN}),timeout=10) as r:return json.load(r)
def db_records():
 with sqlite3.connect('file:'+str(DB_PATH)+'?mode=ro',uri=True) as db:return [json.loads(row[0]) for row in db.execute("SELECT body FROM records WHERE kind='incident' ORDER BY rowid")]

import shutil,re
EVIDENCE=OUT/'evidence';EVIDENCE.mkdir(exist_ok=True);ENV['SAFESENSE_EVIDENCE_DIR']=str(EVIDENCE)
records=db_records();copied=[]
protected=['pages/OverviewPage.tsx','pages/LiveMonitoringPage.tsx','pages/AlertsPage.tsx','pages/DigitalTwinPage.tsx','components/private-area/PrivateAreaMonitoringView.tsx','components/private-area/PrivateAreaDigitalTwin3D.tsx','components/analysis/CameraMonitoringPanel.tsx']
protected_hashes={p:hashlib.sha256((ROOT/'dashboard/src'/p).read_bytes()).hexdigest() for p in protected}
for r in records:
 for e in r.get('evidence',[]):
  for m in e.get('evidence_media',[]):
   if all((ROOT/'runtime/evidence'/(m['id']+suffix)).is_file() for suffix in ('.mp4','.json')):
    for suffix in ('.mp4','.json'):shutil.copy2(ROOT/'runtime/evidence'/(m['id']+suffix),EVIDENCE/(m['id']+suffix))
    copied.append((r,m))
assert copied,'Actual retained incident clips required for this test'
AI='http://127.0.0.1:18021'
def ai(path,token=TOKEN):
 return urlopen(Request(AI+path,headers={'X-SafeSense-Token':token}),timeout=20)
def drawn_images(page):
 # jsPDF shares image resources across pages; count only image Do operators
 # actually painted on this page, not unused entries in /Resources.
 resources=page.get('/Resources',{}).get('/XObject',{})
 resources=resources.get_object() if hasattr(resources,'get_object') else resources
 return sum(1 for name in re.findall(rb'/([A-Za-z0-9]+)\s+Do',page.get_contents().get_data()) if resources.get('/'+name.decode()) and resources['/'+name.decode()].get_object().get('/Subtype')=='/Image')
def read_pdf(path):
 pdf=PdfReader(path);text='\n'.join(p.extract_text() for p in pdf.pages)
 assert all(abs(float(p.mediabox.width)-595.28)<2 and abs(float(p.mediabox.height)-841.89)<2 for p in pdf.pages)
 assert all(len(p.extract_text())>40 for p in pdf.pages)
 return pdf,text
try:
 start_service('backend',[str(ROOT/'.venv/Scripts/python.exe'),'-m','uvicorn','backend.main:app','--host','127.0.0.1','--port','18020'],ROOT,BASE+'/health')
 start_service('inference',[str(ROOT/'.venv-vision/Scripts/python.exe'),'-m','uvicorn','fight_api:app','--host','127.0.0.1','--port','18021'],ROOT,AI+'/health')
 start_service('frontend',['node',str(ROOT/'dashboard/node_modules/vite/bin/vite.js'),'--host','127.0.0.1','--port','3001','--strictPort'],ROOT/'dashboard',DASH)
 zones=get('/zones');zone_names={z['id']:z['name'] for z in zones}
 def thumbnail_security():
  from urllib.error import HTTPError
  r,m=copied[0];route='/monitoring/incidents/'+r['id']+'/evidence/'+m['id']+'/thumbnail'
  with ai(route) as response:
   data=response.read();assert data[:2]==b'\xff\xd8' and response.headers['Content-Type']=='image/jpeg';assert response.headers.get('X-Evidence-Frame-Sec')
  (OUT/'actual-evidence-thumbnail.jpg').write_bytes(data)
  results=[]
  for path,token,expected in [(route,'invalid',401),('/monitoring/incidents/'+next(x['id'] for x in records if x.get('zone_type')!='OPEN_HIDDEN')+'/evidence/'+m['id']+'/thumbnail',TOKEN,403),('/monitoring/incidents/'+next(x['id'] for x in records if x['id']!=r['id'] and x.get('zone_type')=='OPEN_HIDDEN')+'/evidence/'+m['id']+'/thumbnail',TOKEN,404)]:
   try:ai(path,token);raise AssertionError('Unauthorized evidence succeeded')
   except HTTPError as e:assert e.code==expected,(e.code,expected);results.append(e.code)
  return {'JPEG_bytes':len(data),'rejected_statuses':results}
 check('Actual evidence JPEG and authentication/private/ownership rejection',thumbnail_security)
 with sync_playwright() as pw:
  browser=pw.chromium.launch(headless=True,args=['--enable-unsafe-swiftshader']);page=browser.new_page(viewport={'width':1500,'height':1050});page.set_default_timeout(20000)
  names={};errors=[];thumbnail_requests=[];page.on('pageerror',lambda e:errors.append(str(e)));page.on('request',lambda r:thumbnail_requests.append(r.url) if r.url.endswith('/thumbnail') else None)
  page.goto(DASH+'/#/analytics-reports');view=page.get_by_test_id('analytics-reports');expect(view.get_by_test_id('analytics-kpi-total').locator('[data-value]')).to_have_text(str(len(records)))
  def download_pdf(name):
   with page.expect_download(timeout=45000) as download:view.get_by_role('button',name='Download PDF',exact=True).click()
   path=OUT/name;download.value.save_as(path);names[name]=download.value.suggested_filename;return path
  def verify_values(pdf,text,rows):
   first=pdf.pages[0].extract_text()
   kpis={'Total Incidents':len(rows),'High Risk':sum(r['level'] in ('HIGH','CRITICAL') for r in rows),'SOS':sum(r.get('source')=='sos_button' or any(e.get('type','').lower()=='sos' for e in r.get('evidence',[])) for r in rows),'Pending Review':sum(r.get('review_status')=='pending_human_review' for r in rows),'Resolved':sum(r['status']=='RESOLVED' for r in rows)}
   for title,value in kpis.items():assert re.search(re.escape(title)+r'\s+'+str(value)+r'\b',first),(title,value,first)
   for r in rows:assert '#'+r['id'][:8] in text
   for title in ['Incident Trend','Incident Types','Incidents by Zone','Severity Distribution','Response / Resolution Status','Permitted Incident Evidence','Incident Records']:assert title in text,title
   return kpis
  def validate_charts(rows):
   counts={key:Counter(r.get(field) or 'unknown' for r in rows) for key,field in [('severity','level'),('zones','zone_id'),('statuses','status'),('modes','processing_mode'),('sources','source')]}
   counts['types']=Counter(t for r in rows for t in (set(e.get('type') for e in r.get('evidence',[]) if e.get('type')) or {'Not recorded'}))
   counts['trend']=Counter(datetime.fromisoformat(r['created_at'].replace('Z','+00:00')).astimezone(timezone.utc).date().isoformat() for r in rows)
   counts['acknowledgements']=Counter('Acknowledged' if r.get('acknowledged_at') else 'No acknowledgement recorded' for r in rows)
   for key,value in counts.items():
    actual=dict(view.get_by_test_id('analytics-'+key).locator('tbody tr').evaluate_all('(rs)=>rs.map(r=>[r.dataset.key,Number(r.querySelector("td").textContent)])'))
    assert actual==dict(value),(key,actual,dict(value))
   return {key:dict(value) for key,value in counts.items()}
  check('All eight dashboard charts independently match SQLite incident groups',lambda:validate_charts(records))
  def download_csv(rows,name):
   with page.expect_download(timeout=30000) as download:view.get_by_role('button',name='Download CSV',exact=True).click()
   path=OUT/name;download.value.save_as(path);names[name]=download.value.suggested_filename
   data=path.read_bytes();assert data.startswith(b'\xef\xbb\xbf');parsed=list(csv.DictReader(io.StringIO(data.decode('utf-8-sig'))))
   assert {r['Incident ID'] for r in parsed}=={r['id'] for r in rows};assert len(parsed)==len(rows)
   def safe(value):
    value='' if value is None else str(value)
    return "'"+value if re.match(r'^[\s\x00-\x1f]*[=+@-]|^[\t\r\n]',value) else value
   for row in parsed:
    r=next(r for r in rows if r['id']==row['Incident ID']);evidence=r.get('evidence',[])
    allowed=r.get('zone_type')=='OPEN_HIDDEN' and any(z['id']==r['zone_id'] and z['zone_type']=='OPEN_HIDDEN' for z in zones)
    expected=[r['id'],r.get('created_at'),zone_names.get(r['zone_id'],r['zone_id']),'; '.join(dict.fromkeys(e.get('type') for e in evidence if e.get('type'))),r['level'],r.get('source'),'; '.join(e.get('model_version') or '' for e in evidence),'; '.join(str(e['score']) if e.get('score') is not None else '' for e in evidence),r.get('processing_mode'),r.get('review_status'),r.get('assigned_staff') or r.get('staff') or '',r.get('acknowledged_at'),r.get('resolved_at'),'; '.join(str(e.get('evidence_reference') or e.get('id') or 'No retained reference') if allowed else 'Private sensor metadata only; media excluded' for e in evidence)]
    assert list(row.values())==[safe(x) for x in expected],(row,expected)
   return {'rows':len(parsed),'columns':list(csv.DictReader(io.StringIO(data.decode('utf-8-sig'))).fieldnames),'bytes':len(data),'UTF8_BOM':True,'file':name}
  downloaded=download_pdf('download-visual.pdf');pdf,text=read_pdf(downloaded)
  def download_check():
   values=verify_values(pdf,text,records);images=sum(drawn_images(p) for p in pdf.pages);assert images>0,'Real evidence thumbnail missing';assert drawn_images(pdf.pages[0])==0 and drawn_images(pdf.pages[1])==0,'Charts must remain vector'
   (OUT/'download-text.txt').write_text(text,encoding='utf-8')
   assert 'School Command Console' not in text
   return {'pages':len(pdf.pages),'bytes':downloaded.stat().st_size,'evidence_images':images,'vector_chart_pages':2,'KPIs':values}
  check('Download PDF: vector charts, actual KPI values, retained thumbnails and A4 pagination',download_check)
  def csv_all():
   result=download_csv(records,'filtered-all.csv');assert Path(names['filtered-all.csv']).stem==Path(names['download-visual.pdf']).stem;return {**result,'same_dataset_id_as_PDF':True}
  check('Filtered CSV: all 14 fields match SQLite and the PDF dataset ID',csv_all)
  def print_check():
   page.evaluate("""() => {const append=document.body.append.bind(document.body);document.body.append=(...nodes)=>{for(const n of nodes)if(n.tagName==='IFRAME'){const original=n.onload;n.onload=()=>{n.contentWindow.print=()=>{n.dataset.printInvoked='true'};original()}}return append(...nodes)}}""")
   view.get_by_role('button',name='Print PDF',exact=True).click();frame=page.locator('iframe[title="Print SafeSense visual report"]');expect(frame).to_have_attribute('data-print-invoked','true',timeout=45000)
   html=frame.evaluate('(f)=>f.contentDocument.documentElement.outerHTML');(OUT/'print-report.html').write_text(html,encoding='utf-8')
   preview=browser.new_page(viewport={'width':1000,'height':1400});preview.set_content(html);preview.emulate_media(media='print')
   assert preview.locator('button,nav,aside,input,select,video').count()==0
   assert preview.locator('.report-sheet').count()==len(pdf.pages)
   ids=preview.locator('svg image').evaluate_all('(es)=>es.map(e=>e.dataset.incidentId)');assert ids
   assert all(next(r for r in records if r['id']==i)['zone_type']=='OPEN_HIDDEN' for i in ids)
   assert preview.locator('body').get_attribute('data-report-id') in str(pdf.metadata.subject)
   preview.pdf(path=str(OUT/'print-visual.pdf'),prefer_css_page_size=True,print_background=True,display_header_footer=False)
   printed,printed_text=read_pdf(OUT/'print-visual.pdf');assert len(printed.pages)==len(pdf.pages),(len(printed.pages),len(pdf.pages));verify_values(printed,printed_text,records)
   assert sum(drawn_images(p) for p in printed.pages)==sum(drawn_images(p) for p in pdf.pages)
   preview.screenshot(path=str(OUT/'print-preview-browser.png'),full_page=True);preview.close();frame.evaluate('(f)=>f.remove()')
   return {'browser_print_invoked':True,'same_layout_id':str(pdf.metadata.subject),'pages':len(printed.pages),'same_values_and_images':True,'native_dialog':'Headless: print document, invocation and Chromium PDF inspected'}
  check('Print PDF separately: identical dataset/layout, vector SVG pages and permitted images',print_check)
  def filtered():
   r=next(r for r,m in reversed(copied) if r.get('created_at') and r.get('evidence'))
   day=r['created_at'][:10];event=r['evidence'][0]['type'];view.get_by_label('Analytics date range').select_option('custom');view.get_by_label('Analytics from date').fill(day);view.get_by_label('Analytics to date').fill(day);view.get_by_label('Analytics zone',exact=True).select_option(r['zone_id']);view.get_by_label('Analytics severity').select_option(r['level']);view.get_by_label('Analytics event type').select_option(event)
   rows=[x for x in records if x['created_at'][:10]==day and x['zone_id']==r['zone_id'] and x['level']==r['level'] and any(e.get('type')==event for e in x.get('evidence',[]))]
   expect(view.get_by_test_id('analytics-kpi-total').locator('[data-value]')).to_have_text(str(len(rows)))
   validate_charts(rows);download_csv(rows,'filtered-subset.csv')
   filtered_path=download_pdf('filtered-visual.pdf');selected_pdf,selected_text=read_pdf(filtered_path);verify_values(selected_pdf,selected_text,rows)
   for other in records:
    if other['id'] not in {x['id'] for x in rows}:assert '#'+other['id'][:8] not in selected_text
   assert day in selected_text and zone_names[r['zone_id']] in selected_text
   assert Path(names['filtered-subset.csv']).stem==Path(names['filtered-visual.pdf']).stem
   view.get_by_role('button',name='Reset filters',exact=True).click()
   return {'day':day,'zone':r['zone_id'],'severity':r['level'],'event':event,'selected':len(rows),'pages':len(selected_pdf.pages)}
  check('Actual date, zone, severity and event filters constrain the entire visual report',filtered)
  def private_empty():
   private=next(r for r in records if r.get('zone_type')!='OPEN_HIDDEN');view.get_by_label('Analytics zone',exact=True).select_option(private['zone_id']);start_requests=len(thumbnail_requests)
   download_csv([r for r in records if r['zone_id']==private['zone_id']],'private-metadata.csv')
   private_path=download_pdf('private-metadata.pdf');private_pdf,private_text=read_pdf(private_path);assert sum(drawn_images(p) for p in private_pdf.pages)==0
   assert len(thumbnail_requests)==start_requests,'Private export requested video thumbnails';assert 'sensor metadata only' in private_text
   view.get_by_role('button',name='Reset filters',exact=True).click();view.get_by_label('Analytics date range').select_option('custom');view.get_by_label('Analytics from date').fill('2099-01-01');view.get_by_label('Analytics to date').fill('2099-01-02')
   download_csv([],'empty.csv')
   empty_path=download_pdf('no-data.pdf');empty_pdf,empty_text=read_pdf(empty_path);assert empty_text.count('No data')>=10;assert sum(drawn_images(p) for p in empty_pdf.pages)==0
   return {'private_images':0,'private_thumbnail_requests':0,'no_data_labels':empty_text.count('No data'),'empty_pages':len(empty_pdf.pages)}
  check('Private selections never request images; empty reports display No data',private_empty)
  def navigation_and_features():
   view.get_by_role('button',name='Reset filters',exact=True).click()
   nav=page.locator('aside')
   expect(nav.get_by_role('button',name='Analytics & Reports',exact=True)).to_have_count(1);expect(nav.get_by_role('button',name='Analytics',exact=True)).to_have_count(0);expect(nav.get_by_role('button',name='Reports',exact=True)).to_have_count(0)
   for alias in ['/#/analytics','/#/reports','/analytics','/reports','/#/analytics-reports','/analytics-reports']:
    page.goto(DASH+alias);expect(view.get_by_test_id('analytics-kpi-total').locator('[data-value]')).to_have_text(str(len(records)));assert page.url.endswith('#/analytics-reports');validate_charts(records)
   for destination in ['Overview','Live Monitoring','Alerts','Digital Twin Map']:
    nav.get_by_role('button',name=destination,exact=True).click();expect(page.locator('main')).to_be_visible()
    if destination=='Overview':expect(page.get_by_role('heading',name='Latest Incidents',exact=True)).to_be_visible()
    elif destination=='Live Monitoring':expect(page.get_by_role('heading',name='Campus Camera Feeds',exact=True)).to_be_visible()
    elif destination=='Alerts':expect(page.locator('main h2').first).to_be_visible()
    else:expect(page.get_by_role('heading',name='Interactive Campus Digital Twin',exact=True)).to_be_visible()
   page.locator('[data-zone-id="ZONE_TOILET_BLINDSPOT"] polygon').first.click()
   private=page.get_by_test_id('private-monitoring-view');expect(private).to_be_visible();scene=page.get_by_test_id('private-twin-scene');expect(scene.locator('canvas')).to_be_visible()
   assert private.locator('video,img').count()==0
   healthy=scene.locator('canvas').evaluate('(c)=>{const gl=c.getContext("webgl2");return !!gl&&!gl.isContextLost()&&c.width>0}')
   assert healthy
   page.screenshot(path=str(OUT/'private-monitoring-regression.png'),full_page=True)
   nav.get_by_role('button',name='Analytics & Reports',exact=True).click();expect(view).to_be_visible();page.screenshot(path=str(OUT/'combined-desktop.png'),full_page=True)
   page.set_viewport_size({'width':390,'height':844});page.wait_for_timeout(200);assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1');page.screenshot(path=str(OUT/'combined-mobile.png'),full_page=True);page.set_viewport_size({'width':1500,'height':1050})
   return {'aliases':6,'single_navigation':True,'other_pages':4,'private_3D_WebGL':healthy,'private_media':0,'responsive':True}
  check('Combined navigation, legacy links and unchanged monitoring pages/private 3D',navigation_and_features)
  def fixture_exports():
   # Explicit UI stress/security fixtures only; actual-data assertions above use SQLite.
   import copy,uuid
   long_label='Long Layout Test Zone - '+'North perimeter corridor and supervised access walkway '*12
   template=copy.deepcopy(records[0]);template.update(zone_id='FIXTURE_ZONE',zone_type='OPEN_HIDDEN',processing_mode='simulation',source='simulation',is_test=True,status='NEW',review_status='pending_human_review',acknowledged_at=None,resolved_at=None,assigned_staff='=HYPERLINK("fixture")',evidence=[{'type':'fall','model_version':'fixture-layout-only','score':None,'evidence_reference':'fixture,"quoted"\nreference'}])
   long_records=[{**template,'id':str(uuid.uuid5(uuid.NAMESPACE_URL,'safesense-long-'+str(i)))} for i in range(2)]
   stress_records=[{**template,'id':str(uuid.uuid5(uuid.NAMESPACE_URL,'safesense-stress-'+str(i)))} for i in range(300)]
   fixture=browser.new_page(viewport={'width':1500,'height':1050});fixture_records=long_records;fixture_zone=long_label
   fixture.route('**/incidents',lambda route:route.fulfill(json=fixture_records));fixture.route('**/zones',lambda route:route.fulfill(json=[{'id':'FIXTURE_ZONE','name':fixture_zone,'zone_type':'OPEN_HIDDEN'}]))
   fixture.goto(DASH+'/#/analytics-reports');fv=fixture.get_by_test_id('analytics-reports');expect(fv.get_by_test_id('analytics-kpi-total').locator('[data-value]')).to_have_text('2')
   fv.get_by_label('Analytics zone',exact=True).select_option('FIXTURE_ZONE')
   with fixture.expect_download() as dl:fv.get_by_role('button',name='Download PDF',exact=True).click()
   dl.value.save_as(OUT/'long-labels.pdf');long_pdf,long_text=read_pdf(OUT/'long-labels.pdf');assert 'Report Filter Scope' in long_text
   for r in long_records:assert '#'+r['id'][:8] in long_text
   with fixture.expect_download() as dl:fv.get_by_role('button',name='Download CSV',exact=True).click()
   dl.value.save_as(OUT/'long-labels.csv');csv_rows=list(csv.DictReader(io.StringIO((OUT/'long-labels.csv').read_text(encoding='utf-8-sig'))));assert csv_rows[0]['Zone']==long_label;assert csv_rows[0]['Assigned Staff'].startswith("'=");assert csv_rows[0]['Evidence Reference']=='fixture,"quoted"\nreference'
   fixture_records=stress_records;fixture_zone='Large dataset test zone';fixture.reload();expect(fv.get_by_test_id('analytics-kpi-total').locator('[data-value]')).to_have_text('300')
   with fixture.expect_download() as dl:fv.get_by_role('button',name='Download PDF',exact=True).click()
   dl.value.save_as(OUT/'large-dataset.pdf');stress_pdf,stress_text=read_pdf(OUT/'large-dataset.pdf');assert len(stress_pdf.pages)>10
   for r in stress_records:assert '#'+r['id'][:8] in stress_text
   with fixture.expect_download() as dl:fv.get_by_role('button',name='Download CSV',exact=True).click()
   dl.value.save_as(OUT/'large-dataset.csv');assert len(list(csv.DictReader(io.StringIO((OUT/'large-dataset.csv').read_text(encoding='utf-8-sig')))))==300
   fixture.evaluate("""()=>{const append=document.body.append.bind(document.body);document.body.append=(...nodes)=>{for(const n of nodes)if(n.tagName==='IFRAME'){const original=n.onload;n.onload=()=>{n.contentWindow.print=()=>{n.dataset.printInvoked='true'};original()}}return append(...nodes)}}""")
   fv.get_by_role('button',name='Print PDF',exact=True).click();frame=fixture.locator('iframe[title="Print SafeSense visual report"]');expect(frame).to_have_attribute('data-print-invoked','true');html=frame.evaluate('(f)=>f.contentDocument.documentElement.outerHTML')
   preview=browser.new_page();preview.set_content(html);preview.emulate_media(media='print');preview.pdf(path=str(OUT/'large-dataset-print.pdf'),prefer_css_page_size=True,print_background=True,display_header_footer=False);print_pdf,print_text=read_pdf(OUT/'large-dataset-print.pdf');assert len(print_pdf.pages)==len(stress_pdf.pages)
   for r in stress_records:assert '#'+r['id'][:8] in print_text
   preview.close();fixture.close()
   return {'source':'explicit UI fixture, not operational statistics','long_label_chars':len(long_label),'long_label_records':2,'long_label_pages':len(long_pdf.pages),'large_records':300,'download_and_print_pages':len(stress_pdf.pages),'CSV_rows':300,'formula_protection':True}
  check('Long labels, CSV escaping/formula protection and 300-record PDF/print page breaks',fixture_exports)
  assert not errors,errors;browser.close()
 assert db_records()==records,'Report exports changed incident data'
 assert protected_hashes=={p:hashlib.sha256((ROOT/'dashboard/src'/p).read_bytes()).hexdigest() for p in protected}
 (OUT/'protected-source-hashes.json').write_text(json.dumps(protected_hashes,indent=2))
 print(json.dumps({'passed':sum(r['status']=='PASS' for r in RESULTS),'failed':sum(r['status']=='FAIL' for r in RESULTS),'SQLite_incidents':len(records),'unchanged':True}),flush=True)
finally:
 for process,log in reversed(processes):
  if process.poll() is None:process.terminate();process.wait(timeout=20)
  log.close()
if any(r['status']=='FAIL' for r in RESULTS):sys.exit(1)
