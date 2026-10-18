"""
EXPERIMENTO: ¿funcionan las reglas en otras clases de activo?

PREGUNTA

La estrategia pierde dinero en ETFs de renta variable limpios de
sesgo (1265 operaciones, intervalo del 90% entero por debajo de
cero). Pero es un sistema de TENDENCIA, y hay clases de activo con
tendencias historicamente mas largas y limpias que la renta
variable: cripto y materias primas.

Esto no es buscar el universo que de el numero bonito. Es probar
una hipotesis distinta y declarada antes de verla: si el sistema
sirve para algo, deberia servir donde las tendencias son mas
marcadas.

HONESTIDAD SOBRE EL RESULTADO

Lo que se acepta como "funciona" esta fijado de antemano:

  - intervalo del 90% del bootstrap ENTERO por encima de cero
  - y que se mantenga al partir en train/test

Si sale positivo pero con el cero dentro del intervalo, NO cuenta
como que funciona: cuenta como que no se sabe. Y si una clase sale
bien y otras mal, quedarse con la buena es sesgo de seleccion
otra vez.

SESGO EN CRIPTO

Bitcoin tiene el sesgo de supervivencia mas fuerte que existe:
subio de centimos a decenas de miles. Cualquier sistema largo
sobre BTC parece brillante. Por eso:

  - se mide tambien el SHORT por separado
  - se compara contra comprar y mantener, que es la referencia
    honesta: si el bot no bate a no hacer nada, no aporta
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

PERIODO = os.getenv("PERIODO_EXP", "15y")
SALIDA_JSON = os.getenv("SALIDA_JSON", "resultados/clases.json")

# Cada clase: (nombre, tickers, providers a usar)
CLASES = {
    "cripto": {
        "tickers": ["BTC-USD", "ETH-USD", "LTC-USD", "BCH-USD"],
        "providers": "coinbase,yfinance",
        "nota": "24/7. BTC tiene el sesgo de supervivencia mas fuerte que existe.",
    },
    "materias_primas": {
        "tickers": ["GLD", "SLV", "USO", "DBC", "DBA", "UNG", "PPLT"],
        "providers": "yfinance,stooq",
        "nota": "ETFs de materias primas, todos anteriores a 2011.",
    },
    "renta_variable": {
        "tickers": ["SPY", "QQQ", "IWM", "DIA", "MDY",
                    "XLE", "XLF", "XLK", "XLV", "XLI",
                    "XLP", "XLY", "XLU", "XLB"],
        "providers": "yfinance,stooq",
        "nota": "Indices amplios y sectores. El universo que ya perdio.",
    },
    "bonos": {
        "tickers": ["TLT", "IEF", "LQD", "HYG", "SHY"],
        "providers": "yfinance,stooq",
        "nota": "Renta fija. Volatilidad muy distinta a la renta variable.",
    },
    "divisas": {
        "tickers": ["FXE", "FXY", "FXB", "FXF", "UUP"],
        "providers": "yfinance,stooq",
        "nota": "ETFs de divisas contra el dolar.",
    },
}


def cargar(tickers, providers, timeframe="1d"):
    anterior = os.environ.get("DATA_PROVIDER_ORDER")
    os.environ["DATA_PROVIDER_ORDER"] = providers

    # config ya esta importado; se fuerza el orden en data_feed.
    import data_feed
    data_feed.DATA_PROVIDER_ORDER = [p.strip() for p in providers.split(",")]

    datos, fallos = {}, []
    for t in tickers:
        try:
            df, prov = get_data(t, timeframe, PERIODO)
            df = add_indicators(df)
            if df is None or len(df) < MIN_WARMUP_BARS + 100:
                fallos.append(f"{t}: pocas velas ({0 if df is None else len(df)})")
                continue
            datos[t] = df
            print(f"    {t:10} {prov:10} {len(df):6} velas  "
                  f"{df.index[0].date()} -> {df.index[-1].date()}")
        except Exception as e:
            fallos.append(f"{t}: {type(e).__name__}: {str(e)[:60]}")
            print(f"    {t:10} ERROR {type(e).__name__}: {str(e)[:60]}")

    if anterior is not None:
        os.environ["DATA_PROVIDER_ORDER"] = anterior
    return datos, fallos


def comprar_y_mantener(datos, capital):
    """
    Referencia honesta: repartir el capital a partes iguales entre
    los activos y no hacer nada. Si el bot no bate esto, no aporta.
    """
    if not datos:
        return None
    por_activo = capital / len(datos)
    final = 0.0
    for df in datos.values():
        inicio = float(df.iloc[MIN_WARMUP_BARS]["Close"])
        fin = float(df.iloc[-1]["Close"])
        final += por_activo * (fin / inicio)

    dias = max((df.index[-1] - df.index[MIN_WARMUP_BARS]).days
               for df in datos.values())
    anios = dias / 365.25
    anual = ((final / capital) ** (1 / anios) - 1) * 100 if anios > 0 else 0.0
    return {"capital_final": final, "anual_pct": anual, "anios": anios}


def analizar(nombre, info):
    print(f"\n{'=' * 70}")
    print(f"CLASE: {nombre.upper().replace('_', ' ')}")
    print(f"{'=' * 70}")
    print(f"  {info['nota']}")
    print(f"  Descargando con providers: {info['providers']}")

    datos, fallos = cargar(info["tickers"], info["providers"])

    if not datos:
        print(f"  Sin datos utilizables. Fallos: {fallos}")
        return None

    huecos = max(2, min(6, len(datos)))
    r = backtest_cartera(datos, CAPITAL, huecos, 0.005)

    if r is None or r["operaciones"] < 30:
        n = 0 if r is None else r["operaciones"]
        print(f"  Solo {n} operaciones: muestra insuficiente para concluir.")
        return {"clase": nombre, "activos": len(datos), "operaciones": n,
                "concluyente": False}

    pnls = [t["pnl"] for t in r["cerradas"]]
    b = bootstrap_expectativa(pnls, n=10000)
    bh = comprar_y_mantener(datos, CAPITAL)

    largos = [t for t in r["cerradas"] if t["signal"] == "BUY"]
    cortos = [t for t in r["cerradas"] if t["signal"] == "SELL"]

    def resumen(ops):
        if not ops:
            return {"n": 0, "expectativa": 0.0, "wr": 0.0}
        p = [t["pnl"] for t in ops]
        return {
            "n": len(p),
            "expectativa": sum(p) / len(p),
            "wr": sum(1 for x in p if x > 0) / len(p) * 100,
        }

    rl, rc = resumen(largos), resumen(cortos)

    print(f"\n  {len(datos)} activos | {huecos} huecos | "
          f"{r['operaciones']} operaciones en {r['anios']:.1f} años")
    print(f"  Winrate {r['winrate']:.1f}% | PF {r['pf']:.2f} | "
          f"Expectativa {r['expectativa']:+.4f}")
    print(f"  Rentabilidad anual del bot:     {r['rent_anual_pct']:+7.2f}%")
    if bh:
        print(f"  Comprar y mantener (referencia): {bh['anual_pct']:+7.2f}%")
    print(f"  Peor drawdown: {r['peor_dd']:.1f}%")
    print(f"\n  Bootstrap ({b['n_operaciones']} ops):")
    print(f"    Intervalo 90%: {b['p05']:+.4f}  a  {b['p95']:+.4f}")
    print(f"    Prob. expectativa > 0: {b['prob_positiva'] * 100:.1f}%")
    print(f"\n  Largos: {rl['n']:4} ops | exp {rl['expectativa']:+.4f} | "
          f"WR {rl['wr']:.1f}%")
    print(f"  Cortos: {rc['n']:4} ops | exp {rc['expectativa']:+.4f} | "
          f"WR {rc['wr']:.1f}%")

    # Criterio fijado ANTES de ver el resultado.
    funciona = b["p05"] > 0
    bate_bh = bool(bh and r["rent_anual_pct"] > bh["anual_pct"])

    print()
    if funciona and bate_bh:
        print("  >>> PASA EL CRITERIO: intervalo entero por encima de cero")
        print("      Y bate a comprar y mantener.")
    elif funciona:
        print("  >>> Intervalo por encima de cero, pero NO bate a comprar y")
        print("      mantener. Mas trabajo y mas riesgo para menos resultado.")
    elif b["p95"] < 0:
        print("  >>> CONCLUYENTE EN CONTRA: intervalo entero por debajo de cero.")
    else:
        print("  >>> NO CONCLUYENTE: el cero esta dentro del intervalo.")

    return {
        "clase": nombre,
        "nota": info["nota"],
        "activos": len(datos),
        "tickers": sorted(datos.keys()),
        "fallos": fallos,
        "huecos": huecos,
        "operaciones": r["operaciones"],
        "anios": r["anios"],
        "ops_anio": r["ops_anio"],
        "winrate": r["winrate"],
        "pf": r["pf"],
        "expectativa": r["expectativa"],
        "rent_anual_pct": r["rent_anual_pct"],
        "peor_dd": r["peor_dd"],
        "boot_p05": b["p05"],
        "boot_p95": b["p95"],
        "boot_prob_positiva": b["prob_positiva"],
        "buy_hold_anual_pct": bh["anual_pct"] if bh else None,
        "largos": rl,
        "cortos": rc,
        "concluyente": True,
        "pasa_criterio": bool(funciona and bate_bh),
        "concluyente_en_contra": bool(b["p95"] < 0),
    }


def main():
    print("=" * 70)
    print("EXPERIMENTO POR CLASE DE ACTIVO")
    print("=" * 70)
    print(f"Periodo: {PERIODO} | Capital: {CAPITAL:.0f} EUR | Timeframe: 1d")
    print()
    print("Criterio de exito, fijado ANTES de ver los resultados:")
    print("  1. intervalo del 90% del bootstrap entero por encima de cero")
    print("  2. y que bata a comprar y mantener")

    salida = []
    for nombre, info in CLASES.items():
        try:
            r = analizar(nombre, info)
            if r:
                salida.append(r)
        except Exception as e:
            print(f"\n  ERROR en {nombre}: {type(e).__name__}: {e}")

    print("\n" + "=" * 70)
    print("RESUMEN")
    print("=" * 70)
    print(f"  {'CLASE':18} {'OPS':>5} {'EXPECT':>9} {'ANUAL%':>8} "
          f"{'B&H%':>8} {'P(>0)':>7}  VEREDICTO")
    for r in salida:
        if not r.get("concluyente"):
            print(f"  {r['clase']:18} {r['operaciones']:5}  muestra insuficiente")
            continue
        bh = r["buy_hold_anual_pct"]
        if r["pasa_criterio"]:
            v = "PASA"
        elif r["concluyente_en_contra"]:
            v = "en contra"
        elif r["boot_p05"] > 0:
            v = "positivo, no bate B&H"
        else:
            v = "no concluyente"
        print(f"  {r['clase']:18} {r['operaciones']:5} "
              f"{r['expectativa']:+9.4f} {r['rent_anual_pct']:+8.2f} "
              f"{bh if bh is not None else 0:+8.2f} "
              f"{r['boot_prob_positiva']*100:6.1f}%  {v}")

    pasan = [r for r in salida if r.get("pasa_criterio")]
    print()
    if pasan:
        print(f"  Clases que pasan el criterio: "
              f"{', '.join(r['clase'] for r in pasan)}")
        print("  OJO: una sola clase que pasa de cinco probadas puede ser")
        print("  casualidad. Antes de creerselo hay que partirla en")
        print("  train/test y comprobar que aguanta.")
    else:
        print("  Ninguna clase pasa el criterio fijado de antemano.")

    os.makedirs(os.path.dirname(SALIDA_JSON) or ".", exist_ok=True)
    with open(SALIDA_JSON, "w", encoding="utf-8") as f:
        json.dump({"periodo": PERIODO, "capital": CAPITAL,
                   "clases": salida}, f, indent=2, ensure_ascii=False)
    print(f"\n  JSON escrito en {SALIDA_JSON}")

    print("=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(main())
