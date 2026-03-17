import sqlite3
from datetime import date, datetime, timedelta
from config import DATABASE_NAME, CAPITAL


def _get_connection():
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def _safe_float(value, default=0.0):
    try:
        return float(value)
    except Exception:
        return default


def _safe_int(value, default=0):
    try:
        return int(value)
    except Exception:
        return default


def _column_exists(cursor, table_name, column_name):
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = cursor.fetchall()
    return any(col["name"] == column_name for col in columns)


def _ensure_column(cursor, table_name, column_name, column_type):
    if not _column_exists(cursor, table_name, column_name):
        cursor.execute(
            f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}"
        )


def init_db():
    conn = _get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS signals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        ticker TEXT,
        signal TEXT,
        close_price REAL,
        ema200 REAL,
        rsi REAL,
        macd REAL,
        macd_signal REAL,
        atr REAL,
        stop_loss REAL,
        take_profit REAL
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS paper_trades (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp_open TEXT,
        timestamp_close TEXT,
        ticker TEXT,
        signal TEXT,
        entry_price REAL,
        exit_price REAL,
        stop_loss REAL,
        take_profit REAL,
        position_size REAL,
        pnl REAL,
        status TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS paper_state (
        id INTEGER PRIMARY KEY CHECK (id = 1),
        capital REAL
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS risk_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        ticker TEXT,
        signal TEXT,
        event_type TEXT,
        reason TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS feed_audit (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        ticker TEXT,
        provider TEXT,
        timeframe TEXT,
        period TEXT,
        rows_count INTEGER,
        status TEXT,
        message TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS setup_alerts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        ticker TEXT,
        alert_type TEXT,
        reason TEXT
    )
    """)

    cursor.execute("""
    INSERT OR IGNORE INTO paper_state (id, capital)
    VALUES (1, ?)
    """, (_safe_float(CAPITAL),))

    _ensure_column(cursor, "signals", "regime", "TEXT")
    _ensure_column(cursor, "paper_trades", "regime", "TEXT")

    cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_signals_ticker_timestamp
    ON signals (ticker, timestamp)
    """)

    cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_paper_trades_status_ticker
    ON paper_trades (status, ticker)
    """)

    cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_risk_events_ticker_timestamp
    ON risk_events (ticker, timestamp)
    """)

    cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_feed_audit_ticker_timestamp
    ON feed_audit (ticker, timestamp)
    """)

    cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_setup_alerts_ticker_type_timestamp
    ON setup_alerts (ticker, alert_type, timestamp)
    """)

    conn.commit()
    conn.close()


def log_feed_event(timestamp, ticker, provider, timeframe, period, rows_count, status, message):
    conn = _get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO feed_audit (
        timestamp, ticker, provider, timeframe, period, rows_count, status, message
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        timestamp,
        ticker,
        provider,
        timeframe,
        period,
        _safe_int(rows_count),
        status,
        str(message)
    ))

    conn.commit()
    conn.close()


def log_setup_alert(timestamp, ticker, alert_type, reason):
    conn = _get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO setup_alerts (
        timestamp, ticker, alert_type, reason
    ) VALUES (?, ?, ?, ?)
    """, (
        timestamp,
        ticker,
        alert_type,
        str(reason)
    ))

    conn.commit()
    conn.close()


def has_recent_setup_alert(ticker, alert_type, within_minutes=180):
    conn = _get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT timestamp
    FROM setup_alerts
    WHERE ticker = ?
      AND alert_type = ?
    ORDER BY id DESC
    LIMIT 1
    """, (ticker, alert_type))

    row = cursor.fetchone()
    conn.close()

    if not row or not row["timestamp"]:
        return False

    try:
        last_ts = datetime.fromisoformat(row["timestamp"])
    except Exception:
        return False

    return last_ts >= datetime.now() - timedelta(minutes=_safe_int(within_minutes, 180))


def save_signal(timestamp, ticker, signal, regime, df, trade):
    last = df.iloc[-1]

    stop_loss = trade.get("stop_loss") if isinstance(trade, dict) else None
    take_profit = trade.get("take_profit") if isinstance(trade, dict) else None

    conn = _get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO signals (
        timestamp, ticker, signal, regime, close_price, ema200, rsi,
        macd, macd_signal, atr, stop_loss, take_profit
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        timestamp,
        ticker,
        signal,
        regime,
        _safe_float(last.get("Close")),
        _safe_float(last.get("ema200")),
        _safe_float(last.get("rsi")),
        _safe_float(last.get("macd")),
        _safe_float(last.get("macd_signal")),
        _safe_float(last.get("atr")),
        _safe_float(stop_loss) if stop_loss is not None else None,
        _safe_float(take_profit) if take_profit is not None else None
    ))

    conn.commit()
    conn.close()


