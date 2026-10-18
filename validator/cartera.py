"""
Backtester de CARTERA.

QUÉ PROBLEMA RESUELVE

El backtester existente corre cada activo por separado y le da
1000 € propios. Eso no es lo que hace el bot:

  - el bot tiene UNA cuenta, no una por activo
  - MAX_OPEN_TRADES limita las posiciones simultáneas de toda la
    cuenta, y el backtest por activo nunca lo aplicaba
  - el tamaño de posición se calcula sobre el capital de la cuenta,
    que sube y baja con TODAS las operaciones, no con las de un
    activo aislado

Con 4 activos y 2 huecos la diferencia es moderada. Con 30 activos
es la diferencia entre un resultado creíble y uno inventado: la
cartera no puede abrir 30 posiciones a la vez.

POR QUÉ IMPORTA MÁS DE LO QUE PARECE

La medición de Robert Carver sobre diversificación entre
instrumentos (qoppac.blogspot.com, marzo 2023) dice que en
seguimiento de tendencia, con pesos iguales, pasar de pocos
instrumentos a muchos multiplica el Sharpe por ~3, y la curva
sigue subiendo a 100 instrumentos. SHARK es un sistema de
tendencia (EMA200 + ADX + MACD).

Eso NO es más ventaja por operación: es la misma ventaja aplicada
más veces y menos correlacionada. Y a diferencia de tocar
umbrales, aplicar las mismas reglas a más instrumentos no es
sobreajustar: es probarlas fuera de muestra.

El límite, también de Carver: la ganancia de Sharpe solo se
convierte en más rentabilidad si se puede escalar al mismo
objetivo de riesgo. Y avisa de que con menos de 50.000 $ el
redondeo a contratos enteros se come el beneficio. Con CFDs, que
admiten fracciones, ese problema concreto desaparece.

OPTIMIZACIÓN VERIFICADA

El motor original pasa df.iloc[:i+1] en cada vela, lo que copia un
DataFrame que crece y da coste cuadrático. Aquí se pasa una
ventana de las últimas VENTANA velas.

El resultado es IDÉNTICO, no aproximado, porque ninguna función de
la cadena mira más atrás de 50 velas y los indicadores vienen ya
calculados como columnas:

  detect_market_regime      rolling(50) + última vela
  evaluate_volatility_filter rolling(50) + última vela
  check_signal              últimas 2 velas
  scan_smart_opportunity    últimas 21 velas
  calculate_trade_levels    última vela

tests/test_cartera.py verifica esa equivalencia numéricamente
contra el motor original en vez de darla por supuesta.
"""

import os
import sys
from collections import Counter

import pandas as pd

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from config import (
    CAPITAL,
    RISK_PER_TRADE,
    MAX_OPEN_TRADES,
    COOLDOWN_HOURS_PER_ASSET,
)

from market_regime import detect_market_regime
from signals import check_signal
from opportunity_scanner import scan_smart_opportunity
from risk_management import calculate_trade_levels
from session_volatility_intelligence import (
    evaluate_session_filter,
    evaluate_volatility_filter,
)
from final_decision_engine import evaluate_final_decision

MIN_WARMUP_BARS = 200
VENTANA = 250           # > 200 de warmup + margen; ver docstring
COSTE_POR_PATA = 0.0008  # 0.08% por pata = 0.16% ida y vuelta


def _ai_neutral():
    return {"score": 55.0, "decision": "NEUTRAL",
            "reason": "Backtest", "exact_count": 0,
            "ticker_count": 0, "signal_count": 0}


def _contexto_neutral():
    return {"ticker_signal_score": 55.0, "ticker_regime_score": 55.0,
            "signal_score": 55.0, "final_score": 55.0,
            "decision": "NEUTRAL", "reason": "Backtest"}


def _riesgo_ok():
    return {"allow": True, "reason": "Controlado por el simulador de cartera"}


