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
import zipfile
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


def _is_zip(path: Path) -> bool:
    try:
        with open(path, "rb") as f:
            return f.read(4) == b"PK\x03\x04"
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

    asset   = assets[0]
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
    Скачивает обновление (.zip или .exe) и запускает замену.
    Определяет формат автоматически по содержимому файла.
    """
    if not download_url:
        return False

    # sys.executable — путь к запущенному .exe
    current_exe = Path(sys.executable)
    install_dir = current_exe.parent
    tmp_dir     = Path(tempfile.mkdtemp())
    download_to = tmp_dir / "update_download"

    # ── Скачиваем ────────────────────────────────────────
    req = urllib.request.Request(download_url, headers={
        "User-Agent": "OBD2-Diagnostics-Updater/1.0",
    })
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            total      = int(resp.headers.get("Content-Length", 0))
            downloaded = 0
            with open(download_to, "wb") as f:
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

    # ── Определяем формат и готовим замену ───────────────
    if _is_zip(download_to):
        # Новый формат: zip с папкой OBD2_Diagnostics/
        extract_dir = tmp_dir / "extracted"
        try:
            with zipfile.ZipFile(download_to, "r") as zf:
                zf.extractall(extract_dir)
        except Exception:
            return False

        # Папка внутри zip: OBD2_Diagnostics/
        new_dir = extract_dir / "OBD2_Diagnostics"
        if not new_dir.exists():
            new_dir = extract_dir

        if not (new_dir / "OBD2_Diagnostics.exe").exists():
            return False

        # PowerShell Copy-Item — надёжно работает с пробелами в путях
        ps_src = str(new_dir).replace("'", "''")
        ps_dst = str(install_dir).replace("'", "''")

        bat = tmp_dir / "do_update.bat"
        bat_lines = [
            "@echo off",
            "ping 127.0.0.1 -n 4 >nul",
            f"powershell -NoProfile -Command \"Copy-Item -Path '{ps_src}\\*' -Destination '{ps_dst}' -Recurse -Force\"",
            f"start \"\" \"{install_dir}\\OBD2_Diagnostics.exe\"",
            "del \"%~f0\"",
        ]

    else:
        # Старый формат или одиночный exe
        # Проверяем MZ-заголовок
        try:
            with open(download_to, "rb") as f:
                if f.read(2) != b"MZ":
                    return False
        except Exception:
            return False

        new_exe = tmp_dir / "OBD2_Diagnostics_new.exe"
        download_to.rename(new_exe)

        bat = tmp_dir / "do_update.bat"
        bat_lines = [
            "@echo off",
            "ping 127.0.0.1 -n 4 >nul",
            f"move /Y \"{new_exe}\" \"{current_exe}\"",
            f"start \"\" \"{current_exe}\"",
            "del \"%~f0\"",
        ]

    # ── Записываем и запускаем bat ────────────────────────
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
