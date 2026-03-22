"""
SHARK V15 SNIPER — Backtester Fiel

Usa la misma lógica que live_engine.py, pero simulando histórico barra por barra.
"""

import sys
from pathlib import Path

import pandas as pd

CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import (
    ASSETS,
    TIMEFRAME,
    CAPITAL,
    RISK_PER_TRADE,
    SNIPER_MODE,
    SNIPER_MIN_ADX,
    SNIPER_MIN_AI_SCORE,
    SNIPER_MIN_FINAL_SCORE,
)
from data_feed import get_data
from indicators import add_indicators
from market_regime import detect_market_regime
from signals import check_signal
from opportunity_scanner import scan_smart_opportunity
from risk_management import calculate_trade_levels
from session_volatility_intelligence import (
    evaluate_session_filter,
    evaluate_volatility_filter,
)
from final_decision_engine import evaluate_final_decision


# =========================================================
# CONFIGURACIÓN DEL BACKTEST
# =========================================================
BACKTEST_PERIOD = "60d"          # yfinance intradía 30m funciona bien con 60d
BACKTEST_TIMEFRAME = TIMEFRAME

MIN_WARMUP_BARS = 200

# 0.08% TOTAL ida+vuelta
TRADING_COST_PCT = 0.0008
ENTRY_COST_PCT = TRADING_COST_PCT / 2
EXIT_COST_PCT = TRADING_COST_PCT / 2

TRAIN_RATIO = 0.70


# =========================================================
# SIMULACIÓN DE CAPAS SIN HISTORIAL
# =========================================================
def _simulate_ai_result():
    return {
        "score": 55.0,
        "decision": "NEUTRAL",
        "reason": "Backtest: sin historial simulado",
        "exact_count": 0,
        "ticker_count": 0,
        "signal_count": 0,
    }


def _simulate_context_result():
    return {
        "ticker_signal_score": 55.0,
        "ticker_regime_score": 55.0,
        "signal_score": 55.0,
        "final_score": 55.0,
        "decision": "NEUTRAL",
        "reason": "Backtest: sin historial simulado",
    }


def _simulate_risk_result():
    return {
        "allow": True,
        "reason": "Backtest: riesgo controlado por simulador",
    }


