"""
EdgeTrader – Universal Signal Bot
by Philip Babuda
Wird von EdgeTrader UI gestartet – liest Einstellungen aus edgetrader_config.json
"""

import re, asyncio, logging, json, os, sys, threading, time
from telethon import TelegramClient, events
from telethon.errors import SessionPasswordNeededError
from binance.client import Client
from binance.enums import *
from trade_history import TradeHistory

# ── Pfade ────────────────────────────────────────────────
def get_app_dir() -> str:
    base = os.environ.get("APPDATA", os.path.expanduser("~"))
    app_dir = os.path.join(base, "EdgeTrader")
    os.makedirs(app_dir, exist_ok=True)
    return app_dir

APP_DIR = get_app_dir()

# ── Config laden ─────────────────────────────────────────
CONFIG_FILE = os.path.join(APP_DIR, "edgetrader_config.json")

def load_profile() -> tuple:
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    # Profil-Index: aus Kommandozeile oder active_profile
    if len(sys.argv) > 1:
        try:
            idx = int(sys.argv[1])
        except ValueError:
            idx = cfg.get("active_profile", 0)
    else:
        idx = cfg.get("active_profile", 0)
    return cfg["profiles"][idx], idx

P, PROFILE_INDEX = load_profile()

# ── Telegram Defaults (EdgeTrader App-Credentials) ──
_DEFAULT_TG_API_ID   = "31561693"
_DEFAULT_TG_API_HASH = "76831e21ac32da38129342a94e05ab94"

TELEGRAM_API_ID     = int(P.get("telegram_api_id") or _DEFAULT_TG_API_ID)
TELEGRAM_API_HASH   = P.get("telegram_api_hash") or _DEFAULT_TG_API_HASH
TELEGRAM_BOT        = P["telegram_channel"]
BINANCE_API_KEY     = P["api_key"]
BINANCE_API_SECRET  = P["api_secret"]
TESTNET             = P.get("testnet", True)
LEVERAGE            = int(P.get("leverage", 5))
CAPITAL_PER_TRADE   = float(P.get("capital", 100))
SL_PERCENT          = float(P.get("sl_percent", 1.5))

# ── Feature Toggles ──────────────────────────────────
TP_ENABLED          = P.get("tp_enabled", True)
SL_ENABLED          = P.get("sl_enabled", True)
AUTO_SL_ENABLED     = P.get("auto_sl_enabled", True)
TRAILING_ENABLED    = P.get("trailing_enabled", False)
TRAILING_PERCENT    = float(P.get("trailing_percent", 1.0))
LIMIT_INV_ENABLED   = P.get("limit_invalidation_enabled", True)
LIMIT_INV_PERCENT   = float(P.get("limit_invalidation_percent", 2.0))

# ── Signal Mapping laden ──────────────────────────────────
def _terms(key: str) -> list:
    raw = P.get(key, "")
    return [t.strip() for t in raw.split(",") if t.strip()]

def _build_pattern(terms: list) -> str:
    return "|".join(re.escape(t) for t in terms)

MAP_LONG   = _build_pattern(_terms("map_long"))   or "LONG|BUY"
MAP_SHORT  = _build_pattern(_terms("map_short"))  or "SHORT|SELL"
MAP_PAIR   = _build_pattern(_terms("map_pair"))   or "Pair"
MAP_ENTRY  = _build_pattern(_terms("map_entry"))  or "Entry"
MAP_TP     = _build_pattern(_terms("map_tp"))     or "TP"
MAP_SL     = _build_pattern(_terms("map_sl"))     or "SL"
MAP_CLOSE  = _build_pattern(_terms("map_close"))  or "CLOSED"
MAP_MARKET = _build_pattern(_terms("map_market")) or "MARKET|Markt|MKT"
MAP_LIMIT  = _build_pattern(_terms("map_limit"))  or "LIMIT|LMT"

# ── Logging ───────────────────────────────────────────────
LOG_FILE = os.path.join(APP_DIR, f"edgetrader_{PROFILE_INDEX}.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler()
    ]
)
log = logging.getLogger(__name__)
open_trades = {}   # { signal_nr: {"symbol": str, "trade_id": int} }
trade_db = TradeHistory()

# ── Binance Client ────────────────────────────────────────
binance = Client(
    api_key=BINANCE_API_KEY,
    api_secret=BINANCE_API_SECRET,
    testnet=TESTNET
)

# ── Hedge Mode erkennen ──────────────────────────────────
HEDGE_MODE = False
try:
    _pm = binance.futures_get_position_mode()
    HEDGE_MODE = _pm.get("dualSidePosition", False)
    if HEDGE_MODE:
        log.info("📌 Hedge Mode (Dual Position) erkannt – positionSide wird gesetzt")
    else:
        log.info("📌 One-Way Mode erkannt")
except Exception as e:
    log.warning(f"Position-Mode-Check fehlgeschlagen: {e}")


def _pos_side_kwargs(direction: str, is_close: bool = False) -> dict:
    """Gibt positionSide-Parameter für Hedge Mode zurück."""
    if not HEDGE_MODE:
        return {}
    # Im Hedge Mode: LONG-Position öffnen → positionSide=LONG
    # LONG-Position schließen → positionSide=LONG (mit SELL)
    return {"positionSide": direction}


def setup_symbol(symbol: str):
    try:
        binance.futures_change_leverage(symbol=symbol, leverage=LEVERAGE)
        binance.futures_change_margin_type(symbol=symbol, marginType="CROSSED")
    except Exception as e:
        if "No need to change" not in str(e):
            log.warning(f"Symbol Setup: {e}")


