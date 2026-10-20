"""
PUERTAS DE ACEPTACION — segunda auditoria (2026-10-20), tabla final de
`PLAN_CLAUDE.md`.

La regla que las gobierna, textual del plan:

    "No se exige un rendimiento favorable para pasar. Se exige el
     comportamiento economico correcto."

Y la que me ataron a la muñeca despues de que escribiera dos criterios con
un `or True`:

    "Prohibidos `or True`, sustituir un error por exito o mover el tiempo de
     decision para satisfacer el validador."

Cada puerta codifica el RESULTADO EXIGIDO por el plan, no lo que el codigo
hace hoy. Se arreglan corrigiendo el motor. Nunca ajustando el esperado.

Alcance de este archivo: las puertas del CAMBIO 1 (eventos, NAV y
metricas). Las puertas V07, V10-V18 y V20-V24 pertenecen a los cambios 2 a
5 y llegan con ellos; mientras no esten, este archivo las declara
PENDIENTE y no las cuenta como aprobadas. Declararlas pendientes es lo que
el plan exige: "Si una capacidad sigue fuera de alcance, bloqueala y
declarala. No la sustituyas por una afirmacion de implementacion completa."

Uso:  python tests/test_puertas.py
"""
import io
import os
import sys
import types

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)
sys.path.insert(0, os.path.join(REPO, "tests"))

os.environ.setdefault("TELEGRAM_TOKEN", "")
os.environ.setdefault("CAPITAL", "1000")
sys.modules.setdefault("yfinance", types.ModuleType("yfinance"))

import _ta_stub
_ta_stub.instalar_si_falta()

import numpy as np
import pandas as pd

PASA = []
FALLA = []
PENDIENTE = []


def check(ident, nombre, cond, detalle=""):
    if cond:
        PASA.append(ident)
        print(f"  PASA       [{ident}] {nombre}")
    else:
        FALLA.append((ident, nombre, detalle))
        print(f"  FALLA      [{ident}] {nombre}")
        if detalle:
            print(f"                     {detalle}")


def pendiente(ident, nombre, cambio):
    PENDIENTE.append((ident, nombre, cambio))
    print(f"  PENDIENTE  [{ident}] {nombre}  (cambio {cambio})")


T0 = pd.Timestamp("2021-06-01", tz="UTC")


def diaria(n, cierres=None, aperturas=None, inicio="2021-01-04"):
    """Sesiones diarias con Open y Close controlados por separado."""
    idx = pd.bdate_range(inicio, periods=n, tz="UTC")
    c = pd.Series([100.0] * n, index=idx, dtype=float)
    o = pd.Series([100.0] * n, index=idx, dtype=float)
    if cierres:
        for i, v in cierres.items():
            c.iloc[i] = float(v)
    if aperturas:
        for i, v in aperturas.items():
            o.iloc[i] = float(v)
    return pd.DataFrame({"Open": o, "High": pd.concat([o, c], axis=1).max(axis=1),
                         "Low": pd.concat([o, c], axis=1).min(axis=1),
                         "Close": c, "Volume": 1e6}, index=idx)


from libro import LibroContado, Instrumento, OperacionNoEjecutable, LibroInvalido
from evaluador.mensual import EvaluadorMensual, Politicas
from evaluador.metricas import por_ano_natural


def politicas_simples(**kw):
    base = dict(capital_inicial=1000.0, coste_rel=0.0, coste_fijo=0.0,
                dias_liquidacion=0, permitir_fraccionado=False, lote=1.0,
                calentamiento_sesiones=0)
    base.update(kw)
    return Politicas(**base)


class TodoEnA:
    id = "PUERTA_TODO_EN_A"
    solo_primera_decision = True

    def __call__(self, vista, elegibles, libro):
        return {"A": 1.0}, {}, {}


class LuegoLaMitad:
    id = "PUERTA_MITAD"

    def __init__(self):
        self.n = 0

    def __call__(self, vista, elegibles, libro):
        self.n += 1
        return ({"A": 1.0} if self.n == 1 else {"A": 0.5}), {}, {}


