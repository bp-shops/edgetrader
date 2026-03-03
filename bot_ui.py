"""
EdgeTrader – Universal Signal Bot UI
by Philip Babuda
"""

import tkinter as tk
from tkinter import scrolledtext, messagebox, ttk
import subprocess, threading, sys, os, re, json
from datetime import datetime
from license_manager import (
    get_license_info, activate_license, is_trial_expired,
    is_licensed, get_trial_days_left, get_license_days_left, init_trial
)
from updater import check_for_update, download_and_install
from trade_history import TradeHistory

VERSION = "1.1.0"

# ── Pfade ────────────────────────────────────────────────
def get_app_dir() -> str:
    """Gibt das AppData-Verzeichnis für EdgeTrader zurück."""
    base = os.environ.get("APPDATA", os.path.expanduser("~"))
    app_dir = os.path.join(base, "EdgeTrader")
    os.makedirs(app_dir, exist_ok=True)
    return app_dir

def get_install_dir() -> str:
    """Gibt das Installationsverzeichnis zurück (wo die .exe liegt)."""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

APP_DIR = get_app_dir()

# ── Farben ───────────────────────────────────────────────
BG     = "#0d0f14"
CARD   = "#161a22"
CARD2  = "#1e2330"
ACCENT = "#f0b429"
GREEN  = "#22c55e"
RED    = "#ef4444"
BLUE   = "#3b82f6"
TEXT   = "#e2e8f0"
DIM    = "#64748b"
CF     = ("Consolas", 9)
CF_B   = ("Consolas", 9,  "bold")
CF_L   = ("Consolas", 11, "bold")
CF_T   = ("Consolas", 20, "bold")

CONFIG_FILE = os.path.join(APP_DIR, "edgetrader_config.json")

# ─────────────────────────────────────────────────────────
#  BROKER DEFINITIONEN
#  engine: "ccxt"   → wird über ccxt angesprochen (1 Bibliothek für alle)
#  engine: "custom" → eigene Bibliothek nötig
# ─────────────────────────────────────────────────────────
BROKERS = {
    # ── Crypto Futures (alle via ccxt) ───────────────────
    "Binance Futures": {
        "engine": "ccxt", "ccxt_id": "binanceusdm",
        "category": "🟡 Crypto Futures",
        "fields": ["API Key", "API Secret"],
        "keys":   ["api_key", "api_secret"],
        "has_testnet": True,
        "testnet_url": "https://testnet.binancefuture.com",
        "info": "Größte Crypto-Börse weltweit",
    },
    "Bybit": {
        "engine": "ccxt", "ccxt_id": "bybit",
        "category": "🟡 Crypto Futures",
        "fields": ["API Key", "API Secret"],
        "keys":   ["api_key", "api_secret"],
        "has_testnet": True,
        "testnet_url": "https://testnet.bybit.com",
        "info": "Top Derivate-Exchange",
    },
    "OKX": {
        "engine": "ccxt", "ccxt_id": "okx",
        "category": "🟡 Crypto Futures",
        "fields": ["API Key", "API Secret", "Passphrase"],
        "keys":   ["api_key", "api_secret", "passphrase"],
        "has_testnet": True,
        "testnet_url": "https://www.okx.com/testnet",
        "info": "OKX Futures & Spot",
    },
    "KuCoin Futures": {
        "engine": "ccxt", "ccxt_id": "kucoinfutures",
        "category": "🟡 Crypto Futures",
        "fields": ["API Key", "API Secret", "Passphrase"],
        "keys":   ["api_key", "api_secret", "passphrase"],
        "has_testnet": True,
        "testnet_url": "https://sandbox-futures.kucoin.com",
        "info": "KuCoin Futures Plattform",
    },
    "Bitget": {
        "engine": "ccxt", "ccxt_id": "bitget",
        "category": "🟡 Crypto Futures",
        "fields": ["API Key", "API Secret", "Passphrase"],
        "keys":   ["api_key", "api_secret", "passphrase"],
        "has_testnet": False,
        "info": "Bitget Copy-Trading & Futures",
    },
    "MEXC": {
        "engine": "ccxt", "ccxt_id": "mexc",
        "category": "🟡 Crypto Futures",
        "fields": ["API Key", "API Secret"],
        "keys":   ["api_key", "api_secret"],
        "has_testnet": False,
        "info": "MEXC Global Futures",
    },
    "Gate.io": {
        "engine": "ccxt", "ccxt_id": "gateio",
        "category": "🟡 Crypto Futures",
        "fields": ["API Key", "API Secret"],
        "keys":   ["api_key", "api_secret"],
        "has_testnet": True,
        "testnet_url": "https://futures-testnet.gateio.ws",
        "info": "Gate.io Futures & Spot",
    },
    "Phemex": {
        "engine": "ccxt", "ccxt_id": "phemex",
        "category": "🟡 Crypto Futures",
        "fields": ["API Key", "API Secret"],
        "keys":   ["api_key", "api_secret"],
        "has_testnet": True,
        "testnet_url": "https://testnet.phemex.com",
        "info": "Phemex Crypto Futures",
    },
    "BitMEX": {
        "engine": "ccxt", "ccxt_id": "bitmex",
        "category": "🟡 Crypto Futures",
        "fields": ["API Key", "API Secret"],
        "keys":   ["api_key", "api_secret"],
        "has_testnet": True,
        "testnet_url": "https://testnet.bitmex.com",
        "info": "Ursprüngliche Futures-Exchange",
    },
    "Kraken Futures": {
        "engine": "ccxt", "ccxt_id": "krakenfutures",
        "category": "🟡 Crypto Futures",
        "fields": ["API Key", "API Secret"],
        "keys":   ["api_key", "api_secret"],
        "has_testnet": True,
        "testnet_url": "https://demo-futures.kraken.com",
        "info": "Kraken Futures (Europa)",
    },
    "Huobi / HTX": {
        "engine": "ccxt", "ccxt_id": "htx",
        "category": "🟡 Crypto Futures",
        "fields": ["API Key", "API Secret"],
        "keys":   ["api_key", "api_secret"],
        "has_testnet": False,
        "info": "HTX (ehem. Huobi) Futures",
    },
    "BingX": {
        "engine": "ccxt", "ccxt_id": "bingx",
        "category": "🟡 Crypto Futures",
        "fields": ["API Key", "API Secret"],
        "keys":   ["api_key", "api_secret"],
        "has_testnet": False,
        "info": "BingX Copy-Trading & Futures",
    },
    "Coinbase Advanced": {
        "engine": "ccxt", "ccxt_id": "coinbase",
        "category": "🟡 Crypto Futures",
        "fields": ["API Key", "API Secret"],
        "keys":   ["api_key", "api_secret"],
        "has_testnet": True,
        "testnet_url": "https://public.sandbox.exchange.coinbase.com",
        "info": "Coinbase Advanced Trade",
    },
    "Deribit": {
        "engine": "ccxt", "ccxt_id": "deribit",
        "category": "🟡 Crypto Futures",
        "fields": ["API Key", "API Secret"],
        "keys":   ["api_key", "api_secret"],
        "has_testnet": True,
        "testnet_url": "https://test.deribit.com",
        "info": "Options & Futures (BTC/ETH)",
    },
    "WOO X": {
        "engine": "ccxt", "ccxt_id": "woofipro",
        "category": "🟡 Crypto Futures",
        "fields": ["API Key", "API Secret"],
        "keys":   ["api_key", "api_secret"],
        "has_testnet": True,
        "info": "WOO X Futures",
    },
    "Bitunix": {
        "engine": "ccxt", "ccxt_id": "bitunix",
        "category": "🟡 Crypto Futures",
        "fields": ["API Key", "API Secret"],
        "keys":   ["api_key", "api_secret"],
        "has_testnet": False,
        "info": "Bitunix Futures – niedrige Gebühren",
    },
    "Crypto.com": {
        "engine": "ccxt", "ccxt_id": "cryptocom",
        "category": "🟡 Crypto Futures",
        "fields": ["API Key", "API Secret"],
        "keys":   ["api_key", "api_secret"],
        "has_testnet": True,
        "testnet_url": "https://uat-api.3702.com",
        "info": "Crypto.com Exchange – Spot & Derivate",
    },
    # ── Stocks / CFD ─────────────────────────────────────
    "Alpaca (Stocks)": {
        "engine": "custom", "package": "alpaca-trade-api", "import": "alpaca_trade_api",
        "category": "📈 Stocks / CFD",
        "fields": ["API Key", "API Secret"],
        "keys":   ["api_key", "api_secret"],
        "has_testnet": True,
        "testnet_url": "https://paper-api.alpaca.markets",
        "info": "US Stocks & ETFs – Paper Trading",
    },
    "Interactive Brokers": {
        "engine": "custom", "package": "ib_insync", "import": "ib_insync",
        "category": "📈 Stocks / CFD",
        "fields": ["Host", "Port", "Client ID"],
        "keys":   ["api_key", "api_secret", "passphrase"],
        "has_testnet": True,
        "info": "IB TWS / Gateway Paper Trading",
    },
    "MetaTrader 5": {
        "engine": "custom", "package": "MetaTrader5", "import": "MetaTrader5",
        "category": "📈 Stocks / CFD",
        "fields": ["Login (Kontonummer)", "Passwort", "Server"],
        "keys":   ["api_key", "api_secret", "passphrase"],
        "has_testnet": True,
        "info": "MT5 – Forex, CFD, Aktien",
    },
    "Tradier": {
        "engine": "custom", "package": "requests", "import": "requests",
        "category": "📈 Stocks / CFD",
        "fields": ["API Token"],
        "keys":   ["api_key"],
        "has_testnet": True,
        "testnet_url": "https://sandbox.tradier.com",
        "info": "Tradier US Stocks Broker",
    },
    "RoboForex": {
        "engine": "custom", "package": "MetaTrader5", "import": "MetaTrader5",
        "category": "📈 Stocks / CFD",
        "fields": ["Login (Kontonummer)", "Passwort", "Server"],
        "keys":   ["api_key", "api_secret", "passphrase"],
        "has_testnet": True,
        "testnet_url": "https://my.roboforex.com",
        "info": "RoboForex – Forex, CFD, Krypto (MT5)",
    },
    # ── Prop Trading ────────────────────────────────────
    "FTMO": {
        "engine": "custom", "package": "MetaTrader5", "import": "MetaTrader5",
        "category": "🏆 Prop Trading",
        "fields": ["Login (Kontonummer)", "Passwort", "Server"],
        "keys":   ["api_key", "api_secret", "passphrase"],
        "has_testnet": True,
        "info": "FTMO Prop Trading – Challenge & Funded (MT5)",
    },
}

BROKER_NAMES   = list(BROKERS.keys())
BROKER_CATS    = sorted(set(b["category"] for b in BROKERS.values()))
CCXT_BROKERS   = [n for n, b in BROKERS.items() if b["engine"] == "ccxt"]
CUSTOM_BROKERS = [n for n, b in BROKERS.items() if b["engine"] == "custom"]

# ── Default Profil ───────────────────────────────────────
DEFAULT_PROFILE = {
    "name":              "Mein Profil",
    "telegram_api_id":   "31561693",
    "telegram_api_hash": "76831e21ac32da38129342a94e05ab94",
    "telegram_channel":  "",
    "broker":            "Binance Futures",
    "api_key":           "",
    "api_secret":        "",
    "passphrase":        "",
    "testnet":           True,
    "leverage":          "5",
    "capital":           "100",
    "sl_percent":        "1.5",
    "map_signal_start":  "Signal #",
    "map_long":          "LONG, BUY, KAUFEN",
    "map_short":         "SHORT, SELL, VERKAUFEN",
    "map_pair":          "Pair, Symbol, Coin, Asset",
    "map_entry":         "Entry, Einstieg, Buy at, Sell at",
    "map_tp":            "TP, TakeProfit, Take Profit, Ziel, Target",
    "map_sl":            "SL, StopLoss, Stop Loss, Stop, Absicherung",
    "map_close":         "CLOSED, Close, Exit, Geschlossen, Schließen",
    "map_market":        "MARKET, Markt, MKT",
    "map_limit":         "LIMIT, LMT",
    "tp_enabled":        True,
    "sl_enabled":        True,
    "auto_sl_enabled":   True,
    "tp_distribution":   "33,33,34",
    "trailing_enabled":  False,
    "trailing_percent":  "1.0",
    "trailing_trigger":  "TP1",
    "limit_invalidation_enabled": True,
    "limit_invalidation_percent": "2.0",
}

DEFAULT_CONFIG = {"active_profile": 0, "profiles": [DEFAULT_PROFILE.copy()]}

# Multi-Bot Management: {profile_index: {"process": Popen, "thread": Thread}}
bot_processes = {}
MAX_BOTS = 10


def load_config() -> dict:
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            for p in data.get("profiles", []):
                for k, v in DEFAULT_PROFILE.items():
                    p.setdefault(k, v)
            return data
        except Exception:
            pass
    # Erster Start: Default-Config anlegen
    # Prüfe ob eine default_config.json im Install-Verzeichnis liegt
    install_default = os.path.join(get_install_dir(), "default_config.json")
    if os.path.exists(install_default):
        try:
            with open(install_default, "r", encoding="utf-8") as f:
                data = json.load(f)
            save_config(data)
            return data
        except Exception:
            pass
    default = json.loads(json.dumps(DEFAULT_CONFIG))
    save_config(default)
    return default


def save_config(cfg):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)


