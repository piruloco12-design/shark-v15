import sqlite3
import pandas as pd
from config import DATABASE_NAME, CAPITAL, ASSETS
from asset_ranker import get_asset_ranking_table
from capital_allocator import get_capital_allocation_map
from trade_intelligence import get_trade_intelligence_table
from asset_labels import get_asset_label


def _connect():
    return sqlite3.connect(DATABASE_NAME)


def _add_asset_name_column(df, ticker_col="ticker"):
    if df.empty or ticker_col not in df.columns:
        return df

    df = df.copy()
    df.insert(1, "asset_name", df[ticker_col].apply(get_asset_label))
    return df


def load_closed_trades():
    conn = _connect()

    query = """
    SELECT
        id,
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
    FROM paper_trades
    WHERE status = 'CLOSED'
    ORDER BY id ASC
    """

    df = pd.read_sql_query(query, conn)
    conn.close()

    if not df.empty:
        df["timestamp_open"] = pd.to_datetime(df["timestamp_open"], errors="coerce")
        df["timestamp_close"] = pd.to_datetime(df["timestamp_close"], errors="coerce")

    return _add_asset_name_column(df)


def load_open_trades():
    conn = _connect()

    query = """
    SELECT
        id,
        timestamp_open,
        ticker,
        signal,
        regime,
        entry_price,
        stop_loss,
        take_profit,
        position_size,
        status
    FROM paper_trades
    WHERE status = 'OPEN'
    ORDER BY id ASC
    """

    df = pd.read_sql_query(query, conn)
    conn.close()

    if not df.empty:
        df["timestamp_open"] = pd.to_datetime(df["timestamp_open"], errors="coerce")

    return _add_asset_name_column(df)


def load_signals(limit=100):
    conn = _connect()

    query = f"""
    SELECT
        id,
        timestamp,
        ticker,
        signal,
        regime,
        close_price,
        ema200,
        rsi,
        macd,
        macd_signal,
        atr,
        stop_loss,
        take_profit
    FROM signals
    ORDER BY id DESC
    LIMIT {int(limit)}
    """

    df = pd.read_sql_query(query, conn)
    conn.close()

    if not df.empty:
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")

    return _add_asset_name_column(df)


def load_risk_events(limit=100):
    conn = _connect()

    query = f"""
    SELECT
        id,
        timestamp,
        ticker,
        signal,
        event_type,
        reason
    FROM risk_events
    ORDER BY id DESC
    LIMIT {int(limit)}
    """

    df = pd.read_sql_query(query, conn)
    conn.close()

    if not df.empty:
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")

    return _add_asset_name_column(df)


def load_feed_audit(limit=100):
    conn = _connect()

    query = f"""
    SELECT
        id,
        timestamp,
        ticker,
        provider,
        timeframe,
        period,
        rows_count,
        status,
        message
    FROM feed_audit
    ORDER BY id DESC
    LIMIT {int(limit)}
    """

    df = pd.read_sql_query(query, conn)
    conn.close()

    if not df.empty:
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")

    return _add_asset_name_column(df)


def get_current_capital():
    conn = _connect()
    cursor = conn.cursor()

    cursor.execute("SELECT capital FROM paper_state WHERE id = 1")
    row = cursor.fetchone()

    conn.close()

    if row is None:
        return float(CAPITAL)

    return float(row[0])


def build_equity_curve():
    trades = load_closed_trades()

    if trades.empty:
        return pd.DataFrame({
            "step": [0],
            "equity": [float(CAPITAL)]
        })

    equity = float(CAPITAL)
    rows = [{"step": 0, "equity": equity, "timestamp_close": None}]

    for _, row in trades.iterrows():
        equity += float(row["pnl"])
        rows.append({
            "step": len(rows),
            "equity": equity,
            "timestamp_close": row["timestamp_close"]
        })

    return pd.DataFrame(rows)


def calculate_max_drawdown(equity_df):
    if equity_df.empty:
        return 0.0

    equity_series = equity_df["equity"]
    running_peak = equity_series.cummax()
    drawdown = running_peak - equity_series

    return float(drawdown.max())


def calculate_profit_factor(trades_df):
    if trades_df.empty:
        return 0.0

    gross_profit = trades_df.loc[trades_df["pnl"] > 0, "pnl"].sum()
    gross_loss = abs(trades_df.loc[trades_df["pnl"] <= 0, "pnl"].sum())

    if gross_loss == 0:
        return 0.0

    return float(gross_profit / gross_loss)


