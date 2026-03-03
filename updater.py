"""
EdgeTrader – Auto-Updater v2
by Philip Babuda

Prüft beim Start ob eine neue Version verfügbar ist.
Lädt Updates automatisch herunter und installiert sie.

Update-Quellen (in Reihenfolge):
  1. GitHub Gist (primär)  – funktioniert auch mit privatem Repo
  2. GitHub Releases API   – Fallback
"""

import os, sys, json, threading, tempfile, subprocess, ssl
import urllib.request
import urllib.error

try:
    import certifi
    _SSL_CTX = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    _SSL_CTX = ssl.create_default_context()

# ── UPDATE-QUELLEN ────────────────────────────────────────
# 1. GitHub Gist (öffentlich, kein Token nötig)
#    Erstelle einen öffentlichen Gist mit Datei "version.json"
#    Gist-URL: https://gist.githubusercontent.com/{USER}/{GIST_ID}/raw/version.json
GIST_URL = "https://gist.githubusercontent.com/pb993/a2d8636b279a7fbd2e650ec8f5742b79/raw/version.json"

# 2. GitHub Releases API (Fallback)
#    Funktioniert mit öffentlichen Repos ohne Token
RELEASES_API = "https://api.github.com/repos/bp-shops/edgetrader/releases/latest"

# 3. Legacy: Raw GitHub (altes Format, letzte Fallback-Option)
RAW_URL = "https://raw.githubusercontent.com/bp-shops/edgetrader/main/version.json"


def _parse_version(v: str) -> tuple:
    """'1.2.3' → (1, 2, 3) für Vergleich."""
    try:
        return tuple(int(x) for x in v.strip().split("."))
    except Exception:
        return (0, 0, 0)


def _fetch_json(url: str, timeout: int = 5) -> dict:
    """Holt JSON von einer URL. Gibt {} bei Fehler zurück."""
    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "EdgeTrader/Updater",
                "Accept": "application/json",
            }
        )
        with urllib.request.urlopen(req, timeout=timeout, context=_SSL_CTX) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception:
        return {}


def _check_gist() -> dict:
    """Prüft GitHub Gist auf Updates."""
    data = _fetch_json(GIST_URL)
    if data and "version" in data:
        return {
            "version": data["version"],
            "download_url": data.get("download_url", ""),
            "changelog": data.get("changelog", ""),
        }
    return {}


def _check_releases_api() -> dict:
    """Prüft GitHub Releases API auf Updates."""
    data = _fetch_json(RELEASES_API)
    if not data or "tag_name" not in data:
        return {}

    version = data["tag_name"].lstrip("v")
    download_url = ""
    # Suche nach .exe Asset
    for asset in data.get("assets", []):
        name = asset.get("name", "").lower()
        if name.endswith(".exe") and "setup" in name:
            download_url = asset.get("browser_download_url", "")
            break

    return {
        "version": version,
        "download_url": download_url,
        "changelog": data.get("body", "")[:200],
    }


def _check_raw_github() -> dict:
    """Prüft Raw GitHub (Legacy-Fallback)."""
    data = _fetch_json(RAW_URL)
    if data and "version" in data:
        return {
            "version": data["version"],
            "download_url": data.get("download_url", ""),
            "changelog": data.get("changelog", ""),
        }
    return {}


def check_for_update(current_version: str, callback=None, error_callback=None):
    """
    Prüft ob ein Update verfügbar ist (im Hintergrund-Thread).
    Versucht 3 Quellen: Gist → Releases API → Raw GitHub.

    callback(info) wird aufgerufen mit:
      info = {
        "update_available": True/False,
        "latest_version": "1.2.0",
        "download_url": "https://...",
        "changelog": "Was ist neu...",
        "current_version": "1.1.0",
        "source": "gist" / "releases" / "raw"
      }
    """
    def _check():
        try:
            # Quellen der Reihe nach probieren
            sources = [
                ("gist", _check_gist),
                ("releases", _check_releases_api),
                ("raw", _check_raw_github),
            ]

            update_info = {}
            source_name = ""

            for name, checker in sources:
                info = checker()
                if info and info.get("version"):
                    update_info = info
                    source_name = name
                    break

            if not update_info:
                raise Exception("Keine Update-Quelle erreichbar")

            latest = update_info.get("version", "0.0.0")
            result = {
                "update_available": _parse_version(latest) > _parse_version(current_version),
                "latest_version": latest,
                "download_url": update_info.get("download_url", ""),
                "changelog": update_info.get("changelog", ""),
                "current_version": current_version,
                "source": source_name,
            }

            if callback:
                callback(result)

        except Exception as e:
            if error_callback:
                error_callback(str(e))

    threading.Thread(target=_check, daemon=True).start()


def download_and_install(download_url: str, progress_callback=None):
    """
    Lädt die neue Setup.exe herunter und startet die Installation.
    progress_callback(percent) wird mit dem Fortschritt aufgerufen.
    """
    def _download():
        try:
            tmp_dir = os.path.join(tempfile.gettempdir(), "EdgeTrader_Update")
            os.makedirs(tmp_dir, exist_ok=True)
            setup_path = os.path.join(tmp_dir, "EdgeTrader_Setup_Update.exe")

            req = urllib.request.Request(
                download_url,
                headers={"User-Agent": "EdgeTrader/Updater"}
            )

            with urllib.request.urlopen(req, timeout=60, context=_SSL_CTX) as resp:
                total = int(resp.headers.get("Content-Length", 0))
                downloaded = 0
                chunk_size = 65536

                with open(setup_path, "wb") as f:
                    while True:
                        chunk = resp.read(chunk_size)
                        if not chunk:
                            break
                        f.write(chunk)
                        downloaded += len(chunk)
                        if progress_callback and total > 0:
                            percent = int((downloaded / total) * 100)
                            progress_callback(percent)

            if progress_callback:
                progress_callback(100)

            if os.path.exists(setup_path):
                subprocess.Popen([setup_path], shell=True)
                sys.exit(0)

        except Exception as e:
            if progress_callback:
                progress_callback(-1)

    threading.Thread(target=_download, daemon=True).start()


# ── Für direktes Testen ──────────────────────────────────
if __name__ == "__main__":
    def on_result(info):
        print(f"Quelle:            {info.get('source', '?')}")
        print(f"Update verfügbar:  {info['update_available']}")
        print(f"Aktuelle Version:  {info['current_version']}")
        print(f"Neueste Version:   {info['latest_version']}")
        if info['changelog']:
            print(f"Changelog:         {info['changelog'][:100]}")
        if info['download_url']:
            print(f"Download:          {info['download_url']}")

    def on_error(msg):
        print(f"Fehler: {msg}")

    print("Prüfe auf Updates (3 Quellen)...")
    check_for_update("1.0.0", callback=on_result, error_callback=on_error)
    import time; time.sleep(10)
