import time
from datetime import datetime, timezone

from config import (
    ASSETS,
    TIMEFRAME,
    PERIOD,
    CAPITAL,
    RISK_PER_TRADE,
    LOOP_INTERVAL,
    MIN_BARS,
    STARTUP_MESSAGE_ENABLED,
    VERBOSE_LOGS,
    SAVE_ALL_SIGNALS,
    COSTE_POR_PATA,
)

from data_feed import get_data
from indicators import add_indicators
from market_regime import detect_market_regime
from signals import check_signal
from opportunity_scanner import scan_smart_opportunity
from risk_management import calculate_trade_levels


def _safe_float_local(valor, defecto):
    """El capital de la cuenta, o el configurado si no se puede leer.

    Si la lectura falla no se bloquea el ciclo, pero tampoco se finge un
    efectivo infinito: se cae al capital declarado, que es el supuesto de
    partida.
    """
    try:
        v = float(valor)
    except (TypeError, ValueError):
        return float(defecto)
    if v != v or v in (float("inf"), float("-inf")) or v <= 0:
        return float(defecto)
    return v
from final_decision_engine import evaluate_final_decision
from storage import init_db, save_signal, get_paper_capital

from ai_filter import evaluate_signal_quality

# --- Ampliacion institucional (seccion 15). En try/except a proposito:
# si la ampliacion no importa, el bot sigue funcionando exactamente como
# antes. Es un anexo, no una dependencia.
try:
    from institucional.configuracion import desde_entorno as _inst_config
    from institucional.observacion import (
        evaluar as evaluar_observacion,
        fallos_de_registro as fallos_registro_inst,
        init_observacion,
    )
    _INST_EXTENSION = _inst_config()
    INSTITUCIONAL_DISPONIBLE = True
except Exception as _e_inst:      # pragma: no cover
    _INST_EXTENSION = None
    INSTITUCIONAL_DISPONIBLE = False
    _INST_ERROR = str(_e_inst)

# Series diarias y ranking para M02/M03.
#
# Esto estaba a None y SOLO se rellenaba en tests/_replay_runner.py, asi que
# por la ruta de produccion M02 y M03 registraban NO_DATA siempre: los logs
# mostraban evaluaciones, la tabla se llenaba de filas, y ninguna llevaba una
# opinion dentro. Parecia que los modulos funcionaban.
#
# Ahora los llena una tarea mensual persistida (institucional/snapshot.py).
# El ciclo intradia NO descarga: lee el snapshot de la base de datos. Solo
# cuando el snapshot caduca, una vez al mes, se vuelve a descargar.
_INST_SERIES_TR = None
_INST_EFECTIVO = None
_INST_RANKING = None
_INST_SNAPSHOT_ID = None


def _refrescar_snapshot_institucional(forzar=False):
    """Carga el snapshot mensual y, si caduco, lo reconstruye.

    Nunca lanza: si falla, los modulos se quedan sin datos y registran
    NO_DATA, que es la degradacion correcta. Lo que no puede pasar es que
    un fallo aqui tumbe un ciclo del bot.
    """
    global _INST_SERIES_TR, _INST_EFECTIVO, _INST_RANKING, _INST_SNAPSHOT_ID

    if not INSTITUCIONAL_DISPONIBLE or _INST_EXTENSION is None:
        return
    if _INST_EXTENSION.mode == "OFF":
        return

    try:
        from institucional import snapshot as _snap

        hace_falta, motivo = _snap.hace_falta_actualizar()
        if hace_falta or forzar:
            _log(f"INST | snapshot: {motivo} -> reconstruyendo")
            resultado = _snap.actualizar_si_toca(
                list(ASSETS), config_hash=_INST_EXTENSION.config_hash())
            snap = resultado["snapshot"]
        else:
            snap = _snap.cargar_ultimo()

        if snap is None:
            _log("INST | sin snapshot disponible: M02/M03 quedan en NO_DATA")
            return

        _INST_SERIES_TR = snap.get("series") or None
        _INST_EFECTIVO = snap.get("efectivo")
        _INST_RANKING = _snap.a_ranking(snap)
        _INST_SNAPSHOT_ID = snap.get("snapshot_id")

        import pandas as _pd
        _log(
            f"INST | snapshot {_INST_SNAPSHOT_ID} | "
            f"{len(_INST_SERIES_TR or {})} series | "
            f"vigente hasta "
            f"{_pd.Timestamp(snap['valid_until'], unit='s', tz='UTC').date()} | "
            f"ranking {snap['ranking']['seleccionados']}"
        )
        if snap.get("incidencias"):
            _log(f"INST | incidencias del snapshot: {snap['incidencias']}")

    except Exception as e:
        _log(f"INST | no se pudo refrescar el snapshot: {type(e).__name__}: {e}")

