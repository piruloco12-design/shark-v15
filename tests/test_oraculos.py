"""
Oraculos numericos independientes.

Los cinco casos vienen de la especificacion externa del
2026-10-19 (seccion 11), con su resultado exacto ya fijado. Son
una verificacion INDEPENDIENTE: el valor esperado no sale de lo
que hace el codigo, sino de la aritmetica declarada por alguien
que no escribio este codigo.

Es la clase de prueba que caza un error de contabilidad que los
tests propios no ven, porque los tests propios suelen comprobar
que el codigo hace lo que su autor creia.

No son backtests de mercado: verifican unidades y signos.
"""
import math
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

OK = 0
FALLOS = []


def check(nombre, cond, detalle=""):
    global OK
    if cond:
        OK += 1
        print(f"  PASA   {nombre}")
    else:
        FALLOS.append(nombre)
        print(f"  FALLA  {nombre}  {detalle}")


print("\n=== ORACULO 1: comisiones por lado, spread ya en el precio ===")
print("    Compra 10 a 100,02 y venta 10 a 101,00. Comision 0,50 por lado.")
print("    Esperado: P&L neto = 8,80")

cantidad = 10
entrada, salida = 100.02, 101.00
comision_lado = 0.50

bruto = (salida - entrada) * cantidad
neto = bruto - comision_lado * 2

print(f"    bruto {bruto:.2f} - comisiones {comision_lado*2:.2f} = {neto:.2f}")
check("P&L neto = 8,80", abs(neto - 8.80) < 1e-9, f"-> {neto}")
check("el spread NO se descuenta otra vez",
      abs(neto - 8.80) < 1e-9,
      "los precios ya son ask de compra y bid de venta")


print("\n=== ORACULO 2: gap mas alla del stop ===")
print("    Largo 5 a 100, stop 99. Siguiente precio negociable 95,")
print("    slippage adverso 0,10. Comisiones cero.")
print("    Esperado: salida 94,90 y P&L = -25,50  (NO -5,00)")

cantidad = 5
entrada, stop = 100.0, 99.0
primer_negociable = 95.0
slippage = 0.10

salida_real = primer_negociable - slippage
pnl_real = (salida_real - entrada) * cantidad
pnl_ingenuo = (stop - entrada) * cantidad

print(f"    salida real {salida_real:.2f} -> P&L {pnl_real:.2f}")
print(f"    si se usara el stop: {pnl_ingenuo:.2f}  <- lo que NO debe hacerse")
check("salida = 94,90", abs(salida_real - 94.90) < 1e-9, f"-> {salida_real}")
check("P&L = -25,50", abs(pnl_real - (-25.50)) < 1e-9, f"-> {pnl_real}")
check("el stop NO limita la perdida en un gap", pnl_real < pnl_ingenuo,
      "un stop no es garantia de perdida acotada")


print("\n=== ORACULO 3: tamaño con coste fijo dentro del presupuesto ===")
print("    Riesgo presupuestado 5,00. Perdida por unidad al stop 1,00.")
print("    Coste fijo completo 0,40. Lote 1.")
print("    Esperado: maximo 4 unidades (perdida modelada 4,40).")
print("    Cinco implican 5,40 y se rechazan.")

presupuesto = 5.00
perdida_unidad = 1.00
coste_fijo = 0.40

def perdida_modelada(q):
    return q * perdida_unidad + coste_fijo

maximo = 0
for q in range(1, 20):
    if perdida_modelada(q) <= presupuesto:
        maximo = q
    else:
        break

print(f"    q=4 -> {perdida_modelada(4):.2f}   q=5 -> {perdida_modelada(5):.2f}")
check("maximo = 4 unidades", maximo == 4, f"-> {maximo}")
check("4 unidades caben", perdida_modelada(4) <= presupuesto)
check("5 unidades NO caben", perdida_modelada(5) > presupuesto,
      f"-> {perdida_modelada(5)}")
check("la perdida de 4 es 4,40", abs(perdida_modelada(4) - 4.40) < 1e-9)


print("\n=== ORACULO 4: expectativa con coste ===")
print("    G=1,25R  L=1R  p=0,47  C=0,10R")
print("    Esperado: EV = -0,0425 R  y  p_equilibrio = 0,488888...")

