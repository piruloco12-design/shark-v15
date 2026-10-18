"""
Pruebas de la contabilidad de costes del backtester.

Existe por un fallo que daba resultados imposibles: expectativa
+0.06 por trade con 37 trades, y a la vez PnL total -13.84.

La causa era que el coste de entrada se restaba del capital al
abrir pero nunca entraba en el pnl del trade, mientras que el de
salida si. Como winrate, expectativa y profit factor se calculan
sobre ese pnl, todas las estadisticas por trade omitian la mitad
de los costes y salian mejores de lo real.

La invariante que se comprueba aqui: la suma de los pnl de los
trades cerrados tiene que cuadrar con la variacion de capital,
salvo los costes de entrada de trades que quedaron abiertos.
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


def activo_en_tendencia(n_dias=40):
    """Tendencia limpia: todas las velas señalizan, todo cierra en TP."""
    marcas = []
    dia = pd.Timestamp("2026-01-05 09:30", tz=TZ_EST)
    while len(marcas) < n_dias * 13:
        if dia.dayofweek < 5:
            for k in range(13):
                marcas.append(dia + pd.Timedelta(minutes=30 * k))
        dia = (dia + pd.Timedelta(days=1)).normalize() + pd.Timedelta(hours=9, minutes=30)

    idx = pd.DatetimeIndex(marcas[: n_dias * 13])
    close = pd.Series([100.0 + 0.5 * i for i in range(len(idx))], index=idx)

    return pd.DataFrame({
        "Open": close, "High": close + 1.0, "Low": close - 1.0, "Close": close,
        "Volume": 1000.0, "atr": 1.0, "rsi": 60.0, "adx": 25.0,
        "ema200": close - 1.0, "macd": 0.5, "macd_signal": 0.2,
    }, index=idx)


df = activo_en_tendencia()
r = bt.run_v16_backtest_single_asset("TEST", df, 1000.0, "COSTES")

trades = r["closed_trades"]
print(f"\nBacktest de prueba: {len(trades)} trades cerrados")


print("\n=== 1) la invariante principal ===")

suma_pnls = sum(t["pnl"] for t in trades)
variacion_capital = r["capital_final"] - r["capital_start"]

# Diferencia legitima: el coste de entrada de un trade que quedara
# abierto al final del periodo.
coste_medio = (sum(t["coste_entrada"] for t in trades) / len(trades)) if trades else 0.0
margen = coste_medio + 0.01

print(f"  suma de pnl de trades : {suma_pnls:+.4f}")
print(f"  variacion de capital  : {variacion_capital:+.4f}")
print(f"  diferencia            : {abs(suma_pnls - variacion_capital):.4f}"
      f"  (margen {margen:.4f})")

check("la suma de los pnl cuadra con la variacion de capital",
      abs(suma_pnls - variacion_capital) <= margen,
      f"-> descuadre {abs(suma_pnls - variacion_capital):.4f}")


print("\n=== 2) cada trade descuenta AMBOS costes ===")

check("todos los trades registran coste de entrada",
      all("coste_entrada" in t for t in trades))
check("todos los trades registran coste de salida",
      all("coste_salida" in t for t in trades))
check("todos los costes de entrada son positivos",
      all(t["coste_entrada"] > 0 for t in trades),
      f"-> {[t['coste_entrada'] for t in trades[:3]]}")

malos = [
    t for t in trades
    if abs(t["pnl"] - (t["pnl_bruto"] - t["coste_salida"] - t["coste_entrada"])) > 1e-9
]
check("pnl = bruto - salida - entrada en todos los trades",
      not malos, f"-> {len(malos)} trades mal")

check("el pnl neto es SIEMPRE menor que el bruto",
      all(t["pnl"] < t["pnl_bruto"] for t in trades))


print("\n=== 3) el fallo viejo quedaria detectado ===")

# Reproduce el calculo antiguo: pnl sin el coste de entrada.
pnls_viejos = [t["pnl_bruto"] - t["coste_salida"] for t in trades]
exp_vieja = sum(pnls_viejos) / len(pnls_viejos)
exp_nueva = suma_pnls / len(trades)

print(f"  expectativa con el calculo viejo : {exp_vieja:+.4f}")
print(f"  expectativa con el calculo nuevo : {exp_nueva:+.4f}")
print(f"  sobreestimacion                  : {exp_vieja - exp_nueva:+.4f} por trade")

check("el calculo viejo sobreestimaba la expectativa",
      exp_vieja > exp_nueva, f"-> vieja {exp_vieja}, nueva {exp_nueva}")
check("la sobreestimacion es el coste medio de entrada",
      abs((exp_vieja - exp_nueva) - coste_medio) < 1e-9,
      f"-> dif {exp_vieja - exp_nueva:.6f}, coste medio {coste_medio:.6f}")


print("\n=== 4) el profit factor tambien cambia ===")

def pf_de(pnls):
    g = sum(p for p in pnls if p > 0)
    p_ = abs(sum(p for p in pnls if p <= 0))
    return g / p_ if p_ > 0 else float("inf")

pnls_nuevos = [t["pnl"] for t in trades]
pf_viejo = pf_de(pnls_viejos)
pf_nuevo = pf_de(pnls_nuevos)

print(f"  PF viejo: {pf_viejo:.4f} | PF nuevo: {pf_nuevo:.4f}")
check("el PF con costes completos no es mejor que el incompleto",
      pf_nuevo <= pf_viejo, f"-> {pf_nuevo} vs {pf_viejo}")


print("\n=== 5) con coste cero los dos calculos coinciden ===")

coste_original = bt.TRADING_COST_PCT
bt.TRADING_COST_PCT = 0.0
r0 = bt.run_v16_backtest_single_asset("TEST", df, 1000.0, "SINCOSTE")
bt.TRADING_COST_PCT = coste_original

t0 = r0["closed_trades"]
check("sin costes, pnl neto == pnl bruto",
      all(abs(t["pnl"] - t["pnl_bruto"]) < 1e-12 for t in t0))
check("sin costes, la suma cuadra exacta",
      abs(sum(t["pnl"] for t in t0)
          - (r0["capital_final"] - r0["capital_start"])) < 1e-9)
check("sin costes el resultado es mejor que con costes",
      sum(t["pnl"] for t in t0) > suma_pnls,
      f"-> {sum(t['pnl'] for t in t0):.2f} vs {suma_pnls:.2f}")


print("\n" + "=" * 62)
print(f"RESULTADO: {OK} pruebas pasadas, {len(FALLOS)} fallos")
for f in FALLOS:
    print(f"  - {f}")
print("=" * 62)

os.unlink(_tmpdb.name)
sys.exit(1 if FALLOS else 0)
