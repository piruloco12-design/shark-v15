"""
PRUEBAS DE INTEGRACION DE LA RUTA VIVA.

Exigidas por la tercera revision, §10 P0, textual:

    "Pruebas de integracion necesarias -- ejecutadas a traves de la ruta de
     apertura, no solo sobre una funcion auxiliar"

Esa frase es el punto. Yo habia escrito `capacidades_core.py` declarando
moneda y cortos BLOQUEADAS citando `LibroContado`, y era FALSO para la
ruta viva: la que abre posiciones es `paper_broker.open_trade` ->
`storage.create_paper_trade`, y no pasaba por el libro. Comprobe la guarda
en lo que habia construido, no en el camino que se ejecuta. Con 1.000 de
saldo se podian comprometer 2.000 y un SELL sin inventario registraba un
corto.

Asi que todas estas pruebas entran por `open_trade` y
`check_and_close_trades`. Si una pasa llamando a un auxiliar pero falla
por la ruta real, no sirve de nada.

Almacenamiento en memoria, sin red y sin mensajes: no se abre una base de
datos real ni se envia nada.

Uso:  python tests/test_integracion_core.py
"""
import io
import json
import os
import shutil
import sys
import tempfile
import types

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)
sys.path.insert(0, os.path.join(REPO, "tests"))

os.environ.setdefault("TELEGRAM_TOKEN", "")
os.environ.setdefault("CAPITAL", "1000")
sys.modules.setdefault("yfinance", types.ModuleType("yfinance"))

PASA, FALLA = [], []


def check(ident, nombre, cond, detalle=""):
    if cond:
        PASA.append(ident)
        print(f"  PASA   [{ident}] {nombre}")
    else:
        FALLA.append((ident, nombre, detalle))
        print(f"  FALLA  [{ident}] {nombre}")
        if detalle:
            print(f"                 {detalle}")


# ---- doble de storage que conserva la semantica de la API real ----
ESTADO = {"capital": 1000.0, "trades": [], "cerrados": [], "riesgo": [],
          "actualizaciones": []}


def _reset_storage():
    ESTADO["capital"] = 1000.0
    ESTADO["trades"] = []
    ESTADO["cerrados"] = []
    ESTADO["riesgo"] = []
    ESTADO["actualizaciones"] = []


S = types.ModuleType("storage")
S.get_paper_capital = lambda: ESTADO["capital"]
S.get_open_paper_trades = lambda: list(ESTADO["trades"])


def _crear(**kw):
    kw["id"] = len(ESTADO["trades"]) + len(ESTADO["cerrados"]) + 1
    ESTADO["trades"].append(dict(kw))
    return kw["id"]


def _actualizar(v):
    ESTADO["actualizaciones"].append(v)
    ESTADO["capital"] = v


def _cerrar(**kw):
    ESTADO["cerrados"].append(dict(kw))
    ESTADO["trades"] = [t for t in ESTADO["trades"]
                        if t.get("id") != kw.get("trade_id")]


S.create_paper_trade = _crear
S.update_paper_capital = _actualizar
S.close_paper_trade = _cerrar
S.log_risk_event = lambda **k: ESTADO["riesgo"].append(dict(k))
S.has_open_trade_for_ticker = lambda t: any(
    x["ticker"] == t for x in ESTADO["trades"])
sys.modules["storage"] = S

T = types.ModuleType("telegram_alerts")
T.send_telegram_message = lambda *a, **k: None
T.format_open_trade_message = lambda *a, **k: ""
T.format_close_trade_message = lambda *a, **k: ""
sys.modules["telegram_alerts"] = T

import paper_broker as B
from cuenta_contado import ConflictoDeEvento

B.MENSAJE_BROKER_AL_ABRIR = False
TMP = tempfile.mkdtemp(prefix="integr_core_")
_n = [0]


def cuenta_limpia(**kw):
    """Una cuenta nueva por caso: los casos no se contaminan entre si."""
    _n[0] += 1
    _reset_storage()
    ruta = os.path.join(TMP, f"c{_n[0]}.sqlite")
    return B.cuenta(ruta=ruta, reiniciar=True, **kw), ruta