# Imports directos — NO en try/except para que fallen ruidosamente si hay error
from paper_broker import (
    open_trade,
    check_and_close_trades,
    has_open_trade_for_ticker,
)

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

# Noticias + verificacion con Gemini. Opcionales las dos: si
# fallan, el bot opera igual. Un filtro de noticias caido no puede
# dejar la cuenta parada ni, peor, operando a ciegas creyendo que
# alguien ha verificado algo.
try:
    from noticias import obtener_noticias, formatear_para_prompt
    from gemini_filter import (
        verificar_operacion,
        estado as estado_gemini,
        probar_conexion as probar_gemini,
    )
    NOTICIAS_DISPONIBLES = True
except Exception as _e:
    print(f"AVISO: filtro de noticias no disponible ({_e})")
    NOTICIAS_DISPONIBLES = False

    def obtener_noticias(ticker, usar_cache=True):
        return [], None, "modulo no disponible"

    def formatear_para_prompt(titulares):
        return "(sin noticias)"

    def verificar_operacion(*a, **k):
        return {"veredicto": "NEUTRAL", "confianza": 0,
                "motivo": "modulo no disponible", "fuente": "interno",
                "bloquea": False}

    def estado_gemini():
        return "Filtro de noticias: NO DISPONIBLE"

    def probar_gemini():
        return True, "Filtro de noticias no disponible"

# Archivo histórico de velas. Es opcional: si falla, el bot sigue
# operando igual, solo deja de acumular histórico. Por eso va en
# try/except, al contrario que paper_broker, que es esencial.
try:
    from historial_mercado import (
        init_historial,
        guardar as guardar_historial,
        comprobar_persistencia,
    )
    HISTORIAL_DISPONIBLE = True
except Exception as _e:
    print(f"AVISO: historial_mercado no disponible ({_e}). "
          f"El bot funciona, pero no acumulará histórico de velas.")
    HISTORIAL_DISPONIBLE = False

    def init_historial():
        return

    def guardar_historial(ticker, timeframe, df):
        return 0

    def comprobar_persistencia():
        return True, "historial_mercado no disponible"

from telegram_alerts import send_telegram_message


# =========================================================
# HELPERS
# =========================================================

def _safe_float(value, default=0.0):
    try:
        value = float(value)
    except (TypeError, ValueError):
        return default
    # NaN se trata como dato ausente: si pasa como número, las
    # comparaciones de más abajo fallan en silencio.
    if value != value:
        return default
    return value


def _ahora_utc():
    return datetime.now(timezone.utc).isoformat()


def _send_startup_message():
    if not STARTUP_MESSAGE_ENABLED:
        return
    send_telegram_message(
        f"🤖 SHARK V15 SNIPER INICIADO EN RENDER\n\n"
        f"Timeframe: {TIMEFRAME}\n"
        f"Loop: {LOOP_INTERVAL}s\n"
        f"Activos: {len(ASSETS)}\n"
        f"Base de datos: {_ruta_db()}"
    )


def _ruta_db():
    """Ruta REAL de la base de datos, resuelta a absoluta."""
    try:
        import os
        from config import DATABASE_NAME
        return os.path.abspath(DATABASE_NAME)
    except Exception:
        return "desconocida"


def _send_cycle_ok():
    send_telegram_message(
        f"✅ SHARK V15 SNIPER ACTIVO\n"
        f"Loop ejecutado correctamente.\n"
        f"Timeframe: {TIMEFRAME}\n"
        f"Loop: {LOOP_INTERVAL}s\n"
        f"Activos: {len(ASSETS)}"
    )


def _send_error_message(text):
    try:
        send_telegram_message(f"❌ ERROR SHARK V15\n\n{text}")
    except Exception:
        pass