def _get_symbol_info(symbol: str) -> dict:
    """Holt LOT_SIZE (stepSize) und PRICE_FILTER (tickSize) für ein Symbol."""
    try:
        info = binance.futures_exchange_info()
        for s in info["symbols"]:
            if s["symbol"] == symbol:
                result = {"step": 0.001, "tick": 0.01}
                for fi in s["filters"]:
                    if fi["filterType"] == "LOT_SIZE":
                        result["step"] = float(fi["stepSize"])
                    elif fi["filterType"] == "PRICE_FILTER":
                        result["tick"] = float(fi["tickSize"])
                return result
    except Exception as e:
        log.warning(f"Symbol-Info Fehler: {e}")
    return {"step": 0.001, "tick": 0.01}


def _round_to_tick(price: float, tick: float) -> float:
    """Rundet einen Preis auf die nächste gültige Tick-Size."""
    if tick <= 0:
        return price
    prec = max(0, len(str(tick).rstrip("0").split(".")[-1]))
    return round(round(price / tick) * tick, prec)


def get_quantity(symbol: str, sym_info: dict = None) -> float:
    try:
        price = float(binance.futures_symbol_ticker(symbol=symbol)["price"])
        if sym_info is None:
            sym_info = _get_symbol_info(symbol)
        step = sym_info["step"]
        raw  = (CAPITAL_PER_TRADE * LEVERAGE) / price
        prec = len(str(step).rstrip("0").split(".")[-1])
        return round(raw - (raw % step), prec)
    except Exception as e:
        log.error(f"Quantity Fehler: {e}"); return 0.0


def calc_sl(entry: float, direction: str) -> float:
    """Berechnet SL aus Entry ± SL_PERCENT."""
    offset = entry * (SL_PERCENT / 100)
    sl = round(entry - offset if direction == "LONG" else entry + offset, 8)
    log.info(f"🧮 SL berechnet: Entry {entry} ± {SL_PERCENT}% → {sl}")
    return sl


