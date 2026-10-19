"""
Pruebas del estimador de M01.

Dos cosas que hay que comprobar y no asumir:

  1. Que las definiciones de R salen bien sobre oráculos calculados a mano.
  2. Que el filtro DISCRIMINA. La auditoría avisó de que «si todas las
     operaciones reciben el mismo pronóstico y el mismo coste relativo, el
     filtro será prácticamente todas o ninguna». Eso es contrastable, y si
     resulta cierto hay que decirlo: un filtro que no discrimina no es un
     filtro, es un interruptor de encendido disfrazado.

Y la fuga más fácil de cometer aquí: entrenar con una operación que se abrió
antes del corte pero cerró después. Contiene información posterior al corte.
Hay un oráculo para eso.
"""
import os
import sys
from datetime import datetime, timedelta

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

import numpy as np

from institucional.m01_estimador import (
    DatosInsuficientes, Operacion, ajustar, decidir,
    ganancia_bruta_estimable, margen_conservador, walk_forward,
)

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


D0 = datetime(2024, 1, 1)


def op(i, pnl, *, cantidad=10.0, entrada=100.0, stop=98.0, costes=1.0,
       dias_abierta=0, dias_cerrada=5, estrategia="shark", direccion="BUY"):
    return Operacion(
        id=f"op{i}", abierta_en=D0 + timedelta(days=dias_abierta),
        cerrada_en=D0 + timedelta(days=dias_cerrada),
        cantidad=cantidad, precio_entrada=entrada, stop_inicial=stop,
        pnl_bruto=pnl, costes_totales=costes,
        estrategia=estrategia, direccion=direccion)


# =====================================================================
print("\n=== 1) Las definiciones, contra oraculos a mano ===")
# =====================================================================

# 10 unidades, entrada 100, stop 98 -> riesgo inicial = 10 * 2 = 20
o = op(1, pnl=40.0, costes=4.0)
check("riesgo inicial = cantidad * distancia al stop de ENTRADA",
      abs(o.riesgo_inicial - 20.0) < 1e-12, f"-> {o.riesgo_inicial}")
check("R bruto = pnl bruto / riesgo inicial",
      abs(o.R_bruto - 2.0) < 1e-12, f"-> {o.R_bruto}")
check("R neto = (pnl bruto - costes) / riesgo inicial",
      abs(o.R_neto - 1.8) < 1e-12, f"-> {o.R_neto}")

# El denominador NO se redefine con un stop movido. Si una operacion movio
# el stop a 99.9, su riesgo inicial sigue siendo el de la entrada.
o_movido = op(2, pnl=40.0, stop=98.0)
check("un stop movido despues no cambia el denominador",
      abs(o_movido.riesgo_inicial - 20.0) < 1e-12,
      "-> si se recalculara con el stop final, mover el stop a favor daria "
      "un denominador pequeno y un R enorme: el estimador premiaria justo "
      "lo que no debe")

o_cero = op(3, pnl=10.0, entrada=100.0, stop=100.0)
check("riesgo cero marca la operacion como NO utilizable",
      not o_cero.utilizable, f"-> riesgo {o_cero.riesgo_inicial}")
try:
    o_cero.R_bruto
    check("y pedir su R lanza en vez de devolver un numero", False)
except DatosInsuficientes:
    check("y pedir su R lanza en vez de devolver un numero", True)

o_nan = op(4, pnl=float("nan"))
check("un pnl no finito tampoco es utilizable", not o_nan.utilizable)


# =====================================================================
print("\n=== 2) Madurez: la fuga mas facil de cometer ===")
# =====================================================================

CORTE = D0 + timedelta(days=100)

# 20 operaciones cerradas ANTES del corte.
maduras = [op(i, pnl=np.sin(i) * 20 + 10, dias_abierta=i,
              dias_cerrada=i + 5) for i in range(20)]
# Una que se abrio antes del corte pero cerro DESPUES: contiene
# informacion posterior al corte.
cruzada = op(99, pnl=1000.0, dias_abierta=98, dias_cerrada=140)

m_sin = ajustar(maduras, corte=CORTE)
m_con = ajustar(maduras + [cruzada], corte=CORTE)
check("una operacion que cruza el corte NO entra en el entrenamiento",
      m_sin.n == m_con.n and abs(m_sin.mu_R - m_con.mu_R) < 1e-12,
      f"-> sin: n={m_sin.n} mu={m_sin.mu_R:.4f}; "
      f"con: n={m_con.n} mu={m_con.mu_R:.4f}. Si entrara, su pnl de 1000 "
      f"moveria la media y seria fuga.")

check("el modelo declara su ventana temporal",
      m_sin.desde <= m_sin.hasta < CORTE,
      f"-> {m_sin.desde} .. {m_sin.hasta}")


