"""
EXPERIMENTO: M02 y M03 como ESTRATEGIAS PROPIAS, solo largos, mensual.

=====================================================================
CRITERIOS REGISTRADOS ANTES DE VER NINGUN RESULTADO
=====================================================================

Esto no es "probar cosas hasta que una salga bien". Lo que cuenta como
que funciona esta fijado aqui y no se toca despues:

  1. Retorno anual NETO de costes por encima de COMPRAR Y MANTENER el
     mismo universo equiponderado.
     Batir al efectivo no basta. Si una estrategia gana menos que
     comprar los mismos ETF y no tocarlos, no aporta nada: aporta
     trabajo, riesgo de ejecucion y comisiones.

  2. Y por encima de la referencia de efectivo (BIL).

  3. Y que se mantenga al partir la muestra: primer 60% (train) y
     ultimo 40% (test). Las DOS mitades tienen que batir a comprar y
     mantener de SU propia mitad. Si solo lo hace en una, el dictamen
     es INCONCLUSO, no "funciona".

  4. Se informa Sharpe Y dinero absoluto por separado (caso I29 del
     documento). Mas Sharpe con menos dinero NO se presenta como
     mejora del beneficio.

Si M02/M03 baten al efectivo pero NO a comprar y mantener, el
veredicto es: "es una forma peor de estar invertido", y se dice asi.

=====================================================================
SESGOS QUE ESTE EXPERIMENTO *NO* PUEDE QUITAR
=====================================================================

  - SUPERVIVENCIA DEL UNIVERSO. La lista de tickers es de HOY. Los ETF
    que cerraron no estan. yfinance no da universos historicos, asi
    que esto no se puede arreglar aqui, solo declarar. El efecto
    empuja los resultados HACIA ARRIBA, para todas las variantes y
    tambien para comprar y mantener.

  - CRIPTO. BTC subio de centimos a decenas de miles. Cualquier cosa
    larga sobre BTC parece brillante. Se mide aparte y se informa
    aparte.

  - Un ETF que empieza tarde entra tarde (exige 253 sesiones), lo
    cual SI es correcto: no se puede comprar un fondo que no existia.

=====================================================================
LO QUE SE MIDE ADEMAS: AJUSTADO vs SIN AJUSTAR
=====================================================================

Shark corre con auto_adjust=False, o sea precios SIN ajustar por
dividendos ni splits. En una senal de 12 meses eso no es un detalle:
cada dividendo aparece como una caida que el tenedor no sufrio. Se
mide el mismo experimento con las dos series para ver cuanto cambia.
"""

import json
import os
import sys

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)

for ruta in (PROJECT_ROOT, CURRENT_DIR):
    if ruta not in sys.path:
        sys.path.insert(0, ruta)

import numpy as np
import pandas as pd

import data_feed
from institucional import referencia as R
from institucional.vista import cierres_mensuales

PERIODO = os.getenv("PERIODO_EXP", "15y")
SALIDA_JSON = os.getenv("SALIDA_INST", "resultados/institucional.json")

# Coste por pata, el mismo que usa el backtester de Shark.
COSTE_POR_PATA = 0.0008

# Referencia de efectivo. BIL = letras del Tesoro 1-3 meses.
# Es un BENCHMARK reproducible, no el interes que cobra la cuenta de
# Brian, que es 0%. Las dos cosas se informan.
TICKER_EFECTIVO = "BIL"

# Hipotesis iniciales del documento. No son optimos.
LOOKBACK = 252
SKIP = 21
VENTANA_VOL = 63
K_SELECCION = 5          # posiciones maximas de M03
BANDA_CANDIDATA = 0.02   # un solo valor, fijado aqui, contra banda cero

# Universo: union de las cinco clases que ya medimos con Shark, para
# que la comparacion sea sobre el MISMO terreno.
UNIVERSO = {
    "renta_variable": ["SPY", "QQQ", "IWM", "DIA", "MDY", "XLE", "XLF",
                       "XLK", "XLV", "XLI", "XLP", "XLY", "XLU", "XLB"],
    "materias_primas": ["GLD", "SLV", "USO", "DBC", "DBA", "UNG", "PPLT"],
    "bonos": ["TLT", "IEF", "LQD", "HYG", "SHY"],
    "divisas": ["FXE", "FXY", "FXB", "FXF", "UUP"],
}
# Cripto aparte, por el sesgo.
CRIPTO = ["BTC-USD", "ETH-USD"]


