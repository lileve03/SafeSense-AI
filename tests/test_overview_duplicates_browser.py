"""Read-only verification against current local data; no incident mutations or AI runs."""
from pathlib import Path
import sys,os,json,copy,hashlib,tempfile
from urllib.request import Request,urlopen
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.stdout.reconfigure(encoding='utf-8')
OUT=ROOT/'runtime/overview-task1';OUT.mkdir(parents=True,exist_ok=True)
TOKEN=os.getenv('SAFESENSE_API_TOKEN','local-demo-only')
def live(path):
    with urlopen(Request('http://127.0.0.1:8000'+path,headers={'X-SafeSense-Token':TOKEN}),timeout=5) as response:return json.load(response)
state=live('/state');before=copy.deepcopy(state['incidents'])
unchanged=['dashboard/src/pages/OverviewPage.tsx','dashboard/src/pages/AlertsPage.tsx','dashboard/src/components/incidents/ActiveHistoricalIncidents.tsx']
expected=['24555a4be7f190de52b7a3b3650a1d744988bfdaed0fc7707b4a62be5664976f','90ded8031c6c4fcd094876c9fef6a6128beb2e6be5170d0acdaf6ac9cd914fc7','5a847f8d4647310d55b7b97b85ef489cbe3aabe2176e5d060e1bd9a594c70c7d']
hashes={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in unchanged}
assert list(hashes.values())==expected,'Protected Overview/Alerts source changed'
with tempfile.TemporaryDirectory() as tmp:
    os.environ['SAFESENSE_DB_PATH']=str(Path(tmp)/'test.sqlite3')
    from backend import main
    from fastapi.testclient import TestClient
    main._incidents=copy.deepcopy(list(reversed(before)))
    client=TestClient(main.app,headers={'X-SafeSense-Token':main.TOKEN})
    insights=client.get('/insights').json()
    assert client.get('/incidents').json()==before
    assert main._incidents==list(reversed(before))
    from backend.overview_insights import recorded_identity
    selected=[next(i for i in before if i['id']==r['incident_id']) for r in insights]
    keys=[recorded_identity(i) for i in selected if recorded_identity(i) is not None]
    assert len(keys)==len(set(keys))
    from playwright.sync_api import sync_playwright,expect
    with sync_playwright() as pw:
        browser=pw.chromium.launch(headless=True)
        baseline=browser.new_page(viewport={'width':1500,'height':1050})
        baseline.goto('http://127.0.0.1:3000',wait_until='domcontentloaded')
        expect(baseline.get_by_text('FastAPI Connected',exact=True)).to_be_visible()
        expect(baseline.get_by_role('heading',name='Evidence-based Safety Insights',exact=True)).to_be_visible()
        layout=baseline.locator('main').evaluate('(m)=>Array.from(m.querySelectorAll("div[class*=grid],section")).map(n=>n.className)')
        baseline.screenshot(path=str(OUT/'overview-before.png'),full_page=True)
        baseline.locator('aside').get_by_role('button',name='Alerts',exact=True).click()
        expect(baseline.get_by_label('Incident source',exact=True)).to_be_visible()
        alerts_before=baseline.locator('main').inner_text()
        page=browser.new_page(viewport={'width':1500,'height':1050})
        page.route('**/insights',lambda route:route.fulfill(status=200,content_type='application/json',body=json.dumps(insights)))
        errors=[];page.on('pageerror',lambda error:errors.append(str(error)))
        page.goto('http://127.0.0.1:3000',wait_until='domcontentloaded')
        expect(page.get_by_text('FastAPI Connected',exact=True)).to_be_visible()
        section=page.get_by_role('heading',name='Evidence-based Safety Insights',exact=True).locator('..')
        for row in insights[:4]:expect(section.get_by_text(row['summary'],exact=True)).to_have_count(1)
        assert len(section.locator('p').all_text_contents())==min(4,len(insights))+1
        assert page.locator('main').evaluate('(m)=>Array.from(m.querySelectorAll("div[class*=grid],section")).map(n=>n.className)')==layout
        page.screenshot(path=str(OUT/'overview-after.png'),full_page=True)
        page.locator('aside').get_by_role('button',name='Alerts',exact=True).click()
        expect(page.get_by_label('Incident source',exact=True)).to_be_visible()
        assert page.locator('main').inner_text()==alerts_before,'Alerts content changed'
        page.get_by_label('Incident source',exact=True).select_option('vision')
        expect(page.get_by_label('Incident source',exact=True)).to_have_value('vision')
        page.screenshot(path=str(OUT/'alerts-unchanged.png'),full_page=True)
        assert not errors,errors
        browser.close()
assert live('/state')['incidents']==before,'Read-only verification changed stored incidents'
result={'status':'PASS','active_incidents_before':sum(i['status'] not in ('RESOLVED','FALSE_ALARM') for i in before),
        'unique_insights':len(insights),'protected_source_hashes':hashes,'overview_layout_unchanged':True,
        'alerts_content_unchanged':True,'alerts_filter_works':True,'incident_records_unchanged':True,
        'browser_errors':[],'insight_endpoint':'New backend tested in isolation with existing incident snapshot; browser uses its exact response'}
(OUT/'results.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result,indent=2))
