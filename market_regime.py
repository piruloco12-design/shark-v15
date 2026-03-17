def detect_market_regime(df):
    last = df.iloc[-1]

    close = float(last["Close"])
    ema = float(last["ema200"])
    adx = float(last["adx"])
    atr = float(last["atr"])

    atr_mean = float(df["atr"].rolling(50).mean().iloc[-1])

    # tendencia alcista fuerte
    if close > ema and adx >= 20 and atr >= atr_mean:
        return "BULL_TREND"

    # tendencia bajista fuerte
    if close < ema and adx >= 20 and atr >= atr_mean:
        return "BEAR_TREND"

    # alta volatilidad sin confirmación clara
    if atr > atr_mean * 1.3:
        return "HIGH_VOL"

    # resto: rango / mercado débil
    return "RANGE"