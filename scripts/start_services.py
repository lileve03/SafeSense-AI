"""Local demo supervisor. All three servers bind loopback; Ctrl+C stops only its children."""
from pathlib import Path
from urllib.request import urlopen
import os
import shutil
import socket
import subprocess
import sys
import time
import secrets

ROOT=Path(__file__).resolve().parents[1]

def load_local_environment(path=None):
    path=Path(path) if path is not None else ROOT/'.env'
    if path.is_file():
        for raw in path.read_text(encoding='utf-8-sig').splitlines():
            line=raw.strip()
            if line and not line.startswith('#') and '=' in line:
                key,value=line.split('=',1)
                key=key.strip()
                if key.startswith(('SAFESENSE_','TELEGRAM_')):
                    os.environ.setdefault(key,value.strip().strip('\"').strip("'"))
    # A generic Chat ID is a TEST-only compatibility alias, never a staff fallback.
    if os.getenv('TELEGRAM_MODE')=='test' and not os.getenv('TELEGRAM_TEST_CHAT_ID') and os.getenv('TELEGRAM_CHAT_ID'):
        os.environ['TELEGRAM_TEST_CHAT_ID']=os.environ['TELEGRAM_CHAT_ID']

def service_environment(name, environment):
    return {key:value for key,value in environment.items() if not key.startswith('TELEGRAM_') and key!='SAFESENSE_INGEST_TOKEN'} if name=='dashboard' else environment.copy()


def main():
    load_local_environment()
    backend_port=int(os.getenv('SAFESENSE_BACKEND_PORT','8000'))
    ai_port=int(os.getenv('SAFESENSE_AI_PORT','8001'))
    dashboard_port=int(os.getenv('SAFESENSE_DASHBOARD_PORT','3000'))
    for port in (backend_port,ai_port,dashboard_port):
        with socket.socket() as sock:
            try: sock.bind(('127.0.0.1',port))
            except OSError: raise SystemExit(f'Port {port} already in use. Existing process was not stopped.')
    backend=ROOT/'.venv/Scripts/python.exe'
    vision=ROOT/'.venv-vision/Scripts/python.exe'
    node=shutil.which('node')
    vite=ROOT/'dashboard/node_modules/vite/bin/vite.js'
    for path in (backend,vision,vite):
        if not path.is_file():raise SystemExit(f'Missing {path}; follow README setup')
    if not node:raise SystemExit('Node.js is unavailable')
    logs=ROOT/'runtime/logs';logs.mkdir(parents=True,exist_ok=True)
    commands=[('backend',[str(backend),'-m','uvicorn','backend.main:app','--host','127.0.0.1','--port',str(backend_port)],ROOT,f'http://127.0.0.1:{backend_port}/health'),
              ('inference',[str(vision),'-m','uvicorn','fight_api:app','--host','127.0.0.1','--port',str(ai_port)],ROOT,f'http://127.0.0.1:{ai_port}/health'),
              ('dashboard',[node,str(vite),'--host','127.0.0.1','--port',str(dashboard_port),'--strictPort'],ROOT/'dashboard',f'http://127.0.0.1:{dashboard_port}')]
    processes=[]
    env=os.environ.copy()
    # Keep both services and Vite on the same explicit local demo token.
    env.setdefault('SAFESENSE_API_TOKEN','local-demo-only')
    if not env.get('SAFESENSE_INGEST_TOKEN'):env['SAFESENSE_INGEST_TOKEN']=secrets.token_urlsafe(32)
    env['VITE_SAFESENSE_API_TOKEN']=env['SAFESENSE_API_TOKEN']
    env.setdefault('SAFESENSE_BACKEND_URL',f'http://127.0.0.1:{backend_port}')
    env.setdefault('SAFESENSE_AI_URL',f'http://127.0.0.1:{ai_port}')
    env.setdefault('VITE_API_BASE_URL',f'http://127.0.0.1:{backend_port}')
    env.setdefault('VITE_AI_BASE_URL',f'http://127.0.0.1:{ai_port}')
    try:
        for name,cmd,cwd,url in commands:
            log=(logs/(name+'.log')).open('w',encoding='utf-8')
            child_env=service_environment(name,env)
            process=subprocess.Popen(cmd,cwd=cwd,env=child_env,stdout=log,stderr=subprocess.STDOUT,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            processes.append((process,log))
            deadline=time.monotonic()+60
            while time.monotonic()<deadline:
                if process.poll() is not None:raise RuntimeError(f'{name} exited; inspect runtime/logs/{name}.log')
                try:
                    with urlopen(url,timeout=1) as response:
                        if response.status==200:break
                except OSError:time.sleep(.3)
            else:raise RuntimeError(f'{name} startup timeout; inspect its log')
            print(f'{name} ready: {url} (PID {process.pid})',flush=True)
        print(f'SafeSense: http://127.0.0.1:{dashboard_port} | Ctrl+C stops this demo. Production dispatch disabled.',flush=True)
        if '--smoke-test' in sys.argv:return
        while True:
            for process,_ in processes:
                if process.poll() is not None:raise RuntimeError('A service stopped; inspect runtime/logs')
            time.sleep(1)
    except KeyboardInterrupt:
        print('Stopping demo services...',flush=True)
    finally:
        for process,log in reversed(processes):
            process.terminate()
            try:process.wait(timeout=8)
            except subprocess.TimeoutExpired:process.kill()
            log.close()

if __name__=='__main__': main()
