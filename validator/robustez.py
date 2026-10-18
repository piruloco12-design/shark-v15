"""
Análisis de robustez: ¿el resultado del backtest significa algo?

POR QUÉ ESTO Y NO MÁS INDICADORES

El backtest da un número. Ese número puede venir de tres sitios:

  1. una ventaja real y repetible
  2. suerte en una muestra pequeña
  3. haber ajustado los parámetros hasta que saliera bonito

Añadir indicadores no distingue entre los tres. Estas tres pruebas
sí, y son la diferencia entre arriesgar dinero sobre algo real y
arriesgarlo sobre un artefacto.

LAS TRES PRUEBAS

1) BOOTSTRAP DE LA EXPECTATIVA
   Remuestrea las operaciones con reemplazo miles de veces y mide
   en qué fracción de los universos la expectativa sale positiva.
   Si de 10.000 remuestreos la expectativa es positiva en el 55%,
   el edge es indistinguible de una moneda. Con 25 operaciones esto
   casi siempre sale indeciso, y eso es información: significa
   "todavía no se sabe", no "funciona".

2) MONTE CARLO DE LA CURVA DE CAPITAL
   Baraja el orden de las operaciones muchas veces. La expectativa
   no cambia al barajar, pero el peor drawdown sí, y mucho. Sirve
   para ver cuánto puede doler una mala racha que sencillamente no
   ocurrió en el orden histórico, y qué probabilidad hay de perder
   un porcentaje dado del capital.

3) BARRIDO DE PARÁMETROS
   Repite el backtest variando los múltiplos de stop y objetivo.
   Si el resultado bueno es un pico aislado rodeado de resultados
   malos, es sobreajuste: la configuración exacta funcionaba por
   casualidad. Si es una meseta (los vecinos también funcionan),
   hay más probabilidad de que sea real.

   Esta es la prueba que dice si la optimización de SL 2.0 / TP 2.5
   encontró algo o se ajustó al ruido.

USO

    python validator/robustez.py
    TIMEFRAME=1d PERIOD=15y python validator/robustez.py
"""

import os
import random
import sys

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

from config import (
    ASSETS,
    TIMEFRAME,
    PERIOD,
    CAPITAL,
    SL_ATR_MULT,
    TP_ATR_MULT,
)

from data_feed import get_data
from indicators import add_indicators

from shark_v15_backtester import (
    run_v16_backtest_single_asset,
    MIN_WARMUP_BARS,
)

N_BOOTSTRAP = int(os.getenv("N_BOOTSTRAP", "10000"))
N_MONTECARLO = int(os.getenv("N_MONTECARLO", "5000"))
SEMILLA = int(os.getenv("SEMILLA", "42"))


# =========================================================
# ESTADÍSTICA
# =========================================================

def _percentil(valores_ordenados, p):
    if not valores_ordenados:
        return 0.0
    k = (len(valores_ordenados) - 1) * (p / 100.0)
    bajo = int(k)
    alto = min(bajo + 1, len(valores_ordenados) - 1)
    peso = k - bajo
    return valores_ordenados[bajo] * (1 - peso) + valores_ordenados[alto] * peso


def bootstrap_expectativa(pnls, n=N_BOOTSTRAP, semilla=SEMILLA):
    """
    Remuestrea las operaciones con reemplazo y devuelve la
    distribución de la expectativa por operación.
    """
    if len(pnls) < 2:
        return None

    rng = random.Random(semilla)
    total = len(pnls)
    expectativas = []

    for _ in range(n):
        muestra = [pnls[rng.randrange(total)] for _ in range(total)]
        expectativas.append(sum(muestra) / total)

    expectativas.sort()

    positivas = sum(1 for e in expectativas if e > 0)

    return {
        "n_operaciones": total,
        "expectativa_real": sum(pnls) / total,
        "media": sum(expectativas) / len(expectativas),
        "p05": _percentil(expectativas, 5),
        "p50": _percentil(expectativas, 50),
        "p95": _percentil(expectativas, 95),
        "prob_positiva": positivas / len(expectativas),
    }


