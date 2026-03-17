from config import (
    SNIPER_MODE,
    SNIPER_ALLOWED_REGIMES,
    SNIPER_MIN_ADX,
    SNIPER_MIN_AI_SCORE,
    SNIPER_MIN_CONTEXT_SCORE,
    SNIPER_MIN_FINAL_SCORE,
    NORMAL_MIN_FINAL_SCORE
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


def _normalize_reason(value, default="N/A"):
    if value is None:
        return default
    text = str(value).strip()
    return text if text else default


def _clamp(value, min_value=0.0, max_value=100.0):
    return max(min_value, min(max_value, value))


def _build_base_score(ai_score, context_score, adx):
    """
    Score central V15:
    - AI quality
    - Context quality
    - Trend strength via ADX
    """
    trend_score = (_clamp(min(adx, 40.0), 0.0, 40.0) / 40.0) * 100.0

    score = (
        ai_score * 0.35 +
        context_score * 0.40 +
        trend_score * 0.25
    )

    return round(_clamp(score), 2)


def _collect_hard_block_reasons(
    ai_decision,
    context_decision,
    session_allow,
    volatility_allow,
    risk_allow,
    session_result,
    volatility_result,
    risk_result
):
    reasons = []

    if ai_decision == "BLOCK":
        reasons.append("AI bloqueó la señal")

    if context_decision == "BLOCK":
        reasons.append("Trade intelligence bloqueó el contexto")

    if not session_allow:
        reasons.append(
            f"Sesión no válida: {_normalize_reason(session_result.get('reason'))}"
        )

    if not volatility_allow:
        reasons.append(
            f"Volatilidad no válida: {_normalize_reason(volatility_result.get('reason'))}"
        )

    if not risk_allow:
        reasons.append(
            f"Riesgo bloqueado: {_normalize_reason(risk_result.get('reason'))}"
        )

    return reasons


def _collect_sniper_block_reasons(regime, adx, ai_score, context_score, final_score):
    reasons = []

    if regime not in SNIPER_ALLOWED_REGIMES:
        reasons.append(f"Regime no permitido para sniper: {regime}")

    if adx < SNIPER_MIN_ADX:
        reasons.append(f"ADX insuficiente para sniper: {adx:.2f} < {SNIPER_MIN_ADX}")

    if ai_score < SNIPER_MIN_AI_SCORE:
        reasons.append(f"AI score insuficiente para sniper: {ai_score:.2f} < {SNIPER_MIN_AI_SCORE}")

    if context_score < SNIPER_MIN_CONTEXT_SCORE:
        reasons.append(f"Context score insuficiente para sniper: {context_score:.2f} < {SNIPER_MIN_CONTEXT_SCORE}")

    if final_score < SNIPER_MIN_FINAL_SCORE:
        reasons.append(f"Score final insuficiente para sniper: {final_score:.2f} < {SNIPER_MIN_FINAL_SCORE}")

    return reasons


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
    CEREBRO FINAL V15 SNIPER

    Flujo:
    1. Validar hard blocks operativos
    2. Calcular score unificado
    3. Aplicar filtros sniper
    4. Decidir ALLOW o BLOCK
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

    base_score = _build_base_score(
        ai_score=ai_score,
        context_score=context_score,
        adx=adx
    )

    hard_block_reasons = _collect_hard_block_reasons(
        ai_decision=ai_decision,
        context_decision=context_decision,
        session_allow=session_allow,
        volatility_allow=volatility_allow,
        risk_allow=risk_allow,
        session_result=session_result,
        volatility_result=volatility_result,
        risk_result=risk_result
    )

    if hard_block_reasons:
        return {
            "decision": "BLOCK",
            "score": base_score,
            "reason": " | ".join(hard_block_reasons),
            "debug": {
                "mode": "SNIPER" if SNIPER_MODE else "NORMAL",
                "ai_score": round(ai_score, 2),
                "context_score": round(context_score, 2),
                "adx": round(adx, 2),
                "regime": regime,
                "hard_block": True,
                "sniper_checks_passed": False
            }
        }

    if SNIPER_MODE:
        sniper_block_reasons = _collect_sniper_block_reasons(
            regime=regime,
            adx=adx,
            ai_score=ai_score,
            context_score=context_score,
            final_score=base_score
        )

        if sniper_block_reasons:
            return {
                "decision": "BLOCK",
                "score": base_score,
                "reason": " | ".join(sniper_block_reasons),
                "debug": {
                    "mode": "SNIPER",
                    "ai_score": round(ai_score, 2),
                    "context_score": round(context_score, 2),
                    "adx": round(adx, 2),
                    "regime": regime,
                    "hard_block": False,
                    "sniper_checks_passed": False
                }
            }

        return {
            "decision": "ALLOW",
            "score": base_score,
            "reason": "Sniper trade aprobado: filtros y score alineados",
            "debug": {
                "mode": "SNIPER",
                "ai_score": round(ai_score, 2),
                "context_score": round(context_score, 2),
                "adx": round(adx, 2),
                "regime": regime,
                "hard_block": False,
                "sniper_checks_passed": True
            }
        }

    if base_score >= NORMAL_MIN_FINAL_SCORE:
        return {
            "decision": "ALLOW",
            "score": base_score,
            "reason": "Todos los filtros alineados",
            "debug": {
                "mode": "NORMAL",
                "ai_score": round(ai_score, 2),
                "context_score": round(context_score, 2),
                "adx": round(adx, 2),
                "regime": regime,
                "hard_block": False,
                "sniper_checks_passed": None
            }
        }

    return {
        "decision": "BLOCK",
        "score": base_score,
        "reason": f"Score final insuficiente: {base_score:.2f} < {NORMAL_MIN_FINAL_SCORE}",
        "debug": {
            "mode": "NORMAL",
            "ai_score": round(ai_score, 2),
            "context_score": round(context_score, 2),
            "adx": round(adx, 2),
            "regime": regime,
            "hard_block": False,
            "sniper_checks_passed": None
        }
    }