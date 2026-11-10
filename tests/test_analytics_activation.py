
"""Read-only active UI snapshot check; accounts for concurrent incoming incidents."""
from pathlib import Path
from collections import Counter
import json,sqlite3
from playwright.sync_api import sync_playwright,expect
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'runtime/analytics-task5'
with sync_playwright() as pw:
 browser=pw.chromium.launch(headless=True);page=browser.new_page(viewport={'width':1500,'height':1050});errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
 page.goto('http://127.0.0.1:3000')
 with page.expect_response(lambda r:r.url=='http://127.0.0.1:8000/incidents') as pending:
  page.locator('aside').get_by_role('button',name='Analytics',exact=True).click()
 response=pending.value;assert response.status==200;actual=response.json()
 root=page.get_by_test_id('operational-analytics')
 expect(root.get_by_test_id('analytics-kpi-total').locator('[data-value]')).to_have_text(str(len(actual)))
 with sqlite3.connect('file:'+str(ROOT/'runtime/safesense.sqlite3')+'?mode=ro',uri=True) as db:
  stored={row['id']:row for row in (json.loads(result[0]) for result in db.execute("select body from records where kind='incident'"))}
 assert all(row['id'] in stored for row in actual)
 # Compare the precise response snapshot with persisted records for those IDs;
 # newer incident IDs arriving concurrently are allowed and are picked up at refresh.
 snapshots=[stored[row['id']] for row in actual]
 for chart,field in [('severity','level'),('zones','zone_id'),('sources','source'),('modes','processing_mode'),('statuses','status')]:
  expected=dict(Counter(row.get(field) or 'unknown' for row in snapshots))
  displayed=dict(root.get_by_test_id('analytics-'+chart).locator('tbody tr').evaluate_all('(rows)=>rows.map(r=>[r.dataset.key,Number(r.querySelector("td").textContent)])'))
  assert displayed==expected,(chart,displayed,expected)
 assert page.get_by_role('heading',name='Saved Research Evaluations',exact=True).count()==0
 page.screenshot(path=str(OUT/'active-analytics.png'),full_page=True)
 assert not errors,errors
 result={'status':'PASS','active_snapshot_incidents':len(actual),'snapshot_matches_SQLite':True,'evaluation_section_absent':True,'browser_errors':errors,'scope':'Actual backend response and persisted records; read-only, with concurrent new incident IDs permitted'}
 (OUT/'activation.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2));browser.close()