def montecarlo_drawdown(pnls, capital_inicial=CAPITAL,
                        n=N_MONTECARLO, semilla=SEMILLA):
    """
    Baraja el orden de las operaciones y mide el peor drawdown de
    cada universo. Barajar no cambia el resultado final, solo el
    camino: sirve para ver qué racha mala era posible.
    """
    if len(pnls) < 2:
        return None

    rng = random.Random(semilla)
    drawdowns = []
    finales = []
    arruinados = 0

    for _ in range(n):
        orden = pnls[:]
        rng.shuffle(orden)

        capital = capital_inicial
        pico = capital_inicial
        peor_dd = 0.0
        toco_fondo = False

        for pnl in orden:
            capital += pnl
            if capital > pico:
                pico = capital
            dd = (pico - capital) / pico * 100 if pico > 0 else 0.0
            if dd > peor_dd:
                peor_dd = dd
            # "Ruina" práctica: perder la mitad del capital.
            if capital <= capital_inicial * 0.5:
                toco_fondo = True

        drawdowns.append(peor_dd)
        finales.append(capital)
        if toco_fondo:
            arruinados += 1

    drawdowns.sort()
    finales.sort()

    return {
        "dd_mediano": _percentil(drawdowns, 50),
        "dd_p95": _percentil(drawdowns, 95),
        "dd_peor": drawdowns[-1],
        "final_p05": _percentil(finales, 5),
        "final_p50": _percentil(finales, 50),
        "final_p95": _percentil(finales, 95),
        "prob_perder_mitad": arruinados / n,
        "prob_terminar_en_perdida": sum(1 for f in finales if f < capital_inicial) / n,
    }


# =========================================================
# CARGA DE DATOS
# =========================================================

def cargar_datos():
    datos = {}
    print(f"Descargando {TIMEFRAME} / {PERIOD} ...")

    for ticker in ASSETS:
        try:
            df, provider = get_data(ticker, TIMEFRAME, PERIOD)
            df = add_indicators(df)

            if df is None or len(df) < MIN_WARMUP_BARS + 50:
                velas = 0 if df is None else len(df)
                print(f"  {ticker:7} descartado: {velas} velas, "
                      f"hacen falta {MIN_WARMUP_BARS + 50}")
                continue

            datos[ticker] = df
            print(f"  {ticker:7} {provider:10} {len(df):6} velas")

        except Exception as e:
            print(f"  {ticker:7} ERROR: {type(e).__name__}: {e}")

    return datos


def operaciones_de(datos, sl_mult=None, tp_mult=None):
    """Lanza el backtest en cada activo y junta todas las operaciones."""
    todas = []
    for ticker, df in datos.items():
        r = run_v16_backtest_single_asset(
            ticker, df, CAPITAL, "ROBUSTEZ",
            sl_mult=sl_mult, tp_mult=tp_mult,
        )
        todas.extend(r["closed_trades"])
    return todas


# =========================================================
# BARRIDO DE PARÁMETROS
# =========================================================

