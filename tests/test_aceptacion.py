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

# El evaluador viejo (validator/experimento_institucional.py) se conserva
# como artefacto identificado, con sus resultados marcados invalidos en
# resultados/LEEME_RESULTADOS_INVALIDADOS.md. Los criterios economicos se
# miden contra la version NUEVA, que es lo que la auditoria pide: "corregir
# ... en una version nueva", no parchear la vieja.
from evaluador.mensual import (
    ComprarYMantener, EvaluadorMensual, M03Momentum, Politicas,
    RebalanceoEquiponderado,
)


def serie_b(valores, inicio="2018-01-01"):
    idx = pd.date_range(inicio, periods=len(valores), freq="B", tz="UTC")
    c = pd.Series([float(v) for v in valores], index=idx)
    return pd.DataFrame({"Open": c, "High": c, "Low": c, "Close": c,
                         "Volume": 1e6}, index=idx)


# El oraculo: A sube a 200 y vuelve a 100; B plano. El movimiento ocurre
# DESPUES del calentamiento, para que el periodo evaluado lo contenga.
N = 600
A_SUBE_VUELVE = [100.0] * 300 + [200.0] * 100 + [100.0] * (N - 400)
B_PLANO = [100.0] * N

pol_sin_costes = Politicas(capital_inicial=1000.0, coste_rel=0.0,
                           calentamiento_sesiones=253)
ev = EvaluadorMensual({"A": serie_b(A_SUBE_VUELVE), "B": serie_b(B_PLANO)},
                      pol_sin_costes)

r_bh = ev.correr(ComprarYMantener())
check("A1", "comprar y mantener con cantidades fijas termina donde empezo",
      abs(r_bh["retorno_total"]) < 1e-6,
      f"-> retorno total {r_bh['retorno_total']*100:+.6f}%. A acaba donde "
      f"empezo y B no se movio: el patrimonio no puede cambiar.")

r_reb = ev.correr(RebalanceoEquiponderado())
check("A2", "el rebalanceo equiponderado existe como estrategia aparte y "
      "termina en 1,1250",
      abs(r_reb["retorno_total"] - 0.125) < 1e-6,
      f"-> {r_reb['retorno_total']*100:+.4f}%")

check("A3", "comprar y mantener solo opera una vez",
      r_bh["decisiones"] == 1 and r_bh["intenciones"] == 2,
      f"-> {r_bh['decisiones']} decisiones, {r_bh['intenciones']} intenciones")

check("A4", "el rebalanceo registra MAS intenciones que la compra inicial",
      r_reb["intenciones"] > 2,
      f"-> {r_reb['intenciones']} intenciones en "
      f"{r_reb['decisiones']} decisiones")

pol_con_costes = Politicas(capital_inicial=1000.0, coste_rel=0.0008,
                           calentamiento_sesiones=253)
ev_c = EvaluadorMensual({"A": serie_b(A_SUBE_VUELVE), "B": serie_b(B_PLANO)},
                        pol_con_costes)
r_reb_c = ev_c.correr(RebalanceoEquiponderado())
check("A5", "con costes, cada rebalanceo se cobra y baja el NAV",
      r_reb_c["comisiones_moneda"] > 0
      and r_reb_c["retorno_total"] < r_reb["retorno_total"],
      f"-> comisiones {r_reb_c['comisiones_moneda']:.4f}, retorno "
      f"{r_reb_c['retorno_total']*100:+.4f}% vs {r_reb['retorno_total']*100:+.4f}% "
      f"sin costes")


# =====================================================================
print("\n=== B) El libro tiene que ser una cuenta al contado ===")
# =====================================================================

from risk_management import calculate_trade_levels

idx = pd.date_range("2026-01-02 14:30", periods=300, freq="30min", tz="UTC")
c = pd.Series([100.0] * 300, index=idx)
df_plano = pd.DataFrame({"Open": c, "High": c + 0.05, "Low": c - 0.05,
                         "Close": c, "Volume": 1e6}, index=idx)
df_plano["atr"] = 0.10

# B1 se conserva INTACTO: sin declarar efectivo, el tamano es el de
# siempre. Eso es lo que pide la auditoria al preservar la linea base.
setup_b1 = calculate_trade_levels(df=df_plano, signal="BUY", capital=1000,
                                  risk_per_trade=0.005)
