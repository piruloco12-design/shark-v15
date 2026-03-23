import time
from datetime import datetime

from config import (
    ASSETS,
    TIMEFRAME,
    PERIOD,
    CAPITAL,
    RISK_PER_TRADE,
    LOOP_INTERVAL,
    STARTUP_MESSAGE_ENABLED,
    VERBOSE_LOGS,
    SAVE_ALL_SIGNALS,
)

from data_feed import get_data
from indicators import add_indicators
from market_regime import detect_market_regime
from signals import check_signal
from opportunity_scanner import scan_smart_opportunity
from risk_management import calculate_trade_levels
from final_decision_engine import evaluate_final_decision

from ai_filter import evaluate_signal_quality
from storage import init_db

try:
    from trade_intelligence import evaluate_trade_context
except Exception:
    def evaluate_trade_context(ticker, signal, regime):
        return {
            "ticker_signal_score": 55.0,
            "ticker_regime_score": 55.0,
            "signal_score": 55.0,
            "final_score": 55.0,
            "decision": "NEUTRAL",
            "reason": "trade_intelligence no disponible"
        }

try:
    from session_volatility_intelligence import (
        evaluate_session_filter,
        evaluate_volatility_filter,
    )
except Exception:
    def evaluate_session_filter(data, regime):
        return {"allow": True, "reason": "session_volatility_intelligence no disponible"}

    def evaluate_volatility_filter(data, regime):
        return {"allow": True, "reason": "session_volatility_intelligence no disponible"}

try:
    from risk_control_engine import evaluate_risk_controls
except Exception:
    def evaluate_risk_controls(ticker=None, signal=None):
        return {"allow": True, "reason": "risk_control_engine no disponible"}

try:
    from paper_broker import (
        open_trade,
        update_open_trades,
        has_open_trade_for_ticker,
    )
except Exception:
    def open_trade(ticker, signal, regime, trade_setup):
        print(f"[paper_broker fallback] open_trade | {ticker} | {signal} | {regime} | {trade_setup}")

    def update_open_trades():
        return

    def has_open_trade_for_ticker(ticker):
        return False

try:
    from storage import save_signal
except Exception:
    def save_signal(**kwargs):
        return

try:
    import telegram_alerts
except Exception:
    telegram_alerts = None


# =========================================================
# HELPERS
# =========================================================

def _safe_float(value, default=0.0):
    try:
        return float(value)
    except Exception:
        return default


def _safe_send_telegram(text):
    if telegram_alerts is None:
        return

    candidates = [
        "send_telegram_message",
        "send_message",
        "send_alert",
        "send_text_message",
    ]

    for fn_name in candidates:
        fn = getattr(telegram_alerts, fn_name, None)
        if callable(fn):
            try:
                fn(text)
                return
            except Exception:
                pass


def _send_startup_message():
    if not STARTUP_MESSAGE_ENABLED:
        return

    msg = (
        "🤖 SHARK V15 SNIPER INICIADO EN RENDER\n\n"
        f"Loop ejecutado correctamente.\n"
        f"Timeframe: {TIMEFRAME}\n"
        f"Loop: {LOOP_INTERVAL}s\n"
        f"Activos: {len(ASSETS)}"
    )
    _safe_send_telegram(msg)


def _send_cycle_ok():
    msg = (
        "✅ SHARK V15 SNIPER ACTIVO\n"
        "Loop ejecutado correctamente.\n"
        f"Timeframe: {TIMEFRAME}\n"
        f"Loop: {LOOP_INTERVAL}s\n"
        f"Activos: {len(ASSETS)}"
    )
    _safe_send_telegram(msg)


def _send_error_message(text):
    _safe_send_telegram(f"❌ ERROR SHARK V15\n\n{text}")


def _send_trade_open_message(ticker, signal, trade_setup, capital_snapshot):
    entry = _safe_float(trade_setup.get("entry"))
    stop = _safe_float(trade_setup.get("stop_loss"))
    tp = _safe_float(trade_setup.get("take_profit"))
    size = _safe_float(trade_setup.get("position_size"))
    rr = _safe_float(trade_setup.get("rr_ratio"))

    msg = (
        "📈 SHARK TRADE ABIERTO\n\n"
        f"Activo: {ticker}\n"
        f"Dirección: {signal}\n\n"
        f"Entry: {entry:.2f} USD\n"
        f"Stop: {stop:.2f} USD\n"
        f"TP: {tp:.2f} USD\n\n"
        f"Size: {size:.4f}\n"
        f"R:R: {rr:.2f}\n"
        f"Capital actual: {capital_snapshot:.2f} €"
    )
    _safe_send_telegram(msg)