# =========================================================
# MOTOR DE BACKTEST PRINCIPAL
# =========================================================
def run_v15_backtest_single_asset(
    ticker,
    df,
    capital_start,
    label="FULL",
    start_eval_index=None,
):
    """
    Corre el backtest V15 completo para un solo activo.

    start_eval_index:
    - permite usar warmup previo
    - pero contar señales/trades solo desde cierto punto
    """

    if start_eval_index is None:
        start_eval_index = MIN_WARMUP_BARS

    capital = capital_start
    open_position = None
    closed_trades = []
    equity_curve = []

    total_signals = 0
    total_allowed = 0
    total_blocked = 0
    block_reasons = {}

    for i in range(MIN_WARMUP_BARS, len(df)):
        data = df.iloc[: i + 1].copy()
        last = data.iloc[-1]
        price = float(last["Close"])

        # -------------------------------------------------
        # 1) CERRAR posición abierta si toca SL o TP
        # -------------------------------------------------
        if open_position is not None:
            entry = open_position["entry"]
            sl = open_position["stop_loss"]
            tp = open_position["take_profit"]
            size = open_position["position_size"]
            sig = open_position["signal"]

            bar_high = float(last["High"])
            bar_low = float(last["Low"])

            should_close = False
            exit_price = 0.0
            pnl = 0.0
            close_reason = ""

            if sig == "BUY":
                hit_sl = bar_low <= sl
                hit_tp = bar_high >= tp

                if hit_sl and hit_tp:
                    exit_price = sl
                    pnl = (sl - entry) * size
                    close_reason = "STOP_LOSS_SAME_BAR"
                    should_close = True
                elif hit_sl:
                    exit_price = sl
                    pnl = (sl - entry) * size
                    close_reason = "STOP_LOSS"
                    should_close = True
                elif hit_tp:
                    exit_price = tp
                    pnl = (tp - entry) * size
                    close_reason = "TAKE_PROFIT"
                    should_close = True

            elif sig == "SELL":
                hit_sl = bar_high >= sl
                hit_tp = bar_low <= tp

                if hit_sl and hit_tp:
                    exit_price = sl
                    pnl = (entry - sl) * size
                    close_reason = "STOP_LOSS_SAME_BAR"
                    should_close = True
                elif hit_sl:
                    exit_price = sl
                    pnl = (entry - sl) * size
                    close_reason = "STOP_LOSS"
                    should_close = True
                elif hit_tp:
                    exit_price = tp
                    pnl = (entry - tp) * size
                    close_reason = "TAKE_PROFIT"
                    should_close = True

            if should_close:
                exit_cost = exit_price * EXIT_COST_PCT * size
                pnl -= exit_cost
                capital += pnl

                if open_position["count_for_stats"]:
                    closed_trades.append({
                        "ticker": ticker,
                        "signal": sig,
                        "regime": open_position["regime"],
                        "entry": entry,
                        "exit": exit_price,
                        "pnl": pnl,
                        "size": size,
                        "bars_held": i - open_position["bar_index"],
                        "timestamp": str(data.index[-1]),
                        "close_reason": close_reason,
                    })

                open_position = None

        # -------------------------------------------------
        # 2) EVALUAR nueva señal
        # -------------------------------------------------
        if open_position is None:
            regime = detect_market_regime(data)

            base_signal = check_signal(data)
            signal = base_signal

            scanner_info = {"signal": "NO_SIGNAL", "reason": "No usado"}
            if base_signal == "NO_SIGNAL":
                scanner_info = scan_smart_opportunity(data)
                if scanner_info["signal"] in ["BUY", "SELL"]:
                    signal = scanner_info["signal"]

            if signal in ["BUY", "SELL"] and i >= start_eval_index:
                total_signals += 1

            if signal in ["BUY", "SELL"]:
                adx_value = float(last["adx"])

                ai_result = _simulate_ai_result()
                context_result = _simulate_context_result()
                session_result = evaluate_session_filter(data, regime)
                volatility_result = evaluate_volatility_filter(data, regime)
                risk_result = _simulate_risk_result()

                final_result = evaluate_final_decision(
                    ai_result=ai_result,
                    context_result=context_result,
                    session_result=session_result,
                    volatility_result=volatility_result,
                    risk_result=risk_result,
                    adx=adx_value,
                    regime=regime,
                )

                if i >= start_eval_index:
                    if final_result["decision"] == "ALLOW":
                        total_allowed += 1
                    else:
                        total_blocked += 1
                        reason = final_result.get("reason", "Unknown")
                        block_reasons[reason] = block_reasons.get(reason, 0) + 1

                if final_result["decision"] == "ALLOW":
                    trade_setup = calculate_trade_levels(
                        df=data,
                        signal=signal,
                        capital=capital,
                        risk_per_trade=RISK_PER_TRADE,
                    )

                    if trade_setup["position_size"] > 0:
                        entry_cost = price * ENTRY_COST_PCT * trade_setup["position_size"]
                        capital -= entry_cost

                        open_position = {
                            "signal": signal,
                            "regime": regime,
                            "entry": trade_setup["entry"],
                            "stop_loss": trade_setup["stop_loss"],
                            "take_profit": trade_setup["take_profit"],
                            "position_size": trade_setup["position_size"],
                            "bar_index": i,
                            "count_for_stats": i >= start_eval_index,
                        }

        # -------------------------------------------------
        # 3) EQUITY CURVE
        # -------------------------------------------------
        floating = 0.0
        if open_position is not None:
            sig = open_position["signal"]
            entry = open_position["entry"]
            size = open_position["position_size"]

            if sig == "BUY":
                floating = (price - entry) * size
            elif sig == "SELL":
                floating = (entry - price) * size

        equity_curve.append(capital + floating)

    # -------------------------------------------------
    # ESTADÍSTICAS
    # -------------------------------------------------
    pnl_values = [t["pnl"] for t in closed_trades]
    total_trades = len(pnl_values)

    wins = [p for p in pnl_values if p > 0]
    losses = [p for p in pnl_values if p <= 0]

    winrate = (len(wins) / total_trades * 100) if total_trades > 0 else 0.0
    avg_trade = sum(pnl_values) / total_trades if total_trades > 0 else 0.0

    gross_profit = sum(wins) if wins else 0.0
    gross_loss = abs(sum(losses)) if losses else 0.0
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0.0

    avg_win = sum(wins) / len(wins) if wins else 0.0
    avg_loss = abs(sum(losses) / len(losses)) if losses else 0.0
    win_pct = len(wins) / total_trades if total_trades > 0 else 0.0
    loss_pct = len(losses) / total_trades if total_trades > 0 else 0.0
    expectancy = (win_pct * avg_win) - (loss_pct * avg_loss)

    peak = capital_start
    max_dd = 0.0
    for eq in equity_curve:
        if eq > peak:
            peak = eq
        dd = peak - eq
        if dd > max_dd:
            max_dd = dd

    max_dd_pct = (max_dd / capital_start * 100) if capital_start > 0 else 0.0

    bars_held = [t["bars_held"] for t in closed_trades]
    avg_bars = sum(bars_held) / len(bars_held) if bars_held else 0.0

    regime_dist = {}
    for t in closed_trades:
        r = t["regime"]
        regime_dist[r] = regime_dist.get(r, 0) + 1

    signal_dist = {}
    for t in closed_trades:
        s = t["signal"]
        signal_dist[s] = signal_dist.get(s, 0) + 1

    return {
        "ticker": ticker,
        "label": label,
        "capital_start": capital_start,
        "capital_final": capital,
        "total_bars": max(len(df) - start_eval_index, 0),
        "total_signals": total_signals,
        "total_allowed": total_allowed,
        "total_blocked": total_blocked,
        "total_trades": total_trades,
        "wins": len(wins),
        "losses": len(losses),
        "winrate": round(winrate, 2),
        "avg_trade": round(avg_trade, 2),
        "avg_win": round(avg_win, 2),
        "avg_loss": round(avg_loss, 2),
        "expectancy": round(expectancy, 2),
        "gross_profit": round(gross_profit, 2),
        "gross_loss": round(gross_loss, 2),
        "profit_factor": round(profit_factor, 2),
        "max_drawdown": round(max_dd, 2),
        "max_drawdown_pct": round(max_dd_pct, 2),
        "avg_bars_held": round(avg_bars, 1),
        "equity_curve": equity_curve,
        "closed_trades": closed_trades,
        "block_reasons": block_reasons,
        "regime_distribution": regime_dist,
        "signal_distribution": signal_dist,
    }


