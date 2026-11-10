"""Run the existing HTTP smoke script against a disposable backend process."""
from pathlib import Path
import subprocess
import sys
import time
from urllib.request import urlopen
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'runtime/test-results'
log=(OUT/'legacy-backend.log').open('w')
p=subprocess.Popen([str(ROOT/'.venv/Scripts/python.exe'),'-m','uvicorn','backend.main:app','--host','127.0.0.1','--port','18002'],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
try:
    for _ in range(120):
        try:
            with urlopen('http://127.0.0.1:18002/health',timeout=1):break
        except OSError:time.sleep(.25)
    result=subprocess.run([sys.executable,'scripts/test_e2e.py','--base','http://127.0.0.1:18002','--reset','--output','runtime/test-results/legacy-api-results.csv'],cwd=ROOT,capture_output=True,text=True)
    (OUT/'legacy-smoke.txt').write_text(result.stdout+result.stderr,encoding='utf-8')
    print(result.stdout)
    if result.stderr:print(result.stderr)
    sys.exit(result.returncode)
finally:
    p.terminate();p.wait(timeout=8);log.close()