# =====================================================================
print("\n=== 3) Muestra insuficiente -> NO_DATA, no una estimacion ===")
# =====================================================================

try:
    ajustar([op(i, pnl=10.0, dias_cerrada=i + 1) for i in range(5)],
            corte=CORTE)
    check("con 5 operaciones se niega a estimar", False, "-> estimo")
except DatosInsuficientes:
    check("con 5 operaciones se niega a estimar", True)

try:
    ajustar([op(i, pnl=10.0, entrada=100.0, stop=100.0, dias_cerrada=i + 1)
             for i in range(30)], corte=CORTE)
    check("30 operaciones con riesgo cero no sirven", False, "-> estimo")
except DatosInsuficientes:
    check("30 operaciones con riesgo cero no sirven (no se rellenan)", True)

mezcla = [op(i, pnl=10.0, dias_cerrada=i + 1) for i in range(15)]
mezcla.append(Operacion(id="eur", abierta_en=D0, cerrada_en=D0 + timedelta(days=2),
                        cantidad=10, precio_entrada=100, stop_inicial=98,
                        pnl_bruto=20, costes_totales=1, moneda="EUR",
                        estrategia="shark"))
try:
    ajustar(mezcla, corte=CORTE)
    check("no promedia R de monedas distintas", False, "-> promedio")
except DatosInsuficientes:
    check("no promedia R de monedas distintas sin normalizar", True)

cuenta = sum(1 for o in [op(i, pnl=10.0, entrada=100, stop=100,
                            dias_cerrada=i + 1) for i in range(12)]
             + [op(100 + i, pnl=10.0, dias_cerrada=i + 1) for i in range(12)]
             if o.utilizable)
m_mix = ajustar([op(i, pnl=10.0, entrada=100, stop=100, dias_cerrada=i + 1)
                 for i in range(12)]
                + [op(100 + i, pnl=np.cos(i) * 15 + 8, dias_cerrada=i + 1)
                   for i in range(12)], corte=CORTE)
check("las descartadas se CUENTAN, no desaparecen",
      m_mix.descartadas == 12 and m_mix.n == 12,
      f"-> n={m_mix.n}, descartadas={m_mix.descartadas}")


# =====================================================================
print("\n=== 4) La puerta ===")
# =====================================================================

sin_modelo = decidir(10.0, 2.0, None, coste_ida_vuelta=1.0)
check("sin modelo el estado es UNSUPPORTED y no permite nada",
      sin_modelo["estado"] == "UNSUPPORTED" and sin_modelo["permite"] is None,
      f"-> {sin_modelo}")

# mu_R positivo y grande: la ganancia estimable supera el coste.
buenas = [op(i, pnl=40.0 + np.sin(i) * 5, dias_cerrada=i + 1)
          for i in range(30)]
m_bueno = ajustar(buenas, corte=CORTE)
d_pasa = decidir(10.0, 2.0, m_bueno, coste_ida_vuelta=1.0)
check("con un R historico alto y coste bajo, pasa",
      d_pasa["estado"] == "READY" and d_pasa["permite"] is True,
      f"-> {d_pasa['margen_conservador']}")

d_no = decidir(10.0, 2.0, m_bueno, coste_ida_vuelta=10_000.0)
check("con un coste enorme, no pasa",
      d_no["permite"] is False, f"-> {d_no['margen_conservador']}")

check("la puerta usa la COTA INFERIOR, no la media",
      m_bueno.L_R < m_bueno.mu_R
      and abs(margen_conservador(10.0, 2.0, m_bueno, 0.0)
              - 10.0 * 2.0 * m_bueno.L_R) < 1e-9,
      f"-> mu={m_bueno.mu_R:.4f} L={m_bueno.L_R:.4f}")

check("la ganancia estimable es q * distancia * mu, en moneda",
      abs(ganancia_bruta_estimable(10.0, 2.0, m_bueno)
          - 10.0 * 2.0 * m_bueno.mu_R) < 1e-9)

malas = [op(i, pnl=-10.0 + np.sin(i) * 3, dias_cerrada=i + 1)
         for i in range(30)]
m_malo = ajustar(malas, corte=CORTE)
check("con un R historico negativo no pasa nada",
      decidir(10.0, 2.0, m_malo, coste_ida_vuelta=0.0)["permite"] is False,
      f"-> mu={m_malo.mu_R:.4f}")


# =====================================================================
print("\n=== 5) ¿DISCRIMINA? Lo que la auditoria avisó ===")
# =====================================================================

