def calculate_trade_levels(df, signal, capital=1000, risk_per_trade=0.005):
    last = df.iloc[-1]

    price = float(last["Close"])
    atr = float(last["atr"])

    if signal == "BUY":
        stop_loss = price - (1.5 * atr)
        take_profit = price + (3.0 * atr)
    elif signal == "SELL":
        stop_loss = price + (1.5 * atr)
        take_profit = price - (3.0 * atr)
    else:
        return {
            "entry": price,
            "stop_loss": None,
            "take_profit": None,
            "position_size": 0,
            "risk_amount": 0,
            "risk_per_unit": 0,
            "rr_ratio": 0
        }

    risk_amount = capital * risk_per_trade
    risk_per_unit = abs(price - stop_loss)

    if risk_per_unit == 0:
        position_size = 0
    else:
        position_size = risk_amount / risk_per_unit

    reward_per_unit = abs(take_profit - price)
    rr_ratio = reward_per_unit / risk_per_unit if risk_per_unit > 0 else 0

    return {
        "entry": price,
        "stop_loss": stop_loss,
        "take_profit": take_profit,
        "position_size": position_size,
        "risk_amount": risk_amount,
        "risk_per_unit": risk_per_unit,
        "rr_ratio": rr_ratio
    }