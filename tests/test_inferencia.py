"""
Pruebas de la inferencia. Incluye su CALIBRACION, que es lo que importa.

Un contraste estadístico que no rechaza la nula al ritmo que dice no sirve
para nada, y eso no se ve leyendo el código: hay que medirlo. La forma de
medirlo es generar muchos casos donde se sabe que NO hay ventaja y contar
cuántas veces el contraste dice que sí. Si al 5% rechaza el 30% de las
veces, cualquier «resultado significativo» que produzca es basura.

Esto es lo que le faltaba a `bootstrap_expectativa`, que remuestreaba
operaciones individuales sin centrar y llamaba «probabilidad de ventaja» a
la fracción de remuestras positivas. Nunca comprobé si ese número
significaba algo. No significaba nada.
"""
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

import numpy as np
import pandas as pd

from evaluador.inferencia import contraste_diferencial, sensibilidad_bloque
from evaluador.registro import holm

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


IDX = pd.date_range("2011-01-31", periods=200, freq="ME", tz="UTC")


def nav(retornos):
    r = np.asarray(retornos, dtype="float64")
    return pd.Series(np.cumprod(1.0 + r) * 1000.0, index=IDX[:len(r)])


# =====================================================================
print("\n=== 1) Calibracion: SIN ventaja debe rechazar ~5% de las veces ===")
# =====================================================================

rng = np.random.default_rng(7)
N_SIM = 200
rechazos_5, rechazos_10 = 0, 0

for k in range(N_SIM):
    # Dos series con el MISMO retorno esperado y un factor comun, que es
    # el caso realista: una estrategia y su referencia comparten mercado.
    comun = rng.normal(0.006, 0.040, 179)
    a = nav(comun + rng.normal(0.0, 0.015, 179))
    b = nav(comun + rng.normal(0.0, 0.015, 179))
    p = contraste_diferencial(a, b, remuestras=400,
                              semilla=1000 + k)["p_valor_una_cola"]
    if p <= 0.05:
        rechazos_5 += 1
    if p <= 0.10:
        rechazos_10 += 1

tasa_5 = rechazos_5 / N_SIM
tasa_10 = rechazos_10 / N_SIM
print(f"         al 5%:  {rechazos_5}/{N_SIM} = {tasa_5*100:.1f}%")
print(f"         al 10%: {rechazos_10}/{N_SIM} = {tasa_10*100:.1f}%")

# Margen amplio porque 200 simulaciones tienen su propio error de muestreo:
# con una tasa real del 5%, el 95% de las veces caería entre 2% y 8,5%.
check("al 5% nominal rechaza entre el 1% y el 11%",
      0.01 <= tasa_5 <= 0.11,
      f"-> {tasa_5*100:.1f}%. Si fuera mucho mayor, cualquier resultado "
      f"significativo seria ruido; si fuera casi cero, el contraste no "
      f"detectaria nada nunca.")
check("al 10% nominal rechaza mas que al 5% (es monotono)",
      tasa_10 >= tasa_5,
      f"-> 10%: {tasa_10*100:.1f}% vs 5%: {tasa_5*100:.1f}%")


# =====================================================================
print("\n=== 2) Potencia: CON ventaja real debe detectarla ===")
# =====================================================================

detectados = 0
for k in range(60):
    comun = rng.normal(0.006, 0.040, 179)
    a = nav(comun + rng.normal(0.003, 0.015, 179))   # +0,3%/mes de ventaja
    b = nav(comun + rng.normal(0.000, 0.015, 179))
    if contraste_diferencial(a, b, remuestras=400,
                             semilla=2000 + k)["p_valor_una_cola"] <= 0.05:
        detectados += 1
potencia = detectados / 60
print(f"         ventaja de +0,3%/mes detectada en {detectados}/60 "
      f"= {potencia*100:.0f}%")
check("detecta una ventaja de +0,3% mensual en mas de la mitad de los casos",
      potencia > 0.5,
      f"-> potencia {potencia*100:.0f}%: con esta muestra el contraste no "
      f"veria una ventaja aunque existiera")


# =====================================================================
print("\n=== 3) Casos límite ===")
# =====================================================================

base = nav(rng.normal(0.006, 0.040, 179))
r = contraste_diferencial(base, base.copy(), remuestras=500)
check("dos series identicas dan diferencial exactamente cero",
      abs(r["diferencial_medio_periodico"]) < 1e-12,
      f"-> {r['diferencial_medio_periodico']}")
check("y su p-valor no es significativo",
      r["p_valor_una_cola"] > 0.05, f"-> p={r['p_valor_una_cola']}")

peor = nav(rng.normal(0.006, 0.040, 179) - 0.005)
r_peor = contraste_diferencial(peor, base, remuestras=500)
check("una estrategia PEOR no da un p-valor significativo",
      r_peor["p_valor_una_cola"] > 0.05,
      f"-> p={r_peor['p_valor_una_cola']}, diferencial "
      f"{r_peor['diferencial_medio_periodico']:+.6f}")

try:
    contraste_diferencial(base.iloc[:10], base.iloc[:10], remuestras=100)
    check("una muestra corta se rechaza en vez de dar un numero", False,
          "-> no lanzo")
except ValueError:
    check("una muestra corta se rechaza en vez de dar un numero", True)

check("el intervalo de confianza contiene el diferencial observado",
      r_peor["ic90_diferencial"][0] <= r_peor["diferencial_medio_periodico"]
      <= r_peor["ic90_diferencial"][1],
      f"-> {r_peor['ic90_diferencial']} vs "
      f"{r_peor['diferencial_medio_periodico']}")