def open_position(symbol: str, direction: str,
                  entry: float = None, tp_list: list = None, sl: float = None,
                  order_type: str = "MARKET", signal_nr: str = "0"):
    setup_symbol(symbol)
    sym_info = _get_symbol_info(symbol)
    tick     = sym_info["tick"]
    qty      = get_quantity(symbol, sym_info)
    if qty <= 0:
        log.error("Menge = 0 – Abbruch"); return

    if tp_list is None:
        tp_list = []

    side       = SIDE_BUY  if direction == "LONG" else SIDE_SELL
    close_side = SIDE_SELL if direction == "LONG" else SIDE_BUY

    # SL aus % berechnen falls nicht im Signal vorhanden
    if sl is None and entry and AUTO_SL_ENABLED:
        sl = calc_sl(entry, direction)

    # Preise auf Tick-Size runden
    if entry: entry = _round_to_tick(entry, tick)
    tp_list = [_round_to_tick(tp, tick) for tp in tp_list]
    if sl:    sl    = _round_to_tick(sl, tick)

    # TP-Mengen berechnen (Verteilung über TP-Level)
    tp_quantities = _calc_tp_quantities(qty, len(tp_list), sym_info) if tp_list else []

    # Limit ohne Entry-Preis → Fallback auf Market
    if order_type == "LIMIT" and not entry:
        log.warning("⚠️ LIMIT-Order ohne Entry-Preis – falle auf MARKET zurück")
        order_type = "MARKET"

    # Hedge Mode kwargs für Entry-Orders
    pos_kwargs = _pos_side_kwargs(direction)

    # Bei LIMIT: Prüfe ob Entry-Preis für Binance-LIMIT gültig ist
    # LONG LIMIT → Entry muss <= aktueller Preis (kaufe billiger)
    # SHORT LIMIT → Entry muss >= aktueller Preis (verkaufe teurer)
    # Sonst → STOP_MARKET verwenden (Entry wird als stopPrice genutzt)
    actual_order_type = order_type
    if order_type == "LIMIT" and entry:
        try:
            cur_price = float(binance.futures_symbol_ticker(symbol=symbol)["price"])
            if direction == "LONG" and entry > cur_price:
                actual_order_type = "STOP"
                log.info(f"📌 LONG Entry {entry} > Markt {cur_price} → verwende STOP statt LIMIT")
            elif direction == "SHORT" and entry < cur_price:
                actual_order_type = "STOP"
                log.info(f"📌 SHORT Entry {entry} < Markt {cur_price} → verwende STOP statt LIMIT")
        except Exception:
            pass

    trade_id = None
    try:
        if order_type == "LIMIT":
            if actual_order_type == "STOP":
                # STOP-MARKET: wartet bis Preis Entry erreicht, dann Market-Order
                o = binance.futures_create_order(
                    symbol=symbol, side=side,
                    type=FUTURE_ORDER_TYPE_STOP_MARKET,
                    stopPrice=entry, closePosition=False,
                    timeInForce="GTE_GTC", workingType="MARK_PRICE",
                    quantity=qty, **pos_kwargs)
            else:
                o = binance.futures_create_order(
                    symbol=symbol, side=side,
                    type=ORDER_TYPE_LIMIT, quantity=qty,
                    price=entry, timeInForce=TIME_IN_FORCE_GTC,
                    **pos_kwargs)
            order_id = o['orderId']
            log.info(f"✅ {actual_order_type} {direction}: {symbol} | {qty} @ {entry} | ID: {order_id}")

            # Trade in DB speichern
            trade_id = trade_db.record_open(
                profile_index=PROFILE_INDEX, profile_name=P.get("name",""),
                signal_nr=signal_nr, symbol=symbol, direction=direction,
                order_type=actual_order_type, entry_price=entry, quantity=qty,
                leverage=LEVERAGE, capital=CAPITAL_PER_TRADE,
                tp_prices=tp_list, sl_price=sl,
                broker=P.get("broker",""), testnet=TESTNET)
            log.info(f"📝 Trade #{trade_id} in Datenbank gespeichert")
            print(f"TRADE_OPEN|{json.dumps({'trade_id':trade_id,'symbol':symbol,'direction':direction,'entry':entry})}", flush=True)

            # Bei LIMIT/STOP: TP/SL erst setzen wenn Order gefüllt wird
            if (tp_list and TP_ENABLED) or (sl and SL_ENABLED):
                tp_info = ", ".join([str(tp) for tp in tp_list]) if tp_list else "–"
                log.info(f"⏳ Überwache {actual_order_type}-Order – TP/SL werden nach Füllung gesetzt")
                log.info(f"   TP: [{tp_info}] | SL: {sl}")
                threading.Thread(
                    target=_monitor_limit_fill,
                    args=(symbol, order_id, close_side, qty, tp_list, tp_quantities,
                          sl, direction, trade_id),
                    daemon=True
                ).start()
        else:
            o = binance.futures_create_order(
                symbol=symbol, side=side,
                type=ORDER_TYPE_MARKET, quantity=qty,
                **pos_kwargs)
            log.info(f"✅ MARKET {direction}: {symbol} | {qty} | ID: {o['orderId']}")

            # Trade in DB speichern
            actual_entry = entry
            if not actual_entry:
                try:
                    actual_entry = float(binance.futures_symbol_ticker(symbol=symbol)["price"])
                except Exception:
                    pass
            trade_id = trade_db.record_open(
                profile_index=PROFILE_INDEX, profile_name=P.get("name",""),
                signal_nr=signal_nr, symbol=symbol, direction=direction,
                order_type=order_type, entry_price=actual_entry, quantity=qty,
                leverage=LEVERAGE, capital=CAPITAL_PER_TRADE,
                tp_prices=tp_list, sl_price=sl,
                broker=P.get("broker",""), testnet=TESTNET)
            log.info(f"📝 Trade #{trade_id} in Datenbank gespeichert")
            print(f"TRADE_OPEN|{json.dumps({'trade_id':trade_id,'symbol':symbol,'direction':direction,'entry':actual_entry})}", flush=True)

            # TP-Orders setzen (Multi-TP: jede mit Teilmenge)
            tp_order_ids = {}  # {orderId: "TP1", "TP2", ...}
            if tp_list and TP_ENABLED:
                for i, (tp_price, tp_qty) in enumerate(zip(tp_list, tp_quantities)):
                    if tp_qty <= 0:
                        continue
                    try:
                        tp_resp = binance.futures_create_order(
                            symbol=symbol, side=close_side,
                            type=FUTURE_ORDER_TYPE_TAKE_PROFIT_MARKET,
                            stopPrice=tp_price, quantity=tp_qty,
                            timeInForce="GTE_GTC", workingType="MARK_PRICE",
                            **_pos_side_kwargs(direction))
                        tp_order_ids[tp_resp['orderId']] = f"TP{i+1}"
                        log.info(f"🎯 TP{i+1} gesetzt: {tp_price} | Qty: {tp_qty} | ID: {tp_resp['orderId']}")
                    except Exception as e:
                        log.error(f"TP{i+1} Fehler: {e}")

            # SL mit closePosition=True (schließt gesamte Rest-Position)
            sl_order_id = None
            if sl and SL_ENABLED:
                try:
                    sl_resp = binance.futures_create_order(
                        symbol=symbol, side=close_side,
                        type=FUTURE_ORDER_TYPE_STOP_MARKET,
                        stopPrice=sl, closePosition=True,
                        timeInForce="GTE_GTC", workingType="MARK_PRICE",
                        **_pos_side_kwargs(direction))
                    sl_order_id = sl_resp.get('orderId')
                    log.info(f"🛑 SL gesetzt: {sl}  ({SL_PERCENT}% vom Entry) | ID: {sl_order_id}")
                except Exception as e:
                    log.error(f"SL Fehler: {e}")

            # Trailing TP aktivieren (wenn TP1 erreicht → Trailing übernimmt)
            if TRAILING_ENABLED and tp_order_ids and len(tp_list) > 1:
                TrailingTPManager(
                    symbol=symbol, direction=direction,
                    tp_order_ids=tp_order_ids, sl_order_id=sl_order_id,
                    remaining_qty=qty, trailing_percent=TRAILING_PERCENT,
                    trade_id=trade_id
                ).start_monitoring()
                log.info(f"📈 Trailing-Monitor aktiviert: {symbol} | Trail: {TRAILING_PERCENT}%")

    except Exception as e:
        log.error(f"Order Fehler: {e}")

    return trade_id