def barrido_parametros(datos):
    """
    Repite el backtest con distintos múltiplos de stop y objetivo.
    Busca si la configuración actual es un pico o una meseta.
    """
    multiplos_sl = [1.5, 2.0, 2.5, 3.0]
    multiplos_tp = [2.0, 2.5, 3.0, 3.5]

    print(f"\n{'SL':>5} {'TP':>5} {'R:R':>5} {'OPS':>5} {'WR%':>6} "
          f"{'EXPECT':>9} {'PF':>6}  VEREDICTO")
    print("-" * 62)

    resultados = []

    for sl in multiplos_sl:
        for tp in multiplos_tp:
            operaciones = operaciones_de(datos, sl_mult=sl, tp_mult=tp)
            pnls = [t["pnl"] for t in operaciones]

            if not pnls:
                print(f"{sl:5.1f} {tp:5.1f} {tp/sl:5.2f} {0:5}  sin operaciones")
                continue

            ganadoras = [p for p in pnls if p > 0]
            perdedoras = [p for p in pnls if p <= 0]

            wr = len(ganadoras) / len(pnls) * 100
            expectativa = sum(pnls) / len(pnls)
            bruto_ganado = sum(ganadoras) if ganadoras else 0.0
            bruto_perdido = abs(sum(perdedoras)) if perdedoras else 0.0
            pf = bruto_ganado / bruto_perdido if bruto_perdido > 0 else 0.0

            es_actual = (abs(sl - SL_ATR_MULT) < 1e-9 and
                         abs(tp - TP_ATR_MULT) < 1e-9)

            marca = " <-- CONFIG ACTUAL" if es_actual else ""
            signo = "+" if expectativa > 0 else " "

            print(f"{sl:5.1f} {tp:5.1f} {tp/sl:5.2f} {len(pnls):5} {wr:6.1f} "
                  f"{signo}{expectativa:8.4f} {pf:6.2f}{marca}")

            resultados.append({
                "sl": sl, "tp": tp, "operaciones": len(pnls),
                "winrate": wr, "expectativa": expectativa, "pf": pf,
                "es_actual": es_actual,
            })

    return resultados


def interpretar_barrido(resultados):
    if not resultados:
        return

    positivos = [r for r in resultados if r["expectativa"] > 0]
    total = len(resultados)

    print(f"\nCombinaciones con expectativa positiva: "
          f"{len(positivos)} de {total}")

    actual = next((r for r in resultados if r["es_actual"]), None)

    if actual is None:
        return

    print(f"Configuración actual (SL {actual['sl']} / TP {actual['tp']}): "
          f"expectativa {actual['expectativa']:+.4f}, PF {actual['pf']:.2f}")

    # Vecinos: una posición de distancia en la rejilla.
    vecinos = [
        r for r in resultados
        if not r["es_actual"]
        and abs(r["sl"] - actual["sl"]) <= 0.5
        and abs(r["tp"] - actual["tp"]) <= 0.5
    ]

    if not vecinos:
        return

    vecinos_positivos = [v for v in vecinos if v["expectativa"] > 0]

    print(f"Vecinos inmediatos con expectativa positiva: "
          f"{len(vecinos_positivos)} de {len(vecinos)}")

    print()
    if actual["expectativa"] <= 0:
        print("LECTURA: la configuración actual no tiene expectativa positiva")
        print("         en este periodo. Si otras combinaciones sí, ojo: elegir")
        print("         ahora la mejor de la tabla ES sobreajustar.")
    elif len(vecinos_positivos) == 0:
        print("LECTURA: PICO AISLADO. La configuración actual funciona y sus")
        print("         vecinos no. Eso es la firma del sobreajuste: el")
        print("         resultado depende de haber acertado el número exacto,")
        print("         que es justo lo que no se repite fuera de muestra.")
    elif len(vecinos_positivos) >= len(vecinos) * 0.6:
        print("LECTURA: MESETA. La configuración actual y la mayoría de sus")
        print("         vecinos funcionan. No demuestra que haya edge, pero")
        print("         es compatible con que el efecto sea real y no el")
        print("         número exacto elegido.")
    else:
        print("LECTURA: ZONA MIXTA. Ni pico ni meseta clara. Con esta muestra")
        print("         no se puede separar señal de ruido.")


# =========================================================
# INFORME
# =========================================================