# =====================================================================
# Carga
# =====================================================================

def cargar(tickers, ajustado, providers="yfinance,stooq"):
    data_feed.DATA_PROVIDER_ORDER = [p.strip() for p in providers.split(",")]
    series, fallos = {}, {}
    for t in tickers:
        try:
            if ajustado:
                df, prov = data_feed.get_serie_total_return(t, PERIODO, "1d")
            else:
                df, prov = data_feed.get_data(t, "1d", PERIODO)
            if len(df) < LOOKBACK + 2:
                fallos[t] = f"solo {len(df)} sesiones"
                continue
            series[t] = df
        except Exception as e:
            fallos[t] = f"{type(e).__name__}: {str(e)[:60]}"
    return series, fallos


# =====================================================================
# Motor comun: una cartera mensual, solo largos, con costes
# =====================================================================

def _panel_mensual(series):
    """Cierres mensuales alineados en un DataFrame. No rellena huecos."""
    cierres = {}
    for t, df in series.items():
        m = cierres_mensuales(df)
        s = m["Close"]
        s.index = s.index.normalize().tz_convert("UTC")
        cierres[t] = s
    panel = pd.DataFrame(cierres).sort_index()
    return panel


def _diario_alineado(series):
    diario = {}
    for t, df in series.items():
        s = df["Close"]
        s.index = s.index.normalize().tz_convert("UTC")
        diario[t] = s[~s.index.duplicated(keep="last")]
    return pd.DataFrame(diario).sort_index()


