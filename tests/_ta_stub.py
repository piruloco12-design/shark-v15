"""
Sustituto minimo de la libreria `ta`, SOLO para poder correr pruebas
donde no esta instalada (este contenedor no tiene salida a PyPI).

Implementa exactamente los cinco indicadores que usa indicators.py, con
las formulas estandar: EMA, RSI de Wilder, MACD 12/26/9, ATR de Wilder
y ADX de Wilder.

IMPORTANTE: esto NO sustituye a `ta` en produccion ni en CI. Se instala
solo si `import ta` falla. En CI la libreria real si esta, asi que las
pruebas corren contra ella. Para la prueba de caracterizacion da igual
cual de las dos se use: compara una corrida contra otra, no contra un
valor de referencia, y las dos corridas usan la misma.
"""
import sys
import types

import pandas as pd


def _ema(serie, window):
    return serie.ewm(span=window, min_periods=window, adjust=False).mean()


def ema_indicator(close, window=14, fillna=False):
    return _ema(close, window)


def rsi(close, window=14, fillna=False):
    delta = close.diff()
    subidas = delta.clip(lower=0)
    bajadas = (-delta).clip(lower=0)
    # Wilder: media exponencial con alpha = 1/window
    media_sub = subidas.ewm(alpha=1 / window, min_periods=window,
                            adjust=False).mean()
    media_baj = bajadas.ewm(alpha=1 / window, min_periods=window,
                            adjust=False).mean()
    rs = media_sub / media_baj.replace(0, float("nan"))
    return 100 - (100 / (1 + rs))


class MACD:
    def __init__(self, close, window_slow=26, window_fast=12,
                 window_sign=9, fillna=False):
        self._linea = _ema(close, window_fast) - _ema(close, window_slow)
        self._senal = self._linea.ewm(span=window_sign,
                                      min_periods=window_sign,
                                      adjust=False).mean()

    def macd(self):
        return self._linea

    def macd_signal(self):
        return self._senal


def _rango_verdadero(high, low, close):
    cierre_previo = close.shift(1)
    return pd.concat([
        high - low,
        (high - cierre_previo).abs(),
        (low - cierre_previo).abs(),
    ], axis=1).max(axis=1)


def average_true_range(high, low, close, window=14, fillna=False):
    tr = _rango_verdadero(high, low, close)
    return tr.ewm(alpha=1 / window, min_periods=window, adjust=False).mean()


def adx(high, low, close, window=14, fillna=False):
    subida = high.diff()
    bajada = -low.diff()
    dm_mas = ((subida > bajada) & (subida > 0)) * subida.clip(lower=0)
    dm_menos = ((bajada > subida) & (bajada > 0)) * bajada.clip(lower=0)

    tr = _rango_verdadero(high, low, close)
    atr = tr.ewm(alpha=1 / window, min_periods=window, adjust=False).mean()

    di_mas = 100 * dm_mas.ewm(alpha=1 / window, min_periods=window,
                              adjust=False).mean() / atr
    di_menos = 100 * dm_menos.ewm(alpha=1 / window, min_periods=window,
                                  adjust=False).mean() / atr
    suma = (di_mas + di_menos).replace(0, float("nan"))
    dx = 100 * (di_mas - di_menos).abs() / suma
    return dx.ewm(alpha=1 / window, min_periods=window, adjust=False).mean()


def instalar_si_falta():
    """Instala el sustituto solo si la libreria real no esta."""
    try:
        import ta  # noqa: F401
        return False
    except ImportError:
        pass

    modulo = types.ModuleType("ta")
    trend = types.ModuleType("ta.trend")
    momentum = types.ModuleType("ta.momentum")
    volatility = types.ModuleType("ta.volatility")

    trend.ema_indicator = ema_indicator
    trend.MACD = MACD
    trend.adx = adx
    momentum.rsi = rsi
    volatility.average_true_range = average_true_range

    modulo.trend = trend
    modulo.momentum = momentum
    modulo.volatility = volatility

    sys.modules["ta"] = modulo
    sys.modules["ta.trend"] = trend
    sys.modules["ta.momentum"] = momentum
    sys.modules["ta.volatility"] = volatility
    return True
