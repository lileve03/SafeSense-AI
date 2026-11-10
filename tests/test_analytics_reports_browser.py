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
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'runtime/analytics-reports-merge';OUT.mkdir(parents=True,exist_ok=True)
sys.stdout.reconfigure(encoding='utf-8');RESULTS=[]

BASE='http://127.0.0.1:18020';DASH='http://127.0.0.1:3001';TOKEN='analytics-read-only-test'
DB_PATH=OUT/('snapshot-'+str(time.time_ns())+'.sqlite3')
with sqlite3.connect('file:'+str(ROOT/'runtime/safesense.sqlite3')+'?mode=ro',uri=True) as original,sqlite3.connect(DB_PATH) as copied:original.backup(copied)
ENV=os.environ.copy();ENV.update(SAFESENSE_DB_PATH=str(DB_PATH),SAFESENSE_API_TOKEN=TOKEN,VITE_SAFESENSE_API_TOKEN=TOKEN,TELEGRAM_MODE='disabled',VITE_API_BASE_URL=BASE,VITE_AI_BASE_URL='http://127.0.0.1:18021')
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

try:
 start_service('backend',[str(ROOT/'.venv/Scripts/python.exe'),'-m','uvicorn','backend.main:app','--host','127.0.0.1','--port','18020'],ROOT,BASE+'/health')
 start_service('frontend',['node',str(ROOT/'dashboard/node_modules/vite/bin/vite.js'),'--host','127.0.0.1','--port','3001','--strictPort'],ROOT/'dashboard',DASH)
 records=db_records();protected=['pages/OverviewPage.tsx','pages/LiveMonitoringPage.tsx','pages/AlertsPage.tsx','pages/DigitalTwinPage.tsx','components/private-area/PrivateAreaMonitoringView.tsx','components/private-area/PrivateAreaDigitalTwin3D.tsx']
 hashes={p:hashlib.sha256((ROOT/'dashboard/src'/p).read_bytes()).hexdigest() for p in protected}
 def parsed(v):
  try:return datetime.fromisoformat(v.replace('Z','+00:00')).astimezone(timezone.utc)
  except (ValueError,TypeError,AttributeError):return None
 def duration(s):
  if s is None:return 'Not measured'
  if s<60:return f'{s:.1f}s'
  if s<3600:return f'{s/60:.1f} min'
  if s<86400:return f'{s/3600:.1f} hr'
  return f'{s/86400:.1f} days'
 with sync_playwright() as pw:
  browser=pw.chromium.launch(headless=True);page=browser.new_page(viewport={'width':1500,'height':1050});page.set_default_timeout(15000)
  errors=[];evaluations=[];page.on('pageerror',lambda e:errors.append(str(e)));page.on('request',lambda r:evaluations.append(r.url) if '/analytics/evaluations' in r.url else None)
  page.goto(DASH);page.locator('aside').get_by_role('button',name='Analytics & Reports',exact=True).click()
  view=page.get_by_test_id('analytics-reports');expect(view.get_by_test_id('analytics-kpi-total')).to_be_visible()
  def reset():view.get_by_role('button',name='Reset filters',exact=True).click()
  def validate(rows):
   intervals=[(parsed(r['acknowledged_at'])-parsed(r['created_at'])).total_seconds() for r in rows if parsed(r.get('acknowledged_at')) and parsed(r.get('created_at')) and parsed(r['acknowledged_at'])>=parsed(r['created_at'])]
   kpis={'total':len(rows),'high':sum(r['level'] in ('HIGH','CRITICAL') for r in rows),'sos':sum(r.get('source')=='sos_button' or any(e.get('type','').lower()=='sos' for e in r.get('evidence',[])) for r in rows),'pending':sum(r.get('review_status')=='pending_human_review' for r in rows),'resolved':sum(r['status']=='RESOLVED' for r in rows),'ack-time':duration(sum(intervals)/len(intervals) if intervals else None)}
   for key,value in kpis.items():expect(view.get_by_test_id('analytics-kpi-'+key).locator('[data-value]')).to_have_text(str(value))
   if rows:
    counts={key:Counter(r.get(field) or 'unknown' for r in rows) for key,field in [('severity','level'),('zones','zone_id'),('statuses','status'),('modes','processing_mode'),('sources','source')]}
    counts['types']=Counter(t for r in rows for t in (set(e.get('type') for e in r.get('evidence',[]) if e.get('type')) or {'Not recorded'}))
    counts['trend']=Counter(parsed(r['created_at']).date().isoformat() for r in rows if parsed(r.get('created_at')))
    counts['acknowledgements']=Counter('Acknowledged' if parsed(r.get('acknowledged_at')) else 'No acknowledgement recorded' for r in rows)
    for key,value in counts.items():
     actual=dict(view.get_by_test_id('analytics-'+key).locator('tbody tr').evaluate_all('(rs)=>rs.map(r=>[r.dataset.key,Number(r.querySelector("td").textContent)])'))
     assert actual==dict(value),(key,actual,dict(value))
    assert view.get_by_role('table',name='Report incidents',exact=True).locator('tbody tr').count()==len(rows)
    ids=set(view.get_by_label('Report incident',exact=True).locator('option').evaluate_all('(es)=>es.map(e=>e.value)'));assert ids=={r['id'] for r in rows}
   else:assert view.get_by_test_id('incident-report').count()==0
   return kpis
  check('Real SQLite: six KPIs, eight distributions, table and report selector agree',lambda:validate(records))
  def navigation():
   nav=page.locator('aside');expect(nav.get_by_role('button',name='Analytics & Reports',exact=True)).to_have_count(1)
   expect(nav.get_by_role('button',name='Analytics',exact=True)).to_have_count(0);expect(nav.get_by_role('button',name='Reports',exact=True)).to_have_count(0)
   for link in ['/#/analytics','/#/reports','/analytics','/reports','/#/analytics-reports','/analytics-reports']:
    page.goto(DASH+link);expect(view.get_by_test_id('analytics-kpi-total')).to_be_visible();assert page.url.endswith('#/analytics-reports'),page.url
   assert not evaluations
   expect(page.get_by_text('Model evaluation',exact=True)).to_have_count(0)
   for destination in ['Overview','Live Monitoring','Alerts','Digital Twin Map','Analytics & Reports']:
    nav.get_by_role('button',name=destination,exact=True).click();expect(page.locator('main')).to_be_visible()
   validate(records)
   return {'legacy_and_canonical_links':6,'single_navigation':True,'research_requests':len(evaluations),'protected_navigation':True}
  check('Merged navigation, legacy route redirects and protected destinations',navigation)
  def filters():
   seen=[]
   for title,field in [('Zone','zone_id'),('Severity','level'),('Processing mode','processing_mode')]:
    reset();value=next(r[field] for r in records if r.get(field));view.get_by_label('Analytics '+title.lower(),exact=True).select_option(value);seen.append({title:value,**validate([r for r in records if r.get(field)==value])})
   reset();event=next(e['type'] for r in records for e in r.get('evidence',[]) if e.get('type'));view.get_by_label('Analytics event type',exact=True).select_option(event);validate([r for r in records if any(e.get('type')==event for e in r.get('evidence',[]))])
   reset();view.get_by_text('Response & source filters',exact=True).click()
   for title,field in [('Status','status'),('Source','source')]:
    reset();value=next(r[field] for r in records if r.get(field));view.get_by_label('Analytics '+title.lower(),exact=True).select_option(value);validate([r for r in records if r.get(field)==value])
   reset();view.get_by_label('Analytics acknowledgement').select_option('acknowledged');validate([r for r in records if parsed(r.get('acknowledged_at'))])
   reset();r=next(r for r in records if r.get('evidence'));event=r['evidence'][0]['type'];view.get_by_label('Analytics zone',exact=True).select_option(r['zone_id']);view.get_by_label('Analytics severity',exact=True).select_option(r['level']);view.get_by_label('Analytics event type',exact=True).select_option(event)
   validate([x for x in records if x['zone_id']==r['zone_id'] and x['level']==r['level'] and any(e.get('type')==event for e in x.get('evidence',[]))]);reset()
   return {'categorical_filters':7,'combined_filter':True,'examples':seen}
  check('All date-independent filters and their intersection drive every component',filters)
  def dates():
   reset();day=min(parsed(r['created_at']).date().isoformat() for r in records if parsed(r.get('created_at')))
   view.get_by_label('Analytics date range').select_option('custom');view.get_by_label('Analytics from date').fill(day);view.get_by_label('Analytics to date').fill(day);selected=[r for r in records if parsed(r.get('created_at')) and parsed(r['created_at']).date().isoformat()==day];validate(selected)
   view.get_by_label('Analytics from date').fill('2099-01-01');view.get_by_label('Analytics to date').fill('2000-01-01');expect(view.get_by_text('From date must be on or before To date.',exact=True)).to_be_visible();expect(view.get_by_test_id('analytics-kpi-total')).to_have_count(0);expect(view.get_by_test_id('incident-report')).to_have_count(0)
   view.get_by_label('Analytics to date').fill('2099-01-02');validate([]);reset();validate(records)
   return {'inclusive_UTC_day':day,'matching':len(selected),'invalid_and_empty':True}
  check('UTC date ranges, invalid ranges and empty results',dates)
  def responsive():
   reset();assert page.evaluate("getComputedStyle(document.querySelector('[data-testid=analytics-reports] .bg-white')).backgroundColor")=='rgb(16, 30, 52)'
   page.screenshot(path=str(OUT/'combined-desktop.png'),full_page=True)
   page.set_viewport_size({'width':390,'height':844});page.wait_for_timeout(200);assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1');page.screenshot(path=str(OUT/'combined-mobile.png'),full_page=True);page.set_viewport_size({'width':1500,'height':1050})
   return {'dark_surface':True,'mobile_width':390,'no_horizontal_overflow':True}
  check('Dark dashboard styling and responsive layout',responsive)
  root=page.get_by_test_id('incident-report');expect(root).to_be_visible()
  identifier=view.get_by_label('Report incident',exact=True).input_value();report=get('/incidents/'+identifier+'/report')
  def pdf_check():
   with page.expect_download() as d:root.get_by_role('button',name='Download PDF',exact=True).click()
   path=OUT/'selected-report.pdf';d.value.save_as(path)
   pdf=PdfReader(path);text='\n'.join(p.extract_text() for p in pdf.pages);(OUT/'selected-report.txt').write_text(text,encoding='utf-8')
   assert identifier in text
   for term in ['Summary','Evidence','Response','Analysis',report['zone_id'],report['status']]:assert term in text,term
   for p in pdf.pages:
    assert abs(float(p.mediabox.width)-595.28)<1
    assert abs(float(p.mediabox.height)-841.89)<1
    assert len(p.extract_text())>30
    assert len(p.images)==0
   return {'file':str(path),'bytes':path.stat().st_size,'pages':len(pdf.pages),'extractable_characters':len(text),'A4':True}
  check('Download PDF: actual selected report, readable text, A4 pagination',pdf_check)
  def csv_check():
   with page.expect_download() as d:root.get_by_role('button',name='Download CSV',exact=True).click()
   path=OUT/'selected-report.csv';d.value.save_as(path);data=path.read_bytes();assert data.startswith(b'\xef\xbb\xbf')
   rows=list(csv.DictReader(io.StringIO(data.decode('utf-8-sig'))));assert len(rows)==1
   row=rows[0];assert row['incident_id']==identifier and row['zone']==report['zone_id'] and row['status']==report['status']
   assert row['event_type']=='; '.join(e['type'] for e in report['evidence'])
   return {'file':str(path),'bytes':len(data),'records':len(rows),'columns':list(row)}
  check('Download CSV: actual selected incident and UTF-8 columns',csv_check)
  def print_check():
   page.add_init_script("window.print=function(){window.__printed=true}")
   # Patch iframe print before invoking it; Chromium headless has no native preview UI.
   page.evaluate("""() => { const append= document.body.append.bind(document.body);document.body.append=(...nodes)=>{for(const n of nodes)if(n.tagName==='IFRAME'){const original=n.onload;n.onload=()=>{n.contentWindow.print=()=>{n.dataset.printInvoked='true'};original()}}return append(...nodes)}}""")
   root.get_by_role('button',name='Print / Save as PDF',exact=True).click()
   frame=page.locator('iframe[title="Print SafeSense report"]');expect(frame).to_have_attribute('data-print-invoked','true')
   html=frame.evaluate('(f)=>f.contentDocument.documentElement.outerHTML');(OUT/'print-report.html').write_text(html,encoding='utf-8')
   preview=browser.new_page();preview.set_content(html);preview.emulate_media(media='print')
   assert preview.locator('button,nav,aside,video,img').count()==0
   assert preview.locator('h2').all_text_contents()==['Summary','Evidence','Response','Analysis']
   assert identifier in preview.inner_text('body')
   preview.pdf(path=str(OUT/'print-preview.pdf'),prefer_css_page_size=True)
   preview.screenshot(path=str(OUT/'print-preview.png'),full_page=True)
   pdf=PdfReader(OUT/'print-preview.pdf');assert all(abs(float(p.mediabox.width)-595.28)<2 for p in pdf.pages)
   preview.close();frame.evaluate('(f)=>f.remove()')
   return {'browser_print_invoked':True,'preview_pdf':str(OUT/'print-preview.pdf'),'pages':len(pdf.pages),'native_dialog':'Headless browser; print document verified via print media and Chromium PDF'}
  check('Print function and isolated A4 print preview',print_check)
  def security():
   return page.evaluate(r"""async()=>{const m=await import('/src/lib/reportExport.ts');
    const cells=['=1+1',' +SUM(A1)','@evil','-1','\tcmd','normal,comma','quote"text','line\nnext'];
    const escaped=cells.map(m.csvCell);
    if(!escaped.slice(0,5).every(x=>x.startsWith('"\'')))throw Error('formula protection');
    const r={id:'privacy-test',zone_type:'PRIVATE',evidence:[{id:'e',type:'SOS',evidence_reference:'SECRET.mp4',evidence_media:[{url:'SECRET.jpg'}]}]};
    const outputs=[m.reportCsv(r),m.reportPrintHtml(r,'scope','date'),m.reportPdf(r,'scope','date').output()];
    if(outputs.some(x=>x.includes('SECRET')))throw Error('private media leaked');
    const long={...r,history:Array.from({length:100},(_,i)=>({timestamp:'2026-10-29',status:'ACKNOWLEDGED',note:'Pagination verification row '+i+' '+('Long response detail. '.repeat(10))}))};
    const pdf=m.reportPdf(long,'stress','date');if(pdf.getNumberOfPages()<3)throw Error('pagination');
    return {formula_escaping:escaped,private_media_excluded:true,stress_pages:pdf.getNumberOfPages()};}""")
  check('Formula injection, escaping, private media exclusion, long PDF pagination',security)

  def privacy_evidence():
   private=next((r for r in records if r.get('zone_type')!='OPEN_HIDDEN'),None)
   if private:
    view.get_by_label('Report incident',exact=True).select_option(private['id']);expect(root).to_be_visible();root.get_by_role('tab',name='Evidence',exact=True).click();expect(root.get_by_text('Private sensor metadata only. No images, video, or speech are captured.',exact=True)).to_be_visible();assert root.locator('img,video').count()==0
   for tab in ['Summary','Evidence','Response','Analysis']:
    root.get_by_role('tab',name=tab,exact=True).click();expect(root.get_by_role('tabpanel',name=tab)).to_be_visible()
   view.get_by_role('button',name='Collapse report',exact=True).click();expect(root).to_have_count(0);view.get_by_role('button',name='Expand report',exact=True).click();expect(root).to_be_visible()
   return {'private_record_checked':bool(private),'report_sections':4,'collapse_expand':True}
  check('Private evidence restrictions and existing report sections',privacy_evidence)
  def unavailable():
   empty=browser.new_page();empty.route('**/incidents',lambda r:r.fulfill(json=[]));empty.goto(DASH+'/#/reports');expect(empty.get_by_text('No incident records are saved yet.',exact=True)).to_be_visible();assert empty.get_by_test_id('incident-report').count()==0;empty.close()
   failed=browser.new_page();failed.route('**/incidents',lambda r:r.fulfill(status=503,json={'detail':'explicit error fixture'}));failed.goto(DASH+'/#/analytics');expect(failed.get_by_text('No statistics are available until records load.',exact=False)).to_be_visible();assert failed.get_by_test_id('analytics-kpi-total').count()==0;failed.close()
   page.route('**/incidents',lambda r:r.fulfill(status=503,json={'detail':'explicit stale-refresh fixture'}));view.get_by_role('button',name='Refresh records',exact=True).click();expect(view.get_by_text('Showing the last successful snapshot;',exact=False)).to_be_visible();validate(records)
   return {'empty':True,'initial_failure':True,'stale_snapshot_explicit':True}
  check('Empty, unavailable and failed-refresh states',unavailable)
  check('No browser exceptions or research API calls',lambda:{'errors':errors,'research_requests':evaluations} if not errors and not evaluations else (_ for _ in ()).throw(AssertionError((errors,evaluations))))
  browser.close()
 assert db_records()==records,'Read-only checks changed incident data'
 assert hashes=={p:hashlib.sha256((ROOT/'dashboard/src'/p).read_bytes()).hexdigest() for p in protected}
 print(json.dumps({'passed':sum(r['status']=='PASS' for r in RESULTS),'failed':sum(r['status']=='FAIL' for r in RESULTS),'actual_SQLite_incidents':len(records),'database_unchanged':True}),flush=True)
finally:
 for process,log in reversed(processes):
  if process.poll() is None:process.terminate();process.wait(timeout=20)
  log.close()
if any(r['status']=='FAIL' for r in RESULTS):sys.exit(1)
