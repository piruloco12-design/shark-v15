"""
Inferencia sobre retornos, respetando la dependencia temporal.

QUE ESTABA MAL ANTES

`bootstrap_expectativa` remuestreaba el P&L de operaciones de forma
independiente, como si cada operación fuera una observación aislada, y su
`prob_positiva` era la fracción de remuestras con media positiva. La
auditoría lo señaló: eso no es una probabilidad de que exista ventaja ni un
p-valor válido, y menos para una familia de hipótesis.

Dos defectos, y el segundo es el grave:

  1. Barajar operaciones individuales rompe la dependencia temporal. Dos
     operaciones del mismo mes, o de la misma tendencia, no son
     independientes.
  2. Remuestrear la distribución OBSERVADA sin centrarla no da un p-valor
     bajo la hipótesis nula: da un intervalo de confianza. Para un p-valor
     hay que construir la distribución del estadístico CUANDO LA NULA ES
     CIERTA, y eso exige centrar.

AQUI

Bootstrap estacionario (Politis-Romano): bloques de longitud geométrica con
media declarada de antemano, remuestreados SIMULTANEAMENTE para la
estrategia y su referencia, sobre las mismas fechas. Así se conserva tanto
la autocorrelación como la correlación entre las dos series, que es lo que
hace falta para medir un diferencial.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

SEMILLA_POR_DEFECTO = 20261019


def _alinear(estrategia: pd.Series, referencia: pd.Series) -> pd.DataFrame:
    """Retornos de las dos series sobre las MISMAS fechas."""
    a = pd.Series(estrategia).dropna().sort_index()
    b = pd.Series(referencia).dropna().sort_index()
    comun = a.index.intersection(b.index)
    if len(comun) < 24:
        raise ValueError(
            f"solo {len(comun)} observaciones comunes; hacen falta al menos 24")
    df = pd.DataFrame({"estrategia": a.loc[comun], "referencia": b.loc[comun]})
    retornos = df.pct_change().dropna()
    retornos["diferencial"] = retornos["estrategia"] - retornos["referencia"]
    return retornos


def _indices_bloques_estacionarios(n, longitud_media, rng):
    """Índices de un bootstrap estacionario de Politis-Romano.

    La longitud de cada bloque es geométrica con media `longitud_media`, y
    el índice se envuelve circularmente. La longitud media se fija ANTES,
    por regla, no eligiendo la que dé el p-valor más bajo.
    """
    p = 1.0 / max(1.0, float(longitud_media))
    idx = np.empty(n, dtype=np.int64)
    i = 0
    while i < n:
        inicio = rng.integers(0, n)
        largo = min(n - i, int(rng.geometric(p)))
        for k in range(largo):
            idx[i + k] = (inicio + k) % n
        i += largo
    return idx


def contraste_diferencial(
    nav_estrategia: pd.Series,
    nav_referencia: pd.Series,
    *,
    umbral: float = 0.0,
    longitud_bloque_media: float = 12.0,
    remuestras: int = 5000,
    semilla: int = SEMILLA_POR_DEFECTO,
) -> dict:
    """Contrasta si el diferencial medio supera `umbral`.

    Nula: media del retorno diferencial <= umbral.
    Alternativa: media > umbral (una cola; se declara aquí, no después).

    El p-valor se obtiene centrando el diferencial en el umbral, que es lo
    que construye la distribución del estadístico BAJO LA NULA. Sin centrar
    sale un intervalo de confianza, no un p-valor.
    """
    retornos = _alinear(nav_estrategia, nav_referencia)
    d = retornos["diferencial"].to_numpy(dtype="float64")
    n = len(d)
    observado = float(d.mean())

    rng = np.random.default_rng(semilla)
    # Centrado en el umbral: así la nula es cierta en la población
    # remuestreada y el p-valor significa lo que debe significar.
    centrado = d - observado + umbral

    medias = np.empty(remuestras, dtype="float64")
    for r in range(remuestras):
        idx = _indices_bloques_estacionarios(n, longitud_bloque_media, rng)
        medias[r] = centrado[idx].mean()

    # Una cola: P(media remuestreada >= observada | nula cierta)
    p = float((medias >= observado).sum() + 1) / (remuestras + 1)

    # Intervalo de confianza del diferencial, SIN centrar (es otra cosa).
    medias_ic = np.empty(remuestras, dtype="float64")
    rng2 = np.random.default_rng(semilla + 1)
    for r in range(remuestras):
        idx = _indices_bloques_estacionarios(n, longitud_bloque_media, rng2)
        medias_ic[r] = d[idx].mean()

    return {
        "observaciones": n,
        "diferencial_medio_periodico": round(observado, 8),
        "umbral": umbral,
        "p_valor_una_cola": round(p, 6),
        "ic90_diferencial": [round(float(np.percentile(medias_ic, 5)), 8),
                             round(float(np.percentile(medias_ic, 95)), 8)],
        "ic95_diferencial": [round(float(np.percentile(medias_ic, 2.5)), 8),
                             round(float(np.percentile(medias_ic, 97.5)), 8)],
        "metodo": "bootstrap estacionario Politis-Romano, bloques "
                  "simultaneos para estrategia y referencia",
        "longitud_bloque_media": longitud_bloque_media,
        "remuestras": remuestras,
        "semilla": semilla,
        "_nota": (
            "p-valor con el diferencial CENTRADO en el umbral, que es lo que "
            "construye la distribucion bajo la nula. El IC va sin centrar: "
            "son dos cosas distintas y antes se confundian."
        ),
    }


def sensibilidad_bloque(nav_estrategia, nav_referencia, *, umbral=0.0,
                        longitudes=(6.0, 12.0, 24.0), remuestras=2000,
                        semilla=SEMILLA_POR_DEFECTO) -> dict:
    """El p-valor con varias longitudes de bloque, para ver si depende de eso.

    Se informan TODAS. Quedarse con la que dé el p-valor más bajo sería otra
    búsqueda, y la auditoría lo prohíbe expresamente.
    """
    salida = {}
    for L in longitudes:
        r = contraste_diferencial(nav_estrategia, nav_referencia,
                                  umbral=umbral, longitud_bloque_media=L,
                                  remuestras=remuestras, semilla=semilla)
        salida[f"bloque_{L:g}"] = {
            "p_valor": r["p_valor_una_cola"],
            "ic90": r["ic90_diferencial"],
        }
    salida["_nota"] = ("la longitud declarada de antemano es 12; las otras "
                       "son sensibilidad, no alternativas entre las que elegir")
    return salida
