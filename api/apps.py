import os
import sys
import shutil
import stat
import zipfile
import urllib.request
from pathlib import Path
from django.apps import AppConfig

def ensure_js_runtime():
    """Ensure a JavaScript runtime (Deno or Node) is present in PATH for yt-dlp on Linux cloud servers"""
    if shutil.which('node') or shutil.which('deno') or shutil.which('qjs'):
        return

    if sys.platform != 'linux':
        return

    bin_dir = Path.home() / '.local_bin'
    bin_dir.mkdir(parents=True, exist_ok=True)
    deno_exe = bin_dir / 'deno'

    if not deno_exe.exists():
        try:
            url = 'https://github.com/denoland/deno/releases/latest/download/deno-x86_64-unknown-linux-gnu.zip'
            zip_path = bin_dir / 'deno.zip'
            urllib.request.urlretrieve(url, zip_path)
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(bin_dir)
            if zip_path.exists():
                zip_path.unlink()
            if deno_exe.exists():
                deno_exe.chmod(deno_exe.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
        except Exception as e:
            print(f"Notice: Auto JS runtime initialization: {e}")

    if deno_exe.exists() and str(bin_dir) not in os.environ.get('PATH', ''):
        os.environ['PATH'] = f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}"

class ApiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'api'

    def ready(self):
        ensure_js_runtime()

