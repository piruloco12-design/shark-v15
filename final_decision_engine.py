from config import (
    SNIPER_MODE,
    SNIPER_ALLOWED_REGIMES,
    SNIPER_MIN_ADX,
    SNIPER_MIN_AI_SCORE,
    SNIPER_MIN_CONTEXT_SCORE,
    SNIPER_MIN_FINAL_SCORE
)


def evaluate_final_decision(
    ai_result,
    context_result,
    session_result,
    volatility_result,
    risk_result,
    adx,
    regime
):
    """
    Semáforo final V15 Sniper.
    """

    ai_decision = ai_result.get("decision", "NEUTRAL")
    ai_score = float(ai_result.get("score", 50))

    context_decision = context_result.get("decision", "NEUTRAL")
    context_score = float(context_result.get("final_score", 50))

    session_allow = bool(session_result.get("allow", False))
    volatility_allow = bool(volatility_result.get("allow", False))
    risk_allow = bool(risk_result.get("allow", False))

    adx = float(adx)
    regime = str(regime)

    reasons = []

    if ai_decision == "BLOCK":
        reasons.append("AI bloqueó la señal")

    if context_decision == "BLOCK":
        reasons.append("Trade intelligence bloqueó el contexto")

    if not session_allow:
        reasons.append(f"Sesión no válida: {session_result.get('reason', 'N/A')}")

    if not volatility_allow:
        reasons.append(f"Volatilidad no válida: {volatility_result.get('reason', 'N/A')}")

    if not risk_allow:
        reasons.append(f"Riesgo bloqueado: {risk_result.get('reason', 'N/A')}")

    if reasons:
        score = (ai_score * 0.40) + (context_score * 0.35) + ((min(adx, 40) / 40.0) * 25.0)
        return {
            "decision": "BLOCK",
            "score": round(score, 2),
            "reason": " | ".join(reasons)
        }

    trend_score = (min(adx, 40) / 40.0) * 100.0

    score = (
        ai_score * 0.35 +
        context_score * 0.35 +
        trend_score * 0.30
    )
    score = round(score, 2)

    if SNIPER_MODE:
        if regime not in SNIPER_ALLOWED_REGIMES:
            return {
                "decision": "BLOCK",
                "score": score,
                "reason": f"Regime no permitido para sniper: {regime}"
            }

        if adx < SNIPER_MIN_ADX:
            return {
                "decision": "BLOCK",
                "score": score,
                "reason": f"ADX insuficiente para sniper: {adx:.2f}"
            }

        if ai_score < SNIPER_MIN_AI_SCORE:
            return {
                "decision": "BLOCK",
                "score": score,
                "reason": f"AI score insuficiente para sniper: {ai_score:.2f}"
            }

        if context_score < SNIPER_MIN_CONTEXT_SCORE:
            return {
                "decision": "BLOCK",
                "score": score,
                "reason": f"Context score insuficiente para sniper: {context_score:.2f}"
            }

        if score < SNIPER_MIN_FINAL_SCORE:
            return {
                "decision": "BLOCK",
                "score": score,
                "reason": f"Score final insuficiente para sniper: {score:.2f}"
            }

        return {
            "decision": "ALLOW",
            "score": score,
            "reason": "Sniper trade aprobado"
        }

    if score >= 58:
        return {
            "decision": "ALLOW",
            "score": score,
            "reason": "Todos los filtros alineados"
        }

    return {
        "decision": "BLOCK",
        "score": score,
        "reason": "Score final insuficiente"
    }