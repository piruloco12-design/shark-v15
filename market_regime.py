def _safe_float(value, default=0.0):
    try:
        return float(value)
    except Exception:
        return default


def detect_market_regime(df):
    """
    Detector de régimen — versión que formó parte del edge positivo.

    Características:
    - NO exige close >= prev_close (una vela de pausa no mata tendencia)
    - RSI relajado (46 bull, 54 bear)
    - ADX 23 para BULL/BEAR_TREND, 20 para TREND genérico
    - price_vs_ema_pct 0.15 para fuertes, 0.05 para genérico
    """

    if df is None or df.empty or len(df) < 60:
        return "RANGE"

    last = df.iloc[-1]

    close = _safe_float(last["Close"])
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
        macd >= macd_signal and
        rsi >= 46
    )

    bearish_structure = (
        close < ema and
        macd <= macd_signal and
        rsi <= 54
    )

    # 1) TENDENCIAS FUERTES
    if adx >= 23:
        if bullish_structure and price_vs_ema_pct >= 0.15:
            return "BULL_TREND"
        if bearish_structure and price_vs_ema_pct <= -0.15:
            return "BEAR_TREND"

    # 2) TENDENCIA GENÉRICA
    if adx >= 20:
        if bullish_structure and price_vs_ema_pct >= 0.05:
            return "TREND"
        if bearish_structure and price_vs_ema_pct <= -0.05:
            return "TREND"

    # 3) VOLATILIDAD ALTA SIN ESTRUCTURA
    if atr_mean > 0 and atr >= atr_mean * 1.35 and adx < 20:
        return "HIGH_VOL"

    # 4) RANGO
    return "RANGE"