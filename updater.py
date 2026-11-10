"""Actualizare Windows cu confirmare și verificare SHA-256."""
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

CONFIG = Path(__file__).with_name('update_config.json')
MAX_DOWNLOAD = 150 * 1024 * 1024

def _urlopen(url, timeout=12):
    if not url.startswith('https://'):
        raise ValueError('Actualizările necesită HTTPS.')
    return urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent':'Betel-Padureni-Updater/1'}), timeout=timeout)

def _version(value):
    if not re.fullmatch(r'\d+\.\d+\.\d+', value):
        raise ValueError('Versiune invalidă în manifest.')
    return tuple(int(x) for x in value.split('.'))

def _config():
    # În EXE, fișierul poate fi pus lângă executabil, pentru configurare.
    external = Path(sys.executable).parent / 'update_config.json' if getattr(sys,'frozen',False) else CONFIG
    if not external.exists():
        raise RuntimeError('Actualizările nu sunt configurate. Pune update_config.json lângă aplicație.')
    cfg = json.loads(external.read_text(encoding='utf-8'))
    url = cfg.get('manifest_url','')
    if not url or 'UTILIZATOR' in url or 'REPOSITORY' in url:
        raise RuntimeError('Actualizările nu sunt configurate încă. Completează manifest_url din update_config.json cu adresa GitHub Releases.')
    return url

def find_update(current):
    url = _config()
    with _urlopen(url) as response:
        if response.geturl().split(':',1)[0] != 'https':
            raise RuntimeError('Redirecționare nesigură.')
        raw = response.read(65537)
    if len(raw) > 65536:
        raise ValueError('Manifest prea mare.')
    obj = json.loads(raw.decode('utf-8'))
    version = str(obj['version'])
    if _version(version) <= _version(current):
        return None
    exe_url = str(obj['url'])
    if not exe_url.startswith('https://'):
        raise ValueError('Linkul executabilului trebuie să fie HTTPS.')
    checksum = str(obj['sha256']).lower()
    if not re.fullmatch(r'[0-9a-f]{64}',checksum):
        raise ValueError('SHA-256 invalid în manifest.')
    return version, str(obj.get('notes','Actualizare disponibilă.')), exe_url, checksum

def download_verified(url, expected_sha256):
    fd, name = tempfile.mkstemp(prefix='betel-update-', suffix='.exe')
    os.close(fd)
    dest = Path(name)
    digest = hashlib.sha256()
    total = 0
    try:
        with _urlopen(url, timeout=30) as response, dest.open('wb') as output:
            if not response.geturl().startswith('https://'):
                raise RuntimeError('Redirecționare nesigură.')
            while True:
                chunk = response.read(1024*256)
                if not chunk: break
                total += len(chunk)
                if total > MAX_DOWNLOAD:
                    raise ValueError('Fișier prea mare (peste 150 MB).')
                digest.update(chunk)
                output.write(chunk)
        if digest.hexdigest() != expected_sha256:
            raise ValueError('Verificarea SHA-256 a eșuat. Actualizarea a fost anulată.')
        if dest.read_bytes()[:2] != b'MZ':
            raise ValueError('Fișierul descărcat nu este un executabil Windows.')
        return dest
    except Exception:
        dest.unlink(missing_ok=True)
        raise

def launch_installer(staged):
    if os.name != 'nt' or not getattr(sys,'frozen',False):
        raise RuntimeError('Instalarea automată funcționează numai din aplicația EXE pe Windows.')
    target = Path(sys.executable).resolve()
    if not target.is_file():
        raise RuntimeError('Executabilul curent nu există.')
    # Script local, generat de aplicație; nu executăm cod descărcat de pe internet.
    # Așteaptă închiderea procesului, înlocuiește executabilul și pornește noua versiune.
    script = r"""param([string]$Source,[string]$Target,[int]$OldPid)
$ErrorActionPreference = 'Stop'
Start-Sleep -Seconds 2
try { Wait-Process -Id $OldPid -Timeout 60 -ErrorAction SilentlyContinue } catch {}
$backup = "$Target.bak"
try {
    if (Test-Path -LiteralPath $backup) { Remove-Item -LiteralPath $backup -Force }
    Move-Item -LiteralPath $Target -Destination $backup -Force
    try { Move-Item -LiteralPath $Source -Destination $Target -Force }
    catch { Move-Item -LiteralPath $backup -Destination $Target -Force; throw }
    Start-Process -FilePath $Target
} catch {
    Add-Type -AssemblyName System.Windows.Forms
    [System.Windows.Forms.MessageBox]::Show("Actualizarea nu a reusit: $($_.Exception.Message)", 'Organizator Cantari') | Out-Null
}
"""
    fd, path = tempfile.mkstemp(prefix='betel-install-', suffix='.ps1')
    os.close(fd)
    Path(path).write_text(script, encoding='utf-8-sig')
    subprocess.Popen(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-WindowStyle','Hidden','-File',path,
                      '-Source',str(staged),'-Target',str(target),'-OldPid',str(os.getpid())],
                     creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
