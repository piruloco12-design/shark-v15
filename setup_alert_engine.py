def detect_setup_watch(df, regime):
    """
    Detecta setups en formación aunque todavía no haya trade.
    Devuelve:
    - WATCH_BUY
    - WATCH_SELL
    - NONE
    """

    if df is None or df.empty or len(df) < 60:
        return {
            "alert_type": "NONE",
            "reason": "Sin suficiente historial"
        }

    last = df.iloc[-1]
    recent = df.tail(12)

    close_price = float(last["Close"])
    ema200 = float(last["ema200"])
    rsi = float(last["rsi"])
    macd = float(last["macd"])
    macd_signal = float(last["macd_signal"])
    adx = float(last["adx"])

    recent_high = float(recent["High"].max())
    recent_low = float(recent["Low"].min())

    distance_to_high_pct = ((recent_high - close_price) / close_price) * 100 if close_price > 0 else 999
    distance_to_low_pct = ((close_price - recent_low) / close_price) * 100 if close_price > 0 else 999

    # WATCH BUY
    if (
        close_price > ema200 and
        adx >= 18 and
        macd >= macd_signal and
        48 <= rsi <= 62 and
        distance_to_high_pct <= 1.2
    ):
        return {
            "alert_type": "WATCH_BUY",
            "reason": f"Posible breakout alcista en formación | Regime={regime} | DistHigh={distance_to_high_pct:.2f}%"
        }

    # WATCH SELL
    if (
        close_price < ema200 and
        adx >= 18 and
        macd <= macd_signal and
        38 <= rsi <= 52 and
        distance_to_low_pct <= 1.2
    ):
        return {
            "alert_type": "WATCH_SELL",
            "reason": f"Posible breakdown bajista en formación | Regime={regime} | DistLow={distance_to_low_pct:.2f}%"
        }

    return {
        "alert_type": "NONE",
        "reason": "Sin setup cercano"
    }