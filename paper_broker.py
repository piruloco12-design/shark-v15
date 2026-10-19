import math
from datetime import datetime

from config import MENSAJE_BROKER_AL_ABRIR

# Deslizamiento adverso que se aplica SOLO cuando un hueco atraviesa el
# stop. Es un ESCENARIO declarado, no una medición: no hay fills reales
# todavía, ni bid/ask, solo OHLC. Cero significa "ejecuta justo en la
# apertura del hueco", que ya es mucho mejor que el nivel del stop pero
# sigue siendo optimista: una orden stop de mercado en un hueco suele
# ejecutarse algo peor. Al declararlo aquí, cambiar el escenario es
# visible y cuesta un commit.
DESLIZAMIENTO_EN_HUECO = 0.0


from storage import (
    get_paper_capital,
    update_paper_capital,
    get_open_paper_trades,
    create_paper_trade,
    close_paper_trade
)
from telegram_alerts import (
    send_telegram_message,
    format_open_trade_message,
    format_close_trade_message
)


def _safe_float(value, default=0.0):
    try:
        value = float(value)
    except (TypeError, ValueError):
        return default
    # NaN e infinito se tratan como ausencia de dato. Sin esto,
    # un NaN atraviesa todas las validaciones de abajo porque
    # float('nan') <= 0 es False.
    if not math.isfinite(value):
        return default
    return value


def _es_finito(*valores):
    for v in valores:
        try:
            if not math.isfinite(float(v)):
                return False
        except (TypeError, ValueError):
            return False
    return True


def has_open_trade_for_ticker(ticker):
    open_trades = get_open_paper_trades()

    for trade in open_trades:
        if trade["ticker"] == ticker:
            return True

    return False


def _is_valid_trade_setup(trade_setup, signal=None):
    if not isinstance(trade_setup, dict):
        return False

    required_keys = ["entry", "stop_loss", "take_profit", "position_size"]

    for key in required_keys:
        if key not in trade_setup:
            return False

    # Rechazo explícito de NaN/infinito ANTES de comparar.
    if not _es_finito(
        trade_setup.get("entry"),
        trade_setup.get("stop_loss"),
        trade_setup.get("take_profit"),
        trade_setup.get("position_size"),
    ):
        return False

    entry = _safe_float(trade_setup.get("entry"))
    stop_loss = _safe_float(trade_setup.get("stop_loss"))
    take_profit = _safe_float(trade_setup.get("take_profit"))
    position_size = _safe_float(trade_setup.get("position_size"))

    if entry <= 0:
        return False

    if stop_loss <= 0:
        return False

    if take_profit <= 0:
        return False

    if position_size <= 0:
        return False

    # Coherencia direccional: un BUY con el stop por encima de la
    # entrada no es un trade, es un bug. Antes se guardaba igual.
    if signal == "BUY" and not (stop_loss < entry < take_profit):
        return False

    if signal == "SELL" and not (take_profit < entry < stop_loss):
        return False

    return True


def open_trade(ticker, signal, regime, trade_setup):
    capital = _safe_float(get_paper_capital())

    if signal not in ["BUY", "SELL"]:
        print(f"PAPER BROKER | Trade no abierto en {ticker}: señal inválida ({signal})")
        return capital

    if has_open_trade_for_ticker(ticker):
        print(f"PAPER BROKER | Trade ya abierto en {ticker}, no se abre duplicado")
        return capital

    if not _is_valid_trade_setup(trade_setup, signal):
        print(f"PAPER BROKER | Trade setup inválido en {ticker}, no se abre trade")
        return capital

    create_paper_trade(
        timestamp_open=datetime.now().isoformat(),
        ticker=ticker,
        signal=signal,
        regime=regime,
        entry_price=_safe_float(trade_setup["entry"]),
        stop_loss=_safe_float(trade_setup["stop_loss"]),
        take_profit=_safe_float(trade_setup["take_profit"]),
        position_size=_safe_float(trade_setup["position_size"])
    )

    print(
        f"PAPER BROKER | Trade abierto | "
        f"{ticker} | {signal} | "
        f"Entry: {_safe_float(trade_setup['entry']):.4f} | "
        f"SL: {_safe_float(trade_setup['stop_loss']):.4f} | "
        f"TP: {_safe_float(trade_setup['take_profit']):.4f} | "
        f"Size: {_safe_float(trade_setup['position_size']):.4f}"
    )

    # El aviso corto del broker solo se manda si se pide: la
    # ficha movil de live_engine ya lleva todo esto y mas, y
    # mandar los dos duplicaba cada apertura en Telegram.
    if MENSAJE_BROKER_AL_ABRIR:
        msg = format_open_trade_message(ticker, signal, trade_setup, capital)
        send_telegram_message(msg)

    return capital