def _monitor_limit_fill(symbol: str, order_id: int, close_side: str,
                        qty: float, tp_list: list = None, tp_quantities: list = None,
                        sl: float = None, direction: str = "LONG",
                        trade_id: int = None):
    """Überwacht eine LIMIT-Order und setzt TP/SL nach Füllung."""
    if tp_list is None:
        tp_list = []
    if tp_quantities is None:
        tp_quantities = []
    while True:
        time.sleep(5)
        try:
            order = binance.futures_get_order(symbol=symbol, orderId=order_id)
            status = order.get("status", "")

            # ── Limit-Invalidierung: Prüfe ob Markt zu weit weg ──
            if status == "NEW" and LIMIT_INV_ENABLED:
                try:
                    entry_price = float(order.get("price", 0))
                    if entry_price > 0:
                        cur = float(binance.futures_symbol_ticker(symbol=symbol)["price"])
                        deviation = abs(cur - entry_price) / entry_price * 100
                        if deviation > LIMIT_INV_PERCENT:
                            binance.futures_cancel_order(symbol=symbol, orderId=order_id)
                            log.warning(f"⚠️ LIMIT-Order gecancelt: {symbol} | "
                                        f"Markt {deviation:.1f}% vom Entry ({LIMIT_INV_PERCENT}% Toleranz)")
                            if trade_id:
                                trade_db.record_close(trade_id, cur, "LIMIT_INVALIDATED")
                                print(f"TRADE_CLOSE|{json.dumps({'trade_id':trade_id,'symbol':symbol,'exit':cur,'reason':'LIMIT_INVALIDATED'})}", flush=True)
                            return
                except Exception as e:
                    log.warning(f"Invalidierungs-Check Fehler: {e}")

            if status == "FILLED":
                log.info(f"✅ LIMIT-Order gefüllt: {symbol} | ID: {order_id}")
                try:
                    # Aktuellen Preis holen für TP-Validierung
                    try:
                        current_price = float(binance.futures_symbol_ticker(symbol=symbol)["price"])
                    except Exception:
                        current_price = None

                    # Multi-TP setzen
                    tp_order_ids = {}
                    if tp_list and TP_ENABLED:
                        for i, (tp_price, tp_qty) in enumerate(zip(tp_list, tp_quantities)):
                            if tp_qty <= 0:
                                continue
                            try:
                                # Prüfe ob TP schon erreicht wurde (would immediately trigger)
                                tp_already_hit = False
                                if current_price:
                                    if direction == "LONG" and current_price >= tp_price:
                                        tp_already_hit = True
                                    elif direction == "SHORT" and current_price <= tp_price:
                                        tp_already_hit = True

                                if tp_already_hit:
                                    # TP schon erreicht → sofort Market-Close für diesen Teil
                                    binance.futures_create_order(
                                        symbol=symbol, side=close_side,
                                        type=ORDER_TYPE_MARKET, quantity=tp_qty,
                                        **_pos_side_kwargs(direction))
                                    log.info(f"🎯 TP{i+1} bereits erreicht → Market-Close: {tp_qty} @ ~{current_price}")
                                else:
                                    tp_resp = binance.futures_create_order(
                                        symbol=symbol, side=close_side,
                                        type=FUTURE_ORDER_TYPE_TAKE_PROFIT_MARKET,
                                        stopPrice=tp_price, quantity=tp_qty,
                                        timeInForce="GTE_GTC", workingType="MARK_PRICE",
                                        **_pos_side_kwargs(direction))
                                    tp_order_ids[tp_resp['orderId']] = f"TP{i+1}"
                                    log.info(f"🎯 TP{i+1} gesetzt: {tp_price} | Qty: {tp_qty} | ID: {tp_resp['orderId']}")
                            except Exception as e:
                                log.error(f"TP{i+1} Fehler: {e}")

                    sl_order_id = None
                    if sl and SL_ENABLED:
                        try:
                            # Prüfe ob SL schon erreicht wurde
                            sl_already_hit = False
                            if current_price:
                                if direction == "LONG" and current_price <= sl:
                                    sl_already_hit = True
                                elif direction == "SHORT" and current_price >= sl:
                                    sl_already_hit = True

                            if sl_already_hit:
                                binance.futures_create_order(
                                    symbol=symbol, side=close_side,
                                    type=ORDER_TYPE_MARKET, closePosition=True,
                                    **_pos_side_kwargs(direction))
                                log.warning(f"🛑 SL bereits erreicht → Market-Close: {symbol}")
                            else:
                                sl_resp = binance.futures_create_order(
                                    symbol=symbol, side=close_side,
                                    type=FUTURE_ORDER_TYPE_STOP_MARKET,
                                    stopPrice=sl, closePosition=True,
                                    timeInForce="GTE_GTC", workingType="MARK_PRICE",
                                    **_pos_side_kwargs(direction))
                                sl_order_id = sl_resp.get('orderId')
                                log.info(f"🛑 SL gesetzt: {sl}  ({SL_PERCENT}% vom Entry) | ID: {sl_order_id}")
                        except Exception as e:
                            log.error(f"SL Fehler: {e}")

                    # Trailing TP aktivieren
                    if TRAILING_ENABLED and tp_order_ids and len(tp_list) > 1:
                        TrailingTPManager(
                            symbol=symbol, direction=direction,
                            tp_order_ids=tp_order_ids, sl_order_id=sl_order_id,
                            remaining_qty=qty, trailing_percent=TRAILING_PERCENT,
                            trade_id=trade_id
                        ).start_monitoring()
                        log.info(f"📈 Trailing-Monitor aktiviert: {symbol} | Trail: {TRAILING_PERCENT}%")

                except Exception as e:
                    log.error(f"TP/SL Fehler nach LIMIT-Fill: {e}")
                return

            elif status in ("CANCELED", "CANCELLED", "EXPIRED", "REJECTED"):
                log.warning(f"⚠️ LIMIT-Order {status}: {symbol} | ID: {order_id} – kein TP/SL")
                return

        except Exception as e:
            log.warning(f"Monitor-Check Fehler: {e}")