def _send_mobile_signal_message(
    ticker, signal, data, regime,
    ai_result, context_result, session_result,
    volatility_result, risk_result, trade_setup, final_result,
    veredicto_noticias=None,
):
    last = data.iloc[-1]

    price = _safe_float(last.get("Close"))
    rsi = _safe_float(last.get("rsi"))
    adx = _safe_float(last.get("adx"))
    atr = _safe_float(last.get("atr"))
    ema200 = _safe_float(last.get("ema200"))
    macd = _safe_float(last.get("macd"))
    macd_sig = _safe_float(last.get("macd_signal"))

    entry = _safe_float(trade_setup.get("entry"))
    stop = _safe_float(trade_setup.get("stop_loss"))
    tp = _safe_float(trade_setup.get("take_profit"))
    rr = _safe_float(trade_setup.get("rr_ratio"))
    size = _safe_float(trade_setup.get("position_size"))
    # Antes esta línea decía "5.00 €" fijo en el mensaje. Daba la
    # cifra correcta solo mientras CAPITAL=1000 y RISK=0.005; al
    # cambiar cualquiera de los dos, mentía.
    riesgo = _safe_float(trade_setup.get("risk_amount"), CAPITAL * RISK_PER_TRADE)
    ai_score = _safe_float(ai_result.get("score", 50))
    ctx_score = _safe_float(context_result.get("final_score", 55))

    session_label = "Sí" if session_result.get("allow", True) else "No"
    vol_label = "NORMAL" if volatility_result.get("allow", True) else "BLOQUEADA"
    fuerza = "ALTA" if adx >= 30 else "MEDIA" if adx >= 25 else "BAJA"

    if signal == "BUY":
        motivo = (
            f"Tendencia alcista: precio ({price:.2f}) sobre EMA200 ({ema200:.2f}), "
            f"RSI {rsi:.2f}, MACD {macd:.2f} > señal {macd_sig:.2f}, "
            f"ADX {adx:.2f} confirmando fuerza."
        )
    else:
        motivo = (
            f"Tendencia bajista: precio ({price:.2f}) bajo EMA200 ({ema200:.2f}), "
            f"RSI {rsi:.2f}, MACD {macd:.2f} < señal {macd_sig:.2f}, "
            f"ADX {adx:.2f} confirmando fuerza."
        )

    msg = (
        f"📱 SHARK EJECUCIÓN MÓVIL\n\n"
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
        f"Riesgo estimado: {riesgo:.2f} €\n"
        f"Size: {size:.4f}\n\n"
        f"RSI: {rsi:.2f}\n"
        f"ADX: {adx:.2f}\n"
        f"ATR: {atr:.2f}\n"
        f"Regime: {regime}\n"
        f"Session: {session_result.get('reason', 'OK')}\n"
        f"Volatilidad: {vol_label}\n\n"
        f"AI: {ai_result.get('decision', 'NEUTRAL')} ({ai_score:.1f})\n"
        f"Contexto: {context_result.get('decision', 'NEUTRAL')} ({ctx_score:.1f})\n"
        f"Risk: {'ALLOW' if risk_result.get('allow', True) else 'BLOCK'}\n"
        f"{_linea_noticias(veredicto_noticias)}\n"
        f"Motivo:\n{motivo}"
    )
    send_telegram_message(msg)


def _linea_noticias(veredicto):
    """Linea de noticias para la ficha de Telegram."""
    if not veredicto or veredicto.get("fuente") != "gemini":
        return ""
    icono = {"APROBAR": "🟢", "VETAR": "🔴"}.get(veredicto["veredicto"], "⚪")
    sufijo = " (modo sombra: no bloquea)" if not veredicto.get("bloquea") \
        and veredicto["veredicto"] == "VETAR" else ""
    return (f"Noticias: {icono} {veredicto['veredicto']} "
            f"({veredicto['confianza']}%){sufijo}\n"
            f"  {veredicto['motivo'][:90]}\n")


