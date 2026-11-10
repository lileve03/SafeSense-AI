"""Browser playback derivatives only; inference and datasets retain original sources."""
import hashlib
import shutil
import subprocess
from pathlib import Path
from threading import Lock
from uuid import uuid4
from fastapi import HTTPException
from backend.analysis_cache import content_hash,identity_hash

CACHE=Path(__file__).resolve().parents[1]/'runtime'/'playback'
LOCK=Lock()
READY={}

def playback_source(path):
    signature=(str(Path(path).resolve()),Path(path).stat().st_size,Path(path).stat().st_mtime_ns)
    previous=READY.get(signature)
    if previous and previous.is_file():return previous
    key=identity_hash({'source':content_hash(path),'encoding':'h264-pad-faststart-v1'})
    output=CACHE/(key+'.mp4')
    if output.is_file():READY[signature]=output;return output
    ffmpeg=shutil.which('ffmpeg')
    probe=shutil.which('ffprobe')
    options=dict(stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=90,
                 creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    if probe:
        try:
            codec=subprocess.run([probe,'-v','error','-select_streams','v:0','-show_entries',
                'stream=codec_name','-of','default=noprint_wrappers=1:nokey=1',str(path)],check=True,**options).stdout.decode().strip()
            if codec=='h264':READY[signature]=path;return path
        except (OSError,subprocess.SubprocessError):pass
    with LOCK:
        if output.is_file():return output
        if not ffmpeg:raise HTTPException(503,'Browser playback requires FFmpeg for this recording')
        CACHE.mkdir(parents=True,exist_ok=True)
        temporary=CACHE/(key+'-'+str(uuid4())+'.mp4')
        try:
            subprocess.run([ffmpeg,'-nostdin','-v','error','-y','-i',str(path),'-map','0:v:0','-an',
                '-vf','pad=ceil(iw/2)*2:ceil(ih/2)*2','-c:v','libx264','-preset','ultrafast',
                '-pix_fmt','yuv420p','-movflags','+faststart',str(temporary)],check=True,**options)
            temporary.replace(output)
        except (OSError,subprocess.SubprocessError) as exc:
            raise HTTPException(503,'Recording playback conversion failed') from exc
        finally:temporary.unlink(missing_ok=True)
    READY[signature]=output
    while len(READY)>32:READY.pop(next(iter(READY)))
    return output