class TrailingTPManager:
    """Überwacht TP-Fills und implementiert Trailing Stop Logik."""

    def __init__(self, symbol, direction, tp_order_ids, sl_order_id,
                 remaining_qty, trailing_percent, trade_id=None):
        self.symbol = symbol
        self.direction = direction
        self.tp_order_ids = tp_order_ids  # {order_id: "TP1", "TP2", ...}
        self.sl_order_id = sl_order_id
        self.remaining_qty = remaining_qty
        self.trailing_percent = trailing_percent
        self.trade_id = trade_id
        self.highest_price = 0
        self.lowest_price = float('inf')
        self.trailing_active = False

    def start_monitoring(self):
        threading.Thread(target=self._monitor_loop, daemon=True).start()

    def _monitor_loop(self):
        log.info(f"📈 Trailing-Monitor gestartet: {self.symbol} | Trail: {self.trailing_percent}%")
        while True:
            time.sleep(3)
            try:
                # Prüfe ob TP-Orders gefüllt wurden
                for oid, level in list(self.tp_order_ids.items()):
                    try:
                        order = binance.futures_get_order(symbol=self.symbol, orderId=oid)
                        if order["status"] == "FILLED":
                            filled_qty = float(order.get("executedQty", 0))
                            self.remaining_qty -= filled_qty
                            log.info(f"🎯 {level} erreicht: {self.symbol} | Qty: {filled_qty}")
                            del self.tp_order_ids[oid]
                            self._on_tp_filled(level)
                        elif order["status"] in ("CANCELED", "CANCELLED", "EXPIRED"):
                            del self.tp_order_ids[oid]
                    except Exception:
                        pass

                # Trailing Stop aktualisieren wenn aktiv
                if self.trailing_active:
                    self._update_trailing_stop()

                # Wenn keine TPs mehr und kein Trailing → fertig
                if not self.tp_order_ids and not self.trailing_active:
                    return

            except Exception as e:
                log.warning(f"Trailing Monitor Fehler: {e}")

    def _on_tp_filled(self, level):
        """Wenn TP1 erreicht → Trailing aktivieren."""
        if level == "TP1" and not self.trailing_active:
            # Restliche TP-Orders canceln
            for oid in list(self.tp_order_ids.keys()):
                try:
                    binance.futures_cancel_order(symbol=self.symbol, orderId=oid)
                    log.info(f"❌ {self.tp_order_ids[oid]} gecancelt (Trailing übernimmt)")
                except Exception:
                    pass
            self.tp_order_ids.clear()

            # Trailing aktivieren
            self.trailing_active = True
            try:
                current = float(binance.futures_symbol_ticker(symbol=self.symbol)["price"])
            except Exception:
                current = 0
            if self.direction == "LONG":
                self.highest_price = current
            else:
                self.lowest_price = current
            log.info(f"📈 Trailing aktiviert: {self.symbol} ab {current} | Trail: {self.trailing_percent}%")

    def _update_trailing_stop(self):
        """Verfolgt den Preis und schließt bei Rückfall."""
        try:
            current = float(binance.futures_symbol_ticker(symbol=self.symbol)["price"])
        except Exception:
            return

        if self.direction == "LONG":
            if current > self.highest_price:
                self.highest_price = current
            trail_price = self.highest_price * (1 - self.trailing_percent / 100)
            if current <= trail_price:
                self._execute_trailing_close(current)
                return
        else:  # SHORT
            if current < self.lowest_price:
                self.lowest_price = current
            trail_price = self.lowest_price * (1 + self.trailing_percent / 100)
            if current >= trail_price:
                self._execute_trailing_close(current)
                return

    def _execute_trailing_close(self, price):
        """Schließt die Rest-Position per Market."""
        close_side = SIDE_SELL if self.direction == "LONG" else SIDE_BUY
        try:
            # Bestehenden SL canceln
            if self.sl_order_id:
                try:
                    binance.futures_cancel_order(symbol=self.symbol, orderId=self.sl_order_id)
                except Exception:
                    pass

            # Rest-Position schließen
            if self.remaining_qty > 0:
                trail_kwargs = _pos_side_kwargs(self.direction)
                if HEDGE_MODE:
                    binance.futures_create_order(
                        symbol=self.symbol, side=close_side,
                        type=ORDER_TYPE_MARKET,
                        quantity=self.remaining_qty, **trail_kwargs)
                else:
                    binance.futures_create_order(
                        symbol=self.symbol, side=close_side,
                        type=ORDER_TYPE_MARKET,
                        quantity=self.remaining_qty, reduceOnly=True)
                log.info(f"📈 Trailing Close: {self.symbol} @ ~{price:.2f} | Qty: {self.remaining_qty}")

                # Trade in DB schließen
                if self.trade_id:
                    trade_db.record_close(self.trade_id, price, "TRAILING_TP")
                    print(f"TRADE_CLOSE|{json.dumps({'trade_id':self.trade_id,'symbol':self.symbol,'exit':price,'reason':'TRAILING_TP'})}", flush=True)

            self.trailing_active = False
        except Exception as e:
            log.error(f"Trailing Close Fehler: {e}")


