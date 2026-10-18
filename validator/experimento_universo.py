"""
EXPERIMENTO: ¿cambia la economía al diversificar entre instrumentos?

LA HIPÓTESIS QUE SE PRUEBA

El análisis de robustez dejó el bot en +0.058 R por operación y 33
operaciones al año = ~1% anual. Para llegar a algo útil hacen
falta más ventaja por operación o muchas más operaciones.

Robert Carver midió que en seguimiento de tendencia, con pesos
iguales, diversificar entre instrumentos multiplica el Sharpe por
~3, y que la curva sigue subiendo a 100 instrumentos
(qoppac.blogspot.com, marzo 2023). SHARK es un sistema de
tendencia.

Esto NO busca más ventaja por operación: busca la misma ventaja
aplicada más veces y menos correlacionada. Y aplicar reglas sin
cambiarlas a instrumentos nuevos no es sobreajustar, es probarlas
fuera de muestra.

EL UNIVERSO, Y POR QUÉ ESTE

Los 4 activos actuales son IWM + NVDA, AMZN y META. Las tres
últimas son mega-caps elegidas en 2026. Backtestear NVDA 15 años
atrás es backtestear la mejor acción grande de la década: no mide
la estrategia, mide que acertamos el ticker mirando el resultado.

Como lo dice la literatura de sesgos de backtest: "una lista de
tickers de hoy es información del futuro".

El universo limpio de aquí abajo son ETFs de índice, sector,
región, bonos y materias primas. Todos existían antes de 2011 y
ninguno está elegido por haber subido: son los vehículos obvios
que cualquiera tenía disponibles entonces. Queda un resto de
sesgo (los ETFs que quebraron no están), pero es pequeño al lado
de elegir NVDA.

USO
    python validator/experimento_universo.py
"""

import json
import os
import sys

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)

for ruta in (PROJECT_ROOT, CURRENT_DIR):
    if ruta not in sys.path:
        sys.path.insert(0, ruta)

from config import CAPITAL
from data_feed import get_data
from indicators import add_indicators
from cartera import backtest_cartera, MIN_WARMUP_BARS
from robustez import bootstrap_expectativa

TIMEFRAME = "1d"
PERIODO = os.getenv("PERIODO_EXP", "15y")

# Los 4 de producción. IWM es un índice; las otras tres son
# mega-caps elegidas hoy, con el sesgo de selección que eso tiene.
UNIVERSO_ACTUAL = ["IWM", "NVDA", "AMZN", "META"]

# ETFs de índice/sector/región/bonos/materias primas, todos
# anteriores a 2011 y ninguno elegido por rentabilidad.
UNIVERSO_LIMPIO = [
    # Índices amplios USA
    "SPY", "QQQ", "IWM", "DIA", "MDY",
    # Sectores USA (SPDR, desde 1998)
    "XLE", "XLF", "XLK", "XLV", "XLI", "XLP", "XLY", "XLU", "XLB",
    # Internacional
    "EFA", "EEM", "EWJ", "EWG", "EWU", "FXI",
    # Renta fija
    "TLT", "IEF", "LQD", "HYG", "SHY",
    # Materias primas
    "GLD", "SLV", "USO", "DBC",
    # Inmobiliario
    "IYR",
]

# Solo renta variable USA: indices amplios + sectores.
#
# Esta division esta elegida POR ADELANTADO y por una razon de
# fondo, no mirando cuales perdieron. Las reglas del bot estan
# calibradas sobre acciones: umbrales fijos de ADX 22 y multiplos
# de ATR. Los bonos cortos (SHY) tienen una volatilidad diminuta y
# las materias primas (USO, DBC) un comportamiento distinto, asi
# que aplicarles los mismos numeros sin reescalar no es una prueba
# justa de la hipotesis de diversificacion.
#
# Carver diversifica con el sistema reescalado por instrumento
# (objetivo de volatilidad y forecast normalizado). Aqui se aplican
# umbrales identicos a todo, asi que el universo homogeneo es el
# que de verdad pone a prueba la idea.
UNIVERSO_ACCIONES = [
    "SPY", "QQQ", "IWM", "DIA", "MDY",
    "XLE", "XLF", "XLK", "XLV", "XLI", "XLP", "XLY", "XLU", "XLB",
]


