from storage import get_closed_trade_stats


def evaluate_signal_quality(ticker, signal):
    """
    Devuelve un score AI de 0 a 100 basado en:
    - historial específico ticker+signal
    - historial general del ticker
    - historial general del signal
    """

    exact_trades = get_closed_trade_stats(ticker=ticker, signal=signal, limit=50)
    ticker_trades = get_closed_trade_stats(ticker=ticker, signal=None, limit=100)
    signal_trades = get_closed_trade_stats(ticker=None, signal=signal, limit=100)

    # Sin historial: neutro
    if len(exact_trades) == 0 and len(ticker_trades) == 0 and len(signal_trades) == 0:
        return {
            "score": 50,
            "decision": "NEUTRAL",
            "reason": "Sin historial suficiente"
        }

    def compute_stats(trades):
        if not trades:
            return {
                "count": 0,
                "winrate": 0,
                "avg_pnl": 0
            }

        wins = len([t for t in trades if t["pnl"] > 0])
        count = len(trades)
        winrate = wins / count * 100
        avg_pnl = sum(t["pnl"] for t in trades) / count

        return {
            "count": count,
            "winrate": winrate,
            "avg_pnl": avg_pnl
        }

    exact_stats = compute_stats(exact_trades)
    ticker_stats = compute_stats(ticker_trades)
    signal_stats = compute_stats(signal_trades)

    # Score ponderado
    score = 50

    # Historial exacto ticker+signal
    if exact_stats["count"] >= 5:
        score += (exact_stats["winrate"] - 50) * 0.6
        score += exact_stats["avg_pnl"] * 2.0

    # Historial del ticker
    if ticker_stats["count"] >= 10:
        score += (ticker_stats["winrate"] - 50) * 0.3
        score += ticker_stats["avg_pnl"] * 1.0

    # Historial general del signal
    if signal_stats["count"] >= 10:
        score += (signal_stats["winrate"] - 50) * 0.2
        score += signal_stats["avg_pnl"] * 0.5

    score = max(0, min(100, score))

    if score >= 60:
        decision = "ALLOW"
        reason = "Historial favorable"
    elif score <= 40:
        decision = "BLOCK"
        reason = "Historial desfavorable"
    else:
        decision = "NEUTRAL"
        reason = "Ventaja no concluyente"

    return {
        "score": round(score, 2),
        "decision": decision,
        "reason": reason,
        "exact_count": exact_stats["count"],
        "ticker_count": ticker_stats["count"],
        "signal_count": signal_stats["count"]
    }