def comprobar_proveedores():
    """
    Prueba cada proveedor de la cascada al arrancar y devuelve el
    resultado en texto.

    Existe porque las claves de API viven en Render, no en CI: yo
    puedo verificar yfinance y coinbase desde fuera, pero finnhub,
    alpha_vantage y twelve_data solo se pueden probar donde estan
    sus claves. Si el principal se cae y los respaldos tampoco
    funcionan, mas vale saberlo el dia que arranca el bot y no el
    dia que Yahoo cambie la web.
    """
    import data_feed

    cascada = list(data_feed.DATA_PROVIDER_ORDER)
    ticker = ASSETS[0] if ASSETS else "SPY"
    lineas = []
    funcionan = 0

    for proveedor in cascada:
        original = data_feed.DATA_PROVIDER_ORDER
        try:
            data_feed.DATA_PROVIDER_ORDER = [proveedor]
            df, _ = get_data(ticker, TIMEFRAME, PERIOD)
            lineas.append(f"✅ {proveedor}: {len(df)} velas")
            funcionan += 1
        except Exception as e:
            lineas.append(f"❌ {proveedor}: {type(e).__name__}")
        finally:
            data_feed.DATA_PROVIDER_ORDER = original

    return funcionan, len(cascada), lineas


def _log(msg):
    if VERBOSE_LOGS:
        print(msg)


# =========================================================
# CORE
# =========================================================