nominal_b1 = float(setup_b1["position_size"]) * float(setup_b1["entry"])

# La variante al contado SI declara el efectivo, y entonces el nominal
# tiene que caber.
setup_cash = calculate_trade_levels(df=df_plano, signal="BUY", capital=1000,
                                    risk_per_trade=0.005,
                                    efectivo_disponible=1000.0,
                                    coste_rel=0.0008)
nominal_cash = float(setup_cash["position_size"]) * float(setup_cash["entry"])

check("B1", "la variante al contado no abre nominal por encima del efectivo",
      nominal_cash <= 1000.0 + 1e-6,
      f"-> nominal {nominal_cash:.2f} con 1000 disponibles")

check("B2", "el calculo de tamano acepta el efectivo disponible",
      "efectivo_disponible" in calculate_trade_levels.__code__.co_varnames,
      "-> la firma no conoce el efectivo: no puede reservarlo")

check("B3", "el recorte por efectivo queda DICHO en el setup, no escondido",
      "recorte_por_efectivo" in setup_cash
      and setup_cash["recorte_por_efectivo"]["nominal_por_riesgo"] > 1000,
      "-> un tamano pequeno sin explicacion parece decision de "
      "volatilidad cuando fue falta de dinero")

check("B4", "B1 queda intacto: sin declarar efectivo, el tamano no cambia",
      abs(nominal_b1 - 2500.0) < 1.0
      and "recorte_por_efectivo" not in setup_b1,
      f"-> nominal B1 {nominal_b1:.2f}. Preservar la linea base significa "
      f"que su comportamiento no se toca.")


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

from evaluador import metricas as MET

# Un solo salto del +10% y luego plano: el CAGR tiene que repartir ese
# 10% sobre TODO el intervalo, no sobre el que empieza despues del salto.
nav_salto = pd.Series(
    [1.0] * 10 + [1.1] * 240,
    index=pd.date_range("2020-01-01", periods=250, freq="B", tz="UTC"))
anos = (nav_salto.index[-1] - nav_salto.index[0]).days / 365.25
cagr_correcto = 1.1 ** (1 / anos) - 1
check("D1", "el CAGR usa el intervalo completo, incluido el primer periodo",
      abs(MET.cagr(nav_salto) - cagr_correcto) < 1e-9,
      f"-> {MET.cagr(nav_salto)*100:.6f}% vs {cagr_correcto*100:.6f}%")

sh = MET.sharpe(nav_salto, tasa_libre_periodica=0.0)
check("D2", "el Sharpe sale de retornos diferenciales y declara su referencia",
      sh.get("sharpe") is not None and "referencia" in sh
      and "media_diferencial_periodica" in sh,
      f"-> {sh}")

# Una caida intramensual que el fin de mes no ve.
fechas = pd.date_range("2020-01-01", periods=70, freq="B", tz="UTC")
valores = [1.0] * 70
valores[35] = 0.70          # un dia a mitad de mes
nav_hueco = pd.Series(valores, index=fechas)
dd_diario = MET.drawdown_maximo(nav_hueco)
dd_mensual = MET.drawdown_maximo(nav_hueco.resample("ME").last().dropna())
check("D3", "la caida maxima diaria ve lo que la mensual no ve",
      dd_diario < dd_mensual - 1e-9,
      f"-> diaria {dd_diario*100:.2f}% vs mensual {dd_mensual*100:.2f}%")

check("D4", "el resumen separa comisiones, nominal y coste sobre nominal",
      all(k in r_reb_c for k in ("comisiones_moneda", "nominal_ejecutado",
                                 "coste_sobre_nominal_pb",
                                 "coste_por_intencion_moneda")),
      f"-> faltan campos en el resumen")

# Una serie que empieza en julio: 2020 es parcial por definicion.
nav_parcial = pd.Series(
    [1.0 + i * 0.001 for i in range(400)],
    index=pd.date_range("2020-07-01", periods=400, freq="B", tz="UTC"))
