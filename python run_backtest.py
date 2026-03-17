from config import CAPITAL, RISK_PER_TRADE
from signals import check_signal
from risk_management import calculate_trade_levels


def run_portfolio_backtest(data_dict, selected_assets, max_positions=3):
    capital = CAPITAL
    trading_cost_pct = 0.0006  # 0.06% coste estimado total

    open_positions = []
    closed_trades = []
    equity_curve = []

    if not selected_assets:
        return {
            "final_capital": capital,
            "closed_trades": 0,
            "wins": 0,
            "losses": 0,
            "winrate": 0,
            "avg_trade": 0,
            "profit_factor": 0,
            "max_drawdown": 0,
            "equity_curve": [],
            "selected_assets": []
        }

    # índice común entre todos los activos seleccionados
    common_index = None
    for asset in selected_assets:
        asset_index = data_dict[asset].index
        if common_index is None:
            common_index = asset_index
        else:
            common_index = common_index.intersection(asset_index)

    common_index = common_index.sort_values()

    # necesitamos historial suficiente para EMA200 y demás
    if len(common_index) < 250:
        return {
            "final_capital": capital,
            "closed_trades": 0,
            "wins": 0,
            "losses": 0,
            "winrate": 0,
            "avg_trade": 0,
            "profit_factor": 0,
            "max_drawdown": 0,
            "equity_curve": [],
            "selected_assets": selected_assets
        }

    for current_time in common_index[200:]:
        # =====================================================
        # 1. Gestionar posiciones abiertas
        # =====================================================
        positions_to_close = []

        for pos in open_positions:
            ticker = pos["ticker"]
            df_asset = data_dict[ticker]

            if current_time not in df_asset.index:
                continue

            current_row = df_asset.loc[current_time]
            price = float(current_row["Close"])

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
                    closed_trades.append(pnl)
                    positions_to_close.append(pos)

            elif signal == "SELL":
                if price >= stop_loss or price <= take_profit:
                    cost = price * trading_cost_pct * position_size
                    pnl = ((entry_price - price) * position_size) - cost
                    capital += pnl
                    closed_trades.append(pnl)
                    positions_to_close.append(pos)

        for pos in positions_to_close:
            open_positions.remove(pos)

        # =====================================================
        # 2. Buscar nuevas entradas
        # =====================================================
        already_open_tickers = [p["ticker"] for p in open_positions]

        for ticker in selected_assets:
            if len(open_positions) >= max_positions:
                break

            if ticker in already_open_tickers:
                continue

            df_asset = data_dict[ticker]
            data_until_now = df_asset.loc[:current_time]

            if len(data_until_now) < 200:
                continue

            signal = check_signal(data_until_now)

            if signal in ["BUY", "SELL"]:
                trade = calculate_trade_levels(
                    data_until_now,
                    signal,
                    capital=capital,
                    risk_per_trade=RISK_PER_TRADE
                )

                if trade["position_size"] > 0:
                    open_positions.append({
                        "ticker": ticker,
                        "signal": signal,
                        "entry": float(trade["entry"]),
                        "stop_loss": float(trade["stop_loss"]),
                        "take_profit": float(trade["take_profit"]),
                        "position_size": float(trade["position_size"])
                    })

        # =====================================================
        # 3. Equity flotante
        # =====================================================
        floating_pnl = 0

        for pos in open_positions:
            ticker = pos["ticker"]
            df_asset = data_dict[ticker]

            if current_time not in df_asset.index:
                continue

            price = float(df_asset.loc[current_time]["Close"])

            if pos["signal"] == "BUY":
                floating_pnl += (price - pos["entry"]) * pos["position_size"]
            elif pos["signal"] == "SELL":
                floating_pnl += (pos["entry"] - price) * pos["position_size"]

        equity_curve.append(capital + floating_pnl)

    # =========================================================
    # Métricas finales
    # =========================================================
    total_trades = len(closed_trades)
    wins = len([t for t in closed_trades if t > 0])
    losses = len([t for t in closed_trades if t <= 0])
    winrate = (wins / total_trades * 100) if total_trades > 0 else 0
    avg_trade = sum(closed_trades) / total_trades if total_trades > 0 else 0

    gross_profit = sum([t for t in closed_trades if t > 0])
    gross_loss = abs(sum([t for t in closed_trades if t <= 0]))
    profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else 0

    peak = CAPITAL
    max_drawdown = 0

    for value in equity_curve:
        if value > peak:
            peak = value

        drawdown = peak - value

        if drawdown > max_drawdown:
            max_drawdown = drawdown

    final_capital = equity_curve[-1] if equity_curve else capital

    return {
        "final_capital": final_capital,
        "closed_trades": total_trades,
        "wins": wins,
        "losses": losses,
        "winrate": winrate,
        "avg_trade": avg_trade,
        "profit_factor": profit_factor,
        "max_drawdown": max_drawdown,
        "equity_curve": equity_curve,
        "selected_assets": selected_assets
    }