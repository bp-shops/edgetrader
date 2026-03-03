"""
EdgeTrader – Lizenz-Manager v2
by Philip Babuda

Features:
  - Key-Format:  EDGE-{Plan}-{XXXX}-{XXXX}-{XXX}{Nonce}
  - Pläne:       W = Woche (7 Tage), M = Monat (30 Tage), Y = Jahr (365 Tage)
  - Nonce:       A, B, C … für Nachkäufe desselben Kunden
  - Anti-Reuse:  Lizenzdaten werden an 3 Orten gespeichert
                 (AppData, LocalAppData, Registry)
  - Hardware-ID: Lizenz ist an eine Maschine gebunden
  - Trial:       7 Tage kostenlos (ebenfalls in allen 3 Orten gespeichert)
"""

import os, json, hashlib, hmac, time, base64, uuid, platform

# ── Geheimer Schlüssel (NUR du kennst diesen!) ────────────
_SECRET = b"EdgeTr4d3r_PhilipBabuda_2026_SECRET_KEY_xK9mP2"

# ── Konstanten ────────────────────────────────────────────
TRIAL_DAYS = 7
LICENSE_FILE = "edgetrader_license.dat"

PLAN_DAYS = {"W": 7, "M": 30, "Y": 365}
PLAN_LABELS = {"W": "Woche", "M": "Monat", "Y": "Jahr"}


# ══════════════════════════════════════════════════════════
#  VERSCHLÜSSELUNG
# ══════════════════════════════════════════════════════════
def _xor_crypt(data: bytes, key: bytes) -> bytes:
    return bytes(b ^ key[i % len(key)] for i, b in enumerate(data))


def _encode(data: dict) -> str:
    raw = json.dumps(data).encode("utf-8")
    encrypted = _xor_crypt(raw, _SECRET)
    return base64.b64encode(encrypted).decode("ascii")


def _decode(text: str) -> dict:
    try:
        encrypted = base64.b64decode(text.encode("ascii"))
        raw = _xor_crypt(encrypted, _SECRET)
        return json.loads(raw.decode("utf-8"))
    except Exception:
        return {}


# ══════════════════════════════════════════════════════════
#  HARDWARE-ID
# ══════════════════════════════════════════════════════════
def get_machine_id() -> str:
    parts = [
        platform.node(),
        platform.machine(),
        platform.processor(),
        str(uuid.getnode()),
    ]
    raw = "|".join(parts).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:16].upper()


# ══════════════════════════════════════════════════════════
#  ANTI-REUSE: 3 SPEICHERORTE
# ══════════════════════════════════════════════════════════
def _get_file_paths() -> list:
    """Gibt die 2 Datei-Pfade zurück (AppData + LocalAppData)."""
    paths = []
    for env_var in ("APPDATA", "LOCALAPPDATA"):
        base = os.environ.get(env_var, "")
        if base:
            d = os.path.join(base, "EdgeTrader")
            os.makedirs(d, exist_ok=True)
            paths.append(os.path.join(d, LICENSE_FILE))
    # Fallback falls keine env-Variablen
    if not paths:
        d = os.path.join(os.path.expanduser("~"), ".edgetrader")
        os.makedirs(d, exist_ok=True)
        paths.append(os.path.join(d, LICENSE_FILE))
    return paths


def _read_registry() -> dict:
    """Liest Lizenzdaten aus der Windows-Registry."""
    try:
        import winreg
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"SOFTWARE\EdgeTrader")
        val, _ = winreg.QueryValueEx(key, "license_data")
        winreg.CloseKey(key)
        return _decode(val)
    except Exception:
        return {}


def _write_registry(data: dict):
    """Schreibt Lizenzdaten in die Windows-Registry."""
    try:
        import winreg
        key = winreg.CreateKeyEx(
            winreg.HKEY_CURRENT_USER, r"SOFTWARE\EdgeTrader",
            0, winreg.KEY_WRITE
        )
        winreg.SetValueEx(key, "license_data", 0, winreg.REG_SZ, _encode(data))
        winreg.CloseKey(key)
    except Exception:
        pass


def _read_file(path: str) -> dict:
    """Liest eine einzelne Lizenzdatei."""
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return _decode(f.read().strip())
    except Exception:
        return {}


