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
from evaluador.mensual import (EvaluadorMensual, Politicas,
                               SinDatosSuficientes)
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


class _AmbosActivos:
    id = "PUERTA_AMBOS"
    solo_primera_decision = True

    def __call__(self, vista, elegibles, libro):
        return {"VIVO": 0.5, "MUERTO": 0.5}, {}, {}


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

print("\n=== CF1, CF2: comision minima por orden (hallazgo propio) ===")
# =====================================================================
# No esta en la tabla del plan: salio al medir la sensibilidad a la
# tarifa sobre el panel real. Con comision minima por orden el libro se
# iba a EFECTIVO NEGATIVO y abortaba la corrida entera.

# CF1: una venta cuyo importe no cubre la comision fija se rechaza.
# Fraccionado: es el regimen del experimento (permitir_fraccionado=True,
# lote=0.0) y el unico en el que una venta puede quedar por debajo de la
# comision fija. Con lote 1,0 vender 0,3 redondea a cero y la prueba
# pasaria sin tocar el fallo.
Cf = LibroContado(1000.0, permitir_fraccionado=True)
Cf.comprar("A", 10, 2.0, momento=T0, coste_rel=0.0008, coste_fijo=0.0)
caja_antes = Cf.efectivo
mv_cf = Cf.vender("A", 0.3, 2.0, momento=T0, coste_rel=0.0008, coste_fijo=2.0)
check("CF1", "venta cuyo importe no cubre la comision fija: rechazada",
      mv_cf.cantidad_ejecutada <= 1e-12
      and abs(Cf.efectivo - caja_antes) < 1e-12
      and abs(Cf.cantidad("A") - 10.0) < 1e-9
      and "antieconomica" in (mv_cf.rechazo or ""),
      f"-> ejecutada {mv_cf.cantidad_ejecutada}, caja {Cf.efectivo} "
      f"(antes {caja_antes}), motivo {mv_cf.rechazo!r}")

# CF2: y el efectivo NUNCA se va a negativo con comision fija. Antes se
# iba, y la invariante lo cazaba abortando la corrida sin decir de donde.
Cf2 = LibroContado(100.0, permitir_fraccionado=True)
Cf2.comprar("B", 20, 1.0, momento=T0, coste_rel=0.0008, coste_fijo=1.0)
for _ in range(25):
    Cf2.vender("B", 0.5, 1.0, momento=T0, coste_rel=0.0008, coste_fijo=1.0)
try:
    Cf2.comprobar_invariantes()
    invariantes_ok = Cf2.efectivo >= -1e-9
    det_cf2 = f"-> efectivo {Cf2.efectivo}, cantidad {Cf2.cantidad('B')}"
except LibroInvalido as e:
    invariantes_ok = False
    det_cf2 = f"-> {e}"
check("CF2", "25 ventas pequenas con comision fija no dejan caja negativa",
      invariantes_ok, det_cf2)

# CF3: y el rechazo es una POLITICA, no una ley. Correccion de lo que
# afirme: lo presente como consecuencia del contrato sin margen, y no lo
# es. El caso exacto de la tercera revision: caja 999,40, una unidad a
# 0,60, comision 2. Ejecutar deja 998,00, que no es negativa. El contrato
# contable para T+0 es caja_utilizable + ingreso - costes >= 0.
_res = {}
for _pol in ("RECHAZAR", "EJECUTAR_SI_HAY_CAJA"):
    _L = LibroContado(1000.0, permitir_fraccionado=True,
                      politica_venta_antieconomica=_pol)
    _L.comprar("A", 1, 0.6, momento=T0)
    _m = _L.vender("A", 1, 0.6, momento=T0, coste_fijo=2.0)
    _res[_pol] = (_m.cantidad_ejecutada, round(_L.efectivo, 6),
                  _L.cantidad("A"))
check("CF3", "el rechazo de una venta antieconomica es politica declarada",
      _res["RECHAZAR"] == (0.0, 999.4, 1.0)
      and _res["EJECUTAR_SI_HAY_CAJA"] == (1.0, 998.0, 0.0),
      f"-> RECHAZAR {_res['RECHAZAR']}, EJECUTAR_SI_HAY_CAJA "
      f"{_res['EJECUTAR_SI_HAY_CAJA']}. Exigido (0, 999.4, 1) y (1, 998.0, 0)")

