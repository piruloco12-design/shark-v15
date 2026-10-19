"""
Vista inmutable "disponible en el momento de decidir".

El punto de esto es que sea imposible leer una vela que no habia
ocurrido todavia. No es un detalle teorico: el error mas caro de un
backtest es decidir el martes con el cierre del miercoles, y produce
resultados espectaculares que no existen.

La regla: una vela con marca de tiempo t cubre el intervalo que EMPIEZA
en t. Una vela diaria del 2026-03-10 no esta cerrada hasta el final de
ese dia. Por eso el corte usa el final de la vela, no su marca.
"""

from __future__ import annotations

import numpy
import pandas as pd

from institucional.referencia import DataError

# Duracion de cada vela, para saber cuando termina.
DURACION = {
    "1m": pd.Timedelta(minutes=1),
    "5m": pd.Timedelta(minutes=5),
    "15m": pd.Timedelta(minutes=15),
    "30m": pd.Timedelta(minutes=30),
    "1h": pd.Timedelta(hours=1),
    "1d": pd.Timedelta(days=1),
}


def recortar_disponible(df: pd.DataFrame, decision_time, timeframe: str = "1d"):
    """Devuelve solo las velas CERRADAS en decision_time.

    Lanza DataError si el indice no es utilizable, porque decidir con un
    indice ambiguo es peor que no decidir.
    """
    if df is None or len(df) == 0:
        raise DataError("serie vacia")
    if not isinstance(df.index, pd.DatetimeIndex):
        raise DataError("se requiere DatetimeIndex")
    if df.index.tz is None:
        raise DataError("indice sin zona horaria: no se puede comparar")
    if not df.index.is_monotonic_increasing:
        raise DataError("indice desordenado")
    if df.index.has_duplicates:
        raise DataError("indice con marcas duplicadas")

    duracion = DURACION.get(timeframe)
    if duracion is None:
        raise DataError(f"timeframe sin duracion definida: {timeframe}")

    corte = pd.Timestamp(decision_time)
    if corte.tz is None:
        raise DataError("decision_time sin zona horaria")

    # El cierre de la vela t ocurre en t + duracion. Solo vale si ese
    # instante ya paso.
    cerradas = df.index + duracion <= corte
    recortado = df.loc[cerradas]
    if len(recortado) == 0:
        raise DataError(f"ninguna vela cerrada antes de {corte}")
    return recortado


def ultimo_disponible_epoch(df: pd.DataFrame, timeframe: str = "1d") -> int:
    """Momento en que el dato mas reciente de la vista estuvo disponible."""
    duracion = DURACION[timeframe]
    return int((df.index[-1] + duracion).timestamp())


def cierres_mensuales(df: pd.DataFrame) -> pd.DataFrame:
    """Ultima sesion de cada mes. El calendario que usan M02 y M03.

    No se inventan meses que no estan en los datos: si falta un mes
    entero, no aparece, y el llamante vera el hueco.
    """
    if not isinstance(df.index, pd.DatetimeIndex):
        raise DataError("se requiere DatetimeIndex")
    if len(df) == 0:
        return df
    # Ultima fila de cada mes: aquella cuyo mes difiere del de la
    # siguiente fila (y la ultima de todas). Se hace con una mascara
    # para no perder la zona horaria del indice, que es lo que pasa
    # al reconstruir marcas con groupby/apply.
    # OJO: periodo.shift(-1) sobre un PeriodIndex RESTA un mes a cada
    # valor, no mueve posiciones. Usarlo aqui devolvia todas las filas,
    # es decir rebalanceo diario disfrazado de mensual. Se compara por
    # posicion con numpy.
    clave = df.index.year * 100 + df.index.month
    siguiente = numpy.roll(clave, -1)
    ultima_del_mes = clave != siguiente
    ultima_del_mes[-1] = True        # la ultima fila cierra su mes
    return df.loc[ultima_del_mes]