def _send_mobile_signal_message(
    ticker,
    signal,
    data,
    regime,
    ai_result,
    context_result,
    session_result,
    volatility_result,
    risk_result,
    trade_setup,
    final_result,
):
    last = data.iloc[-1]

    price = _safe_float(last.get("Close"))
    rsi = _safe_float(last.get("rsi"))
    adx = _safe_float(last.get("adx"))
    atr = _safe_float(last.get("atr"))
    ema200 = _safe_float(last.get("ema200"))
    macd = _safe_float(last.get("macd"))
    macd_signal = _safe_float(last.get("macd_signal"))

    entry = _safe_float(trade_setup.get("entry"))
    stop = _safe_float(trade_setup.get("stop_loss"))
    tp = _safe_float(trade_setup.get("take_profit"))
    rr = _safe_float(trade_setup.get("rr_ratio"))
    size = _safe_float(trade_setup.get("position_size"))
    ai_score = _safe_float(ai_result.get("score", 50))
    ctx_score = _safe_float(context_result.get("final_score", 55))

    session_reason = session_result.get("reason", "")
    session_label = "Sí" if session_result.get("allow", True) else "No"
    vol_label = "NORMAL" if volatility_result.get("allow", True) else "BLOQUEADA"

    fuerza = "ALTA" if adx >= 30 else "MEDIA" if adx >= 25 else "BAJA"

    if signal == "BUY":
        motivo = (
            f"Tendencia alcista: precio ({price:.2f}) sobre EMA200 ({ema200:.2f}), "
            f"RSI {rsi:.2f}, MACD {macd:.2f} > señal {macd_signal:.2f}, "
            f"ADX {adx:.2f} confirmando fuerza."
        )
    else:
        motivo = (
            f"Tendencia bajista: precio ({price:.2f}) bajo EMA200 ({ema200:.2f}), "
            f"RSI {rsi:.2f}, MACD {macd:.2f} < señal {macd_signal:.2f}, "
            f"ADX {adx:.2f} confirmando fuerza."
        )

    msg = (
        "📱 SHARK EJECUCIÓN MÓVIL\n\n"
        f"Activo: {ticker}\n"
        f"Dirección: {signal}\n"
        f"Operable ahora: {session_label}\n"
        f"Fuerza: {fuerza}\n"
        f"Moneda esperada: USD\n\n"
        f"Precio actual: {price:.2f} USD\n"
        f"Entry: {entry:.2f} USD\n"
        f"Stop: {stop:.2f} USD\n"
        f"Take Profit: {tp:.2f} USD\n\n"
        f"R:R: {rr:.2f}\n"
        f"Riesgo estimado: 5.00 €\n"
        f"Size: {size:.4f}\n\n"
        f"RSI: {rsi:.2f}\n"
        f"ADX: {adx:.2f}\n"
        f"ATR: {atr:.2f}\n"
        f"Regime: {regime}\n"
        f"Session: {session_reason if session_reason else 'OK'}\n"
        f"Volatilidad: {vol_label}\n\n"
        f"AI: {ai_result.get('decision', 'NEUTRAL')} ({ai_score:.1f})\n"
        f"Contexto: {context_result.get('decision', 'NEUTRAL')} ({ctx_score:.1f})\n"
        f"Risk: {'ALLOW' if risk_result.get('allow', True) else 'BLOCK'}\n\n"
        f"Motivo:\n{motivo}"
    )
    _safe_send_telegram(msg)


def _log(msg):
    if VERBOSE_LOGS:
        print(msg)


# =========================================================
# CORE
# =========================================================