# Y las dos formulas de coste, con el algebra de la tercera revision.
from libro import comision_explicita
check("CF4", "fijo aditivo y minimo por orden son formulas DISTINTAS",
      abs(comision_explicita(200, 0.0008, 0.50, 0.0) - 0.66) < 1e-12
      and abs(comision_explicita(200, 0.0008, 0.0, 0.50) - 0.50) < 1e-12,
      f"-> N=200, 8 pb: aditivo "
      f"{comision_explicita(200, 0.0008, 0.50, 0.0)} (exigido 0.66), minimo "
      f"{comision_explicita(200, 0.0008, 0.0, 0.50)} (exigido 0.50). Medi la "
      f"aditiva y la llame minimo")

# =====================================================================
print("\n=== V12, V13, V14: datos y snapshots ===")
# =====================================================================
import tempfile
from pathlib import Path
from institucional import snapshot as SNAP

_idx300 = pd.bdate_range("2025-01-01", periods=300, tz="UTC")
_c300 = pd.Series(np.linspace(100.0, 160.0, 300), index=_idx300)
_df300 = pd.DataFrame({"Open": _c300, "High": _c300 * 1.01,
                       "Low": _c300 * 0.99, "Close": _c300,
                       "Volume": 1e6}, index=_idx300)

# V13 / oraculo O11. La ultima vela diaria aun no ha cerrado: su dia no ha
# acabado. Eso NO justifica tirar las 299 maduras.
try:
    snap13 = SNAP.construir(["A", "B"],
                            descargar=lambda _: (_df300.copy(), "fixture"),
                            ahora=_idx300[-1])
    filas = min(len(df) for df in snap13["series"].values())
    obs = pd.Timestamp(snap13["observation_time"], unit="s", tz="UTC")
    ok13 = filas == 299 and obs == _idx300[-2]
    det13 = (f"-> filas usadas {filas} (exigido 299), observacion "
             f"{obs.date()} (exigido {_idx300[-2].date()})")
except Exception as e:
    ok13 = False
    det13 = (f"-> {type(e).__name__}: {str(e)[:90]}. Rechaza el snapshot "
             f"entero por una vela abierta y tira 299 filas maduras")
check("V13", "299 velas maduras mas una abierta: se usa la vista madura",
      ok13, det13)

# Y la referencia de efectivo tiene que recortarse igual que los activos:
# si conserva velas posteriores, la senal mira el futuro por ese lado.
try:
    ef = snap13.get("efectivo")
    ok13b = ef is None or len(ef) == 0 or ef.index[-1] <= obs
    det13b = (f"-> ultima vela del efectivo "
              f"{(ef.index[-1].date() if ef is not None and len(ef) else None)}, "
              f"observacion {obs.date()}")
except Exception as e:
    ok13b = False
    det13b = f"-> {type(e).__name__}: {e}"
check("V13b", "la referencia de efectivo se recorta a la misma observacion",
      ok13b, det13b)

# V14 / oraculo O12. Un snapshot RECUPERADO 20 dias despues del corte no
# demuestra que revision se conocia entonces.
_db_vieja = SNAP.DATABASE_NAME
with tempfile.TemporaryDirectory() as _tmp:
    SNAP.DATABASE_NAME = str(Path(_tmp) / "snapshots.sqlite")
    try:
        _obs = _idx300[-1]
        _rec = _obs + pd.Timedelta(days=20)
        _snap14 = SNAP.construir(["A", "B"],
                                 descargar=lambda _: (_df300.copy(), "fixture"),
                                 ahora=_rec)
        SNAP.guardar(_snap14)
        _corte = _obs + pd.Timedelta(days=2)
        _cargado = SNAP.cargar_ultimo(_corte)
        ok14 = _cargado is None
        det14 = (f"-> devuelto={_cargado is not None} para una decision del "
                 f"{_corte.date()} con recuperacion del {_rec.date()}: "
                 f"se filtraba por disponibilidad y no por recuperacion")
    except Exception as e:
        ok14 = False
        det14 = f"-> {type(e).__name__}: {str(e)[:90]}"
    finally:
        SNAP.DATABASE_NAME = _db_vieja