def _write_file(path: str, data: dict):
    """Schreibt eine einzelne Lizenzdatei."""
    try:
        d = os.path.dirname(path)
        os.makedirs(d, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(_encode(data))
    except Exception:
        pass


def _read_license() -> dict:
    """
    Liest Lizenzdaten aus ALLEN 3 Orten.
    Gibt die "beste" Version zurück (zuletzt aktiviert).
    """
    candidates = []

    # Dateien
    for p in _get_file_paths():
        d = _read_file(p)
        if d:
            candidates.append(d)

    # Registry
    d = _read_registry()
    if d:
        candidates.append(d)

    if not candidates:
        return {}

    # Wähle die Version mit der neuesten activation_time
    # (oder trial_start falls nicht aktiviert)
    best = candidates[0]
    for c in candidates[1:]:
        c_time = c.get("activation_time", c.get("trial_start", 0))
        b_time = best.get("activation_time", best.get("trial_start", 0))
        if c_time > b_time:
            best = c
        # Aktivierte Lizenz hat immer Vorrang
        if c.get("activated") and not best.get("activated"):
            best = c

    return best


def _write_license(data: dict):
    """Schreibt Lizenzdaten in ALLE 3 Orte."""
    for p in _get_file_paths():
        _write_file(p, data)
    _write_registry(data)


# ══════════════════════════════════════════════════════════
#  SCHLÜSSEL-GENERIERUNG & VALIDIERUNG
# ══════════════════════════════════════════════════════════
def generate_key(customer_name: str, plan: str = "M", nonce: str = "A") -> str:
    """
    Generiert einen Lizenzschlüssel.
    Format: EDGE-{Plan}-{XXXX}-{XXXX}-{XXX}{Nonce}
    Beispiel: EDGE-M-A3F2-B8C1-D4EA
    """
    plan = plan.upper()
    nonce = nonce.upper()
    if plan not in PLAN_DAYS:
        plan = "M"
    if not nonce or len(nonce) != 1:
        nonce = "A"

    payload = f"{customer_name.strip().lower()}|{plan}|{nonce}".encode("utf-8")
    sig = hmac.new(_SECRET, payload, hashlib.sha256).hexdigest().upper()
    p1 = sig[0:4]
    p2 = sig[4:8]
    p3 = sig[8:11] + nonce
    return f"EDGE-{plan}-{p1}-{p2}-{p3}"


def validate_key(key: str, customer_name: str) -> tuple:
    """
    Prüft ob ein Lizenzschlüssel gültig ist.
    Returns: (valid: bool, plan: str, nonce: str)
    """
    key = key.strip().upper()
    parts = key.split("-")

    # Neues Format: EDGE-{Plan}-{XXXX}-{XXXX}-{XXXX}
    if len(parts) == 5 and parts[0] == "EDGE":
        plan = parts[1]
        if plan not in PLAN_DAYS:
            return False, "", ""
        nonce = parts[4][-1]  # Letztes Zeichen = Nonce
        expected = generate_key(customer_name, plan, nonce)
        if hmac.compare_digest(key, expected):
            return True, plan, nonce
        return False, "", ""

    # Altes Format: ET-XXXX-XXXX-XXXX-XXXX (Abwärtskompatibilität)
    if len(parts) == 5 and parts[0] == "ET":
        payload = customer_name.strip().lower().encode("utf-8")
        sig = hmac.new(_SECRET, payload, hashlib.sha256).hexdigest().upper()
        old_parts = [sig[i:i+4] for i in range(0, 16, 4)]
        expected_old = f"ET-{old_parts[0]}-{old_parts[1]}-{old_parts[2]}-{old_parts[3]}"
        if hmac.compare_digest(key, expected_old):
            return True, "Y", "A"  # Alte Keys = 1 Jahr
        return False, "", ""

    return False, "", ""


# ══════════════════════════════════════════════════════════
#  TRIAL-SYSTEM
# ══════════════════════════════════════════════════════════
def init_trial():
    """Startet die Testphase beim ersten Start."""
    data = _read_license()
    if not data:
        data = {
            "trial_start": int(time.time()),
            "machine_id": get_machine_id(),
            "activated": False,
            "customer": "",
            "key": "",
            "plan": "",
            "nonce": "",
        }
        _write_license(data)
    return data


def get_trial_days_left() -> int:
    """Gibt die verbleibenden Trial-Tage zurück. -1 wenn aktiviert."""
    data = _read_license()
    if not data:
        data = init_trial()

    if data.get("activated"):
        return -1

    start = data.get("trial_start", int(time.time()))
    elapsed = (int(time.time()) - start) / 86400
    remaining = max(0, TRIAL_DAYS - int(elapsed))
    return remaining


# ══════════════════════════════════════════════════════════
#  LIZENZ-PRÜFUNG
# ══════════════════════════════════════════════════════════
def is_licensed() -> bool:
    """Prüft ob eine gültige, nicht abgelaufene Lizenz vorhanden ist."""
    data = _read_license()
    if not data.get("activated"):
        return False

    key = data.get("key", "")

    # Alte ET-Keys: Übergangsweise als 1-Jahres-Lizenz behandeln
    if key.startswith("ET-"):
        activation = data.get("activation_time", 0)
        if activation == 0:
            return True  # Kein Zeitstempel → gültig lassen
        expiry = activation + (365 * 86400)
        return int(time.time()) <= expiry

    # Neue EDGE-Keys: Plan-basierte Laufzeit
    plan = data.get("plan", "M")
    activation = data.get("activation_time", 0)
    if activation == 0:
        return True
    duration = PLAN_DAYS.get(plan, 30) * 86400
    expiry = activation + duration
    return int(time.time()) <= expiry


def is_trial_expired() -> bool:
    """Prüft ob die Testphase abgelaufen ist."""
    days = get_trial_days_left()
    return days == 0 and not is_licensed()


def get_license_days_left() -> int:
    """Gibt die verbleibenden Lizenz-Tage zurück. -1 wenn Trial."""
    data = _read_license()
    if not data.get("activated"):
        return -1

    key = data.get("key", "")
    plan = data.get("plan", "M")
    activation = data.get("activation_time", 0)

    if activation == 0:
        return 999  # Unbekannt → großer Wert

    if key.startswith("ET-"):
        duration = 365
    else:
        duration = PLAN_DAYS.get(plan, 30)

    expiry = activation + (duration * 86400)
    remaining = (expiry - int(time.time())) / 86400
    return max(0, int(remaining))


# ══════════════════════════════════════════════════════════
#  AKTIVIERUNG
# ══════════════════════════════════════════════════════════
def activate_license(customer_name: str, license_key: str) -> tuple:
    """
    Aktiviert eine Lizenz.
    Returns: (success: bool, message: str)
    """
    if not customer_name.strip():
        return False, "Bitte gib deinen Namen ein."

    if not license_key.strip():
        return False, "Bitte gib einen Lizenzschlüssel ein."

    valid, plan, nonce = validate_key(license_key, customer_name)

    if not valid:
        return False, "Ungültiger Lizenzschlüssel! Bitte prüfe Name und Key."

    # Anti-Reuse: Prüfe ob Key schon auf anderer Maschine aktiviert wurde
    existing = _read_license()
    if (existing.get("activated")
            and existing.get("key") == license_key.strip().upper()
            and existing.get("machine_id") != get_machine_id()):
        return False, "Dieser Key wurde bereits auf einem anderen PC aktiviert!"

    # Aktivierung durchführen
    data = _read_license()
    if not data:
        data = init_trial()

    plan_label = PLAN_LABELS.get(plan, "Monat")
    duration = PLAN_DAYS.get(plan, 30)

    data["activated"] = True
    data["customer"] = customer_name.strip()
    data["key"] = license_key.strip().upper()
    data["plan"] = plan
    data["nonce"] = nonce
    data["activation_time"] = int(time.time())
    data["machine_id"] = get_machine_id()

    # In alle 3 Orte schreiben
    _write_license(data)

    return True, f"Lizenz aktiviert ({plan_label}) für: {customer_name}"


# ══════════════════════════════════════════════════════════
#  INFORMATIONEN
# ══════════════════════════════════════════════════════════
def get_license_info() -> dict:
    """Gibt alle Lizenz-Informationen zurück."""
    data = _read_license()
    if not data:
        data = init_trial()

    info = {
        "activated": data.get("activated", False),
        "customer": data.get("customer", ""),
        "trial_days_left": get_trial_days_left(),
        "machine_id": get_machine_id(),
        "trial_start": data.get("trial_start", 0),
        "plan": data.get("plan", ""),
        "plan_label": "",
        "license_days_left": -1,
        "license_expired": False,
    }

    if info["activated"]:
        plan = data.get("plan", "M")
        info["plan_label"] = PLAN_LABELS.get(plan, "Monat")
        info["license_days_left"] = get_license_days_left()
        info["license_expired"] = info["license_days_left"] == 0

    return info


# ══════════════════════════════════════════════════════════
#  DIREKTES TESTEN
# ══════════════════════════════════════════════════════════
if __name__ == "__main__":
    print("=== EdgeTrader Lizenz-Manager v2 ===")
    print()
    info = get_license_info()
    print(f"Maschinen-ID:      {info['machine_id']}")
    print(f"Aktiviert:         {info['activated']}")
    print(f"Kunde:             {info['customer'] or '---'}")
    print(f"Plan:              {info['plan_label'] or '---'}")
    print(f"Trial Tage übrig:  {info['trial_days_left']}")
    print(f"Lizenz Tage übrig: {info['license_days_left']}")
    print()
    # Test-Keys generieren
    test_name = "Test Kunde"
    for plan in ("W", "M", "Y"):
        for nonce in ("A", "B"):
            key = generate_key(test_name, plan, nonce)
            valid, p, n = validate_key(key, test_name)
            print(f"  {plan}/{nonce}: {key}  → valid={valid}")
    print()
    # Altes Format testen
    old_payload = test_name.strip().lower().encode("utf-8")
    old_sig = hmac.new(_SECRET, old_payload, hashlib.sha256).hexdigest().upper()
    old_parts = [old_sig[i:i+4] for i in range(0, 16, 4)]
    old_key = f"ET-{old_parts[0]}-{old_parts[1]}-{old_parts[2]}-{old_parts[3]}"
    valid, p, n = validate_key(old_key, test_name)
    print(f"  ALT: {old_key}  → valid={valid}, plan={p}, nonce={n}")
