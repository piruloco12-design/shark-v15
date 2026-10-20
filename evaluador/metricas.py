"""
Métricas derivadas del NAV neto diario. Con los nombres correctos.

El evaluador anterior publicaba tres cifras mal:

  - un «Sharpe» que era CAGR partido por volatilidad anualizada. Un Sharpe
    es media de retornos DIFERENCIALES frente a una referencia, dividida por
    la desviación de esos mismos retornos diferenciales. Ni restaba la
    referencia ni usaba la media.
  - un CAGR cuyo numerador incluía el primer rendimiento y cuyo denominador
    empezaba después de ese rendimiento. Verificado: 3,0572% contra 2,9813%
    en un ejemplo de un solo movimiento.
  - una caída máxima medida solo en los puntos mensuales, que no puede ver
    una caída intramensual.

Aquí todo sale de la serie de NAV diario neto, que es una sola fuente, y
cada campo dice en qué unidad está.
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd

SESIONES_ANUALES = 252
MESES_ANUALES = 12


def _serie_limpia(nav: pd.Series) -> pd.Series:
    s = pd.Series(nav).dropna()
    if not isinstance(s.index, pd.DatetimeIndex):
        raise ValueError("el NAV necesita un DatetimeIndex")
    return s.sort_index()


def cagr(nav: pd.Series) -> float:
    """Tasa anual compuesta sobre el intervalo COMPLETO de la serie.

    El NAV tiene que incluir su valor INICIAL, antes de cualquier coste o
    rendimiento. Si la serie empieza después del primer movimiento, ese
    rendimiento está en el numerador y su tiempo no está en el denominador,
    y el resultado sale inflado.
    """
    s = _serie_limpia(nav)
    if len(s) < 2 or s.iloc[0] <= 0:
        return float("nan")
    anos = (s.index[-1] - s.index[0]).days / 365.25
    if anos <= 0:
        return float("nan")
    return float((s.iloc[-1] / s.iloc[0]) ** (1.0 / anos) - 1.0)


def retorno_total(nav: pd.Series) -> float:
    s = _serie_limpia(nav)
    if len(s) < 2 or s.iloc[0] <= 0:
        return float("nan")
    return float(s.iloc[-1] / s.iloc[0] - 1.0)


def drawdown_maximo(nav: pd.Series) -> float:
    """Caída máxima sobre la serie que se le pase.

    Si se le pasa el NAV DIARIO, ve las caídas intramensuales. Si se le pasa
    una serie mensual, solo ve las que coinciden con fin de mes, y eso hay
    que decirlo al informar.
    """
    s = _serie_limpia(nav)
    if len(s) < 2:
        return float("nan")
    v = s.to_numpy(dtype="float64")
    pico = np.maximum.accumulate(v)
    return float(((v - pico) / pico).min())


def sharpe(nav: pd.Series, nav_referencia: pd.Series | None = None,
           tasa_libre_periodica: float = 0.0,
           periodos_por_ano: int = SESIONES_ANUALES) -> dict:
    """Sharpe de verdad: sobre retornos DIFERENCIALES.

    `nav_referencia` es la serie de la referencia frente a la que se mide.
    Si no se da, se usa `tasa_libre_periodica` como tasa constante por
    periodo. Una de las dos tiene que declararse: un Sharpe sin referencia
    declarada no se puede interpretar.
    """
    s = _serie_limpia(nav)
    if len(s) < 3:
        return {"sharpe": None, "motivo": "muestra insuficiente"}

    r = s.pct_change().dropna()
    if nav_referencia is not None:
        ref = _serie_limpia(nav_referencia).reindex(s.index).ffill()
        r_ref = ref.pct_change().reindex(r.index)
        if r_ref.isna().all():
            return {"sharpe": None, "motivo": "referencia no alineable"}
        diferencial = (r - r_ref).dropna()
        etiqueta = "serie de referencia"
    else:
        diferencial = r - float(tasa_libre_periodica)
        etiqueta = f"tasa constante {tasa_libre_periodica:.8f} por periodo"

    if len(diferencial) < 3:
        return {"sharpe": None, "motivo": "pocos retornos diferenciales"}
    desv = float(diferencial.std(ddof=1))
    if not math.isfinite(desv) or desv <= 0:
        return {"sharpe": None, "motivo": "desviación degenerada"}

    media = float(diferencial.mean())
    return {
        "sharpe": round(media / desv * math.sqrt(periodos_por_ano), 4),
        "media_diferencial_periodica": round(media, 8),
        "desviacion_diferencial_periodica": round(desv, 8),
        "periodos": len(diferencial),
        "periodos_por_ano": periodos_por_ano,
        "referencia": etiqueta,
    }


def volatilidad_anual(nav: pd.Series,
                      periodos_por_ano: int = SESIONES_ANUALES) -> float:
    s = _serie_limpia(nav)
    r = s.pct_change().dropna()
    if len(r) < 3:
        return float("nan")
    return float(r.std(ddof=1) * math.sqrt(periodos_por_ano))


def por_ano_natural(nav: pd.Series, nav_inicial=None) -> dict:
    """Retorno de cada año natural, derivado del NAV neto.

    Contrato del plan (cambio 1):

        retorno_año[y] = NAV_ultimo_de_y / NAV_ultimo_anterior_a_y - 1

    La version anterior dividia la ultima observacion del año por la
    PRIMERA del mismo año. Eso borra el tramo que va del cierre de
    diciembre a la primera sesion de enero, que es un retorno real y cae
    en el año nuevo. Con 100 el 31 de diciembre y 110 la primera sesion de
    enero, el año nuevo salia al 0% en vez del +10%.

    Y descartaba entero cualquier año con menos de dos observaciones. Un
    año no se borra: se informa marcado como parcial. Borrarlo rompe
    tambien la identidad de factores, porque su tramo desaparece del
    producto sin desaparecer del NAV.
    """
    s = _serie_limpia(nav)
    if not len(s):
        return {}
    base = float(nav_inicial) if nav_inicial is not None else float(s.iloc[0])
    if not np.isfinite(base) or base <= 0:
        raise ValueError(f"NAV base no admisible: {base!r}")
    salida = {}
    anterior = base
    for ano, trozo in s.groupby(s.index.year):
        ultimo = float(trozo.iloc[-1])
        completo = (trozo.index[0].month == 1 and trozo.index[-1].month == 12)
        factor = ultimo / anterior
        salida[str(ano)] = {
            "retorno": round(factor - 1.0, 6),
            "factor": factor,                 # sin redondear: la identidad
            "completo": bool(completo),       # se comprueba con este
            "observaciones": int(len(trozo)),
            "nav_base": round(anterior, 6),
            "nav_final": round(ultimo, 6),
            "cobertura": "PARCIAL" if not completo else "COMPLETO",
        }
        anterior = ultimo
    return salida


def identidad_de_factores(nav: pd.Series, nav_inicial=None,
                          anual=None, tolerancia=1e-9) -> dict:
    """El producto de los factores anuales debe reproducir el NAV.

    Exigido por el plan: "Exige que el producto de factores periodicos
    coincida con NAV_final/NAV_inicial". Se comprueba dentro de la
    libreria, no solo en una prueba, para que una futura regresion en
    `por_ano_natural` no pase inadvertida.
    """
    s = _serie_limpia(nav)
    if not len(s):
        return {"coincide": True, "anos": 0}
    anual = por_ano_natural(s, nav_inicial) if anual is None else anual
    producto = 1.0
    for ano in sorted(anual):
        producto *= float(anual[ano]["factor"])
    base = float(nav_inicial) if nav_inicial is not None else float(s.iloc[0])
    objetivo = float(s.iloc[-1]) / base
    error = abs(producto - objetivo)
    return {
        "producto_de_factores": producto,
        "nav_final_sobre_inicial": objetivo,
        "error_absoluto": error,
        "coincide": bool(error <= tolerancia * max(1.0, abs(objetivo))),
        "anos": len(anual),
    }


def resumen(nav_diario: pd.Series, *, nav_referencia=None,
            tasa_libre_periodica=0.0, nav_mensual=None,
            etiqueta="") -> dict:
    """Todo junto, con la unidad de cada cifra dicha en su nombre."""
    s = _serie_limpia(nav_diario)
    sh = sharpe(s, nav_referencia, tasa_libre_periodica)

    salida = {
        "etiqueta": etiqueta,
        "inicio": str(s.index[0].date()),
        "fin": str(s.index[-1].date()),
        "anos": round((s.index[-1] - s.index[0]).days / 365.25, 4),
        "nav_inicial": round(float(s.iloc[0]), 6),
        "nav_final": round(float(s.iloc[-1]), 6),
        "retorno_total": round(retorno_total(s), 6),
        "cagr": round(cagr(s), 6),
        "volatilidad_anual_diaria": round(volatilidad_anual(s), 6),
        "max_drawdown_diario": round(drawdown_maximo(s), 6),
        "sharpe_diferencial": sh.get("sharpe"),
        "sharpe_detalle": sh,
        "observaciones_diarias": len(s),
        "retorno_por_ano": por_ano_natural(s),
    }
    if nav_mensual is not None and len(nav_mensual) > 2:
        salida["max_drawdown_mensual"] = round(
            drawdown_maximo(nav_mensual), 6)
        salida["_nota_drawdown"] = (
            "el mensual solo ve caídas que coinciden con fin de mes; el "
            "diario ve también las intramensuales")
    return salida