def informe_bootstrap(b):
    print("\n" + "=" * 62)
    print("1) BOOTSTRAP DE LA EXPECTATIVA")
    print("=" * 62)

    if b is None:
        print("Hacen falta al menos 2 operaciones.")
        return

    print(f"Operaciones:            {b['n_operaciones']}")
    print(f"Expectativa observada:  {b['expectativa_real']:+.4f} € por operación")
    print(f"Intervalo 90%:          {b['p05']:+.4f}  a  {b['p95']:+.4f}")
    print(f"Prob. expectativa > 0:  {b['prob_positiva'] * 100:.1f}%")
    print()

    p = b["prob_positiva"]
    if b["p05"] > 0:
        print("LECTURA: el intervalo del 90% está entero por encima de cero.")
        print("         Es el resultado más fuerte que esta prueba puede dar.")
    elif b["p95"] < 0:
        print("LECTURA: el intervalo del 90% está entero por debajo de cero.")
        print("         La estrategia pierde, y no por mala suerte.")
    elif p >= 0.95:
        print("LECTURA: expectativa positiva en el 95% de los remuestreos.")
    elif p <= 0.05:
        print("LECTURA: expectativa negativa de forma consistente.")
    else:
        print("LECTURA: INDECISO. El cero está dentro del intervalo, así que")
        print("         esta muestra no distingue la estrategia de una moneda.")
        print("         No significa que no funcione: significa que todavía no")
        print("         se sabe. La única cura es más operaciones.")


def informe_montecarlo(mc):
    print("\n" + "=" * 62)
    print("2) MONTE CARLO DE LA CURVA DE CAPITAL")
    print("=" * 62)

    if mc is None:
        print("Hacen falta al menos 2 operaciones.")
        return

    print(f"Capital inicial:              {CAPITAL:.2f} €")
    print(f"Drawdown mediano:             {mc['dd_mediano']:.2f}%")
    print(f"Drawdown percentil 95:        {mc['dd_p95']:.2f}%")
    print(f"Peor drawdown simulado:       {mc['dd_peor']:.2f}%")
    print()
    print(f"Capital final, percentil 5:   {mc['final_p05']:.2f} €")
    print(f"Capital final, mediana:       {mc['final_p50']:.2f} €")
    print(f"Capital final, percentil 95:  {mc['final_p95']:.2f} €")
    print()
    print(f"Prob. terminar en pérdida:    {mc['prob_terminar_en_perdida'] * 100:.1f}%")
    print(f"Prob. perder la mitad:        {mc['prob_perder_mitad'] * 100:.1f}%")
    print()
    print(f"LECTURA: con estas operaciones en otro orden, el drawdown que hay")
    print(f"         que estar dispuesto a aguantar es del {mc['dd_p95']:.1f}%,")
    print(f"         no el que salió en el histórico. El orden de las")
    print(f"         operaciones es azar; la racha mala no tiene por qué")
    print(f"         haber caído dentro del periodo de prueba.")


def main():
    print("=" * 62)
    print("ANÁLISIS DE ROBUSTEZ — SHARK V15")
    print("=" * 62)
    print(f"Timeframe: {TIMEFRAME} | Periodo: {PERIOD}")
    print(f"Activos: {ASSETS}")
    print(f"Config actual: SL {SL_ATR_MULT} ATR / TP {TP_ATR_MULT} ATR")
    print(f"Bootstrap: {N_BOOTSTRAP} | Monte Carlo: {N_MONTECARLO}")
    print()

    datos = cargar_datos()

    if not datos:
        print("\nSin datos utilizables. No se puede analizar.")
        return 1

    operaciones = operaciones_de(datos)
    pnls = [t["pnl"] for t in operaciones]

    print(f"\nOperaciones totales con la config actual: {len(pnls)}")

    if len(pnls) < 2:
        print("Muy pocas operaciones para cualquier análisis estadístico.")
        print("Eso ya es el resultado: no hay nada que medir.")
        return 0

    if len(pnls) < 30:
        print()
        print(f"AVISO: {len(pnls)} operaciones es una muestra muy pequeña.")
        print("       Por debajo de ~100 los intervalos salen tan anchos que")
        print("       casi cualquier conclusión cabe dentro. Lo que sigue hay")
        print("       que leerlo sabiendo eso.")

    informe_bootstrap(bootstrap_expectativa(pnls))
    informe_montecarlo(montecarlo_drawdown(pnls))

    print("\n" + "=" * 62)
    print("3) BARRIDO DE PARÁMETROS (SL / TP)")
    print("=" * 62)
    interpretar_barrido(barrido_parametros(datos))

    print("\n" + "=" * 62)
    return 0


if __name__ == "__main__":
    sys.exit(main())
