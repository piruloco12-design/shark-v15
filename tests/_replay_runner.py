"""
Ejecuta UN ciclo de live_engine con datos sinteticos deterministas y
escupe un JSON canonico de todo lo que decidio.

No es una prueba por si mismo: lo usa tests/test_observacion.py, que lo
corre dos veces (extension OFF y OBSERVE) en procesos SEPARADOS y
compara las dos salidas. Procesos separados a proposito: varios modulos
leen DATABASE_NAME al importarse, y en un solo proceso el estado de la
primera corrida contaminaria la segunda. Si las dos salidas no son
identicas, la ampliacion esta cambiando a B1 y eso es inaceptable.

Uso:  python tests/_replay_runner.py <ruta_db> <modo> <salida_json>
"""
import json
import os
import sys
import types

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

RUTA_DB, MODO, SALIDA = sys.argv[1], sys.argv[2], sys.argv[3]

# --- entorno fijo ANTES de importar nada del proyecto ---
os.environ["DATABASE_NAME"] = RUTA_DB
os.environ["TELEGRAM_TOKEN"] = ""
os.environ["TELEGRAM_CHAT_ID"] = ""
os.environ["ASSETS"] = "AAA,BBB,CCC"
os.environ["TIMEFRAME"] = "30m"
os.environ["MIN_BARS"] = "220"
os.environ["STARTUP_MESSAGE_ENABLED"] = "false"
os.environ["SAVE_ALL_SIGNALS"] = "true"
os.environ["GEMINI_FILTER_ENABLED"] = "false"
os.environ["NOTICIAS_ENABLED"] = "false"
os.environ["INSTITUCIONAL_MODO"] = MODO

sys.modules.setdefault("yfinance", types.ModuleType("yfinance"))

# `ta` no esta instalada en este contenedor (sin salida a PyPI). En CI
# si lo esta y se usa la real; aqui se usa el sustituto. Para esta
# prueba da igual: compara una corrida contra otra, no contra un valor
# de referencia, y las dos usan la misma implementacion.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _ta_stub
USANDO_STUB_TA = _ta_stub.instalar_si_falta()

import pandas as pd

from zona_mercado import zona as _zona
ZONA = _zona()


# ---------------------------------------------------------------
# Datos sinteticos: AAA sube con aceleracion final (debe dar BUY),
# BBB baja (candidato a SELL), CCC lateral (NO_SIGNAL).
# Todo determinista: ni random ni reloj.
# ---------------------------------------------------------------

def _oscila(i, amplitud):
    return amplitud * ((i * 7919 % 101) / 100.0 - 0.5)


def _indice_rth(n):
    """Indice de velas de 30m SOLO en horario regular, dias laborables.

    Los datos reales llegan asi: data_feed recorta a 09:30-16:00 ET de
    lunes a viernes, 13 velas por sesion. Un indice continuo de 30
    minutos pone la ultima vela en una madrugada o un sabado, y
    entonces el filtro de sesion bloquea todo y la prueba no llega
    nunca al bloque que tiene que comprobar.
    """
    marcas = []
    dia = pd.Timestamp("2026-01-05 09:30", tz=ZONA)   # un lunes
    while len(marcas) < n:
        if dia.weekday() < 5:
            for k in range(13):                       # 09:30 .. 15:30
                marcas.append(dia + pd.Timedelta(minutes=30 * k))
                if len(marcas) >= n:
                    break
        dia = (dia + pd.Timedelta(days=1)).normalize() \
            + pd.Timedelta(hours=9, minutes=30)
    idx = pd.DatetimeIndex(marcas[:n]).tz_convert("UTC")
    return idx


def _serie(ticker, n=400):
    if ticker == "AAA":
        base = [100 * (1.0025 ** i) * (1 + _oscila(i, 0.012)) for i in range(n)]
        # Aceleracion en las ultimas velas para disparar reaceleracion.
        for k in range(1, 6):
            base[-k] *= 1.0 + 0.004 * (6 - k)
    elif ticker == "BBB":
        base = [300 * (0.9975 ** i) * (1 + _oscila(i, 0.012)) for i in range(n)]
        for k in range(1, 6):
            base[-k] *= 1.0 - 0.004 * (6 - k)
    else:
        base = [150 * (1 + _oscila(i, 0.03)) for i in range(n)]

    close = pd.Series(base, index=_indice_rth(n))
    return pd.DataFrame({
        "Open": close.shift(1).fillna(close.iloc[0]),
        "High": close * 1.002,
        "Low": close * 0.998,
        "Close": close,
        "Volume": 1_000_000.0,
    }, index=close.index)


SERIES = {t: _serie(t) for t in ("AAA", "BBB", "CCC")}

import live_engine
from indicators import add_indicators