# =========================================================
# WALK-FORWARD
# =========================================================
def run_walk_forward_v15(ticker, df, capital_start):
    split_idx = int(len(df) * TRAIN_RATIO)

    train_df = df.iloc[:split_idx].copy()
    train_result = run_v15_backtest_single_asset(
        ticker=ticker,
        df=train_df,
        capital_start=capital_start,
        label="TRAIN",
        start_eval_index=MIN_WARMUP_BARS,
    )

    test_start = max(split_idx - MIN_WARMUP_BARS, 0)
    test_df_slice = df.iloc[test_start:].copy()
    test_eval_index = split_idx - test_start

    test_result = run_v15_backtest_single_asset(
        ticker=ticker,
        df=test_df_slice,
        capital_start=capital_start,
        label="TEST",
        start_eval_index=test_eval_index,
    )

    return {
        "train": train_result,
        "test": test_result,
    }


# =========================================================
# REPORTE
# =========================================================
def print_result(r, indent=""):
    p = indent
    print(f"{p}{'=' * 60}")
    print(f"{p}{r['ticker']} | {r['label']} | Bars: {r['total_bars']}")
    print(f"{p}{'=' * 60}")
    print(
        f"{p}Capital:     {r['capital_start']:.2f} → {r['capital_final']:.2f}  "
        f"({r['capital_final'] - r['capital_start']:+.2f})"
    )
    print(
        f"{p}Señales:     {r['total_signals']} generadas | "
        f"{r['total_allowed']} ALLOW | {r['total_blocked']} BLOCK"
    )
    print(
        f"{p}Trades:      {r['total_trades']} cerrados | "
        f"{r['wins']} wins | {r['losses']} losses"
    )
    print(f"{p}Winrate:     {r['winrate']:.1f}%")
    print(f"{p}Avg Trade:   {r['avg_trade']:.2f}")
    print(f"{p}Avg Win:     {r['avg_win']:.2f}  |  Avg Loss: {r['avg_loss']:.2f}")
    print(f"{p}Expectancy:  {r['expectancy']:.2f} por trade")
    print(f"{p}PF:          {r['profit_factor']:.2f}")
    print(f"{p}Max DD:      {r['max_drawdown']:.2f} ({r['max_drawdown_pct']:.1f}%)")
    print(f"{p}Avg Bars:    {r['avg_bars_held']:.0f} velas")

    if r["regime_distribution"]:
        print(f"{p}Regímenes:   {r['regime_distribution']}")
    if r["signal_distribution"]:
        print(f"{p}Señales:     {r['signal_distribution']}")

    if r["block_reasons"]:
        print(f"{p}Bloqueos principales:")
        sorted_blocks = sorted(r["block_reasons"].items(), key=lambda x: -x[1])
        for reason, count in sorted_blocks[:5]:
            print(f"{p}  {count:>4}x  {reason[:80]}")

    print()


