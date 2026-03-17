import time
from datetime import datetime, timedelta

from config import (
    ASSETS,
    TIMEFRAME,
    PERIOD,
    RISK_PER_TRADE,
    LOOP_INTERVAL,
    SETUP_ALERTS_ENABLED,
    SETUP_ALERT_COOLDOWN_MINUTES,
    SIGNAL_ALERT_COOLDOWN_MINUTES,
    ERROR_ALERT_COOLDOWN_MINUTES,
    STARTUP_MESSAGE_ENABLED
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


# =========================================================
# ANTI-SPAM RUNTIME MEMORY
# =========================================================
_SIGNAL_ALERT_MEMORY = {}
_SETUP_ALERT_MEMORY = {}
_ERROR_ALERT_MEMORY = {}


def _now():
    return datetime.now()


def _normalize_text(value):
    if value is None:
        return ""
    return str(value).strip()


def _round_safe(value, digits=4):
    try:
        return round(float(value), digits)
    except Exception:
        return 0.0


def _should_send_runtime_alert(memory_store, key, signature, cooldown_minutes):
    """
    Regla anti-spam:
    - Si nunca se envió -> enviar
    - Si la firma cambió -> enviar inmediatamente
    - Si la firma es igual y sigue dentro del cooldown -> NO enviar
    - Si la firma es igual pero el cooldown expiró -> enviar
    """
    now = _now()
    existing = memory_store.get(key)

    if existing is None:
        memory_store[key] = {
            "signature": signature,
            "timestamp": now
        }
        return True

    last_signature = existing.get("signature")
    last_timestamp = existing.get("timestamp")

    if last_signature != signature:
        memory_store[key] = {
            "signature": signature,
            "timestamp": now
        }
        return True

    if last_timestamp is None:
        memory_store[key] = {
            "signature": signature,
            "timestamp": now
        }
        return True

    elapsed = now - last_timestamp
    if elapsed >= timedelta(minutes=cooldown_minutes):
        memory_store[key] = {
            "signature": signature,
            "timestamp": now
        }
        return True

    return False


def _build_signal_alert_signature(
    ticker,
    signal,
    regime,
    trade_setup,
    ai_result,
    context_result,
    session_result,
    volatility_result,
    final_result,
    scanner_info
):
    return (
        f"{ticker}|"
        f"{signal}|"
        f"{regime}|"
        f"{_round_safe(trade_setup.get('entry', 0), 2)}|"
        f"{_round_safe(trade_setup.get('stop_loss', 0), 2)}|"
        f"{_round_safe(trade_setup.get('take_profit', 0), 2)}|"
        f"{_round_safe(trade_setup.get('position_size', 0), 4)}|"
        f"{_round_safe(ai_result.get('score', 0), 1)}|"
        f"{_round_safe(context_result.get('final_score', 0), 1)}|"
        f"{_normalize_text(session_result.get('session'))}|"
        f"{_normalize_text(volatility_result.get('volatility_state'))}|"
        f"{_normalize_text(final_result.get('decision'))}|"
        f"{_round_safe(final_result.get('score', 0), 1)}|"
        f"{_normalize_text(scanner_info.get('signal'))}|"
        f"{_normalize_text(scanner_info.get('reason'))}"
    )


def _build_setup_alert_signature(ticker, setup_info, regime, last_row):
    return (
        f"{ticker}|"
        f"{_normalize_text(setup_info.get('alert_type'))}|"
        f"{_normalize_text(regime)}|"
        f"{_round_safe(last_row.get('Close', 0), 2)}|"
        f"{_round_safe(last_row.get('rsi', 0), 2)}|"
        f"{_round_safe(last_row.get('adx', 0), 2)}|"
        f"{_normalize_text(setup_info.get('reason'))}"
    )


def _build_error_signature(scope, error_text):
    clean_error = _normalize_text(error_text)
    return f"{scope}|{clean_error}"


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

                    setup_signature = _build_setup_alert_signature(
                        ticker=ticker,
                        setup_info=setup_info,
                        regime=regime,
                        last_row=last
                    )

                    db_allows_setup = not has_recent_setup_alert(
                        ticker=ticker,
                        alert_type=setup_info["alert_type"],
                        within_minutes=SETUP_ALERT_COOLDOWN_MINUTES
                    )

                    runtime_allows_setup = _should_send_runtime_alert(
                        memory_store=_SETUP_ALERT_MEMORY,
                        key=f"{ticker}|{setup_info['alert_type']}",
                        signature=setup_signature,
                        cooldown_minutes=SETUP_ALERT_COOLDOWN_MINUTES
                    )

                    if db_allows_setup and runtime_allows_setup:
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
                    else:
                        print(f"ANTI-SPAM SETUP | {asset_name} | alerta duplicada evitada")

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

                already_has_open_trade = has_open_trade_for_ticker(ticker)

                signal_signature = _build_signal_alert_signature(
                    ticker=ticker,
                    signal=signal,
                    regime=regime,
                    trade_setup=trade_setup,
                    ai_result=ai_result,
                    context_result=context_result,
                    session_result=session_result,
                    volatility_result=volatility_result,
                    final_result=final_result,
                    scanner_info=scanner_info
                )

                can_send_signal_alert = _should_send_runtime_alert(
                    memory_store=_SIGNAL_ALERT_MEMORY,
                    key=f"{ticker}|{signal}",
                    signature=signal_signature,
                    cooldown_minutes=SIGNAL_ALERT_COOLDOWN_MINUTES
                )

                if not already_has_open_trade and can_send_signal_alert:
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
                else:
                    if already_has_open_trade:
                        print(f"ANTI-SPAM SIGNAL | {asset_name} | ya existe trade abierto")
                    elif not can_send_signal_alert:
                        print(f"ANTI-SPAM SIGNAL | {asset_name} | señal duplicada evitada")

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

    if STARTUP_MESSAGE_ENABLED:
        send_telegram_message("🤖 SHARK V15 SNIPER INICIADO")

    print("=== SHARK V15 SNIPER INICIADO ===")

    while True:
        try:
            run_live_cycle()
        except Exception as e:
            error_text = str(e)
            print(f"Error en ciclo live: {error_text}")

            error_signature = _build_error_signature("LIVE_CYCLE", error_text)

            can_send_error = _should_send_runtime_alert(
                memory_store=_ERROR_ALERT_MEMORY,
                key="LIVE_CYCLE",
                signature=error_signature,
                cooldown_minutes=ERROR_ALERT_COOLDOWN_MINUTES
            )

            if can_send_error:
                send_telegram_message(f"❌ Error en ciclo live: {error_text}")
            else:
                print("ANTI-SPAM ERROR | error repetido no enviado a Telegram")

        print(f"Esperando {interval_seconds} segundos para el próximo ciclo...\n")
        time.sleep(interval_seconds)