# Series diarias total-return para M02/M03 (solo en OBSERVE las usa).
_DIARIAS = {}
for _t in SERIES:
    _n = 400
    if _t == "AAA":
        _v = [100 * (1.0015 ** i) + _oscila(i, 0.5) for i in range(_n)]
    elif _t == "BBB":
        _v = [300 * (0.9985 ** i) + _oscila(i, 0.5) for i in range(_n)]
    else:
        _v = [150 + _oscila(i, 3.0) for i in range(_n)]
    _idx = pd.date_range("2024-06-03", periods=_n, freq="B", tz="UTC")
    _c = pd.Series(_v, index=_idx)
    _DIARIAS[_t] = pd.DataFrame({"Open": _c, "High": _c * 1.001,
                                 "Low": _c * 0.999, "Close": _c,
                                 "Volume": 1e6}, index=_idx)

_EFECTIVO = pd.DataFrame(
    {"Open": 0, "High": 0, "Low": 0,
     "Close": pd.Series([100 * (1.00008 ** i) + _oscila(i, 0.01)
                         for i in range(400)],
                        index=pd.date_range("2024-06-03", periods=400,
                                            freq="B", tz="UTC")),
     "Volume": 1e6})
for _col in ("Open", "High", "Low"):
    _EFECTIVO[_col] = _EFECTIVO["Close"]


# --- parches: nada de red, nada de Telegram ---
live_engine.get_data = lambda ticker, tf, period: (SERIES[ticker].copy(), "sintetico")
live_engine._send_mobile_signal_message = lambda *a, **k: None
live_engine._send_cycle_ok = lambda *a, **k: None
live_engine._send_error_message = lambda *a, **k: None
live_engine._send_startup_message = lambda *a, **k: None
if hasattr(live_engine, "HISTORIAL_DISPONIBLE"):
    live_engine.HISTORIAL_DISPONIBLE = False

# Datos que la observacion necesita, inyectados por el runner.
from institucional.modulos import m03_ranking as _m03_ranking
live_engine._INST_RANKING = _m03_ranking(
    _DIARIAS, pd.Timestamp("2026-01-20", tz="UTC"), k=2)
live_engine._INST_SERIES_TR = _DIARIAS
live_engine._INST_EFECTIVO = _EFECTIVO

import storage
storage.init_db()

# --- capturar el log ---
LINEAS = []
_log_original = live_engine._log
live_engine._log = lambda msg: (LINEAS.append(str(msg)), _log_original(msg))[0]

live_engine.run_live_cycle()

# --- volcado canonico ---
import sqlite3

# Solo las lineas que reflejan DECISIONES del nucleo. Se quitan las que
# llevan hora o rutas, que cambian entre corridas por motivos que no
# tienen nada que ver con la ampliacion.
PREFIJOS_DECISION = ("AAA |", "BBB |", "CCC |", "AI |", "INTEL |",
                     "SESSION |", "VOL |", "RISK |", "FINAL |", "-->",
                     "SKIP |", "FEED OK", "FEED SKIP")
decisiones = [l for l in LINEAS
              if any(l.strip().startswith(p) for p in PREFIJOS_DECISION)]
# FEED OK lleva el numero de velas, que si debe coincidir, pero no el
# provider ni las archivadas.
decisiones = [l.split(" | ")[0] + " | " + " | ".join(l.split(" | ")[1:])
              for l in decisiones]

conn = sqlite3.connect(RUTA_DB)
conn.row_factory = sqlite3.Row


EXCLUIDAS = {}


def volcar(tabla, aplicar_exclusion=True):
    try:
        filas = conn.execute(f"SELECT * FROM {tabla}").fetchall()
    except sqlite3.OperationalError:
        return None
    if not filas:
        EXCLUIDAS[tabla] = []
        return []
    fuera = columnas_excluidas(filas[0].keys()) if aplicar_exclusion else ()
    EXCLUIDAS[tabla] = sorted(fuera)
    return [{k: f[k] for k in f.keys() if k not in fuera} for f in filas]


# Las columnas de reloj y de id cambian entre corridas porque las dos
# corridas ocurren en instantes distintos, no por la ampliacion. Se
# excluyen de la comparacion, pero la lista se detecta por patron (no a
# mano, que es como se me escapo timestamp_open) y se VUELCA en el JSON
# para que la exclusion sea visible y no un agujero silencioso.
import re

PATRON_RELOJ = re.compile(
    r"(^id$|timestamp|_at$|^fecha|time$|_time$|^hora)", re.IGNORECASE)


def columnas_excluidas(nombres):
    return tuple(n for n in nombres if PATRON_RELOJ.search(n))

resultado = {
    "modo": MODO,
    "ta_sustituida": USANDO_STUB_TA,
    "decisiones": decisiones,
    "signals": volcar("signals"),
    "paper_trades": volcar("paper_trades"),
    "paper_state": volcar("paper_state"),
    "risk_events": volcar("risk_events"),
    # Esta tabla SI debe diferir: existe solo en OBSERVE.
    "columnas_excluidas": EXCLUIDAS,
    "observacion_filas": len(volcar("observacion_institucional", aplicar_exclusion=False) or []),
}

with open(SALIDA, "w") as f:
    json.dump(resultado, f, indent=2, sort_keys=True, default=str)

print(f"[runner] modo={MODO} decisiones={len(decisiones)} "
      f"signals={len(resultado['signals'] or [])} "
      f"trades={len(resultado['paper_trades'] or [])} "
      f"observacion={resultado['observacion_filas']}")