def run_live_cycle():
    _log("\n=== SHARK V15 SNIPER LIVE CYCLE ===")
    _log(f"Hora: {_ahora_utc()}")

    # Comprobacion barata: una consulta a la base de datos. Solo descarga
    # si el snapshot ha caducado, que es una vez al mes.
    if INSTITUCIONAL_DISPONIBLE and _INST_SERIES_TR is None:
        _refrescar_snapshot_institucional()

    # -------------------------------------------------
    # 1) DESCARGAR DATOS DE TODOS LOS ACTIVOS
    # -------------------------------------------------
    latest_prices = {}
    rangos_barra = {}
    market_data = {}

    for ticker in ASSETS:
        try:
            df, provider = get_data(ticker, TIMEFRAME, PERIOD)
            df = add_indicators(df)

            if df is not None and len(df) >= MIN_BARS:
                ultima = df.iloc[-1]
                latest_prices[ticker] = float(ultima["Close"])
                # El máximo y el mínimo de la vela en curso. Sin
                # esto, el cierre de trades solo ve el Close y se
                # pierde los toques de stop/target intravela.
                rangos_barra[ticker] = {
                    # La apertura entra aqui porque es lo que permite
                    # distinguir un hueco de un toque intravela. Sin
                    # ella el broker ejecutaba los huecos al nivel del
                    # stop, un precio que no se negocio.
                    "open": float(ultima["Open"]),
                    "high": float(ultima["High"]),
                    "low": float(ultima["Low"]),
                }
                market_data[ticker] = df

                # Acumular en el archivo histórico. yfinance solo da
                # 60 días en intradía; guardando cada descarga, esa
                # ventana móvil se convierte en un histórico que
                # crece con el tiempo.
                guardadas = 0
                if HISTORIAL_DISPONIBLE:
                    try:
                        guardadas = guardar_historial(ticker, TIMEFRAME, df)
                    except Exception as e:
                        _log(f"HISTORIAL warning | {ticker}: {e}")

                _log(
                    f"FEED OK | {ticker} | {provider} | {len(df)} velas"
                    + (f" | {guardadas} archivadas" if guardadas else "")
                )
            else:
                velas = 0 if df is None else len(df)
                _log(f"FEED SKIP | {ticker} | datos insuficientes ({velas} < {MIN_BARS})")

        except Exception as e:
            _log(f"FEED ERROR | {ticker} | {e}")

    # -------------------------------------------------
    # 2) CERRAR TRADES ABIERTOS QUE TOCARON SL/TP
    # -------------------------------------------------
    if latest_prices:
        try:
            check_and_close_trades(latest_prices, rangos_barra)
        except Exception as e:
            _log(f"ERROR check_and_close_trades: {e}")

    # -------------------------------------------------
    # 3) EVALUAR SEÑALES PARA CADA ACTIVO
    # -------------------------------------------------
    for ticker, df in market_data.items():
        try:
            last = df.iloc[-1]
            adx_value = _safe_float(last.get("adx"))
            regime = str(detect_market_regime(df)).strip().upper()

            # --- SEÑAL ---
            base_signal = check_signal(df)
            signal = base_signal
            scanner_info = {"signal": "NO_SIGNAL", "reason": "No usado"}

            if base_signal == "NO_SIGNAL":
                scanner_info = scan_smart_opportunity(df)
                if scanner_info.get("signal") in ["BUY", "SELL"]:
                    signal = scanner_info["signal"]

            _log(
                f"{ticker} | Base: {base_signal} | Scanner: {scanner_info.get('signal')} | "
                f"Signal: {signal} | Regime: {regime} | "
                f"Close: {_safe_float(last.get('Close')):.2f} | "
                f"RSI: {_safe_float(last.get('rsi')):.2f} | ADX: {adx_value:.2f}"
            )

            if signal not in ["BUY", "SELL"]:
                continue

            # --- DUPLICADO CHECK (antes de evaluar filtros) ---
            if has_open_trade_for_ticker(ticker):
                _log(f"SKIP | {ticker} | ya tiene trade abierto")
                continue

            # --- TRADE SETUP ---
            # EFECTIVO Y COSTE DECLARADOS. El parametro existia desde la
            # auditoria anterior y NADIE lo llamaba: el dimensionado no
            # miraba si el nominal cabia en la cuenta ni cobraba la
            # ejecucion. Con capital 1.000, precio 100 y ATR 0,10 abria
            # nominal 2.500.
            #
            # `capital` sigue siendo el configurado a proposito: es la base
            # de RIESGO de B1 y cambiarla seria cambiar la estrategia. El
            # plan es explicito: "No cambies senales al reparar
            # contabilidad". El efectivo de la cuenta es una restriccion
            # contable y va por su propio parametro.
            _efectivo = _safe_float_local(get_paper_capital(), CAPITAL)
            trade_setup = calculate_trade_levels(
                df=df,
                signal=signal,
                capital=CAPITAL,
                risk_per_trade=RISK_PER_TRADE,
                efectivo_disponible=_efectivo,
                coste_rel=COSTE_POR_PATA,
            )

            # --- GUARDAR SEÑAL EN DB ---
            if SAVE_ALL_SIGNALS:
                try:
                    save_signal(
                        timestamp=datetime.now().isoformat(),
                        ticker=ticker,
                        signal=signal,
                        regime=regime,
                        df=df,
                        trade=trade_setup,
                    )
                except Exception as e:
                    _log(f"save_signal warning | {ticker}: {e}")

            # --- FILTROS ---
            ai_result = evaluate_signal_quality(ticker, signal)
            context_result = evaluate_trade_context(ticker, signal, regime)
            session_result = evaluate_session_filter(df, regime)
            volatility_result = evaluate_volatility_filter(df, regime)
            risk_result = evaluate_risk_controls(ticker=ticker, signal=signal)

            _log(f"AI | {ticker} | Score: {ai_result.get('score')} | Decision: {ai_result.get('decision')}")
            _log(f"INTEL | {ticker} | Score: {context_result.get('final_score')} | Decision: {context_result.get('decision')}")
            _log(f"SESSION | {ticker} | Allow: {session_result.get('allow')} | {session_result.get('reason')}")
            _log(f"VOL | {ticker} | Allow: {volatility_result.get('allow')} | {volatility_result.get('reason')}")
            _log(f"RISK | {ticker} | Allow: {risk_result.get('allow')} | {risk_result.get('reason')}")

            # --- DECISIÓN FINAL ---
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
                _log(f"--> BLOQUEADO | {ticker} | {final_result.get('reason')}")
                try:
                    from storage import log_risk_event
                    log_risk_event(
                        timestamp=datetime.now().isoformat(),
                        ticker=ticker,
                        signal=signal,
                        event_type="FINAL_BLOCK",
                        reason=final_result.get("reason", "Unknown"),
                    )
                except Exception:
                    pass
                continue

            # --- VERIFICAR POSITION SIZE ---
            if _safe_float(trade_setup.get("position_size")) <= 0:
                _log(f"--> BLOQUEADO | {ticker} | position_size inválido")
                continue

            # --- VERIFICACION DE NOTICIAS ---
            # Va aqui a proposito: solo sobre operaciones que ya
            # pasaron todo lo demas. Consultar noticias de cada
            # señal descartada gastaria la cuota de las APIs en
            # operaciones que nunca se iban a abrir.
            veredicto_noticias = None
            if NOTICIAS_DISPONIBLES:
                try:
                    titulares, fuente_noticias, error_noticias = obtener_noticias(ticker)

                    veredicto_noticias = verificar_operacion(
                        ticker=ticker,
                        direccion=signal,
                        precio=_safe_float(last.get("Close")),
                        regimen=regime,
                        noticias_texto=formatear_para_prompt(titulares),
                    )

                    _log(
                        f"NOTICIAS | {ticker} | {len(titulares)} titulares"
                        f"{f' ({fuente_noticias})' if fuente_noticias else ''} | "
                        f"{veredicto_noticias['veredicto']} "
                        f"({veredicto_noticias['confianza']}%) | "
                        f"{veredicto_noticias['motivo'][:70]}"
                    )
                    if error_noticias:
                        _log(f"NOTICIAS warning | {ticker}: {error_noticias[:100]}")

                    try:
                        from storage import guardar_veredicto_noticias
                        guardar_veredicto_noticias(
                            timestamp=datetime.now().isoformat(),
                            ticker=ticker,
                            signal=signal,
                            regime=regime,
                            precio=_safe_float(last.get("Close")),
                            veredicto=veredicto_noticias["veredicto"],
                            confianza=veredicto_noticias["confianza"],
                            motivo=veredicto_noticias["motivo"],
                            fuente=veredicto_noticias["fuente"],
                            bloqueo_aplicado=veredicto_noticias["bloquea"],
                            n_titulares=len(titulares),
                        )
                    except Exception as e:
                        _log(f"veredicto no guardado | {ticker}: {e}")

                    if veredicto_noticias["bloquea"]:
                        _log(
                            f"--> VETADO POR NOTICIAS | {ticker} | "
                            f"{veredicto_noticias['motivo']}"
                        )
                        continue

                except Exception as e:
                    # Cualquier fallo aqui deja pasar la operacion:
                    # el filtro no es esencial.
                    _log(f"NOTICIAS error | {ticker}: {e}")

            # --- OBSERVACION INSTITUCIONAL (seccion 15 de la spec) ---
            # Va aqui, sobre operaciones que YA pasaron todo lo demas,
            # porque la pregunta que interesa medir es "de las que el
            # bot iba a abrir, cuantas habria vetado cada modulo".
            #
            # En modo OBSERVE (el defecto) esto NO puede bloquear nada:
            # la funcion devuelve False antes de leer ninguna opinion.
            # tests/test_observacion.py lo comprueba corriendo el ciclo
            # completo con la extension apagada y encendida y exigiendo
            # que las decisiones sean identicas.
            if INSTITUCIONAL_DISPONIBLE and _INST_EXTENSION is not None:
                try:
                    bloquear_inst, evaluaciones_inst = evaluar_observacion(
                        ticker=ticker,
                        df=df,
                        signal=signal,
                        regime=regime,
                        base_signal_id=f"{ticker}-{df.index[-1].isoformat()}",
                        extension=_INST_EXTENSION,
                        series_tr=globals().get("_INST_SERIES_TR"),
                        serie_efectivo=globals().get("_INST_EFECTIVO"),
                        ranking=globals().get("_INST_RANKING"),
                        nominal=_safe_float(trade_setup.get("position_size"))
                        * _safe_float(last.get("Close")),
                    )
                    for _ev in evaluaciones_inst:
                        _log(
                            f"INST | {ticker} | {_ev.module_id} | {_ev.status}"
                            f" | {'/'.join(_ev.reason_codes)}"
                            f" | habria_bloqueado="
                            f"{_ev.veta_entrada(exigido=True)}"
                        )
                    for _f in fallos_registro_inst():
                        _log(f"INST | evidencia NO guardada | {_f}")
                    if bloquear_inst:
                        # Solo alcanzable en ENFORCE, nunca en OBSERVE.
                        _log(f"--> VETADO POR EXTENSION | {ticker}")
                        continue
                except Exception as e:
                    # La ampliacion no puede tumbar un ciclo en vivo.
                    _log(f"INST error | {ticker}: {e}")

            # --- ABRIR TRADE ---
            # El orden importa y antes estaba al revés: se mandaba
            # la alerta a Telegram y DESPUÉS se intentaba abrir el
            # trade. Si open_trade lo rechazaba (setup inválido,
            # duplicado) o la base de datos fallaba, la alerta ya
            # estaba enviada. Eso producía avisos de trades que no
            # existían en la base de datos.
            #
            # Ahora: abrir primero, comprobar que quedó guardado de
            # verdad, y solo entonces avisar.
            open_trade(ticker, signal, regime, trade_setup)

            if not has_open_trade_for_ticker(ticker):
                _log(
                    f"--> NO PERSISTIDO | {ticker} | open_trade no dejó el trade "
                    f"en la base de datos, no se envía alerta"
                )
                continue

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
                veredicto_noticias=veredicto_noticias,
            )

        except Exception as e:
            err = f"{ticker} | ERROR live cycle: {e}"
            print(err)
            _send_error_message(err)