def print_consolidated(results, label):
    total_trades = sum(r["total_trades"] for r in results)
    total_wins = sum(r["wins"] for r in results)
    total_losses = sum(r["losses"] for r in results)
    total_pnl = sum(r["capital_final"] - r["capital_start"] for r in results)
    total_signals = sum(r["total_signals"] for r in results)
    total_allowed = sum(r["total_allowed"] for r in results)
    total_blocked = sum(r["total_blocked"] for r in results)

    all_pnls = []
    for r in results:
        all_pnls.extend([t["pnl"] for t in r["closed_trades"]])

    winrate = (total_wins / total_trades * 100) if total_trades > 0 else 0.0
    avg_trade = sum(all_pnls) / len(all_pnls) if all_pnls else 0.0

    wins_pnl = [p for p in all_pnls if p > 0]
    losses_pnl = [p for p in all_pnls if p <= 0]
    gp = sum(wins_pnl) if wins_pnl else 0.0
    gl = abs(sum(losses_pnl)) if losses_pnl else 0.0
    pf = gp / gl if gl > 0 else 0.0

    avg_win = sum(wins_pnl) / len(wins_pnl) if wins_pnl else 0.0
    avg_loss = abs(sum(losses_pnl) / len(losses_pnl)) if losses_pnl else 0.0
    w_pct = len(wins_pnl) / len(all_pnls) if all_pnls else 0.0
    l_pct = len(losses_pnl) / len(all_pnls) if all_pnls else 0.0
    expectancy = (w_pct * avg_win) - (l_pct * avg_loss)

    max_dd = max((r["max_drawdown"] for r in results), default=0.0)

    print(f"\n{'#' * 65}")
    print(f"  CONSOLIDADO {label} — {len(results)} activos")
    print(f"{'#' * 65}")
    print(
        f"  Señales:     {total_signals} generadas | "
        f"{total_allowed} ALLOW | {total_blocked} BLOCK"
    )
    print(
        f"  Trades:      {total_trades} cerrados | "
        f"{total_wins} wins | {total_losses} losses"
    )
    print(f"  Winrate:     {winrate:.1f}%")
    print(f"  Avg Trade:   {avg_trade:.2f}")
    print(f"  Avg Win:     {avg_win:.2f}  |  Avg Loss: {avg_loss:.2f}")
    print(f"  Expectancy:  {expectancy:.2f} por trade")
    print(f"  PF:          {pf:.2f}")
    print(f"  PnL total:   {total_pnl:+.2f}")
    print(f"  Peor DD:     {max_dd:.2f}")
    print(f"{'#' * 65}\n")

    print("  VEREDICTO:")
    if total_trades < 20:
        print("  ⚠️  Muy pocos trades para conclusiones fiables.")
    elif expectancy > 0 and pf >= 1.2 and winrate >= 30:
        print("  ✅  HAY EDGE. Expectancy positiva, PF > 1.2, winrate razonable.")
    elif expectancy > 0:
        print("  🟡  Edge marginal. Positivo pero débil.")
    else:
        print("  ❌  NO HAY EDGE. Expectancy negativa.")
    print()


