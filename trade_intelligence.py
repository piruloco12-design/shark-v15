import sqlite3
import pandas as pd
from config import DATABASE_NAME


def _load_closed_trade_contexts():
    conn = sqlite3.connect(DATABASE_NAME)

    query = """
    SELECT
        ticker,
        signal,
        regime,
        pnl
    FROM paper_trades
    WHERE status = 'CLOSED'
      AND regime IS NOT NULL
    """

    df = pd.read_sql_query(query, conn)
    conn.close()

    return df


def _compute_score(df):
    if df.empty:
        return {
            "count": 0,
            "winrate": 0.0,
            "avg_pnl": 0.0,
            "score": 50.0,
            "reason": "Sin historial"
        }

    count = len(df)
    wins = int((df["pnl"] > 0).sum())
    winrate = wins / count * 100 if count > 0 else 0.0
    avg_pnl = float(df["pnl"].mean()) if count > 0 else 0.0

    score = 50.0

    if count >= 3:
        score += (winrate - 50.0) * 0.5
        score += avg_pnl * 2.0

    score = max(0.0, min(100.0, score))

    if score >= 60:
        reason = "Contexto favorable"
    elif score <= 40:
        reason = "Contexto desfavorable"
    else:
        reason = "Contexto neutro"

    return {
        "count": count,
        "winrate": round(winrate, 2),
        "avg_pnl": round(avg_pnl, 2),
        "score": round(score, 2),
        "reason": reason
    }


def evaluate_trade_context(ticker, signal, regime):
    df = _load_closed_trade_contexts()

    if df.empty:
        return {
            "ticker_signal_score": 50.0,
            "ticker_regime_score": 50.0,
            "signal_score": 50.0,
            "final_score": 50.0,
            "decision": "NEUTRAL",
            "reason": "Sin historial suficiente"
        }

    df_ticker_signal = df[(df["ticker"] == ticker) & (df["signal"] == signal)]
    df_ticker_regime = df[(df["ticker"] == ticker) & (df["regime"] == regime)]
    df_signal = df[df["signal"] == signal]

    stats_ticker_signal = _compute_score(df_ticker_signal)
    stats_ticker_regime = _compute_score(df_ticker_regime)
    stats_signal = _compute_score(df_signal)

    final_score = (
        stats_ticker_signal["score"] * 0.45 +
        stats_ticker_regime["score"] * 0.35 +
        stats_signal["score"] * 0.20
    )

    final_score = round(final_score, 2)

    if final_score >= 60:
        decision = "ALLOW"
        reason = "Contexto histórico favorable"
    elif final_score <= 40:
        decision = "BLOCK"
        reason = "Contexto histórico débil"
    else:
        decision = "NEUTRAL"
        reason = "Contexto no concluyente"

    return {
        "ticker_signal_score": stats_ticker_signal["score"],
        "ticker_regime_score": stats_ticker_regime["score"],
        "signal_score": stats_signal["score"],
        "final_score": final_score,
        "decision": decision,
        "reason": reason
    }


def get_trade_intelligence_table():
    df = _load_closed_trade_contexts()

    if df.empty:
        return pd.DataFrame(columns=[
            "ticker", "signal", "regime", "trades", "winrate", "avg_pnl"
        ])

    grouped = df.groupby(["ticker", "signal", "regime"]).agg(
        trades=("pnl", "count"),
        winrate=("pnl", lambda x: round((x > 0).sum() / len(x) * 100, 2) if len(x) > 0 else 0.0),
        avg_pnl=("pnl", "mean")
    ).reset_index()

    grouped["avg_pnl"] = grouped["avg_pnl"].round(2)
    grouped = grouped.sort_values(["trades", "avg_pnl"], ascending=[False, False]).reset_index(drop=True)

    return grouped