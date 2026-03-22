from config import (
    SNIPER_MODE,
    SNIPER_ALLOWED_REGIMES,
    SNIPER_MIN_ADX,
    SNIPER_MIN_AI_SCORE,
    SNIPER_MIN_CONTEXT_SCORE,
    SNIPER_MIN_FINAL_SCORE,
    NORMAL_MIN_FINAL_SCORE,
)


def _safe_float(value, default=0.0):
    try:
        return float(value)
    except Exception:
        return default


def _safe_bool(value, default=False):
    try:
        return bool(value)
    except Exception:
        return default


def _clamp(value, min_value=0.0, max_value=100.0):
    return max(min_value, min(max_value, value))


def _build_base_score(ai_score, context_score, adx):
    """
    Score central: AI 35%, Context 40%, ADX 25%.
    Esta fórmula fue la que produjo edge positivo.
    """
    trend_score = (_clamp(min(adx, 40.0), 0.0, 40.0) / 40.0) * 100.0
    score = (
        ai_score * 0.35 +
        context_score * 0.40 +
        trend_score * 0.25
    )
    return round(_clamp(score), 2)


def evaluate_final_decision(
    ai_result,
    context_result,
    session_result,
    volatility_result,
    risk_result,
    adx,
    regime,
    data=None,
    ticker=None,
):
    """
    Cerebro final — versión que demostró edge positivo.

    Acepta data y ticker como parámetros opcionales para
    compatibilidad con llamadas V16, pero no los usa para
    filtros adicionales (esos filtros destruyeron el edge).
    """

    ai_decision = str(ai_result.get("decision", "NEUTRAL")).upper()
    ai_score = _clamp(_safe_float(ai_result.get("score", 50.0), 50.0))

    context_decision = str(context_result.get("decision", "NEUTRAL")).upper()
    context_score = _clamp(_safe_float(context_result.get("final_score", 50.0), 50.0))

    session_allow = _safe_bool(session_result.get("allow", False), False)
    volatility_allow = _safe_bool(volatility_result.get("allow", False), False)
    risk_allow = _safe_bool(risk_result.get("allow", False), False)

    adx = _safe_float(adx, 0.0)
    regime = str(regime).strip().upper()

    base_score = _build_base_score(ai_score, context_score, adx)

    debug = {
        "mode": "SNIPER" if SNIPER_MODE else "NORMAL",
        "ai_score": round(ai_score, 2),
        "context_score": round(context_score, 2),
        "adx": round(adx, 2),
        "regime": regime,
        "final_score": base_score,
        "ticker": ticker,
    }

    # -------------------------------------------------
    # HARD BLOCKS
    # -------------------------------------------------
    if ai_decision == "BLOCK":
        return {
            "decision": "BLOCK",
            "score": base_score,
            "reason": "AI bloqueó la señal",
            "debug": debug,
        }

    if context_decision == "BLOCK":
        return {
            "decision": "BLOCK",
            "score": base_score,
            "reason": "Trade intelligence bloqueó el contexto",
            "debug": debug,
        }

    if not session_allow:
        return {
            "decision": "BLOCK",
            "score": base_score,
            "reason": f"Sesión no válida: {session_result.get('reason', 'N/A')}",
            "debug": debug,
        }

    if not volatility_allow:
        return {
            "decision": "BLOCK",
            "score": base_score,
            "reason": f"Volatilidad no válida: {volatility_result.get('reason', 'N/A')}",
            "debug": debug,
        }

    if not risk_allow:
        return {
            "decision": "BLOCK",
            "score": base_score,
            "reason": f"Riesgo bloqueado: {risk_result.get('reason', 'N/A')}",
            "debug": debug,
        }

    # -------------------------------------------------
    # SNIPER MODE
    # -------------------------------------------------
    if SNIPER_MODE:
        blocks = []

        if regime not in SNIPER_ALLOWED_REGIMES:
            blocks.append(f"Regime no permitido para entrada sniper: {regime}")

        if adx < SNIPER_MIN_ADX:
            blocks.append(f"ADX insuficiente para sniper: {adx:.2f} < {SNIPER_MIN_ADX}")

        if ai_score < SNIPER_MIN_AI_SCORE:
            blocks.append(f"AI score insuficiente para sniper: {ai_score:.2f} < {SNIPER_MIN_AI_SCORE}")

        if context_score < SNIPER_MIN_CONTEXT_SCORE:
            blocks.append(f"Context score insuficiente para sniper: {context_score:.2f} < {SNIPER_MIN_CONTEXT_SCORE}")

        if base_score < SNIPER_MIN_FINAL_SCORE:
            blocks.append(f"Score final insuficiente para sniper: {base_score:.2f} < {SNIPER_MIN_FINAL_SCORE}")

        if blocks:
            return {
                "decision": "BLOCK",
                "score": base_score,
                "reason": " | ".join(blocks),
                "debug": debug,
            }

        return {
            "decision": "ALLOW",
            "score": base_score,
            "reason": "Sniper trade aprobado",
            "debug": debug,
        }

    # -------------------------------------------------
    # NORMAL MODE
    # -------------------------------------------------
    if regime == "RANGE":
        return {
            "decision": "BLOCK",
            "score": base_score,
            "reason": "Modo normal bloqueó entrada en RANGE",
            "debug": debug,
        }

    if base_score >= NORMAL_MIN_FINAL_SCORE:
        return {
            "decision": "ALLOW",
            "score": base_score,
            "reason": "Todos los filtros alineados",
            "debug": debug,
        }

    return {
        "decision": "BLOCK",
        "score": base_score,
        "reason": f"Score final insuficiente: {base_score:.2f} < {NORMAL_MIN_FINAL_SCORE}",
        "debug": debug,
    }