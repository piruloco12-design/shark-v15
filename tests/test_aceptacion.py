"""
PRUEBAS DE ACEPTACION — hoy FALLAN a proposito.

Vienen de la auditoría externa del 2026-10-19 (tabla 4.7) y de mis propias
reproducciones de sus hallazgos. Cada una codifica un contrato ECONOMICO,
no el comportamiento actual del código.

La regla que las gobierna, textual de la auditoría:

    "No resolver una prueba cambiando su esperado para que coincida con el
     error actual. El esperado procede del contrato económico."

Así que estas pruebas se arreglan corrigiendo el motor, nunca ajustando el
valor esperado. Mientras fallen, miden exactamente cuánto falta.

Por qué existen separadas de las demás: las otras 352 comprobaciones pasan
y aun así el evaluador daba cifras económicas falsas. Eran pruebas de
contabilidad interna y de contratos, y ninguna llamaba al ejecutor con un
caso cuyo resultado correcto se conociera de antemano. Esa es la lección:
una igualdad aritmética aislada no valida el motor que usa Shark.

En CI este archivo corre sin bloquear, para que el hueco sea visible en cada
corrida en vez de quedar escondido. Cuando pasen todas, pasa a bloquear.

Uso:  python tests/test_aceptacion.py
"""
import os
import sys
import types

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)
sys.path.insert(0, os.path.join(REPO, "tests"))
sys.path.insert(0, os.path.join(REPO, "validator"))

os.environ.setdefault("TELEGRAM_TOKEN", "")
os.environ.setdefault("CAPITAL", "1000")
sys.modules.setdefault("yfinance", types.ModuleType("yfinance"))

import _ta_stub
_ta_stub.instalar_si_falta()

import pandas as pd

PASA = []
FALLA = []


def check(ident, nombre, cond, detalle=""):
    if cond:
        PASA.append(ident)
        print(f"  PASA   [{ident}] {nombre}")
    else:
        FALLA.append((ident, nombre, detalle))
        print(f"  FALLA  [{ident}] {nombre}")
        if detalle:
            print(f"                 {detalle}")


def mensual(valores, inicio="2020-01-31"):
    """Una fila por mes, para que cada fila sea un cierre mensual."""
    idx = pd.date_range(inicio, periods=len(valores), freq="ME", tz="UTC")
    c = pd.Series([float(v) for v in valores], index=idx)
    return pd.DataFrame({"Open": c, "High": c, "Low": c, "Close": c,
                         "Volume": 1e6}, index=idx)


# =====================================================================
print("\n=== A) El benchmark tiene que ser comprar y mantener de verdad ===")
# =====================================================================

import validator.experimento_institucional as E

# Sin calentamiento, para aislar la contabilidad de la señal.
E.LOOKBACK, E.SKIP, E.VENTANA_VOL = 0, 0, 2

N = 40
sube_y_vuelve = [100.0, 200.0, 100.0] + [100.0] * (N - 3)
plano = [100.0] * N

E.COSTE_POR_PATA = 0.0
m = E.simular({"A": mensual(sube_y_vuelve), "B": mensual(plano)}, modo="comprar")
final = m["patrimonio_final"] if m else None

# Comprar 0,5 de A y 0,5 de B y NO tocar nada: A acaba donde empezó, B no se
# movió. El patrimonio acaba igual que empezó. Esto es aritmética, no una
# opinión sobre mercados.
check("A1", "comprar y mantener con cantidades fijas termina en 1,0000",
      final is not None and abs(final - 1.0) < 1e-6,
      f"-> devuelve {final}. 1,1250 es rebalanceo mensual 50/50, otra "
      f"estrategia distinta.")

E.COSTE_POR_PATA = 0.0008
mc = E.simular({"A": mensual(sube_y_vuelve), "B": mensual(plano)}, modo="comprar")
check("A2", "comprar y mantener con costes sigue en 1,0000 menos la compra inicial",
      mc is not None and 0.998 < mc["patrimonio_final"] <= 1.0,
      f"-> devuelve {mc['patrimonio_final'] if mc else None}")

# Y si se quiere medir rebalanceo mensual, que exista como variante APARTE
# y que cobre sus operaciones.
check("A3", "existe una variante de rebalanceo equiponderado que cobra cada "
      "rebalanceo",
      hasattr(E, "MODO_REBALANCEO_EQUIPONDERADO"),
      "-> no existe. Hace falta separar 'comprar y mantener' de "
      "'rebalanceo equiponderado', y cobrar el segundo.")

if mc is not None:
    # Un rebalanceo mensual real sobre A que dobla y vuelve tiene que
    # registrar MAS de dos intenciones.
    check("A4", "un benchmark que rebalancea registra mas de 2 intenciones",
          mc["intenciones"] > 2,
          f"-> {mc['intenciones']} intenciones: solo las compras iniciales")


# =====================================================================
print("\n=== B) El libro tiene que ser una cuenta al contado ===")
# =====================================================================

