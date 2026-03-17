from asset_ranker import calculate_asset_scores


def get_asset_scale_factor(ticker):
    """
    Devuelve un multiplicador de tamaño según el historial del activo.

    Rango típico:
    0.70  -> activo flojo
    1.00  -> neutro
    1.25  -> bueno
    1.50  -> muy bueno
    """

    scores = calculate_asset_scores()

    # Sin historial: neutro
    if not scores or ticker not in scores:
        return {
            "scale_factor": 1.0,
            "score": 0.0,
            "reason": "Sin historial suficiente"
        }

    asset_data = scores[ticker]
    score = float(asset_data["score"])
    trades = int(asset_data["trades"])

    # Si todavía hay muy pocos trades, no escalamos agresivamente
    if trades < 5:
        return {
            "scale_factor": 1.0,
            "score": score,
            "reason": "Historial insuficiente, tamaño neutro"
        }

    if score >= 60:
        return {
            "scale_factor": 1.50,
            "score": score,
            "reason": "Activo muy fuerte"
        }

    if score >= 45:
        return {
            "scale_factor": 1.25,
            "score": score,
            "reason": "Activo favorable"
        }

    if score >= 25:
        return {
            "scale_factor": 1.00,
            "score": score,
            "reason": "Activo neutro"
        }

    return {
        "scale_factor": 0.70,
        "score": score,
        "reason": "Activo débil, reducir tamaño"
    }


def apply_position_scaling(trade_setup, ticker):
    """
    Ajusta position_size y risk_amount sin tocar entry/SL/TP.
    """
    scale_info = get_asset_scale_factor(ticker)
    scale_factor = float(scale_info["scale_factor"])

    scaled_trade = dict(trade_setup)

    scaled_trade["position_size"] = float(trade_setup["position_size"]) * scale_factor
    scaled_trade["scaled_risk_amount"] = float(trade_setup["risk_amount"]) * scale_factor
    scaled_trade["scale_factor"] = scale_factor
    scaled_trade["asset_score"] = float(scale_info["score"])
    scaled_trade["scale_reason"] = scale_info["reason"]

    return scaled_trade