# =====================================================================
print("\n=== V01-V02: el NAV de cierre no se mezcla con precios de fill ===")
# =====================================================================
# Plan, bucle de eventos: "si evento es cierre de sesion: marcar TODAS las
# posiciones al cierre o a una marca anterior identificada".
#
# Hoy el evaluador valora en el paso 3 (antes de los fills) y el fill
# reescribe `precio_valoracion` con el precio de ejecucion. En un dia con
# operacion, lo comprado hoy queda a la apertura y el resto al cierre.

# 50 sesiones. Decision en la 30 (cierre 100), fill en la 31 (apertura
# 100), y el cierre de la 31 es 110. Con capital 1000 y precio 100 el
# objetivo es exactamente 10 unidades.
serie = diaria(50, cierres={31: 110.0}, aperturas={31: 100.0})
fecha_dec = serie.index[30]
fecha_fill = serie.index[31]

ev = EvaluadorMensual({"A": serie}, politicas_simples(),
                      fechas_decision=[fecha_dec])
r = ev.correr(TodoEnA())
nav = r["_nav"]

try:
    nav_fill = float(nav.loc[fecha_fill])
except Exception as e:
    nav_fill = float("nan")

check("V01", "compra 10 a 100; cierre del mismo dia a 110 -> NAV 1.100",
      abs(nav_fill - 1100.0) < 1e-6,
      f"-> NAV del dia del fill = {nav_fill!r}, exigido 1100.0 "
      f"(la ganancia del dia no se retrasa)")

# V02: venta parcial. Decision 1 compra todo; decision 2 baja al 50%. El
# dia del fill parcial, las unidades que QUEDAN deben valorarse al cierre.
serie2 = diaria(60, cierres={41: 110.0}, aperturas={41: 100.0})
d1, d2 = serie2.index[20], serie2.index[40]
fill2 = serie2.index[41]
ev2 = EvaluadorMensual({"A": serie2}, politicas_simples(),
                       fechas_decision=[d1, d2])
r2 = ev2.correr(LuegoLaMitad())
nav2 = r2["_nav"]
try:
    nav_parcial = float(nav2.loc[fill2])
except Exception:
    nav_parcial = float("nan")
# 10 unidades comparadas a 100 (nav 1000). Al 50%: vende 5 a la apertura
# 100 -> caja 500, quedan 5. Al cierre de 110 esas 5 valen 550 -> 1050.
check("V02", "venta parcial: TODAS las unidades restantes se valoran al cierre",
      abs(nav_parcial - 1050.0) < 1e-6,
      f"-> NAV del fill parcial = {nav_parcial!r}, exigido 1050.0 "
      f"(5 unidades a 110 + 500 de caja)")

# =====================================================================
print("\n=== V03-V05: derechos de cobro tipados e idempotencia ===")
# =====================================================================
# Plan: "En una venta diferida, el nominal neto sale de la posicion y entra
# en un derecho de cobro. No es utilizable todavia, pero forma parte del
# NAV. Al liquidar, baja exactamente ese derecho y sube exactamente caja."

L = LibroContado(1000.0, dias_liquidacion=2)
L.comprar("A", 10, 100.0, momento=T0)
L.valorar("A", 100.0, T0)
nav_antes = L.nav()
L.vender("A", 5, 100.0, momento=T0)
nav_venta = L.nav()
utilizable = L.efectivo_utilizable
check("V03", "venta diferida de 5 a 100: NAV conservado y 500 no gastables",
      abs(nav_antes - 1000.0) < 1e-6 and abs(nav_venta - 1000.0) < 1e-6
      and utilizable < 1e-6,
      f"-> NAV antes {nav_antes}, NAV tras la venta {nav_venta} "
      f"(exigido 1000.0), utilizable {utilizable} (exigido 0.0)")

L.liquidar_pendientes(T0 + pd.Timedelta(days=2))
nav_liq = L.nav()
check("V03b", "al liquidar: baja el derecho y sube la caja, NAV intacto",
      abs(nav_liq - 1000.0) < 1e-6 and abs(L.efectivo_utilizable - 500.0) < 1e-6,
      f"-> NAV {nav_liq} (exigido 1000.0), utilizable {L.efectivo_utilizable} "
      f"(exigido 500.0)")