from risk_management import calculate_trade_levels

idx = pd.date_range("2026-01-02 14:30", periods=300, freq="30min", tz="UTC")
c = pd.Series([100.0] * 300, index=idx)
df_plano = pd.DataFrame({"Open": c, "High": c + 0.05, "Low": c - 0.05,
                         "Close": c, "Volume": 1e6}, index=idx)
df_plano["atr"] = 0.10

setup = calculate_trade_levels(df=df_plano, signal="BUY", capital=1000,
                               risk_per_trade=0.005)
nominal = float(setup["position_size"]) * float(setup["entry"])

check("B1", "el nominal abierto no supera el capital de una cuenta al contado",
      nominal <= 1000.0 + 1e-6,
      f"-> nominal {nominal:.2f} con capital 1000 "
      f"({nominal/1000:.2f}x). El limite de perdida al stop se respeta "
      f"({float(setup['risk_amount']):.2f}), pero el nominal no cabe.")

check("B2", "el calculo de tamano recibe el efectivo disponible, no solo el capital",
      "efectivo_disponible" in calculate_trade_levels.__code__.co_varnames,
      "-> la firma no conoce el efectivo: no puede reservarlo")


# =====================================================================
print("\n=== C) Los stops no pueden ejecutar a precios que no existieron ===")
# =====================================================================

from paper_broker import _decidir_cierre

# Largo con stop en 99. La barra siguiente abre en 95 y su maximo es 95.
# No se pudo vender a 99: ese precio no se negocio.
cerrado, precio_salida, motivo = _decidir_cierre(
    "BUY", stop_loss=99.0, take_profit=110.0, price=95.0, high=95.0, low=95.0)

check("C1", "un hueco por debajo del stop ejecuta en la barra, no en el stop",
      cerrado and precio_salida <= 95.0 + 1e-9,
      f"-> sale a {precio_salida} cuando el maximo de la barra fue 95. "
      f"Con 5 unidades compradas a 100: {(precio_salida-100)*5:+.2f} en vez "
      f"de {(95-100)*5:+.2f}")

# Simetrico para un corto contrafactual: hueco por ENCIMA del stop.
cerrado_s, precio_s, _ = _decidir_cierre(
    "SELL", stop_loss=101.0, take_profit=90.0, price=105.0, high=105.0,
    low=105.0)
check("C2", "lo mismo en el lado corto del contrafactual",
      cerrado_s and precio_s >= 105.0 - 1e-9,
      f"-> sale a {precio_s} cuando el minimo de la barra fue 105")

check("C3", "el cierre acepta la apertura de la barra, que es lo que decide "
      "un hueco",
      "open" in _decidir_cierre.__code__.co_varnames
      or "apertura" in _decidir_cierre.__code__.co_varnames,
      "-> la firma solo recibe price/high/low: sin la apertura no se puede "
      "modelar un hueco")


# =====================================================================
print("\n=== D) Métricas con el nombre y la unidad correctos ===")
# =====================================================================

E.COSTE_POR_PATA = 0.0
un_salto = [100.0, 110.0] + [110.0] * (N - 2)
md = E.simular({"A": mensual(un_salto)}, modo="comprar")

if md:
    serie_d = mensual(un_salto)
    anos_reales = (serie_d.index[-1] - serie_d.index[0]).days / 365.25
    cagr_correcto = md["patrimonio_final"] ** (1 / anos_reales) - 1
    check("D1", "el CAGR usa el intervalo completo, incluido el primer periodo",
          abs(md["retorno_anual"] - cagr_correcto) < 1e-6,
          f"-> motor {md['retorno_anual']*100:.4f}% vs correcto "
          f"{cagr_correcto*100:.4f}%. El primer retorno esta en el "
          f"patrimonio pero su tiempo no se cuenta.")

    check("D2", "el Sharpe se calcula sobre retornos diferenciales",
          "sharpe_diferencial" in md or "referencia_sharpe" in md,
          "-> el campo 'sharpe' es CAGR/volatilidad: ni resta una "
          "referencia ni usa la media de retornos")

    check("D3", "se informa la caida maxima DIARIA, no solo en puntos mensuales",
          "max_drawdown_diario" in md,
          "-> solo hay max_drawdown sobre la curva mensual; una caida "
          "intramensual no aparece")

    check("D4", "la expectativa monetaria y el multiplo de riesgo van separados",
          "pnl_moneda" in md or "R_neto" in md,
          "-> la 'expectativa R' de los experimentos es media de P&L en "
          "unidades del simulador, no un multiplo de riesgo")


# =====================================================================
print("\n=== E) Calendario y causalidad del mensual ===")
# =====================================================================

from institucional.vista import cierres_mensuales

completo = pd.DataFrame(
    {"Close": range(400)},
    index=pd.date_range("2025-01-01", periods=400, freq="B", tz="UTC"))
cortado = completo.loc[completo.index <= pd.Timestamp("2026-02-13", tz="UTC")]
m_cortado = cierres_mensuales(cortado)

