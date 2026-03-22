def calculate_trade_levels(df, signal, capital=1000, risk_per_trade=0.005):
    """
    Cálculo de niveles de trade — Tanda optimizada para gestión de riesgo.

    Cambios vs versión anterior:
    - SL ampliado de 1.5 ATR a 2.0 ATR
      (dar más espacio al trade para respirar sin ser sacado por ruido)
    - TP ajustado de 3.0 ATR a 2.5 ATR
      (target más alcanzable, menos trades que nunca llegan al TP)
    - R:R pasa de 2.0 a 1.25
      (compensado por mayor winrate esperado)

    Justificación:
    Con SL 1.5 ATR en velas de 30m, el ruido normal del mercado
    sacaba al bot antes de que el trade tuviera tiempo de funcionar.
    Avg Loss era ~7.5 con winrate ~30% y R:R 2:1 → expectancy negativa.

    Con SL 2.0 ATR:
    - menos stops por ruido
    - winrate debería subir
    - si WR >= 45% con R:R 1.25:1, hay edge positivo

    Para que un R:R de 1.25:1 sea rentable se necesita WR >= 45%.
    Para que un R:R de 1.5:1 sea rentable se necesita WR >= 40%.
    El anterior R:R 2.0:1 necesitaba WR >= 34% pero no lo lograba.
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