# V04: dividendo devengado y pagado despues.
D = LibroContado(1000.0)
D.comprar("A", 10, 100.0, momento=T0)
D.valorar("A", 98.0, T0)          # el precio cae por el dividendo
D.dividendo("A", 2.0, momento=T0, momento_pago=T0 + pd.Timedelta(days=5))
nav_dev = D.nav()
D.liquidar_pendientes(T0 + pd.Timedelta(days=5))
nav_pag = D.nav()
check("V04", "dividendo 2 devengado y pagado despues: el NAV no gana otros 2",
      abs(nav_dev - 1000.0) < 1e-6 and abs(nav_pag - 1000.0) < 1e-6,
      f"-> NAV al devengo {nav_dev}, NAV tras el pago {nav_pag} "
      f"(exigido 1000.0 en ambos; si el segundo es 1020 el derecho se "
      f"cobro sin darse de baja)")

# V05: repetir pago y fill con el mismo identificador.
I = LibroContado(1000.0)
try:
    I.comprar("A", 2, 100.0, momento=T0, event_id="fill-1")
    I.comprar("A", 2, 100.0, momento=T0, event_id="fill-1")
    q = I.cantidad("A")
    caja = I.efectivo
    ok_fill = abs(q - 2.0) < 1e-9 and abs(caja - 800.0) < 1e-6
    det_fill = f"-> cantidad {q} (exigido 2.0), caja {caja} (exigido 800.0)"
except TypeError as e:
    ok_fill = False
    det_fill = f"-> el libro no acepta event_id: {e}"
check("V05", "repetir un fill con el mismo event_id no duplica ejecucion",
      ok_fill, det_fill)

I2 = LibroContado(1000.0)
I2.comprar("A", 10, 100.0, momento=T0)
I2.valorar("A", 98.0, T0)
try:
    I2.dividendo("A", 2.0, momento=T0,
                 momento_pago=T0 + pd.Timedelta(days=5), event_id="div-1")
    I2.dividendo("A", 2.0, momento=T0,
                 momento_pago=T0 + pd.Timedelta(days=5), event_id="div-1")
    I2.liquidar_pendientes(T0 + pd.Timedelta(days=5))
    I2.liquidar_pendientes(T0 + pd.Timedelta(days=9))
    ok_div = abs(I2.nav() - 1000.0) < 1e-6 and abs(I2.efectivo - 20.0) < 1e-6
    det_div = (f"-> NAV {I2.nav()} (exigido 1000.0), caja {I2.efectivo} "
               f"(exigido 20.0)")
except TypeError as e:
    ok_div = False
    det_div = f"-> el dividendo no acepta event_id: {e}"
check("V05b", "repetir un pago con el mismo event_id no duplica caja ni derechos",
      ok_div, det_div)

# =====================================================================
print("\n=== V06: retornos anuales reconciliados ===")
# =====================================================================
# Plan: retorno_año[y] = NAV_ultimo_de_y / NAV_ultimo_anterior_a_y - 1
nav_anos = pd.Series(
    [100.0, 110.0, 121.0],
    index=pd.DatetimeIndex(["2020-12-31", "2021-01-04", "2021-12-31"], tz="UTC"))
res = por_ano_natural(nav_anos)
r2021 = res.get("2021", {}).get("retorno")
check("V06", "100 en diciembre y 110 la primera sesion de enero -> +10% en 2021",
      r2021 is not None and abs(r2021 - 0.21) < 1e-9,
      f"-> 2021 = {r2021!r}, exigido 0.21 (121/100-1). Si sale 0.1 se perdio "
      f"el tramo 31-dic -> primera sesion de enero")

# Identidad de factores: el producto de los factores anuales tiene que
# reproducir NAV_final / NAV_inicial.
from evaluador.metricas import identidad_de_factores
ident = identidad_de_factores(nav_anos, anual=res)
check("V06b", "el producto de los factores anuales reproduce NAV_final/NAV_inicial",
      bool(ident.get("coincide")),
      f"-> producto {ident.get('producto_de_factores')}, objetivo "
      f"{ident.get('nav_final_sobre_inicial')}, error "
      f"{ident.get('error_absoluto')}")
