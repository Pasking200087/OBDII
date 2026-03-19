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
    req = urllib.request.Request(url, headers={
        "Accept":     "application/vnd.github.v3+json",
        "User-Agent": "OBD2-Diagnostics-Updater/1.0",
    })
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode())


def _is_exe(path: Path) -> bool:
    """Проверяет MZ-заголовок (Windows PE / Inno Setup installer)."""
    try:
        with open(path, "rb") as f:
            return f.read(2) == b"MZ"
    except Exception:
        return False


# ─────────────────────────────────────────────────────────
# Публичный API
# ─────────────────────────────────────────────────────────

def get_current_version() -> str:
    return CURRENT_VERSION


def check_for_update() -> dict | None:
    """Проверяет наличие новой версии. Возвращает dict или None."""
    data = _gh_request(RELEASE_URL)

    remote_ver = data.get("tag_name", "")
    if not remote_ver or remote_ver == CURRENT_VERSION:
        return None

    assets = data.get("assets", [])
    if not assets:
        return None

    # Предпочитаем Setup.exe, иначе берём первый ассет
    asset = next(
        (a for a in assets if a.get("name", "").endswith("_Setup.exe")),
        assets[0],
    )
    size_mb = round(asset.get("size", 0) / 1024 / 1024, 1)

    return {
        "version":      remote_ver,
        "description":  data.get("body", ""),
        "download_url": asset["browser_download_url"],
        "filename":     asset.get("name", ""),
        "size_mb":      size_mb,
    }


def apply_update(download_url: str, progress_cb=None) -> bool:
    """
    Скачивает установщик (.exe) и запускает его тихо (/SILENT).
    Inno Setup сам закроет старую версию, установит новую и перезапустит.
    """
    if not download_url:
        return False

    tmp_dir     = Path(tempfile.mkdtemp())
    installer   = tmp_dir / "OBD2_Diagnostics_Setup.exe"

    # ── Скачиваем ────────────────────────────────────────
    req = urllib.request.Request(download_url, headers={
        "User-Agent": "OBD2-Diagnostics-Updater/1.0",
    })
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            total      = int(resp.headers.get("Content-Length", 0))
            downloaded = 0
            with open(installer, "wb") as f:
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

    if not _is_exe(installer):
        return False

    # ── Bat-скрипт: ждём закрытия приложения, запускаем установщик ──
    # /SILENT   — тихая установка с полосой прогресса
    # /NORESTART — не перезагружать ПК
    # /CLOSEAPPLICATIONS — закрыть запущенные копии программы
    bat = tmp_dir / "do_update.bat"
    bat_lines = [
        "@echo off",
        "ping 127.0.0.1 -n 4 >nul",
        f"\"{installer}\" /SILENT /NORESTART /CLOSEAPPLICATIONS",
        "del \"%~f0\"",
    ]
    bat_content = "\r\n".join(bat_lines) + "\r\n"
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
    """Запускает проверку обновления в фоновом потоке."""
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
