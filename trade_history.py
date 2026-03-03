"""
EdgeTrader – Trade History & Statistics
by Philip Babuda
Persistiert Trades in SQLite, liefert Statistiken.
"""

import sqlite3, os, json, threading
from datetime import datetime


def get_app_dir() -> str:
    base = os.environ.get("APPDATA", os.path.expanduser("~"))
    app_dir = os.path.join(base, "EdgeTrader")
    os.makedirs(app_dir, exist_ok=True)
    return app_dir


DB_FILE = os.path.join(get_app_dir(), "edgetrader_trades.db")
_lock = threading.Lock()

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS trades (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_index INTEGER,
    profile_name  TEXT,
    signal_nr     TEXT,
    symbol        TEXT NOT NULL,
    direction     TEXT NOT NULL,
    order_type    TEXT DEFAULT 'MARKET',
    entry_price   REAL,
    quantity      REAL,
    leverage      INTEGER,
    capital       REAL,
    tp_prices     TEXT,
    sl_price      REAL,
    exit_price    REAL,
    exit_reason   TEXT,
    pnl_usdt      REAL,
    pnl_percent   REAL,
    opened_at     TEXT NOT NULL,
    closed_at     TEXT,
    status        TEXT DEFAULT 'OPEN',
    broker        TEXT,
    testnet       INTEGER DEFAULT 1
);