# Mismo modelo, mismo coste RELATIVO, distintos tamanos. Si el filtro no
# distingue, aprueba o rechaza todo por igual.
COSTE_REL = 0.0016          # ida y vuelta, 8 pb por pata
decisiones_rel = []
for cantidad in (1, 5, 10, 50, 100, 500):
    nominal = cantidad * 100.0
    decisiones_rel.append(
        decidir(cantidad, 2.0, m_bueno,
                coste_ida_vuelta=nominal * COSTE_REL)["permite"])
todas_iguales = len(set(decisiones_rel)) == 1
print(f"         con coste puramente proporcional: {decisiones_rel}")
check("CONFIRMADO: con coste proporcional el filtro es todo-o-nada",
      todas_iguales,
      "-> si discriminara aqui, seria por un artefacto de escala")
print("         La auditoria tenia razon: un coste proporcional se cancela")
print("         contra una ganancia tambien proporcional al tamano, asi que")
print("         el filtro no distingue entre operaciones. No es un filtro.")

# Ahora con un coste FIJO por orden, que NO escala con el tamano. Ahi si
# puede discriminar: las operaciones pequenas no cubren la comision minima.
#
# El umbral se BUSCA, no se adivina. Mi primera version puso una comision
# de 1,00 y espero que frenara a una unidad; con un R historico de ~2 y
# distancia 2, cada unidad rinde ~3,8 esperados, asi que 1,00 no frena
# nada. La expectativa estaba mal, no el codigo.
COSTE_FIJO = 20.0
tamanos = [0.5, 1, 2, 3, 5, 10, 20, 50]
decisiones_fijo = [
    (q, decidir(q, 2.0, m_bueno,
                coste_ida_vuelta=COSTE_FIJO + q * 100.0 * COSTE_REL)["permite"])
    for q in tamanos
]
print(f"         con comision minima de {COSTE_FIJO:.0f}: "
      f"{[(q, v) for q, v in decisiones_fijo]}")

rechazadas = [q for q, v in decisiones_fijo if not v]
aceptadas = [q for q, v in decisiones_fijo if v]
check("con un coste FIJO por orden si discrimina: existe un umbral de tamano",
      bool(rechazadas) and bool(aceptadas)
      and max(rechazadas) < min(aceptadas),
      f"-> rechaza {rechazadas}, acepta {aceptadas}. Si no hubiera umbral, "
      f"el filtro seguiria siendo todo-o-nada.")
if rechazadas and aceptadas:
    print(f"         umbral entre {max(rechazadas)} y {min(aceptadas)} "
          f"unidades: por debajo, la comision minima se come la ganancia "
          f"esperada")
print("         Conclusion: M01 solo sirve donde el coste NO es")
print("         proporcional. Con la tarifa que asume el backtester (8 pb")
print("         por pata, sin minimo) no tiene nada que filtrar.")


# =====================================================================
print("\n=== 6) Walk-forward ===")
# =====================================================================

# Operaciones a lo largo de dos anos, con un R que cambia a mitad: el
# estimador entrenado en la primera mitad tiene que FALLAR en la segunda,
# y el walk-forward tiene que ensenarlo.
largas = []
for i in range(120):
    pnl = 30.0 + np.sin(i) * 8 if i < 60 else -15.0 + np.sin(i) * 8
    largas.append(op(i, pnl=pnl, dias_abierta=i * 5, dias_cerrada=i * 5 + 3))

cortes = [D0 + timedelta(days=d) for d in (200, 300, 400, 500)]
wf = walk_forward(largas, cortes)
check("el walk-forward evalua varios tramos",
      len(wf["tramos"]) >= 2, f"-> {len(wf['tramos'])} tramos")
if wf.get("resumen"):
    r = wf["resumen"]
    print(f"         R predicho medio {r['R_predicho_medio']:+.4f}  "
          f"realizado {r['R_realizado_medio']:+.4f}  "
          f"error absoluto medio {r['error_absoluto_medio']:.4f}")
    check("detecta que el pronostico falla cuando el regimen cambia",
          r["error_absoluto_medio"] > 0.5,
          f"-> error absoluto medio {r['error_absoluto_medio']}: si fuera "
          f"pequeno, el estimador habria acertado y esta prueba no probaria "
          f"nada")
    check("el resumen avisa de cuando el pronostico no dice nada",
          "_lectura" in r)

check("un corte sin muestra suficiente se registra como incidencia",
      isinstance(wf["incidencias"], list))

wf_vacio = walk_forward(largas[:5], cortes)
check("sin operaciones suficientes no inventa tramos",
      not wf_vacio["tramos"] and wf_vacio["incidencias"])


print("\n" + "=" * 62)
print(f"RESULTADO: {OK} pruebas pasadas, {len(FALLOS)} fallos")
for f in FALLOS:
    print(f"  - {f}")
print("=" * 62)
sys.exit(1 if FALLOS else 0)