ident_corto = identidad_de_factores(
    pd.Series([100.0, 105.0, 110.0],
              index=pd.DatetimeIndex(["2020-12-31", "2021-06-30", "2022-01-03"],
                                     tz="UTC")))
check("V06d", "la identidad de factores aguanta tambien con años parciales",
      bool(ident_corto.get("coincide")),
      f"-> error {ident_corto.get('error_absoluto')}")

# Y un año con una sola observacion no puede desaparecer en silencio.
nav_corto = pd.Series(
    [100.0, 105.0, 110.0],
    index=pd.DatetimeIndex(["2020-12-31", "2021-06-30", "2022-01-03"], tz="UTC"))
res_corto = por_ano_natural(nav_corto)
check("V06c", "un año con una sola observacion se informa, no se borra",
      set(res_corto) >= {"2020", "2021", "2022"},
      f"-> años informados {sorted(res_corto)}, exigidos 2020, 2021 y 2022 "
      f"(marcados parciales, no eliminados)")

# =====================================================================
print("\n=== V08-V09: capacidades no implementadas se rechazan ===")
# =====================================================================
# Plan: "Manten primero la version de una sola moneda; rechaza un
# instrumento de otra moneda mientras no exista FX implementado. No
# deduzcas paridad 1:1."
F = LibroContado(1000.0, moneda_cuenta="USD")
F.registrar_instrumento(Instrumento("EUREKA", moneda="EUR"))
try:
    F.comprar("EUREKA", 1, 100.0, momento=T0)
    rechazado = False
except (OperacionNoEjecutable, LibroInvalido):
    rechazado = True
check("V08", "instrumento EUR en cuenta USD sin FX: rechazo antes de tocar el libro",
      rechazado and abs(F.efectivo - 1000.0) < 1e-6
      and F.cantidad("EUREKA") <= 0,
      f"-> rechazado={rechazado}, caja {F.efectivo} (exigido 1000.0), "
      f"cantidad {F.cantidad('EUREKA')} (exigido 0)")

try:
    politicas_simples(politica_terminal="LIQUIDAR_CON_FX_Y_RETENCION")
    err_terminal = False
except Exception:
    err_terminal = True
check("V09", "politica terminal no implementada: error explicito de configuracion",
      err_terminal,
      "-> Politicas acepto una politica terminal que nadie implementa")

# =====================================================================
print("\n=== V07, V10, V11, V22: admision de ordenes ===")
# =====================================================================
# Plan, cambio 2: "si exige ejecucion completa y no cabe: rechazar toda la
# orden" y "reservar por order_id de forma atomica".

# V07 / oraculo O06. Capital 100, se piden 2 unidades a 100 (hacen falta
# 200) con la reduccion DESACTIVADA.
P = LibroContado(100.0)
try:
    P.comprar("A", 2, 100.0, momento=T0, reducir_si_no_cabe=False)
    rechazo_total = False
except OperacionNoEjecutable:
    rechazo_total = True
check("V07", "compra impagable con reduccion desactivada: rechazo completo",
      rechazo_total and P.cantidad("A") <= 0 and abs(P.efectivo - 100.0) < 1e-9,
      f"-> rechazada={rechazo_total}, cantidad {P.cantidad('A')} (exigido 0), "
      f"caja {P.efectivo} (exigido 100.0). Si compro 1 unidad, la bandera "
      f"solo se honraba cuando no cabia NADA")

# V10 / oraculo O14. Objetivo 40% fijado con el cierre a 100; la sesion
# siguiente ABRE a 200. Cuatro unidades a 200 son el 80% del NAV, y el
# tope se declaro duro.
from limites_cartera import LimitesCartera
serie_g = diaria(60, cierres={}, aperturas={})
serie_g.loc[serie_g.index[21]:, ["Open", "High", "Low", "Close"]] = 200.0
d_g = serie_g.index[20]
f_g = serie_g.index[21]
lim = LimitesCartera(max_por_instrumento=0.4, max_por_grupo=0.4,
                     grupos={"A": "grupo_A"})