# ─────────────────────────────────────────────────────────
class EdgeTraderApp:
    def __init__(self, root):
        self.root    = root
        self.root.title(f"EdgeTrader v{VERSION} – Universal Signal Bot  |  by Philip Babuda")
        self.root.geometry("780x740")
        self.root.minsize(680, 580)
        self.root.configure(bg=BG)
        self.root.resizable(True, True)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.cfg     = load_config()
        self._ensure_profiles()

        # ── Lizenz-Check beim Start ────────────────────────
        init_trial()
        if is_trial_expired() and not is_licensed():
            self._show_license_wall()
            # Trotzdem Update-Check (damit User weiß, dass neue Version da ist)
            self.root.after(3000, self._check_for_updates_silent)
            return
        self._build()
        # Trial-Hinweis im Log anzeigen
        self.root.after(500, self._show_license_status)
        # Update-Check im Hintergrund
        self.root.after(2000, self._check_for_updates)

    def _ensure_profiles(self):
        if not self.cfg.get("profiles"):
            self.cfg["profiles"] = [DEFAULT_PROFILE.copy()]
        self.cfg.setdefault("active_profile", 0)
        for p in self.cfg["profiles"]:
            for k, v in DEFAULT_PROFILE.items():
                p.setdefault(k, v)

    def profile(self) -> dict:
        return self.cfg["profiles"][self.cfg["active_profile"]]

    # ── Scroll-Hilfsmethoden ────────────────────────────────
    def _on_mousewheel(self, event, canvas):
        """Mausrad-Scrolling für Canvas-Widgets."""
        canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _bind_mousewheel(self, widget, canvas):
        """Bindet Mausrad-Scrolling rekursiv an Widget und alle Kinder."""
        widget.bind("<MouseWheel>", lambda e: self._on_mousewheel(e, canvas))
        for child in widget.winfo_children():
            self._bind_mousewheel(child, canvas)

    # ── Layout ────────────────────────────────────────────
    def _build(self):
        hdr = tk.Frame(self.root, bg=BG)
        hdr.pack(fill="x", padx=30, pady=(20,0))
        lft = tk.Frame(hdr, bg=BG); lft.pack(side="left")
        tk.Label(lft, text="⚡ EDGETRADER", font=CF_T, bg=BG, fg=ACCENT).pack(anchor="w")
        tk.Label(lft, text="Universal Signal Bot  |  by Philip Babuda", font=CF, bg=BG, fg=DIM).pack(anchor="w")
        rgt = tk.Frame(hdr, bg=BG); rgt.pack(side="right", anchor="n", pady=4)
        self.dot  = tk.Label(rgt, text="●", font=("Consolas",18), bg=BG, fg=RED)
        self.slbl = tk.Label(rgt, text="GESTOPPT", font=CF_B, bg=BG, fg=RED)
        self.dot.pack(side="right")
        self.slbl.pack(side="right", padx=(0,5))

        # Profil-Leiste
        pbar = tk.Frame(self.root, bg=CARD2)
        pbar.pack(fill="x", padx=30, pady=(8,0))
        tk.Label(pbar, text="  Profil:", font=CF_B, bg=CARD2, fg=DIM).pack(side="left", pady=6)
        self.profile_var  = tk.StringVar()
        self.profile_menu = ttk.Combobox(pbar, textvariable=self.profile_var,
                                          font=CF, width=24, state="readonly")
        self.profile_menu.pack(side="left", padx=8, pady=6)
        self.profile_menu.bind("<<ComboboxSelected>>", self._on_profile_change)
        for txt, cmd, fg in [("＋ Neu", self._new_profile, ACCENT),
                               ("🗑 Löschen", self._delete_profile, RED)]:
            tk.Button(pbar, text=txt, font=CF, bg=CARD, fg=fg,
                      bd=0, relief="flat", cursor="hand2", padx=8, pady=4,
                      command=cmd).pack(side="left", padx=(0,4))
        self._refresh_profile_menu()

        tk.Frame(self.root, bg=ACCENT, height=1).pack(fill="x", padx=30, pady=8)

        tbar = tk.Frame(self.root, bg=BG)
        tbar.pack(fill="x", padx=30, pady=(0,10))
        self.tabs = {}; self.tab_btns = {}
        for name, label in [("dashboard","📊  DASHBOARD"),("bot","▶  BOT"),("settings","⚙️  EINSTELLUNGEN"),("mapping","🗺️  SIGNAL MAP"),("history","📜  TRADES"),("help","📖  HILFE")]:
            btn = tk.Button(tbar, text=label, font=CF_B, bd=0, relief="flat",
                            cursor="hand2", padx=16, pady=6,
                            command=lambda n=name: self._switch_tab(n))
            btn.pack(side="left", padx=(0,4))
            self.tab_btns[name] = btn

        # Lizenz-Button (rechts in der Tab-Leiste)
        lic_info = get_license_info()
        if lic_info["activated"]:
            lic_text = "✅ Lizenziert"
            lic_fg = GREEN
        else:
            lic_text = f"🔑 Trial ({lic_info['trial_days_left']}d)"
            lic_fg = ACCENT
        tk.Button(tbar, text=lic_text, font=CF, bd=0, relief="flat",
                  bg=CARD, fg=lic_fg, cursor="hand2", padx=10, pady=6,
                  command=self._show_activation_dialog).pack(side="right")

        self.content = tk.Frame(self.root, bg=BG)
        self.content.pack(fill="both", expand=True, padx=30)

        self.trade_db = TradeHistory()
        self._build_dashboard_tab()
        self._build_bot_tab()
        self._build_settings_tab()
        self._build_mapping_tab()
        self._build_history_tab()
        self._build_help_tab()
        self._switch_tab("dashboard")

        if lic_info["activated"]:
            plan_lbl = lic_info.get("plan_label", "")
            days_left = lic_info.get("license_days_left", -1)
            lic_status = f"LIZENZIERT ({plan_lbl})" if plan_lbl else "LIZENZIERT"
            if days_left >= 0:
                lic_status += f" – {days_left}d"
        else:
            lic_status = f"TESTVERSION ({lic_info['trial_days_left']} Tage)"
        self.footer_label = tk.Label(self.root,
                 text=f"EdgeTrader v{VERSION} © 2026 by Philip Babuda  |  {lic_status}  |  Alle Rechte vorbehalten",
                 font=("Consolas",7), bg=BG, fg=DIM)
        self.footer_label.pack(pady=(4,6))

    def _switch_tab(self, name):
        for f in self.tabs.values(): f.pack_forget()
        self.tabs[name].pack(fill="both", expand=True)
        for n, btn in self.tab_btns.items():
            btn.configure(bg=ACCENT if n==name else CARD2,
                          fg="#000000" if n==name else DIM)

    # ── Profile ───────────────────────────────────────────
    def _refresh_profile_menu(self):
        names = [p["name"] for p in self.cfg["profiles"]]
        self.profile_menu["values"] = names
        self.profile_menu.current(self.cfg["active_profile"])

    def _on_profile_change(self, _=None):
        self.cfg["active_profile"] = self.profile_menu.current()
        save_config(self.cfg)
        self._load_profile_into_ui()
        self._log(f"Profil gewechselt: {self.profile()['name']}", "warn")

    def _load_profile_into_ui(self):
        p = self.profile()
        self.leverage_var.set(p["leverage"])
        self.capital_var.set(p["capital"])
        self.sl_var.set(p["sl_percent"])
        self.ch_label.configure(text=p["telegram_channel"])
        broker = p.get("broker","Binance Futures")
        b_info = BROKERS.get(broker, {})
        mode = "[Test]" if p["testnet"] else "[LIVE]"
        self.ex_label.configure(text=f"{broker} {mode}")
        self.cat_label.configure(text=b_info.get("category",""))
        for key, var in self.setting_vars.items(): var.set(p.get(key,""))
        self.broker_var.set(broker)
        self.testnet_var.set(p.get("testnet",True))
        self._update_broker_fields()
        for key, var in self.map_vars.items(): var.set(p.get(key,""))
        # Toggles laden
        self.tp_enabled_var.set(p.get("tp_enabled", True))
        self.sl_enabled_var.set(p.get("sl_enabled", True))
        self.auto_sl_enabled_var.set(p.get("auto_sl_enabled", True))
        # TP/Trailing Settings laden
        self.tp_dist_var.set(p.get("tp_distribution", "33,33,34"))
        self.trailing_enabled_var.set(p.get("trailing_enabled", False))
        self.trailing_pct_var.set(p.get("trailing_percent", "1.0"))

    def _new_profile(self):
        win = tk.Toplevel(self.root)
        win.title("Neues Profil"); win.configure(bg=BG)
        win.geometry("300x130"); win.grab_set()
        tk.Label(win, text="Profilname:", font=CF_B, bg=BG, fg=TEXT).pack(pady=(20,4))
        nv = tk.StringVar()
        tk.Entry(win, textvariable=nv, font=CF, bg=CARD2, fg=TEXT,
                 insertbackground=ACCENT, bd=0, relief="flat", width=28).pack()
        def create():
            name = nv.get().strip()
            if not name: return
            np = DEFAULT_PROFILE.copy(); np["name"] = name
            self.cfg["profiles"].append(np)
            self.cfg["active_profile"] = len(self.cfg["profiles"])-1
            save_config(self.cfg)
            self._refresh_profile_menu()
            self.profile_menu.current(self.cfg["active_profile"])
            self._load_profile_into_ui()
            win.destroy()
            self._log(f"✅ Profil erstellt: {name}", "success")
        tk.Button(win, text="Erstellen", font=CF_B, bg=ACCENT, fg="#000",
                  bd=0, relief="flat", cursor="hand2", padx=12, pady=6,
                  command=create).pack(pady=12)

    def _delete_profile(self):
        if len(self.cfg["profiles"]) <= 1:
            messagebox.showwarning("Hinweis","Mindestens ein Profil muss vorhanden sein!"); return
        name = self.profile()["name"]
        if messagebox.askyesno("Löschen", f"Profil '{name}' löschen?"):
            self.cfg["profiles"].pop(self.cfg["active_profile"])
            self.cfg["active_profile"] = 0
            save_config(self.cfg)
            self._refresh_profile_menu()
            self._load_profile_into_ui()
            self._log(f"Profil '{name}' gelöscht.", "warn")

    # ── Bot-Panel Helpers ────────────────────────────────
    def _refresh_bot_rows(self):
        """Aktualisiert das 'Aktive Bots' Panel."""
        if not hasattr(self, 'bots_panel'):
            return
        for w in self.bots_panel.winfo_children():
            w.destroy()
        self.bot_rows = {}

        for i, profile in enumerate(self.cfg["profiles"]):
            row = tk.Frame(self.bots_panel, bg=CARD2, padx=8, pady=4)
            row.pack(fill="x", pady=(0,2))

            is_running = i in bot_processes
            dot_color = GREEN if is_running else RED
            dot = tk.Label(row, text="●", font=("Consolas",12), bg=CARD2, fg=dot_color)
            dot.pack(side="left")

            tk.Label(row, text=f"  {profile['name']}", font=CF_B,
                     bg=CARD2, fg=TEXT).pack(side="left")
            broker = profile.get("broker", "?")
            mode = "Test" if profile.get("testnet", True) else "LIVE"
            tk.Label(row, text=f"  ({broker} {mode})", font=("Consolas",8),
                     bg=CARD2, fg=DIM).pack(side="left")

            if is_running:
                btn = tk.Button(row, text="⏹", font=CF, bg=RED, fg="#000",
                               bd=0, cursor="hand2", padx=8, pady=2,
                               command=lambda idx=i: self.stop_bot(idx))
            else:
                btn = tk.Button(row, text="▶", font=CF, bg=GREEN, fg="#000",
                               bd=0, cursor="hand2", padx=8, pady=2,
                               command=lambda idx=i: self.start_bot(idx))
            btn.pack(side="right")

            self.bot_rows[i] = {"dot": dot, "btn": btn}

        count = len(bot_processes)
        if hasattr(self, 'bot_count_label'):
            self.bot_count_label.configure(text=f"{count}/{MAX_BOTS}")

    def _start_all_bots(self):
        """Startet alle Profile."""
        for i in range(len(self.cfg["profiles"])):
            if i not in bot_processes:
                self.start_bot(i)

    def _stop_all_bots(self):
        """Stoppt alle laufenden Bots."""
        for i in list(bot_processes.keys()):
            self.stop_bot(i)

    # ── DASHBOARD TAB ─────────────────────────────────────
    def _build_dashboard_tab(self):
        f = tk.Frame(self.content, bg=BG)
        self.tabs["dashboard"] = f

        # ── Balance Cards ────────────────────────────────
        bal_row = tk.Frame(f, bg=BG)
        bal_row.pack(fill="x", pady=(0,8))
        for i in range(3): bal_row.columnconfigure(i, weight=1)

        self.dash_balance_lbl   = self._card(bal_row, "💰 Gesamt-Balance", "–", 0)
        self.dash_unrealized_lbl = self._card(bal_row, "📈 Unrealisiert", "–", 1)
        self.dash_pnl_lbl       = self._card(bal_row, "📊 Gesamt P&L", "–", 2)

        # ── Aktive Bots Status ───────────────────────────
        status_header = tk.Frame(f, bg=BG)
        status_header.pack(fill="x", pady=(0,4))
        tk.Label(status_header, text="BOT STATUS", font=CF_B, bg=BG, fg=ACCENT).pack(side="left")
        self.dash_bot_count = tk.Label(status_header, text="0 aktiv", font=CF, bg=BG, fg=DIM)
        self.dash_bot_count.pack(side="right")

        self.dash_bots_frame = tk.Frame(f, bg=CARD, padx=8, pady=4)
        self.dash_bots_frame.pack(fill="x", pady=(0,8))
        tk.Label(self.dash_bots_frame, text="Keine Bots gestartet",
                 font=CF, bg=CARD, fg=DIM, pady=8).pack()

        # ── Offene Positionen ────────────────────────────
        tk.Label(f, text="OFFENE POSITIONEN", font=CF_B, bg=BG, fg=ACCENT).pack(anchor="w", pady=(0,4))

        pos_columns = ("profile", "symbol", "direction", "entry", "size", "unrealized")
        pos_frame = tk.Frame(f, bg=CARD)
        pos_frame.pack(fill="both", expand=True, pady=(0,8))

        style = ttk.Style()
        style.theme_use("clam")
        # Globale Treeview-Basis dunkel machen
        style.configure("Treeview", background=CARD, foreground=TEXT,
                        fieldbackground=CARD, borderwidth=0, font=CF, rowheight=24)
        style.configure("Treeview.Heading", background=CARD2, foreground=ACCENT,
                        font=CF_B, borderwidth=0, relief="flat")
        style.map("Treeview",
                  background=[("selected", CARD2)],
                  foreground=[("selected", TEXT)])
        # Scrollbar dunkel
        style.configure("Vertical.TScrollbar",
                        background=CARD2, troughcolor=CARD, borderwidth=0,
                        arrowcolor=DIM, relief="flat")
        style.map("Vertical.TScrollbar",
                  background=[("active", ACCENT), ("pressed", ACCENT)])
        # Dashboard-Treeview
        style.configure("Dash.Treeview",
                        background=CARD, foreground=TEXT, fieldbackground=CARD,
                        font=CF, rowheight=24, borderwidth=0)
        style.configure("Dash.Treeview.Heading",
                        background=CARD2, foreground=ACCENT, font=CF_B,
                        borderwidth=0, relief="flat")
        style.map("Dash.Treeview",
                  background=[("selected", CARD2)],
                  foreground=[("selected", TEXT)])

        self.positions_tree = ttk.Treeview(pos_frame, columns=pos_columns,
                                            show="headings", height=8, style="Dash.Treeview")
        for col_id, heading, width in [
            ("profile",   "Profil",     100),
            ("symbol",    "Symbol",      90),
            ("direction", "Richtung",    70),
            ("entry",     "Entry",       90),
            ("size",      "Größe",       80),
            ("unrealized","P&L",         90),
        ]:
            self.positions_tree.heading(col_id, text=heading)
            self.positions_tree.column(col_id, width=width, minwidth=50)

        self.positions_tree.tag_configure("profit", foreground=GREEN)
        self.positions_tree.tag_configure("loss", foreground=RED)

        pos_scroll = ttk.Scrollbar(pos_frame, orient="vertical",
                                    command=self.positions_tree.yview)
        self.positions_tree.configure(yscrollcommand=pos_scroll.set)
        self.positions_tree.pack(side="left", fill="both", expand=True)
        pos_scroll.pack(side="right", fill="y")

        # ── Close-Button ────────────────────────────────
        close_btn_frame = tk.Frame(f, bg=BG)
        close_btn_frame.pack(fill="x", pady=(0,4))
        tk.Button(close_btn_frame, text="❌  POSITION SCHLIESSEN",
                  font=CF_B, bg=RED, fg="#fff", activebackground="#dc2626",
                  bd=0, relief="flat", cursor="hand2", padx=16, pady=6,
                  command=self._close_selected_position).pack(side="left")
        tk.Button(close_btn_frame, text="🔄  AKTUALISIEREN",
                  font=CF_B, bg=BLUE, fg="#000", activebackground="#2563eb",
                  bd=0, relief="flat", cursor="hand2", padx=16, pady=6,
                  command=self._dashboard_refresh).pack(side="right")

        # ── Statistiken (aus Trade History) ───────────────
        stats_row = tk.Frame(f, bg=BG)
        stats_row.pack(fill="x", pady=(0,4))
        for i in range(4): stats_row.columnconfigure(i, weight=1)

        self.dash_stat_trades = self._stat_card(stats_row, "Trades", "0", 0)
        self.dash_stat_winrate = self._stat_card(stats_row, "Win Rate", "0%", 1)
        self.dash_stat_avgwin = self._stat_card(stats_row, "Ø Gewinn", "–", 2)
        self.dash_stat_avgloss = self._stat_card(stats_row, "Ø Verlust", "–", 3)

        # ── Auto-Refresh starten ─────────────────────────
        self._dashboard_refresh()

    def _close_selected_position(self):
        """Schließt die im Dashboard selektierte Position per Market-Order."""
        sel = self.positions_tree.selection()
        if not sel:
            messagebox.showwarning("Keine Auswahl", "Bitte wähle eine Position in der Tabelle aus.")
            return

        values = self.positions_tree.item(sel[0], "values")
        if not values or len(values) < 2:
            return

        profile_name = values[0]
        symbol = values[1]

        if not messagebox.askyesno("Position schließen",
                f"Möchtest du {symbol} ({profile_name}) per Marktpreis schließen?\n\n"
                f"Alle offenen Orders für {symbol} werden gecancelt."):
            return

        def do_close():
            try:
                # Passendes Profil finden
                target_profile = None
                for p in self.cfg.get("profiles", []):
                    if p.get("name", "") == profile_name:
                        target_profile = p
                        break
                if not target_profile:
                    target_profile = self.profile()

                # Binance Client erstellen
                from binance.client import Client
                from binance.enums import SIDE_BUY, SIDE_SELL, ORDER_TYPE_MARKET
                testnet = target_profile.get("testnet", True)
                client = Client(
                    target_profile["api_key"],
                    target_profile["api_secret"],
                    testnet=testnet)
                if testnet:
                    client.FUTURES_URL = "https://testnet.binancefuture.com/fapi"

                # Position schließen
                exit_price = None
                closed = False
                for pos in client.futures_position_information(symbol=symbol):
                    qty = float(pos["positionAmt"])
                    if qty == 0:
                        continue
                    side = SIDE_SELL if qty > 0 else SIDE_BUY
                    try:
                        exit_price = float(client.futures_symbol_ticker(symbol=symbol)["price"])
                    except Exception:
                        pass
                    client.futures_create_order(
                        symbol=symbol, side=side,
                        type=ORDER_TYPE_MARKET,
                        quantity=abs(qty), reduceOnly=True)
                    closed = True

                # Offene Orders canceln (TP/SL)
                try:
                    client.futures_cancel_all_open_orders(symbol=symbol)
                except Exception:
                    pass

                # Trade in DB als geschlossen markieren
                self.trade_db.record_close_by_symbol(symbol, exit_price, "MANUAL_CLOSE")

                if closed:
                    self.root.after(0, lambda: self._log(
                        f"🔒 {symbol} manuell geschlossen @ ~{exit_price}", "warn"))
                    self.root.after(0, lambda: messagebox.showinfo(
                        "Geschlossen", f"{symbol} wurde per Marktpreis geschlossen."))
                else:
                    self.root.after(0, lambda: messagebox.showinfo(
                        "Keine Position", f"Keine offene Position für {symbol} gefunden."))

                # Dashboard aktualisieren
                self.root.after(500, self._dashboard_refresh)

            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror(
                    "Fehler", f"Position konnte nicht geschlossen werden:\n{e}"))
                self.root.after(0, lambda: self._log(f"❌ Close Fehler: {e}", "error"))

        threading.Thread(target=do_close, daemon=True).start()

    def _dashboard_refresh(self):
        """Aktualisiert Dashboard-Daten alle 30 Sekunden."""
        threading.Thread(target=self._fetch_dashboard_data, daemon=True).start()
        self.root.after(30000, self._dashboard_refresh)

    def _fetch_dashboard_data(self):
        """Holt Balance und Positionen von allen laufenden Brokern."""
        total_balance = 0
        total_unrealized = 0
        positions = []
        bot_statuses = []

        for idx in list(bot_processes.keys()):
            if idx >= len(self.cfg["profiles"]):
                continue
            p = self.cfg["profiles"][idx]
            pname = p.get("name", "?")
            broker = p.get("broker", "?")
            bot_statuses.append({"name": pname, "broker": broker, "index": idx})

            try:
                if broker == "Binance Futures":
                    from binance.client import Client as BClient
                    c = BClient(p["api_key"], p["api_secret"], testnet=p.get("testnet", True))
                    bal = c.futures_account_balance()
                    usdt = next((float(b["balance"]) for b in bal if b["asset"]=="USDT"), 0)
                    total_balance += usdt

                    for pos in c.futures_position_information():
                        qty = float(pos["positionAmt"])
                        if qty == 0: continue
                        unrealized = float(pos["unRealizedProfit"])
                        total_unrealized += unrealized
                        positions.append({
                            "profile": pname,
                            "symbol": pos["symbol"],
                            "direction": "LONG" if qty > 0 else "SHORT",
                            "entry": float(pos["entryPrice"]),
                            "size": abs(qty),
                            "unrealized": unrealized,
                        })
            except Exception:
                pass

        # Trade-Statistiken
        stats = self.trade_db.get_statistics()

        # UI auf Main-Thread aktualisieren
        self.root.after(0, self._update_dashboard_ui,
                       total_balance, total_unrealized, positions, bot_statuses, stats)

    def _update_dashboard_ui(self, balance, unrealized, positions, bot_statuses, stats):
        """Aktualisiert alle Dashboard-Widgets."""
        # Balance Cards
        self.dash_balance_lbl.configure(text=f"{balance:.2f} USDT")
        ur_color = GREEN if unrealized >= 0 else RED
        self.dash_unrealized_lbl.configure(
            text=f"{'+' if unrealized>0 else ''}{unrealized:.2f} USDT", fg=ur_color)

        pnl = stats.get("total_pnl", 0)
        pnl_color = GREEN if pnl >= 0 else RED
        self.dash_pnl_lbl.configure(
            text=f"{'+' if pnl>0 else ''}{pnl:.2f} USDT", fg=pnl_color)

        # Bot Status
        for w in self.dash_bots_frame.winfo_children():
            w.destroy()
        count = len(bot_statuses)
        self.dash_bot_count.configure(text=f"{count} aktiv")

        if count == 0:
            tk.Label(self.dash_bots_frame, text="Keine Bots gestartet – gehe zum BOT Tab",
                     font=CF, bg=CARD, fg=DIM, pady=8).pack()
        else:
            for bs in bot_statuses:
                row = tk.Frame(self.dash_bots_frame, bg=CARD2, padx=8, pady=4)
                row.pack(fill="x", pady=(0,2))
                tk.Label(row, text="●", font=("Consolas",10), bg=CARD2, fg=GREEN).pack(side="left")
                tk.Label(row, text=f"  {bs['name']}  ({bs['broker']})",
                         font=CF, bg=CARD2, fg=TEXT).pack(side="left")

        # Positionen Tabelle
        for item in self.positions_tree.get_children():
            self.positions_tree.delete(item)

        for pos in positions:
            tag = "profit" if pos["unrealized"] >= 0 else "loss"
            self.positions_tree.insert("", "end", values=(
                pos["profile"], pos["symbol"], pos["direction"],
                f"{pos['entry']:.2f}", f"{pos['size']}", f"{pos['unrealized']:.2f}"
            ), tags=(tag,))

        # Statistiken
        self.dash_stat_trades.configure(text=str(stats.get("total_trades", 0)))
        self.dash_stat_winrate.configure(text=f"{stats.get('win_rate', 0):.1f}%")
        avg_win = stats.get("avg_win", 0)
        self.dash_stat_avgwin.configure(
            text=f"+{avg_win:.2f}" if avg_win > 0 else "–", fg=GREEN if avg_win > 0 else DIM)
        avg_loss = stats.get("avg_loss", 0)
        self.dash_stat_avgloss.configure(
            text=f"{avg_loss:.2f}" if avg_loss < 0 else "–", fg=RED if avg_loss < 0 else DIM)

    # ── BOT TAB ───────────────────────────────────────────
    def _build_bot_tab(self):
        f = tk.Frame(self.content, bg=BG)
        self.tabs["bot"] = f
        p = self.profile()

        cards = tk.Frame(f, bg=BG)
        cards.pack(fill="x", pady=(0,8))
        for i in range(3): cards.columnconfigure(i, weight=1)

        self.ch_label  = self._card(cards, "📡 Kanal", p["telegram_channel"], 0)
        broker = p.get("broker","Binance Futures")
        self.ex_label  = self._card(cards, "🏦 Broker",
                                     f"{broker} {'[Test]' if p['testnet'] else '[LIVE]'}", 1)
        b_info = BROKERS.get(broker,{})
        self.cat_label = self._card(cards, "📂 Kategorie", b_info.get("category",""), 2)

        edit = tk.Frame(f, bg=BG)
        edit.pack(fill="x", pady=(0,6))
        for i in range(3): edit.columnconfigure(i, weight=1)
        self.leverage_var = tk.StringVar(value=p["leverage"])
        self.capital_var  = tk.StringVar(value=p["capital"])
        self.sl_var       = tk.StringVar(value=p["sl_percent"])
        self._edit_card(edit, "⚙️  Hebel",         self.leverage_var, "× Margin", 0)
        self._edit_card(edit, "💰 Kapital / Trade", self.capital_var,  "USDT",     1)
        self._edit_card(edit, "🛑 Stop Loss",       self.sl_var,       "% Entry",  2)

        tk.Label(f, text="ℹ️  LONG: SL = Entry − SL%   |   SHORT: SL = Entry + SL%",
                 font=("Consolas",8), bg=BG, fg=DIM).pack(anchor="w", pady=(0,4))

        # ── Toggles (TP/SL an/aus) ─────────────────────
        toggles = tk.Frame(f, bg=CARD2, padx=12, pady=8)
        toggles.pack(fill="x", pady=(0,6))
        tk.Label(toggles, text="Funktionen:", font=CF_B, bg=CARD2, fg=DIM).pack(side="left")

        self.tp_enabled_var = tk.BooleanVar(value=p.get("tp_enabled", True))
        tk.Checkbutton(toggles, text="Take Profit", variable=self.tp_enabled_var,
                       font=CF, bg=CARD2, fg=GREEN, selectcolor=CARD,
                       activebackground=CARD2).pack(side="left", padx=(12,0))

        self.sl_enabled_var = tk.BooleanVar(value=p.get("sl_enabled", True))
        tk.Checkbutton(toggles, text="Stop Loss", variable=self.sl_enabled_var,
                       font=CF, bg=CARD2, fg=GREEN, selectcolor=CARD,
                       activebackground=CARD2).pack(side="left", padx=(12,0))

        self.auto_sl_enabled_var = tk.BooleanVar(value=p.get("auto_sl_enabled", True))
        tk.Checkbutton(toggles, text="Auto SL (%)", variable=self.auto_sl_enabled_var,
                       font=CF, bg=CARD2, fg=GREEN, selectcolor=CARD,
                       activebackground=CARD2).pack(side="left", padx=(12,0))

        # ── Aktive Bots Panel ──────────────────────────────
        bots_header = tk.Frame(f, bg=BG)
        bots_header.pack(fill="x", pady=(0,2))
        tk.Label(bots_header, text="AKTIVE BOTS", font=CF_B, bg=BG, fg=ACCENT).pack(side="left")
        self.bot_count_label = tk.Label(bots_header, text="0/10", font=CF, bg=BG, fg=DIM)
        self.bot_count_label.pack(side="right")

        self.bots_panel = tk.Frame(f, bg=CARD, padx=4, pady=4)
        self.bots_panel.pack(fill="x", pady=(0,6))
        self.bot_rows = {}
        self._refresh_bot_rows()

        # ── Live Log ──────────────────────────────────────
        lf = tk.Frame(f, bg=CARD)
        lf.pack(fill="both", expand=True, pady=(0,8))
        tk.Label(lf, text="  LIVE LOG", font=CF_B, bg=CARD, fg=DIM, anchor="w").pack(fill="x", pady=(8,0))
        self.log_box = scrolledtext.ScrolledText(
            lf, font=("Consolas",9), bg=CARD, fg=TEXT,
            insertbackground=ACCENT, borderwidth=0, relief="flat",
            state="disabled", height=7, wrap="word")
        self.log_box.pack(fill="both", expand=True, padx=8, pady=(0,8))
        for tag, col in [("info",TEXT),("success",GREEN),("error",RED),("warn",ACCENT),("dim",DIM)]:
            self.log_box.tag_config(tag, foreground=col)

        bf = tk.Frame(f, bg=BG)
        bf.pack(fill="x", pady=(0,6))
        self.start_btn = tk.Button(bf, text="▶  PROFIL STARTEN", font=CF_L,
            bg=GREEN, fg="#000", activebackground="#16a34a",
            bd=0, relief="flat", cursor="hand2", padx=20, pady=10,
            command=self.start_bot)
        self.start_btn.pack(side="left", expand=True, fill="x", padx=(0,4))
        self.stop_btn = tk.Button(bf, text="⏹  STOPPEN", font=CF_L,
            bg=CARD, fg=DIM, bd=0, relief="flat", cursor="hand2",
            padx=20, pady=10, state="disabled", command=self.stop_bot)
        self.stop_btn.pack(side="left", expand=True, fill="x", padx=(0,4))
        tk.Button(bf, text="▶▶  ALLE", font=CF_B,
            bg=CARD2, fg=GREEN, bd=0, relief="flat", cursor="hand2",
            padx=12, pady=10, command=self._start_all_bots).pack(side="left", padx=(0,4))
        tk.Button(bf, text="⏹⏹  ALLE", font=CF_B,
            bg=CARD2, fg=RED, bd=0, relief="flat", cursor="hand2",
            padx=12, pady=10, command=self._stop_all_bots).pack(side="left")

        self._log(f"EdgeTrader geladen – {len(BROKERS)} Broker verfügbar", "dim")
        self._log(f"Aktives Profil: {self.profile()['name']}", "dim")

    # ── SETTINGS TAB ──────────────────────────────────────
    def _build_settings_tab(self):
        f = tk.Frame(self.content, bg=BG)
        self.tabs["settings"] = f
        p = self.profile()

        # Scrollbar für Settings
        canvas = tk.Canvas(f, bg=BG, highlightthickness=0)
        scrollbar = ttk.Scrollbar(f, orient="vertical", command=canvas.yview)
        self.settings_inner = tk.Frame(canvas, bg=BG)
        self.settings_inner.bind("<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        settings_win_id = canvas.create_window((0,0), window=self.settings_inner, anchor="nw")
        # Canvas-Breite synchronisieren
        canvas.bind("<Configure>",
            lambda e: canvas.itemconfig(settings_win_id, width=e.width))
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self.settings_canvas = canvas

        si = self.settings_inner

        # ── Telegram ────────────────────────────────────
        self._section(si, "TELEGRAM")
        self.setting_vars = {}

        # Kanal / Bot – das Hauptfeld, das jeder User braucht
        var = self._settings_row(si, "Kanal / Bot", p.get("telegram_channel",""), secret=False)
        self.setting_vars["telegram_channel"] = var

        # Erweitert-Button (API ID & Hash versteckt)
        self.tg_advanced_frame = tk.Frame(si, bg=BG)
        self.tg_advanced_frame.pack(fill="x", pady=(2,0))
        self.tg_advanced_visible = False
        self.tg_advanced_btn = tk.Label(
            self.tg_advanced_frame, text="▶ Erweitert (API-Zugangsdaten)",
            font=CF, bg=BG, fg=DIM, cursor="hand2")
        self.tg_advanced_btn.pack(anchor="w", padx=4)
        self.tg_advanced_btn.bind("<Button-1>", self._toggle_tg_advanced)

        # Versteckter Bereich für API ID & Hash
        self.tg_advanced_content = tk.Frame(si, bg=BG)
        for label, key in [("API ID","telegram_api_id"),
                            ("API Hash","telegram_api_hash")]:
            var = self._settings_row(self.tg_advanced_content, label,
                                      p.get(key, DEFAULT_PROFILE.get(key,"")), secret=False)
            self.setting_vars[key] = var
        # Hinweis
        tk.Label(self.tg_advanced_content,
                 text="ℹ️ Vorausgefüllt – nur ändern wenn du eigene App-Credentials nutzen willst.",
                 font=("Segoe UI", 8), bg=BG, fg=DIM, anchor="w").pack(fill="x", padx=16, pady=(0,4))
        # Standardmäßig versteckt
        self.tg_advanced_content.pack_forget()

        # ── Broker Auswahl ───────────────────────────────
        self._section(si, "BROKER AUSWAHL")

        # Kategorie Filter
        cat_row = tk.Frame(si, bg=BG)
        cat_row.pack(fill="x", pady=(0,4))
        tk.Label(cat_row, text="Filter:", font=CF_B, bg=BG, fg=DIM).pack(side="left")
        self.cat_filter_var = tk.StringVar(value="Alle")
        cat_values = ["Alle"] + BROKER_CATS
        cat_filter = ttk.Combobox(cat_row, textvariable=self.cat_filter_var,
                                   values=cat_values, font=CF, width=20, state="readonly")
        cat_filter.pack(side="left", padx=8)
        cat_filter.bind("<<ComboboxSelected>>", self._filter_brokers)

        broker_row = tk.Frame(si, bg=CARD2, padx=12, pady=8)
        broker_row.pack(fill="x", pady=(0,4))
        tk.Label(broker_row, text="Exchange", font=CF_B, bg=CARD2, fg=DIM, width=14, anchor="w").pack(side="left")

        self.broker_var = tk.StringVar(value=p.get("broker","Binance Futures"))
        self.broker_combo = ttk.Combobox(broker_row, textvariable=self.broker_var,
                                          values=BROKER_NAMES, font=CF, width=26, state="readonly")
        self.broker_combo.pack(side="left", padx=(8,10))
        self.broker_combo.bind("<<ComboboxSelected>>", lambda _: self._update_broker_fields())

        # Broker Info Label
        self.broker_info_label = tk.Label(broker_row, text="", font=("Consolas",8),
                                           bg=CARD2, fg=DIM)
        self.broker_info_label.pack(side="left")

        # Install Button
        self.install_frame = tk.Frame(si, bg=BG)
        self.install_frame.pack(fill="x", pady=(0,4))
        self.install_btn = tk.Button(self.install_frame,
            text="📦 Bibliothek installieren", font=CF,
            bg=CARD, fg=ACCENT, bd=0, relief="flat", cursor="hand2",
            padx=10, pady=5, command=self._install_broker_package)
        self.install_btn.pack(side="left")
        self.ccxt_status = tk.Label(self.install_frame, text="", font=CF, bg=BG, fg=DIM)
        self.ccxt_status.pack(side="left", padx=10)

        # Dynamische Broker-Felder
        self.broker_fields_frame = tk.Frame(si, bg=BG)
        self.broker_fields_frame.pack(fill="x", pady=(0,4))
        self.broker_field_vars = {}
        self._update_broker_fields()

        # ── Modus ────────────────────────────────────────
        self._section(si, "MODUS")
        mode_row = tk.Frame(si, bg=CARD2, padx=12, pady=8)
        mode_row.pack(fill="x", pady=(0,4))
        self.testnet_var = tk.BooleanVar(value=p.get("testnet",True))
        tk.Radiobutton(mode_row, text="📋 Testnet / Paper Trading",
                       variable=self.testnet_var, value=True, font=CF,
                       bg=CARD2, fg=GREEN, selectcolor=CARD,
                       activebackground=CARD2).pack(side="left", padx=(0,16))
        tk.Radiobutton(mode_row, text="🔴 Live Trading (echtes Geld!)",
                       variable=self.testnet_var, value=False, font=CF,
                       bg=CARD2, fg=RED, selectcolor=CARD,
                       activebackground=CARD2).pack(side="left")

        # Testnet Link
        self.testnet_link = tk.Label(si, text="", font=("Consolas",8),
                                      bg=BG, fg=BLUE, cursor="hand2")
        self.testnet_link.pack(anchor="w", pady=(0,6))

        # ── Take Profit Verteilung ────────────────────────
        self._section(si, "TAKE PROFIT VERTEILUNG")
        tp_dist_row = tk.Frame(si, bg=CARD2, padx=12, pady=8)
        tp_dist_row.pack(fill="x", pady=(0,4))
        tk.Label(tp_dist_row, text="TP Verteilung (%)", font=CF_B,
                 bg=CARD2, fg=DIM, width=18, anchor="w").pack(side="left")
        self.tp_dist_var = tk.StringVar(value=p.get("tp_distribution", "33,33,34"))
        tk.Entry(tp_dist_row, textvariable=self.tp_dist_var, font=CF, bg=CARD, fg=TEXT,
                 insertbackground=ACCENT, bd=0, relief="flat", width=20).pack(side="left", padx=8)
        tk.Label(tp_dist_row, text="z.B. 33,33,34 = 3 TPs  |  50,50 = 2 TPs  |  100 = 1 TP",
                 font=("Consolas",8), bg=CARD2, fg=DIM).pack(side="left")

        # ── Trailing Take Profit ─────────────────────────
        self._section(si, "TRAILING TAKE PROFIT")
        trail_row = tk.Frame(si, bg=CARD2, padx=12, pady=8)
        trail_row.pack(fill="x", pady=(0,4))
        self.trailing_enabled_var = tk.BooleanVar(value=p.get("trailing_enabled", False))
        tk.Checkbutton(trail_row, text="Trailing TP aktivieren",
                       variable=self.trailing_enabled_var,
                       font=CF, bg=CARD2, fg=GREEN, selectcolor=CARD,
                       activebackground=CARD2).pack(side="left")
        tk.Label(trail_row, text="  Trail %:", font=CF, bg=CARD2, fg=DIM).pack(side="left", padx=(16,0))
        self.trailing_pct_var = tk.StringVar(value=p.get("trailing_percent", "1.0"))
        tk.Entry(trail_row, textvariable=self.trailing_pct_var, font=CF, bg=CARD, fg=TEXT,
                 insertbackground=ACCENT, bd=0, relief="flat", width=6).pack(side="left", padx=4)
        tk.Label(trail_row, text="%", font=CF, bg=CARD2, fg=DIM).pack(side="left")
        tk.Label(si, text="ℹ️  Wenn TP1 erreicht wird, verfolgt der Bot den Preis und schließt bei Rückfall um X%",
                 font=("Consolas",8), bg=BG, fg=DIM).pack(anchor="w", pady=(0,6))

        # ── Limit-Order Verwaltung ──────────────────────
        self._section(si, "LIMIT-ORDER VERWALTUNG")
        lim_row = tk.Frame(si, bg=CARD2, padx=12, pady=8)
        lim_row.pack(fill="x", pady=(0,4))
        self.limit_inv_enabled_var = tk.BooleanVar(value=p.get("limit_invalidation_enabled", True))
        tk.Checkbutton(lim_row, text="Auto-Cancel wenn Markt zu weit weg",
                       variable=self.limit_inv_enabled_var,
                       font=CF, bg=CARD2, fg=GREEN, selectcolor=CARD,
                       activebackground=CARD2).pack(side="left")
        tk.Label(lim_row, text="  Toleranz:", font=CF, bg=CARD2, fg=DIM).pack(side="left", padx=(16,0))
        self.limit_inv_pct_var = tk.StringVar(value=p.get("limit_invalidation_percent", "2.0"))
        tk.Entry(lim_row, textvariable=self.limit_inv_pct_var, font=CF, bg=CARD, fg=TEXT,
                 insertbackground=ACCENT, bd=0, relief="flat", width=6).pack(side="left", padx=4)
        tk.Label(lim_row, text="%", font=CF, bg=CARD2, fg=DIM).pack(side="left")
        tk.Label(si, text="ℹ️  Offene LIMIT-Orders werden gecancelt wenn der Marktpreis > X% vom Entry abweicht",
                 font=("Consolas",8), bg=BG, fg=DIM).pack(anchor="w", pady=(0,6))

        # ── Verbindungstest ──────────────────────────────
        self._section(si, "VERBINDUNGSTEST")

        # Status Anzeige
        status_grid = tk.Frame(si, bg=BG)
        status_grid.pack(fill="x", pady=(0,6))
        status_grid.columnconfigure(0, weight=1)
        status_grid.columnconfigure(1, weight=1)

        # Telegram Status Card
        tg_card = tk.Frame(status_grid, bg=CARD2, padx=12, pady=10)
        tg_card.grid(row=0, column=0, padx=(0,4), sticky="ew")
        tk.Label(tg_card, text="📡 Telegram API", font=CF_B, bg=CARD2, fg=TEXT).pack(anchor="w")
        self.tg_status_dot   = tk.Label(tg_card, text="●  Nicht getestet",
                                         font=CF, bg=CARD2, fg=DIM)
        self.tg_status_dot.pack(anchor="w", pady=(4,0))
        self.tg_status_info  = tk.Label(tg_card, text="", font=("Consolas",8),
                                         bg=CARD2, fg=DIM, wraplength=280, justify="left")
        self.tg_status_info.pack(anchor="w")

        # Broker Status Card
        br_card = tk.Frame(status_grid, bg=CARD2, padx=12, pady=10)
        br_card.grid(row=0, column=1, padx=(4,0), sticky="ew")
        tk.Label(br_card, text="🏦 Broker API", font=CF_B, bg=CARD2, fg=TEXT).pack(anchor="w")
        self.br_status_dot   = tk.Label(br_card, text="●  Nicht getestet",
                                         font=CF, bg=CARD2, fg=DIM)
        self.br_status_dot.pack(anchor="w", pady=(4,0))
        self.br_status_info  = tk.Label(br_card, text="", font=("Consolas",8),
                                         bg=CARD2, fg=DIM, wraplength=280, justify="left")
        self.br_status_info.pack(anchor="w")

        # Test Button
        self.test_btn = tk.Button(si, text="🔌  VERBINDUNG TESTEN",
            font=CF_L, bg=BLUE, fg="#000", activebackground="#2563eb",
            bd=0, relief="flat", cursor="hand2", padx=20, pady=10,
            command=self._test_connections)
        self.test_btn.pack(fill="x", pady=(0,8))

        # ── Buttons ──────────────────────────────────────
        bf = tk.Frame(si, bg=BG)
        bf.pack(fill="x", pady=(0,4))
        tk.Button(bf, text="💾  SPEICHERN", font=CF_L,
                  bg=ACCENT, fg="#000", activebackground="#d97706",
                  bd=0, relief="flat", cursor="hand2", padx=20, pady=10,
                  command=self.save_settings).pack(side="left", expand=True, fill="x", padx=(0,8))
        tk.Button(bf, text="↩  ZURÜCKSETZEN", font=CF_L, bg=CARD, fg=DIM,
                  bd=0, relief="flat", cursor="hand2", padx=20, pady=10,
                  command=self.reset_settings).pack(side="left", expand=True, fill="x")

        # Mausrad-Scrolling binden
        self._bind_mousewheel(self.settings_inner, self.settings_canvas)

    def _section(self, parent, title):
        tk.Frame(parent, bg=ACCENT, height=1).pack(fill="x", pady=(8,4))
        tk.Label(parent, text=f"  {title}", font=CF_B, bg=BG, fg=ACCENT).pack(anchor="w", pady=(0,2))

    def _settings_row(self, parent, label, value, secret=False):
        row = tk.Frame(parent, bg=CARD2, padx=12, pady=7)
        row.pack(fill="x", pady=(0,3))
        tk.Label(row, text=label, font=CF_B, bg=CARD2, fg=DIM, width=14, anchor="w").pack(side="left")
        var = tk.StringVar(value=value)
        tk.Entry(row, textvariable=var, font=CF, bg=CARD, fg=TEXT,
                 insertbackground=ACCENT, bd=0, relief="flat",
                 show="*" if secret else "", width=50).pack(
                     side="left", padx=(8,0), fill="x", expand=True)
        return var

    def _toggle_tg_advanced(self, _=None):
        """Telegram Erweitert-Bereich ein-/ausklappen."""
        if self.tg_advanced_visible:
            self.tg_advanced_content.pack_forget()
            self.tg_advanced_btn.configure(text="▶ Erweitert (API-Zugangsdaten)")
            self.tg_advanced_visible = False
        else:
            # Nach dem Button-Frame einfügen
            self.tg_advanced_content.pack(fill="x", pady=(0,4),
                                          after=self.tg_advanced_frame)
            self.tg_advanced_btn.configure(text="▼ Erweitert (API-Zugangsdaten)")
            self.tg_advanced_visible = True

    def _filter_brokers(self, _=None):
        cat = self.cat_filter_var.get()
        if cat == "Alle":
            filtered = BROKER_NAMES
        else:
            filtered = [n for n, b in BROKERS.items() if b["category"] == cat]
        self.broker_combo["values"] = filtered
        if self.broker_var.get() not in filtered:
            self.broker_var.set(filtered[0])
            self._update_broker_fields()

    def _update_broker_fields(self):
        for w in self.broker_fields_frame.winfo_children(): w.destroy()
        self.broker_field_vars = {}
        broker_name = self.broker_var.get()
        broker      = BROKERS.get(broker_name, BROKERS["Binance Futures"])
        p           = self.profile()

        # Info
        self.broker_info_label.configure(text=broker.get("info",""))

        # Testnet Link (nur aktualisieren wenn Widget bereits existiert)
        if hasattr(self, "testnet_link"):
            testnet_url = broker.get("testnet_url","")
            if testnet_url:
                self.testnet_link.configure(text=f"🔗 Testnet: {testnet_url}")
            else:
                self.testnet_link.configure(text="ℹ️  Kein offizielles Testnet verfügbar")

        # API Felder
        for label, key in zip(broker["fields"], broker["keys"]):
            row = tk.Frame(self.broker_fields_frame, bg=CARD2, padx=12, pady=7)
            row.pack(fill="x", pady=(0,3))
            tk.Label(row, text=label, font=CF_B, bg=CARD2, fg=DIM, width=14, anchor="w").pack(side="left")
            var = tk.StringVar(value=p.get(key,""))
            tk.Entry(row, textvariable=var, font=CF, bg=CARD, fg=TEXT,
                     insertbackground=ACCENT, bd=0, relief="flat",
                     show="*", width=50).pack(side="left", padx=(8,0), fill="x", expand=True)
            self.broker_field_vars[key] = var

        # Install Button anpassen
        if broker["engine"] == "ccxt":
            pkg = "ccxt"
            imp = "ccxt"
        else:
            pkg = broker.get("package","")
            imp = broker.get("import","")

        try:
            mod = __import__(imp)
            ver = getattr(mod, "__version__", "")
            ver_str = f"v{ver}" if ver else ""
            self.install_btn.configure(
                text=f"✅ {broker_name} – bereit {ver_str}".strip(),
                fg=GREEN, state="disabled")
            self.ccxt_status.configure(text="", fg=DIM)
        except ImportError:
            self.install_btn.configure(
                text=f"📦 {broker_name} – Bibliothek installieren",
                fg=ACCENT, state="normal")
            self.ccxt_status.configure(text="⚠️ Nicht installiert", fg=RED)

        # Mausrad-Scrolling für neu erstellte Widgets binden
        if hasattr(self, 'settings_canvas'):
            self._bind_mousewheel(self.broker_fields_frame, self.settings_canvas)

    def _install_broker_package(self):
        broker_name = self.broker_var.get()
        broker      = BROKERS[broker_name]
        package     = "ccxt" if broker["engine"] == "ccxt" else broker.get("package","")

        # ── Bestätigung einholen ─────────────────────────
        confirmed = messagebox.askyesno(
            "📦 Bibliothek installieren",
            f"Für '{broker_name}' wird folgende Python-Bibliothek benötigt:\n\n"
            f"  → {package}\n\n"
            f"Jetzt installieren?"
        )
        if not confirmed:
            self._log(f"Installation von {package} abgebrochen.", "dim")
            return

        # ── Installation starten ─────────────────────────
        self._switch_tab("bot")
        self._log(f"📦 Installiere {package} für {broker_name}...", "warn")
        self.install_btn.configure(text="⏳ Wird installiert...", state="disabled")

        def do_install():
            try:
                subprocess.check_call(
                    [sys.executable, "-m", "pip", "install", package,
                     "--break-system-packages"],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                self.root.after(0, lambda: self._log(
                    f"✅ {package} für {broker_name} erfolgreich installiert!", "success"))
                self.root.after(0, self._update_broker_fields)
            except Exception:
                try:
                    subprocess.check_call(
                        [sys.executable, "-m", "pip", "install", package],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    self.root.after(0, lambda: self._log(
                        f"✅ {package} für {broker_name} installiert!", "success"))
                    self.root.after(0, self._update_broker_fields)
                except Exception as e2:
                    self.root.after(0, lambda: self._log(
                        f"❌ Installation fehlgeschlagen: {e2}", "error"))
                    self.root.after(0, lambda: self.install_btn.configure(
                        text=f"📦 {package} installieren", fg=ACCENT, state="normal"))

        threading.Thread(target=do_install, daemon=True).start()

    # ── Verbindungstest ───────────────────────────────────
    def _test_connections(self):
        """Testet Telegram und Broker API gleichzeitig."""
        self.test_btn.configure(text="⏳ Teste...", state="disabled")
        self.tg_status_dot.configure(text="● Teste...", fg=ACCENT)
        self.br_status_dot.configure(text="● Teste...", fg=ACCENT)
        self.tg_status_info.configure(text="")
        self.br_status_info.configure(text="")

        # Aktuelle Werte aus den Feldern lesen (noch nicht gespeichert)
        tg_id   = self.setting_vars.get("telegram_api_id",   tk.StringVar()).get().strip()
        tg_hash = self.setting_vars.get("telegram_api_hash", tk.StringVar()).get().strip()
        api_key = self.broker_field_vars.get("api_key",    tk.StringVar()).get().strip()
        api_sec = self.broker_field_vars.get("api_secret", tk.StringVar()).get().strip()
        broker_name = self.broker_var.get()
        broker      = BROKERS.get(broker_name, {})
        testnet     = self.testnet_var.get()

        def test_telegram():
            try:
                if not tg_id.isdigit():
                    raise ValueError("API ID muss eine Zahl sein")
                if len(tg_hash) < 10:
                    raise ValueError("API Hash zu kurz")
                # Einfacher HTTP-Check ob Telegram erreichbar ist
                import urllib.request, ssl
                try:
                    import certifi
                    ctx = ssl.create_default_context(cafile=certifi.where())
                except ImportError:
                    ctx = ssl.create_default_context()
                urllib.request.urlopen("https://api.telegram.org", timeout=5, context=ctx)
                self.root.after(0, lambda: self.tg_status_dot.configure(
                    text="●  Verbunden ✓", fg=GREEN))
                self.root.after(0, lambda: self.tg_status_info.configure(
                    text=f"API ID: {tg_id[:4]}{'*'*4}  |  Hash: {tg_hash[:4]}{'*'*8}", fg=DIM))
            except Exception as e:
                msg = str(e)
                self.root.after(0, lambda: self.tg_status_dot.configure(
                    text="●  Fehler ✗", fg=RED))
                self.root.after(0, lambda: self.tg_status_info.configure(
                    text=msg[:60], fg=RED))

        def test_broker():
            try:
                if not api_key or not api_sec:
                    raise ValueError("API Key / Secret fehlt")

                # ── Binance Futures: direkt über python-binance testen ──
                if broker_name == "Binance Futures":
                    from binance.client import Client
                    c = Client(api_key, api_sec, testnet=testnet)
                    bal = c.futures_account_balance()
                    usdt = next((float(b["balance"]) for b in bal if b["asset"]=="USDT"), 0)
                    self.root.after(0, lambda: self.br_status_dot.configure(
                        text="●  Verbunden ✓", fg=GREEN))
                    self.root.after(0, lambda: self.br_status_info.configure(
                        text=f"Binance Futures  |  Balance: {usdt:.2f} USDT  |  {'Testnet' if testnet else 'LIVE'}", fg=DIM))

                # ── Alle anderen ccxt-Broker ──
                elif broker.get("engine") == "ccxt":
                    import ccxt
                    exchange_id = broker.get("ccxt_id", "binanceusdm")
                    exchange_cls = getattr(ccxt, exchange_id)
                    params = {"apiKey": api_key, "secret": api_sec}
                    if testnet and broker.get("has_testnet"):
                        params["options"] = {"defaultType": "future"}
                        params["sandbox"] = True
                    ex = exchange_cls(params)
                    balance = ex.fetch_balance()
                    usdt = balance.get("USDT", {}).get("free", 0)
                    self.root.after(0, lambda: self.br_status_dot.configure(
                        text="●  Verbunden ✓", fg=GREEN))
                    self.root.after(0, lambda: self.br_status_info.configure(
                        text=f"{broker_name}  |  Balance: {usdt:.2f} USDT  |  {'Testnet' if testnet else 'LIVE'}", fg=DIM))

                # ── Custom Broker ──
                elif broker.get("engine") == "custom":
                    imp = broker.get("import","")
                    __import__(imp)
                    self.root.after(0, lambda: self.br_status_dot.configure(
                        text="●  Bibliothek OK ✓", fg=ACCENT))
                    self.root.after(0, lambda: self.br_status_info.configure(
                        text="Bibliothek installiert – API nicht automatisch testbar", fg=DIM))

            except ImportError:
                self.root.after(0, lambda: self.br_status_dot.configure(
                    text="●  Bibliothek fehlt ✗", fg=RED))
                self.root.after(0, lambda: self.br_status_info.configure(
                    text="Bitte zuerst Bibliothek installieren", fg=RED))
            except Exception as e:
                msg = str(e)[:70]
                self.root.after(0, lambda: self.br_status_dot.configure(
                    text="●  Fehler ✗", fg=RED))
                self.root.after(0, lambda: self.br_status_info.configure(
                    text=msg, fg=RED))

        def run_tests():
            test_telegram()
            test_broker()
            self.root.after(0, lambda: self.test_btn.configure(
                text="🔌  VERBINDUNG TESTEN", state="normal"))

        threading.Thread(target=run_tests, daemon=True).start()

    # ── MAPPING TAB ───────────────────────────────────────
    def _build_mapping_tab(self):
        f = tk.Frame(self.content, bg=BG)
        self.tabs["mapping"] = f
        p = self.profile()

        # Scrollbar für Mapping
        map_canvas = tk.Canvas(f, bg=BG, highlightthickness=0)
        map_scroll = ttk.Scrollbar(f, orient="vertical", command=map_canvas.yview)
        self.mapping_inner = tk.Frame(map_canvas, bg=BG)
        self.mapping_inner.bind("<Configure>",
            lambda e: map_canvas.configure(scrollregion=map_canvas.bbox("all")))
        map_win_id = map_canvas.create_window((0,0), window=self.mapping_inner, anchor="nw")
        map_canvas.configure(yscrollcommand=map_scroll.set)
        map_canvas.pack(side="left", fill="both", expand=True)
        map_scroll.pack(side="right", fill="y")
        self.mapping_canvas = map_canvas
        # Canvas-Breite synchronisieren
        map_canvas.bind("<Configure>",
            lambda e: map_canvas.itemconfig(map_win_id, width=e.width))

        mi = self.mapping_inner

        tk.Label(mi, text="Signal Mapping – Begriffe definieren",
                 font=CF_B, bg=BG, fg=ACCENT).pack(anchor="w", pady=(0,4))
        tk.Label(mi, text="Trage alle Begriffe ein die dein Bot verwendet. Mehrere Begriffe kommagetrennt.",
                 font=("Consolas",8), bg=BG, fg=DIM).pack(anchor="w", pady=(0,8))

        self.map_vars = {}
        map_fields = [
            ("Signal Start",  "map_signal_start", "Womit beginnt\nein Signal?"),
            ("LONG / BUY",    "map_long",          "Kauf-Richtung"),
            ("SHORT / SELL",  "map_short",         "Verkauf-Richtung"),
            ("Symbol / Pair", "map_pair",          "Begriff vor\ndem Paar"),
            ("Entry Preis",   "map_entry",         "Einstiegspreis"),
            ("Take Profit",   "map_tp",            "Gewinnziel"),
            ("Stop Loss",     "map_sl",            "Verlustgrenze"),
            ("Close / Exit",  "map_close",         "Position\nschließen"),
            ("Market Order",  "map_market",        "Markt-Order\n(sofort kaufen)"),
            ("Limit Order",   "map_limit",         "Limit-Order\n(zum Wunschpreis)"),
        ]

        for label, key, hint in map_fields:
            row = tk.Frame(mi, bg=CARD2, padx=12, pady=8)
            row.pack(fill="x", pady=(0,4))
            row.columnconfigure(0, minsize=200)
            row.columnconfigure(1, weight=1)

            tk.Label(row, text=label, font=("Consolas",10,"bold"),
                     bg=CARD2, fg=ACCENT, anchor="w").grid(row=0, column=0, sticky="w")
            tk.Label(row, text=hint, font=("Consolas",8),
                     bg=CARD2, fg=DIM, anchor="w", justify="left").grid(row=1, column=0, sticky="w")

            var = tk.StringVar(value=p.get(key,""))
            tk.Entry(row, textvariable=var, font=("Consolas",10),
                     bg=CARD, fg=ACCENT, insertbackground=ACCENT,
                     bd=0, relief="flat").grid(row=0, column=1, rowspan=2,
                                               sticky="ew", padx=(12,0), ipady=5)
            self.map_vars[key] = var

        tk.Frame(mi, bg=DIM, height=1).pack(fill="x", pady=(8,6))
        tk.Label(mi, text="💡  Beispiel:  TP = 'TP, TakeProfit, Ziel, Target'  →  Bot erkennt alle Varianten automatisch",
                 font=("Consolas",8), bg=BG, fg=DIM).pack(anchor="w")

        bf = tk.Frame(mi, bg=BG)
        bf.pack(fill="x", pady=(8,0))
        tk.Button(bf, text="💾  MAPPING SPEICHERN", font=CF_L,
                  bg=ACCENT, fg="#000", activebackground="#d97706",
                  bd=0, relief="flat", cursor="hand2", padx=20, pady=10,
                  command=self.save_mapping).pack(side="left", expand=True, fill="x", padx=(0,8))
        tk.Button(bf, text="↩  STANDARD", font=CF_L, bg=CARD, fg=DIM,
                  bd=0, relief="flat", cursor="hand2", padx=20, pady=10,
                  command=self.reset_mapping).pack(side="left", expand=True, fill="x")

        # Mausrad-Scrolling binden
        self._bind_mousewheel(self.mapping_inner, map_canvas)

    # ── TRADE HISTORY TAB ─────────────────────────────────
    def _build_history_tab(self):
        f = tk.Frame(self.content, bg=BG)
        self.tabs["history"] = f

        # ── Statistik-Cards ─────────────────────────────
        stats_row = tk.Frame(f, bg=BG)
        stats_row.pack(fill="x", pady=(0,8))
        for i in range(4): stats_row.columnconfigure(i, weight=1)

        self.stat_pnl_lbl   = self._stat_card(stats_row, "💰 Gesamt P&L", "0.00 USDT", 0)
        self.stat_win_lbl   = self._stat_card(stats_row, "📈 Win Rate", "0%", 1)
        self.stat_count_lbl = self._stat_card(stats_row, "📊 Trades", "0", 2)
        self.stat_best_lbl  = self._stat_card(stats_row, "🏆 Bester", "0.00 USDT", 3)

        # ── Tabelle ──────────────────────────────────────
        tk.Label(f, text="  TRADE HISTORY", font=CF_B, bg=BG, fg=ACCENT).pack(anchor="w", pady=(0,4))

        # Treeview Style anpassen (History)
        style = ttk.Style()
        style.configure("Dark.Treeview",
                        background=CARD, foreground=TEXT, fieldbackground=CARD,
                        font=CF, rowheight=24, borderwidth=0)
        style.configure("Dark.Treeview.Heading",
                        background=CARD2, foreground=ACCENT, font=CF_B,
                        borderwidth=0, relief="flat")
        style.map("Dark.Treeview",
                  background=[("selected", CARD2)],
                  foreground=[("selected", TEXT)])

        columns = ("time", "symbol", "direction", "type", "entry", "exit", "pnl", "status")
        tree_frame = tk.Frame(f, bg=CARD)
        tree_frame.pack(fill="both", expand=True, pady=(0,8))

        self.history_tree = ttk.Treeview(tree_frame, columns=columns,
                                          show="headings", height=12, style="Dark.Treeview")

        # Spalten konfigurieren
        col_config = [
            ("time",      "Zeit",       120),
            ("symbol",    "Symbol",      90),
            ("direction", "Richtung",    70),
            ("type",      "Typ",         60),
            ("entry",     "Entry",       90),
            ("exit",      "Exit",        90),
            ("pnl",       "P&L (USDT)",  90),
            ("status",    "Status",      70),
        ]
        for col_id, heading, width in col_config:
            self.history_tree.heading(col_id, text=heading)
            self.history_tree.column(col_id, width=width, minwidth=50)

        # Scrollbar
        tree_scroll = ttk.Scrollbar(tree_frame, orient="vertical",
                                     command=self.history_tree.yview)
        self.history_tree.configure(yscrollcommand=tree_scroll.set)
        self.history_tree.pack(side="left", fill="both", expand=True)
        tree_scroll.pack(side="right", fill="y")

        # Tags für Farben
        self.history_tree.tag_configure("win", foreground=GREEN)
        self.history_tree.tag_configure("loss", foreground=RED)
        self.history_tree.tag_configure("open", foreground=ACCENT)

        # ── Buttons ──────────────────────────────────────
        bf = tk.Frame(f, bg=BG)
        bf.pack(fill="x", pady=(0,4))
        tk.Button(bf, text="🔄  AKTUALISIEREN", font=CF_L,
                  bg=BLUE, fg="#000", activebackground="#2563eb",
                  bd=0, relief="flat", cursor="hand2", padx=20, pady=10,
                  command=self._refresh_history).pack(side="left", expand=True, fill="x", padx=(0,4))
        tk.Button(bf, text="🗑️  STATISTIKEN ZURÜCKSETZEN", font=CF_L,
                  bg="#dc2626", fg="#fff", activebackground="#b91c1c",
                  bd=0, relief="flat", cursor="hand2", padx=20, pady=10,
                  command=self._reset_statistics).pack(side="left", expand=True, fill="x")

        # Initial laden
        self.root.after(1000, self._refresh_history)

    def _stat_card(self, parent, label, value, col):
        """Erstellt eine Statistik-Card."""
        card = tk.Frame(parent, bg=CARD, padx=10, pady=8)
        card.grid(row=0, column=col, padx=(0 if col==0 else 4, 0), sticky="ew")
        tk.Label(card, text=label, font=("Consolas",8), bg=CARD, fg=DIM).pack(anchor="w")
        lbl = tk.Label(card, text=value, font=CF_B, bg=CARD, fg=ACCENT)
        lbl.pack(anchor="w")
        return lbl

    @staticmethod
    def _fmt_pnl(val):
        """Formatiert P&L-Werte dynamisch (mehr Dezimalen für kleine Beträge)."""
        if val is None:
            return "–"
        prefix = "+" if val > 0 else ""
        if abs(val) >= 1.0:
            return f"{prefix}{val:.2f}"
        elif abs(val) >= 0.01:
            return f"{prefix}{val:.4f}"
        else:
            return f"{prefix}{val:.6f}"

    @staticmethod
    def _fmt_price(val):
        """Formatiert Preise dynamisch (mehr Dezimalen für Micro-Coins)."""
        if not val or val == 0:
            return "–"
        if val >= 1.0:
            return f"{val:.2f}"
        elif val >= 0.001:
            return f"{val:.4f}"
        else:
            return f"{val:.8f}"

    def _refresh_history(self):
        """Lädt Trade-History und Statistiken aus der Datenbank."""
        try:
            # Statistiken laden
            stats = self.trade_db.get_statistics()

            # Gesamt P&L
            pnl = stats["total_pnl"]
            if pnl == 0 and stats["total_trades"] == 0:
                self.stat_pnl_lbl.configure(text="–", fg=DIM)
            else:
                pnl_color = GREEN if pnl >= 0 else RED
                self.stat_pnl_lbl.configure(
                    text=f"{self._fmt_pnl(pnl)} USDT", fg=pnl_color)

            # Win Rate
            wr = stats['win_rate']
            self.stat_win_lbl.configure(
                text=f"{wr:.1f}%" if stats["total_trades"] > 0 else "–",
                fg=GREEN if wr >= 50 else (RED if wr > 0 else DIM))

            # Trade-Zähler
            self.stat_count_lbl.configure(text=str(stats["total_trades"]))

            # Bester Trade
            best = stats["best_trade"]
            self.stat_best_lbl.configure(
                text=f"+{self._fmt_pnl(best)} USDT" if best > 0 else "–",
                fg=GREEN if best > 0 else DIM)

            # Tabelle leeren
            for item in self.history_tree.get_children():
                self.history_tree.delete(item)

            # Trades laden
            trades = self.trade_db.get_all_trades(limit=200)
            for t in trades:
                opened = t.get("opened_at", "")[:16].replace("T", " ")
                pnl_val = t.get("pnl_usdt")
                pnl_str = self._fmt_pnl(pnl_val)
                exit_str = self._fmt_price(t.get("exit_price"))
                entry_str = self._fmt_price(t.get("entry_price"))

                if t["status"] == "OPEN":
                    tag = "open"
                elif pnl_val and pnl_val > 0:
                    tag = "win"
                elif pnl_val and pnl_val < 0:
                    tag = "loss"
                else:
                    tag = ""

                self.history_tree.insert("", "end", values=(
                    opened, t["symbol"], t["direction"], t.get("order_type",""),
                    entry_str, exit_str, pnl_str, t["status"]
                ), tags=(tag,))
        except Exception as e:
            self._log(f"History Fehler: {e}", "error")

    def _reset_statistics(self):
        """Setzt alle Trade-Statistiken zurück (löscht Trade-History)."""
        if not messagebox.askyesno(
            "Statistiken zurücksetzen",
            "Alle Trade-Daten unwiderruflich löschen?\n\n"
            "Dies entfernt ALLE Trades aus der Datenbank\n"
            "(offene + geschlossene).\n\n"
            "Dieser Vorgang kann NICHT rückgängig gemacht werden!"):
            return
        # Zweite Bestätigung für Sicherheit
        if not messagebox.askyesno(
            "⚠️ Endgültig löschen?",
            "Bist du WIRKLICH sicher?\n\n"
            "Alle Trades werden gelöscht!"):
            return
        try:
            self.trade_db.clear_all_trades()
            self._refresh_history()
            self._log("🗑️  Alle Trade-Statistiken zurückgesetzt.", "warn")
            messagebox.showinfo("Zurückgesetzt", "Alle Trade-Daten wurden gelöscht.")
        except Exception as e:
            self._log(f"Reset Fehler: {e}", "error")
            messagebox.showerror("Fehler", f"Fehler beim Zurücksetzen:\n{e}")

    # ── HELP / ANLEITUNG TAB ─────────────────────────────
    def _build_help_tab(self):
        f = tk.Frame(self.content, bg=BG)
        self.tabs["help"] = f

        # Scrollbare Textbox für die Anleitung
        hdr = tk.Frame(f, bg=BG)
        hdr.pack(fill="x", pady=(0,8))
        tk.Label(hdr, text="📖  Anleitung – So funktioniert EdgeTrader",
                 font=CF_L, bg=BG, fg=ACCENT).pack(side="left")

        txt = scrolledtext.ScrolledText(
            f, font=("Consolas", 9), bg=CARD, fg=TEXT,
            insertbackground=ACCENT, borderwidth=0, relief="flat",
            state="normal", wrap="word", padx=16, pady=12)
        txt.pack(fill="both", expand=True)

        # Tag-Styles
        txt.tag_config("h1", font=("Consolas", 14, "bold"), foreground=ACCENT)
        txt.tag_config("h2", font=("Consolas", 11, "bold"), foreground=ACCENT)
        txt.tag_config("h3", font=("Consolas", 10, "bold"), foreground="#f0b429")
        txt.tag_config("bold", font=("Consolas", 9, "bold"), foreground=TEXT)
        txt.tag_config("accent", foreground=ACCENT)
        txt.tag_config("green", foreground=GREEN)
        txt.tag_config("red", foreground=RED)
        txt.tag_config("blue", foreground=BLUE)
        txt.tag_config("dim", foreground=DIM)
        txt.tag_config("warn", foreground=ACCENT, font=("Consolas", 9, "bold"))

        def h1(text): txt.insert("end", f"\n{text}\n", "h1"); txt.insert("end", "\n")
        def h2(text): txt.insert("end", f"{text}\n", "h2")
        def ln(text, tag=""):  txt.insert("end", f"{text}\n", tag if tag else ())
        def br(): txt.insert("end", "\n")

        # ── Inhalt ─────────────────────────────────────
        h1("WILLKOMMEN BEI EDGETRADER")
        ln("EdgeTrader verbindet deinen Telegram-Kanal mit deinem", "dim")
        ln("Broker und handelt Signale vollautomatisch.", "dim")
        ln(f"Version {VERSION}  |  {len(BROKERS)} Broker unterstützt", "dim")

        h1("1. SCHNELLSTART")
        h2("Schritt 1: Telegram-Kanal eintragen")
        ln("  1. Gehe zu EINSTELLUNGEN")
        ln("  2. Trage den Namen deines Signal-Kanals ein", "accent")
        ln("     (ohne @ – z.B. 'MeinSignalKanal')")
        ln("  3. Beim ersten Start wirst du nach deiner")
        ln("     Telefonnummer + Code gefragt (einmalig!)")
        br()
        ln("  Hinweis: API ID & Hash sind bereits vorkonfiguriert.", "dim")
        ln("  Falls du eigene verwenden willst:", "dim")
        ln("  → Klicke 'Erweitert' unter Telegram-Einstellungen", "dim")
        br()
        h2("Schritt 2: Broker einrichten")
        ln("  1. Wähle deinen Broker (z.B. Binance Futures)")
        ln("  2. Erstelle API-Keys auf der Broker-Website")
        ln("     (nur Trading-Rechte, KEIN Withdrawal!)", "warn")
        ln("  3. Trage API Key + Secret unter EINSTELLUNGEN ein", "accent")
        ln("  4. Wähle Testnet (zum Üben) oder Live", "warn")
        br()
        h2("Schritt 3: Kanal & Mapping")
        ln("  1. Gehe zum SIGNAL MAP Tab")
        ln("  2. Prüfe ob die Schlüsselwörter zu deinem Anbieter passen")
        ln("  3. Passe sie ggf. an (Komma-getrennte Begriffe)")
        br()
        h2("Schritt 4: Bot starten")
        ln("  1. Gehe zum BOT Tab", "green")
        ln("  2. Stelle Hebel, Kapital und Stop Loss ein")
        ln("  3. Klicke 'BOT STARTEN'", "green")
        ln("  4. Der Bot wartet jetzt auf Signale!", "green")

        h1("2. EINSTELLUNGEN ERKLÄRT")
        h2("Telegram")
        ln("  Kanal / Bot   Name des Telegram-Kanals (ohne @)")
        ln("  API ID        Vorkonfiguriert – nur bei Bedarf ändern", "dim")
        ln("  API Hash      Vorkonfiguriert – nur bei Bedarf ändern", "dim")
        br()
        h2("Broker")
        ln("  Exchange      Wähle deinen Broker aus der Liste")
        ln("  API Key       Dein API-Schlüssel vom Broker")
        ln("  API Secret    Dein geheimer API-Schlüssel")
        ln("  Passphrase    Nur bei OKX, KuCoin, Bitget nötig")
        br()
        h2("Modus")
        ln("  Testnet       Zum Üben mit Spielgeld (empfohlen!)", "green")
        ln("  Live          Echtes Geld – VORSICHT!", "red")

        h1("3. TRADING-PARAMETER")
        h2("Hebel (Leverage)")
        ln("  Multiplikator für deine Position (1-125x)")
        ln("  Höherer Hebel = höheres Risiko!", "red")
        ln("  Empfehlung für Anfänger: 2-5x", "accent")
        br()
        h2("Kapital pro Trade")
        ln("  Wie viel USDT pro Signal eingesetzt wird")
        ln("  Beispiel: 100 USDT bei 5x = 500 USDT Position")
        br()
        h2("Stop Loss (%)")
        ln("  Automatische Verlustbegrenzung in % vom Entry")
        ln("  LONG:  SL = Entry - SL%", "accent")
        ln("  SHORT: SL = Entry + SL%", "accent")
        ln("  Empfehlung: 1-3%", "accent")
        br()
        h2("Take Profit (TP)")
        ln("  Vom Signal vorgegebene Gewinnziele")
        ln("  Verteilung anpassbar (z.B. 33,33,34 für 3 TPs)")
        ln("  TP kann aktiviert/deaktiviert werden")
        br()
        h2("Trailing Take Profit")
        ln("  Zieht den Stop Loss automatisch nach,")
        ln("  wenn ein TP-Level erreicht wird.", "accent")
        ln("  Trailing %: Abstand zum aktuellen Preis")
        ln("  Trigger: Ab welchem TP-Level nachgezogen wird")
        br()
        h2("Limit-Order Invalidierung")
        ln("  Prüft offene LIMIT-Orders kontinuierlich.")
        ln("  Wenn der Marktpreis zu weit vom Entry abweicht,", "accent")
        ln("  wird die Order automatisch gecancelt.", "accent")
        ln("  Schwelle in % einstellbar (Standard: 2%)")

        h1("4. SIGNAL MAPPING")
        ln("Der Bot erkennt Signale anhand von Schlüsselwörtern.", "dim")
        ln("Passe sie an deinen Signal-Anbieter an!", "dim")
        br()
        ln("  LONG / BUY      Begriffe für Kauf-Signale")
        ln("  SHORT / SELL     Begriffe für Verkauf-Signale")
        ln("  Symbol / Pair    Begriff vor dem Trading-Paar")
        ln("  Entry            Begriff vor dem Einstiegspreis")
        ln("  Take Profit      Begriff vor dem Gewinnziel")
        ln("  Stop Loss        Begriff vor der Verlustgrenze")
        ln("  Close / Exit     Signal zum Schließen")
        ln("  Market / Limit   Ordertyp-Erkennung")
        br()
        ln("  Mehrere Begriffe mit Komma trennen:", "accent")
        ln("  z.B.  TP, TakeProfit, Take Profit, Ziel, Target", "accent")

        h1("5. DASHBOARD")
        ln("Das Dashboard zeigt alle offenen Positionen in Echtzeit.", "dim")
        br()
        h2("Position schließen")
        ln("  1. Wähle eine Position in der Tabelle aus")
        ln("  2. Klicke 'POSITION SCHLIESSEN'", "red")
        ln("  3. Bestätige im Dialog")
        ln("  → Position wird zum Marktpreis geschlossen", "accent")
        ln("  → Alle offenen TP/SL-Orders werden gecancelt", "accent")

        h1("6. TRADES & STATISTIKEN")
        ln("Unter TRADES siehst du alle vergangenen Trades.", "dim")
        br()
        h2("Statistiken")
        ln("  💰 Gesamt P&L    Gesamter Gewinn/Verlust in USDT")
        ln("  📈 Win Rate      Prozent der Gewinn-Trades")
        ln("  📊 Trades        Anzahl abgeschlossener + offener Trades")
        ln("  🏆 Bester        Höchster Einzel-Gewinn")
        br()
        ln("  Statistiken können über den Button zurückgesetzt werden.", "dim")

        h1("7. PROFILE")
        ln("Erstelle verschiedene Profile für verschiedene Setups:", "dim")
        br()
        ln("  Profil 1:  Binance Testnet + Kanal A", "accent")
        ln("  Profil 2:  Bybit Live + Kanal B", "accent")
        ln("  Profil 3:  OKX Testnet + Kanal C", "accent")
        br()
        ln("  Schnell wechseln über die Profil-Leiste oben!")
        ln("  Bis zu 10 Bots gleichzeitig möglich!", "green")

        h1("8. UNTERSTÜTZTE BROKER")
        h2("Crypto Futures")
        for name, b in BROKERS.items():
            if "Crypto" in b["category"]:
                test = "  (Testnet)" if b.get("has_testnet") else ""
                ln(f"  • {name}{test}", "accent")
        br()
        h2("Stocks / CFD")
        for name, b in BROKERS.items():
            if "Stocks" in b["category"]:
                ln(f"  • {name}  –  {b.get('info','')}", "accent")

        h1("9. SICHERHEITSHINWEISE")
        ln("  • API-Keys NIEMALS teilen oder öffentlich posten!", "red")
        ln("  • Testnet IMMER zuerst nutzen!", "red")
        ln("  • Nur Kapital einsetzen das du verlieren kannst!", "red")
        ln("  • API-Keys mit minimalen Rechten erstellen", "warn")
        ln("    (nur Trading, kein Withdrawal!)", "warn")
        ln("  • Stop Loss IMMER aktiviert lassen", "warn")

        h1("10. RISIKO-HINWEIS")
        ln("Der Handel mit Kryptowährungen und Derivaten birgt", "red")
        ln("erhebliche Risiken bis hin zum TOTALVERLUST.", "red")
        ln("Gehebelte Produkte können zu Verlusten führen,", "red")
        ln("die Ihre Einlage übersteigen.", "red")
        br()
        ln("EdgeTrader ist ein Werkzeug – KEINE Anlageberatung.", "warn")
        ln("Sie handeln ausschließlich auf eigenes Risiko.", "warn")

        h1("11. LIZENZ & KONTAKT")
        info = get_license_info()
        if info["activated"]:
            ln(f"  Status:  LIZENZIERT", "green")
            ln(f"  Kunde:   {info['customer']}", "green")
        else:
            ln(f"  Status:  TESTVERSION ({info['trial_days_left']} Tage übrig)", "warn")
            ln(f"  Klicke auf '🔑 Trial' oben rechts zum Aktivieren", "accent")
        br()
        ln("  Herausgeber:", "dim")
        ln("  BP-Shops – Philip Babuda", "accent")
        ln("  Ernst-Schenk-Str. 9b, 91550 Dinkelsbühl", "dim")
        ln("  E-Mail: reklamation@bp-shops.com", "blue")
        br()
        ln(f"  EdgeTrader v{VERSION} © 2026 – Alle Rechte vorbehalten", "dim")

        txt.configure(state="disabled")

    # ── Speichern ─────────────────────────────────────────
    def save_settings(self):
        p = self.profile()
        for key, var in self.setting_vars.items(): p[key] = var.get().strip()
        for key, var in self.broker_field_vars.items(): p[key] = var.get().strip()
        p["broker"]  = self.broker_var.get()
        p["testnet"] = self.testnet_var.get()
        # TP/Trailing Settings speichern
        p["tp_distribution"]  = self.tp_dist_var.get().strip()
        p["trailing_enabled"] = self.trailing_enabled_var.get()
        p["trailing_percent"] = self.trailing_pct_var.get().strip()
        # Limit-Order Invalidierung
        p["limit_invalidation_enabled"] = self.limit_inv_enabled_var.get()
        p["limit_invalidation_percent"] = self.limit_inv_pct_var.get().strip()
        if not p["telegram_api_id"].isdigit():
            messagebox.showerror("Fehler","Telegram API ID muss eine Zahl sein!"); return
        save_config(self.cfg)
        broker = p["broker"]
        b_info = BROKERS.get(broker,{})
        self.ch_label.configure(text=p["telegram_channel"])
        self.ex_label.configure(text=f"{broker} {'[Test]' if p['testnet'] else '[LIVE]'}")
        self.cat_label.configure(text=b_info.get("category",""))
        messagebox.showinfo("✅ Gespeichert","Einstellungen gespeichert!\nBot neu starten für Änderungen.")
        self._switch_tab("bot")
        self._log(f"⚙️  Gespeichert – Broker: {broker} | {b_info.get('category','')}", "warn")

    def save_mapping(self):
        p = self.profile()
        for key, var in self.map_vars.items(): p[key] = var.get().strip()
        save_config(self.cfg)
        messagebox.showinfo("✅ Gespeichert","Signal Mapping gespeichert!\nBot neu starten für Änderungen.")
        self._switch_tab("bot")
        self._log("🗺️  Signal Mapping gespeichert.", "warn")

    def reset_settings(self):
        if messagebox.askyesno("Zurücksetzen","Einstellungen zurücksetzen?"):
            p = self.profile()
            for k in ["telegram_api_id","telegram_api_hash","telegram_channel",
                      "broker","api_key","api_secret","passphrase","testnet"]:
                p[k] = DEFAULT_PROFILE[k]
            self._load_profile_into_ui()
            save_config(self.cfg); self._log("Einstellungen zurückgesetzt.", "warn")

    def reset_mapping(self):
        if messagebox.askyesno("Zurücksetzen","Mapping auf Standard?"):
            p = self.profile()
            for k in self.map_vars:
                p[k] = DEFAULT_PROFILE[k]; self.map_vars[k].set(p[k])
            save_config(self.cfg); self._log("Mapping zurückgesetzt.", "warn")

    # ── Bot starten ───────────────────────────────────────
    def start_bot(self, profile_index: int = None):
        global bot_processes

        if profile_index is None:
            profile_index = self.cfg["active_profile"]

        if profile_index in bot_processes:
            self._log(f"⚠️ Profil {profile_index} läuft bereits!", "warn")
            return

        if len(bot_processes) >= MAX_BOTS:
            self._log(f"❌ Maximum {MAX_BOTS} Bots erreicht!", "error")
            return

        p = self.cfg["profiles"][profile_index]

        # Aktives Profil: Werte aus UI lesen und speichern
        if profile_index == self.cfg["active_profile"]:
            try:
                lev = int(self.leverage_var.get())
                cap = float(self.capital_var.get())
                sl  = float(self.sl_var.get().replace(",","."))
            except ValueError:
                self._log("❌ Ungültige Handelswerte!", "error"); return
            if not (1<=lev<=125) or cap<=0 or not (0.1<=sl<=20):
                self._log("❌ Werte außerhalb des erlaubten Bereichs!", "error"); return
            p["leverage"] = str(lev); p["capital"] = str(cap); p["sl_percent"] = str(sl)
            p["tp_enabled"]      = self.tp_enabled_var.get()
            p["sl_enabled"]      = self.sl_enabled_var.get()
            p["auto_sl_enabled"] = self.auto_sl_enabled_var.get()

        save_config(self.cfg)

        # Im gepackten Modus (.exe) den Bot als eigene .exe starten
        install_dir = get_install_dir()
        if getattr(sys, 'frozen', False):
            bot_exe = os.path.join(install_dir, "edgetrader_bot.exe")
            if not os.path.exists(bot_exe):
                self._log("❌ edgetrader_bot.exe nicht gefunden!", "error"); return
            cmd = [bot_exe, str(profile_index)]
        else:
            script = os.path.join(install_dir, "telegram_binance_bot.py")
            if not os.path.exists(script):
                self._log("❌ telegram_binance_bot.py nicht gefunden!", "error"); return
            cmd = [sys.executable, script, str(profile_index)]

        broker = p.get("broker","Binance Futures")
        mode   = "TESTNET" if p["testnet"] else "⚠️ LIVE"
        self._log(f"[{p['name']}] ⚙️  {mode} | {broker}", "warn")

        proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding="utf-8", errors="replace", bufsize=1,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform=="win32" else 0)

        reader = threading.Thread(
            target=self._read_output, args=(proc, profile_index), daemon=True)
        reader.start()

        bot_processes[profile_index] = {"process": proc, "thread": reader}
        self._update_status_display()
        self._refresh_bot_rows()
        self._log(f"✅ [{p['name']}] Bot gestartet – warte auf Signale...", "success")
        self.root.after(1000, lambda: self._check_process(profile_index))

    def _read_output(self, process, profile_index: int):
        profile_name = self.cfg["profiles"][profile_index]["name"]
        prefix = f"[{profile_name}]"

        for line in process.stdout:
            line = line.strip()
            if not line: continue

            # ── Telegram-Authentifizierung abfangen ──────────
            if line == "AUTH_PHONE_REQUIRED":
                self.root.after(0, self._ask_telegram_auth, "phone", process, profile_index)
                continue
            elif line == "AUTH_CODE_REQUIRED":
                self.root.after(0, self._ask_telegram_auth, "code", process, profile_index)
                continue
            elif line == "AUTH_2FA_REQUIRED":
                self.root.after(0, self._ask_telegram_auth, "2fa", process, profile_index)
                continue

            # ── Trade-Events abfangen ─────────────────────────
            if line.startswith("TRADE_OPEN|") or line.startswith("TRADE_CLOSE|"):
                self.root.after(100, self._refresh_history)
                continue

            # ── Recovery-Event: Dashboard + Trades aktualisieren ──
            if line.startswith("RECOVERY|"):
                self.root.after(100, self._refresh_history)
                self.root.after(200, self._dashboard_refresh)
                self.root.after(0, self._log, f"{prefix} 🔄 Offene Positionen wiederhergestellt", "success")
                continue

            # ── Normales Log-Routing ─────────────────────────
            if any(x in line for x in ["✅","🎯","complete","authentifiziert","Recovery abgeschlossen"]): tag="success"
            elif any(x in line for x in ["ERROR","Fehler","❌"]): tag="error"
            elif any(x in line for x in ["📩","📊","🔒","INFO","⚙️","🗺️","📱","🔍","📈"]): tag="warn"
            else: tag="info"
            self.root.after(0, self._log, f"{prefix} {line}", tag)

    def _ask_telegram_auth(self, auth_type, process=None, profile_index=None):
        """Zeigt Telegram-Authentifizierungs-Dialog und sendet Antwort an Bot."""
        import tkinter.simpledialog

        pname = ""
        if profile_index is not None and profile_index < len(self.cfg["profiles"]):
            pname = f" ({self.cfg['profiles'][profile_index]['name']})"

        if auth_type == "phone":
            title  = f"Telegram Login{pname}"
            prompt = "Bitte gib deine Telefonnummer ein\n(mit Landesvorwahl, z.B. +49...):"
            self._log(f"📱 Telegram Login{pname} – Telefonnummer eingeben...", "warn")
        elif auth_type == "code":
            title  = f"Telegram Verifizierung{pname}"
            prompt = "Bitte gib den Code ein,\nden du per Telegram/SMS erhalten hast:"
            self._log(f"📱 Verifizierungscode{pname} eingeben...", "warn")
        else:  # 2fa
            title  = f"Telegram 2FA{pname}"
            prompt = "Bitte gib dein Zwei-Faktor-Passwort ein:"
            self._log(f"🔐 2FA-Passwort{pname} eingeben...", "warn")

        result = tkinter.simpledialog.askstring(title, prompt, parent=self.root)

        if result and process and process.poll() is None:
            try:
                process.stdin.write(result + "\n")
                process.stdin.flush()
            except (OSError, BrokenPipeError):
                self._log("❌ Kommunikation mit Bot fehlgeschlagen", "error")
                if profile_index is not None:
                    self.stop_bot(profile_index)
        else:
            self._log("❌ Authentifizierung abgebrochen", "error")
            if profile_index is not None:
                self.stop_bot(profile_index)

    def _check_process(self, profile_index: int = None):
        if profile_index is not None and profile_index in bot_processes:
            proc = bot_processes[profile_index]["process"]
            if proc.poll() is not None:
                pname = self.cfg["profiles"][profile_index]["name"] if profile_index < len(self.cfg["profiles"]) else "?"
                del bot_processes[profile_index]
                self._update_status_display()
                self._refresh_bot_rows()
                self._log(f"⚠️ [{pname}] Bot unerwartet beendet.", "error")
            else:
                self.root.after(2000, lambda: self._check_process(profile_index))
        else:
            # Alle laufenden Bots checken
            for idx in list(bot_processes.keys()):
                self.root.after(0, lambda i=idx: self._check_process(i))

    def stop_bot(self, profile_index: int = None):
        global bot_processes
        if profile_index is None:
            profile_index = self.cfg["active_profile"]

        if profile_index in bot_processes:
            proc = bot_processes[profile_index]["process"]
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait(timeout=3)
            del bot_processes[profile_index]
            pname = self.cfg["profiles"][profile_index]["name"] if profile_index < len(self.cfg["profiles"]) else "?"
            self._log(f"[{pname}] Bot gestoppt.", "warn")

        self._update_status_display()
        self._refresh_bot_rows()

    def _update_status_display(self):
        """Aktualisiert die Status-Anzeige im Header."""
        count = len(bot_processes)
        if count == 0:
            self.dot.configure(fg=RED)
            self.slbl.configure(text="GESTOPPT", fg=RED)
            if hasattr(self, 'start_btn'):
                self.start_btn.configure(state="normal", bg=GREEN, fg="#000")
                self.stop_btn.configure(state="disabled", bg=CARD, fg=DIM)
        else:
            self.dot.configure(fg=GREEN)
            self.slbl.configure(text=f"{count} AKTIV", fg=GREEN)
            # Aktives Profil: Button-Status anpassen
            active = self.cfg["active_profile"]
            if hasattr(self, 'start_btn'):
                if active in bot_processes:
                    self.start_btn.configure(state="disabled", bg="#374151", fg=DIM)
                    self.stop_btn.configure(state="normal", bg=RED, fg="#000")
                else:
                    self.start_btn.configure(state="normal", bg=GREEN, fg="#000")
                    self.stop_btn.configure(state="disabled", bg=CARD, fg=DIM)

    def _on_close(self):
        """Alle Bot-Prozesse beenden und App schließen."""
        for idx in list(bot_processes.keys()):
            try:
                proc = bot_processes[idx]["process"]
                if proc.poll() is None:
                    proc.terminate()
                    try:
                        proc.wait(timeout=3)
                    except subprocess.TimeoutExpired:
                        proc.kill()
            except Exception:
                pass
        bot_processes.clear()
        self.root.destroy()

    # ── Helpers ───────────────────────────────────────────
    def _log(self, msg, tag="info"):
        ts = datetime.now().strftime("%H:%M:%S")
        self.log_box.configure(state="normal")
        self.log_box.insert("end", f"[{ts}] ","dim")
        self.log_box.insert("end", msg+"\n", tag)
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def _card(self, parent, label, value, col):
        f = tk.Frame(parent, bg=CARD, padx=12, pady=8)
        f.grid(row=0, column=col, padx=(0 if col==0 else 6,0), sticky="ew")
        parent.columnconfigure(col, weight=1)
        tk.Label(f, text=label, font=CF, bg=CARD, fg=DIM).pack(anchor="w")
        lbl = tk.Label(f, text=value, font=CF_B, bg=CARD, fg=ACCENT)
        lbl.pack(anchor="w")
        return lbl

    def _edit_card(self, parent, label, var, unit, col):
        f = tk.Frame(parent, bg=CARD2, padx=12, pady=8)
        f.grid(row=0, column=col, padx=(0 if col==0 else 6,0), sticky="ew")
        tk.Label(f, text=label, font=CF, bg=CARD2, fg=DIM).pack(anchor="w")
        tk.Entry(f, textvariable=var, font=("Consolas",13,"bold"),
                 bg=CARD2, fg=ACCENT, insertbackground=ACCENT,
                 bd=0, relief="flat", width=7).pack(anchor="w")
        tk.Label(f, text=unit, font=CF, bg=CARD2, fg=DIM).pack(anchor="w")

    # ── LIZENZ-SYSTEM ─────────────────────────────────────
    def _show_license_status(self):
        """Zeigt den Lizenz-Status im Log beim Start."""
        info = get_license_info()
        if info["activated"]:
            plan_txt = info.get("plan_label", "")
            days_left = info.get("license_days_left", -1)
            if info.get("license_expired"):
                self._log(f"⚠️ Lizenz abgelaufen!  |  {info['customer']}  |  Bitte erneuern!", "error")
            elif days_left <= 3 and days_left >= 0:
                self._log(f"⚠️ Lizenz läuft in {days_left} Tag(en) ab!  |  {info['customer']}  |  Plan: {plan_txt}", "warn")
            else:
                extra = f"  |  Noch {days_left} Tage" if days_left >= 0 else ""
                self._log(f"Lizenz aktiv  |  {info['customer']}  |  Plan: {plan_txt}{extra}", "success")
        else:
            days = info["trial_days_left"]
            if days > 3:
                self._log(f"TESTVERSION  |  Noch {days} Tage kostenlos testen", "warn")
            elif days > 0:
                self._log(f"TESTVERSION  |  Nur noch {days} Tag(e)! Jetzt Lizenz kaufen!", "error")
            else:
                self._log("Testphase abgelaufen! Bitte Lizenz aktivieren.", "error")

    def _show_license_wall(self):
        """Zeigt den Aktivierungs-Bildschirm wenn Trial abgelaufen."""
        for w in self.root.winfo_children():
            w.destroy()

        self.root.geometry("520x500")
        main = tk.Frame(self.root, bg=BG)
        main.pack(fill="both", expand=True, padx=40, pady=30)

        tk.Label(main, text="⚡", font=("Consolas", 48), bg=BG, fg=ACCENT).pack(pady=(10,0))
        tk.Label(main, text="EDGETRADER", font=CF_T, bg=BG, fg=ACCENT).pack()
        tk.Label(main, text="Universal Signal Bot", font=CF, bg=BG, fg=DIM).pack()

        tk.Frame(main, bg=RED, height=2).pack(fill="x", pady=15)

        # Unterscheide: abgelaufene Lizenz vs. noch nie aktiviert
        info = get_license_info()
        if info.get("license_expired"):
            wall_title = "Lizenz abgelaufen!"
            wall_text = (f"Deine Lizenz ({info.get('plan_label','')}) ist abgelaufen.\n"
                         "Bitte verlängere deine Lizenz um fortzufahren.")
        else:
            wall_title = "Testphase abgelaufen!"
            wall_text = ("Bitte aktiviere deine Lizenz um fortzufahren.\n"
                         "Key-Format: EDGE-{Plan}-XXXX-XXXX-XXXX")

        tk.Label(main, text=wall_title,
                 font=("Consolas", 14, "bold"), bg=BG, fg=RED).pack()
        tk.Label(main, text=wall_text,
                 font=CF, bg=BG, fg=TEXT, justify="center").pack(pady=(4, 15))

        # Eingabefelder
        form = tk.Frame(main, bg=CARD, padx=20, pady=16)
        form.pack(fill="x")

        tk.Label(form, text="Registrierter Name", font=CF_B, bg=CARD, fg=DIM).pack(anchor="w")
        self.lic_name_var = tk.StringVar()
        tk.Entry(form, textvariable=self.lic_name_var, font=CF_L, bg=CARD2, fg=TEXT,
                 insertbackground=ACCENT, bd=0, relief="flat").pack(fill="x", pady=(4, 12), ipady=6)

        tk.Label(form, text="Lizenzschlüssel", font=CF_B, bg=CARD, fg=DIM).pack(anchor="w")
        self.lic_key_var = tk.StringVar()
        tk.Entry(form, textvariable=self.lic_key_var, font=CF_L, bg=CARD2, fg=ACCENT,
                 insertbackground=ACCENT, bd=0, relief="flat").pack(fill="x", pady=(4, 12), ipady=6)

        self.lic_msg = tk.Label(form, text="", font=CF, bg=CARD, fg=RED)
        self.lic_msg.pack()

        tk.Button(main, text="LIZENZ AKTIVIEREN", font=CF_L,
                  bg=GREEN, fg="#000", activebackground="#16a34a",
                  bd=0, relief="flat", cursor="hand2", padx=20, pady=12,
                  command=self._do_activate).pack(fill="x", pady=(15, 0))

        tk.Label(main, text="Lizenz kaufen: Kontaktiere Philip Babuda",
                 font=("Consolas", 8), bg=BG, fg=DIM, cursor="hand2").pack(pady=(10,0))

    def _do_activate(self):
        """Versucht die Lizenz zu aktivieren."""
        name = self.lic_name_var.get().strip()
        key = self.lic_key_var.get().strip()
        success, msg = activate_license(name, key)
        if success:
            self.lic_msg.configure(text=msg, fg=GREEN)
            # Nach 1 Sekunde die App neu laden
            self.root.after(1000, self._restart_app)
        else:
            self.lic_msg.configure(text=msg, fg=RED)

    def _restart_app(self):
        """Lädt die App nach Aktivierung neu."""
        for w in self.root.winfo_children():
            w.destroy()
        self.root.geometry("780x740")
        self.cfg = load_config()
        self._ensure_profiles()
        self._build()
        self.root.after(500, self._show_license_status)

    def _show_activation_dialog(self):
        """Öffnet den Aktivierungs-Dialog (aus dem Menü)."""
        win = tk.Toplevel(self.root)
        win.title("EdgeTrader – Lizenz aktivieren")
        win.configure(bg=BG)
        win.geometry("440x350")
        win.grab_set()
        win.resizable(False, False)

        tk.Label(win, text="⚡ Lizenz aktivieren", font=CF_L, bg=BG, fg=ACCENT).pack(pady=(20,4))

        info = get_license_info()
        if info["activated"]:
            tk.Label(win, text=f"Bereits aktiviert auf: {info['customer']}",
                     font=CF_B, bg=BG, fg=GREEN).pack(pady=10)
            tk.Button(win, text="Schließen", font=CF, bg=CARD, fg=TEXT,
                      bd=0, relief="flat", cursor="hand2", padx=16, pady=8,
                      command=win.destroy).pack(pady=10)
            return

        days = info["trial_days_left"]
        tk.Label(win, text=f"Testversion – noch {days} Tag(e) übrig",
                 font=CF, bg=BG, fg=ACCENT if days > 3 else RED).pack(pady=(0,10))

        form = tk.Frame(win, bg=CARD, padx=20, pady=16)
        form.pack(fill="x", padx=20)

        tk.Label(form, text="Registrierter Name", font=CF_B, bg=CARD, fg=DIM).pack(anchor="w")
        name_var = tk.StringVar()
        tk.Entry(form, textvariable=name_var, font=CF, bg=CARD2, fg=TEXT,
                 insertbackground=ACCENT, bd=0, relief="flat").pack(fill="x", pady=(4,10), ipady=5)

        tk.Label(form, text="Lizenzschlüssel (EDGE-{Plan}-XXXX-XXXX-XXXX)", font=CF_B, bg=CARD, fg=DIM).pack(anchor="w")
        key_var = tk.StringVar()
        tk.Entry(form, textvariable=key_var, font=CF, bg=CARD2, fg=ACCENT,
                 insertbackground=ACCENT, bd=0, relief="flat").pack(fill="x", pady=(4,10), ipady=5)

        msg_lbl = tk.Label(form, text="", font=CF, bg=CARD, fg=RED)
        msg_lbl.pack()

        def do_activate():
            success, msg = activate_license(name_var.get(), key_var.get())
            if success:
                msg_lbl.configure(text=msg, fg=GREEN)
                self._log(f"Lizenz aktiviert: {name_var.get()}", "success")
                win.after(1500, win.destroy)
                # Footer aktualisieren
                lic_info = get_license_info()
                plan_lbl = lic_info.get("plan_label", "")
                if hasattr(self, 'footer_label'):
                    self.footer_label.configure(
                        text=f"EdgeTrader v{VERSION} © 2026 by Philip Babuda  |  LIZENZIERT ({plan_lbl})  |  Alle Rechte vorbehalten")
            else:
                msg_lbl.configure(text=msg, fg=RED)

        tk.Button(win, text="AKTIVIEREN", font=CF_L,
                  bg=GREEN, fg="#000", activebackground="#16a34a",
                  bd=0, relief="flat", cursor="hand2", padx=20, pady=10,
                  command=do_activate).pack(fill="x", padx=20, pady=(12,0))

    # ── AUTO-UPDATER ──────────────────────────────────────
    def _check_for_updates(self):
        """Prüft im Hintergrund ob ein Update verfügbar ist."""
        self._log("🔄 Prüfe auf Updates...", "info")

        def on_update_found(info):
            if info.get("update_available"):
                self.root.after(0, self._show_update_banner, info)
                self.root.after(0, self._log,
                    f"⬆️  UPDATE VERFÜGBAR: v{info['latest_version']} (aktuell: v{VERSION})", "success")
                self.root.after(0, self._log,
                    f"   {info.get('changelog','')}", "warn")
            else:
                self.root.after(0, self._log,
                    f"✅ EdgeTrader v{VERSION} ist aktuell ✓", "success")

        def on_error(msg):
            self.root.after(0, self._log,
                f"⚠️ Update-Check fehlgeschlagen: {msg[:80]}", "warn")

        check_for_update(VERSION, callback=on_update_found, error_callback=on_error)

    def _check_for_updates_silent(self):
        """Update-Check für License-Wall (zeigt Popup statt Log)."""
        def on_update_found(info):
            if info.get("update_available"):
                self.root.after(0, self._show_update_popup_on_wall, info)

        check_for_update(VERSION, callback=on_update_found, error_callback=lambda m: None)

    def _show_update_popup_on_wall(self, info):
        """Zeigt Update-Hinweis als Popup über der License-Wall."""
        try:
            messagebox.showinfo(
                "Update verfügbar!",
                f"EdgeTrader v{info['latest_version']} ist verfügbar!\n\n"
                f"Aktuell: v{VERSION}\n\n"
                f"{info.get('changelog','')}\n\n"
                f"Download: {info.get('download_url','')}")
        except Exception:
            pass

    def _show_update_banner(self, info):
        """Zeigt einen Update-Banner oben in der App."""
        self.update_bar = tk.Frame(self.root, bg="#1a3a1a")
        # Vor dem Content-Frame einfügen
        self.update_bar.pack(fill="x", padx=30, pady=(0,4), before=self.content)

        tk.Label(self.update_bar,
                 text=f"  ⬆️  Update v{info['latest_version']} verfügbar!",
                 font=CF_B, bg="#1a3a1a", fg=GREEN).pack(side="left", padx=(8,0), pady=6)

        if info.get("changelog"):
            tk.Label(self.update_bar,
                     text=f"  –  {info['changelog'][:60]}",
                     font=CF, bg="#1a3a1a", fg=DIM).pack(side="left", pady=6)

        tk.Button(self.update_bar, text="⬆️ JETZT UPDATEN", font=CF_B,
                  bg=GREEN, fg="#000", bd=0, relief="flat", cursor="hand2",
                  padx=12, pady=4,
                  command=lambda: self._do_update(info)).pack(side="right", padx=8, pady=4)

        tk.Button(self.update_bar, text="✕", font=CF,
                  bg="#1a3a1a", fg=DIM, bd=0, relief="flat", cursor="hand2",
                  command=self.update_bar.destroy).pack(side="right")

    def _do_update(self, info):
        """Startet den Download und die Installation."""
        url = info.get("download_url", "")
        if not url:
            self._log("Keine Download-URL gefunden!", "error")
            return

        # Banner in Fortschrittsanzeige umwandeln
        for w in self.update_bar.winfo_children():
            w.destroy()

        tk.Label(self.update_bar,
                 text="  Lade Update herunter...",
                 font=CF_B, bg="#1a3a1a", fg=ACCENT).pack(side="left", padx=8, pady=6)

        self.update_progress = tk.Label(self.update_bar,
                 text="0%", font=CF_B, bg="#1a3a1a", fg=GREEN)
        self.update_progress.pack(side="left", pady=6)

        self._log(f"Lade Update v{info['latest_version']} herunter...", "warn")

        def on_progress(percent):
            if percent == -1:
                self.root.after(0, self._log, "Download fehlgeschlagen!", "error")
                self.root.after(0, self.update_bar.destroy)
            elif percent >= 100:
                self.root.after(0, self.update_progress.configure, {"text": "Starte Installer..."})
                self.root.after(0, self._log, "Download fertig – Installer wird gestartet...", "success")
            else:
                self.root.after(0, self.update_progress.configure, {"text": f"{percent}%"})

        download_and_install(url, progress_callback=on_progress)


if __name__ == "__main__":
    root = tk.Tk()
    EdgeTraderApp(root)
    root.mainloop()
