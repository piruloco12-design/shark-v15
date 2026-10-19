"""
Pruebas de anticipacion: ¿usa el bot informacion del futuro?

Es el riesgo mas peligroso de un backtest porque no deja rastro:
no hay excepcion, no hay numero raro, solo resultados mejores de
lo que la realidad permitiria.

Aqui importa un detalle concreto del diseño: add_indicators()
calcula ema200, rsi, macd, atr y adx sobre la serie ENTERA antes
de empezar el bucle. Si alguno de esos indicadores mirara hacia
delante -una media centrada, una normalizacion global, un
shift negativo- el backtester estaria leyendo el futuro en cada
vela, y nadie se enteraria.

Las dos pruebas de la especificacion (seccion 5.3):

  1. PERTURBACION DEL FUTURO
     Cambiar datos estrictamente posteriores a t. Las decisiones
     en t y anteriores no pueden cambiar.

  2. REPLAY POR PREFIJO
     Calcular con el pipeline alimentado solo hasta t. Debe dar
     lo mismo que la ejecucion completa hasta t.

Si alguna falla, todos los resultados de rentabilidad medidos
hasta ahora quedan en entredicho.
"""
import os
import sys
import tempfile
import types
from datetime import timedelta, timezone

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)
sys.path.insert(0, os.path.join(REPO, "validator"))

_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_db.close()
os.environ["DATABASE_NAME"] = _db.name
os.environ["TELEGRAM_TOKEN"] = ""

_yf = types.ModuleType("yfinance")
_yf.download = lambda *a, **k: None
sys.modules.setdefault("yfinance", _yf)

import pandas as pd
import numpy as np

TZ = timezone(timedelta(hours=-5))

import session_volatility_intelligence as svi
try:
    pd.Timestamp("2026-01-01", tz="UTC").tz_convert("US/Eastern")
except Exception:
    svi.ZONA_MERCADO = TZ

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


def indicadores(df):
    """
    Mismos indicadores que indicators.py, calculados a mano para
    no depender del paquete 'ta' (no instalable en este entorno).

    Todos son causales por definicion: solo miran hacia atras.
    Eso es justo lo que estas pruebas deben CONFIRMAR, no asumir.
    """
    c, h, l = df["Close"], df["High"], df["Low"]
    df = df.copy()
    df["ema200"] = c.ewm(span=200, adjust=False).mean()

    delta = c.diff()
    sube = delta.clip(lower=0).ewm(alpha=1/14, adjust=False).mean()
    baja = (-delta.clip(upper=0)).ewm(alpha=1/14, adjust=False).mean()
    df["rsi"] = 100 - (100 / (1 + sube / baja.replace(0, 1e-9)))

    e12 = c.ewm(span=12, adjust=False).mean()
    e26 = c.ewm(span=26, adjust=False).mean()
    df["macd"] = e12 - e26
    df["macd_signal"] = df["macd"].ewm(span=9, adjust=False).mean()

    tr = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()],
                   axis=1).max(axis=1)
    df["atr"] = tr.ewm(alpha=1/14, adjust=False).mean()
    df["adx"] = 25.0
    return df.bfill()


def serie(n=600, semilla=3):
    import random
    rng = random.Random(semilla)
    idx = pd.date_range("2018-01-02", periods=n, freq="B", tz=TZ)
    precios, p = [], 100.0
    for _ in range(n):
        p *= 1.0 + rng.gauss(0.0005, 0.013)
        precios.append(p)
    c = pd.Series(precios, index=idx)
    r = c * 0.012
    return indicadores(pd.DataFrame({
        "Open": c.shift(1).fillna(c), "High": c + r, "Low": c - r,
        "Close": c, "Volume": 1_000_000.0}, index=idx))


import cartera

def decisiones(df, hasta=None):
    """Operaciones abiertas, como (fecha_apertura, direccion, entrada)."""
    r = cartera.backtest_cartera({"X": df}, 1000.0, max_abiertas=1,
                                 riesgo_pct=0.005, cooldown_horas=6,
                                 hasta=hasta)
    if r is None:
        return []
    return [(t["abierto_en"], t["signal"], round(t["entry"], 8))
            for t in r["cerradas"]]


print("\n=== 1) PERTURBACION DEL FUTURO ===")
print("    Se altera el precio DESPUES de un punto de corte y se")
print("    comprueba que las decisiones anteriores no cambian.")

base = serie()
corte_i = 400
corte_ts = base.index[corte_i]

antes = [d for d in decisiones(base) if pd.Timestamp(d[0]) <= corte_ts]
print(f"    decisiones hasta el corte: {len(antes)}")

