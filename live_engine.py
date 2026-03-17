import time
from datetime import datetime

from config import (
    ASSETS,
    TIMEFRAME,
    PERIOD,
    RISK_PER_TRADE,
    LOOP_INTERVAL,
    SETUP_ALERTS_ENABLED,
    SETUP_ALERT_COOLDOWN_MINUTES
)
from data_feed import get_data
from indicators import add_indicators
from signals import check_signal
from risk_management import calculate_trade_levels
from storage import (
    init_db,
    save_signal,
    get_paper_capital,
    log_risk_event,
    log_feed_event,
    log_setup_alert,
    has_recent_setup_alert
)
from paper_broker import (
    open_trade,
    check_and_close_trades,
    has_open_trade_for_ticker
)
from telegram_alerts import (
    send_telegram_message,
    format_pro_signal_message,
    format_setup_watch_message
)
from ai_filter import evaluate_signal_quality
from risk_control_engine import evaluate_risk_controls
from market_regime import detect_market_regime
from asset_ranker import get_ranked_assets
from position_scaler import apply_position_scaling
from capital_allocator import apply_capital_allocation
from trade_intelligence import evaluate_trade_context
from session_volatility_intelligence import (
    evaluate_session_filter,
    evaluate_volatility_filter
)
from final_decision_engine import evaluate_final_decision
from opportunity_scanner import scan_smart_opportunity
from setup_alert_engine import detect_setup_watch
from asset_labels import get_asset_label_with_ticker


def build_technical_reason(df, signal):
    last = df.iloc[-1]

    close_price = float(last["Close"])
    ema200 = float(last["ema200"])
    rsi = float(last["rsi"])
    macd = float(last["macd"])
    macd_signal = float(last["macd_signal"])
    adx = float(last["adx"])

    if signal == "BUY":
        return (
            f"Tendencia alcista: precio ({close_price:.2f}) sobre EMA200 ({ema200:.2f}), "
            f"RSI {rsi:.2f}, MACD {macd:.2f} > señal {macd_signal:.2f}, "
            f"ADX {adx:.2f} confirmando fuerza."
        )

    if signal == "SELL":
        return (
            f"Tendencia bajista: precio ({close_price:.2f}) bajo EMA200 ({ema200:.2f}), "
            f"RSI {rsi:.2f}, MACD {macd:.2f} < señal {macd_signal:.2f}, "
            f"ADX {adx:.2f} confirmando fuerza."
        )

    return "Sin motivo técnico relevante."


