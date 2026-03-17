import sqlite3
from datetime import date, datetime, timedelta
from config import DATABASE_NAME, CAPITAL


def _column_exists(cursor, table_name, column_name):
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = cursor.fetchall()
    return any(col[1] == column_name for col in columns)


def _ensure_column(cursor, table_name, column_name, column_type):
    if not _column_exists(cursor, table_name, column_name):
        cursor.execute(
            f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}"
        )


def init_db():
    conn = sqlite3.connect(DATABASE_NAME)
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
    """, (float(CAPITAL),))

    _ensure_column(cursor, "signals", "regime", "TEXT")
    _ensure_column(cursor, "paper_trades", "regime", "TEXT")

    conn.commit()
    conn.close()


def log_feed_event(timestamp, ticker, provider, timeframe, period, rows_count, status, message):
    conn = sqlite3.connect(DATABASE_NAME)
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
        int(rows_count),
        status,
        message
    ))

    conn.commit()
    conn.close()


def log_setup_alert(timestamp, ticker, alert_type, reason):
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO setup_alerts (
        timestamp, ticker, alert_type, reason
    ) VALUES (?, ?, ?, ?)
    """, (
        timestamp,
        ticker,
        alert_type,
        reason
    ))

    conn.commit()
    conn.close()


def has_recent_setup_alert(ticker, alert_type, within_minutes=180):
    conn = sqlite3.connect(DATABASE_NAME)
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

    if not row or not row[0]:
        return False

    try:
        last_ts = datetime.fromisoformat(row[0])
    except Exception:
        return False

    return last_ts >= datetime.now() - timedelta(minutes=int(within_minutes))


def save_signal(timestamp, ticker, signal, regime, df, trade):
    last = df.iloc[-1]

    conn = sqlite3.connect(DATABASE_NAME)
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
        float(last["Close"]),
        float(last["ema200"]),
        float(last["rsi"]),
        float(last["macd"]),
        float(last["macd_signal"]),
        float(last["atr"]),
        float(trade["stop_loss"]) if trade["stop_loss"] is not None else None,
        float(trade["take_profit"]) if trade["take_profit"] is not None else None
    ))

    conn.commit()
    conn.close()


def get_paper_capital():
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()

    cursor.execute("SELECT capital FROM paper_state WHERE id = 1")
    row = cursor.fetchone()

    conn.close()
    return float(row[0]) if row else float(CAPITAL)


def update_paper_capital(new_capital):
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()

    cursor.execute("""
    UPDATE paper_state
    SET capital = ?
    WHERE id = 1
    """, (float(new_capital),))

    conn.commit()
    conn.close()


def get_open_paper_trades():
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()

    cursor.execute("""
    SELECT id, timestamp_open, ticker, signal, regime, entry_price,
           stop_loss, take_profit, position_size
    FROM paper_trades
    WHERE status = 'OPEN'
    """)

    rows = cursor.fetchall()
    conn.close()

    trades = []
    for row in rows:
        trades.append({
            "id": row[0],
            "timestamp_open": row[1],
            "ticker": row[2],
            "signal": row[3],
            "regime": row[4],
            "entry_price": float(row[5]),
            "stop_loss": float(row[6]),
            "take_profit": float(row[7]),
            "position_size": float(row[8]),
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
    conn = sqlite3.connect(DATABASE_NAME)
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
        float(entry_price),
        None,
        float(stop_loss),
        float(take_profit),
        float(position_size),
        None,
        "OPEN"
    ))

    conn.commit()
    conn.close()


def close_paper_trade(trade_id, timestamp_close, exit_price, pnl):
    conn = sqlite3.connect(DATABASE_NAME)
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
        float(exit_price),
        float(pnl),
        int(trade_id)
    ))

    conn.commit()
    conn.close()


def get_closed_trade_stats(ticker=None, signal=None, limit=100):
    conn = sqlite3.connect(DATABASE_NAME)
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
    params.append(limit)

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    return [
        {"ticker": row[0], "signal": row[1], "pnl": float(row[2])}
        for row in rows
    ]


def count_open_trades():
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()

    cursor.execute("""
    SELECT COUNT(*)
    FROM paper_trades
    WHERE status = 'OPEN'
    """)

    count = cursor.fetchone()[0]
    conn.close()
    return int(count)


def get_latest_trade_timestamp_for_ticker(ticker):
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()

    cursor.execute("""
    SELECT MAX(ts) FROM (
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

    if row and row[0]:
        return row[0]
    return None


def get_daily_closed_pnl(target_date=None):
    if target_date is None:
        target_date = date.today().isoformat()

    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()

    cursor.execute("""
    SELECT COALESCE(SUM(pnl), 0)
    FROM paper_trades
    WHERE status = 'CLOSED'
      AND DATE(timestamp_close) = ?
    """, (target_date,))

    value = cursor.fetchone()[0]
    conn.close()
    return float(value or 0.0)


def log_risk_event(timestamp, ticker, signal, event_type, reason):
    conn = sqlite3.connect(DATABASE_NAME)
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
        reason
    ))

    conn.commit()
    conn.close()