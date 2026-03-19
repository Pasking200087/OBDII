"""
updater.py — автообновление через GitHub (публичный репозиторий)
Используется в car_diagnostics_gui.py при каждом запуске.
"""

import sys
import json
import tempfile
import threading
import subprocess
import urllib.request
from pathlib import Path

# ─────────────────────────────────────────────────────────
# НАСТРОЙКИ
# ─────────────────────────────────────────────────────────

GITHUB_USER  = "Pasking200087"
GITHUB_REPO  = "OBDII"

# API endpoint последнего релиза (публичный, без токена)
RELEASE_URL = (
    f"https://api.github.com/repos/{GITHUB_USER}/{GITHUB_REPO}"
    f"/releases/latest"
)

# Текущая версия — GitHub Actions заменяет это значение при сборке
CURRENT_VERSION = "dev"


# ─────────────────────────────────────────────────────────
# Вспомогательные
# ─────────────────────────────────────────────────────────

def _gh_request(url: str) -> dict:
    """GET к GitHub API. Бросает исключение при ошибке."""
    req = urllib.request.Request(url, headers={
        "Accept":     "application/vnd.github.v3+json",
        "User-Agent": "OBD2-Diagnostics-Updater/1.0",
    })
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode())


# ─────────────────────────────────────────────────────────
# Публичный API
# ─────────────────────────────────────────────────────────

def get_current_version() -> str:
    return CURRENT_VERSION


def check_for_update() -> dict | None:
    """
    Проверяет наличие новой версии.
    Возвращает dict или None если обновлений нет.
    """
    data = _gh_request(RELEASE_URL)

    remote_ver = data.get("tag_name", "")
    if not remote_ver or remote_ver == CURRENT_VERSION:
        return None   # уже актуальная версия

    assets = data.get("assets", [])
    if not assets:
        return None   # релиз есть, но exe ещё не загружен (сборка идёт)

    asset   = assets[0]
    size_mb = round(asset.get("size", 0) / 1024 / 1024, 1)

    # browser_download_url — прямая ссылка, работает без токена для публичных репо
    return {
        "version":      remote_ver,
        "description":  data.get("body", ""),
        "download_url": asset["browser_download_url"],
        "size_mb":      size_mb,
    }


def apply_update(download_url: str, progress_cb=None) -> bool:
    """
    Скачивает новый .exe и запускает bat-скрипт замены.
    progress_cb(percent: int) вызывается в процессе загрузки.
    """
    if not download_url:
        return False

    current_exe = Path(sys.executable)
    tmp_dir     = Path(tempfile.mkdtemp())
    new_exe     = tmp_dir / "OBD2_Diagnostics_new.exe"

    req = urllib.request.Request(download_url, headers={
        "User-Agent": "OBD2-Diagnostics-Updater/1.0",
    })
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            total      = int(resp.headers.get("Content-Length", 0))
            downloaded = 0
            with open(new_exe, "wb") as f:
                while True:
                    chunk = resp.read(65536)
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)
                    if progress_cb and total:
                        progress_cb(int(downloaded / total * 100))
    except Exception:
        return False

    # Проверяем: скачанный файл должен быть EXE (Magic: MZ)
    try:
        with open(new_exe, "rb") as f:
            if f.read(2) != b"MZ":
                return False
    except Exception:
        return False

    # Bat-скрипт: ждёт закрытия → заменяет exe → перезапускает
    bat = tmp_dir / "do_update.bat"
    bat_content = (
        "@echo off\n"
        "ping 127.0.0.1 -n 4 >nul\n"
        f"move /Y \"{new_exe}\" \"{current_exe}\"\n"
        f"start \"\" \"{current_exe}\"\n"
        "del \"%~f0\"\n"
    )
    try:
        bat.write_text(bat_content, encoding="cp866")
    except (UnicodeEncodeError, LookupError):
        bat.write_bytes(bat_content.encode("utf-8"))

    subprocess.Popen(
        ["cmd", "/c", str(bat)],
        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
    )
    return True


def check_async(on_update_found, on_error=None, on_up_to_date=None):
    """
    Запускает проверку обновления в фоновом потоке.
    on_update_found(info: dict) — вызывается если есть обновление.
    on_error(msg: str)          — вызывается при ошибке сети.
    on_up_to_date()             — вызывается если версия актуальна.
    """
    def _worker():
        try:
            info = check_for_update()
            if info:
                on_update_found(info)
            elif on_up_to_date:
                on_up_to_date()
        except Exception as e:
            if on_error:
                on_error(str(e))

    threading.Thread(target=_worker, daemon=True).start()