check("E1", "una serie que acaba a mitad de mes no genera un cierre mensual ahi",
      m_cortado.index[-1].day >= 20 or m_cortado.index[-1].month != 2,
      f"-> elige {m_cortado.index[-1].date()} como cierre mensual. Hay que "
      f"distinguir valoracion final de fecha valida de decision.")

check("E2", "la decision y la ejecucion tienen momentos distintos",
      hasattr(E, "EJECUTAR_EN_EVENTO_POSTERIOR"),
      "-> simular() decide con un cierre y empieza el retorno en ese mismo "
      "cierre: ejecuta al precio que acaba de observar")

check("E3", "el tramo de test conserva el historial anterior para calentar",
      "historial_previo" in E.partir.__code__.co_varnames,
      "-> partir() recorta el pasado del test, asi que vuelve a esperar un "
      "ano de calentamiento en vez de usar el pasado para los indicadores")


# =====================================================================
print("\n=== F) Vigencia y trazabilidad de los snapshots ===")
# =====================================================================

from institucional.modulos import Ranking, m03_contexto, _version_datos
from institucional import contratos as C

decision = pd.Timestamp("2026-10-19", tz="UTC")

viejo = Ranking(seleccionados=("AAA",), scores={"AAA": 0.2}, excluidos={},
                as_of=int(pd.Timestamp("2025-02-01", tz="UTC").timestamp()),
                dataset_version="v")
ev_viejo = m03_contexto("AAA", viejo, "s", "h", decision, signal="BUY")
check("F1", "un ranking de 626 dias es STALE, no READY",
      ev_viejo.status == C.STALE,
      f"-> {ev_viejo.status}, permite entrada {ev_viejo.allow_new_entry}, "
      f"y renueva vigencia hasta "
      f"{pd.Timestamp(ev_viejo.valid_until, unit='s', tz='UTC').date()}")

futuro = Ranking(seleccionados=("AAA",), scores={"AAA": 0.2}, excluidos={},
                 as_of=int(pd.Timestamp("2026-10-29", tz="UTC").timestamp()),
                 dataset_version="v")
ev_futuro = m03_contexto("AAA", futuro, "s", "h", decision, signal="BUY")
check("F2", "un ranking con datos posteriores a la decision se rechaza",
      ev_futuro.status != C.READY,
      f"-> {ev_futuro.status}: max(as_of, ahora) desplaza la referencia al "
      f"futuro y mata la comprobacion de causalidad")

base = pd.DataFrame(
    {"Close": [100.0, 105.0, 110.0]},
    index=pd.date_range("2026-01-01", periods=3, freq="D", tz="UTC"))
alterado = base.copy()
alterado.iloc[1, 0] = 500.0
check("F3", "cambiar un precio intermedio cambia la version de los datos",
      _version_datos(base) != _version_datos(alterado),
      f"-> mismo identificador {_version_datos(base)}: solo usa longitud, "
      f"extremos y ultimo cierre")

import live_engine
check("F4", "existe una tarea que alimenta las series de M02/M03",
      getattr(live_engine, "_INST_SERIES_TR", None) is not None
      or hasattr(live_engine, "construir_snapshot_institucional"),
      "-> _INST_SERIES_TR/_INST_EFECTIVO/_INST_RANKING son None y solo se "
      "rellenan en tests/_replay_runner.py. Por la ruta entregada, M02 y "
      "M03 registran NO_DATA siempre.")


# =====================================================================
print("\n=== G) La caja y los cortos ===")
# =====================================================================

import inspect
fuente_simular = inspect.getsource(E.simular)
check("G1", "la caja no invertida no cobra el rendimiento de un ETF",
      "cash_diario" not in fuente_simular
      or "POLITICA_CAJA" in fuente_simular,
      "-> la caja libre recibe el rendimiento de BIL, cuando la cuenta de "
      "Brian no esta remunerada. Si se quiere comprar BIL, modelarlo como "
      "posicion con ordenes y costes.")

check("G2", "una apertura corta no entra en el libro ejecutable al contado",
      hasattr(E, "LIBRO_EJECUTABLE_SOLO_LARGOS")
      or "OPEN_SHORT" in fuente_simular,
      "-> no hay separacion entre libro ejecutable y contrafactual: "
      "los SELL se simulan como cortos en el mismo libro")


print("\n" + "=" * 68)
print(f"ACEPTACION: {len(PASA)} pasan, {len(FALLA)} FALLAN")
print("=" * 68)
if FALLA:
    print("\nLo que falta para que las cifras economicas sean creibles:\n")
    for ident, nombre, _ in FALLA:
        print(f"  [{ident}] {nombre}")
    print("\nEstas pruebas se arreglan corrigiendo el motor, nunca ajustando")
    print("el valor esperado. Mientras fallen, ninguna cifra economica de")
    print("resultados/ debe citarse como medicion.")
print("=" * 68)

sys.exit(1 if FALLA else 0)