def run_live_cycle():
    print("\n=== SHARK V15 SNIPER LIVE CYCLE ===")
    print("Hora:", datetime.now().isoformat())

    latest_prices = {}
    market_data = {}

    ranked_assets = get_ranked_assets(ASSETS)
    print("Ranking actual:", [get_asset_label_with_ticker(x) for x in ranked_assets])

    for ticker in ranked_assets:
        asset_name = get_asset_label_with_ticker(ticker)

        try:
            df, provider_used = get_data(ticker, TIMEFRAME, PERIOD)
            df = add_indicators(df)

            market_data[ticker] = df
            latest_prices[ticker] = float(df.iloc[-1]["Close"])

            log_feed_event(
                timestamp=datetime.now().isoformat(),
                ticker=ticker,
                provider=provider_used,
                timeframe=TIMEFRAME,
                period=PERIOD,
                rows_count=len(df),
                status="SUCCESS",
                message=f"Feed OK con {provider_used}"
            )

            print(f"FEED | {asset_name} | Provider: {provider_used} | Rows: {len(df)}")

        except Exception as e:
            log_feed_event(
                timestamp=datetime.now().isoformat(),
                ticker=ticker,
                provider="NONE",
                timeframe=TIMEFRAME,
                period=PERIOD,
                rows_count=0,
                status="FAIL",
                message=str(e)
            )
            print(f"Error cargando {asset_name}: {e}")

    check_and_close_trades(latest_prices)

    capital = get_paper_capital()
    print(f"Capital paper actual: {capital:.2f}")

    for ticker, df in market_data.items():
        asset_name = get_asset_label_with_ticker(ticker)

        try:
            base_signal = check_signal(df)
            regime = detect_market_regime(df)

            scanner_info = {
                "signal": "NO_SIGNAL",
                "reason": "No usado"
            }

            signal = base_signal

            if base_signal == "NO_SIGNAL":
                scanner_info = scan_smart_opportunity(df)
                if scanner_info["signal"] in ["BUY", "SELL"]:
                    signal = scanner_info["signal"]

            last = df.iloc[-1]
            adx_value = float(last["adx"])

            print(
                f"{asset_name} | Señal base: {base_signal} | "
                f"Scanner: {scanner_info['signal']} | "
                f"Final signal: {signal} | "
                f"Regime: {regime} | "
                f"Close: {float(last['Close']):.2f} | "
                f"RSI: {float(last['rsi']):.2f} | "
                f"ADX: {adx_value:.2f}"
            )

            if signal == "NO_SIGNAL" and SETUP_ALERTS_ENABLED:
                setup_info = detect_setup_watch(df, regime)

                if setup_info["alert_type"] != "NONE":
                    print(f"SETUP | {asset_name} | {setup_info['alert_type']} | {setup_info['reason']}")

                    if not has_recent_setup_alert(
                        ticker=ticker,
                        alert_type=setup_info["alert_type"],
                        within_minutes=SETUP_ALERT_COOLDOWN_MINUTES
                    ):
                        send_telegram_message(
                            format_setup_watch_message(
                                ticker=ticker,
                                last_row=last,
                                setup_info=setup_info,
                                regime=regime
                            )
                        )

                        log_setup_alert(
                            timestamp=datetime.now().isoformat(),
                            ticker=ticker,
                            alert_type=setup_info["alert_type"],
                            reason=setup_info["reason"]
                        )

            base_trade_setup = calculate_trade_levels(
                df=df,
                signal=signal,
                capital=capital,
                risk_per_trade=RISK_PER_TRADE
            )

            scaled_trade_setup = apply_position_scaling(base_trade_setup, ticker)
            trade_setup = apply_capital_allocation(
                scaled_trade_setup,
                ticker=ticker,
                default_assets=ASSETS
            )

            save_signal(
                timestamp=datetime.now().isoformat(),
                ticker=ticker,
                signal=signal,
                regime=regime,
                df=df,
                trade=trade_setup
            )

            if signal in ["BUY", "SELL"]:
                ai_result = evaluate_signal_quality(ticker, signal)
                context_result = evaluate_trade_context(ticker, signal, regime)
                session_result = evaluate_session_filter(df, regime)
                volatility_result = evaluate_volatility_filter(df, regime)
                risk_result = evaluate_risk_controls(ticker, signal)

                final_result = evaluate_final_decision(
                    ai_result=ai_result,
                    context_result=context_result,
                    session_result=session_result,
                    volatility_result=volatility_result,
                    risk_result=risk_result,
                    adx=adx_value,
                    regime=regime
                )

                print(
                    f"AI | {asset_name} | Score: {ai_result['score']} | "
                    f"Decision: {ai_result['decision']} | "
                    f"Reason: {ai_result['reason']}"
                )

                print(
                    f"INTEL | {asset_name} | "
                    f"FinalScore: {context_result['final_score']} | "
                    f"Decision: {context_result['decision']} | "
                    f"Reason: {context_result['reason']}"
                )

                print(
                    f"SESSION | {asset_name} | "
                    f"Session: {session_result['session']} | "
                    f"Allow: {session_result['allow']} | "
                    f"Reason: {session_result['reason']}"
                )

                print(
                    f"VOL | {asset_name} | "
                    f"State: {volatility_result['volatility_state']} | "
                    f"Allow: {volatility_result['allow']} | "
                    f"Reason: {volatility_result['reason']}"
                )

                print(
                    f"RISK | {asset_name} | Allow: {risk_result['allow']} | "
                    f"Reason: {risk_result['reason']}"
                )

                print(
                    f"FINAL | {asset_name} | Score: {final_result['score']} | "
                    f"Decision: {final_result['decision']} | "
                    f"Reason: {final_result['reason']}"
                )

                technical_reason = build_technical_reason(df, signal)

                if scanner_info["signal"] in ["BUY", "SELL"]:
                    technical_reason += f" | Scanner extra: {scanner_info['reason']}"

                if final_result["decision"] == "BLOCK":
                    log_risk_event(
                        timestamp=datetime.now().isoformat(),
                        ticker=ticker,
                        signal=signal,
                        event_type="FINAL_BLOCK",
                        reason=final_result["reason"]
                    )

                    print(f"--> Trade bloqueado por semáforo final: {asset_name}")
                    continue

                send_telegram_message(
                    format_pro_signal_message(
                        ticker=ticker,
                        signal=signal,
                        trade_setup=trade_setup,
                        last_row=last,
                        ai_result=ai_result,
                        risk_result=risk_result,
                        regime=regime,
                        technical_reason=technical_reason,
                        session_result=session_result,
                        volatility_result=volatility_result,
                        context_result=context_result
                    )
                )

            if signal in ["BUY", "SELL"] and not has_open_trade_for_ticker(ticker):
                if trade_setup["position_size"] > 0:
                    open_trade(ticker, signal, regime, trade_setup)

                    print(
                        f"--> NUEVO PAPER TRADE: {asset_name} | {signal} | "
                        f"Regime: {regime} | "
                        f"Entry: {trade_setup['entry']:.2f} | "
                        f"SL: {trade_setup['stop_loss']:.2f} | "
                        f"TP: {trade_setup['take_profit']:.2f} | "
                        f"Size: {trade_setup['position_size']:.4f} | "
                        f"Scale: {trade_setup.get('scale_factor', 1.0):.2f} | "
                        f"CapitalAlloc: {trade_setup.get('capital_allocation_factor', 1.0):.2f}"
                    )

        except Exception as e:
            print(f"Error analizando {asset_name}: {e}")


def run_live_engine(interval_seconds=None):
    init_db()

    if interval_seconds is None:
        interval_seconds = LOOP_INTERVAL

    send_telegram_message("🤖 SHARK V15 SNIPER INICIADO")
    print("=== SHARK V15 SNIPER INICIADO ===")

    while True:
        try:
            run_live_cycle()
        except Exception as e:
            print(f"Error en ciclo live: {e}")
            send_telegram_message(f"❌ Error en ciclo live: {e}")

        print(f"Esperando {interval_seconds} segundos para el próximo ciclo...\n")
        time.sleep(interval_seconds)