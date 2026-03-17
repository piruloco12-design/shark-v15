from market_regime import detect_market_regime


def check_signal(df):
    last = df.iloc[-1]

    close = float(last["Close"])
    ema = float(last["ema200"])
    rsi = float(last["rsi"])
    macd = float(last["macd"])
    macd_signal = float(last["macd_signal"])

    regime = detect_market_regime(df)

    # solo operamos en tendencias claras
    if regime == "BULL_TREND":
        if close > ema and rsi < 50 and macd > macd_signal:
            return "BUY"

    if regime == "BEAR_TREND":
        if close < ema and rsi > 50 and macd < macd_signal:
            return "SELL"

    return "NO_SIGNAL"