anos_parcial = MET.por_ano_natural(nav_parcial)
check("D5", "los anos parciales se marcan como parciales",
      anos_parcial.get("2020", {}).get("completo") is False,
      f"-> {[(k, v['completo']) for k, v in anos_parcial.items()]}")


# =====================================================================
print("\n=== E) Calendario y causalidad del mensual ===")
# =====================================================================

# Serie que acaba a mitad de mes: ese dia vale para VALORAR, no para
# decidir un rebalanceo mensual.
hasta_dia_13 = pd.date_range("2018-01-01", "2020-02-13", freq="B", tz="UTC")
c13 = pd.Series([100.0] * len(hasta_dia_13), index=hasta_dia_13)
df13 = pd.DataFrame({"Open": c13, "High": c13, "Low": c13, "Close": c13,
                     "Volume": 1e6}, index=hasta_dia_13)
ev13 = EvaluadorMensual({"A": df13, "B": df13.copy()}, pol_sin_costes)
ultima_decision = ev13.fechas_decision[-1] if ev13.fechas_decision else None
check("E1", "una serie que acaba a mitad de mes no genera decision ahi",
      ultima_decision is None or ultima_decision.month != 2
      or ultima_decision.day >= 20,
      f"-> ultima decision {ultima_decision}")

# La orden decidida en el cierre de mes se ejecuta en una fecha POSTERIOR.
dec = r_reb["_decisiones"]
con_ordenes = [d for d in dec if d.ordenes]
posteriores = all(d.fecha_ejecucion > d.fecha_decision
                  for d in con_ordenes if d.fecha_ejecucion is not None)
check("E2", "la ejecucion ocurre DESPUES de la decision, no al mismo cierre",
      bool(con_ordenes) and posteriores,
      f"-> {len(con_ordenes)} decisiones con ordenes; "
      f"{'todas posteriores' if posteriores else 'alguna al mismo cierre'}")

check("E3", "el calentamiento se separa del periodo evaluado",
      ev.inicio_evaluacion > ev.fechas[0]
      and r_bh["inicio"] >= str(ev.inicio_evaluacion.date()),
      f"-> calentamiento hasta {ev.inicio_evaluacion.date()}, "
      f"NAV desde {r_bh['inicio']}")


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
      hasattr(live_engine, "_refrescar_snapshot_institucional"),
      "-> _INST_SERIES_TR/_INST_EFECTIVO/_INST_RANKING eran None y solo se "
      "rellenaban en tests/_replay_runner.py. Por la ruta de produccion, "
      "M02 y M03 registraban NO_DATA siempre.")

from institucional import snapshot as SNAP
check("F5", "el snapshot persiste y sobrevive a un reinicio",
      hasattr(SNAP, "guardar") and hasattr(SNAP, "cargar_ultimo"),
      "-> no hay persistencia: un reinicio perderia el snapshot")

# F6 y F7 se comprueban EJECUTANDO la tarea sobre una base temporal, no
# mirando si una cadena aparece en el codigo. La primera version de estas
# dos llevaba "or True" al final, lo que las convertia en tautologias:
# pasaban siempre. Es justo lo que la auditoria prohibe, "no resolver una
# prueba cambiando su esperado para que coincida".
import tempfile as _tmp

