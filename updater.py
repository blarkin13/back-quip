"""Opt-in updater for trusted Back Quip GitHub Releases (not arbitrary main branch files)."""
from __future__ import annotations
import hashlib
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
ALLOWED = {'source_fetch.py','app.py','launcher.py','updater.py','requirements.txt','start.bat','start.sh',
           'README.md','.gitignore','static/index.html', 'static/assets/back-quip-logo.png'}
MAX_ARCHIVE = 15 * 1024 * 1024
SETTINGS_PATH = ROOT / '.backquip-settings.json'
CHANNELS = ('development', 'stable')
REQUIRED = {'app.py','source_fetch.py','launcher.py','updater.py','static/index.html'}
TEXT_FILES = ALLOWED - {'static/assets/back-quip-logo.png'}

class UpdateError(Exception):
    pass


def get_channel() -> str:
    """Persistent, machine-local choice; Development is default until releases are used."""
    try:
        saved = json.loads(SETTINGS_PATH.read_text(encoding='utf-8'))
        if saved.get('channel') in CHANNELS:
            return saved['channel']
    except (OSError, ValueError, AttributeError):
        pass
    return 'development'

def set_channel(channel: str) -> str:
    if channel not in CHANNELS:
        raise UpdateError('Choose Development or Stable.')
    temp = SETTINGS_PATH.with_suffix('.tmp')
    temp.write_text(json.dumps({'channel': channel}, indent=2) + '\n', encoding='utf-8')
    os.replace(temp, SETTINGS_PATH)
    return channel

def _github_json(endpoint: str) -> dict:
    if not endpoint.startswith(f'https://api.github.com/repos/{REPO}/'):
        raise UpdateError('Unexpected update source')
    request = urllib.request.Request(endpoint, headers={
        'Accept': 'application/vnd.github+json',
        'User-Agent': 'BackQuip-UpdateChecker/1.7',
        'X-GitHub-Api-Version': '2022-11-28',
    })
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return json.load(response)
    except (OSError, ValueError, urllib.error.HTTPError) as exc:
        raise UpdateError('Could not check GitHub main for changes') from exc

def git_blob_hash(raw: bytes) -> str:
    """Git blob digest, independent of timestamps and ZIP packaging."""
    return hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()

def local_blob_hash(name: str) -> str | None:
    path = ROOT / name
    if not path.is_file():
        return None
    raw = path.read_bytes()
    # Windows git checkouts commonly use CRLF for source files.
    if name in TEXT_FILES:
        raw = raw.replace(b'\r\n', b'\n')
    return git_blob_hash(raw)

def check_development(version: str) -> dict:
    commit = _github_json(f'https://api.github.com/repos/{REPO}/commits/main')
    sha = commit.get('sha', '')
    tree_sha = (commit.get('commit') or {}).get('tree', {}).get('sha', '')
    if not re.fullmatch(r'[0-9a-f]{40}', sha) or not re.fullmatch(r'[0-9a-f]{40}', tree_sha):
        raise UpdateError('GitHub returned an invalid main-branch commit')
    tree = _github_json(f'https://api.github.com/repos/{REPO}/git/trees/{tree_sha}?recursive=1')
    if tree.get('truncated'):
        raise UpdateError('GitHub returned an incomplete file list')
    remote = {e['path']: e['sha'] for e in tree.get('tree', [])
              if e.get('type') == 'blob' and e.get('path') in ALLOWED
              and re.fullmatch(r'[0-9a-f]{40}', e.get('sha', ''))}
    missing = sorted(REQUIRED - remote.keys())
    if missing:
        raise UpdateError('Main is missing required Back Quip files: ' + ', '.join(missing))
    changed = sorted(name for name, digest in remote.items() if local_blob_hash(name) != digest)
    removed = sorted(name for name in ALLOWED if name not in remote and (ROOT / name).is_file())
    return {
        'channel': 'development', 'available': bool(changed or removed),
        'current': version, 'latest': sha[:8], 'commit_sha': sha,
        'changed_files': changed + removed, 'removed_files': removed,
        'file_hashes': remote,
        'release_page': f'https://github.com/{REPO}/commit/{sha}',
        'reason': 'Local files match the latest main branch' if not changed and not removed else '',
    }

