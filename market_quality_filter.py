# market_quality_filter.py

def evaluate_market_quality(data):
    """
    Evalúa si el mercado tiene calidad suficiente para operar.
    Filtra rangos muertos / chop / baja volatilidad.
    """

    last = data.iloc[-1]

    atr = float(last.get("atr", 0))
    adx = float(last.get("adx", 0))

    # -------------------------------------------------
    # FILTRO 1: VOLATILIDAD MÍNIMA (CRÍTICO)
    # -------------------------------------------------
    if atr < 0.5:
        return {
            "allow": False,
            "reason": f"ATR demasiado bajo: {atr:.2f} (mercado muerto)"
        }

    # -------------------------------------------------
    # FILTRO 2: TENDENCIA REAL (no fake)
    # -------------------------------------------------
    if adx < 25:
        return {
            "allow": False,
            "reason": f"ADX débil: {adx:.2f} (<25)"
        }

    return {
        "allow": True,
        "reason": "Mercado con calidad suficiente"
    }