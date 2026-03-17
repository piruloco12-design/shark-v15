def scan_smart_opportunity(df):
    """
    Scanner V15 Sniper:
    - breakout alcista premium
    - breakdown bajista premium
    - pullback en tendencia alcista
    - pullback en tendencia bajista
    """

    if df is None or df.empty or len(df) < 100:
        return {
            "signal": "NO_SIGNAL",
            "reason": "Sin suficiente historial"
        }

    last = df.iloc[-1]
    prev = df.iloc[-2]

    recent_20 = df.tail(20)
    recent_10 = df.tail(10)
    recent_5 = df.tail(5)

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

    recent_high_20 = float(recent_20["High"].max())
    recent_low_20 = float(recent_20["Low"].min())

    recent_high_10 = float(recent_10["High"].max())
    recent_low_10 = float(recent_10["Low"].min())

    recent_low_5 = float(recent_5["Low"].min())
    recent_high_5 = float(recent_5["High"].max())

    atr_pct = (atr / close_price) * 100 if close_price > 0 else 0.0

    # -------------------------------------------------
    # 1) BREAKOUT ALCISTA PREMIUM
    # -------------------------------------------------
    if (
        close_price > ema200 and
        adx >= 24 and
        macd > macd_signal and
        macd > 0 and
        56 <= rsi <= 72 and
        close_price >= recent_high_20 * 0.998 and
        atr_pct >= 0.30
    ):
        return {
            "signal": "BUY",
            "reason": "Breakout alcista premium con tendencia y fuerza"
        }

    # -------------------------------------------------
    # 2) BREAKDOWN BAJISTA PREMIUM
    # -------------------------------------------------
    if (
        close_price < ema200 and
        adx >= 24 and
        macd < macd_signal and
        macd < 0 and
        28 <= rsi <= 44 and
        close_price <= recent_low_20 * 1.002 and
        atr_pct >= 0.30
    ):
        return {
            "signal": "SELL",
            "reason": "Breakdown bajista premium con tendencia y fuerza"
        }

    # -------------------------------------------------
    # 3) PULLBACK ALCISTA EN TENDENCIA
    # -------------------------------------------------
    if (
        close_price > ema200 and
        adx >= 22 and
        45 <= rsi <= 58 and
        macd >= macd_signal and
        prev_macd <= prev_macd_signal and
        close_price > recent_low_5 * 1.01 and
        close_price > prev_close and
        rsi > prev_rsi
    ):
        return {
            "signal": "BUY",
            "reason": "Pullback alcista en tendencia con reanudación de momentum"
        }

    # -------------------------------------------------
    # 4) PULLBACK BAJISTA EN TENDENCIA
    # -------------------------------------------------
    if (
        close_price < ema200 and
        adx >= 22 and
        42 <= rsi <= 55 and
        macd <= macd_signal and
        prev_macd >= prev_macd_signal and
        close_price < recent_high_5 * 0.99 and
        close_price < prev_close and
        rsi < prev_rsi
    ):
        return {
            "signal": "SELL",
            "reason": "Pullback bajista en tendencia con reanudación de momentum"
        }

    return {
        "signal": "NO_SIGNAL",
        "reason": "No se detectó oportunidad sniper"
    }