ev_g = EvaluadorMensual({"A": serie_g},
                        politicas_simples(limites=lim, permitir_fraccionado=False,
                                          lote=1.0),
                        fechas_decision=[d_g])
r_g = ev_g.correr(TodoEnA())
try:
    peso_real = float(r_g["_ledger_diario"].loc[f_g, "expuesto"])
except Exception as e:
    peso_real = float("nan")
check("V10", "objetivo 40% y apertura al doble: la admision no acepta el 80%",
      peso_real <= 0.4 + 1e-6,
      f"-> peso ejecutado {peso_real!r}, tope duro declarado 0.40. El tope "
      f"se aplicaba al objetivo y nadie lo recalculaba con el precio "
      f"ejecutable")

# V11: dos ordenes compiten por el saldo. Reservas por order_id.
Rv = LibroContado(1000.0)
try:
    Rv.reservar_orden("ord-1", 600.0)
    try:
        Rv.reservar_orden("ord-2", 600.0)
        segunda_rechazada = False
    except OperacionNoEjecutable:
        segunda_rechazada = True
    Rv.liberar_orden("ord-1")
    Rv.liberar_orden("ord-1")          # repetir no libera dos veces
    tras_liberar = Rv.reservado
    Rv.reservar_orden("ord-2", 600.0)
    ok_res = (segunda_rechazada and abs(tras_liberar) < 1e-9
              and abs(Rv.reservado - 600.0) < 1e-9)
    det_res = (f"-> segunda rechazada={segunda_rechazada}, reservado tras "
               f"liberar dos veces {tras_liberar} (exigido 0.0), reservado "
               f"final {Rv.reservado} (exigido 600.0)")
except AttributeError as e:
    ok_res = False
    det_res = f"-> no hay reservas por order_id: {e}"
check("V11", "dos ordenes por el mismo saldo: reserva atomica y liberacion individual",
      ok_res, det_res)

# V22: SELL con cero unidades al contado.
Sv = LibroContado(1000.0)
antes_mov = len(Sv.movimientos)
try:
    mv = Sv.vender("A", 5, 100.0, momento=T0)
    sin_corto = Sv.cantidad("A") >= -1e-9
    ejecuto_cero = mv is not None and mv.cantidad_ejecutada <= 1e-9
    quedo_registro = len(Sv.movimientos) > antes_mov
    motivo = bool(getattr(mv, "rechazo", ""))
except OperacionNoEjecutable:
    sin_corto = ejecuto_cero = quedo_registro = motivo = False
check("V22", "SELL con cero unidades: senal registrada, orden rechazada, ningun corto",
      sin_corto and ejecuto_cero and quedo_registro and motivo,
      f"-> sin corto={sin_corto}, ejecuto cero={ejecuto_cero}, "
      f"registro={quedo_registro}, motivo de rechazo={motivo}")

# =====================================================================
print("\n=== V23: el ejecutor del CORE responde a comisiones y capital ===")
# =====================================================================
# Plan: "Cambian comisiones o capital -> Cambian PnL neto/capacidad en
# ejecutor del core". Hoy paper_broker hace pnl = (salida-entrada)*size,
# bruto, y capital += pnl: las comisiones no tocan el capital del bot.

try:
    from paper_broker import contabilizar_cierre
    r0 = contabilizar_cierre("BUY", entry=100.0, exit_price=110.0, size=10.0,
                             capital_antes=1000.0, coste_rel=0.0, coste_fijo=0.0)
    r1 = contabilizar_cierre("BUY", entry=100.0, exit_price=110.0, size=10.0,
                             capital_antes=1000.0, coste_rel=0.0008,
                             coste_fijo=0.0)
    # Bruto 100. Comisiones = (1000 + 1100) * 0,0008 = 1,68. Neto 98,32.
    ok_pnl = (abs(r0["neto"] - 100.0) < 1e-9
              and abs(r1["neto"] - 98.32) < 1e-9
              and abs(r1["capital_despues"] - 1098.32) < 1e-9)
    det_pnl = (f"-> sin coste neto {r0['neto']}, con 8 pb neto {r1['neto']} "
               f"(exigido 98.32) y capital {r1['capital_despues']} "
               f"(exigido 1098.32)")
