
"""Read-only isolated Analytics checks against an actual SQLite snapshot; expectations independently derived from SQLite.
Empty/error API fixtures exercise UI branches only and are labeled explicitly.
"""
from pathlib import Path
from collections import Counter
from datetime import datetime,timezone
from urllib.request import Request,urlopen
import json,sqlite3,hashlib,sys,time,traceback,os,subprocess
from playwright.sync_api import sync_playwright,expect
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'runtime/analytics-task5';OUT.mkdir(parents=True,exist_ok=True)
sys.stdout.reconfigure(encoding='utf-8');RESULTS=[]

BASE='http://127.0.0.1:18000';DASH='http://127.0.0.1:3001';TOKEN='analytics-read-only-test'
DB_PATH=OUT/('snapshot-'+str(time.time_ns())+'.sqlite3')
with sqlite3.connect('file:'+str(ROOT/'runtime/safesense.sqlite3')+'?mode=ro',uri=True) as original,sqlite3.connect(DB_PATH) as copied:original.backup(copied)
ENV=os.environ.copy();ENV.update(SAFESENSE_DB_PATH=str(DB_PATH),SAFESENSE_API_TOKEN=TOKEN,VITE_SAFESENSE_API_TOKEN=TOKEN,TELEGRAM_MODE='disabled',VITE_API_BASE_URL=BASE,VITE_AI_BASE_URL='http://127.0.0.1:18001')
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
 start_service('backend',[str(ROOT/'.venv/Scripts/python.exe'),'-m','uvicorn','backend.main:app','--host','127.0.0.1','--port','18000'],ROOT,BASE+'/health')
 start_service('frontend',['node',str(ROOT/'dashboard/node_modules/vite/bin/vite.js'),'--host','127.0.0.1','--port','3001','--strictPort'],ROOT/'dashboard',DASH)
 records=db_records();api_records=get('/incidents');assert {r['id'] for r in records}=={r['id'] for r in api_records}
 assert len(records)==len(api_records)
 protected=['dashboard/src/pages/OverviewPage.tsx','dashboard/src/pages/AlertsPage.tsx','dashboard/src/components/incidents/ActiveHistoricalIncidents.tsx','dashboard/src/components/private-area/PrivateAreaMonitoringView.tsx','dashboard/src/components/private-area/PrivateAreaDigitalTwin3D.tsx','yolo11n-pose.pt','evaluation/outputs/fight_multiclip_v2/fight_multiclip_classifier.joblib','evaluation/outputs/fight_v3/fight_v3_classifier.joblib','evaluation/outputs/fight_v3/reserved_comparison/comparison.csv','dashboard/src/components/analysis/ResearchMetrics.tsx']
 hashes={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in protected}
 assert hashes[protected[0]]=='24555a4be7f190de52b7a3b3650a1d744988bfdaed0fc7707b4a62be5664976f'
 assert hashes[protected[1]]=='90ded8031c6c4fcd094876c9fef6a6128beb2e6be5170d0acdaf6ac9cd914fc7'
 def parsed(value):
  try:return datetime.fromisoformat(value.replace('Z','+00:00'))
  except (ValueError,TypeError,AttributeError):return None
 def expected(rows):
  result={name:Counter(r.get(field) or 'unknown' for r in rows) for name,field in [('severity','level'),('zones','zone_id'),('sources','source'),('modes','processing_mode'),('statuses','status')]}
  result['acknowledgements']=Counter('Acknowledged' if parsed(r.get('acknowledged_at')) else 'No acknowledgement recorded' for r in rows)
  result['types']=Counter(t for r in rows for t in (set(e.get('type') for e in r.get('evidence',[]) if e.get('type')) or {'Not recorded'}))
  result['trend']=Counter(parsed(r['created_at']).astimezone(timezone.utc).date().isoformat() for r in rows if parsed(r.get('created_at')))
  return result
 def duration_label(seconds):
  if seconds is None:return 'Not measured'
  if seconds<60:return f'{seconds:.1f}s'
  if seconds<3600:return f'{seconds/60:.1f} min'
  if seconds<86400:return f'{seconds/3600:.1f} hr'
  return f'{seconds/86400:.1f} days'
 with sync_playwright() as pw:
  browser=pw.chromium.launch(headless=True);page=browser.new_page(viewport={'width':1500,'height':1050});page.set_default_timeout(15000)
  errors=[];evaluations=[];page.on('pageerror',lambda e:errors.append(str(e)));page.on('request',lambda r:evaluations.append(r.url) if '/analytics/evaluations' in r.url else None)
  page.goto(DASH);page.locator('aside').get_by_role('button',name='Analytics',exact=True).click()
  root=page.get_by_test_id('operational-analytics');expect(root.get_by_test_id('analytics-kpi-total')).to_be_visible()
  def kpi(key):return root.get_by_test_id('analytics-kpi-'+key).locator('[data-value]').inner_text()
  def validate(rows):
   expect(root.get_by_test_id('analytics-kpi-total').locator('[data-value]')).to_have_text(str(len(rows)))
   for chart,counts in expected(rows).items():
    actual=dict(root.get_by_test_id('analytics-'+chart).locator('tbody tr').evaluate_all('(rows)=>rows.map(r=>[r.dataset.key,Number(r.querySelector("td").textContent)])'))
    assert actual==dict(counts),(chart,actual,dict(counts))
   return {'selected':len(rows),'chart_totals':{key:sum(value.values()) for key,value in expected(rows).items()}}
  def reset():root.get_by_role('button',name='Reset filters',exact=True).click()
  def initial():
   result=validate(records)
   assert not evaluations,'Operational page must not request research evaluations'
   expect(page.get_by_role('heading',name='Saved Research Evaluations',exact=True)).to_have_count(0)
   assert root.locator('.recharts-wrapper').count()==8
   open_rows=[r for r in records if r['status'] not in ('RESOLVED','FALSE_ALARM')]
   assert int(kpi('open'))==len(open_rows)
   acknowledged=[r for r in records if parsed(r.get('acknowledged_at'))]
   assert int(kpi('acknowledged'))==len(acknowledged)
   ack_seconds=[(parsed(r['acknowledged_at'])-parsed(r['created_at'])).total_seconds() for r in acknowledged if parsed(r.get('created_at')) and parsed(r['acknowledged_at'])>=parsed(r['created_at'])]
   assert kpi('ack-time')==duration_label(sum(ack_seconds)/len(ack_seconds) if ack_seconds else None)
   closed=[r for r in records if r['status'] in ('RESOLVED','FALSE_ALARM')]
   false=sum(r['status']=='FALSE_ALARM' for r in closed)
   assert kpi('false-alarm-rate')==(f'{false/len(closed)*100:.1f}%' if closed else 'Not measured')
   return {**result,'mean_ack':kpi('ack-time'),'no_evaluation_request':True,'charts':8}
  check('Operational page has no evaluation panel; all metrics and eight charts match SQLite',initial)
  def filters():
   actual=[]
   for label,field in [('processing mode','processing_mode'),('source','source'),('zone','zone_id'),('severity','level'),('status','status')]:
    reset();value=next(r[field] for r in records if r.get(field));root.get_by_label('Analytics '+label,exact=True).select_option(value)
    actual.append({'filter':label,'value':value,**validate([r for r in records if r.get(field)==value])})
   reset();root.get_by_label('Analytics acknowledgement',exact=True).select_option('acknowledged');validate([r for r in records if parsed(r.get('acknowledged_at'))])
   reset();target=next(r for r in records if r['processing_mode']=='recorded_sensor_replay');root.get_by_label('Analytics processing mode',exact=True).select_option(target['processing_mode']);root.get_by_label('Analytics source',exact=True).select_option(target['source']);root.get_by_label('Analytics zone',exact=True).select_option(target['zone_id']);validate([r for r in records if r['processing_mode']==target['processing_mode'] and r['source']==target['source'] and r['zone_id']==target['zone_id']])
   reset();validate(records);return actual
  check('All categorical and combined filters update every chart from the same subset',filters)
  def date_filters():
   day=min(parsed(r['created_at']).astimezone(timezone.utc).date().isoformat() for r in records)
   root.get_by_label('Analytics date range',exact=True).select_option('custom');root.get_by_label('Analytics from date',exact=True).fill(day);root.get_by_label('Analytics to date',exact=True).fill(day)
   result=validate([r for r in records if parsed(r['created_at']).astimezone(timezone.utc).date().isoformat()==day])
   root.get_by_label('Analytics from date',exact=True).fill('2099-01-01');root.get_by_label('Analytics to date',exact=True).fill('2000-01-01')
   expect(root.get_by_text('From date must be on or before To date.',exact=True)).to_be_visible();expect(root.get_by_test_id('analytics-kpi-total')).to_have_count(0)
   root.get_by_label('Analytics to date',exact=True).fill('2099-01-02');validate([])
   expect(root.get_by_text('No incidents match the selected filters.',exact=False)).to_be_visible();assert kpi('ack-time')=='Not measured'
   reset();validate(records);return {'inclusive_UTC_day':day,**result,'invalid_range_handled':True,'empty_filter_handled':True}
  check('Date filters, invalid ranges and empty selection do not show stale statistics',date_filters)
  def interaction():
   chart=root.get_by_test_id('analytics-severity');chart.locator('.recharts-bar-rectangle path').first.hover()
   expect(chart.locator('.recharts-tooltip-wrapper').first).to_be_visible()
   chart.get_by_text('View counts',exact=True).click();expect(chart.get_by_role('table')).to_be_visible()
   page.screenshot(path=str(OUT/'analytics-desktop.png'),full_page=True)
   page.set_viewport_size({'width':390,'height':844});page.wait_for_timeout(250)
   assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
   page.screenshot(path=str(OUT/'analytics-mobile.png'),full_page=True);page.set_viewport_size({'width':1500,'height':1050})
   return {'hover_tooltip':True,'accessible_counts':True,'mobile_no_overflow':True}
  check('Charts render, tooltip/count interaction works, layout stays responsive',interaction)
  def mode_independence():
   toggle=page.get_by_role('button',name=__import__('re').compile('Mode: Backend Events'))
   if toggle.count():
    toggle.click();validate(records);page.get_by_role('button',name=__import__('re').compile('Mode: Simulated Demo')).click()
   return 'Analytics uses persisted records, independent of dashboard demonstration data'
  check('Global demo mode does not substitute invented analytics',mode_independence)
  def preserved_research():
   page.locator('aside').get_by_role('button',name='Reports',exact=True).click();page.get_by_role('button',name='Model evaluation',exact=True).click()
   expect(page.get_by_role('heading',name='Saved Research Evaluations',exact=True)).to_be_visible();expect(page.get_by_text('0.9167',exact=True)).to_be_visible()
   return 'Saved evaluation files/API and Reports > Model evaluation remain available'
  check('Research evaluations retained outside operational Analytics',preserved_research)
  def fixtures():
   empty=browser.new_page();empty.route('**/incidents',lambda route:route.fulfill(json=[]));empty.goto(DASH);empty.locator('aside').get_by_role('button',name='Analytics',exact=True).click()
   expect(empty.get_by_text('No incident records are saved yet.',exact=False)).to_be_visible();assert empty.locator('[data-testid=operational-analytics] .recharts-wrapper').count()==0;empty.close()
   failed=browser.new_page();failed.route('**/incidents',lambda route:route.fulfill(status=503,json={'detail':'Explicit UI error test fixture'}));failed.goto(DASH);failed.locator('aside').get_by_role('button',name='Analytics',exact=True).click()
   expect(failed.get_by_text('No statistics are available until records load.',exact=False)).to_be_visible();expect(failed.get_by_test_id('analytics-kpi-total')).to_have_count(0);failed.close()
   page.locator('aside').get_by_role('button',name='Analytics',exact=True).click();validate(records)
   page.route('**/incidents',lambda route:route.fulfill(status=503,json={'detail':'Explicit stale-snapshot UI test fixture'}));root.get_by_role('button',name='Refresh records',exact=True).click()
   expect(root.get_by_text('Showing the last successful snapshot;',exact=False)).to_be_visible();validate(records)
   return 'Explicit empty/error UI metadata fixtures: no invented zero stats on API failure; last actual snapshot marked stale'
  check('No-record, failed-load and failed-refresh states are explicit',fixtures)
  assert not errors,errors
  browser.close()
 assert db_records()==records,'Read-only Analytics tests changed incident records'
 assert hashes=={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in protected}
 (OUT/'protected-hashes.json').write_text(json.dumps(hashes,indent=2))
 print(json.dumps({'passed':sum(r['status']=='PASS' for r in RESULTS),'failed':sum(r['status']=='FAIL' for r in RESULTS),'actual_SQLite_incidents':len(records),'database_unchanged':True}),flush=True)
 sys.exit(any(r['status']=='FAIL' for r in RESULTS))
finally:
 for process,log in reversed(processes):
  if process.poll() is None:
   process.terminate()
   try:process.wait(timeout=8)
   except subprocess.TimeoutExpired:process.kill()
  log.close()
