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


def open_trade(ticker, signal, regime, trade_setup):
    capital = get_paper_capital()

    create_paper_trade(
        timestamp_open=datetime.now().isoformat(),
        ticker=ticker,
        signal=signal,
        regime=regime,
        entry_price=trade_setup["entry"],
        stop_loss=trade_setup["stop_loss"],
        take_profit=trade_setup["take_profit"],
        position_size=trade_setup["position_size"]
    )

    msg = format_open_trade_message(ticker, signal, trade_setup, capital)
    send_telegram_message(msg)

    return capital


def check_and_close_trades(latest_prices):
    open_trades = get_open_paper_trades()
    capital = get_paper_capital()

    for trade in open_trades:
        ticker = trade["ticker"]

        if ticker not in latest_prices:
            continue

        price = float(latest_prices[ticker])
        signal = trade["signal"]
        entry = trade["entry_price"]
        stop_loss = trade["stop_loss"]
        take_profit = trade["take_profit"]
        size = trade["position_size"]

        should_close = False
        pnl = 0.0

        if signal == "BUY":
            if price <= stop_loss or price >= take_profit:
                pnl = (price - entry) * size
                should_close = True

        elif signal == "SELL":
            if price >= stop_loss or price <= take_profit:
                pnl = (entry - price) * size
                should_close = True

        if should_close:
            capital += pnl

            close_paper_trade(
                trade_id=trade["id"],
                timestamp_close=datetime.now().isoformat(),
                exit_price=price,
                pnl=pnl
            )

            msg = format_close_trade_message(
                ticker=ticker,
                signal=signal,
                exit_price=price,
                pnl=pnl,
                capital=capital
            )
            send_telegram_message(msg)

    update_paper_capital(capital)


def has_open_trade_for_ticker(ticker):
    open_trades = get_open_paper_trades()

    for trade in open_trades:
        if trade["ticker"] == ticker:
            return True

    return False