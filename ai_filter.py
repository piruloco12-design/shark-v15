from storage import get_closed_trade_stats


def _safe_float(value, default=0.0):
    try:
        return float(value)
    except Exception:
        return default


def _clamp(value, min_value=0.0, max_value=100.0):
    return max(min_value, min(max_value, value))


def _compute_stats(trades):
    if not trades:
        return {
            "count": 0,
            "winrate": 0.0,
            "avg_pnl": 0.0,
            "profit_factor_proxy": 1.0
        }

    pnl_values = [_safe_float(t.get("pnl", 0.0)) for t in trades]
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


def _sample_confidence(count, full_confidence_at):
    """
    Devuelve una confianza entre 0 y 1 según el tamaño de muestra.
    """
    if full_confidence_at <= 0:
        return 1.0

    return min(1.0, count / full_confidence_at)


def _score_from_stats(stats, weight, full_confidence_at):
    """
    Convierte stats históricos en contribución de score:
    - winrate aporta el componente principal
    - avg_pnl aporta poco, suavizado
    - profit factor aporta estabilidad adicional
    - el peso real depende del tamaño de muestra
    """
    count = stats["count"]
    confidence = _sample_confidence(count, full_confidence_at)

    if count == 0:
        return 0.0

    winrate_component = (stats["winrate"] - 50.0) * 0.55

    # suavizamos el impacto del pnl promedio
    avg_pnl_component = max(-6.0, min(6.0, stats["avg_pnl"] * 0.75))

    # profit factor como refuerzo, pero moderado
    pf = stats["profit_factor_proxy"]
    pf_component = max(-5.0, min(5.0, (pf - 1.0) * 4.0))

    raw_edge = winrate_component + avg_pnl_component + pf_component

    return raw_edge * weight * confidence


def evaluate_signal_quality(ticker, signal):
    """
    AI Filter V15 optimizado para rentabilidad real.

    Filosofía:
    - no bloquear por falta de historial
    - premiar evidencia fuerte y consistente
    - castigar evidencia mala solo si hay muestra razonable
    - usar score como capa de confianza, no como sentencia ciega
    """

    exact_trades = get_closed_trade_stats(ticker=ticker, signal=signal, limit=50)
    ticker_trades = get_closed_trade_stats(ticker=ticker, signal=None, limit=100)
    signal_trades = get_closed_trade_stats(ticker=None, signal=signal, limit=100)

    exact_stats = _compute_stats(exact_trades)
    ticker_stats = _compute_stats(ticker_trades)
    signal_stats = _compute_stats(signal_trades)

    total_samples = (
        exact_stats["count"] +
        ticker_stats["count"] +
        signal_stats["count"]
    )

    # Base más alta que 50 para no castigar "desconocido"
    # El bloqueo debe venir de evidencia mala, no de ausencia de evidencia.
    score = 55.0

    # Historial exacto ticker+signal → lo más valioso
    score += _score_from_stats(
        stats=exact_stats,
        weight=1.00,
        full_confidence_at=12
    )

    # Historial general del ticker → secundario
    score += _score_from_stats(
        stats=ticker_stats,
        weight=0.55,
        full_confidence_at=20
    )

    # Historial general del tipo de señal → terciario
    score += _score_from_stats(
        stats=signal_stats,
        weight=0.35,
        full_confidence_at=25
    )

    score = _clamp(score, 0.0, 100.0)

    # -------------------------------------------------
    # DECISIONES
    # -------------------------------------------------
    # Sin suficiente muestra total:
    # no bloqueamos, pero tampoco sobreconfiamos
    if total_samples < 8:
        decision = "NEUTRAL"
        reason = "Historial aún limitado; sin evidencia fuerte en contra"

        return {
            "score": round(max(score, 55.0), 2),
            "decision": decision,
            "reason": reason,
            "exact_count": exact_stats["count"],
            "ticker_count": ticker_stats["count"],
            "signal_count": signal_stats["count"]
        }

    # Con suficiente muestra, sí tomamos postura
    if score >= 62:
        decision = "ALLOW"
        reason = "Historial favorable y consistente"
    elif score <= 44:
        decision = "BLOCK"
        reason = "Historial desfavorable con evidencia suficiente"
    else:
        decision = "NEUTRAL"
        reason = "Ventaja aún no concluyente"

    return {
        "score": round(score, 2),
        "decision": decision,
        "reason": reason,
        "exact_count": exact_stats["count"],
        "ticker_count": ticker_stats["count"],
        "signal_count": signal_stats["count"]
    }