def check_update(version: str, channel: str | None = None) -> dict:
    channel = channel or get_channel()
    if channel == 'development':
        return check_development(version)
    if channel == 'stable':
        return {'channel': 'stable', **check_release(version)}
    raise UpdateError('Unknown update channel')

def _entries(archive: Path, *, development: bool):
    """Select only whitelisted application files; reject unsafe zip members."""
    with zipfile.ZipFile(archive) as z:
        files = [i for i in z.infolist() if not i.is_dir()]
        if len(files) > 500 or not files:
            raise UpdateError('Update archive has an unexpected file count')
        result = {}
        for info in files:
            name = info.filename
            if ('\\' in name or name.startswith('/') or '\0' in name or
                '..' in name.split('/') or ':' in name.split('/')[0]):
                raise UpdateError('Unsafe path in update archive')
            if info.external_attr >> 16 & 0o170000 == 0o120000:
                raise UpdateError('Update archive contains a symbolic link')
            parts = name.split('/')
            if development:
                if len(parts) < 2 or not parts[0].lower().startswith('blarkin13-back-quip-'):
                    raise UpdateError('Unexpected GitHub source archive layout')
                name = '/'.join(parts[1:])
            elif len(parts)>1 and parts[0].lower().startswith('back-quip'):
                name = '/'.join(parts[1:])
            if name not in ALLOWED:
                if development: continue
                raise UpdateError('Unexpected file in release ZIP: ' + name)
            if info.file_size > MAX_ARCHIVE:
                raise UpdateError('Oversized application file in ZIP')
            if name in result:
                raise UpdateError('Duplicate file in update: '+name)
            result[name] = (info, z.read(info))
        if not REQUIRED.issubset(result):
            raise UpdateError('Update is missing required application files')
        return {name: raw for name, (_, raw) in result.items()}

def stage_development(update: dict) -> Path:
    sha = update.get('commit_sha', '')
    if not re.fullmatch(r'[0-9a-f]{40}', sha):
        raise UpdateError('Invalid GitHub commit')
    url = f'https://api.github.com/repos/{REPO}/zipball/{sha}'
    path = ROOT / '.backquip-update.zip'
    request = urllib.request.Request(url, headers={'User-Agent':'BackQuip-Updater/1.7',
                                                   'Accept':'application/vnd.github+json'})
    try:
        with urllib.request.urlopen(request, timeout=25) as response, path.open('wb') as dest:
            size = 0
            while chunk := response.read(1 << 20):
                size += len(chunk)
                if size > MAX_ARCHIVE:
                    raise UpdateError('GitHub source archive is too large')
                dest.write(chunk)
        files = _entries(path, development=True)
        expected = update.get('file_hashes', {})
        for name, digest in expected.items():
            if name not in files:
                raise UpdateError(f'Archive is missing expected file: {name}')
            raw = files[name].replace(b'\r\n', b'\n') if name in TEXT_FILES else files[name]
            if git_blob_hash(raw) != digest:
                raise UpdateError(f'Checksum mismatch for {name}')
        return path
    except (OSError, urllib.error.URLError, zipfile.BadZipFile) as exc:
        path.unlink(missing_ok=True)
        raise UpdateError('Unable to download or verify GitHub main') from exc
    except Exception:
        path.unlink(missing_ok=True)
        raise

def stage_update(update: dict) -> Path:
    return stage_development(update) if update.get('channel') == 'development' else stage_release(update)

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
            if not {'app.py','source_fetch.py','launcher.py','updater.py','static/index.html'}.issubset(normalized):
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

