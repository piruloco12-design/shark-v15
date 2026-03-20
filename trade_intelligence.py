import sqlite3
import pandas as pd
from config import DATABASE_NAME


def _safe_float(value, default=0.0):
    try:
        return float(value)
    except Exception:
        return default


def _clamp(value, min_value=0.0, max_value=100.0):
    return max(min_value, min(max_value, value))


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


def _sample_confidence(count, full_confidence_at):
    if full_confidence_at <= 0:
        return 1.0
    return min(1.0, count / full_confidence_at)


def _compute_stats(df):
    if df.empty:
        return {
            "count": 0,
            "winrate": 0.0,
            "avg_pnl": 0.0,
            "profit_factor_proxy": 1.0
        }

    pnl_values = [_safe_float(x, 0.0) for x in df["pnl"].tolist()]
    count = len(pnl_values)

    wins = [x for x in pnl_values if x > 0]
    losses = [x for x in pnl_values if x < 0]

    winrate = (len(wins) / count) * 100.0 if count > 0 else 0.0
    avg_pnl = sum(pnl_values) / count if count > 0 else 0.0

    gross_profit = sum(wins) if wins else 0.0
    gross_loss = abs(sum(losses)) if losses else 0.0

    if gross_loss == 0:
        profit_factor_proxy = 2.0 if gross_profit > 0 else 1.0
    else:
        profit_factor_proxy = gross_profit / gross_loss

    return {
        "count": count,
        "winrate": winrate,
        "avg_pnl": avg_pnl,
        "profit_factor_proxy": profit_factor_proxy
    }


def _score_from_stats(stats, weight, full_confidence_at):
    """
    Convierte stats en edge score estable:
    - winrate aporta el núcleo
    - avg_pnl aporta poco
    - profit factor aporta robustez
    - muestra chica = bajo impacto
    """
    count = stats["count"]
    if count == 0:
        return 0.0

    confidence = _sample_confidence(count, full_confidence_at)

    winrate_component = (stats["winrate"] - 50.0) * 0.60
    avg_pnl_component = max(-6.0, min(6.0, stats["avg_pnl"] * 0.75))

    pf = stats["profit_factor_proxy"]
    pf_component = max(-5.0, min(5.0, (pf - 1.0) * 4.0))

    raw_edge = winrate_component + avg_pnl_component + pf_component

    return raw_edge * weight * confidence


def evaluate_trade_context(ticker, signal, regime):
    """
    Trade Intelligence V15 optimizado.

    Filosofía:
    - no bloquear por desconocimiento
    - usar contexto histórico real sin sobreajuste
    - ponderar por especificidad y tamaño de muestra
    """

    df = _load_closed_trade_contexts()

    if df.empty:
        return {
            "ticker_signal_score": 55.0,
            "ticker_regime_score": 55.0,
            "signal_score": 55.0,
            "final_score": 55.0,
            "decision": "NEUTRAL",
            "reason": "Sin historial suficiente"
        }

    df_ticker_signal = df[
        (df["ticker"] == ticker) &
        (df["signal"] == signal)
    ]

    df_ticker_regime = df[
        (df["ticker"] == ticker) &
        (df["regime"] == regime)
    ]

    df_signal = df[
        (df["signal"] == signal)
    ]

    stats_ticker_signal = _compute_stats(df_ticker_signal)
    stats_ticker_regime = _compute_stats(df_ticker_regime)
    stats_signal = _compute_stats(df_signal)

    total_samples = (
        stats_ticker_signal["count"] +
        stats_ticker_regime["count"] +
        stats_signal["count"]
    )

    # Base más sana: sin historial no queremos matar buenas entradas
    final_score = 55.0

    # ticker+signal = lo más valioso
    final_score += _score_from_stats(
        stats=stats_ticker_signal,
        weight=1.00,
        full_confidence_at=10
    )

    # ticker+regime = segundo nivel de contexto
    final_score += _score_from_stats(
        stats=stats_ticker_regime,
        weight=0.65,
        full_confidence_at=12
    )

    # signal general = apoyo macro
    final_score += _score_from_stats(
        stats=stats_signal,
        weight=0.35,
        full_confidence_at=20
    )

    final_score = round(_clamp(final_score, 0.0, 100.0), 2)

    # -------------------------------------------------
    # DECISIÓN
    # -------------------------------------------------
    if total_samples < 8:
        decision = "NEUTRAL"
        reason = "Historial aún limitado; contexto sin evidencia fuerte en contra"

        return {
            "ticker_signal_score": round(max(55.0, 55.0 + _score_from_stats(stats_ticker_signal, 1.00, 10)), 2),
            "ticker_regime_score": round(max(55.0, 55.0 + _score_from_stats(stats_ticker_regime, 0.65, 12)), 2),
            "signal_score": round(max(55.0, 55.0 + _score_from_stats(stats_signal, 0.35, 20)), 2),
            "final_score": round(max(final_score, 55.0), 2),
            "decision": decision,
            "reason": reason
        }

    if final_score >= 62:
        decision = "ALLOW"
        reason = "Contexto histórico favorable y consistente"
    elif final_score <= 44:
        decision = "BLOCK"
        reason = "Contexto histórico desfavorable con evidencia suficiente"
    else:
        decision = "NEUTRAL"
        reason = "Contexto aún no concluyente"

    return {
        "ticker_signal_score": round(55.0 + _score_from_stats(stats_ticker_signal, 1.00, 10), 2),
        "ticker_regime_score": round(55.0 + _score_from_stats(stats_ticker_regime, 0.65, 12), 2),
        "signal_score": round(55.0 + _score_from_stats(stats_signal, 0.35, 20), 2),
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
    grouped = grouped.sort_values(
        ["trades", "avg_pnl"],
        ascending=[False, False]
    ).reset_index(drop=True)

    return grouped