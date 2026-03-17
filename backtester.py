from config import CAPITAL, RISK_PER_TRADE
from signals import check_signal
from risk_management import calculate_trade_levels

def run_backtest(df, max_positions=5):
    capital = CAPITAL
    trading_cost_pct = 0.0006  # 0.06%

    open_positions = []
    trades = []
    equity_curve = []

    for i in range(200, len(df)):
        data = df.iloc[:i]
        last = data.iloc[-1]
        price = float(last["Close"])

        # 1. Revisar posiciones abiertas
        positions_to_close = []

        for pos in open_positions:
            signal = pos["signal"]
            entry_price = pos["entry"]
            stop_loss = pos["stop_loss"]
            take_profit = pos["take_profit"]
            position_size = pos["position_size"]

            if signal == "BUY":
                if price <= stop_loss or price >= take_profit:
                    cost = price * trading_cost_pct * position_size
                    pnl = ((price - entry_price) * position_size) - cost
                    capital += pnl
                    trades.append(pnl)
                    positions_to_close.append(pos)

            elif signal == "SELL":
                if price >= stop_loss or price <= take_profit:
                    cost = price * trading_cost_pct * position_size
                    pnl = ((entry_price - price) * position_size) - cost
                    capital += pnl
                    trades.append(pnl)
                    positions_to_close.append(pos)

        for pos in positions_to_close:
            open_positions.remove(pos)

        # 2. Buscar nueva entrada
        signal = check_signal(data)

        if signal in ["BUY", "SELL"] and len(open_positions) < max_positions:
            trade = calculate_trade_levels(data, signal, capital, RISK_PER_TRADE)

            if trade["position_size"] > 0:
                open_positions.append({
                    "signal": signal,
                    "entry": float(trade["entry"]),
                    "stop_loss": float(trade["stop_loss"]),
                    "take_profit": float(trade["take_profit"]),
                    "position_size": float(trade["position_size"])
                })

        # 3. Equity aproximada
        floating_pnl = 0

        for pos in open_positions:
            if pos["signal"] == "BUY":
                floating_pnl += (price - pos["entry"]) * pos["position_size"]
            elif pos["signal"] == "SELL":
                floating_pnl += (pos["entry"] - price) * pos["position_size"]

        equity_curve.append(capital + floating_pnl)

    total_trades = len(trades)
    wins = len([t for t in trades if t > 0])
    losses = len([t for t in trades if t <= 0])
    winrate = (wins / total_trades * 100) if total_trades > 0 else 0
    avg_trade = sum(trades) / total_trades if total_trades > 0 else 0

    gross_profit = sum([t for t in trades if t > 0])
    gross_loss = abs(sum([t for t in trades if t <= 0]))
    profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else 0

    peak = CAPITAL
    max_drawdown = 0

    for value in equity_curve:
        if value > peak:
            peak = value

        drawdown = peak - value

        if drawdown > max_drawdown:
            max_drawdown = drawdown

    return {
        "final_capital": capital,
        "trades": trades,
        "equity_curve": equity_curve,
        "total_trades": total_trades,
        "wins": wins,
        "losses": losses,
        "winrate": winrate,
        "avg_trade": avg_trade,
        "profit_factor": profit_factor,
        "max_drawdown": max_drawdown,
        "open_positions_left": len(open_positions)
    }