def _recover_open_positions():
    """Prüft beim Start ob offene Positionen auf Binance existieren
    und stellt open_trades + Überwachung wieder her."""
    global open_trades
    log.info("🔍 Prüfe offene Positionen auf Binance...")

    try:
        # 1. Alle aktiven Positionen von Binance holen
        positions = binance.futures_position_information()
        active_positions = {}
        for pos in positions:
            qty = float(pos.get("positionAmt", 0))
            if qty == 0:
                continue
            sym = pos["symbol"]
            direction = "LONG" if qty > 0 else "SHORT"
            entry_price = float(pos.get("entryPrice", 0))
            active_positions[sym] = {
                "qty": abs(qty),
                "direction": direction,
                "entry_price": entry_price,
                "unrealized_pnl": float(pos.get("unRealizedProfit", 0)),
            }

        if not active_positions:
            log.info("✅ Keine offenen Positionen auf Binance gefunden.")
            return

        log.info(f"📊 {len(active_positions)} offene Position(en) auf Binance gefunden:")
        for sym, info in active_positions.items():
            log.info(f"   • {sym}: {info['direction']} | Qty: {info['qty']} | "
                     f"Entry: {info['entry_price']} | uPnL: {info['unrealized_pnl']:.4f}")

        # 2. Offene Trades aus DB laden
        db_open_trades = trade_db.get_open_trades(profile_index=PROFILE_INDEX)
        db_by_symbol = {}
        for t in db_open_trades:
            db_by_symbol[t["symbol"]] = t

        # 3. Offene Orders von Binance holen (TP/SL-Orders)
        try:
            all_open_orders = binance.futures_get_open_orders()
        except Exception:
            all_open_orders = []

        orders_by_symbol = {}
        for order in all_open_orders:
            sym = order["symbol"]
            if sym not in orders_by_symbol:
                orders_by_symbol[sym] = []
            orders_by_symbol[sym].append(order)

        # 4. Für jede offene Position: Abgleich + Recovery
        for sym, pos_info in active_positions.items():
            direction = pos_info["direction"]
            qty = pos_info["qty"]
            entry = pos_info["entry_price"]

            # DB-Eintrag suchen
            db_trade = db_by_symbol.get(sym)
            trade_id = db_trade["id"] if db_trade else None
            signal_nr = db_trade.get("signal_nr", "R") if db_trade else "R"

            # open_trades Dict wiederherstellen
            open_trades[signal_nr] = {"symbol": sym, "trade_id": trade_id}

            # Bestehende Orders für dieses Symbol prüfen
            sym_orders = orders_by_symbol.get(sym, [])
            has_tp = False
            has_sl = False
            tp_order_ids = {}
            sl_order_id = None

            for order in sym_orders:
                otype = order.get("type", "")
                ostatus = order.get("status", "")
                if ostatus not in ("NEW", "PARTIALLY_FILLED"):
                    continue
                if otype in ("TAKE_PROFIT_MARKET", "TAKE_PROFIT"):
                    has_tp = True
                    tp_order_ids[order["orderId"]] = f"TP"
                elif otype in ("STOP_MARKET", "STOP"):
                    has_sl = True
                    sl_order_id = order["orderId"]

            # Status loggen
            tp_status = f"✅ {len(tp_order_ids)} TP-Order(s)" if has_tp else "❌ Kein TP"
            sl_status = "✅ SL vorhanden" if has_sl else "❌ Kein SL"
            log.info(f"   {sym}: {tp_status} | {sl_status}")

            # Falls kein DB-Eintrag → neuen anlegen
            if not trade_id:
                trade_id = trade_db.record_open(
                    profile_index=PROFILE_INDEX, profile_name=P.get("name", ""),
                    signal_nr=signal_nr, symbol=sym, direction=direction,
                    order_type="RECOVERED", entry_price=entry, quantity=qty,
                    leverage=LEVERAGE, capital=CAPITAL_PER_TRADE,
                    tp_prices=[], sl_price=None,
                    broker=P.get("broker", ""), testnet=TESTNET)
                open_trades[signal_nr] = {"symbol": sym, "trade_id": trade_id}
                log.warning(f"⚠️ {sym}: Kein DB-Eintrag → neuer Trade #{trade_id} angelegt")

            # Falls SL fehlt → nachsetzen
            if not has_sl and SL_ENABLED and AUTO_SL_ENABLED:
                try:
                    sl_price = calc_sl(entry, direction)
                    sym_info = _get_symbol_info(sym)
                    sl_price = _round_to_tick(sl_price, sym_info["tick"])
                    close_side = SIDE_SELL if direction == "LONG" else SIDE_BUY

                    # Prüfe ob SL schon erreicht
                    current_price = float(binance.futures_symbol_ticker(symbol=sym)["price"])
                    sl_already_hit = False
                    if direction == "LONG" and current_price <= sl_price:
                        sl_already_hit = True
                    elif direction == "SHORT" and current_price >= sl_price:
                        sl_already_hit = True

                    if sl_already_hit:
                        log.warning(f"🛑 {sym}: SL bereits erreicht ({current_price} vs SL {sl_price}) "
                                    f"→ Position wird NICHT automatisch geschlossen (manuell prüfen!)")
                    else:
                        sl_resp = binance.futures_create_order(
                            symbol=sym, side=close_side,
                            type=FUTURE_ORDER_TYPE_STOP_MARKET,
                            stopPrice=sl_price, closePosition=True,
                            timeInForce="GTE_GTC", workingType="MARK_PRICE",
                            **_pos_side_kwargs(direction))
                        sl_order_id = sl_resp.get('orderId')
                        log.info(f"🛑 {sym}: SL nachgesetzt: {sl_price} ({SL_PERCENT}%) | ID: {sl_order_id}")
                except Exception as e:
                    log.error(f"SL Recovery Fehler {sym}: {e}")

            # Trailing TP wieder aktivieren wenn TP-Orders existieren und Trailing an
            if TRAILING_ENABLED and tp_order_ids and has_tp:
                TrailingTPManager(
                    symbol=sym, direction=direction,
                    tp_order_ids=tp_order_ids, sl_order_id=sl_order_id,
                    remaining_qty=qty, trailing_percent=TRAILING_PERCENT,
                    trade_id=trade_id
                ).start_monitoring()
                log.info(f"📈 {sym}: Trailing-Monitor wiederhergestellt")

        # 5. DB-Trades die auf Binance nicht mehr existieren → schließen
        #    (z.B. TP/SL wurde ausgelöst während Bot offline war)
        for db_trade in db_open_trades:
            sym = db_trade["symbol"]
            if sym not in active_positions:
                # Position existiert nicht mehr auf Binance → wurde geschlossen
                try:
                    last_price = float(binance.futures_symbol_ticker(symbol=sym)["price"])
                except Exception:
                    last_price = None
                trade_db.record_close(db_trade["id"], last_price, "CLOSED_WHILE_OFFLINE")
                log.info(f"📝 {sym}: Trade #{db_trade['id']} war bereits geschlossen (offline) → DB aktualisiert")
                print(f"TRADE_CLOSE|{json.dumps({'trade_id':db_trade['id'],'symbol':sym,'exit':last_price,'reason':'CLOSED_WHILE_OFFLINE'})}", flush=True)

        log.info(f"✅ Recovery abgeschlossen: {len(open_trades)} aktive Trade(s) wiederhergestellt")
        print(f"RECOVERY|{json.dumps({'count': len(open_trades), 'symbols': list(active_positions.keys())})}", flush=True)

    except Exception as e:
        log.error(f"❌ Recovery Fehler: {e}")