# El umbral economico desplaza el contraste, y tiene que notarse.
mejor = nav(rng.normal(0.006, 0.040, 179) + 0.004)
sin_umbral = contraste_diferencial(mejor, base, umbral=0.0, remuestras=800)
con_umbral = contraste_diferencial(mejor, base, umbral=0.01, remuestras=800)
check("exigir un umbral economico alto sube el p-valor",
      con_umbral["p_valor_una_cola"] > sin_umbral["p_valor_una_cola"],
      f"-> umbral 0: p={sin_umbral['p_valor_una_cola']}, "
      f"umbral 1%: p={con_umbral['p_valor_una_cola']}")

check("se informa la sensibilidad a la longitud de bloque",
      len(sensibilidad_bloque(mejor, base, remuestras=300)) >= 4)


# =====================================================================
print("\n=== 4) Holm: secuencial, no alfa/N para todas ===")
# =====================================================================

res = holm({"h1": 0.002, "h2": 0.02, "h3": 0.04, "h4": 0.5}, alfa=0.05)
check("el primer umbral es alfa/N",
      abs(res["h1"]["umbral_holm"] - 0.05 / 4) < 1e-9,
      f"-> {res['h1']['umbral_holm']}")
check("los umbrales crecen al avanzar en el orden",
      res["h1"]["umbral_holm"] < res["h2"]["umbral_holm"]
      < res["h3"]["umbral_holm"] < res["h4"]["umbral_holm"])
check("la mas pequena se rechaza si pasa su umbral",
      res["h1"]["rechaza_nula"] is True)
check("en cuanto una NO se rechaza, las siguientes tampoco",
      not res["h3"]["rechaza_nula"] and not res["h4"]["rechaza_nula"],
      f"-> h2={res['h2']['rechaza_nula']}, h3={res['h3']['rechaza_nula']}, "
      f"h4={res['h4']['rechaza_nula']}")

# Cuatro p-valores de 0,02: ninguno pasa 0,05/4 = 0,0125, asi que no se
# rechaza ninguno. Sin correccion, los cuatro parecerian significativos.
res2 = holm({f"h{i}": 0.02 for i in range(1, 5)}, alfa=0.05)
check("cuatro p-valores de 0,02 NO se rechazan tras corregir",
      not any(v["rechaza_nula"] for v in res2.values()),
      "-> sin corregir los cuatro pareceria significativos")

res3 = holm({"solo": 0.04}, alfa=0.05)
check("con una sola hipotesis el umbral es alfa",
      abs(res3["solo"]["umbral_holm"] - 0.05) < 1e-9
      and res3["solo"]["rechaza_nula"])

res4 = holm({"a": 0.001, "b": None}, alfa=0.05)
check("un p-valor no calculable no se rechaza ni arrastra a los demas",
      res4["a"]["rechaza_nula"] and not res4["b"]["rechaza_nula"])


# =====================================================================
print("\n=== 5) RESOLUCION DEL APARATO: que ventaja puede detectar ===")
# =====================================================================

# Esto no es una prueba de pasa/falla: es una MEDICION de lo que este
# montaje es capaz de ver con 15 anos de datos mensuales. Importa porque
# acota lo que cualquier conclusion de este proyecto puede significar.
print(f"         {'ventaja/mes':>12} {'ventaja/ano':>12} {'detectada':>11}")
print("         " + "-" * 36)
rng5 = np.random.default_rng(42)
curva = {}
for mensual in (0.0006, 0.001, 0.002, 0.003, 0.005):
    det, N = 0, 40
    for k in range(N):
        comun = rng5.normal(0.006, 0.040, 179)
        a = nav(comun + rng5.normal(mensual, 0.015, 179))
        b = nav(comun + rng5.normal(0.0, 0.015, 179))
        if contraste_diferencial(a, b, remuestras=300,
                                 semilla=5000 + k)["p_valor_una_cola"] <= 0.05:
            det += 1
    anual = (1 + mensual) ** 12 - 1
    curva[mensual] = det / N
    print(f"         {mensual*100:11.2f}% {anual*100:11.2f}% "
          f"{det/N*100:10.0f}%")

print()
print("         AVISO sobre como leer esta curva. El proceso es SINTETICO")
print("         y lo elegi yo: normales IID con factor comun, 179")
print("         incrementos. Son 40 simulaciones por punto, asi que el")
print("         12% es 5/40 (intervalo 5,5-26,1%) y el 60% es 24/40")
print("         (44,6-73,7%). Y la curva NO incluye la correccion de")
print("         Holm, que empeora la deteccion del procedimiento que de")
print("         verdad se aplica.")
print()
print("         Por eso queda RETIRADA la afirmacion de que 'por debajo de")
print("         un 3-4% anual no se distingue de la suerte': eso seria una")
print("         propiedad del aparato frente al proceso REAL, y aqui no")
print("         hay ninguna medida sobre el proceso real. Lo que queda es")
print("         que en ESTE proceso sintetico un efecto del tamano que")
print("         reclame se confunde con el ruido.")

check("la potencia crece con el tamano del efecto (el contraste discrimina)",
      curva[0.005] > curva[0.002] > curva[0.0006],
      f"-> {[(f'{k*100:.2f}%', f'{v*100:.0f}%') for k, v in curva.items()]}")
check("queda registrado que un efecto de +0,72 puntos/ano es casi "
      "indetectable con esta muestra",
      curva[0.0006] < 0.30,
      f"-> potencia {curva[0.0006]*100:.0f}% para +0,06%/mes. Si fuera alta, "
      f"esta advertencia no haria falta.")


print("\n" + "=" * 62)
print(f"RESULTADO: {OK} pruebas pasadas, {len(FALLOS)} fallos")
for f in FALLOS:
    print(f"  - {f}")
print("=" * 62)

sys.exit(1 if FALLOS else 0)