# =========================================================
# MAIN
# =========================================================
def main():
    print("\n" + "=" * 65)
    print("  SHARK V15 SNIPER — BACKTESTER FIEL")
    print("  Usa la misma lógica que live_engine.py")
    print(f"  Timeframe: {BACKTEST_TIMEFRAME} | Período: {BACKTEST_PERIOD}")
    print(f"  Capital: {CAPITAL} | Risk/trade: {RISK_PER_TRADE}")
    print(f"  Sniper mode: {SNIPER_MODE} | Min ADX: {SNIPER_MIN_ADX}")
    print(f"  Min AI Score: {SNIPER_MIN_AI_SCORE} | Min Final Score: {SNIPER_MIN_FINAL_SCORE}")
    print(f"  Trading cost total: {TRADING_COST_PCT * 100:.2f}%")
    print(f"  Activos: {ASSETS}")
    print("=" * 65 + "\n")

    data_dict = {}
    for ticker in ASSETS:
        print(f"Descargando {ticker}...")
        try:
            df, provider = get_data(ticker, BACKTEST_TIMEFRAME, BACKTEST_PERIOD)
            df = add_indicators(df)

            if df is not None and len(df) >= MIN_WARMUP_BARS + 50:
                data_dict[ticker] = df
                print(f"  OK | {provider} | {len(df)} velas")
            else:
                count = len(df) if df is not None else 0
                print(f"  SKIP | datos insuficientes ({count} velas)")
        except Exception as e:
            print(f"  ERROR | {e}")

    if not data_dict:
        print("\nNo se pudo descargar datos de ningún activo. Abortando.")
        sys.exit(1)

    print(f"\n{'=' * 65}")
    print("  FASE 1: BACKTEST COMPLETO (todo el período)")
    print(f"{'=' * 65}\n")

    full_results = []
    for ticker, df in data_dict.items():
        result = run_v15_backtest_single_asset(
            ticker=ticker,
            df=df,
            capital_start=CAPITAL,
            label="FULL",
            start_eval_index=MIN_WARMUP_BARS,
        )
        full_results.append(result)
        print_result(result)

    print_consolidated(full_results, "FULL PERIOD")

    print(f"\n{'=' * 65}")
    print(f"  FASE 2: WALK-FORWARD ({TRAIN_RATIO * 100:.0f}% train / {(1 - TRAIN_RATIO) * 100:.0f}% test)")
    print(f"{'=' * 65}\n")

    train_results = []
    test_results = []

    for ticker, df in data_dict.items():
        wf = run_walk_forward_v15(ticker, df, CAPITAL)

        print(f"--- {ticker} TRAIN ---")
        print_result(wf["train"], indent="  ")
        train_results.append(wf["train"])

        print(f"--- {ticker} TEST ---")
        print_result(wf["test"], indent="  ")
        test_results.append(wf["test"])

    print_consolidated(train_results, "TRAIN (IN-SAMPLE)")
    print_consolidated(test_results, "TEST (OUT-OF-SAMPLE)")

    print(f"\n{'=' * 65}")
    print("  COMPARACIÓN TRAIN vs TEST")
    print(f"{'=' * 65}\n")

    for ticker in data_dict:
        train = next((r for r in train_results if r["ticker"] == ticker), None)
        test = next((r for r in test_results if r["ticker"] == ticker), None)

        if train and test:
            print(f"  {ticker}:")
            print(
                f"    TRAIN: {train['total_trades']} trades | "
                f"WR {train['winrate']:.1f}% | "
                f"PF {train['profit_factor']:.2f} | "
                f"Exp {train['expectancy']:.2f}"
            )
            print(
                f"    TEST:  {test['total_trades']} trades | "
                f"WR {test['winrate']:.1f}% | "
                f"PF {test['profit_factor']:.2f} | "
                f"Exp {test['expectancy']:.2f}"
            )

            if train["total_trades"] > 5 and test["total_trades"] > 5:
                wr_delta = test["winrate"] - train["winrate"]
                pf_delta = test["profit_factor"] - train["profit_factor"]

                if wr_delta < -15 or pf_delta < -0.5:
                    print("    ⚠️  Degradación significativa train→test")
                elif wr_delta > -5 and pf_delta > -0.2:
                    print("    ✅  Consistente entre train y test")
                else:
                    print("    🟡  Degradación moderada")
            else:
                print("    ⚠️  Pocos trades para comparar")

            print()

    print("\n" + "=" * 65)
    print("  BACKTEST COMPLETO")
    print("=" * 65 + "\n")


if __name__ == "__main__":
    main()