def close_position(symbol: str, trade_id: int = None):
    exit_price = None
    try:
        for pos in binance.futures_position_information(symbol=symbol):
            qty = float(pos["positionAmt"])
            if qty == 0: continue
            side = SIDE_SELL if qty > 0 else SIDE_BUY
            direction = "LONG" if qty > 0 else "SHORT"
            # Aktuellen Preis als Exit-Preis merken
            try:
                exit_price = float(binance.futures_symbol_ticker(symbol=symbol)["price"])
            except Exception:
                pass
            close_kwargs = _pos_side_kwargs(direction)
            # Hedge Mode: kein reduceOnly, sondern positionSide
            if HEDGE_MODE:
                binance.futures_create_order(
                    symbol=symbol, side=side,
                    type=ORDER_TYPE_MARKET,
                    quantity=abs(qty), **close_kwargs)
            else:
                binance.futures_create_order(
                    symbol=symbol, side=side,
                    type=ORDER_TYPE_MARKET,
                    quantity=abs(qty), reduceOnly=True)
            log.info(f"🔒 Geschlossen: {symbol} | {abs(qty)}")
        binance.futures_cancel_all_open_orders(symbol=symbol)

        # Trade in DB als geschlossen markieren
        if trade_id:
            trade_db.record_close(trade_id, exit_price, "CLOSE_SIGNAL")
            log.info(f"📝 Trade #{trade_id} geschlossen")
            print(f"TRADE_CLOSE|{json.dumps({'trade_id':trade_id,'symbol':symbol,'exit':exit_price,'reason':'CLOSE_SIGNAL'})}", flush=True)
        else:
            # Fallback: alle offenen Trades für dieses Symbol schließen
            trade_db.record_close_by_symbol(symbol, exit_price, "CLOSE_SIGNAL")

    except Exception as e:
        log.error(f"Close Fehler: {e}")


# ── Signal Parser ─────────────────────────────────────────
def _num(text: str, pattern: str):
    m = re.search(rf"(?:{pattern})\s*:\s*([0-9]+(?:[.,][0-9]+)?)", text, re.IGNORECASE)
    return float(m.group(1).replace(",", ".")) if m else None


def _num_all(text: str, pattern: str) -> list:
    """Findet ALLE Matches für pattern + optionale Zahl + : Wert.
    z.B. TP1: 100, TP2: 110, TP3: 120 → [100.0, 110.0, 120.0]"""
    matches = re.findall(
        rf"(?:{pattern})\s*\d?\s*:\s*([0-9]+(?:[.,][0-9]+)?)", text, re.IGNORECASE)
    return [float(m.replace(",", ".")) for m in matches] if matches else []


def _calc_tp_quantities(total_qty: float, tp_count: int, sym_info: dict) -> list:
    """Verteilt die Gesamtmenge auf TP-Level (z.B. 33%, 33%, 34%)."""
    if tp_count <= 0:
        return []
    if tp_count == 1:
        return [total_qty]

    dist_raw = P.get("tp_distribution", "33,33,34")
    distribution = []
    for x in dist_raw.split(","):
        try:
            distribution.append(float(x.strip()))
        except ValueError:
            pass

    # Auffüllen / kürzen auf tp_count
    while len(distribution) < tp_count:
        distribution.append(distribution[-1] if distribution else 100 / tp_count)
    distribution = distribution[:tp_count]

    # Normalisieren auf 100%
    total_pct = sum(distribution)
    if total_pct <= 0:
        total_pct = 100
    distribution = [d / total_pct for d in distribution]

    step = sym_info["step"]
    prec = max(0, len(str(step).rstrip("0").split(".")[-1]))
    quantities = []
    remaining = total_qty
    for i, pct in enumerate(distribution):
        if i == len(distribution) - 1:
            q = remaining  # Letzter bekommt den Rest
        else:
            q = round(total_qty * pct - (total_qty * pct % step), prec)
            if q < step:
                q = step
            remaining -= q
        if remaining < 0:
            remaining = 0
        quantities.append(round(q, prec))
    return quantities


def parse_signal(text: str):
    upper = text.upper()

    # ── STATUS-NACHRICHTEN IGNORIEREN ────────────────────
    # "ENTRY REACHED", "WIN", "LOSS", "TP HIT" usw. sind keine neuen Signale
    STATUS_PATTERNS = [
        r"ENTRY\s+REACHED",
        r"\bWIN\b",
        r"\bLOSS\b",
        r"\bTP\s+HIT\b",
        r"\bSL\s+HIT\b",
        r"\bBREAKEVEN\b",
        r"\bCANCELLED\b",
        r"\bCANCELED\b",
        r"\bUPDATE\b",
        r"\bTRAILING\b",
    ]
    for pat in STATUS_PATTERNS:
        if re.search(pat, upper):
            return None   # Status-Nachricht, kein handelbares Signal

    # ── CLOSE ────────────────────────────────────────────
    if re.search(MAP_CLOSE, upper, re.IGNORECASE):
        nr_m  = re.search(r"#(\d+)", text)
        sym_m = re.search(r"\b([A-Z]{2,10})(USDT|BUSD|BTC|ETH|BNB)\b", upper)
        if sym_m:
            return {
                "action":    "CLOSE",
                "signal_nr": nr_m.group(1) if nr_m else "?",
                "symbol":    sym_m.group(1) + sym_m.group(2)
            }
        return None

    # ── OPEN – Richtung ──────────────────────────────────
    direction = None
    if re.search(MAP_LONG,  upper, re.IGNORECASE): direction = "LONG"
    elif re.search(MAP_SHORT, upper, re.IGNORECASE): direction = "SHORT"
    if not direction: return None

    # Symbol
    pair_m = re.search(rf"(?:{MAP_PAIR})\s*:\s*([A-Z0-9/\-]{{4,12}})", text, re.IGNORECASE)
    if pair_m:
        symbol = re.sub(r"[/\-]", "", pair_m.group(1).upper())
    else:
        sym_m = re.search(r"\b([A-Z]{2,8})(USDT|BUSD|BTC|ETH|BNB)\b", upper)
        symbol = sym_m.group(1) + sym_m.group(2) if sym_m else None

    if not symbol: return None

    nr_m = re.search(r"#(\d+)", text)

    # Order-Typ erkennen: LIMIT oder MARKET
    if re.search(MAP_LIMIT, upper, re.IGNORECASE):
        order_type = "LIMIT"
    else:
        order_type = "MARKET"

    # Multi-TP: alle TP-Werte sammeln (TP1, TP2, TP3 ...)
    tp_values = _num_all(text, MAP_TP)
    if not tp_values:
        single_tp = _num(text, MAP_TP)
        tp_values = [single_tp] if single_tp else []

    return {
        "action":     "OPEN",
        "signal_nr":  nr_m.group(1) if nr_m else "0",
        "direction":  direction,
        "symbol":     symbol,
        "order_type": order_type,
        "entry":      _num(text, MAP_ENTRY),
        "tp_list":    tp_values,
        "tp":         tp_values[0] if tp_values else None,
        "sl":         _num(text, MAP_SL),
    }