def run_live_cycle():
    _log("\n=== SHARK V15 SNIPER LIVE CYCLE ===")
    _log(f"Hora: {datetime.utcnow().isoformat()}")

    try:
        update_open_trades()
    except Exception as e:
        _log(f"ERROR update_open_trades: {e}")

    for ticker in ASSETS:
        try:
            _log(f"\n--- Evaluando {ticker} ---")

            # -------------------------------------------------
            # DATA
            # -------------------------------------------------
            df, provider = get_data(ticker, TIMEFRAME, PERIOD)
            df = add_indicators(df)

            _log(f"DATA FEED OK | {ticker} | provider={provider} | rows={len(df)}")

            last = df.iloc[-1]
            adx_value = _safe_float(last.get("adx"))
            regime = str(detect_market_regime(df)).strip().upper()

            # -------------------------------------------------
            # SIGNAL
            # -------------------------------------------------
            base_signal = check_signal(df)
            signal = base_signal
            scanner_info = {"signal": "NO_SIGNAL", "reason": "No usado"}

            if base_signal == "NO_SIGNAL":
                scanner_info = scan_smart_opportunity(df)
                if scanner_info.get("signal") in ["BUY", "SELL"]:
                    signal = scanner_info["signal"]

            _log(
                f"{ticker} | Señal base: {base_signal} | "
                f"Scanner: {scanner_info.get('signal')} | "
                f"Final signal: {signal} | Regime: {regime} | "
                f"Close: {_safe_float(last.get('Close')):.2f} | "
                f"RSI: {_safe_float(last.get('rsi')):.2f} | "
                f"ADX: {adx_value:.2f}"
            )

            if signal not in ["BUY", "SELL"]:
                continue

            # -------------------------------------------------
            # OPTIONAL SIGNAL SAVE
            # -------------------------------------------------
            if SAVE_ALL_SIGNALS:
                try:
                    save_signal(
                        ticker=ticker,
                        signal=signal,
                        regime=regime,
                        price=_safe_float(last.get("Close")),
                        rsi=_safe_float(last.get("rsi")),
                        adx=adx_value,
                        reason=scanner_info.get("reason", "") if base_signal == "NO_SIGNAL" else "Base signal",
                    )
                except Exception as e:
                    _log(f"save_signal warning | {ticker}: {e}")

            # -------------------------------------------------
            # AI / CONTEXT / FILTERS
            # -------------------------------------------------
            ai_result = evaluate_signal_quality(ticker, signal)
            _log(
                f"AI | {ticker} | Score: {ai_result.get('score')} | "
                f"Decision: {ai_result.get('decision')} | "
                f"Reason: {ai_result.get('reason')}"
            )

            context_result = evaluate_trade_context(ticker, signal, regime)
            _log(
                f"INTEL | {ticker} | FinalScore: {context_result.get('final_score')} | "
                f"Decision: {context_result.get('decision')} | "
                f"Reason: {context_result.get('reason')}"
            )

            session_result = evaluate_session_filter(df, regime)
            _log(
                f"SESSION | {ticker} | Allow: {session_result.get('allow')} | "
                f"Reason: {session_result.get('reason')}"
            )

            volatility_result = evaluate_volatility_filter(df, regime)
            _log(
                f"VOL | {ticker} | Allow: {volatility_result.get('allow')} | "
                f"Reason: {volatility_result.get('reason')}"
            )

            risk_result = evaluate_risk_controls(ticker=ticker, signal=signal)
            _log(
                f"RISK | {ticker} | Allow: {risk_result.get('allow')} | "
                f"Reason: {risk_result.get('reason')}"
            )

            # -------------------------------------------------
            # FINAL DECISION
            # -------------------------------------------------
            final_result = evaluate_final_decision(
                ai_result=ai_result,
                context_result=context_result,
                session_result=session_result,
                volatility_result=volatility_result,
                risk_result=risk_result,
                adx=adx_value,
                regime=regime,
                data=df,
                ticker=ticker,
            )

            debug = final_result.get("debug", {})
            _log(
                f"FINAL | {ticker} | Score: {debug.get('final_score')} | "
                f"Decision: {final_result.get('decision')} | "
                f"Reason: {final_result.get('reason')}"
            )

            if final_result["decision"] != "ALLOW":
                _log(f"--> Trade bloqueado por semáforo final: {ticker}")
                continue

            # -------------------------------------------------
            # TRADE SETUP
            # -------------------------------------------------
            trade_setup = calculate_trade_levels(
                df=df,
                signal=signal,
                capital=CAPITAL,
                risk_per_trade=RISK_PER_TRADE,
            )

            if has_open_trade_for_ticker(ticker):
                _log(f"--> Trade bloqueado: ya existe trade abierto para {ticker}")
                continue

            if _safe_float(trade_setup.get("position_size")) <= 0:
                _log(f"--> Trade bloqueado: position_size inválido para {ticker}")
                continue

            # -------------------------------------------------
            # OPEN TRADE
            # -------------------------------------------------
            _send_mobile_signal_message(
                ticker=ticker,
                signal=signal,
                data=df,
                regime=regime,
                ai_result=ai_result,
                context_result=context_result,
                session_result=session_result,
                volatility_result=volatility_result,
                risk_result=risk_result,
                trade_setup=trade_setup,
                final_result=final_result,
            )

            open_trade(ticker, signal, regime, trade_setup)
            _send_trade_open_message(ticker, signal, trade_setup, CAPITAL)

        except Exception as e:
            err = f"{ticker} | ERROR live cycle: {e}"
            print(err)
            _send_error_message(err)


def run_live_engine():
    # Inicializar base de datos (crea tablas si no existen)
    init_db()

    print("=" * 50)
    print("SHARK V15 SNIPER - INICIO")
    print("=" * 50)
    print(f"Hora inicio: {datetime.utcnow().isoformat()}")
    print("Entorno: production")
    print(f"Loop interval: {LOOP_INTERVAL} segundos")
    print("=" * 50)

    _send_startup_message()

    first_cycle = True

    while True:
        try:
            run_live_cycle()
            if first_cycle:
                _send_cycle_ok()
                first_cycle = False
        except Exception as e:
            err = f"ERROR GENERAL run_live_engine: {e}"
            print(err)
            _send_error_message(err)

        print(f"Esperando {LOOP_INTERVAL} segundos para el próximo ciclo...")
        time.sleep(LOOP_INTERVAL)