def _decidir_cierre(signal, stop_loss, take_profit, price, high, low,
                    open_=None, deslizamiento=0.0):
    """
    Decide si el trade debe cerrarse y a qué precio exacto.

    Usa el máximo y el mínimo de la vela, no solo el cierre. Esto
    importa: el bot gira cada 5 minutos sobre velas de 30m, así
    que mirando solo el Close se pierden los toques de stop o
    target que ocurrieron DENTRO de la vela y volvieron atrás.

    HUECOS. Antes esta función devolvía siempre el nivel exacto del
    stop, también cuando la vela entera estaba al otro lado. Un largo
    con stop en 99 cuya vela siguiente abría en 95 con máximo 95
    salía a 99: un precio que nadie negoció. Con 5 unidades eso son
    -5,00 declarados contra -25,00 reales, un factor de cinco en la
    pérdida. Ahora, si la apertura ya está más allá del stop, el fill
    parte de esa apertura, que es lo que haría una orden stop de
    mercado, y se le resta el deslizamiento adverso.

    Sin la apertura no se puede distinguir "la vela bajó y tocó el
    stop" de "la vela abrió ya por debajo". En ese caso se usa el
    extremo de la vela, que es el peor precio comprobado y nunca
    mejor que el stop: más pesimista que inventar el nivel.

    Cuando la vela toca stop y target a la vez, se asume stop
    primero. Es el supuesto pesimista y es el mismo que usa el
    backtester, para que paper y backtest sean comparables.

    Devuelve (cerrar, precio_salida, motivo).
    """
    # Sin rango de vela, se degrada al comportamiento anterior:
    # comparar contra el cierre.
    if not _es_finito(high, low):
        high = price
        low = price

    desl = abs(_safe_float(deslizamiento, 0.0))
    apertura = _safe_float(open_, float("nan")) if open_ is not None else float("nan")
    hay_apertura = _es_finito(apertura)

    if signal == "BUY":
        if low <= stop_loss:
            # Peor precio realmente observado en la vela, nunca mejor
            # que el stop.
            if hay_apertura and apertura < stop_loss:
                salida = apertura - desl        # hueco por debajo
            else:
                salida = min(stop_loss, high)   # sin apertura: el peor visto
            return True, max(salida, low - desl), "STOP_LOSS"
        if high >= take_profit:
            # Un hueco a favor tampoco se ejecuta mejor que la apertura.
            if hay_apertura and apertura > take_profit:
                salida = apertura
            else:
                salida = take_profit
            return True, min(salida, high), "TAKE_PROFIT"
        return False, None, None

    if signal == "SELL":
        if high >= stop_loss:
            if hay_apertura and apertura > stop_loss:
                salida = apertura + desl        # hueco por encima
            else:
                salida = max(stop_loss, low)
            return True, min(salida, high + desl), "STOP_LOSS"
        if low <= take_profit:
            if hay_apertura and apertura < take_profit:
                salida = apertura
            else:
                salida = take_profit
            return True, max(salida, low), "TAKE_PROFIT"
        return False, None, None

    return False, None, None