def simular(series, modo, efectivo=None, banda=0.0, k=K_SELECCION):
    """Simula una cartera mensual solo-largos.

    modo:
      "m02"       largo en todo activo con exceso>0 frente al efectivo
      "m03"       los k mejores por momentum 12-1 positivo
      "m02_m03"   los k mejores de entre los que M02 marca LONG
      "comprar"   comprar y mantener equiponderado (benchmark)

    Devuelve dict con la curva de patrimonio y las metricas.
    """
    diario = _diario_alineado(series)
    mensual = _panel_mensual(series)
    if len(mensual) < 15:
        return None

    cash_diario = None
    if efectivo is not None:
        cash_diario = _diario_alineado({"CASH": efectivo})["CASH"]

    fechas = list(mensual.index)
    pesos_actuales = {}
    patrimonio = 1.0
    curva, registro = [], []
    coste_total = 0.0
    n_operaciones = 0

    for i in range(len(fechas) - 1):
        t = fechas[i]
        siguiente = fechas[i + 1]

        # --- decision usando SOLO datos hasta t (inclusive) ---
        hist = diario.loc[diario.index <= t]
        objetivos = {}

        if modo == "comprar":
            vivos = [c for c in mensual.columns
                     if not pd.isna(mensual.loc[t, c])
                     and hist[c].notna().sum() >= LOOKBACK + 1]
            if vivos:
                objetivos = {c: 1.0 / len(vivos) for c in vivos}
        else:
            candidatos, scores = [], {}
            for c in mensual.columns:
                serie_c = hist[c].dropna()
                if len(serie_c) < LOOKBACK + 1:
                    continue

                if modo in ("m02", "m02_m03"):
                    if cash_diario is None:
                        continue
                    cash_c = cash_diario.loc[cash_diario.index <= t].dropna()
                    comun = serie_c.index.intersection(cash_c.index)
                    if len(comun) < max(LOOKBACK, VENTANA_VOL) + 1:
                        continue
                    a = serie_c.loc[comun]
                    b = cash_c.loc[comun]
                    try:
                        senal = R.trend_signal(a.tolist(), b.tolist(),
                                               LOOKBACK, VENTANA_VOL, 252)
                    except R.DataError:
                        continue
                    if senal.side != 1:
                        continue
                    candidatos.append(c)

                if modo in ("m03", "m02_m03"):
                    try:
                        scores[c] = R.momentum_score(serie_c.tolist(),
                                                     LOOKBACK, SKIP)
                    except R.DataError:
                        continue

            if modo == "m02":
                elegidos = tuple(sorted(candidatos))
            elif modo == "m03":
                elegidos = R.rank_positive(scores, k) if scores else ()
            else:  # m02_m03
                filtrados = {c: s for c, s in scores.items() if c in candidatos}
                elegidos = R.rank_positive(filtrados, k) if filtrados else ()

            if elegidos:
                objetivos = {c: 1.0 / len(elegidos) for c in elegidos}

        # --- banda de rebalanceo (M01 D) ---
        if banda > 0:
            efectivos = {}
            for c in set(list(objetivos) + list(pesos_actuales)):
                deseado = objetivos.get(c, 0.0)
                actual = pesos_actuales.get(c, 0.0)
                efectivos[c] = R.buffered_target(actual, deseado, banda)
            total = sum(efectivos.values())
            if total > 1.0:
                efectivos = {c: w / total for c, w in efectivos.items()}
            objetivos = {c: w for c, w in efectivos.items() if w > 1e-12}

        # --- coste de rotacion ---
        rotacion = 0.0
        for c in set(list(objetivos) + list(pesos_actuales)):
            delta = abs(objetivos.get(c, 0.0) - pesos_actuales.get(c, 0.0))
            rotacion += delta
            if delta > 1e-9:
                n_operaciones += 1
        coste = rotacion * COSTE_POR_PATA
        coste_total += coste * patrimonio
        patrimonio *= (1.0 - coste)
        pesos_actuales = objetivos

        # --- retorno del mes siguiente ---
        retorno = 0.0
        for c, w in pesos_actuales.items():
            p0 = mensual.loc[t, c]
            p1 = mensual.loc[siguiente, c]
            if pd.isna(p0) or pd.isna(p1) or p0 <= 0:
                continue
            retorno += w * (p1 / p0 - 1.0)

        # La parte no invertida va al efectivo, con SU rendimiento.
        libre = max(0.0, 1.0 - sum(pesos_actuales.values()))
        if libre > 0 and cash_diario is not None:
            c0 = cash_diario.loc[cash_diario.index <= t]
            c1 = cash_diario.loc[cash_diario.index <= siguiente]
            if len(c0) and len(c1) and c0.iloc[-1] > 0:
                retorno += libre * (c1.iloc[-1] / c0.iloc[-1] - 1.0)

        patrimonio *= (1.0 + retorno)
        curva.append((siguiente, patrimonio))
        registro.append({
            "fecha": str(siguiente.date()),
            "posiciones": len(pesos_actuales),
            "invertido": round(sum(pesos_actuales.values()), 4),
            "retorno_mes": round(retorno, 6),
            "rotacion": round(rotacion, 4),
        })

    return _metricas(curva, registro, coste_total, n_operaciones)


