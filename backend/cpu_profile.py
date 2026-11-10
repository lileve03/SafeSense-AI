"""Small stage timers and optional process memory telemetry; no inference semantics."""
from contextlib import contextmanager
import time
@contextmanager
def stage(profile,name):
 started=time.perf_counter()
 try:yield
 finally:profile[name]=round(profile.get(name,0)+time.perf_counter()-started,6)
def memory_sample():
 try:
  import psutil
  info=psutil.Process().memory_info()
  return {'rss_mb':round(info.rss/1048576,1),'process_peak_mb':round(getattr(info,'peak_wset',info.rss)/1048576,1),'peak_scope':'process lifetime working set (Windows peak_wset where available)'}
 except ImportError:return {'memory':'psutil unavailable'}
