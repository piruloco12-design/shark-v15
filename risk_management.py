import math

from config import SL_ATR_MULT, TP_ATR_MULT


def _es_numero_util(*valores):
    """
    True solo si todos los valores son números finitos.

    Esto existe por un fallo real: si el ATR venía NaN (pasa con
    pocas velas o con un hueco en los datos), el stop y el target
    salían NaN. Y NaN rompe las validaciones de forma silenciosa,
    porque en Python:

        float('nan') <= 0   -->  False

    Es decir, un stop NaN pasaba el chequeo "stop_loss <= 0" de
    paper_broker, pasaba el chequeo "position_size <= 0" de
    live_engine, y acababa guardado en la base de datos como un
    trade con niveles NaN que nunca podía cerrarse.
    """
    for v in valores:
        try:
            if not math.isfinite(float(v)):
                return False
        except (TypeError, ValueError):
            return False
    return True


def _setup_vacio(price):
    return {
        "entry": price,
        "stop_loss": None,
        "take_profit": None,
        "position_size": 0,
        "risk_amount": 0,
        "risk_per_unit": 0,
        "rr_ratio": 0,
    }


def calculate_trade_levels(
    df,
    signal,
    capital=1000,
    risk_per_trade=0.005,
    sl_mult=None,
    tp_mult=None,
):
    """
    Gestión de riesgo — SL 2.0 ATR / TP 2.5 ATR por defecto.
    Este fue el cambio más impactante de toda la optimización.
    WR subió de 30% a 47% al dar más espacio al trade para respirar.

    sl_mult y tp_mult existen para poder barrer los múltiplos en el
    análisis de robustez. Si no se pasan, se usan los de config, que
    son los mismos valores de siempre: el comportamiento por defecto
    no cambia.
    """

    sl_mult = SL_ATR_MULT if sl_mult is None else float(sl_mult)
    tp_mult = TP_ATR_MULT if tp_mult is None else float(tp_mult)

    if df is None or len(df) == 0:
        return _setup_vacio(0.0)

    last = df.iloc[-1]

    try:
        price = float(last["Close"])
        atr = float(last["atr"])
    except (KeyError, TypeError, ValueError):
        return _setup_vacio(0.0)

    # Sin precio y ATR finitos no hay trade posible.
    if not _es_numero_util(price, atr) or price <= 0 or atr <= 0:
        return _setup_vacio(price if _es_numero_util(price) else 0.0)

    if signal == "BUY":
        stop_loss = price - (sl_mult * atr)
        take_profit = price + (tp_mult * atr)
    elif signal == "SELL":
        stop_loss = price + (sl_mult * atr)
        take_profit = price - (tp_mult * atr)
    else:
        return _setup_vacio(price)

    # Un ATR enorme sobre un precio bajo puede dejar el stop (en
    # SELL: el target) por debajo de cero. No es operable.
    if stop_loss <= 0 or take_profit <= 0:
        return _setup_vacio(price)

    risk_amount = capital * risk_per_trade
    risk_per_unit = abs(price - stop_loss)

    if risk_per_unit <= 0:
        return _setup_vacio(price)

    position_size = risk_amount / risk_per_unit

    reward_per_unit = abs(take_profit - price)
    rr_ratio = reward_per_unit / risk_per_unit

    # Última red: si algo salió no finito, devolvemos setup vacío
    # en lugar de un trade corrupto.
    if not _es_numero_util(stop_loss, take_profit, position_size, rr_ratio):
        return _setup_vacio(price)

    return {
        "entry": price,
        "stop_loss": stop_loss,
        "take_profit": take_profit,
        "position_size": position_size,
        "risk_amount": risk_amount,
        "risk_per_unit": risk_per_unit,
        "rr_ratio": rr_ratio,
    }
