def calculate_trade_levels(df, signal, capital=1000, risk_per_trade=0.005):
    """
    Gestión de riesgo — SL 2.0 ATR / TP 2.5 ATR.
    Este fue el cambio más impactante de toda la optimización.
    WR subió de 30% a 47% al dar más espacio al trade para respirar.
    """

    last = df.iloc[-1]
    price = float(last["Close"])
    atr = float(last["atr"])

    if signal == "BUY":
        stop_loss = price - (2.0 * atr)
        take_profit = price + (2.5 * atr)
    elif signal == "SELL":
        stop_loss = price + (2.0 * atr)
        take_profit = price - (2.5 * atr)
    else:
        return {
            "entry": price,
            "stop_loss": None,
            "take_profit": None,
            "position_size": 0,
            "risk_amount": 0,
            "risk_per_unit": 0,
            "rr_ratio": 0,
        }

    risk_amount = capital * risk_per_trade
    risk_per_unit = abs(price - stop_loss)

    position_size = 0 if risk_per_unit == 0 else risk_amount / risk_per_unit

    reward_per_unit = abs(take_profit - price)
    rr_ratio = reward_per_unit / risk_per_unit if risk_per_unit > 0 else 0

    return {
        "entry": price,
        "stop_loss": stop_loss,
        "take_profit": take_profit,
        "position_size": position_size,
        "risk_amount": risk_amount,
        "risk_per_unit": risk_per_unit,
        "rr_ratio": rr_ratio,
    }