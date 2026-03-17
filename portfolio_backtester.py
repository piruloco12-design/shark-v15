from config import CAPITAL, RISK_PER_TRADE
from signals import check_signal
from risk_management import calculate_trade_levels
from asset_rotation import select_top_assets_by_rotation
from correlation_filter import passes_correlation_filter


def run_portfolio_backtest(
    data_dict,
    selected_assets,
    max_positions=3,
    use_rotation=False,
    rotation_lookback=50,
    rotation_top_n=3,
    use_correlation_filter=True,
    correlation_lookback=50,
    max_corr=0.80
):

    capital = CAPITAL
    open_positions = []
    closed_trades = []

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
            "selected_assets": [],
            "avg_open_positions": 0
        }

    common_index = None

    for asset in selected_assets:
        df_index = data_dict[asset].index

        if common_index is None:
            common_index = df_index
        else:
            common_index = common_index.intersection(df_index)

    common_index = common_index.sort_values()

    equity_curve = []
    open_positions_history = []

    for current_time in common_index[200:]:

        # =====================================================
        # 1. ROTACIÓN DINÁMICA
        # =====================================================
        if use_rotation:
            active_assets = select_top_assets_by_rotation(
                data_dict={k: v for k, v in data_dict.items() if k in selected_assets},
                current_time=current_time,
                top_n=rotation_top_n,
                lookback=rotation_lookback
            )
        else:
            active_assets = selected_assets

        positions_to_close = []

        # =====================================================
        # 2. GESTIONAR POSICIONES ABIERTAS
        # =====================================================
        for pos in open_positions:

            ticker = pos["ticker"]
            df = data_dict[ticker]

            if current_time not in df.index:
                continue

            price = float(df.loc[current_time]["Close"])

            entry = pos["entry"]
            sl = pos["sl"]
            tp = pos["tp"]
            size = pos["size"]
            signal = pos["signal"]

            if signal == "BUY":
                if price <= sl or price >= tp:
                    pnl = (price - entry) * size
                    capital += pnl
                    closed_trades.append(pnl)
                    positions_to_close.append(pos)

            elif signal == "SELL":
                if price >= sl or price <= tp:
                    pnl = (entry - price) * size
                    capital += pnl
                    closed_trades.append(pnl)
                    positions_to_close.append(pos)

        for pos in positions_to_close:
            open_positions.remove(pos)

        # =====================================================
        # 3. CERRAR POSICIONES QUE YA NO ESTÁN EN ROTACIÓN
        # =====================================================
        positions_to_close_rotation = []

        for pos in open_positions:
            if pos["ticker"] not in active_assets:
                ticker = pos["ticker"]
                df = data_dict[ticker]

                if current_time not in df.index:
                    continue

                price = float(df.loc[current_time]["Close"])
                entry = pos["entry"]
                size = pos["size"]
                signal = pos["signal"]

                if signal == "BUY":
                    pnl = (price - entry) * size
                else:
                    pnl = (entry - price) * size

                capital += pnl
                closed_trades.append(pnl)
                positions_to_close_rotation.append(pos)

        for pos in positions_to_close_rotation:
            open_positions.remove(pos)

        # =====================================================
        # 4. BUSCAR NUEVAS ENTRADAS
        # =====================================================
        if len(open_positions) < max_positions:

            tickers_abiertos = [p["ticker"] for p in open_positions]

            for ticker in active_assets:

                if len(open_positions) >= max_positions:
                    break

                if ticker in tickers_abiertos:
                    continue

                # filtro de correlación
                if use_correlation_filter:
                    ok_corr = passes_correlation_filter(
                        candidate_ticker=ticker,
                        open_positions=open_positions,
                        data_dict=data_dict,
                        current_time=current_time,
                        max_corr=max_corr,
                        lookback=correlation_lookback
                    )

                    if not ok_corr:
                        continue

                df = data_dict[ticker]
                data = df.loc[:current_time]

                if len(data) < 200:
                    continue

                signal = check_signal(data)

                if signal in ["BUY", "SELL"]:

                    trade = calculate_trade_levels(
                        data,
                        signal,
                        capital,
                        RISK_PER_TRADE
                    )

                    if trade["position_size"] > 0:
                        open_positions.append({
                            "ticker": ticker,
                            "signal": signal,
                            "entry": float(trade["entry"]),
                            "sl": float(trade["stop_loss"]),
                            "tp": float(trade["take_profit"]),
                            "size": float(trade["position_size"])
                        })

                        if len(open_positions) >= max_positions:
                            break

        # =====================================================
        # 5. EQUITY FLOTANTE
        # =====================================================
        floating_pnl = 0

        for pos in open_positions:

            ticker = pos["ticker"]
            df = data_dict[ticker]

            if current_time not in df.index:
                continue

            price = float(df.loc[current_time]["Close"])

            if pos["signal"] == "BUY":
                floating_pnl += (price - pos["entry"]) * pos["size"]
            elif pos["signal"] == "SELL":
                floating_pnl += (pos["entry"] - price) * pos["size"]

        equity_curve.append(capital + floating_pnl)
        open_positions_history.append(len(open_positions))

    trades = len(closed_trades)

    wins = len([x for x in closed_trades if x > 0])
    losses = len([x for x in closed_trades if x <= 0])

    winrate = (wins / trades * 100) if trades > 0 else 0
    avg_trade = sum(closed_trades) / trades if trades > 0 else 0

    gross_profit = sum([x for x in closed_trades if x > 0])
    gross_loss = abs(sum([x for x in closed_trades if x <= 0]))
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0

    peak = CAPITAL
    max_dd = 0

    for x in equity_curve:
        if x > peak:
            peak = x

        dd = peak - x

        if dd > max_dd:
            max_dd = dd

    final_capital = equity_curve[-1] if equity_curve else capital
    avg_open_positions = (
        sum(open_positions_history) / len(open_positions_history)
        if open_positions_history else 0
    )

    return {
        "final_capital": final_capital,
        "closed_trades": trades,
        "wins": wins,
        "losses": losses,
        "winrate": winrate,
        "avg_trade": avg_trade,
        "profit_factor": profit_factor,
        "max_drawdown": max_dd,
        "selected_assets": selected_assets,
        "avg_open_positions": avg_open_positions
    }