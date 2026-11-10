"""Bounded durable cache of genuine completed recorded-video analyses.
No video frames are stored here; media and incident records keep their existing lifecycle.
"""
from functools import lru_cache
from pathlib import Path
from threading import RLock
from uuid import uuid4
import gzip,hashlib,json,os,time

HASH_LOCK=RLock()

def _hash_stream(path):
    digest=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b''):digest.update(chunk)
    return digest.hexdigest()

@lru_cache(maxsize=256)
def _content_hash(path,size,mtime,ctime,inode):
    return _hash_stream(path)

def content_hash(path):
    path=Path(path)
    try:
        stat=path.stat()
        with HASH_LOCK:
            # Windows can report the same timestamp for rapid same-size writes.
            # Always rehash recordings, classifiers and code; only memoize large
            # immutable neural checkpoints (128 MB R3D), including file identity.
            if path.suffix.lower() in ('.pt','.pth') and stat.st_size>=16*1024*1024:
                return _content_hash(str(path.resolve()),stat.st_size,stat.st_mtime_ns,stat.st_ctime_ns,stat.st_ino)
            return _hash_stream(path)
    except OSError:return 'missing'


def identity_hash(identity):
    return hashlib.sha256(json.dumps(identity,sort_keys=True,separators=(',',':')).encode()).hexdigest()

class AnalysisCache:
    def __init__(self,directory,entries=32,bytes_limit=256*1024*1024,ttl_days=7):
        self.directory=Path(directory);self.entries=entries;self.bytes_limit=bytes_limit;self.ttl=ttl_days*86400;self.lock=RLock()
    def _path(self,key):
        if len(key)!=64 or any(c not in '0123456789abcdef' for c in key):raise ValueError('Invalid analysis cache key')
        return self.directory/(key+'.json.gz')
    def load(self,key):
        path=self._path(key)
        try:
            if time.time()-path.stat().st_mtime>self.ttl:return None
            with gzip.open(path,'rt',encoding='utf-8') as stream:
                # Bound decompressed input as well as disk use.
                payload=stream.read(48*1024*1024+1)
            if len(payload)>48*1024*1024:return None
            saved=json.loads(payload)
            if saved.get('key')!=key or saved.get('schema')!=1:return None
            row=saved.get('row')
            if not isinstance(row,dict) or row.get('status')!='COMPLETED':return None
            return row
        except (OSError,ValueError,EOFError):return None
    def save(self,key,row):
        self.directory.mkdir(parents=True,exist_ok=True)
        path=self._path(key);temporary=self.directory/(key+'-'+str(uuid4())+'.tmp')
        with self.lock:
            try:
                with gzip.open(temporary,'wt',encoding='utf-8',compresslevel=3) as stream:json.dump({'schema':1,'key':key,'row':row},stream,separators=(',',':'))
                if temporary.stat().st_size>self.bytes_limit:return
                temporary.replace(path)
                files=sorted(self.directory.glob('*.json.gz'),key=lambda p:p.stat().st_mtime,reverse=True);used=0
                for index,old in enumerate(files):
                    size=old.stat().st_size
                    if index>=self.entries or used+size>self.bytes_limit or time.time()-old.stat().st_mtime>self.ttl:old.unlink(missing_ok=True)
                    else:used+=size
            finally:temporary.unlink(missing_ok=True)

class AnalysisGZipMiddleware:
    """Compress pose JSON only. Leave video/range/thumbnail responses untouched."""
    def __init__(self,app):
        from starlette.middleware.gzip import GZipMiddleware
        self.app=app;self.compressed=GZipMiddleware(app,minimum_size=2048,compresslevel=3)
    async def __call__(self,scope,receive,send):
        app=self.compressed if scope.get('type')=='http' and scope.get('path','').startswith('/monitoring/jobs') else self.app
        await app(scope,receive,send)