def cargar(tickers):
    datos = {}
    fallos = []
    for t in tickers:
        try:
            df, _ = get_data(t, TIMEFRAME, PERIODO)
            df = add_indicators(df)
            if df is None or len(df) < MIN_WARMUP_BARS + 100:
                fallos.append(f"{t} (pocas velas)")
                continue
            datos[t] = df
        except Exception as e:
            fallos.append(f"{t} ({type(e).__name__})")
    return datos, fallos


RECOGIDO = []


def fila(nombre, r):
    if r is None or r["operaciones"] == 0:
        print(f"  {nombre:34} sin operaciones")
        return None

    RECOGIDO.append({
        "nombre": nombre,
        "activos": r["activos"],
        "huecos": r["max_abiertas"],
        "riesgo_pct": r["riesgo_pct"],
        "operaciones": r["operaciones"],
        "ops_anio": r["ops_anio"],
        "winrate": r["winrate"],
        "expectativa": r["expectativa"],
        "pf": r["pf"],
        "rent_anual_pct": r["rent_anual_pct"],
        "peor_dd": r["peor_dd"],
    })

    print(f"  {nombre:34} {r['activos']:3}  {r['max_abiertas']:3}  "
          f"{r['riesgo_pct']*100:4.2f}%  {r['operaciones']:5}  "
          f"{r['ops_anio']:6.1f}  {r['winrate']:5.1f}  "
          f"{r['expectativa']:+7.3f}  {r['pf']:5.2f}  "
          f"{r['rent_anual_pct']:+7.2f}  {r['peor_dd']:6.1f}")
    return r


