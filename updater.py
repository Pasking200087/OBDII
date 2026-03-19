"""
updater.py — автообновление через GitHub (приватный репозиторий)
Используется в car_diagnostics_gui.py при каждом запуске.
"""

import os
import sys
import json
import shutil
import tempfile
import threading
import subprocess
import urllib.request
import urllib.error
from pathlib import Path

# ─────────────────────────────────────────────────────────
# НАСТРОЙКИ — заполните перед сборкой
# ─────────────────────────────────────────────────────────

GITHUB_USER  = "Pasking200087"          # ваш логин на GitHub
GITHUB_REPO  = "OBDII"    # название репозитория
GITHUB_TOKEN = "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"          # Personal Access Token (read:packages, contents)

# API endpoint последнего релиза
RELEASE_URL = (
    f"https://api.github.com/repos/{GITHUB_USER}/{GITHUB_REPO}"
    f"/releases/latest"
)

# Текущая версия программы (меняйте при каждом релизе)
CURRENT_VERSION = "1.0.0"

# Путь к конфигу с токеном (если хотите хранить отдельно от кода)
TOKEN_FILE = Path(os.getenv("APPDATA", ".")) / "OBD2Diagnostics" / "token.cfg"


# ─────────────────────────────────────────────────────────
# Вспомогательные
# ─────────────────────────────────────────────────────────

def _get_token() -> str:
    """Берёт токен: сначала из TOKEN_FILE, потом из константы."""
    if TOKEN_FILE.exists():
        return TOKEN_FILE.read_text().strip()
    return GITHUB_TOKEN


def _gh_request(url: str) -> dict:
    """GET-запрос к GitHub API с авторизацией. Бросает исключение при ошибке."""
    token = _get_token()
    req = urllib.request.Request(url, headers={
        "Authorization": f"token {token}",
        "Accept":        "application/vnd.github.v3+json",
        "User-Agent":    "OBD2-Diagnostics-Updater/1.0",
    })
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode())


def _download_file(url: str, dest: Path) -> bool:
    """Скачать файл с авторизацией GitHub."""
    token = _get_token()
    req = urllib.request.Request(url, headers={
        "Authorization": f"token {token}",
        "Accept":        "application/octet-stream",
        "User-Agent":    "OBD2-Diagnostics-Updater/1.0",
    })
    try:
        with urllib.request.urlopen(req, timeout=60) as resp, open(dest, "wb") as f:
            shutil.copyfileobj(resp, f)
        return True
    except Exception:
        return False



# ─────────────────────────────────────────────────────────
# Публичный API
# ─────────────────────────────────────────────────────────

def save_token(token: str):
    """Сохранить токен в файл конфигурации."""
    TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    TOKEN_FILE.write_text(token.strip())


def get_current_version() -> str:
    return CURRENT_VERSION


def check_for_update() -> dict | None:
    """
    Проверяет наличие новой версии.
    Возвращает dict с информацией об обновлении или None.
    {
        "version":      "1.1.0",
        "description":  "Что изменилось",
        "download_url": "https://...",
        "size_mb":      4.2,
    }
    """
    data = _gh_request(RELEASE_URL)
    if not data or "tag_name" not in data:
        return None

    remote_ver = data["tag_name"]
    if remote_ver == CURRENT_VERSION:
        return None   # уже актуальная версия

    # Берём первый asset (.exe)
    assets = data.get("assets", [])
    if not assets:
        return None

    asset = assets[0]
    size_mb = round(asset.get("size", 0) / 1024 / 1024, 1)

    # URL для приватного репозитория — через API с авторизацией
    asset_api_url = asset.get("url", "")

    return {
        "version":      remote_ver,
        "description":  data.get("body", ""),
        "download_url": asset_api_url,
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

    # Скачиваем с прогрессом
    # GitHub API для приватных ассетов делает редирект на S3 — нужен Accept: octet-stream
    token = _get_token()
    opener = urllib.request.build_opener(urllib.request.HTTPRedirectHandler())
    req = urllib.request.Request(download_url, headers={
        "Authorization": f"token {token}",
        "Accept":        "application/octet-stream",
        "User-Agent":    "OBD2-Diagnostics-Updater/1.0",
    })
    try:
        with opener.open(req, timeout=120) as resp:
            total = int(resp.headers.get("Content-Length", 0))
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

    # Bat-скрипт: ждёт закрытия программы → заменяет exe → перезапускает
    # Используем cp866 (кодировка консоли Windows) чтобы поддержать кирилицу в путях
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
        creationflags=subprocess.CREATE_NO_WINDOW
        if sys.platform == "win32" else 0
    )
    return True


def check_async(on_update_found, on_error=None, on_up_to_date=None):
    """
    Запускает проверку обновления в фоновом потоке.
    on_update_found(info: dict) — вызывается если есть обновление.
    on_error(msg: str)          — вызывается при ошибке сети/токена.
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