check("V14", "un snapshot recuperado tras el corte no se da como captura anterior",
      ok14, det14)

# V14b: y la ruta estricta NO puede ser vacua. Un filtro que rechaza TODO
# no es estricto, esta roto. La primera version de este filtro comparaba
# la columna `creado_en` (TEXT ISO) con un entero: en SQLite eso no da
# error, da siempre falso, asi que no habria devuelto un snapshot jamas y
# M02/M03 habrian vuelto a NO_DATA permanente en produccion sin avisar.
_db_vieja3 = SNAP.DATABASE_NAME
with tempfile.TemporaryDirectory() as _tmp3:
    SNAP.DATABASE_NAME = str(Path(_tmp3) / "snapshots.sqlite")
    try:
        _obs_b = _idx300[-1]
        _rec_b = _obs_b + pd.Timedelta(days=1)
        _snap14b = SNAP.construir(["A", "B"],
                                  descargar=lambda _: (_df300.copy(), "fixture"),
                                  ahora=_rec_b)
        # Captura declarada como creada el dia de su recuperacion.
        _snap14b["creado_en"] = SNAP._creado_texto(int(_rec_b.timestamp()))
        SNAP.guardar(_snap14b)
        _corte_b = _obs_b + pd.Timedelta(days=10)
        _ok_b = SNAP.cargar_ultimo(_corte_b)
        ok14b = _ok_b is not None
        det14b = (f"-> la ruta estricta devolvio {_ok_b is not None} para un "
                  f"snapshot recuperado y creado el {_rec_b.date()} con corte "
                  f"el {_corte_b.date()}: si sale None, el filtro rechaza todo")
    except Exception as e:
        ok14b = False
        det14b = f"-> {type(e).__name__}: {str(e)[:90]}"
    finally:
        SNAP.DATABASE_NAME = _db_vieja3
check("V14b", "la ruta estricta SI devuelve una captura anterior al corte",
      ok14b, det14b)

# V12 / oraculo O15. Caducidad comprobada tambien con la cache llena.
_src_lc = io.open(os.path.join(REPO, "live_engine.py"), encoding="utf-8").read()
_i_ciclo = _src_lc.find("def run_live_cycle")
# Solo CODIGO: un comentario que explique el fallo no es el fallo. La
# primera version de esta puerta buscaba el texto en bruto y la hacia
# fallar el comentario que documentaba el arreglo.
_codigo = [l.split("#", 1)[0] for l in
           _src_lc[_i_ciclo:_i_ciclo + 1600].splitlines()]
_trozo = "\n".join(_codigo)
check("V12", "el ciclo comprueba la caducidad aunque la cache este llena",
      "_INST_SERIES_TR is None" not in _trozo
      and "_refrescar_snapshot_institucional()" in _trozo,
      "-> el refresco esta condicionado a que la cache este VACIA: una vez "
      "cargado, el snapshot no se renueva hasta reiniciar el bot")

_hace_falta, _motivo = (True, "")
try:
    _db_vieja2 = SNAP.DATABASE_NAME
    with tempfile.TemporaryDirectory() as _tmp2:
        SNAP.DATABASE_NAME = str(Path(_tmp2) / "s.sqlite")
        try:
            _s = SNAP.construir(["A"],
                                descargar=lambda _: (_df300.copy(), "fixture"),
                                ahora=_idx300[-1] + pd.Timedelta(days=1))
            SNAP.guardar(_s)
            _lejos = _idx300[-1] + pd.Timedelta(days=400)
            _hace_falta, _motivo = SNAP.hace_falta_actualizar(_lejos)
        finally:
            SNAP.DATABASE_NAME = _db_vieja2
except Exception as e:
    _motivo = f"{type(e).__name__}: {e}"
check("V12b", "un snapshot caducado se detecta por calendario, no por reloj",
      bool(_hace_falta), f"-> hace_falta={_hace_falta}, motivo: {_motivo}")

