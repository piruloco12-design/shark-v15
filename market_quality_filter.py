from config import (
    V16_MARKET_FILTER_ENABLED,
    V16_MIN_ATR_PCT,
    V16_MIN_ADX_QUALITY,
    V16_MIN_LAST5_RANGE_ATR,
    V16_BLOCK_RANGE,
    V16_BLOCK_HIGH_VOL,
)


def _safe_float(value, default=0.0):
    try:
        return float(value)
    except Exception:
        return default


def evaluate_market_quality(data, regime):
    """
    Filtro V16:
    - bloquea régimen flojo si así se configuró
    - exige ADX mínimo real
    - exige ATR% mínimo
    - evita compresión excesiva de las últimas 5 velas
    """

    if not V16_MARKET_FILTER_ENABLED:
        return {
            "allow": True,
            "reason": "Filtro V16 desactivado"
        }

    if data is None or data.empty or len(data) < 20:
        return {
            "allow": False,
            "reason": "Historial insuficiente para filtro de calidad"
        }

    regime = str(regime).strip().upper()

    if V16_BLOCK_RANGE and regime == "RANGE":
        return {
            "allow": False,
            "reason": "Régimen RANGE bloqueado por V16"
        }

    if V16_BLOCK_HIGH_VOL and regime == "HIGH_VOL":
        return {
            "allow": False,
            "reason": "Régimen HIGH_VOL bloqueado por V16"
        }

    last = data.iloc[-1]
    recent_5 = data.tail(5)

    close = _safe_float(last.get("Close"))
    atr = _safe_float(last.get("atr"))
    adx = _safe_float(last.get("adx"))

    if close <= 0:
        return {
            "allow": False,
            "reason": "Close inválido para filtro de calidad"
        }

    atr_pct = (atr / close) * 100 if close > 0 else 0.0
    recent_high = _safe_float(recent_5["High"].max())
    recent_low = _safe_float(recent_5["Low"].min())
    recent_range = recent_high - recent_low
    range_vs_atr = recent_range / atr if atr > 0 else 0.0

    if adx < V16_MIN_ADX_QUALITY:
        return {
            "allow": False,
            "reason": f"Calidad baja: ADX {adx:.2f} < {V16_MIN_ADX_QUALITY:.2f}"
        }

    if atr_pct < V16_MIN_ATR_PCT:
        return {
            "allow": False,
            "reason": f"Calidad baja: ATR% {atr_pct:.2f} < {V16_MIN_ATR_PCT:.2f}"
        }

    if range_vs_atr < V16_MIN_LAST5_RANGE_ATR:
        return {
            "allow": False,
            "reason": f"Calidad baja: compresión últimas 5 velas ({range_vs_atr:.2f} ATR)"
        }

    return {
        "allow": True,
        "reason": (
            f"Mercado válido | ADX {adx:.2f} | ATR% {atr_pct:.2f} | "
            f"Range5/ATR {range_vs_atr:.2f}"
        )
    }