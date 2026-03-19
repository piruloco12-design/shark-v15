def scan_smart_opportunity(df):
    """
    Scanner V15 Sniper optimizado:
    - breakout alcista premium
    - breakdown bajista premium
    - pullback alcista en tendencia
    - pullback bajista en tendencia
    - continuación de tendencia con momentum

    Filosofía:
    - no regalar entradas en rango débil
    - capturar mejor tendencias reales
    - evitar condiciones demasiado rígidas
    """

    if df is None or df.empty or len(df) < 100:
        return {
            "signal": "NO_SIGNAL",
            "reason": "Sin suficiente historial"
        }

    last = df.iloc[-1]
    prev = df.iloc[-2]

    # Ventanas excluyendo la vela actual para medir rupturas reales
    lookback_20_excl_last = df.iloc[-21:-1]
    lookback_10_excl_last = df.iloc[-11:-1]
    lookback_5_excl_last = df.iloc[-6:-1]

    if (
        lookback_20_excl_last.empty or
        lookback_10_excl_last.empty or
        lookback_5_excl_last.empty
    ):
        return {
            "signal": "NO_SIGNAL",
            "reason": "Historial insuficiente para scanner"
        }

    close_price = float(last["Close"])
    prev_close = float(prev["Close"])

    ema200 = float(last["ema200"])
    rsi = float(last["rsi"])
    prev_rsi = float(prev["rsi"])

    macd = float(last["macd"])
    macd_signal = float(last["macd_signal"])
    prev_macd = float(prev["macd"])
    prev_macd_signal = float(prev["macd_signal"])

    adx = float(last["adx"])
    atr = float(last["atr"])

    prev_high_20 = float(lookback_20_excl_last["High"].max())
    prev_low_20 = float(lookback_20_excl_last["Low"].min())

    prev_high_10 = float(lookback_10_excl_last["High"].max())
    prev_low_10 = float(lookback_10_excl_last["Low"].min())

    prev_low_5 = float(lookback_5_excl_last["Low"].min())
    prev_high_5 = float(lookback_5_excl_last["High"].max())

    atr_pct = (atr / close_price) * 100 if close_price > 0 else 0.0
    price_vs_ema_pct = ((close_price - ema200) / ema200) * 100 if ema200 > 0 else 0.0

    bullish_trend = close_price > ema200
    bearish_trend = close_price < ema200

    bullish_momentum = macd > macd_signal and macd >= prev_macd
    bearish_momentum = macd < macd_signal and macd <= prev_macd

    rsi_rising = rsi > prev_rsi
    rsi_falling = rsi < prev_rsi

    # =================================================
    # 1) BREAKOUT ALCISTA PREMIUM
    # =================================================
    if (
        bullish_trend and
        adx >= 24 and
        bullish_momentum and
        macd > 0 and
        56 <= rsi <= 74 and
        close_price > prev_high_20 * 1.001 and
        atr_pct >= 0.30
    ):
        return {
            "signal": "BUY",
            "reason": "Breakout alcista premium con ruptura real, tendencia y fuerza"
        }

    # =================================================
    # 2) BREAKDOWN BAJISTA PREMIUM
    # =================================================
    if (
        bearish_trend and
        adx >= 24 and
        bearish_momentum and
        macd < 0 and
        26 <= rsi <= 46 and
        close_price < prev_low_20 * 0.999 and
        atr_pct >= 0.30
    ):
        return {
            "signal": "SELL",
            "reason": "Breakdown bajista premium con ruptura real, tendencia y fuerza"
        }

    # =================================================
    # 3) PULLBACK ALCISTA EN TENDENCIA
    # =================================================
    if (
        bullish_trend and
        adx >= 22 and
        44 <= rsi <= 60 and
        macd >= macd_signal and
        rsi_rising and
        close_price > prev_close and
        close_price > prev_low_5 * 1.006 and
        price_vs_ema_pct >= 0.30
    ):
        return {
            "signal": "BUY",
            "reason": "Pullback alcista en tendencia con reanudación de momentum"
        }

    # =================================================
    # 4) PULLBACK BAJISTA EN TENDENCIA
    # =================================================
    if (
        bearish_trend and
        adx >= 22 and
        38 <= rsi <= 56 and
        macd <= macd_signal and
        rsi_falling and
        close_price < prev_close and
        close_price < prev_high_5 * 0.994 and
        price_vs_ema_pct <= -0.30
    ):
        return {
            "signal": "SELL",
            "reason": "Pullback bajista en tendencia con reanudación de momentum"
        }

    # =================================================
    # 5) CONTINUACIÓN ALCISTA EN TENDENCIA
    # =================================================
    if (
        bullish_trend and
        adx >= 25 and
        macd > macd_signal and
        macd > 0 and
        rsi >= 58 and
        close_price > prev_high_10 * 1.000 and
        atr_pct >= 0.28
    ):
        return {
            "signal": "BUY",
            "reason": "Continuación alcista con tendencia fuerte y momentum sostenido"
        }

    # =================================================
    # 6) CONTINUACIÓN BAJISTA EN TENDENCIA
    # =================================================
    if (
        bearish_trend and
        adx >= 25 and
        macd < macd_signal and
        macd < 0 and
        rsi <= 44 and
        close_price < prev_low_10 * 1.000 and
        atr_pct >= 0.28
    ):
        return {
            "signal": "SELL",
            "reason": "Continuación bajista con tendencia fuerte y momentum sostenido"
        }

    return {
        "signal": "NO_SIGNAL",
        "reason": "No se detectó oportunidad sniper"
    }