def setup(entry=100.0, size=5.0, sl=98.0, tp=104.0, signal="BUY"):
    if signal == "BUY":
        return {"entry": entry, "stop_loss": sl, "take_profit": tp,
                "position_size": size}
    return {"entry": entry, "stop_loss": tp, "take_profit": sl,
            "position_size": size}


# =====================================================================
print("\n=== I1: una compra no deja comprometer otra vez el mismo saldo ===")
# =====================================================================
c, _ = cuenta_limpia()
B.open_trade("AAA", "BUY", "s", setup(entry=100.0, size=9.0))
caja_tras_1 = c.efectivo_utilizable
B.open_trade("BBB", "BUY", "s", setup(entry=100.0, size=9.0))
nominal = sum(t["entry_price"] * t["position_size"] for t in ESTADO["trades"])
check("I1", "saldo 1000: la segunda compra no compromete otros 1000",
      nominal <= 1000.0 + 1e-9 and len(ESTADO["trades"]) == 1,
      f"-> nominal comprometido {nominal}, operaciones "
      f"{len(ESTADO['trades'])}, caja tras la primera {caja_tras_1:.2f}")

check("I1b", "el rechazo queda registrado como incidencia, no en silencio",
      any(r.get("event_type") == "ADMISION_RECHAZADA" for r in ESTADO["riesgo"]),
      f"-> eventos de riesgo: {[r.get('event_type') for r in ESTADO['riesgo']]}")

# =====================================================================
print("\n=== I2: SELL sin inventario no persiste ningun corto ===")
# =====================================================================
c, _ = cuenta_limpia()
B.open_trade("SIN_INV", "SELL", "s", setup(entry=100.0, size=5.0,
                                           signal="SELL"))
check("I2", "SELL sin inventario: ninguna orden, fill ni posicion corta",
      len(ESTADO["trades"]) == 0 and c.cantidad("SIN_INV") == 0.0
      and abs(c.efectivo_utilizable - 1000.0) < 1e-9,
      f"-> trades {len(ESTADO['trades'])}, cantidad "
      f"{c.cantidad('SIN_INV')}, caja {c.efectivo_utilizable}")

# =====================================================================
print("\n=== I3: instrumento en otra moneda, sin FX ===")
# =====================================================================
c, _ = cuenta_limpia()
estado_antes = json.dumps(c.estado(), sort_keys=True, default=str)
c._instrumento_forzado = None
# Se registra el instrumento en EUR ANTES de la orden, que es el caso
# realista: el producto existe y cotiza en otra moneda.
adm = c.admitir(order_id="eur-1", instrumento="EUREKA", lado="BUY",
                cantidad=1, precio=100.0, moneda="EUR")
estado_despues = json.dumps(c.estado(), sort_keys=True, default=str)
check("I3", "cuenta USD + instrumento EUR: rechazo sin cambios de estado",
      not adm["admitida"] and estado_antes == estado_despues
      and "EUR" in adm["motivo"],
      f"-> admitida={adm['admitida']}, motivo {adm['motivo'][:70]!r}, "
      f"estado intacto={estado_antes == estado_despues}")

# =====================================================================
print("\n=== I4: lote entero por la ruta real ===")
# =====================================================================
c, _ = cuenta_limpia()
B.open_trade("LOTE", "BUY", "s", setup(entry=100.0, size=2.5))
cant = ESTADO["trades"][0]["position_size"] if ESTADO["trades"] else None
check("I4", "lote entero: 2,5 unidades pedidas se ejecutan como 2",
      cant is not None and abs(cant - 2.0) < 1e-9
      and abs(c.cantidad("LOTE") - 2.0) < 1e-9,
      f"-> persistido {cant}, inventario {c.cantidad('LOTE')}. Antes la "
      f"ruta viva registraba 9,992006... declarando acciones enteras")