# =====================================================================
print("\n=== V19, V20, V21: bajas declaradas y calidad visible ===")
# =====================================================================
# Plan: "Una liquidacion declarada necesita evento, precio/cobro, fecha y
# politica de reinversion. Sin esa informacion, marca incertidumbre; no
# inventes perdida total ni venta al ultimo cierre."

# V19: fondo liquidado con cobro diferido.
Lq = LibroContado(1000.0)
Lq.comprar("FONDO", 5, 100.0, momento=T0)     # caja 500, posicion 500
Lq.valorar("FONDO", 100.0, T0)
nav_pre = Lq.nav()
mv = Lq.liquidar_instrumento("FONDO", 90.0, T0,
                             T0 + pd.Timedelta(days=5),
                             event_id="liq-1", fuente="hecho relevante CNMV")
nav_evento = Lq.nav()
q_tras = Lq.cantidad("FONDO")
der = Lq.derechos
Lq.liquidar_pendientes(T0 + pd.Timedelta(days=5))
nav_cobro = Lq.nav()
# 5 unidades a 90 = 450 de derecho. El NAV baja 50, que es la perdida
# DECLARADA por el evento, no una inventada.
check("V19", "fondo liquidado: unidades fuera, derecho dentro, y se cobra",
      q_tras <= 0 and abs(der - 450.0) < 1e-9
      and abs(nav_evento - 950.0) < 1e-9 and abs(nav_cobro - 950.0) < 1e-9
      and abs(Lq.efectivo - 950.0) < 1e-9,
      f"-> NAV antes {nav_pre}, tras el evento {nav_evento} (exigido 950.0), "
      f"tras cobrar {nav_cobro}, unidades {q_tras}, derecho {der} "
      f"(exigido 450.0), caja final {Lq.efectivo}")

# Y la idempotencia del evento: repetirlo no cobra dos veces.
Lq.liquidar_instrumento("FONDO", 90.0, T0, T0 + pd.Timedelta(days=5),
                        event_id="liq-1", fuente="hecho relevante CNMV")
check("V19b", "repetir el evento de liquidacion no cobra dos veces",
      abs(Lq.nav() - 950.0) < 1e-9 and abs(Lq.efectivo - 950.0) < 1e-9,
      f"-> NAV {Lq.nav()}, caja {Lq.efectivo} (exigido 950.0)")

# Una politica de reinversion no implementada se rechaza en vez de
# ejecutarse como si existiera.
Lq2 = LibroContado(1000.0)
Lq2.comprar("F2", 5, 100.0, momento=T0)
try:
    Lq2.liquidar_instrumento("F2", 90.0, T0, politica_reinversion="REINVERTIR",
                             fuente="prospecto")
    rechazo_pol = False
except OperacionNoEjecutable:
    rechazo_pol = True
check("V19c", "politica de reinversion no implementada: error explicito",
      rechazo_pol and Lq2.cantidad("F2") == 5,
      f"-> rechazada={rechazo_pol}, unidades {Lq2.cantidad('F2')} (exigido 5)")

# V20: falta la descarga de un activo congelado.
import universo_congelado as UC
with tempfile.TemporaryDirectory() as _tmpu:
    _ruta = str(Path(_tmpu) / "universo.json")
    _tickers20 = [f"T{i:02d}" for i in range(12)]
    UC.congelar(_tickers20, "prueba de puertas", ruta=_ruta)
    _antes = UC.cargar(_ruta)
    # Falta la descarga de uno: T11 no devuelve datos en esta corrida.
    _est = UC.comprobar(set(_tickers20[:-1]), ruta=_ruta,
                        fecha_comprobacion="2026-10-20")
    _despues = UC.cargar(_ruta)
    _sigue = "T11" in _despues["instrumentos"]
    _denominador = len(_despues["instrumentos"]) == len(_antes["instrumentos"])
check("V20", "falta la descarga de un congelado: se marca, no se borra",
      _sigue and _denominador,
      f"-> T11 sigue en el universo={_sigue}, denominador intacto="
      f"{_denominador} ({len(_despues['instrumentos'])} vs "
      f"{len(_antes['instrumentos'])})")