for factor, nombre in [(1.5, "subida del 50%"), (0.5, "caida del 50%"),
                       (3.0, "triplicar")]:
    perturbado = base.copy()
    # Solo el futuro estricto
    mascara = perturbado.index > corte_ts
    for col in ("Open", "High", "Low", "Close"):
        perturbado.loc[mascara, col] = perturbado.loc[mascara, col] * factor
    # Recalcular indicadores sobre la serie perturbada: esto es lo
    # que delata una fuga, porque si un indicador mira adelante,
    # los valores ANTES del corte tambien cambiarian.
    perturbado = indicadores(perturbado[["Open", "High", "Low", "Close", "Volume"]])

    despues = [d for d in decisiones(perturbado)
               if pd.Timestamp(d[0]) <= corte_ts]
    check(f"{nombre} en el futuro no cambia el pasado",
          antes == despues,
          f"-> {len(antes)} vs {len(despues)} decisiones")

# Los propios indicadores antes del corte deben ser identicos
perturbado = base.copy()
mascara = perturbado.index > corte_ts
for col in ("Open", "High", "Low", "Close"):
    perturbado.loc[mascara, col] *= 2.0
perturbado = indicadores(perturbado[["Open", "High", "Low", "Close", "Volume"]])

for col in ("ema200", "rsi", "macd", "atr"):
    iguales = np.allclose(base[col].iloc[:corte_i + 1].values,
                          perturbado[col].iloc[:corte_i + 1].values,
                          rtol=1e-12, atol=1e-12, equal_nan=True)
    check(f"{col} antes del corte es inmune al futuro", iguales)


print("\n=== 2) REPLAY POR PREFIJO ===")
print("    Alimentar el pipeline SOLO hasta t debe dar las mismas")
print("    decisiones que la ejecucion completa recortada a t.")

# OJO con que se compara. La primera version de esta prueba
# fallaba en los tres cortes por exactamente una operacion, y la
# causa era el propio test:
#
#   una operacion abierta ANTES del corte y cerrada DESPUES
#   aparece en la lista de cerradas de la ejecucion completa,
#   pero en el prefijo sigue abierta y no aparece.
#
# No era fuga de futuro: era comparar dos listas distintas. La
# comparacion correcta usa solo las operaciones que abren Y
# cierran antes del corte.

def cerradas_antes(df, ts, recortar=None):
    r = cartera.backtest_cartera({"X": df}, 1000.0, max_abiertas=1,
                                 riesgo_pct=0.005, cooldown_horas=6)
    if r is None:
        return []
    return [(t["abierto_en"], t["signal"], round(t["entry"], 8))
            for t in r["cerradas"]
            if pd.Timestamp(t["abierto_en"]) <= ts
            and pd.Timestamp(t["timestamp"]) <= ts]


for corte in (350, 450, 520):
    ts = base.index[corte]

    completa = cerradas_antes(base, ts)

    prefijo_df = indicadores(
        base[["Open", "High", "Low", "Close", "Volume"]].iloc[:corte + 1])
    solo_prefijo = cerradas_antes(prefijo_df, ts)

    check(f"prefijo hasta i={corte} coincide con la completa",
          completa == solo_prefijo,
          f"-> completa {len(completa)}, prefijo {len(solo_prefijo)}")

    # Y que la prueba no sea trivial por estar vacia
    check(f"  (i={corte} compara operaciones reales, no listas vacias)",
          len(completa) > 0, f"-> {len(completa)}")


print("\n=== 3) UNA FUGA DELIBERADA DEBE DETECTARSE ===")
print("    Si estas pruebas no cazan una fuga introducida a mano,")
print("    no sirven para nada. Se mete una y se comprueba.")

con_fuga = base.copy()
# shift(-5) = mirar 5 velas hacia delante. Fuga de manual.
con_fuga["ema200"] = con_fuga["Close"].shift(-5).bfill()

perturbado_fuga = base.copy()
mascara = perturbado_fuga.index > corte_ts
for col in ("Open", "High", "Low", "Close"):
    perturbado_fuga.loc[mascara, col] *= 2.0
perturbado_fuga = indicadores(
    perturbado_fuga[["Open", "High", "Low", "Close", "Volume"]])
perturbado_fuga["ema200"] = perturbado_fuga["Close"].shift(-5).bfill()

iguales_fuga = np.allclose(
    con_fuga["ema200"].iloc[:corte_i + 1].values,
    perturbado_fuga["ema200"].iloc[:corte_i + 1].values,
    rtol=1e-12, atol=1e-12, equal_nan=True)

check("una ema200 con shift(-5) SE DETECTA como fuga",
      not iguales_fuga,
      "-> la prueba no detecto una fuga evidente: la prueba esta mal")

d_lim = decisiones(con_fuga, hasta=corte_ts)
d_lim_p = decisiones(perturbado_fuga, hasta=corte_ts)
print(f"    con la fuga: {len(d_lim)} vs {len(d_lim_p)} decisiones "
      f"antes del corte")

print("\n" + "=" * 62)
print(f"RESULTADO: {OK} pruebas pasadas, {len(FALLOS)} fallos")
for f in FALLOS:
    print(f"  - {f}")
print("=" * 62)

os.unlink(_db.name)
sys.exit(1 if FALLOS else 0)
