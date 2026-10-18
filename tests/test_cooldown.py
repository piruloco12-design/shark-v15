"""
Verifica que el backtester aplique el cooldown por activo igual
que lo aplica el bot en real.

Construye un activo sintetico en tendencia perfecta: todas las
velas generan senal BUY y todos los trades acaban en take profit.
Sin cooldown deberia entrar sin parar; con cooldown, no mas de un
trade cada 6 horas.
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

# El paquete 'ta' no es instalable en este entorno. El DataFrame
# sintetico ya trae los indicadores calculados, asi que solo hace
# falta que el import no falle.
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
    svi.ZONA_MERCADO = TZ_EST   # sin tzdata en este entorno

import shark_v15_backtester as bt
from config import COOLDOWN_HOURS_PER_ASSET

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
    """
    Velas de 30m solo en horario regular (13 por dia), precio
    subiendo de forma constante. ATR fijo a 1.0, asi que el take
    profit (+2.5 ATR) se alcanza 5 velas despues de entrar.
    """
    marcas = []
    dia = pd.Timestamp("2026-01-05 09:30", tz=TZ_EST)
    puestos = 0
    while puestos < n_dias * 13:
        if dia.dayofweek < 5:
            for k in range(13):
                marcas.append(dia + pd.Timedelta(minutes=30 * k))
                puestos += 1
        dia = (dia + pd.Timedelta(days=1)).normalize() + pd.Timedelta(hours=9, minutes=30)

    idx = pd.DatetimeIndex(marcas[: n_dias * 13])
    close = pd.Series([100.0 + 0.5 * i for i in range(len(idx))], index=idx)

    return pd.DataFrame({
        "Open": close,
        "High": close + 1.0,
        "Low": close - 1.0,
        "Close": close,
        "Volume": 1000.0,
        "atr": 1.0,
        "rsi": 60.0,
        "adx": 25.0,
        "ema200": close - 1.0,
        "macd": 0.5,
        "macd_signal": 0.2,
    }, index=idx)


df = activo_en_tendencia()
print(f"\nActivo sintetico: {len(df)} velas, "
      f"{df.index[0].date()} -> {df.index[-1].date()}")
print(f"Cooldown configurado: {COOLDOWN_HOURS_PER_ASSET}h\n")

print("=== sin cooldown (comportamiento viejo) ===")
bt.APLICAR_COOLDOWN = False
sin = bt.run_v16_backtest_single_asset("TEST", df, 1000.0, "SIN")
print(f"  trades: {sin['total_trades']} | señales: {sin['total_signals']}")

print("\n=== con cooldown (comportamiento real del bot) ===")
bt.APLICAR_COOLDOWN = True
con = bt.run_v16_backtest_single_asset("TEST", df, 1000.0, "CON")
print(f"  trades: {con['total_trades']} | señales: {con['total_signals']}")
print(f"  bloqueos por cooldown: "
      f"{con['block_reasons'].get(f'Cooldown por activo ({COOLDOWN_HOURS_PER_ASSET}h)', 0)}")

print()
check("sin cooldown genera trades", sin["total_trades"] > 0, f"-> {sin['total_trades']}")
check("el cooldown REDUCE el numero de trades",
      con["total_trades"] < sin["total_trades"],
      f"-> con={con['total_trades']} sin={sin['total_trades']}")
check("el cooldown aparece como motivo de bloqueo",
      any("Cooldown" in r for r in con["block_reasons"]),
      f"-> {dict(con['block_reasons'])}")

# Ningun par de trades consecutivos a menos de 6h de distancia.
marcas = [pd.Timestamp(t["timestamp"]) for t in con["closed_trades"]]
margenes = [(marcas[i] - marcas[i - 1]).total_seconds() / 3600.0
            for i in range(1, len(marcas))]
peor = min(margenes) if margenes else None
check("ningun trade reentra antes de las 6h",
      peor is None or peor >= COOLDOWN_HOURS_PER_ASSET,
      f"-> separacion minima {peor}h")

sin_marcas = [pd.Timestamp(t["timestamp"]) for t in sin["closed_trades"]]
sin_margenes = [(sin_marcas[i] - sin_marcas[i - 1]).total_seconds() / 3600.0
                for i in range(1, len(sin_marcas))]
print(f"\n  separacion minima entre trades: "
      f"sin cooldown {min(sin_margenes):.1f}h | con cooldown {peor:.1f}h")

dias = len(df) / 13.0
print(f"  trades por dia: sin {sin['total_trades']/dias:.2f} | "
      f"con {con['total_trades']/dias:.2f}")

print("\n" + "=" * 62)
print(f"RESULTADO: {OK} pruebas pasadas, {len(FALLOS)} fallos")
if FALLOS:
    for f in FALLOS:
        print(f"  - {f}")
print("=" * 62)

os.unlink(_tmpdb.name)
sys.exit(1 if FALLOS else 0)