# V21: precio ausente -> calidad visible, la fecha NO se elimina.
_idxv = pd.bdate_range("2024-01-01", periods=70, tz="UTC")
_viva = diaria(70, inicio="2024-01-01")
_muerta = _viva.iloc[:10].copy()
_pol21 = politicas_simples()
_ev21 = EvaluadorMensual({"VIVO": _viva, "MUERTO": _muerta}, _pol21,
                         fechas_decision=[_viva.index[1]])
_r21 = _ev21.correr(TodoEnA.__call__.__self__ if False else _AmbosActivos())
check("V21", "precio ausente: calidad visible y el NAV se declara no fiable",
      _r21.get("nav_fiable") is False and _r21.get("dias_no_evaluables", 0) > 0
      and len(_r21["incidencias_valoracion"]) > 0,
      f"-> nav_fiable={_r21.get('nav_fiable')}, dias no evaluables="
      f"{_r21.get('dias_no_evaluables')}, incidencias="
      f"{len(_r21.get('incidencias_valoracion', []))}")

# Y con EXIGIR_EVENTO el motor se niega a dar un numero.
try:
    EvaluadorMensual({"VIVO": _viva, "MUERTO": _muerta},
                     politicas_simples(politica_baja="EXIGIR_EVENTO"),
                     fechas_decision=[_viva.index[1]]).correr(_AmbosActivos())
    _nego = False
except SinDatosSuficientes:
    _nego = True
check("V21b", "con EXIGIR_EVENTO no se emite NAV sin evidencia del evento",
      _nego, "-> emitio un NAV con una posicion sin precio ni evento")

# =====================================================================
print("\n=== V15, V16, V17, V18: M01 ===")
# =====================================================================
from institucional import m01_estimador as M01

# V15 / oraculo O09. Bloques CIRCULARES: diez valores por replica y sin
# sesgo. `v[i:i+bloque]` trunca al final del array, asi que un bloque que
# empieza en 7 da [7,8,9] en vez de envolver a [7,8,9,0,1]: se pierden los
# valores bajos y la media sube.
_v10 = list(range(10))
try:
    _medias = M01.medias_remuestreadas(_v10, bloque=5, remuestras=20000,
                                       semilla=90210)
    _long_ok = getattr(M01, "LONGITUD_ULTIMA_MUESTRA", None)
    ok15 = (len(_medias) == 20000
            and abs(float(np.mean(_medias)) - 4.5) < 0.05)
    det15 = (f"-> media de las medias {float(np.mean(_medias)):.4f}, "
             f"exigida 4.5 (la media verdadera). Con bloques truncados "
             f"sale ~5.62")
except AttributeError as e:
    ok15 = False
    det15 = f"-> no hay remuestreo expuesto para comprobarlo: {e}"
check("V15", "bootstrap n=10 bloque=5: bloques circulares y sin sesgo",
      ok15, det15)

try:
    _idxs = [M01._indices_bloques_circulares(10, 5,
             np.random.default_rng(i)) for i in range(50)]
    ok15b = all(len(x) == 10 for x in _idxs)
    det15b = f"-> longitudes {sorted(set(len(x) for x in _idxs))}, exigida [10]"
except AttributeError as e:
    ok15b = False
    det15b = f"-> no existe el generador circular: {e}"
check("V15b", "cada replica tiene exactamente n valores, no menos",
      ok15b, det15b)

# V16 y V17. 12 operaciones de entrenamiento, 10 en la primera ventana y
# 15 en la segunda. Pronostico bruto PERFECTO y coste de 0,2 R.
def _op(i, cuando, bruto_R=1.0, coste_R=0.2):
    riesgo = 10 * 2.0            # cantidad 10, entrada 100, stop 98
    return M01.Operacion(
        id=f"op{i:03d}", abierta_en=cuando,
        cerrada_en=cuando + pd.Timedelta(days=1),
        cantidad=10.0, precio_entrada=100.0, stop_inicial=98.0,
        pnl_bruto=bruto_R * riesgo, costes_totales=coste_R * riesgo,
        estrategia="B1", direccion="BUY")