_db_prev = os.environ.get("DATABASE_NAME")
_db_tmp = _tmp.NamedTemporaryFile(suffix=".db", delete=False)
_db_tmp.close()
try:
    SNAP.DATABASE_NAME = _db_tmp.name

    def _descarga_falsa(ticker):
        n = 400
        idx = pd.date_range("2024-06-03", periods=n, freq="B", tz="UTC")
        deriva = {"AAA": 1.002, "BBB": 1.0005, "CCC": 0.999}.get(ticker, 1.00007)
        c = pd.Series([100 * (deriva ** i) * (1 + 0.01 * ((i * 7919 % 101) / 100 - 0.5))
                       for i in range(n)], index=idx)
        return pd.DataFrame({"Open": c, "High": c * 1.001, "Low": c * 0.999,
                             "Close": c, "Volume": 1e6}, index=idx), "sintetico"

    _ahora = pd.Timestamp("2026-01-15", tz="UTC")
    _snap = SNAP.construir(["AAA", "BBB", "CCC"], config_hash="h", k=2,
                           descargar=_descarga_falsa, ahora=_ahora)
    SNAP.guardar(_snap)

    # F6: pedirlo con una decision ANTERIOR a los datos no devuelve nada.
    _antes = SNAP.cargar_ultimo(pd.Timestamp("2025-01-01", tz="UTC"))
    _despues = SNAP.cargar_ultimo(_ahora)
    check("F6", "cargar_ultimo no devuelve un snapshot posterior a la decision",
          _antes is None and _despues is not None,
          f"-> con decision anterior devolvio {_antes is not None}, "
          f"con decision posterior {_despues is not None}")

    # F7: consultarlo dos veces en fechas distintas NO mueve la vigencia.
    _v1 = SNAP.cargar_ultimo(pd.Timestamp("2026-01-20", tz="UTC"))["valid_until"]
    _v2 = SNAP.cargar_ultimo(pd.Timestamp("2026-02-05", tz="UTC"))["valid_until"]
    check("F7", "la vigencia sale del calendario del snapshot, no de la consulta",
          _v1 == _v2 == _snap["valid_until"],
          f"-> {_v1} vs {_v2} vs {_snap['valid_until']}")

    # Y que el ranking se pueda reconstruir identico tras el reinicio.
    _rk = SNAP.a_ranking(_despues)
    check("F8", "el ranking se reconstruye identico desde la base de datos",
          list(_rk.seleccionados) == _snap["ranking"]["seleccionados"]
          and _rk.as_of == _snap["ranking"]["as_of"],
          f"-> {_rk.seleccionados} vs {_snap['ranking']['seleccionados']}")
finally:
    os.unlink(_db_tmp.name)
    if _db_prev is not None:
        SNAP.DATABASE_NAME = _db_prev


# =====================================================================
print("\n=== G) La caja y los cortos ===")
# =====================================================================

check("G1", "la politica de caja esta declarada y por defecto NO remunera",
      pol_sin_costes.politica_caja == "SIN_REMUNERAR",
      f"-> {pol_sin_costes.politica_caja}")

from libro import LibroContado, OperacionNoEjecutable
L = LibroContado(1000.0, permitir_fraccionado=True)
try:
    L.abrir_corto("AAA", 5, 100)
    corto_rechazado = False
except OperacionNoEjecutable:
    corto_rechazado = True
check("G2", "el libro ejecutable al contado no admite abrir cortos",
      corto_rechazado, "-> permitio un corto")

# Salida completa exacta: vender todo lo que se tiene no deja polvo.
# Redondear a lote una venta TOTAL dejaba residuos de 1e-9 dentro, y con
# eso M03 con K=5 acababa con 17 posiciones y generaba una orden de venta
# imposible cada mes, que inflaba las intenciones y los rechazos (775 de
# 1801). El CAGR apenas se movia, pero los diagnosticos que la auditoria
# pide quedaban falseados.
L_polvo = LibroContado(10000.0, permitir_fraccionado=True)
L_polvo.comprar("AAA", 1.59813219176543, 100.0)
L_polvo.comprar("AAA", 2.40186780823457, 100.0)
_q = L_polvo.cantidad("AAA")
L_polvo.vender("AAA", _q, 100.0)
check("B5", "vender toda la posicion la cierra del todo, sin polvo",
      "AAA" not in L_polvo.posiciones and L_polvo.cantidad("AAA") == 0.0,
      f"-> queda {L_polvo.cantidad('AAA'):.12f} tras vender {_q:.12f}")

L.comprar("AAA", 5.0, 100.0)
v = L.vender("AAA", 3.0, 100.0)
check("G3", "una venta que reduce un largo existente SI es ejecutable",
      v.cantidad_ejecutada == 3.0 and abs(L.cantidad("AAA") - 2.0) < 1e-9,
      f"-> vendio {v.cantidad_ejecutada}, queda {L.cantidad('AAA')}")

v2 = L.vender("AAA", 100.0, 100.0)
check("G4", "vender mas de lo disponible no abre un corto: se limita",
      v2.cantidad_ejecutada <= 2.0 + 1e-9 and L.cantidad("AAA") <= 1e-9,
      f"-> vendio {v2.cantidad_ejecutada}, queda {L.cantidad('AAA')}")


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
