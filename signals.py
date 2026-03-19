from market_regime import detect_market_regime


def _safe_float(value, default=0.0):
    try:
        return float(value)
    except Exception:
        return default


def check_signal(df):
    """
    Señal base V15 optimizada.

    Objetivo:
    - captar continuación simple en tendencia
    - no pelear contra el régimen
    - dejar al scanner avanzado las entradas más finas
    """

    if df is None or df.empty or len(df) < 3:
        return "NO_SIGNAL"

    last = df.iloc[-1]
    prev = df.iloc[-2]

    close = _safe_float(last["Close"])
    prev_close = _safe_float(prev["Close"])

    ema = _safe_float(last["ema200"])

    rsi = _safe_float(last["rsi"])
    prev_rsi = _safe_float(prev["rsi"])

    macd = _safe_float(last["macd"])
    macd_signal = _safe_float(last["macd_signal"])
    prev_macd = _safe_float(prev["macd"])
    prev_macd_signal = _safe_float(prev["macd_signal"])

    adx = _safe_float(last["adx"])

    regime = str(detect_market_regime(df)).strip().upper()

    bullish_bias = (
        close > ema and
        macd > macd_signal and
        rsi >= 50 and
        adx >= 22
    )

    bearish_bias = (
        close < ema and
        macd < macd_signal and
        rsi <= 50 and
        adx >= 22
    )

    bullish_reacceleration = (
        close > prev_close and
        rsi >= prev_rsi and
        macd >= prev_macd
    )

    bearish_reacceleration = (
        close < prev_close and
        rsi <= prev_rsi and
        macd <= prev_macd
    )

    # =================================================
    # BULL TREND
    # =================================================
    if regime == "BULL_TREND":
        if bullish_bias and bullish_reacceleration:
            return "BUY"

    # =================================================
    # BEAR TREND
    # =================================================
    if regime == "BEAR_TREND":
        if bearish_bias and bearish_reacceleration:
            return "SELL"

    # =================================================
    # TREND genérico
    # =================================================
    if regime == "TREND":
        if bullish_bias and bullish_reacceleration:
            return "BUY"

        if bearish_bias and bearish_reacceleration:
            return "SELL"

    return "NO_SIGNAL"