def run_live_engine():
    init_db()

    # Tabla propia de la ampliacion. Separada de las del nucleo: si
    # falla, el bot sigue; si se borra, no se pierde ninguna operacion.
    if INSTITUCIONAL_DISPONIBLE:
        try:
            init_observacion()
            _log(f"INST | extension en modo {_INST_EXTENSION.mode} | "
                 f"config {_INST_EXTENSION.config_hash()}")
        except Exception as e:
            _log(f"INST | no se pudo inicializar la observacion: {e}")
        # Sin esto, M02 y M03 no ven ningun dato y registran NO_DATA
        # para siempre sin que nada parezca roto.
        _refrescar_snapshot_institucional()
    else:
        _log(f"INST | ampliacion no disponible: "
             f"{globals().get('_INST_ERROR', 'motivo desconocido')}")
    init_historial()

    print("=" * 50)
    print("SHARK V15 SNIPER - INICIO")
    print("=" * 50)
    print(f"Hora inicio: {_ahora_utc()}")
    print("Entorno: production")
    print(f"Loop interval: {LOOP_INTERVAL} segundos")
    print(f"Activos: {ASSETS}")
    print(f"Timeframe: {TIMEFRAME} | Periodo: {PERIOD} | Min velas: {MIN_BARS}")

    # Si la base de datos está en almacenamiento efímero, todo el
    # histórico desaparece en el próximo reinicio. Hay que verlo al
    # arrancar, no descubrirlo cuando el capital vuelva a 1000.
    print(estado_gemini())

    # Prueba real de la clave de Gemini. El filtro nunca falla
    # ruidosamente por diseño, asi que sin esto una clave mala
    # pasaria desapercibida: parece encendido y no verifica nada.
    try:
        gemini_ok, mensaje_gemini = probar_gemini()
        print(f"  {mensaje_gemini}")
        if not gemini_ok:
            _send_error_message(f"FILTRO DE NOTICIAS\n\n{mensaje_gemini}")
        elif "responde correctamente" in mensaje_gemini:
            send_telegram_message(f"🧠 {mensaje_gemini}")
    except Exception as e:
        print(f"  No se pudo probar Gemini: {e}")

    # Autodiagnostico de proveedores: cuales responden de verdad
    # desde donde corre el bot.
    try:
        ok, total, detalle = comprobar_proveedores()
        print(f"Proveedores: {ok} de {total} responden")
        for linea in detalle:
            print(f"  {linea}")
        if ok == 0:
            _send_error_message(
                "NINGUN PROVEEDOR DE DATOS RESPONDE\n\n"
                + "\n".join(detalle)
                + "\n\nEl bot no va a poder operar."
            )
        elif ok == 1:
            _send_error_message(
                "SIN RESPALDO DE DATOS\n\n"
                + "\n".join(detalle)
                + "\n\nSolo responde un proveedor: si se cae, el bot se para."
            )
    except Exception as e:
        print(f"No se pudo comprobar proveedores: {e}")

    persistente, mensaje_persistencia = comprobar_persistencia()
    print(mensaje_persistencia)
    print("=" * 50)

    if not persistente:
        _send_error_message(
            "ALMACENAMIENTO EFÍMERO\n\n"
            "La base de datos se borrará en el próximo reinicio: se "
            "perderán los trades, el capital y el histórico de velas.\n\n"
            "Hay que montar un disco en Render y poner "
            "DATABASE_NAME=/var/data/shark_v8.db"
        )

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