_t0 = pd.Timestamp("2025-01-01", tz="UTC")
_ops = []
for i in range(12):                                    # entrenamiento
    _ops.append(_op(i, _t0 + pd.Timedelta(days=i)))
_c1 = _t0 + pd.Timedelta(days=40)
_c2 = _t0 + pd.Timedelta(days=80)
_cf = _t0 + pd.Timedelta(days=140)
for i in range(10):                                    # ventana 1
    _ops.append(_op(100 + i, _c1 + pd.Timedelta(days=i)))
for i in range(15):                                    # ventana 2
    _ops.append(_op(200 + i, _c2 + pd.Timedelta(days=i)))

try:
    _wf = M01.walk_forward(_ops, [_c1, _c2], estrategia="B1",
                           corte_final=_cf)
    _n = [t.get("n_posteriores") for t in _wf["tramos"]]
    _unicas = _wf.get("operaciones_unicas")
    ok16 = _n == [10, 15] and _unicas == 25
    det16 = (f"-> n por tramo {_n} (exigido [10, 15]), operaciones unicas "
             f"{_unicas} (exigido 25). Si el primer tramo tiene 25, cada "
             f"corte evalua hasta el final y los tramos se solapan")
except TypeError as e:
    _wf = None
    ok16 = False
    det16 = f"-> walk_forward no acepta un corte final explicito: {e}"
check("V16", "dos cortes y 25 decisiones: asignacion 10+15 sin duplicados",
      ok16, det16)

if _wf is not None and _wf.get("tramos"):
    _eb = [t.get("error_pronostico_bruto") for t in _wf["tramos"]]
    _cr = [t.get("coste_R_medio") for t in _wf["tramos"]]
    ok17 = (all(e is not None and abs(e) < 1e-9 for e in _eb)
            and all(c is not None and abs(c - 0.2) < 1e-9 for c in _cr))
    det17 = (f"-> errores brutos {_eb} (exigido 0 en los dos), coste_R "
             f"{_cr} (exigido 0,2). Restar un realizado NETO de un "
             f"pronostico BRUTO inventa un error de -0,2 R")
else:
    ok17 = False
    det17 = "-> sin tramos que medir"
check("V17", "pronostico bruto perfecto: error bruto cero y coste aparte",
      ok17, det17)

# V18 / oraculo O08. El contraejemplo a mi propia conclusion de que con
# 8 pb M01 no tiene nada que filtrar: la CANTIDAD se cancela con costes
# proporcionales, la DISTANCIA del stop no.
_mod = M01.ModeloR("sintetico_v18", 0.1, 0.1, 100, 0, _t0, _t0, "USD",
                   "ejemplo", "BUY", "cota fijada para algebra")
_fino = M01.decidir(10, 0.5, _mod, 1.6)
_ancho = M01.decidir(10, 4.0, _mod, 1.6)
check("V18", "mismo coste proporcional, distinta distancia: decisiones distintas",
      _fino.get("permite") is False and _ancho.get("permite") is True,
      f"-> stop a 0,5 permite={_fino.get('permite')} (exigido False), "
      f"stop a 4 permite={_ancho.get('permite')} (exigido True)")

print("\n=== NE1: la inferencia RECHAZA un NAV no evaluable ===")
# =====================================================================
# Exigido por la tercera revision: "Anade una prueba del consumidor con un
# NAV invalido; no basta con comprobar que el productor anade un campo."
# El bucle de contrastes de experimento.py no miraba `nav_fiable`, asi que
# un NAV con dias no evaluables dentro habria dado un p-valor.
from evaluador.experimento import motivo_no_evaluable

_res_malo = {
    "u/candidata": {"nav_fiable": False, "dias_no_evaluables": 55},
    "u/referencia": {"nav_fiable": True, "dias_no_evaluables": 0},
}
_res_bueno = {
    "u/candidata": {"nav_fiable": True, "dias_no_evaluables": 0},
    "u/referencia": {"nav_fiable": True, "dias_no_evaluables": 0},
}
_m = motivo_no_evaluable(_res_malo, "u/candidata", "u/referencia")
_b = motivo_no_evaluable(_res_bueno, "u/candidata", "u/referencia")
check("NE1", "con una cartera no fiable, el contraste no se emite",
      bool(_m) and "55" in _m and not _b,
      f"-> motivo con NAV invalido {_m!r} (tiene que decir por que), con "
      f"NAV valido {_b!r} (tiene que estar vacio)")