def _metricas(curva, registro, coste_total, n_operaciones):
    if len(curva) < 12:
        return None
    fechas = [c[0] for c in curva]
    valores = np.array([c[1] for c in curva])
    anos = (fechas[-1] - fechas[0]).days / 365.25
    retornos = valores[1:] / valores[:-1] - 1.0

    pico = np.maximum.accumulate(valores)
    drawdown = float(((valores - pico) / pico).min())

    anual = float(valores[-1] ** (1 / anos) - 1) if anos > 0 else float("nan")
    vol = float(retornos.std(ddof=1) * np.sqrt(12)) if len(retornos) > 1 else float("nan")
    sharpe = anual / vol if vol and vol > 0 else float("nan")

    meses_invertido = sum(1 for r in registro if r["invertido"] > 0.01)
    # Dispersion entre periodos: retorno anual de cada ano natural.
    por_ano = {}
    for (f, v), r in zip(curva, registro):
        por_ano.setdefault(f.year, []).append(r["retorno_mes"])
    anuales = {a: float(np.prod([1 + x for x in rs]) - 1)
               for a, rs in por_ano.items() if len(rs) >= 6}

    return {
        "inicio": str(fechas[0].date()),
        "fin": str(fechas[-1].date()),
        "anos": round(anos, 2),
        "patrimonio_final": round(float(valores[-1]), 4),
        "retorno_anual": round(anual, 6),
        "volatilidad_anual": round(vol, 6),
        "sharpe": round(sharpe, 4) if sharpe == sharpe else None,
        "max_drawdown": round(drawdown, 6),
        "meses": len(registro),
        "meses_invertido": meses_invertido,
        "exposicion_media": round(
            float(np.mean([r["invertido"] for r in registro])), 4),
        "posiciones_media": round(
            float(np.mean([r["posiciones"] for r in registro])), 2),
        "rotacion_anual": round(
            float(np.sum([r["rotacion"] for r in registro])) / anos, 3),
        "coste_total_pct_inicial": round(coste_total * 100, 4),
        "intenciones": n_operaciones,
        "coste_por_intencion_pb": round(
            coste_total / n_operaciones * 10000, 2) if n_operaciones else None,
        "retorno_por_ano": {str(a): round(v, 4) for a, v in sorted(anuales.items())},
        "anos_negativos": sum(1 for v in anuales.values() if v < 0),
        "curva": [(str(f.date()), round(float(v), 5)) for f, v in curva],
    }


def partir(series, fraccion=0.6):
    """Corta cada serie en el mismo instante temporal (train/test)."""
    todas = sorted(set().union(*[set(df.index.normalize()) for df in series.values()]))
    corte = todas[int(len(todas) * fraccion)]
    train = {t: df.loc[df.index <= corte] for t, df in series.items()}
    test = {t: df.loc[df.index > corte] for t, df in series.items()}
    return train, test, corte


# =====================================================================
# Ejecucion
# =====================================================================