# ── Telegram Listener ─────────────────────────────────────
SESSION_FILE = os.path.join(APP_DIR, f"edgetrader_session_{PROFILE_INDEX}")
tg = TelegramClient(SESSION_FILE, TELEGRAM_API_ID, TELEGRAM_API_HASH)

@tg.on(events.NewMessage(chats=TELEGRAM_BOT))
async def on_signal(event):
    msg = event.message.text
    if not msg: return
    log.info(f"📩 Nachricht: {msg[:120]}")

    sig = parse_signal(msg)
    if not sig:
        log.warning(f"⚠️ Signal nicht erkannt – Nachricht konnte nicht verarbeitet werden:")
        # Nachricht in Zeilen aufteilen für bessere Lesbarkeit
        for line in msg.strip().split("\n")[:5]:
            log.warning(f"   | {line.strip()[:100]}")
        log.warning("   → Prüfe die Signal Map Einstellungen oder das Signal-Format")
        return

    tp_info = sig.get('tp_list', [])
    log.info(f"📊 Signal erkannt: {sig['action']} | {sig.get('direction','')} | "
             f"{sig['symbol']} | Typ: {sig.get('order_type','MARKET')} | "
             f"TPs: {len(tp_info)}")
    sym = sig["symbol"]
    nr  = sig["signal_nr"]

    if sig["action"] == "CLOSE":
        trade_info = open_trades.get(nr, {})
        close_symbol = trade_info.get("symbol", sym) if isinstance(trade_info, dict) else trade_info
        close_trade_id = trade_info.get("trade_id") if isinstance(trade_info, dict) else None
        close_position(close_symbol, close_trade_id)
        open_trades.pop(nr, None)
    elif sig["action"] == "OPEN":
        trade_id = open_position(sym, sig["direction"],
                      sig.get("entry"), sig.get("tp_list", []), sig.get("sl"),
                      sig.get("order_type", "MARKET"), signal_nr=nr)
        open_trades[nr] = {"symbol": sym, "trade_id": trade_id}


async def main():
    mode = "TESTNET" if TESTNET else "⚠️  LIVE"
    log.info(f"🚀 EdgeTrader Bot gestartet | {mode} | Kanal: {TELEGRAM_BOT}")
    log.info(f"⚙️  {LEVERAGE}x Hebel | {CAPITAL_PER_TRADE} USDT | SL {SL_PERCENT}%")
    log.info(f"🗺️  Mapping – TP: [{P.get('map_tp','')}] | SL: [{P.get('map_sl','')}] | Entry: [{P.get('map_entry','')}]")

    # Retry connect falls Session-DB gesperrt ist (z.B. nach Absturz)
    for attempt in range(5):
        try:
            await tg.connect()
            break
        except Exception as e:
            if "database is locked" in str(e) and attempt < 4:
                log.warning(f"⚠️ Session gesperrt – Versuch {attempt+2}/5...")
                await asyncio.sleep(2)
            else:
                raise

    if not await tg.is_user_authorized():
        # ── Einmalige Telegram-Authentifizierung ────────────
        log.info("📱 Telegram-Login erforderlich (einmalig)...")

        # Telefonnummer anfordern
        print("AUTH_PHONE_REQUIRED", flush=True)
        phone = sys.stdin.readline().strip()
        if not phone:
            log.error("❌ Keine Telefonnummer erhalten – Bot wird beendet.")
            return

        await tg.send_code_request(phone)

        # SMS-Code anfordern
        print("AUTH_CODE_REQUIRED", flush=True)
        code = sys.stdin.readline().strip()
        if not code:
            log.error("❌ Kein Code erhalten – Bot wird beendet.")
            return

        try:
            await tg.sign_in(phone, code)
        except SessionPasswordNeededError:
            # 2FA-Passwort anfordern
            print("AUTH_2FA_REQUIRED", flush=True)
            pw = sys.stdin.readline().strip()
            if not pw:
                log.error("❌ Kein 2FA-Passwort erhalten – Bot wird beendet.")
                return
            await tg.sign_in(password=pw)

        log.info("✅ Telegram erfolgreich authentifiziert! Session gespeichert.")

    # ── Recovery: Offene Positionen prüfen und wiederherstellen ──
    try:
        _recover_open_positions()
    except Exception as e:
        log.error(f"❌ Recovery beim Start fehlgeschlagen: {e}")

    log.info("👂 Warte auf Signale...")
    await tg.run_until_disconnected()


if __name__ == "__main__":
    asyncio.run(main())
