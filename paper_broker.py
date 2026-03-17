from datetime import datetime
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
        return float(value)
    except Exception:
        return default


def has_open_trade_for_ticker(ticker):
    open_trades = get_open_paper_trades()

    for trade in open_trades:
        if trade["ticker"] == ticker:
            return True

    return False


def _is_valid_trade_setup(trade_setup):
    if not isinstance(trade_setup, dict):
        return False

    required_keys = ["entry", "stop_loss", "take_profit", "position_size"]

    for key in required_keys:
        if key not in trade_setup:
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

    return True


def open_trade(ticker, signal, regime, trade_setup):
    capital = _safe_float(get_paper_capital())

    if signal not in ["BUY", "SELL"]:
        print(f"PAPER BROKER | Trade no abierto en {ticker}: señal inválida ({signal})")
        return capital

    if has_open_trade_for_ticker(ticker):
        print(f"PAPER BROKER | Trade ya abierto en {ticker}, no se abre duplicado")
        return capital

    if not _is_valid_trade_setup(trade_setup):
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

    msg = format_open_trade_message(ticker, signal, trade_setup, capital)
    send_telegram_message(msg)

    return capital


def check_and_close_trades(latest_prices):
    open_trades = get_open_paper_trades()
    capital = _safe_float(get_paper_capital())

    if not isinstance(latest_prices, dict):
        print("PAPER BROKER | latest_prices inválido")
        return

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

            should_close = False
            pnl = 0.0
            close_reason = None

            if signal == "BUY":
                if price <= stop_loss:
                    pnl = (price - entry) * size
                    should_close = True
                    close_reason = "STOP_LOSS"
                elif price >= take_profit:
                    pnl = (price - entry) * size
                    should_close = True
                    close_reason = "TAKE_PROFIT"

            elif signal == "SELL":
                if price >= stop_loss:
                    pnl = (entry - price) * size
                    should_close = True
                    close_reason = "STOP_LOSS"
                elif price <= take_profit:
                    pnl = (entry - price) * size
                    should_close = True
                    close_reason = "TAKE_PROFIT"

            else:
                print(f"PAPER BROKER | Señal inválida en trade abierto de {ticker}: {signal}")
                continue

            if should_close:
                capital += pnl

                close_paper_trade(
                    trade_id=trade["id"],
                    timestamp_close=datetime.now().isoformat(),
                    exit_price=price,
                    pnl=pnl
                )

                print(
                    f"PAPER BROKER | Trade cerrado | "
                    f"{ticker} | {signal} | "
                    f"Motivo: {close_reason} | "
                    f"Exit: {price:.4f} | "
                    f"PnL: {pnl:.2f} | "
                    f"Capital: {capital:.2f}"
                )

                msg = format_close_trade_message(
                    ticker=ticker,
                    signal=signal,
                    exit_price=price,
                    pnl=pnl,
                    capital=capital
                )
                send_telegram_message(msg)

        except Exception as e:
            print(f"PAPER BROKER | Error cerrando trade de {trade.get('ticker', 'UNKNOWN')}: {e}")

    update_paper_capital(capital)


def get_open_trade_count():
    open_trades = get_open_paper_trades()
    return len(open_trades)