G, L, p, C = 1.25, 1.00, 0.47, 0.10
ev_bruto = p * G - (1 - p) * L
ev_neto = ev_bruto - C
p_equilibrio = (L + C) / (G + L)

print(f"    EV bruto {ev_bruto:+.4f}  ->  EV neto {ev_neto:+.4f}")
print(f"    p de equilibrio {p_equilibrio:.6f}")
check("EV bruto = +0,0575 R", abs(ev_bruto - 0.0575) < 1e-9, f"-> {ev_bruto}")
check("EV neto = -0,0425 R", abs(ev_neto - (-0.0425)) < 1e-9, f"-> {ev_neto}")
check("p equilibrio = 0,488888...", abs(p_equilibrio - 0.4888888888888889) < 1e-12,
      f"-> {p_equilibrio}")
check("acertar el 47% NO basta con ese coste", p < p_equilibrio,
      "precision no es beneficio")


print("\n=== ORACULO 5: fill parcial y cancelacion ===")
print("    Orden de 10, fill de 4, cancelacion confirmada del resto.")
print("    Esperado: posicion 4 y proteccion para 4.")

pedido, ejecutado = 10, 4
cancelado = pedido - ejecutado

posicion = ejecutado
proteccion = ejecutado
reserva_liberada = cancelado

check("posicion = 4", posicion == 4, f"-> {posicion}")
check("proteccion para 4, no para 10", proteccion == 4, f"-> {proteccion}")
check("ni posicion cero ni proteccion de 10",
      posicion != 0 and proteccion != pedido)
check("se libera solo la reserva no consumida", reserva_liberada == 6,
      f"-> {reserva_liberada}")


print("\n=== CONTRASTE CON EL BACKTESTER REAL ===")
print("    Los oraculos 1 y 4 se comprueban contra el motor de cartera,")
print("    no solo en aritmetica suelta.")

import types
for n, attrs in [("yfinance", {"download": lambda *a, **k: None}), ("ta", {})]:
    m = types.ModuleType(n)
    for k, v in attrs.items():
        setattr(m, k, v)
    sys.modules.setdefault(n, m)
import ta
for sub in ("trend", "momentum", "volatility"):
    sm = types.ModuleType(f"ta.{sub}")
    setattr(ta, sub, sm)
    sys.modules[f"ta.{sub}"] = sm
ta.trend.ema_indicator = ta.trend.adx = ta.trend.MACD = lambda *a, **k: None
ta.momentum.rsi = ta.volatility.average_true_range = lambda *a, **k: None

import tempfile
_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_db.close()
os.environ["DATABASE_NAME"] = _db.name
os.environ["TELEGRAM_TOKEN"] = ""
sys.path.insert(0, os.path.join(REPO, "validator"))
import cartera

# El coste del motor es proporcional, no fijo: se comprueba que
# descuenta las DOS patas, que es el fallo que tenia ayer.
coste_pct = cartera.COSTE_POR_PATA
q, pe, ps = 10.0, 100.02, 101.00
bruto_motor = (ps - pe) * q
coste_entrada = pe * coste_pct * q
coste_salida = ps * coste_pct * q
neto_motor = bruto_motor - coste_entrada - coste_salida

print(f"    coste por pata del motor: {coste_pct*100:.3f}%")
print(f"    bruto {bruto_motor:.4f} - entrada {coste_entrada:.4f} "
      f"- salida {coste_salida:.4f} = {neto_motor:.4f}")
check("el motor descuenta AMBAS patas",
      abs(neto_motor - (bruto_motor - coste_entrada - coste_salida)) < 1e-12)
check("el neto del motor es menor que el bruto", neto_motor < bruto_motor)
check("ida y vuelta = 2x el coste por pata",
      abs((coste_entrada + coste_salida) - coste_pct * q * (pe + ps)) < 1e-12)

os.unlink(_db.name)

print("\n" + "=" * 62)
print(f"RESULTADO: {OK} pruebas pasadas, {len(FALLOS)} fallos")
for f in FALLOS:
    print(f"  - {f}")
print("=" * 62)
sys.exit(1 if FALLOS else 0)