def check_and_close_trades(latest_prices, rangos_barra=None):
    """
    Revisa los trades abiertos y cierra los que tocaron SL o TP.

    latest_prices: {ticker: precio_cierre_actual}
    rangos_barra:  {ticker: {"open": o, "high": h, "low": l}}  (opcional)

    rangos_barra es opcional a propósito, para no romper a quien
    llame con un solo argumento. Pero sin él la detección es peor:
    solo ve el cierre.
    """
    if not isinstance(latest_prices, dict):
        print("PAPER BROKER | latest_prices inválido")
        return

    if not isinstance(rangos_barra, dict):
        rangos_barra = {}

    open_trades = get_open_paper_trades()
    capital = _safe_float(get_paper_capital())
    capital_inicial = capital
    cerrados = 0

    for trade in open_trades:
        try:
            ticker = trade["ticker"]

            if ticker not in latest_prices:
                print(f"PAPER BROKER | Sin precio actual para {ticker}, trade sigue abierto")
                continue

            price = _safe_float(latest_prices[ticker])
            signal = trade["signal"]
            entry = _safe_float(trade["entry_price"])
            stop_loss = _safe_float(trade["stop_loss"])
            take_profit = _safe_float(trade["take_profit"])
            size = _safe_float(trade["position_size"])

            if price <= 0 or entry <= 0 or stop_loss <= 0 or take_profit <= 0 or size <= 0:
                print(f"PAPER BROKER | Datos inválidos en trade abierto de {ticker}, se omite revisión")
                continue

            if signal not in ["BUY", "SELL"]:
                print(f"PAPER BROKER | Señal inválida en trade abierto de {ticker}: {signal}")
                continue

            rango = rangos_barra.get(ticker) or {}
            high = _safe_float(rango.get("high"), default=float("nan"))
            low = _safe_float(rango.get("low"), default=float("nan"))
            # La apertura es lo que distingue "la vela bajó y tocó el
            # stop" de "la vela abrió ya por debajo del stop". Sin
            # ella, un hueco se ejecutaba al nivel del stop, que es un
            # precio que nadie negoció.
            apertura = _safe_float(rango.get("open"), default=float("nan"))

            should_close, exit_price, close_reason = _decidir_cierre(
                signal=signal,
                stop_loss=stop_loss,
                take_profit=take_profit,
                price=price,
                high=high,
                low=low,
                open_=apertura if _es_finito(apertura) else None,
                deslizamiento=DESLIZAMIENTO_EN_HUECO,
            )

            if not should_close:
                continue

            if signal == "BUY":
                pnl = (exit_price - entry) * size
            else:
                pnl = (entry - exit_price) * size

            if not _es_finito(pnl):
                print(f"PAPER BROKER | PnL no finito en {ticker}, se omite cierre")
                continue

            capital += pnl
            cerrados += 1

            close_paper_trade(
                trade_id=trade["id"],
                timestamp_close=datetime.now().isoformat(),
                exit_price=exit_price,
                pnl=pnl
            )

            print(
                f"PAPER BROKER | Trade cerrado | "
                f"{ticker} | {signal} | "
                f"Motivo: {close_reason} | "
                f"Exit: {exit_price:.4f} | "
                f"PnL: {pnl:.2f} | "
                f"Capital: {capital:.2f}"
            )

            msg = format_close_trade_message(
                ticker=ticker,
                signal=signal,
                exit_price=exit_price,
                pnl=pnl,
                capital=capital
            )
            send_telegram_message(msg)

        except Exception as e:
            print(f"PAPER BROKER | Error cerrando trade de {trade.get('ticker', 'UNKNOWN')}: {e}")

    # Solo escribimos capital si de verdad cambió. Antes se
    # reescribía el mismo valor en cada ciclo, cada 5 minutos.
    if cerrados > 0 and capital != capital_inicial:
        update_paper_capital(capital)

    return cerrados


def get_open_trade_count():
    open_trades = get_open_paper_trades()
    return len(open_trades)
