def _safe_float(value, default=0.0):
    try:
        return float(value)
    except Exception:
        return default


def detect_market_regime(df):
    """
    Detector de régimen V15 — Tanda 3 optimizada.

    Cambios vs versión anterior:
    - eliminado close >= prev_close de bullish_structure
    - eliminado close <= prev_close de bearish_structure
      (una sola vela roja no invalida una tendencia alcista,
       una sola vela verde no invalida una tendencia bajista)
    - price_vs_ema_pct bajado de 0.30 a 0.15 para BULL/BEAR_TREND
    - price_vs_ema_pct bajado de 0.10 a 0.05 para TREND genérico
    - ADX para BULL/BEAR_TREND bajado de 26 a 23
    - ADX para TREND genérico bajado de 22 a 20

    Objetivo:
    - detectar tendencia MÁS TEMPRANO (no cuando ya está extendida)
    - permitir que el bot entre con recorrido suficiente hasta TP
    - mantener la cascada BULL/BEAR_TREND > TREND > HIGH_VOL > RANGE
    - no mandar tendencias reales a RANGE por una vela de pausa
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

    # Estructura alcista: precio sobre EMA, MACD favorable, RSI no deprimido
    # Ya NO exige close >= prev_close (una vela roja no mata la tendencia)
    bullish_structure = (
        close > ema and
        macd >= macd_signal and
        rsi >= 46
    )

    # Estructura bajista: precio bajo EMA, MACD desfavorable, RSI no elevado
    # Ya NO exige close <= prev_close (una vela verde no mata la tendencia)
    bearish_structure = (
        close < ema and
        macd <= macd_signal and
        rsi <= 54
    )

    # =================================================
    # 1) TENDENCIAS FUERTES
    # =================================================
    if adx >= 23:
        if bullish_structure and price_vs_ema_pct >= 0.15:
            return "BULL_TREND"

        if bearish_structure and price_vs_ema_pct <= -0.15:
            return "BEAR_TREND"

    # =================================================
    # 2) TENDENCIA GENÉRICA (menos exigente)
    # =================================================
    if adx >= 20:
        if bullish_structure and price_vs_ema_pct >= 0.05:
            return "TREND"

        if bearish_structure and price_vs_ema_pct <= -0.05:
            return "TREND"

    # =================================================
    # 3) VOLATILIDAD ALTA SIN ESTRUCTURA CLARA
    # =================================================
    if atr_mean > 0 and atr >= atr_mean * 1.35 and adx < 20:
        return "HIGH_VOL"

    # =================================================
    # 4) RESTO = RANGO
    # =================================================
    return "RANGE"