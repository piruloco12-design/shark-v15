from storage import get_closed_trade_stats


def _safe_float(value, default=0.0):
    try:
        return float(value)
    except Exception:
        return default


def _safe_int(value, default=0):
    try:
        return int(value)
    except Exception:
        return default


def _build_empty_summary():
    return {
        "total_trades": 0,
        "wins": 0,
        "losses": 0,
        "breakeven": 0,
        "win_rate": 0.0,
        "loss_rate": 0.0,
        "breakeven_rate": 0.0,
        "total_pnl": 0.0,
        "avg_pnl": 0.0,
        "best_trade": 0.0,
        "worst_trade": 0.0
    }


def _calculate_summary(trades):
    summary = _build_empty_summary()

    if not trades:
        return summary

    pnl_values = [_safe_float(t.get("pnl", 0.0)) for t in trades]

    wins = sum(1 for x in pnl_values if x > 0)
    losses = sum(1 for x in pnl_values if x < 0)
    breakeven = sum(1 for x in pnl_values if x == 0)

    total_trades = len(pnl_values)
    total_pnl = sum(pnl_values)
    avg_pnl = total_pnl / total_trades if total_trades > 0 else 0.0
    best_trade = max(pnl_values) if pnl_values else 0.0
    worst_trade = min(pnl_values) if pnl_values else 0.0

    summary["total_trades"] = total_trades
    summary["wins"] = wins
    summary["losses"] = losses
    summary["breakeven"] = breakeven
    summary["win_rate"] = round((wins / total_trades) * 100.0, 2) if total_trades > 0 else 0.0
    summary["loss_rate"] = round((losses / total_trades) * 100.0, 2) if total_trades > 0 else 0.0
    summary["breakeven_rate"] = round((breakeven / total_trades) * 100.0, 2) if total_trades > 0 else 0.0
    summary["total_pnl"] = round(total_pnl, 2)
    summary["avg_pnl"] = round(avg_pnl, 2)
    summary["best_trade"] = round(best_trade, 2)
    summary["worst_trade"] = round(worst_trade, 2)

    return summary


def _group_trades_by_key(trades, key_name):
    grouped = {}

    for trade in trades:
        key_value = str(trade.get(key_name, "UNKNOWN")).strip().upper()

        if key_value not in grouped:
            grouped[key_value] = []

        grouped[key_value].append(trade)

    return grouped


def analyze_performance(limit=500):
    trades = get_closed_trade_stats(limit=limit)

    result = {
        "global": _calculate_summary(trades),
        "by_ticker": {},
        "by_signal": {},
        "best_ticker": None,
        "worst_ticker": None
    }

    if not trades:
        return result

    grouped_by_ticker = _group_trades_by_key(trades, "ticker")
    grouped_by_signal = _group_trades_by_key(trades, "signal")

    for ticker, ticker_trades in grouped_by_ticker.items():
        result["by_ticker"][ticker] = _calculate_summary(ticker_trades)

    for signal, signal_trades in grouped_by_signal.items():
        result["by_signal"][signal] = _calculate_summary(signal_trades)

    sorted_tickers = sorted(
        result["by_ticker"].items(),
        key=lambda item: item[1]["total_pnl"],
        reverse=True
    )

    if sorted_tickers:
        result["best_ticker"] = {
            "ticker": sorted_tickers[0][0],
            "stats": sorted_tickers[0][1]
        }
        result["worst_ticker"] = {
            "ticker": sorted_tickers[-1][0],
            "stats": sorted_tickers[-1][1]
        }

    return result


def format_performance_report(limit=500):
    analysis = analyze_performance(limit=limit)

    global_stats = analysis["global"]

    if global_stats["total_trades"] == 0:
        return (
            "📊 AUDITORÍA SHARK V15\n\n"
            "No hay trades cerrados todavía.\n"
            "Todavía no se puede calcular performance real."
        )

    lines = []

    lines.append("📊 AUDITORÍA SHARK V15")
    lines.append("")
    lines.append("RESUMEN GLOBAL")
    lines.append(f"Trades cerrados: {global_stats['total_trades']}")
    lines.append(f"Ganados: {global_stats['wins']}")
    lines.append(f"Perdidos: {global_stats['losses']}")
    lines.append(f"Breakeven: {global_stats['breakeven']}")
    lines.append(f"Win Rate: {global_stats['win_rate']:.2f}%")
    lines.append(f"PnL total: {global_stats['total_pnl']:.2f} €")
    lines.append(f"PnL promedio: {global_stats['avg_pnl']:.2f} €")
    lines.append(f"Mejor trade: {global_stats['best_trade']:.2f} €")
    lines.append(f"Peor trade: {global_stats['worst_trade']:.2f} €")
    lines.append("")

    if analysis["best_ticker"]:
        best = analysis["best_ticker"]
        lines.append("MEJOR ACTIVO")
        lines.append(
            f"{best['ticker']} | PnL: {best['stats']['total_pnl']:.2f} € | "
            f"Win Rate: {best['stats']['win_rate']:.2f}% | "
            f"Trades: {best['stats']['total_trades']}"
        )
        lines.append("")

    if analysis["worst_ticker"]:
        worst = analysis["worst_ticker"]
        lines.append("PEOR ACTIVO")
        lines.append(
            f"{worst['ticker']} | PnL: {worst['stats']['total_pnl']:.2f} € | "
            f"Win Rate: {worst['stats']['win_rate']:.2f}% | "
            f"Trades: {worst['stats']['total_trades']}"
        )
        lines.append("")

    if analysis["by_signal"]:
        lines.append("POR DIRECCIÓN")
        for signal, stats in sorted(analysis["by_signal"].items()):
            lines.append(
                f"{signal} | Trades: {stats['total_trades']} | "
                f"Win Rate: {stats['win_rate']:.2f}% | "
                f"PnL: {stats['total_pnl']:.2f} €"
            )
        lines.append("")

    if analysis["by_ticker"]:
        lines.append("POR ACTIVO")
        for ticker, stats in sorted(
            analysis["by_ticker"].items(),
            key=lambda item: item[1]["total_pnl"],
            reverse=True
        ):
            lines.append(
                f"{ticker} | Trades: {stats['total_trades']} | "
                f"Win Rate: {stats['win_rate']:.2f}% | "
                f"PnL: {stats['total_pnl']:.2f} €"
            )

    return "\n".join(lines)