def backtest_cartera(
    datos,
    capital_inicial=None,
    max_abiertas=None,
    riesgo_pct=None,
    cooldown_horas=None,
    sl_mult=None,
    tp_mult=None,
    desde=None,
    hasta=None,
):
    """
    Simula UNA cuenta operando todos los activos de `datos`.

    datos: {ticker: DataFrame con indicadores ya calculados}
    desde / hasta: timestamps para recortar el periodo evaluado
                   (el warmup se sigue tomando de antes).

    Devuelve un dict con la curva de capital, las operaciones y las
    estadísticas de la cartera.
    """
    capital_inicial = CAPITAL if capital_inicial is None else capital_inicial
    max_abiertas = MAX_OPEN_TRADES if max_abiertas is None else max_abiertas
    riesgo_pct = RISK_PER_TRADE if riesgo_pct is None else riesgo_pct
    cooldown_horas = (COOLDOWN_HOURS_PER_ASSET
                      if cooldown_horas is None else cooldown_horas)

    if not datos:
        return None

    # Línea de tiempo común: todas las marcas de todos los activos.
    marcas = set()
    for df in datos.values():
        if len(df) > MIN_WARMUP_BARS:
            marcas.update(df.index[MIN_WARMUP_BARS:])
    linea = sorted(marcas)

    if desde is not None:
        linea = [t for t in linea if t >= desde]
    if hasta is not None:
        linea = [t for t in linea if t <= hasta]

    if not linea:
        return None

    # Posición de cada marca dentro de cada activo, para cortar la
    # ventana sin buscar en el índice cada vez.
    posicion = {t: {ts: i for i, ts in enumerate(df.index)}
                for t, df in datos.items()}

    capital = capital_inicial
    abiertas = {}            # ticker -> posición abierta
    cooldown_hasta = {}      # ticker -> marca
    cerradas = []
    curva = []
    pico = capital_inicial
    peor_dd = 0.0

    senales = 0
    permitidas = 0
    bloqueadas = 0
    motivos = Counter()

    for ahora in linea:

        # ---------------------------------------------------------
        # 1) CIERRES
        # ---------------------------------------------------------
        for ticker in list(abiertas.keys()):
            df = datos[ticker]
            i = posicion[ticker].get(ahora)
            if i is None:
                continue   # ese activo no cotiza en esta marca

            vela = df.iloc[i]
            pos = abiertas[ticker]

            alto = float(vela["High"])
            bajo = float(vela["Low"])

            salida = None
            motivo = None

            if pos["signal"] == "BUY":
                if bajo <= pos["stop_loss"]:
                    salida, motivo = pos["stop_loss"], "STOP_LOSS"
                elif alto >= pos["take_profit"]:
                    salida, motivo = pos["take_profit"], "TAKE_PROFIT"
            else:
                if alto >= pos["stop_loss"]:
                    salida, motivo = pos["stop_loss"], "STOP_LOSS"
                elif bajo <= pos["take_profit"]:
                    salida, motivo = pos["take_profit"], "TAKE_PROFIT"

            if salida is None:
                continue

            tam = pos["position_size"]
            if pos["signal"] == "BUY":
                bruto = (salida - pos["entry"]) * tam
            else:
                bruto = (pos["entry"] - salida) * tam

            coste_salida = salida * COSTE_POR_PATA * tam
            # El coste de entrada ya se cobró al abrir; se descuenta
            # del pnl del trade para que las estadísticas incluyan
            # todo el coste y cuadren con la variación de capital.
            capital += bruto - coste_salida
            neto = bruto - coste_salida - pos["coste_entrada"]

            cerradas.append({
                "ticker": ticker,
                "signal": pos["signal"],
                "regime": pos["regime"],
                "entry": pos["entry"],
                "exit": salida,
                "pnl": neto,
                "pnl_bruto": bruto,
                "coste_entrada": pos["coste_entrada"],
                "coste_salida": coste_salida,
                "size": tam,
                "motivo": motivo,
                "abierto_en": str(pos["abierto_en"]),
                "timestamp": str(ahora),
            })

            del abiertas[ticker]
            cooldown_hasta[ticker] = ahora + pd.Timedelta(hours=cooldown_horas)

        # ---------------------------------------------------------
        # 2) APERTURAS
        # ---------------------------------------------------------
        # Se evalua TODO y luego se ordena por puntuacion, en vez
        # de ir llenando huecos por orden del diccionario. Antes,
        # con pocos huecos, los activos que salian primero en el
        # diccionario tenian prioridad sistematica: un sesgo
        # alfabetico disfrazado de estrategia.
        candidatos = []

        for ticker, df in datos.items():
            if ticker in abiertas:
                continue

            i = posicion[ticker].get(ahora)
            if i is None or i < MIN_WARMUP_BARS:
                continue

            # Ventana en lugar del prefijo completo: mismo
            # resultado, coste lineal. Ver docstring.
            ventana = df.iloc[max(0, i - VENTANA + 1): i + 1]
            vela = ventana.iloc[-1]

            regime = str(detect_market_regime(ventana)).strip().upper()

            senal = check_signal(ventana)
            if senal == "NO_SIGNAL":
                scan = scan_smart_opportunity(ventana)
                if scan.get("signal") in ["BUY", "SELL"]:
                    senal = scan["signal"]

            if senal not in ["BUY", "SELL"]:
                continue

            senales += 1

            if ticker in cooldown_hasta and ahora < cooldown_hasta[ticker]:
                bloqueadas += 1
                motivos[f"Cooldown por activo ({cooldown_horas}h)"] += 1
                continue

            decision = evaluate_final_decision(
                ai_result=_ai_neutral(),
                context_result=_contexto_neutral(),
                session_result=evaluate_session_filter(ventana, regime),
                volatility_result=evaluate_volatility_filter(ventana, regime),
                risk_result=_riesgo_ok(),
                adx=float(vela["adx"]),
                regime=regime,
                data=ventana,
                ticker=ticker,
            )

            if decision["decision"] != "ALLOW":
                bloqueadas += 1
                motivos[decision.get("reason", "Desconocido")] += 1
                continue

            permitidas += 1
            candidatos.append((float(decision.get("score", 0.0)),
                               ticker, senal, regime, ventana))

        # Mejor puntuacion primero; el nombre del activo solo
        # desempata, para que el resultado sea reproducible.
        candidatos.sort(key=lambda c: (-c[0], c[1]))

        for score, ticker, senal, regime, ventana in candidatos:
            if len(abiertas) >= max_abiertas:
                # La cuenta esta llena: esta señal era valida y se
                # pierde. Contarlo dice cuantas veces el limite de
                # posiciones simultaneas es el cuello de botella.
                bloqueadas += 1
                motivos[f"Cuenta llena ({max_abiertas} posiciones)"] += 1
                continue

            # El tamaño se calcula sobre el capital ACTUAL de la
            # cuenta, no sobre 1000 fijos por activo.
            setup = calculate_trade_levels(
                df=ventana,
                signal=senal,
                capital=capital,
                risk_per_trade=riesgo_pct,
                sl_mult=sl_mult,
                tp_mult=tp_mult,
            )

            tam = float(setup.get("position_size", 0) or 0)
            if tam <= 0:
                continue

            coste_entrada = setup["entry"] * COSTE_POR_PATA * tam
            capital -= coste_entrada

            abiertas[ticker] = {
                "signal": senal,
                "regime": regime,
                "entry": setup["entry"],
                "stop_loss": setup["stop_loss"],
                "take_profit": setup["take_profit"],
                "position_size": tam,
                "coste_entrada": coste_entrada,
                "abierto_en": ahora,
                "score": score,
            }

        # ---------------------------------------------------------
        # 3) CURVA DE CAPITAL
        # ---------------------------------------------------------
        flotante = 0.0
        for ticker, pos in abiertas.items():
            i = posicion[ticker].get(ahora)
            if i is None:
                continue
            precio = float(datos[ticker].iloc[i]["Close"])
            if pos["signal"] == "BUY":
                flotante += (precio - pos["entry"]) * pos["position_size"]
            else:
                flotante += (pos["entry"] - precio) * pos["position_size"]

        equity = capital + flotante
        curva.append((ahora, equity))

        if equity > pico:
            pico = equity
        if pico > 0:
            dd = (pico - equity) / pico * 100
            if dd > peor_dd:
                peor_dd = dd

    # -------------------------------------------------------------
    # ESTADÍSTICAS
    # -------------------------------------------------------------
    pnls = [t["pnl"] for t in cerradas]
    n = len(pnls)

    ganadoras = [p for p in pnls if p > 0]
    perdedoras = [p for p in pnls if p <= 0]

    bruto_g = sum(ganadoras) if ganadoras else 0.0
    bruto_p = abs(sum(perdedoras)) if perdedoras else 0.0

    anios = (linea[-1] - linea[0]).days / 365.25 if len(linea) > 1 else 0.0

    return {
        "activos": len(datos),
        "max_abiertas": max_abiertas,
        "riesgo_pct": riesgo_pct,
        "capital_start": capital_inicial,
        "capital_final": capital,
        "equity_final": curva[-1][1] if curva else capital_inicial,
        "operaciones": n,
        "ganadoras": len(ganadoras),
        "perdedoras": len(perdedoras),
        "winrate": len(ganadoras) / n * 100 if n else 0.0,
        "expectativa": sum(pnls) / n if n else 0.0,
        "pf": bruto_g / bruto_p if bruto_p > 0 else 0.0,
        "pnl_total": sum(pnls),
        "peor_dd": peor_dd,
        "anios": anios,
        "ops_anio": n / anios if anios > 0 else 0.0,
        "rent_anual_pct": (
            ((curva[-1][1] / capital_inicial) ** (1 / anios) - 1) * 100
            if anios > 0 and curva and curva[-1][1] > 0 else 0.0
        ),
        "senales": senales,
        "permitidas": permitidas,
        "bloqueadas": bloqueadas,
        "motivos": motivos,
        "cerradas": cerradas,
        "curva": curva,
        "abiertas_al_final": len(abiertas),
    }