def get_paper_capital():
    conn = _get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT capital FROM paper_state WHERE id = 1")
    row = cursor.fetchone()

    conn.close()
    return _safe_float(row["capital"], _safe_float(CAPITAL)) if row else _safe_float(CAPITAL)


def update_paper_capital(new_capital):
    conn = _get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    UPDATE paper_state
    SET capital = ?
    WHERE id = 1
    """, (_safe_float(new_capital),))

    conn.commit()
    conn.close()


def get_open_paper_trades():
    conn = _get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT id, timestamp_open, ticker, signal, regime, entry_price,
           stop_loss, take_profit, position_size
    FROM paper_trades
    WHERE status = 'OPEN'
    ORDER BY id ASC
    """)

    rows = cursor.fetchall()
    conn.close()

    trades = []
    for row in rows:
        trades.append({
            "id": row["id"],
            "timestamp_open": row["timestamp_open"],
            "ticker": row["ticker"],
            "signal": row["signal"],
            "regime": row["regime"],
            "entry_price": _safe_float(row["entry_price"]),
            "stop_loss": _safe_float(row["stop_loss"]),
            "take_profit": _safe_float(row["take_profit"]),
            "position_size": _safe_float(row["position_size"]),
        })

    return trades


def create_paper_trade(
    timestamp_open,
    ticker,
    signal,
    regime,
    entry_price,
    stop_loss,
    take_profit,
    position_size
):
    conn = _get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO paper_trades (
        timestamp_open,
        timestamp_close,
        ticker,
        signal,
        regime,
        entry_price,
        exit_price,
        stop_loss,
        take_profit,
        position_size,
        pnl,
        status
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        timestamp_open,
        None,
        ticker,
        signal,
        regime,
        _safe_float(entry_price),
        None,
        _safe_float(stop_loss),
        _safe_float(take_profit),
        _safe_float(position_size),
        None,
        "OPEN"
    ))

    conn.commit()
    conn.close()


def close_paper_trade(trade_id, timestamp_close, exit_price, pnl):
    conn = _get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    UPDATE paper_trades
    SET
        timestamp_close = ?,
        exit_price = ?,
        pnl = ?,
        status = 'CLOSED'
    WHERE id = ?
    """, (
        timestamp_close,
        _safe_float(exit_price),
        _safe_float(pnl),
        _safe_int(trade_id)
    ))

    conn.commit()
    conn.close()


def get_closed_trade_stats(ticker=None, signal=None, limit=100):
    conn = _get_connection()
    cursor = conn.cursor()

    query = """
    SELECT ticker, signal, pnl
    FROM paper_trades
    WHERE status = 'CLOSED'
    """
    params = []

    if ticker is not None:
        query += " AND ticker = ?"
        params.append(ticker)

    if signal is not None:
        query += " AND signal = ?"
        params.append(signal)

    query += " ORDER BY id DESC LIMIT ?"
    params.append(_safe_int(limit, 100))

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    return [
        {
            "ticker": row["ticker"],
            "signal": row["signal"],
            "pnl": _safe_float(row["pnl"])
        }
        for row in rows
    ]


def count_open_trades():
    conn = _get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT COUNT(*)
    FROM paper_trades
    WHERE status = 'OPEN'
    """)

    row = cursor.fetchone()
    conn.close()

    if not row:
        return 0

    return _safe_int(row[0], 0)


def get_latest_trade_timestamp_for_ticker(ticker):
    conn = _get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT MAX(ts) AS latest_ts FROM (
        SELECT timestamp_open AS ts
        FROM paper_trades
        WHERE ticker = ?
        UNION ALL
        SELECT timestamp_close AS ts
        FROM paper_trades
        WHERE ticker = ? AND timestamp_close IS NOT NULL
    )
    """, (ticker, ticker))

    row = cursor.fetchone()
    conn.close()

    if row and row["latest_ts"]:
        return row["latest_ts"]

    return None


def get_daily_closed_pnl(target_date=None):
    if target_date is None:
        target_date = date.today().isoformat()

    conn = _get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT COALESCE(SUM(pnl), 0) AS total_pnl
    FROM paper_trades
    WHERE status = 'CLOSED'
      AND DATE(timestamp_close) = ?
    """, (target_date,))

    row = cursor.fetchone()
    conn.close()

    if not row:
        return 0.0

    return _safe_float(row["total_pnl"], 0.0)


def log_risk_event(timestamp, ticker, signal, event_type, reason):
    conn = _get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO risk_events (
        timestamp, ticker, signal, event_type, reason
    ) VALUES (?, ?, ?, ?, ?)
    """, (
        timestamp,
        ticker,
        signal,
        event_type,
        str(reason)
    ))

    conn.commit()
    conn.close()