def bloque(nombre, series, efectivo, resultados):
    print(f"\n{'=' * 70}")
    print(f"{nombre}  ({len(series)} activos)")
    print("=" * 70)

    variantes = {
        "comprar_y_mantener": dict(modo="comprar"),
        "M02_tendencia": dict(modo="m02"),
        "M03_momentum_12_1": dict(modo="m03"),
        "M02_mas_M03": dict(modo="m02_m03"),
        "M03_con_banda": dict(modo="m03", banda=BANDA_CANDIDATA),
    }

    print(f"\n{'VARIANTE':22} {'ANUAL':>8} {'SHARPE':>7} {'MAXDD':>8} "
          f"{'EXPOS':>7} {'ROT/A':>7} {'FINAL':>8}")
    print("-" * 70)

    salida = {}
    for clave, kwargs in variantes.items():
        m = simular(series, efectivo=efectivo, **kwargs)
        if m is None:
            print(f"{clave:22} muestra insuficiente")
            continue
        salida[clave] = m
        print(f"{clave:22} {m['retorno_anual'] * 100:7.2f}% "
              f"{(m['sharpe'] if m['sharpe'] is not None else 0):7.2f} "
              f"{m['max_drawdown'] * 100:7.1f}% "
              f"{m['exposicion_media'] * 100:6.1f}% "
              f"{m['rotacion_anual']:7.2f} {m['patrimonio_final']:8.3f}")

    # Efectivo puro como referencia
    if efectivo is not None:
        m_cash = simular({TICKER_EFECTIVO: efectivo}, modo="comprar")
        if m_cash:
            salida["efectivo_BIL"] = m_cash
            print(f"{'efectivo (BIL)':22} {m_cash['retorno_anual'] * 100:7.2f}% "
                  f"{'':7} {m_cash['max_drawdown'] * 100:7.1f}%")
    print(f"{'cuenta sin remunerar':22} {0.0:7.2f}%   "
          f"(lo que de verdad cobra la cuenta: 0%)")

    # --- los criterios registrados ---
    print(f"\n  CRITERIOS REGISTRADOS")
    bh = salida.get("comprar_y_mantener")
    train, test, corte = partir(series)
    print(f"  corte train/test: {corte.date()}")

    dictamenes = {}
    for clave in ("M02_tendencia", "M03_momentum_12_1", "M02_mas_M03"):
        if clave not in salida or bh is None:
            continue
        v = salida[clave]
        bate_bh = v["retorno_anual"] > bh["retorno_anual"]
        bate_cash = v["retorno_anual"] > salida.get(
            "efectivo_BIL", {"retorno_anual": 0.0})["retorno_anual"]

        modo = {"M02_tendencia": "m02", "M03_momentum_12_1": "m03",
                "M02_mas_M03": "m02_m03"}[clave]
        mitades = {}
        for etiqueta, trozo in (("train", train), ("test", test)):
            ef = efectivo
            if ef is not None:
                ef = ef.loc[ef.index <= corte] if etiqueta == "train" \
                    else ef.loc[ef.index > corte]
            a = simular(trozo, modo=modo, efectivo=ef)
            b = simular(trozo, modo="comprar", efectivo=ef)
            mitades[etiqueta] = {
                "estrategia": a["retorno_anual"] if a else None,
                "comprar": b["retorno_anual"] if b else None,
                "bate": (a and b and a["retorno_anual"] > b["retorno_anual"]),
            }

        ambas = all(m["bate"] for m in mitades.values())
        if bate_bh and bate_cash and ambas:
            veredicto = "PASA"
        elif not bate_bh:
            veredicto = "NO PASA: forma peor de estar invertido"
        elif not bate_cash:
            veredicto = "NO PASA: por debajo del efectivo"
        else:
            veredicto = "INCONCLUSO: no se sostiene en las dos mitades"

        dictamenes[clave] = {
            "bate_comprar_y_mantener": bool(bate_bh),
            "bate_efectivo": bool(bate_cash),
            "mitades": mitades,
            "veredicto": veredicto,
        }
        print(f"\n  {clave}")
        print(f"    anual {v['retorno_anual'] * 100:+.2f}%  vs comprar y "
              f"mantener {bh['retorno_anual'] * 100:+.2f}%  -> "
              f"{'bate' if bate_bh else 'NO bate'}")
        for etq, m in mitades.items():
            if m["estrategia"] is None or m["comprar"] is None:
                print(f"    {etq:5}: muestra insuficiente")
                continue
            print(f"    {etq:5}: {m['estrategia'] * 100:+.2f}% vs "
                  f"{m['comprar'] * 100:+.2f}%  -> "
                  f"{'bate' if m['bate'] else 'NO bate'}")
        print(f"    VEREDICTO: {veredicto}")

        # Caso I29: mas Sharpe con menos dinero se informa, no se vende.
        if (v["sharpe"] is not None and bh["sharpe"] is not None
                and v["sharpe"] > bh["sharpe"] and not bate_bh):
            print(f"    I29: mejor Sharpe ({v['sharpe']:.2f} vs "
                  f"{bh['sharpe']:.2f}) pero MENOS dinero. No es una "
                  f"mejora del beneficio.")

    resultados[nombre] = {"variantes": salida, "dictamenes": dictamenes,
                          "corte_train_test": str(corte.date())}