def apply_release(path: Path, pid: int, channel: str = 'stable') -> None:
    """Apply a previously staged update after the server has exited."""
    if channel not in CHANNELS:
        raise UpdateError('Invalid update channel')
    if channel == 'stable':
        validate_archive(path)
    selected = _entries(path, development=(channel == 'development'))
    if pid > 0:
        for _ in range(100):
            if not _running(pid): break
            time.sleep(.15)
        else:
            raise UpdateError('Old server did not exit; update not installed')
    backup = ROOT / '.backquip-update-backup'
    backup.mkdir(exist_ok=True)
    replacement = ROOT / '.backquip-update-extract'
    if replacement.exists(): shutil.rmtree(replacement)
    replacement.mkdir()
    for name, raw in selected.items():
        target = replacement / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
    copied = []
    removed = []
    try:
        # In Development, mirror removals of optional managed files as well.
        # Required files have already been validated by _entries.
        if channel == 'development':
            for name in sorted(ALLOWED - selected.keys() - REQUIRED):
                dst = ROOT / name
                if dst.exists() and dst.is_file():
                    backup_file = backup / name
                    backup_file.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(dst, backup_file)
                    dst.unlink()
                    removed.append(name)
        for name in sorted(selected):
            src = replacement / name
            dst = ROOT / name
            if dst.exists():
                b = backup / name
                b.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(dst, b)
            dst.parent.mkdir(parents=True, exist_ok=True)
            os.replace(src, dst)
            copied.append(name)
    except Exception:
        for name in copied + removed:
            b = backup / name
            if b.exists():
                (ROOT / name).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(b, ROOT / name)
        raise
    finally:
        shutil.rmtree(replacement, ignore_errors=True)
        path.unlink(missing_ok=True)
    # Local settings, models, .git, and virtualenv are never replaced.
    command = ['cmd','/c',str(ROOT/'start.bat')] if sys.platform == 'win32' else ['bash',str(ROOT/'start.sh')]
    env = dict(os.environ, BACKQUIP_SKIP_STARTUP_UPDATE='1')
    with (ROOT / '.backquip-update.log').open('a') as log:
        subprocess.Popen(command, cwd=str(ROOT), env=env, stdin=subprocess.DEVNULL,
                         stdout=log, stderr=subprocess.STDOUT,
                         creationflags=getattr(subprocess,'CREATE_NEW_PROCESS_GROUP',0),
                         start_new_session=sys.platform != 'win32')

def restart_after_exit(pid: int) -> None:
    if pid <= 0: raise UpdateError('Invalid restart PID')
    for _ in range(100):
        if not _running(pid): break
        time.sleep(.15)
    else:
        raise UpdateError('Previous server did not exit')
    command=['cmd','/c',str(ROOT/'start.bat')] if sys.platform=='win32' else ['bash',str(ROOT/'start.sh')]
    with (ROOT/'.backquip-restart.log').open('a') as log:
        subprocess.Popen(command,cwd=str(ROOT),stdin=subprocess.DEVNULL,
                         stdout=log,stderr=subprocess.STDOUT,
                         creationflags=getattr(subprocess,'CREATE_NEW_PROCESS_GROUP',0),
                         start_new_session=sys.platform!='win32')

def _running(pid):
    try:os.kill(pid,0);return True
    except OSError:return False

if __name__=='__main__':
    try:
        if len(sys.argv) in (4,5) and sys.argv[1]=='apply':
            apply_release(Path(sys.argv[2]), int(sys.argv[3]), sys.argv[4] if len(sys.argv)==5 else 'stable')
        elif len(sys.argv)==3 and sys.argv[1]=='restart':
            restart_after_exit(int(sys.argv[2]))
        else:
            sys.exit('Usage: updater.py apply ARCHIVE PID [stable|development] | restart PID')
    except Exception as exc:
        (ROOT/'.backquip-update.log').open('a').write(f'Update/restart failed: {exc}\n')
        sys.exit(1)
