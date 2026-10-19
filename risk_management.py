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
    efectivo_disponible=None,
    coste_rel=0.0,
):
    """
    Gestión de riesgo — SL 2.0 ATR / TP 2.5 ATR por defecto.
    Este fue el cambio más impactante de toda la optimización.
    WR subió de 30% a 47% al dar más espacio al trade para respirar.

    sl_mult y tp_mult existen para poder barrer los múltiplos en el
    análisis de robustez. Si no se pasan, se usan los de config, que
    son los mismos valores de siempre: el comportamiento por defecto
    no cambia.

    EFECTIVO DISPONIBLE — lo que la auditoría encontró

    El tamaño por ATR limita la pérdida TEÓRICA al stop, y eso funciona:
    con capital 1.000 y riesgo 0,5%, arriesga 5,00. Lo que no hacía era
    mirar si el nominal cabía en la cuenta. Con precio 100 y ATR 0,10,
    el stop queda a 0,20 del precio, así que el tamaño sale 25 unidades:
    nominal 2.500, dos veces y media el capital. Un límite de número de
    posiciones no lo impide, porque no mira el dinero.

    `efectivo_disponible` es OPCIONAL a propósito. Sin él, el
    comportamiento es idéntico al de siempre, byte por byte: eso
    preserva B1, que la auditoría exige conservar como referencia
    reproducible. Pasándolo, el tamaño se recorta a lo que la cuenta
    puede pagar, y el setup lo deja dicho en `recorte_por_efectivo`.

    La variante que lo usa es otra estrategia, con su identificador:
    B1_cash_long_only_v1. No es un parámetro que se afine.
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

    # Recorte por efectivo. Solo si se declara: sin este argumento el
    # comportamiento es el de siempre y B1 queda intacto.
    recorte = None
    if efectivo_disponible is not None:
        try:
            disponible = float(efectivo_disponible)
        except (TypeError, ValueError):
            disponible = 0.0
        if not _es_numero_util(disponible) or disponible <= 0:
            return _setup_vacio(price)
        por_unidad = price * (1.0 + max(0.0, float(coste_rel)))
        maxima = disponible / por_unidad if por_unidad > 0 else 0.0
        if maxima < position_size:
            recorte = {
                "tamano_por_riesgo": position_size,
                "tamano_por_efectivo": maxima,
                "nominal_por_riesgo": position_size * price,
                "efectivo_disponible": disponible,
            }
            position_size = maxima
        if position_size <= 0:
            return _setup_vacio(price)

    reward_per_unit = abs(take_profit - price)
    rr_ratio = reward_per_unit / risk_per_unit

    # Última red: si algo salió no finito, devolvemos setup vacío
    # en lugar de un trade corrupto.
    if not _es_numero_util(stop_loss, take_profit, position_size, rr_ratio):
        return _setup_vacio(price)

    setup = {
        "entry": price,
        "stop_loss": stop_loss,
        "take_profit": take_profit,
        "position_size": position_size,
        "risk_amount": risk_amount,
        "risk_per_unit": risk_per_unit,
        "rr_ratio": rr_ratio,
        "nominal": position_size * price,
    }
    if recorte is not None:
        # Que el recorte quede DICHO en el setup, no escondido: quien lea
        # un tamaño pequeño tiene que poder ver que lo limitó el efectivo
        # y no la volatilidad.
        setup["recorte_por_efectivo"] = recorte
    return setup