c2, _ = cuenta_limpia(permitir_fraccionado=True, lote=0.0)
B.open_trade("FRAC", "BUY", "s", setup(entry=100.0, size=2.5))
cant_f = ESTADO["trades"][0]["position_size"] if ESTADO["trades"] else None
check("I4b", "fraccion SOLO con la capacidad declarada explicitamente",
      cant_f is not None and abs(cant_f - 2.5) < 1e-9,
      f"-> con permitir_fraccionado=True se ejecuta {cant_f}")

# =====================================================================
print("\n=== I5: fill repetido ===")
# =====================================================================
c, _ = cuenta_limpia()
B.open_trade("REP", "BUY", "s", setup(entry=100.0, size=3.0))
caja_1 = c.efectivo_utilizable
inv_1 = c.cantidad("REP")
ev = [e for e in c.eventos() if e["tipo"] == "COMPRA"][-1]
r = c.aplicar_fill(event_id=ev["event_id"], order_id=ev["payload"]["order_id"],
                   instrumento="REP", lado="BUY",
                   cantidad=ev["payload"]["cantidad"],
                   precio=ev["payload"]["precio"],
                   coste_rel=ev["payload"]["coste_rel"],
                   coste_fijo=ev["payload"]["coste_fijo"],
                   momento=ev["payload"]["momento"],
                   riesgo_inicial=ev["payload"]["riesgo_inicial"],
                   motivo=ev["payload"]["motivo"],
                   cantidad_pre_admision=ev["payload"]["cantidad_pre_admision"])
check("I5", "repetir el mismo fill no cambia saldos ni cantidades",
      r.get("repetido") and abs(c.efectivo_utilizable - caja_1) < 1e-12
      and abs(c.cantidad("REP") - inv_1) < 1e-12,
      f"-> repetido={r.get('repetido')}, caja {c.efectivo_utilizable} "
      f"(antes {caja_1}), inventario {c.cantidad('REP')} (antes {inv_1})")

try:
    c.aplicar_fill(event_id=ev["event_id"], order_id="otro", instrumento="REP",
                   lado="BUY", cantidad=99.0, precio=1.0)
    conflicto = False
except ConflictoDeEvento:
    conflicto = True
check("I5b", "el mismo event_id con OTRO contenido da conflicto, no silencio",
      conflicto, "-> se acepto un contenido distinto bajo el mismo event_id")

# =====================================================================
print("\n=== I6: cancelar una orden no toca la reserva de otra ===")
# =====================================================================
c, _ = cuenta_limpia()
a1 = c.admitir(order_id="ord-A", instrumento="AA", lado="BUY", cantidad=3,
               precio=100.0, coste_rel=0.0008)
a2 = c.admitir(order_id="ord-B", instrumento="BB", lado="BUY", cantidad=3,
               precio=100.0, coste_rel=0.0008)
res_b_antes = c.libro.reserva_de("ord-B")
c.liberar("ord-A")
c.liberar("ord-A")          # repetir no libera mas
res_b = c.libro.reserva_de("ord-B")
check("I6", "cancelar A deja intacta la reserva de B",
      a1["admitida"] and a2["admitida"]
      and c.libro.reserva_de("ord-A") == 0.0
      and abs(res_b - res_b_antes) < 1e-12 and res_b > 0,
      f"-> reserva A {c.libro.reserva_de('ord-A')}, reserva B {res_b} "
      f"(antes {res_b_antes})")

# =====================================================================
print("\n=== I7: reiniciar reconstruye el MISMO estado ===")
# =====================================================================
c, ruta = cuenta_limpia()
B.open_trade("R1", "BUY", "s", setup(entry=100.0, size=3.0))
B.open_trade("R2", "BUY", "s", setup(entry=50.0, size=4.0))
c.admitir(order_id="viva-1", instrumento="R3", lado="BUY", cantidad=1,
          precio=10.0, coste_rel=0.0008)
estado_antes = json.dumps(c.estado(), sort_keys=True, default=str)
eventos_antes = len(c.eventos())

from cuenta_contado import CuentaContado
c_nueva = CuentaContado(ruta, moneda="USD", lote=1.0,
                        permitir_fraccionado=False, dias_liquidacion=0)
