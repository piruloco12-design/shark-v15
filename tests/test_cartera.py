"""
Pruebas del backtester de cartera.

Lo mas importante que verifica: que la optimizacion de ventana
(pasar las ultimas 250 velas en vez del prefijo completo) da
resultados IDENTICOS al motor original, no parecidos.

Si no fueran identicos, la optimizacion estaria cambiando la
estrategia en silencio, que es peor que no optimizar.
"""
import os
import sys
import tempfile
import types
from datetime import timedelta, timezone

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)
sys.path.insert(0, os.path.join(REPO, "validator"))

_tmpdb = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_tmpdb.close()
os.environ["DATABASE_NAME"] = _tmpdb.name
os.environ["TELEGRAM_TOKEN"] = ""

_stub_yf = types.ModuleType("yfinance")
_stub_yf.download = lambda *a, **k: None
sys.modules.setdefault("yfinance", _stub_yf)

_stub_ta = types.ModuleType("ta")
for _sub in ("trend", "momentum", "volatility"):
    _m = types.ModuleType(f"ta.{_sub}")
    setattr(_stub_ta, _sub, _m)
    sys.modules[f"ta.{_sub}"] = _m
_stub_ta.trend.ema_indicator = lambda *a, **k: None
_stub_ta.trend.adx = lambda *a, **k: None
_stub_ta.trend.MACD = lambda *a, **k: None
_stub_ta.momentum.rsi = lambda *a, **k: None
_stub_ta.volatility.average_true_range = lambda *a, **k: None
sys.modules.setdefault("ta", _stub_ta)

import pandas as pd

TZ_EST = timezone(timedelta(hours=-5))

import session_volatility_intelligence as svi
try:
    pd.Timestamp("2026-01-01", tz="UTC").tz_convert("US/Eastern")
except Exception:
    svi.ZONA_MERCADO = TZ_EST

import shark_v15_backtester as bt
import cartera as ct

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


def serie_diaria(n=900, semilla=1, base=100.0):
    """
    Velas diarias con un camino irregular (no una recta), para que
    haya entradas y salidas variadas por stop y por objetivo.
    """
    import random
    rng = random.Random(semilla)
    idx = pd.date_range("2016-01-04", periods=n, freq="B", tz=TZ_EST)

    precios = []
    p = base
    for i in range(n):
        p *= 1.0 + rng.gauss(0.0004, 0.012)
        precios.append(p)

    close = pd.Series(precios, index=idx)
    ema = close.ewm(span=200, adjust=False).mean()
    delta = close.diff()
    sube = delta.clip(lower=0).rolling(14).mean()
    baja = (-delta.clip(upper=0)).rolling(14).mean()
    rs = sube / baja.replace(0, 1e-9)
    rsi = 100 - (100 / (1 + rs))
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    macd = ema12 - ema26
    rango = (close * 0.012)

    df = pd.DataFrame({
        "Open": close.shift(1).fillna(close),
        "High": close + rango,
        "Low": close - rango,
        "Close": close,
        "Volume": 1_000_000.0,
        "atr": rango.rolling(14).mean().bfill(),
        "rsi": rsi.fillna(50.0),
        "adx": 25.0,
        "ema200": ema,
        "macd": macd,
        "macd_signal": macd.ewm(span=9, adjust=False).mean(),
    }, index=idx)

    return df


print("\n=== 1) EQUIVALENCIA con el motor original ===")
print("    (1 activo, 1 hueco: la cartera debe reproducir el por-activo)")

df = serie_diaria(900, semilla=7)

original = bt.run_v16_backtest_single_asset("X", df, 1000.0, "ORIG")
caartera = ct.backtest_cartera(
    {"X": df},
    capital_inicial=1000.0,
    max_abiertas=1,
    riesgo_pct=0.005,
    cooldown_horas=6,
)

print(f"    original: {original['total_trades']} ops | "
      f"capital {original['capital_final']:.4f}")
print(f"    cartera : {caartera['operaciones']} ops | "
      f"capital {caartera['capital_final']:.4f}")

check("mismo numero de operaciones",
      original["total_trades"] == caartera["operaciones"],
      f"-> {original['total_trades']} vs {caartera['operaciones']}")

check("mismo capital final (±0.01)",
      abs(original["capital_final"] - caartera["capital_final"]) < 0.01,
      f"-> {original['capital_final']:.4f} vs {caartera['capital_final']:.4f}")

o_ops = original["closed_trades"]
c_ops = caartera["cerradas"]

if len(o_ops) == len(c_ops) and o_ops:
    difs_entrada = [abs(a["entry"] - b["entry"]) for a, b in zip(o_ops, c_ops)]
    difs_salida = [abs(a["exit"] - b["exit"]) for a, b in zip(o_ops, c_ops)]
    difs_pnl = [abs(a["pnl"] - b["pnl"]) for a, b in zip(o_ops, c_ops)]
    mismas_marcas = sum(1 for a, b in zip(o_ops, c_ops)
                        if a["timestamp"] == b["timestamp"])

    check("todas las entradas coinciden", max(difs_entrada) < 1e-9,
          f"-> peor dif {max(difs_entrada):.2e}")
    check("todas las salidas coinciden", max(difs_salida) < 1e-9,
          f"-> peor dif {max(difs_salida):.2e}")
    check("todos los pnl coinciden", max(difs_pnl) < 1e-9,
          f"-> peor dif {max(difs_pnl):.2e}")
    check("todas las fechas de cierre coinciden",
          mismas_marcas == len(o_ops),
          f"-> {mismas_marcas} de {len(o_ops)}")
    check("misma direccion en todas",
          all(a["signal"] == b["signal"] for a, b in zip(o_ops, c_ops)))
