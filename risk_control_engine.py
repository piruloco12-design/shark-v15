from datetime import datetime, timedelta, date

from config import (
    CAPITAL,
    MAX_OPEN_TRADES,
    MAX_DAILY_LOSS_PCT,
    MAX_DRAWDOWN_PCT,
    COOLDOWN_HOURS_PER_ASSET,
    BLOCK_DUPLICATE_SIGNALS
)
from storage import (
    count_open_trades,
    get_latest_trade_timestamp_for_ticker,
    get_daily_closed_pnl,
    get_paper_capital,
    get_open_paper_trades
)


def _parse_dt(value):
    if not value:
        return None

    try:
        return datetime.fromisoformat(value)
    except Exception:
        return None


def check_max_open_trades():
    open_count = count_open_trades()

    if open_count >= MAX_OPEN_TRADES:
        return {
            "allow": False,
            "reason": f"Máximo de trades abiertos alcanzado ({MAX_OPEN_TRADES})"
        }

    return {
        "allow": True,
        "reason": "OK"
    }


def check_daily_loss_limit():
    daily_pnl = get_daily_closed_pnl()
    max_daily_loss_abs = CAPITAL * MAX_DAILY_LOSS_PCT

    if daily_pnl <= -max_daily_loss_abs:
        return {
            "allow": False,
            "reason": f"Límite de pérdida diaria alcanzado: {daily_pnl:.2f}"
        }

    return {
        "allow": True,
        "reason": "OK"
    }


def check_drawdown_limit():
    current_capital = get_paper_capital()
    max_loss_abs = CAPITAL * MAX_DRAWDOWN_PCT
    current_drawdown = CAPITAL - current_capital

    if current_drawdown >= max_loss_abs:
        return {
            "allow": False,
            "reason": f"Drawdown máximo alcanzado: {current_drawdown:.2f}"
        }

    return {
        "allow": True,
        "reason": "OK"
    }


def check_asset_cooldown(ticker):
    latest_ts = get_latest_trade_timestamp_for_ticker(ticker)

    if latest_ts is None:
        return {
            "allow": True,
            "reason": "OK"
        }

    latest_dt = _parse_dt(latest_ts)
    if latest_dt is None:
        return {
            "allow": True,
            "reason": "OK"
        }

    cooldown_until = latest_dt + timedelta(hours=COOLDOWN_HOURS_PER_ASSET)

    if datetime.now() < cooldown_until:
        return {
            "allow": False,
            "reason": f"Cooldown activo hasta {cooldown_until.isoformat(timespec='minutes')}"
        }

    return {
        "allow": True,
        "reason": "OK"
    }


def check_duplicate_trade(ticker, signal):
    if not BLOCK_DUPLICATE_SIGNALS:
        return {
            "allow": True,
            "reason": "OK"
        }

    open_trades = get_open_paper_trades()

    for trade in open_trades:
        if trade["ticker"] == ticker and trade["signal"] == signal:
            return {
                "allow": False,
                "reason": f"Trade duplicado abierto para {ticker} {signal}"
            }

    return {
        "allow": True,
        "reason": "OK"
    }


def evaluate_risk_controls(ticker, signal):
    checks = [
        check_max_open_trades(),
        check_daily_loss_limit(),
        check_drawdown_limit(),
        check_asset_cooldown(ticker),
        check_duplicate_trade(ticker, signal),
    ]

    for result in checks:
        if not result["allow"]:
            return result

    return {
        "allow": True,
        "reason": "Todos los controles OK"
    }