def main():
    resultados = {
        "periodo": PERIODO,
        "coste_por_pata": COSTE_POR_PATA,
        "parametros": {"lookback": LOOKBACK, "skip": SKIP,
                       "ventana_vol": VENTANA_VOL, "k": K_SELECCION,
                       "banda_candidata": BANDA_CANDIDATA},
        "referencia_efectivo": TICKER_EFECTIVO,
        "criterios_registrados": [
            "bate comprar y mantener del mismo universo equiponderado",
            "y bate la referencia de efectivo",
            "y se sostiene en train (60%) y test (40%) por separado",
        ],
        "sesgos_declarados": [
            "universo de hoy: los ETF cerrados no estan (empuja hacia arriba)",
            "cripto medido aparte por supervivencia extrema",
            "precios ajustados: los fills reales no se hacen a ese nivel",
        ],
        "bloques": {},
    }

    print("=" * 70)
    print("M02 / M03 COMO ESTRATEGIAS PROPIAS — SOLO LARGOS, MENSUAL")
    print("=" * 70)
    print(f"Periodo {PERIODO} | coste {COSTE_POR_PATA * 10000:.0f} pb por pata")
    print(f"Lookback {LOOKBACK} | skip {SKIP} | K {K_SELECCION}")
    print("Solo largos: la cuenta es al contado, sin CFD. No hay cortos.")

    # Efectivo
    efectivo, fallos_cash = cargar([TICKER_EFECTIVO], ajustado=True)
    efectivo = efectivo.get(TICKER_EFECTIVO)
    if efectivo is None:
        print(f"\nAVISO: no se pudo cargar {TICKER_EFECTIVO}: {fallos_cash}")
        print("M02 necesita una referencia de efectivo explicita. El "
              "documento prohibe usar cero para tapar un dato que falta,")
        print("asi que M02 queda sin medir en esta corrida.")

    todos = [t for ts in UNIVERSO.values() for t in ts]
    series, fallos = cargar(todos, ajustado=True)
    print(f"\nCargados {len(series)}/{len(todos)} activos ajustados")
    if fallos:
        for t, m in fallos.items():
            print(f"  sin datos: {t}: {m}")
    resultados["fallos_carga"] = fallos

    bloque("multiactivo_sin_cripto", series, efectivo, resultados["bloques"])

    for clase, tickers in UNIVERSO.items():
        sub = {t: df for t, df in series.items() if t in tickers}
        if len(sub) >= 3:
            bloque(f"clase_{clase}", sub, efectivo, resultados["bloques"])

    cripto, fallos_c = cargar(CRIPTO, ajustado=True, providers="yfinance,coinbase")
    if len(cripto) >= 2:
        bloque("cripto_sesgo_extremo", cripto, efectivo, resultados["bloques"])

    # ---- ajustado vs sin ajustar ----
    print(f"\n{'=' * 70}")
    print("AJUSTADO vs SIN AJUSTAR — cuanto cambia por dividendos y splits")
    print("=" * 70)
    sin_ajustar, _ = cargar(todos, ajustado=False)
    comparacion = {}
    for modo, etiqueta in (("comprar", "comprar_y_mantener"),
                           ("m03", "M03_momentum_12_1")):
        a = simular(series, modo=modo, efectivo=efectivo)
        b = simular(sin_ajustar, modo=modo, efectivo=efectivo)
        if a and b:
            comparacion[etiqueta] = {
                "ajustado": a["retorno_anual"],
                "sin_ajustar": b["retorno_anual"],
                "diferencia_anual": a["retorno_anual"] - b["retorno_anual"],
            }
            print(f"  {etiqueta:24} ajustado {a['retorno_anual'] * 100:+6.2f}%  "
                  f"sin ajustar {b['retorno_anual'] * 100:+6.2f}%  "
                  f"diferencia {(a['retorno_anual'] - b['retorno_anual']) * 100:+.2f} "
                  f"puntos/ano")
    resultados["ajustado_vs_sin_ajustar"] = comparacion
    print("\n  Shark corre SIN ajustar. Esa diferencia es el sesgo que")
    print("  arrastran todos los backtests diarios largos hechos hasta hoy.")

    os.makedirs(os.path.dirname(SALIDA_JSON) or ".", exist_ok=True)
    with open(SALIDA_JSON, "w") as f:
        json.dump(resultados, f, indent=2)
    print(f"\nGuardado en {SALIDA_JSON}")

    # Resumen final honesto
    print(f"\n{'=' * 70}")
    print("RESUMEN")
    print("=" * 70)
    pasan = []
    for nombre, b in resultados["bloques"].items():
        for clave, d in b.get("dictamenes", {}).items():
            if d["veredicto"] == "PASA":
                pasan.append(f"{nombre}/{clave}")
    if pasan:
        print(f"Pasan los criterios registrados: {len(pasan)}")
        for p in pasan:
            print(f"  - {p}")
        print("\nOJO: que pasen los criterios NO autoriza capital. El")
        print("documento exige presupuesto explicito y el modo sigue en")
        print("OBSERVE. Esto es evidencia, no una decision.")
    else:
        print("NINGUNA variante pasa los criterios registrados.")
        print("Eso incluye que ninguna bate a comprar y mantener en las")
        print("dos mitades de la muestra.")


if __name__ == "__main__":
    main()
