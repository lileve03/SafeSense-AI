"""Isolated browser smoke test: original WebGL room and acquisition mode guards."""
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import tempfile
import time
import httpx
from playwright.sync_api import sync_playwright, expect

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'runtime/hardware-prototype-checks'
OUT.mkdir(parents=True,exist_ok=True)
processes=[]
with tempfile.TemporaryDirectory() as temp:
    env={**os.environ,'SAFESENSE_DB_PATH':str(Path(temp)/'browser.sqlite3'),'TELEGRAM_MODE':'disabled',
         'TELEGRAM_STAFF_DISPATCH_ENABLED':'false','SAFESENSE_API_TOKEN':'hardware-browser-test',
         'VITE_SAFESENSE_API_TOKEN':'hardware-browser-test','VITE_API_BASE_URL':'http://127.0.0.1:18830',
         'VITE_AI_BASE_URL':'http://127.0.0.1:18832'}
    try:
        for port in (18830,3001):
            with socket.socket() as probe:probe.bind(('127.0.0.1',port))
        commands=[('backend',[str(ROOT/'.venv/Scripts/python.exe'),'-m','uvicorn','backend.main:app','--host','127.0.0.1','--port','18830'],ROOT,'http://127.0.0.1:18830/health'),
                  ('frontend',[shutil.which('node'),str(ROOT/'dashboard/node_modules/vite/bin/vite.js'),'--host','127.0.0.1','--port','3001','--strictPort'],ROOT/'dashboard','http://127.0.0.1:3001')]
        for name,cmd,cwd,url in commands:
            log=(OUT/(name+'.log')).open('w',encoding='utf-8')
            proc=subprocess.Popen(cmd,cwd=cwd,env=env,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
            processes.append((proc,log))
            for _ in range(100):
                if proc.poll() is not None:raise RuntimeError(name+' exited')
                try:
                    if httpx.get(url,timeout=1).status_code==200:break
                except httpx.HTTPError:pass
                time.sleep(.2)
            else:raise RuntimeError(name+' startup timed out')
        with sync_playwright() as pw:
            browser=pw.chromium.launch(headless=True,args=['--enable-unsafe-swiftshader'])
            page=browser.new_page(viewport={'width':1600,'height':1100})
            errors=[]
            page.on('pageerror',lambda error:errors.append(str(error)))
            page.goto('http://127.0.0.1:3001')
            page.locator('aside').get_by_role('button',name='Digital Twin Map',exact=True).click()
            page.locator('[data-zone-id="ZONE_TOILET_BLINDSPOT"] polygon').first.click()
            page.get_by_role('button',name='Advanced Monitoring',exact=True).click()
            panel=page.get_by_test_id('normalized-sensor-panel')
            scene=page.get_by_test_id('private-twin-scene')
            expect(panel).to_be_visible()
            expect(scene.locator('canvas')).to_be_visible()
            expect(scene).to_have_attribute('data-positioned-occupants','0')
            expect(panel).to_contain_text('Hardware Disconnected')
            panel.get_by_role('combobox',name='Source mode').select_option('LIVE_HARDWARE')
            expect(scene).to_have_attribute('data-processing-mode','LIVE_HARDWARE')
            expect(scene).to_have_attribute('data-positioned-occupants','0')
            expect(panel).to_contain_text('No observation available')
            panel.get_by_role('combobox',name='Source mode').select_option('SIMULATION')
            panel.get_by_role('button',name='Submit simulated fall + scream observation').click()
            expect(panel).to_contain_text('simulated-radar-acoustic')
            expect(panel).to_contain_text('VALID')
            panel.get_by_role('combobox',name='Source mode').select_option('RECORDED_REPLAY')
            expect(scene).to_have_attribute('data-positioned-occupants','0')
            expect(scene).to_have_attribute('data-tracking-preview','off')
            assert not errors,errors
            scene.screenshot(path=str(OUT/'original-room.png'))
            browser.close()
        (OUT/'browser-results.json').write_text(json.dumps({'status':'PASS','checks':['original WebGL room retained','recorded empty view has no fabricated people','hardware disconnected with zero positioned occupants','simulation shared-interface submission','mode switch clears simulation tracks','no browser runtime errors']},indent=2))
        print('PASS: 6 browser checks')
    finally:
        for proc,log in reversed(processes):
            proc.terminate()
            try:proc.wait(timeout=8)
            except subprocess.TimeoutExpired:proc.kill();proc.wait()
            log.close()