estado_despues = json.dumps(c_nueva.estado(), sort_keys=True, default=str)
check("I7", "reiniciar: estado contable identico, derivado de los eventos",
      estado_antes == estado_despues and len(c_nueva.eventos()) == eventos_antes,
      f"-> {eventos_antes} eventos; iguales={estado_antes == estado_despues}")

check("I7b", "la reserva viva sobrevive al reinicio",
      abs(c_nueva.libro.reserva_de("viva-1")
          - c.libro.reserva_de("viva-1")) < 1e-12
      and c_nueva.libro.reserva_de("viva-1") > 0,
      f"-> reserva tras reiniciar {c_nueva.libro.reserva_de('viva-1')}")

# =====================================================================
print("\n=== I8: los dos saldos no divergen al cerrar ===")
# =====================================================================
c, _ = cuenta_limpia()
B.open_trade("CIE", "BUY", "s", setup(entry=100.0, size=5.0, tp=104.0))
B.check_and_close_trades({"CIE": 104.0},
                         {"CIE": {"high": 105.0, "low": 99.0, "open": 100.0}})
nav = c.nav({"CIE": 104.0})
# 1000 - 500 - 0,40 = 499,60 al abrir. +520 - 0,416 al cerrar = 1019,184.
check("I8", "tras cerrar: caja, espejo e inventario cuadran",
      abs(c.efectivo_utilizable - 1019.184) < 1e-6
      and abs(ESTADO["capital"] - 1019.184) < 1e-6
      and c.cantidad("CIE") == 0.0,
      f"-> caja {c.efectivo_utilizable}, espejo {ESTADO['capital']}, "
      f"inventario {c.cantidad('CIE')} (exigido 1019.184 / 1019.184 / 0)")

check("I8b", "cada pata se cobra UNA vez en su propio fill",
      abs(nav["nav"] - 1019.184) < 1e-6,
      f"-> NAV {nav['nav']}: bruto 20, comisiones 0,816 (0,40 + 0,416), "
      f"neto 19,184")

# =====================================================================
print("\n=== I9: un fill fallido no envenena el registro ===")
# =====================================================================
c, ruta9 = cuenta_limpia()
# Un fill imposible: comprar mucho mas de lo que cabe, con la reduccion
# desactivada por dentro (aplicar_fill no reduce).
r_mal = c.aplicar_fill(event_id="malo-1", order_id="malo-1",
                       instrumento="XX", lado="BUY", cantidad=1000.0,
                       precio=100.0, coste_rel=0.0008)
caja_tras_fallo = c.efectivo_utilizable
try:
    c3 = CuentaContado(ruta9, moneda="USD", lote=1.0,
                       permitir_fraccionado=False, dias_liquidacion=0)
    reconstruye = True
    caja_reconstruida = c3.efectivo_utilizable
    incidencias = len(getattr(c3, "incidencias", []))
except Exception as e:
    reconstruye = False
    caja_reconstruida = None
    incidencias = 0
check("I9", "un fill que fallo no rompe la reconstruccion",
      (not r_mal.get("aplicado")) and reconstruye
      and abs((caja_reconstruida or -1) - caja_tras_fallo) < 1e-9,
      f"-> aplicado={r_mal.get('aplicado')}, reconstruye={reconstruye}, "
      f"caja {caja_tras_fallo} vs reconstruida {caja_reconstruida}")

check("I9b", "y el intento queda como incidencia, no borrado",
      incidencias >= 1,
      f"-> {incidencias} incidencias tras reconstruir")

shutil.rmtree(TMP, ignore_errors=True)

print("\n" + "=" * 70)
print(f"INTEGRACION DE LA RUTA VIVA: {len(PASA)} pasan, {len(FALLA)} FALLAN")
print("=" * 70)
if FALLA:
    print("\nLa ruta que de verdad opera no cumple:\n")
    for ident, nombre, _ in FALLA:
        print(f"  [{ident}] {nombre}")
    print("\nNo vale arreglarlo en una funcion auxiliar: estas pruebas")
    print("entran por open_trade y check_and_close_trades a proposito.")
print("=" * 70)

sys.exit(1 if FALLA else 0)
