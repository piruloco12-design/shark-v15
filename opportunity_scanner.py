from market_regime import detect_market_regime


def _safe_float(value, default=0.0):
    try:
        return float(value)
    except Exception:
        return default


def _count_true(*conditions):
    return sum(1 for c in conditions if c)


def scan_smart_opportunity(df):
    """
    Scanner — versión con filtro de régimen y condiciones relajadas.
    """

    if df is None or df.empty or len(df) < 100:
        return {
            "signal": "NO_SIGNAL",
            "reason": "Sin suficiente historial"
        }

    regime = str(detect_market_regime(df)).strip().upper()

    if regime in ("RANGE", "HIGH_VOL"):
        return {
            "signal": "NO_SIGNAL",
            "reason": f"Scanner bloqueado: régimen {regime}"
        }

    last = df.iloc[-1]
    prev = df.iloc[-2]

    lookback_20 = df.iloc[-21:-1]
    lookback_10 = df.iloc[-11:-1]
    lookback_5 = df.iloc[-6:-1]

    if lookback_20.empty or lookback_10.empty or lookback_5.empty:
        return {
            "signal": "NO_SIGNAL",
            "reason": "Historial insuficiente para scanner"
        }

    close = _safe_float(last["Close"])
    prev_close = _safe_float(prev["Close"])
    ema200 = _safe_float(last["ema200"])
    rsi = _safe_float(last["rsi"])
    prev_rsi = _safe_float(prev["rsi"])
    macd = _safe_float(last["macd"])
    macd_signal_val = _safe_float(last["macd_signal"])
    prev_macd = _safe_float(prev["macd"])
    adx = _safe_float(last["adx"])

    prev_high_20 = _safe_float(lookback_20["High"].max())
    prev_low_20 = _safe_float(lookback_20["Low"].min())
    prev_high_10 = _safe_float(lookback_10["High"].max())
    prev_low_10 = _safe_float(lookback_10["Low"].min())

    price_vs_ema_pct = ((close - ema200) / ema200) * 100 if ema200 > 0 else 0.0

    bullish_trend = close > ema200
    bearish_trend = close < ema200

    bullish_momentum = _count_true(
        macd > macd_signal_val,
        macd >= prev_macd,
        rsi > prev_rsi
    ) >= 2

    bearish_momentum = _count_true(
        macd < macd_signal_val,
        macd <= prev_macd,
        rsi < prev_rsi
    ) >= 2

    # 1) BREAKOUT ALCISTA
    if (
        bullish_trend and
        adx >= 22 and
        bullish_momentum and
        50 <= rsi <= 78 and
        close > prev_high_20 * 1.001
    ):
        return {
            "signal": "BUY",
            "reason": "Breakout alcista: ruptura de high_20 con tendencia y momentum"
        }

    # 2) BREAKDOWN BAJISTA
    if (
        bearish_trend and
        adx >= 22 and
        bearish_momentum and
        22 <= rsi <= 50 and
        close < prev_low_20 * 0.999
    ):
        return {
            "signal": "SELL",
            "reason": "Breakdown bajista: ruptura de low_20 con tendencia y momentum"
        }

    # 3) PULLBACK ALCISTA
    if (
        bullish_trend and
        adx >= 20 and
        macd >= macd_signal_val and
        40 <= rsi <= 62 and
        close > prev_close and
        price_vs_ema_pct >= 0.10
    ):
        return {
            "signal": "BUY",
            "reason": "Pullback alcista: rebote en tendencia con MACD favorable"
        }

    # 4) PULLBACK BAJISTA
    if (
        bearish_trend and
        adx >= 20 and
        macd <= macd_signal_val and
        38 <= rsi <= 60 and
        close < prev_close and
        price_vs_ema_pct <= -0.10
    ):
        return {
            "signal": "SELL",
            "reason": "Pullback bajista: continuación en tendencia con MACD desfavorable"
        }

    # 5) CONTINUACIÓN ALCISTA
    if (
        bullish_trend and
        adx >= 23 and
        macd > macd_signal_val and
        rsi >= 54 and
        close > prev_high_10
    ):
        return {
            "signal": "BUY",
            "reason": "Continuación alcista: tendencia fuerte con momentum sostenido"
        }

    # 6) CONTINUACIÓN BAJISTA
    if (
        bearish_trend and
        adx >= 23 and
        macd < macd_signal_val and
        rsi <= 46 and
        close < prev_low_10
    ):
        return {
            "signal": "SELL",
            "reason": "Continuación bajista: tendencia fuerte con momentum sostenido"
        }

    return {
        "signal": "NO_SIGNAL",
        "reason": "No se detectó oportunidad sniper"
    }