def main():
    print("=" * 110)
    print("EXPERIMENTO DE UNIVERSO — ¿diversificar cambia la economía?")
    print("=" * 110)
    print(f"Timeframe: {TIMEFRAME} | Periodo: {PERIODO} | Capital: {CAPITAL:.0f} EUR")
    print()

    print("Descargando universo de produccion...")
    datos_actual, fallos_a = cargar(UNIVERSO_ACTUAL)
    print(f"  {len(datos_actual)} de {len(UNIVERSO_ACTUAL)} activos"
          + (f" | fallos: {fallos_a}" if fallos_a else ""))

    print("Descargando universo limpio...")
    datos_limpio, fallos_l = cargar(UNIVERSO_LIMPIO)
    print(f"  {len(datos_limpio)} de {len(UNIVERSO_LIMPIO)} activos"
          + (f" | fallos: {fallos_l}" if fallos_l else ""))

    # Subconjunto homogeneo, sin volver a descargar.
    datos_acciones = {t: datos_limpio[t]
                      for t in UNIVERSO_ACCIONES if t in datos_limpio}
    print(f"  de los cuales {len(datos_acciones)} son renta variable USA")

    if not datos_actual and not datos_limpio:
        print("\nSin datos. No se puede experimentar.")
        return 1

    print()
    print("=" * 110)
    print(f"  {'CONFIGURACION':34} {'ACT':>3}  {'HUE':>3}  {'RIESGO':>6}  "
          f"{'OPS':>5}  {'OPS/AÑO':>6}  {'WR%':>5}  {'EXPECT':>7}  "
          f"{'PF':>5}  {'ANUAL%':>7}  {'DD%':>6}")
    print("=" * 110)

    resultados = {}

    if datos_actual:
        print("\n  -- universo de produccion (con sesgo de seleccion) --")
        resultados["actual_2"] = fila(
            "4 activos / 2 huecos (ACTUAL)",
            backtest_cartera(datos_actual, CAPITAL, 2, 0.005))
        resultados["actual_4"] = fila(
            "4 activos / 4 huecos",
            backtest_cartera(datos_actual, CAPITAL, 4, 0.005))

    if datos_limpio:
        print("\n  -- universo limpio de ETFs --")
        resultados["limpio_2"] = fila(
            f"{len(datos_limpio)} ETFs / 2 huecos",
            backtest_cartera(datos_limpio, CAPITAL, 2, 0.005))
        resultados["limpio_6"] = fila(
            f"{len(datos_limpio)} ETFs / 6 huecos",
            backtest_cartera(datos_limpio, CAPITAL, 6, 0.005))
        resultados["limpio_12"] = fila(
            f"{len(datos_limpio)} ETFs / 12 huecos",
            backtest_cartera(datos_limpio, CAPITAL, 12, 0.005))
        resultados["limpio_20"] = fila(
            f"{len(datos_limpio)} ETFs / 20 huecos",
            backtest_cartera(datos_limpio, CAPITAL, 20, 0.005))

    if datos_acciones:
        print("\n  -- solo renta variable USA (universo homogeneo) --")
        print("     (los umbrales del bot estan calibrados sobre acciones;")
        print("      bonos y materias primas necesitarian reescalado)")
        resultados["acciones_2"] = fila(
            f"{len(datos_acciones)} ETFs accion / 2 huecos",
            backtest_cartera(datos_acciones, CAPITAL, 2, 0.005))
        resultados["acciones_6"] = fila(
            f"{len(datos_acciones)} ETFs accion / 6 huecos",
            backtest_cartera(datos_acciones, CAPITAL, 6, 0.005))
        resultados["acciones_6_bajo"] = fila(
            f"{len(datos_acciones)} ETFs accion / 6 huecos / 0.25%",
            backtest_cartera(datos_acciones, CAPITAL, 6, 0.0025))

    if datos_limpio:
        print("\n  -- mismo numero de huecos, riesgo ajustado --")
        print("     (mas posiciones a la vez = mas riesgo total;")
        print("      bajar el riesgo por operacion lo compensa)")
        resultados["limpio_12_bajo"] = fila(
            f"{len(datos_limpio)} ETFs / 12 huecos / 0.25%",
            backtest_cartera(datos_limpio, CAPITAL, 12, 0.0025))
        resultados["limpio_12_alto"] = fila(
            f"{len(datos_limpio)} ETFs / 12 huecos / 1.0%",
            backtest_cartera(datos_limpio, CAPITAL, 12, 0.01))

    print("=" * 110)

    # -----------------------------------------------------------
    # CUELLO DE BOTELLA
    # -----------------------------------------------------------
    mejor = (resultados.get("acciones_6")
             or resultados.get("limpio_12")
             or resultados.get("limpio_6"))
    if mejor:
        print("\n" + "=" * 70)
        print("¿QUE ESTA LIMITANDO LAS OPERACIONES?")
        print("=" * 70)
        for motivo, veces in mejor["motivos"].most_common(6):
            pct = veces / max(mejor["senales"], 1) * 100
            print(f"  {veces:6}x ({pct:5.1f}% de las señales)  {motivo[:60]}")

    # -----------------------------------------------------------
    # SIGNIFICANCIA
    # -----------------------------------------------------------
    if mejor and mejor["operaciones"] >= 30:
        print("\n" + "=" * 70)
        print("¿EL RESULTADO DEL UNIVERSO LIMPIO ES SIGNIFICATIVO?")
        print("=" * 70)
        pnls = [t["pnl"] for t in mejor["cerradas"]]
        b = bootstrap_expectativa(pnls, n=10000)
        print(f"  Operaciones:            {b['n_operaciones']}")
        print(f"  Expectativa observada:  {b['expectativa_real']:+.4f} EUR")
        print(f"  Intervalo 90%:          {b['p05']:+.4f}  a  {b['p95']:+.4f}")
        print(f"  Prob. expectativa > 0:  {b['prob_positiva']*100:.1f}%")
        print()
        if b["p05"] > 0:
            print("  LECTURA: intervalo entero por encima de cero. Es el")
            print("           resultado mas fuerte que esta prueba puede dar.")
        elif b["p95"] < 0:
            # Esta rama faltaba. Sin ella, un resultado
            # CONCLUYENTEMENTE NEGATIVO se reportaba como
            # "no sabemos", que es el error comodo.
            print("  LECTURA: intervalo entero por DEBAJO de cero. Esto no es")
            print("           incertidumbre: es un resultado concluyente en")
            print("           contra. Con esta muestra, la estrategia pierde")
            print("           dinero en este universo, y no por mala suerte.")
        elif b["prob_positiva"] >= 0.95:
            print("  LECTURA: positivo en mas del 95% de los remuestreos.")
        elif b["prob_positiva"] <= 0.05:
            print("  LECTURA: negativo de forma consistente en los")
            print("           remuestreos.")
        else:
            print("  LECTURA: el cero sigue dentro del intervalo. Mas")
            print("           operaciones reducen el ruido, pero no han")
            print("           bastado para demostrar la ventaja.")

    # -----------------------------------------------------------
    # COMPARACION FINAL
    # -----------------------------------------------------------
    print("\n" + "=" * 70)
    print("VEREDICTO")
    print("=" * 70)

    base = resultados.get("actual_2")
    if base and mejor:
        print(f"  Config actual (4 activos / 2 huecos):")
        print(f"    {base['ops_anio']:.1f} ops/año | "
              f"{base['rent_anual_pct']:+.2f}% anual | DD {base['peor_dd']:.1f}%")
        print(f"  Universo limpio diversificado:")
        print(f"    {mejor['ops_anio']:.1f} ops/año | "
              f"{mejor['rent_anual_pct']:+.2f}% anual | DD {mejor['peor_dd']:.1f}%")
        print()

        factor_ops = (mejor["ops_anio"] / base["ops_anio"]
                      if base["ops_anio"] > 0 else 0)
        print(f"  Operaciones por año: x{factor_ops:.1f}")

        if mejor["rent_anual_pct"] > base["rent_anual_pct"]:
            print(f"  Rentabilidad anual: de {base['rent_anual_pct']:+.2f}% "
                  f"a {mejor['rent_anual_pct']:+.2f}%")
        else:
            print(f"  La diversificacion NO mejoro la rentabilidad")
            print(f"  ({base['rent_anual_pct']:+.2f}% -> "
                  f"{mejor['rent_anual_pct']:+.2f}%)")
            print("  Si la ventaja no se mantiene fuera de los 4 activos")
            print("  elegidos, probablemente venia de haberlos elegido.")

        if mejor["rent_anual_pct"] > 0:
            cap = 12000 / (mejor["rent_anual_pct"] / 100)
            print(f"\n  Capital para 1.000 EUR/mes: {cap:>12,.0f} EUR")

    # JSON para el dashboard: datos, no texto parseado.
    salida = {
        "configuraciones": RECOGIDO,
        "cuello_botella": (
            [{"motivo": m, "veces": v,
              "pct_senales": v / max(mejor["senales"], 1) * 100}
             for m, v in mejor["motivos"].most_common(8)]
            if mejor else []
        ),
        "bootstrap": None,
    }
    if mejor and mejor["operaciones"] >= 30:
        b = bootstrap_expectativa([t["pnl"] for t in mejor["cerradas"]], n=10000)
        salida["bootstrap"] = {
            "operaciones": b["n_operaciones"],
            "expectativa": b["expectativa_real"],
            "p05": b["p05"], "p95": b["p95"],
            "prob_positiva": b["prob_positiva"],
        }

    ruta = os.getenv("SALIDA_JSON_UNIVERSO", "resultados/universo.json")
    os.makedirs(os.path.dirname(ruta) or ".", exist_ok=True)
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(salida, f, indent=2, ensure_ascii=False)
    print(f"\n  JSON escrito en {ruta}")

    print("=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(main())
