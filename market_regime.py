def _safe_float(value, default=0.0):
    try:
        return float(value)
    except Exception:
        return default


def detect_market_regime(df):
    """
    Detector de régimen V15 optimizado.

    Prioridades:
    - identificar tendencia útil sin depender demasiado del ATR
    - no mandar demasiado mercado a RANGE
    - usar ADX como fuerza principal
    - conservar una salida HIGH_VOL cuando haya desorden extremo
    """

    if df is None or df.empty or len(df) < 60:
        return "RANGE"

    last = df.iloc[-1]
    prev = df.iloc[-2]

    close = _safe_float(last["Close"])
    prev_close = _safe_float(prev["Close"])

    ema = _safe_float(last["ema200"])
    adx = _safe_float(last["adx"])
    atr = _safe_float(last["atr"])
    rsi = _safe_float(last["rsi"])
    macd = _safe_float(last["macd"])
    macd_signal = _safe_float(last["macd_signal"])

    atr_mean = _safe_float(df["atr"].rolling(50).mean().iloc[-1])
    price_vs_ema_pct = ((close - ema) / ema) * 100 if ema > 0 else 0.0

    bullish_structure = (
        close > ema and
        close >= prev_close and
        macd >= macd_signal and
        rsi >= 48
    )

    bearish_structure = (
        close < ema and
        close <= prev_close and
        macd <= macd_signal and
        rsi <= 52
    )

    # =================================================
    # 1) TENDENCIAS FUERTES
    # =================================================
    if adx >= 26:
        if bullish_structure and price_vs_ema_pct >= 0.30:
            return "BULL_TREND"

        if bearish_structure and price_vs_ema_pct <= -0.30:
            return "BEAR_TREND"

    # =================================================
    # 2) TENDENCIA GENÉRICA (menos exigente)
    # =================================================
    if adx >= 22:
        if bullish_structure and price_vs_ema_pct >= 0.10:
            return "TREND"

        if bearish_structure and price_vs_ema_pct <= -0.10:
            return "TREND"

    # =================================================
    # 3) VOLATILIDAD ALTA SIN ESTRUCTURA CLARA
    # =================================================
    if atr_mean > 0 and atr >= atr_mean * 1.35 and adx < 22:
        return "HIGH_VOL"

    # =================================================
    # 4) RESTO = RANGO
    # =================================================
    return "RANGE"