check("NE1b", "una cartera que falta tambien impide contrastar",
      bool(motivo_no_evaluable({}, "u/candidata")),
      "-> una clave ausente no puede pasar por contrastable")

# =====================================================================
print("\n=== V24: reejecucion reproducible ===")
# =====================================================================
# Reejecutar con los MISMOS artefactos tiene que dar las mismas
# decisiones, los mismos fills, el mismo libro y las mismas metricas. Si
# no, no hay experimento: hay una anecdota.
_serie24 = diaria(90, cierres={30: 112.0, 55: 95.0, 70: 130.0},
                  aperturas={31: 108.0, 56: 97.0})
_fd24 = [_serie24.index[20], _serie24.index[40], _serie24.index[60]]
_pol24 = politicas_simples(coste_rel=0.0008, permitir_fraccionado=False,
                           lote=1.0, dias_liquidacion=1)

def _corrida24():
    ev = EvaluadorMensual({"A": _serie24}, _pol24, fechas_decision=_fd24)
    r = ev.correr(LuegoLaMitad())
    libro = r["_libro"]
    fills = [(m.momento, m.tipo, m.instrumento, m.cantidad_solicitada,
              m.cantidad_ejecutada, m.precio_ejecucion,
              round(m.costes.get("comision", 0.0), 10))
             for m in libro.movimientos]
    decisiones = [(d.fecha_decision, tuple(sorted(d.pesos_deseados.items())),
                   tuple(sorted(d.scores.items())))
                  for d in r["_decisiones"]]
    return {
        "nav": r["_nav"],
        "fills": fills,
        "decisiones": decisiones,
        "estado": libro.estado(),
        "cagr": r.get("cagr"),
        "retorno_total": r.get("retorno_total"),
        "comisiones": r.get("comisiones_moneda"),
    }

_a24, _b24 = _corrida24(), _corrida24()
_nav_igual = (len(_a24["nav"]) == len(_b24["nav"])
              and bool((_a24["nav"].index == _b24["nav"].index).all())
              and float(np.abs(_a24["nav"].values - _b24["nav"].values).max()) == 0.0)
check("V24", "reejecucion: NAV identico al bit, sin tolerancia",
      _nav_igual,
      f"-> maxima diferencia "
      f"{float(np.abs(_a24['nav'].values - _b24['nav'].values).max()) if len(_a24['nav']) == len(_b24['nav']) else 'longitudes distintas'}")

check("V24b", "reejecucion: mismas decisiones y mismos fills",
      _a24["decisiones"] == _b24["decisiones"]
      and _a24["fills"] == _b24["fills"],
      f"-> decisiones iguales={_a24['decisiones'] == _b24['decisiones']}, "
      f"fills iguales={_a24['fills'] == _b24['fills']} "
      f"({len(_a24['fills'])} vs {len(_b24['fills'])} apuntes)")

check("V24c", "reejecucion: mismo libro final y mismas metricas",
      _a24["estado"] == _b24["estado"]
      and _a24["cagr"] == _b24["cagr"]
      and _a24["retorno_total"] == _b24["retorno_total"]
      and _a24["comisiones"] == _b24["comisiones"],
      f"-> CAGR {_a24['cagr']} vs {_b24['cagr']}, comisiones "
      f"{_a24['comisiones']} vs {_b24['comisiones']}")

# Y que la corrida haya hecho algo: una reproducibilidad de cero
# operaciones no demuestra nada.
check("V24d", "la corrida comparada SI opera (si no, no prueba nada)",
      len(_a24["fills"]) >= 4 and len(_a24["decisiones"]) == 3,
      f"-> {len(_a24['fills'])} apuntes y {len(_a24['decisiones'])} "
      f"decisiones; con cero operaciones dos corridas vacias coinciden "
      f"trivialmente")

# =====================================================================
print("\n=== Puertas de cambios posteriores ===")
# =====================================================================

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
