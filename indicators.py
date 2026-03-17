import pandas as pd
import ta


def add_indicators(df):

    close = df["Close"]
    high = df["High"]
    low = df["Low"]

    df["ema200"] = ta.trend.ema_indicator(close, window=200)

    df["rsi"] = ta.momentum.rsi(close, window=14)

    macd = ta.trend.MACD(close)
    df["macd"] = macd.macd()
    df["macd_signal"] = macd.macd_signal()

    df["atr"] = ta.volatility.average_true_range(
        high,
        low,
        close,
        window=14
    )

    df["adx"] = ta.trend.adx(
        high,
        low,
        close,
        window=14
    )

    return df