except ImportError as e:
    ok_pnl = False
    det_pnl = f"-> el core no tiene contabilidad de cierre con comisiones: {e}"
except Exception as e:
    ok_pnl = False
    det_pnl = f"-> {type(e).__name__}: {e}"
check("V23", "las comisiones mueven el PnL neto y el capital del core",
      ok_pnl, det_pnl)

# La capacidad tiene que responder al efectivo, no solo al capital
# configurado.
from risk_management import calculate_trade_levels
_i = pd.date_range("2026-01-02 14:30", periods=300, freq="30min", tz="UTC")
_c = pd.Series([100.0] * 300, index=_i)
df_cap = pd.DataFrame({"Open": _c, "High": _c + 0.05, "Low": _c - 0.05,
                       "Close": _c, "Volume": 1e6}, index=_i)
df_cap["atr"] = 0.10
s_rico = calculate_trade_levels(df=df_cap, signal="BUY", capital=1000,
                                risk_per_trade=0.005,
                                efectivo_disponible=1000.0, coste_rel=0.0008)
s_pobre = calculate_trade_levels(df=df_cap, signal="BUY", capital=1000,
                                 risk_per_trade=0.005,
                                 efectivo_disponible=100.0, coste_rel=0.0008)
nom_r = float(s_rico["position_size"]) * float(s_rico["entry"])
nom_p = float(s_pobre["position_size"]) * float(s_pobre["entry"])
check("V23b", "la capacidad responde al efectivo disponible",
      nom_p < nom_r and nom_p <= 100.0 + 1e-6,
      f"-> nominal con 1000 de efectivo {nom_r:.2f}, con 100 {nom_p:.2f} "
      f"(tiene que caber en 100)")

# Y el cableado: la funcion existia y NADIE la llamaba con efectivo. Esto
# comprueba la llamada real en el core, no la firma.
_src_le = io.open(os.path.join(REPO, "live_engine.py"), encoding="utf-8").read()
_i0 = _src_le.find("calculate_trade_levels(")
_llamada = _src_le[_i0:_i0 + 420] if _i0 >= 0 else ""
check("V23c", "el core llama al dimensionado declarando efectivo y coste",
      "efectivo_disponible" in _llamada and "coste_rel" in _llamada,
      f"-> la llamada del core no pasa efectivo ni coste; el parametro "
      f"existia y nadie lo usaba")

# =====================================================================
print("\n=== Puertas de cambios posteriores ===")
# =====================================================================
pendiente("V12", "snapshot caducado con el proceso en marcha", 3)
pendiente("V13", "299 velas maduras mas una abierta", 3)
pendiente("V14", "recuperacion posterior al corte historico", 3)
pendiente("V15", "bootstrap n=10 bloque=5 sin truncar", 4)
pendiente("V16", "dos cortes, 25 decisiones futuras unicas", 4)
pendiente("V17", "pronostico bruto perfecto con costes de 0,2 R", 4)
pendiente("V18", "mismo coste proporcional, distinta distancia/precio", 4)
pendiente("V19", "fondo liquidado con cobro diferido", 3)
pendiente("V20", "falta la descarga de un activo congelado", 3)
pendiente("V21", "precio ausente o NAV invalido: calidad visible", 1)
pendiente("V24", "reejecucion con los mismos artefactos", 5)

print("\n" + "=" * 70)
print(f"PUERTAS: {len(PASA)} pasan, {len(FALLA)} FALLAN, "
      f"{len(PENDIENTE)} pendientes de su cambio")
print("=" * 70)
if FALLA:
    print("\nComportamiento economico que el motor todavia no cumple:\n")
    for ident, nombre, _ in FALLA:
        print(f"  [{ident}] {nombre}")
    print("\nSe arreglan corrigiendo el motor, nunca ajustando el esperado.")
print("=" * 70)

sys.exit(1 if FALLA else 0)