def calculate_summary():
    closed_trades = load_closed_trades()
    open_trades = load_open_trades()
    current_capital = get_current_capital()
    equity_df = build_equity_curve()
    risk_df = load_risk_events(limit=3000)

    total_closed = len(closed_trades)
    wins = int((closed_trades["pnl"] > 0).sum()) if not closed_trades.empty else 0
    losses = int((closed_trades["pnl"] <= 0).sum()) if not closed_trades.empty else 0

    winrate = (wins / total_closed * 100) if total_closed > 0 else 0.0
    avg_trade = float(closed_trades["pnl"].mean()) if total_closed > 0 else 0.0
    total_pnl = float(closed_trades["pnl"].sum()) if total_closed > 0 else 0.0
    profit_factor = calculate_profit_factor(closed_trades)
    max_drawdown = calculate_max_drawdown(equity_df)

    risk_blocks = 0 if risk_df.empty else int((risk_df["event_type"] == "RISK_BLOCK").sum())
    ai_blocks = 0 if risk_df.empty else int((risk_df["event_type"] == "AI_BLOCK").sum())
    intel_blocks = 0 if risk_df.empty else int((risk_df["event_type"] == "INTELLIGENCE_BLOCK").sum())
    session_blocks = 0 if risk_df.empty else int((risk_df["event_type"] == "SESSION_BLOCK").sum())
    volatility_blocks = 0 if risk_df.empty else int((risk_df["event_type"] == "VOLATILITY_BLOCK").sum())
    final_blocks = 0 if risk_df.empty else int((risk_df["event_type"] == "FINAL_BLOCK").sum())

    return {
        "capital_actual": round(current_capital, 2),
        "capital_inicial": float(CAPITAL),
        "total_pnl": round(total_pnl, 2),
        "trades_cerrados": total_closed,
        "trades_abiertos": len(open_trades),
        "wins": wins,
        "losses": losses,
        "winrate": round(winrate, 2),
        "avg_trade": round(avg_trade, 2),
        "profit_factor": round(profit_factor, 2),
        "max_drawdown": round(max_drawdown, 2),
        "risk_blocks": risk_blocks,
        "ai_blocks": ai_blocks,
        "intel_blocks": intel_blocks,
        "session_blocks": session_blocks,
        "volatility_blocks": volatility_blocks,
        "final_blocks": final_blocks
    }


def by_ticker_stats():
    df = load_closed_trades()

    if df.empty:
        return pd.DataFrame(columns=[
            "ticker", "asset_name", "trades", "wins", "losses",
            "winrate", "total_pnl", "avg_pnl"
        ])

    grouped = df.groupby(["ticker", "asset_name"]).agg(
        trades=("id", "count"),
        wins=("pnl", lambda x: int((x > 0).sum())),
        losses=("pnl", lambda x: int((x <= 0).sum())),
        total_pnl=("pnl", "sum"),
        avg_pnl=("pnl", "mean")
    ).reset_index()

    grouped["winrate"] = grouped.apply(
        lambda row: (row["wins"] / row["trades"] * 100) if row["trades"] > 0 else 0,
        axis=1
    )

    grouped = grouped[[
        "ticker", "asset_name", "trades", "wins", "losses", "winrate", "total_pnl", "avg_pnl"
    ]].sort_values("total_pnl", ascending=False)

    return grouped.round(2)


def by_signal_stats():
    df = load_closed_trades()

    if df.empty:
        return pd.DataFrame(columns=[
            "signal", "trades", "wins", "losses",
            "winrate", "total_pnl", "avg_pnl"
        ])

    grouped = df.groupby("signal").agg(
        trades=("id", "count"),
        wins=("pnl", lambda x: int((x > 0).sum())),
        losses=("pnl", lambda x: int((x <= 0).sum())),
        total_pnl=("pnl", "sum"),
        avg_pnl=("pnl", "mean")
    ).reset_index()

    grouped["winrate"] = grouped.apply(
        lambda row: (row["wins"] / row["trades"] * 100) if row["trades"] > 0 else 0,
        axis=1
    )

    grouped = grouped[[
        "signal", "trades", "wins", "losses", "winrate", "total_pnl", "avg_pnl"
    ]].sort_values("total_pnl", ascending=False)

    return grouped.round(2)


def recent_closed_trades(limit=20):
    df = load_closed_trades()

    if df.empty:
        return df

    return df.sort_values("id", ascending=False).head(limit).reset_index(drop=True)


def recent_open_trades():
    df = load_open_trades()

    if df.empty:
        return df

    return df.sort_values("id", ascending=False).reset_index(drop=True)


def get_asset_ranking():
    df = get_asset_ranking_table(ASSETS)
    if not df.empty and "ticker" in df.columns:
        df = _add_asset_name_column(df)
    return df


def get_capital_allocation_table():
    allocation_map = get_capital_allocation_map(ASSETS)

    rows = []
    for asset, data in allocation_map.items():
        rows.append({
            "ticker": asset,
            "asset_name": get_asset_label(asset),
            "capital_weight": round(float(data["weight"]), 4),
            "score": round(float(data["score"]), 2),
            "reason": data["reason"]
        })

    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.sort_values("capital_weight", ascending=False).reset_index(drop=True)

    return df


def get_trade_intelligence():
    df = get_trade_intelligence_table()
    if not df.empty and "ticker" in df.columns:
        df = _add_asset_name_column(df)
    return df