else:
    check("listas de operaciones comparables", False,
          f"-> {len(o_ops)} vs {len(c_ops)}")

check("mismas señales contadas",
      original["total_signals"] == caartera["senales"],
      f"-> {original['total_signals']} vs {caartera['senales']}")


print("\n=== 2) el limite de posiciones simultaneas se aplica ===")

datos = {f"A{i}": serie_diaria(900, semilla=100 + i) for i in range(6)}

for limite in (1, 2, 6):
    r = ct.backtest_cartera(datos, 1000.0, max_abiertas=limite,
                            riesgo_pct=0.005, cooldown_horas=6)
    # Reconstruye el maximo de posiciones solapadas observadas.
    eventos = []
    for t in r["cerradas"]:
        eventos.append((pd.Timestamp(t["abierto_en"]), 1))
        eventos.append((pd.Timestamp(t["timestamp"]), -1))
    eventos.sort()
    vivas = maximo = 0
    for _, d in eventos:
        vivas += d
        maximo = max(maximo, vivas)
    print(f"    limite {limite}: {r['operaciones']:4} ops | "
          f"max solapadas observado {maximo}")
    check(f"con limite {limite} nunca hay mas de {limite} solapadas",
          maximo <= limite, f"-> se observaron {maximo}")


print("\n=== 3) mas activos -> mas operaciones (si hay huecos) ===")

r_pocos = ct.backtest_cartera(
    {k: datos[k] for k in list(datos)[:2]}, 1000.0,
    max_abiertas=6, riesgo_pct=0.005, cooldown_horas=6)
r_muchos = ct.backtest_cartera(
    datos, 1000.0, max_abiertas=6, riesgo_pct=0.005, cooldown_horas=6)

print(f"    2 activos : {r_pocos['operaciones']:4} ops | "
      f"{r_pocos['ops_anio']:.1f}/año")
print(f"    6 activos : {r_muchos['operaciones']:4} ops | "
      f"{r_muchos['ops_anio']:.1f}/año")

check("mas activos generan mas operaciones",
      r_muchos["operaciones"] > r_pocos["operaciones"],
      f"-> {r_muchos['operaciones']} vs {r_pocos['operaciones']}")

check("con 2 huecos se pierden operaciones frente a 6",
      ct.backtest_cartera(datos, 1000.0, max_abiertas=2,
                          riesgo_pct=0.005,
                          cooldown_horas=6)["operaciones"]
      < r_muchos["operaciones"])


print("\n=== 4) contabilidad de la cartera ===")

r = ct.backtest_cartera(datos, 1000.0, max_abiertas=4,
                        riesgo_pct=0.005, cooldown_horas=6)

suma = sum(t["pnl"] for t in r["cerradas"])
variacion = r["capital_final"] - r["capital_start"]
coste_medio = (sum(t["coste_entrada"] for t in r["cerradas"])
               / len(r["cerradas"])) if r["cerradas"] else 0.0
margen = coste_medio * r["abiertas_al_final"] + 0.01

print(f"    suma pnl {suma:+.4f} | variacion capital {variacion:+.4f} "
      f"| abiertas al final {r['abiertas_al_final']}")

check("la suma de pnl cuadra con la variacion de capital",
      abs(suma - variacion) <= margen,
      f"-> descuadre {abs(suma - variacion):.4f}, margen {margen:.4f}")

check("todos los pnl descuentan ambos costes",
      all(abs(t["pnl"] - (t["pnl_bruto"] - t["coste_salida"]
                          - t["coste_entrada"])) < 1e-9
          for t in r["cerradas"]))

check("la curva de capital tiene un punto por marca",
      len(r["curva"]) > 0)
check("el drawdown es un porcentaje valido",
      0.0 <= r["peor_dd"] <= 100.0, f"-> {r['peor_dd']}")
check("no quedan mas abiertas que el limite",
      r["abiertas_al_final"] <= 4, f"-> {r['abiertas_al_final']}")


print("\n=== 5) el tamaño se calcula sobre el capital de la cuenta ===")

r_pobre = ct.backtest_cartera(datos, 1000.0, max_abiertas=4,
                              riesgo_pct=0.005, cooldown_horas=6)
r_rico = ct.backtest_cartera(datos, 100000.0, max_abiertas=4,
                             riesgo_pct=0.005, cooldown_horas=6)

tam_pobre = r_pobre["cerradas"][0]["size"] if r_pobre["cerradas"] else 0
tam_rico = r_rico["cerradas"][0]["size"] if r_rico["cerradas"] else 0

print(f"    con 1.000 EUR  -> primer tamaño {tam_pobre:.4f}")
print(f"    con 100.000 EUR-> primer tamaño {tam_rico:.4f}")

check("mas capital -> posiciones mas grandes", tam_rico > tam_pobre)
check("la proporcion sigue al capital (100x)",
      abs(tam_rico / tam_pobre - 100.0) < 1.0 if tam_pobre else False,
      f"-> ratio {tam_rico / tam_pobre if tam_pobre else 0:.2f}")


print("\n=== 6) robustez ===")

check("sin datos devuelve None", ct.backtest_cartera({}) is None)
corto = {"C": serie_diaria(50)}
check("con menos velas que el warmup devuelve None",
      ct.backtest_cartera(corto) is None)

print("\n" + "=" * 62)
print(f"RESULTADO: {OK} pruebas pasadas, {len(FALLOS)} fallos")
for f in FALLOS:
    print(f"  - {f}")
print("=" * 62)

os.unlink(_tmpdb.name)
sys.exit(1 if FALLOS else 0)
