"""Opt-in updater for trusted Back Quip GitHub Releases (not arbitrary main branch files)."""
from __future__ import annotations
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
import zipfile
from pathlib import Path
from packaging.version import Version, InvalidVersion

ROOT = Path(__file__).resolve().parent
REPO = 'blarkin13/back-quip'
ALLOWED = {'app.py','launcher.py','updater.py','requirements.txt','start.bat','start.sh',
           'README.md','.gitignore','static/index.html', 'static/assets/back-quip-logo.png'}
MAX_ARCHIVE = 15 * 1024 * 1024

class UpdateError(Exception):
    pass

def check_release(version: str) -> dict:
    request = urllib.request.Request(
        f'https://api.github.com/repos/{REPO}/releases/latest',
        headers={'Accept':'application/vnd.github+json','User-Agent':'BackQuip-UpdateChecker/1.4'})
    try:
        with urllib.request.urlopen(request, timeout=8) as response:
            data=json.load(response)
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return {'available':False,'current':version,'latest':None,'reason':'No GitHub release published yet'}
        raise UpdateError('GitHub release check failed') from exc
    except (OSError,ValueError) as exc:
        raise UpdateError('Could not connect to GitHub to check updates') from exc
    tag=data.get('tag_name','').lstrip('vV')
    try: available=Version(tag)>Version(version)
    except InvalidVersion as exc: raise UpdateError('Latest release has an invalid version') from exc
    assets=data.get('assets',[])
    # Only release assets from the repository are eligible; no arbitrary download URLs.
    asset=next((a for a in assets if re.fullmatch(r'Back-Quip-v\d+\.\d+\.\d+\.zip',a.get('name','')) and
               a['name']==f'Back-Quip-v{tag}.zip'),None)
    if available and (not asset or not asset.get('browser_download_url')):
        return {'available':False,'current':version,'latest':tag,'reason':'New release found, but its install ZIP is missing',
                'release_page':data.get('html_url','')}
    return {'available':available,'current':version,'latest':tag,
            'release_page':data.get('html_url',''),'asset_url':asset['browser_download_url'] if asset else None}

def validate_archive(path:Path) -> None:
    try:
        with zipfile.ZipFile(path) as z:
            files=[x for x in z.infolist() if not x.is_dir()]
            if not files or len(files)>40: raise UpdateError('Release ZIP has an unexpected file list')
            normalized=[]
            for item in files:
                name=item.filename.replace('\\','/')
                if name.startswith('/') or '..' in Path(name).parts:
                    raise UpdateError('Release ZIP has an unsafe path')
                parts=name.split('/')
                if len(parts)>1 and parts[0].lower().startswith('back-quip'):
                    name='/'.join(parts[1:])
                if name not in ALLOWED: raise UpdateError('Unexpected file in release ZIP: '+name)
                if item.file_size>MAX_ARCHIVE: raise UpdateError('Release contains an oversized file')
                normalized.append(name)
            if len(set(normalized))!=len(normalized):raise UpdateError('Duplicate file paths in release')
            if not {'app.py','launcher.py','updater.py','static/index.html'}.issubset(normalized):
                raise UpdateError('Release ZIP is missing required application files')
    except zipfile.BadZipFile as exc:raise UpdateError('Downloaded update is not a valid ZIP file') from exc

def stage_release(release: dict) -> Path:
    url=release.get('asset_url')
    if not url or not url.startswith(f'https://github.com/{REPO}/releases/download/'):
        raise UpdateError('GitHub release archive URL is missing or untrusted')
    path=ROOT/'.backquip-update.zip'
    request=urllib.request.Request(url,headers={'User-Agent':'BackQuip-Updater/1.4'})
    try:
        with urllib.request.urlopen(request,timeout=20) as response, path.open('wb') as out:
            size=0
            while True:
                chunk=response.read(1<<20)
                if not chunk:break
                size+=len(chunk)
                if size>MAX_ARCHIVE:raise UpdateError('Release is too large')
                out.write(chunk)
        validate_archive(path)
        return path
    except (OSError,urllib.error.URLError) as exc:
        path.unlink(missing_ok=True)
        raise UpdateError('Unable to download the release') from exc
    except Exception:
        path.unlink(missing_ok=True)
        raise

def apply_release(path:Path,pid:int) -> None:
    validate_archive(path)
    # Give old server time to exit before replacing Python files.
    for _ in range(50):
        if not _running(pid):break
        time.sleep(.2)
    else:
        raise UpdateError('Old server did not exit; update not installed')
    backup=ROOT/'.backquip-update-backup'
    backup.mkdir(exist_ok=True)
    replacement=ROOT/'.backquip-update-extract'
    if replacement.exists():shutil.rmtree(replacement)
    replacement.mkdir()
    with zipfile.ZipFile(path) as z:
        for item in z.infolist():
            if item.is_dir():continue
            name=item.filename.replace('\\','/')
            parts=name.split('/')
            if len(parts)>1 and parts[0].lower().startswith('back-quip'):
                name='/'.join(parts[1:])
            target=replacement/name
            target.parent.mkdir(parents=True,exist_ok=True)
            with z.open(item) as source,target.open('wb') as dest:shutil.copyfileobj(source,dest)
    copied=[]
    try:
        for name in ALLOWED:
            src=replacement/name
            if not src.exists():continue
            dst=ROOT/name
            if dst.exists():
                b=backup/name;b.parent.mkdir(parents=True,exist_ok=True)
                shutil.copy2(dst,b)
            dst.parent.mkdir(parents=True,exist_ok=True)
            os.replace(src,dst)
            copied.append(name)
    except Exception:
        for name in copied:
            b=backup/name
            if b.exists():shutil.copy2(b,ROOT/name)
        raise
    finally:
        shutil.rmtree(replacement,ignore_errors=True)
        path.unlink(missing_ok=True)
    if sys.platform=='win32':
        command=['cmd','/c',str(ROOT/'start.bat')]
    else:
        command=['bash',str(ROOT/'start.sh')]
    subprocess.Popen(command,cwd=str(ROOT),stdin=subprocess.DEVNULL,
                     stdout=(ROOT/'.backquip-update.log').open('a'),stderr=subprocess.STDOUT,
                     creationflags=getattr(subprocess,'CREATE_NEW_PROCESS_GROUP',0),
                     start_new_session=sys.platform!='win32')

def _running(pid):
    try:os.kill(pid,0);return True
    except OSError:return False

if __name__=='__main__':
    if len(sys.argv)==4 and sys.argv[1]=='apply':
        try:apply_release(Path(sys.argv[2]),int(sys.argv[3]))
        except Exception as exc:
            (ROOT/'.backquip-update.log').open('a').write(f'Update failed: {exc}\n')
            sys.exit(1)
    else:sys.exit('Usage: updater.py apply ARCHIVE PID')
