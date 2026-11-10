"""Isolated uvicorn runner with a local test-only graceful-stop marker, no API added."""
import argparse,os,sys,threading,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import uvicorn
parser=argparse.ArgumentParser();parser.add_argument('--port',type=int,required=True);parser.add_argument('--stop-file',required=True);parser.add_argument('--pid-file',required=True)
args=parser.parse_args();stop=Path(args.stop_file);Path(args.pid_file).write_text(str(os.getpid()))
server=uvicorn.Server(uvicorn.Config('backend.main:app',host='127.0.0.1',port=args.port,log_level='warning'))
def watcher():
    while not stop.exists():time.sleep(.05)
    server.should_exit=True
threading.Thread(target=watcher,daemon=True).start();server.run()