CREATE INDEX IF NOT EXISTS idx_trades_symbol ON trades(symbol);
CREATE INDEX IF NOT EXISTS idx_trades_profile ON trades(profile_index);
CREATE INDEX IF NOT EXISTS idx_trades_status ON trades(status);
CREATE INDEX IF NOT EXISTS idx_trades_opened ON trades(opened_at);
"""


class TradeHistory:
    def __init__(self):
        self._init_db()

    def _init_db(self):
        with _lock:
            conn = sqlite3.connect(DB_FILE)
            conn.executescript(SCHEMA_SQL)
            conn.commit()
            conn.close()

    def _conn(self):
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = sqlite3.Row
        return conn

    # ── Schreiben ─────────────────────────────────────────

    def record_open(self, profile_index: int, profile_name: str,
                    signal_nr: str, symbol: str, direction: str,
                    order_type: str, entry_price: float, quantity: float,
                    leverage: int, capital: float,
                    tp_prices: list, sl_price: float,
                    broker: str, testnet: bool) -> int:
        """Speichert einen neuen Trade. Gibt die Trade-ID zurueck."""
        with _lock:
            conn = self._conn()
            cur = conn.execute("""
                INSERT INTO trades
                (profile_index, profile_name, signal_nr, symbol, direction,
                 order_type, entry_price, quantity, leverage, capital,
                 tp_prices, sl_price, opened_at, status, broker, testnet)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                profile_index, profile_name, signal_nr, symbol, direction,
                order_type, entry_price, quantity, leverage, capital,
                json.dumps(tp_prices) if tp_prices else "[]",
                sl_price,
                datetime.now().isoformat(),
                "OPEN", broker, 1 if testnet else 0
            ))
            conn.commit()
            trade_id = cur.lastrowid
            conn.close()
            return trade_id

    def record_close(self, trade_id: int, exit_price: float,
                     exit_reason: str, pnl_usdt: float = None,
                     pnl_percent: float = None):
        """Schliesst einen Trade."""
        with _lock:
            conn = self._conn()
            # Falls P&L nicht berechnet wurde, versuche es hier
            if pnl_usdt is None:
                row = conn.execute(
                    "SELECT entry_price, quantity, direction, leverage FROM trades WHERE id=?",
                    (trade_id,)).fetchone()
                if row and row["entry_price"] and exit_price:
                    entry = row["entry_price"]
                    qty   = row["quantity"] or 0
                    if row["direction"] == "LONG":
                        pnl_usdt = (exit_price - entry) * qty
                    else:
                        pnl_usdt = (entry - exit_price) * qty
                    if entry > 0:
                        pnl_percent = round(pnl_usdt / (entry * qty) * 100, 2)
                    pnl_usdt = round(pnl_usdt, 4)

            conn.execute("""
                UPDATE trades SET
                    exit_price=?, exit_reason=?, pnl_usdt=?, pnl_percent=?,
                    closed_at=?, status='CLOSED'
                WHERE id=?
            """, (exit_price, exit_reason, pnl_usdt, pnl_percent,
                  datetime.now().isoformat(), trade_id))
            conn.commit()
            conn.close()

    def record_close_by_symbol(self, symbol: str, exit_price: float = None,
                               exit_reason: str = "CLOSE_SIGNAL"):
        """Schliesst alle offenen Trades fuer ein Symbol."""
        with _lock:
            conn = self._conn()
            open_trades = conn.execute(
                "SELECT id, entry_price, quantity, direction FROM trades WHERE symbol=? AND status='OPEN'",
                (symbol,)).fetchall()

            for row in open_trades:
                pnl_usdt = None
                pnl_percent = None
                if exit_price and row["entry_price"]:
                    entry = row["entry_price"]
                    qty = row["quantity"] or 0
                    if row["direction"] == "LONG":
                        pnl_usdt = (exit_price - entry) * qty
                    else:
                        pnl_usdt = (entry - exit_price) * qty
                    if entry > 0 and qty > 0:
                        pnl_percent = round(pnl_usdt / (entry * qty) * 100, 2)
                    pnl_usdt = round(pnl_usdt, 4)

                conn.execute("""
                    UPDATE trades SET
                        exit_price=?, exit_reason=?, pnl_usdt=?, pnl_percent=?,
                        closed_at=?, status='CLOSED'
                    WHERE id=?
                """, (exit_price, exit_reason, pnl_usdt, pnl_percent,
                      datetime.now().isoformat(), row["id"]))

            conn.commit()
            conn.close()

    # ── Lesen ─────────────────────────────────────────────

    def get_open_trades(self, profile_index: int = None) -> list:
        """Gibt alle offenen Trades zurueck."""
        with _lock:
            conn = self._conn()
            if profile_index is not None:
                rows = conn.execute(
                    "SELECT * FROM trades WHERE status='OPEN' AND profile_index=? ORDER BY opened_at DESC",
                    (profile_index,)).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM trades WHERE status='OPEN' ORDER BY opened_at DESC"
                ).fetchall()
            conn.close()
            return [dict(r) for r in rows]

    def get_history(self, profile_index: int = None, limit: int = 100) -> list:
        """Gibt geschlossene Trades zurueck (neueste zuerst)."""
        with _lock:
            conn = self._conn()
            if profile_index is not None:
                rows = conn.execute(
                    "SELECT * FROM trades WHERE status='CLOSED' AND profile_index=? ORDER BY closed_at DESC LIMIT ?",
                    (profile_index, limit)).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM trades WHERE status='CLOSED' ORDER BY closed_at DESC LIMIT ?",
                    (limit,)).fetchall()
            conn.close()
            return [dict(r) for r in rows]

    def get_all_trades(self, profile_index: int = None, limit: int = 200) -> list:
        """Gibt alle Trades zurueck (neueste zuerst)."""
        with _lock:
            conn = self._conn()
            if profile_index is not None:
                rows = conn.execute(
                    "SELECT * FROM trades WHERE profile_index=? ORDER BY opened_at DESC LIMIT ?",
                    (profile_index, limit)).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM trades ORDER BY opened_at DESC LIMIT ?",
                    (limit,)).fetchall()
            conn.close()
            return [dict(r) for r in rows]

    def clear_all_trades(self):
        """Loescht ALLE Trades aus der Datenbank (Reset)."""
        with _lock:
            conn = self._conn()
            conn.execute("DELETE FROM trades")
            conn.commit()
            conn.close()

    def get_statistics(self, profile_index: int = None) -> dict:
        """Berechnet Handelsstatistiken."""
        with _lock:
            conn = self._conn()
            where = "WHERE status='CLOSED'"
            params = []
            if profile_index is not None:
                where += " AND profile_index=?"
                params.append(profile_index)

            rows = conn.execute(
                f"SELECT * FROM trades {where}", params).fetchall()
            conn.close()

        # Offene Trades zählen
        with _lock:
            conn2 = self._conn()
            open_where = "WHERE status='OPEN'"
            open_params = []
            if profile_index is not None:
                open_where += " AND profile_index=?"
                open_params.append(profile_index)
            open_count = conn2.execute(
                f"SELECT COUNT(*) as cnt FROM trades {open_where}", open_params
            ).fetchone()["cnt"]
            conn2.close()

        if not rows:
            return {
                "total_trades": 0, "total_pnl": 0.0, "win_rate": 0.0,
                "avg_win": 0.0, "avg_loss": 0.0, "best_trade": 0.0,
                "worst_trade": 0.0, "open_trades": open_count
            }

        pnls = [r["pnl_usdt"] for r in rows if r["pnl_usdt"] is not None]
        wins = [p for p in pnls if p > 0]
        losses = [p for p in pnls if p < 0]

        return {
            "total_trades": len(rows),
            "total_pnl":    round(sum(pnls), 4) if pnls else 0.0,
            "win_rate":     round(len(wins) / len(pnls) * 100, 1) if pnls else 0.0,
            "avg_win":      round(sum(wins) / len(wins), 4) if wins else 0.0,
            "avg_loss":     round(sum(losses) / len(losses), 4) if losses else 0.0,
            "best_trade":   round(max(pnls), 4) if pnls else 0.0,
            "worst_trade":  round(min(pnls), 4) if pnls else 0.0,
            "open_trades":  open_count,
        }
