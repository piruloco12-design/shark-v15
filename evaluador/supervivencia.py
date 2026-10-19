"""
Sesgo de supervivencia: no se corrige, se ACOTA por escenarios.

QUE PREGUNTA RESPONDE

El universo son los 31 ETF que existen hoy. Los que cerraron no están. Yo
dije que ese sesgo «favorece más a M03 porque M03 selecciona». La auditoría
me corrigió: eso no está establecido. Excluir activos desaparecidos cambia
las selecciones y sus trayectorias; algunos pudieron haber sido evitados por
el momentum y otros seleccionados justo antes de caer.

Tiene razón en que no lo sabía. Y se puede medir.

COMO

Se inyectan candidatos MUERTOS con trayectorias declaradas de antemano, se
vuelve a correr la estrategia Y su referencia bajo las mismas hipótesis, y
se mira cómo se mueve el diferencial. Eso da un intervalo de escenarios, no
una corrección estadística del sesgo. La diferencia importa: un escenario
dice «si el mundo fue así, el resultado habría sido este»; una corrección
diría «el resultado verdadero es este». Lo segundo no se puede con estos
datos.

EL PROCESO GENERADOR SE DECLARA ANTES

Y esto es lo que hace que la prueba valga algo. Si eligiera las trayectorias
mirando si ayudan o perjudican a M03, estaría fabricando el resultado. Así
que el proceso está fijado aquí, en el código, y es el mismo para todos los
escenarios:

  Un ETF que cerró tuvo, por el motivo que fuera, un ciclo de vida: nació,
  acumuló algún recorrido, y en algún momento se liquidó. Lo que importa
  para el momentum es que un activo que SUBE entra en la selección. Así
  que la trayectoria adversa interesante es la que sube lo suficiente para
  ser seleccionada y luego se desploma: eso es lo que castiga a quien
  selecciona por fuerza relativa y no a quien compra todo.

  Cada muerto se construye así:
    - vive desde el inicio de la muestra hasta su fecha de liquidación
    - una fase de subida con deriva positiva (lo hace elegible)
    - una fase de caída que termina en el valor de liquidación declarado
    - después de liquidarse, DESAPARECE de la serie: no cotiza más

  Un cierre de ETF NO se sustituye automáticamente por una pérdida del
  100%: los fondos liquidados devuelven su valor liquidativo. El valor de
  recuperación es un parámetro declarado.

QUE NO ES ESTO

No es la magnitud del sesgo real. Para eso hace falta la lista verdadera de
ETF desaparecidos, sus precios y sus liquidaciones, y eso exige
reconstruirla desde documentos del emisor y registros regulatorios. Esto
dice cuánto se movería el resultado SI el mundo hubiera sido como cada
escenario describe.
"""

from __future__ import annotations

import os
import sys

_AQUI = os.path.dirname(os.path.abspath(__file__))
_RAIZ = os.path.dirname(_AQUI)
for _r in (_RAIZ, _AQUI):
    if _r not in sys.path:
        sys.path.insert(0, _r)

import numpy as np
import pandas as pd

VERSION = "2026-10-19.supervivencia.1"

# ---- escenarios, declarados aquí y no ajustados después ----
#
# `fraccion_muertos`: cuántos candidatos desaparecidos se añaden, como
#   fracción del universo superviviente. No es una estimación de la tasa
#   real de cierres de ETF: es un escenario. Tres niveles para ver la
#   sensibilidad, no para elegir el que convenga.
# `recuperacion`: qué fracción del valor conserva el tenedor al liquidarse.
# `anos_vida`: cuánto vive el fondo antes de cerrar.
# `deriva_subida`: la fase que lo hace elegible para el momentum.

ESCENARIOS = {
    "leve": {
        "fraccion_muertos": 0.10,
        "recuperacion": 0.85,
        "anos_vida": 8.0,
        "deriva_subida_anual": 0.12,
        "caida_final": 0.35,
    },
    "moderado": {
        "fraccion_muertos": 0.25,
        "recuperacion": 0.70,
        "anos_vida": 6.0,
        "deriva_subida_anual": 0.20,
        "caida_final": 0.55,
    },
    "severo": {
        "fraccion_muertos": 0.40,
        "recuperacion": 0.50,
        "anos_vida": 5.0,
        "deriva_subida_anual": 0.30,
        "caida_final": 0.75,
    },
}


def construir_muerto(
    nombre: str,
    calendario: pd.DatetimeIndex,
    *,
    anos_vida: float,
    deriva_subida_anual: float,
    caida_final: float,
    recuperacion: float,
    volatilidad_diaria: float,
    semilla: int,
    forma: str = "colapso",
) -> pd.DataFrame:
    """Un ETF que vivió, se deterioró y se liquidó. Y dejó de cotizar.

    DOS FORMAS, y la diferencia no es cosmética:

    `colapso`: sube, entra en la selección por fuerza relativa, y luego se
        desploma. Un rebalanceo mensual puede salirse en cuanto el momentum
        gira; comprar y mantener se lo come entero.

    `desvanecimiento`: nunca sube. Se va deteriorando despacio desde el
        principio hasta que cierra por falta de patrimonio, que es como
        muere la mayoría de los ETF pequeños. El momentum no lo elige
        nunca, así que tampoco le hace falta salirse.

    Las dos formas existen porque el resultado DEPENDE de cuál se use, y
    elegir solo una sería fabricar la conclusión. Con `colapso`, el momentum
    gana algo por salirse a tiempo. Con `desvanecimiento`, no gana nada
    porque nunca entró. Hay que medir las dos y decir que el resultado
    depende de eso.
    """
    rng = np.random.default_rng(semilla)
    sesiones_vida = int(min(len(calendario), anos_vida * 252))
    if sesiones_vida < 300:
        raise ValueError("un muerto con menos de 300 sesiones no es elegible "
                         "para una senal de 252: no probaria nada")

    if forma == "desvanecimiento":
        # Deterioro constante hasta el nivel declarado. Nunca sube, asi que
        # el momentum nunca lo selecciona.
        objetivo = 1.0 - caida_final
        deriva = objetivo ** (1 / sesiones_vida) - 1
        r = rng.normal(deriva, volatilidad_diaria, sesiones_vida)
    elif forma == "colapso":
        # Dos tercios subiendo, un tercio cayendo.
        n_sube = int(sesiones_vida * 2 / 3)
        n_baja = sesiones_vida - n_sube

        deriva_diaria = (1 + deriva_subida_anual) ** (1 / 252) - 1
        r_sube = rng.normal(deriva_diaria, volatilidad_diaria, n_sube)

        # La caída tiene que terminar exactamente en el nivel declarado.
        objetivo = (1.0 - caida_final)
        deriva_baja = objetivo ** (1 / max(1, n_baja)) - 1
        r_baja = rng.normal(deriva_baja, volatilidad_diaria * 1.8, n_baja)
        r = np.concatenate([r_sube, r_baja])
    else:
        raise ValueError(f"forma desconocida: {forma}")
    precios = 100.0 * np.cumprod(1.0 + r)
    precios = np.maximum(precios, 0.01)

    # La liquidación: el tenedor recupera una fracción del último valor.
    # No es cero: un fondo liquidado devuelve su valor liquidativo.
    precios[-1] = precios[-1] * recuperacion

    idx = calendario[:sesiones_vida]
    c = pd.Series(precios, index=idx)
    return pd.DataFrame({
        "Open": c.shift(1).bfill(), "High": c * 1.004, "Low": c * 0.996,
        "Close": c, "Volume": 1e6,
    }, index=idx)


def ampliar_universo(series: dict, escenario: str, *,
                     forma: str = "colapso",
                     semilla_base: int = 909090) -> tuple[dict, dict]:
    """Devuelve (universo ampliado, detalle de los muertos anadidos)."""
    if escenario not in ESCENARIOS:
        raise ValueError(f"escenario desconocido: {escenario}")
    cfg = ESCENARIOS[escenario]

    calendario = pd.DatetimeIndex(
        sorted(set().union(*[set(df.index) for df in series.values()])))
    n_muertos = max(1, int(round(len(series) * cfg["fraccion_muertos"])))

    # Volatilidad típica del universo superviviente, para que los muertos no
    # sean obviamente distintos por su volatilidad.
    vols = []
    for df in series.values():
        r = df["Close"].pct_change().dropna()
        if len(r) > 100:
            vols.append(float(r.std()))
    vol_tipica = float(np.median(vols)) if vols else 0.011

    ampliado = dict(series)
    detalle = {}
    for i in range(n_muertos):
        nombre = f"MUERTO{i+1:02d}"
        df = construir_muerto(
            nombre, calendario,
            anos_vida=cfg["anos_vida"],
            deriva_subida_anual=cfg["deriva_subida_anual"],
            caida_final=cfg["caida_final"],
            recuperacion=cfg["recuperacion"],
            volatilidad_diaria=vol_tipica,
            semilla=semilla_base + i * 17,
            forma=forma,
        )
        ampliado[nombre] = df
        detalle[nombre] = {
            "desde": str(df.index[0].date()),
            "hasta": str(df.index[-1].date()),
            "sesiones": len(df),
            "maximo": round(float(df["Close"].max()), 2),
            "ultimo_tras_liquidar": round(float(df["Close"].iloc[-1]), 2),
            "perdida_desde_maximo": round(
                float(df["Close"].iloc[-1] / df["Close"].max() - 1), 4),
        }
    return ampliado, {
        "escenario": escenario,
        "forma": forma,
        "config": cfg,
        "n_muertos": n_muertos,
        "n_supervivientes": len(series),
        "volatilidad_tipica_usada": round(vol_tipica, 6),
        "muertos": detalle,
    }


def medir(series_reales: dict, politicas, estrategia_factory,
          referencia_factory, *, escenarios=None,
          formas=("colapso", "desvanecimiento")) -> dict:
    """Corre estrategia y referencia con y sin muertos, y compara.

    `estrategia_factory` y `referencia_factory` son funciones sin
    argumentos que devuelven una estrategia nueva, para que cada corrida
    parta de cero.
    """
    from evaluador.mensual import EvaluadorMensual, SinDatosSuficientes

    escenarios = escenarios or list(ESCENARIOS)
    salida = {"version": VERSION, "escenarios": {}}

    # Base: el universo de supervivientes, que es lo que ya medimos.
    ev = EvaluadorMensual(series_reales, politicas)
    base_est = ev.correr(estrategia_factory())
    base_ref = ev.correr(referencia_factory())
    salida["base"] = {
        "activos": len(series_reales),
        "cagr_estrategia": base_est["cagr"],
        "cagr_referencia": base_ref["cagr"],
        "diferencial_cagr": base_est["cagr"] - base_ref["cagr"],
    }

    combinaciones = [(e, f) for f in formas for e in escenarios]
    for nombre_base, forma in combinaciones:
        nombre = f"{nombre_base}/{forma}"
        ampliado, detalle = ampliar_universo(series_reales, nombre_base,
                                             forma=forma)
        try:
            ev2 = EvaluadorMensual(ampliado, politicas)
            est = ev2.correr(estrategia_factory())
            ref = ev2.correr(referencia_factory())
        except SinDatosSuficientes as e:
            salida["escenarios"][nombre] = {"sin_datos": str(e)}
            continue

        dif = est["cagr"] - ref["cagr"]
        # Cuántas veces el momentum eligió un muerto.
        selecciones_muertos = 0
        total_selecciones = 0
        for d in est["_decisiones"]:
            for t in d.pesos_deseados:
                total_selecciones += 1
                if t.startswith("MUERTO"):
                    selecciones_muertos += 1

        salida["escenarios"][nombre] = {
            "detalle_muertos": detalle,
            "cagr_estrategia": est["cagr"],
            "cagr_referencia": ref["cagr"],
            "diferencial_cagr": dif,
            "cambio_en_el_diferencial": dif - salida["base"]["diferencial_cagr"],
            "cambio_estrategia": est["cagr"] - base_est["cagr"],
            "cambio_referencia": ref["cagr"] - base_ref["cagr"],
            "selecciones_de_muertos": selecciones_muertos,
            "selecciones_totales": total_selecciones,
            "pct_selecciones_muertas": round(
                selecciones_muertos / total_selecciones * 100, 2)
            if total_selecciones else 0.0,
        }

    # La pregunta de la auditoría: ¿el sesgo favorece MAS a la estrategia
    # que selecciona, o a la referencia que compra todo?
    cambios = [v["cambio_en_el_diferencial"]
               for v in salida["escenarios"].values()
               if "cambio_en_el_diferencial" in v]
    if cambios:
        salida["dictamen"] = {
            "cambio_minimo_en_el_diferencial": round(min(cambios), 6),
            "cambio_maximo_en_el_diferencial": round(max(cambios), 6),
            "el_sesgo_favorecia_a_la_estrategia": all(c < 0 for c in cambios),
            "el_sesgo_favorecia_a_la_referencia": all(c > 0 for c in cambios),
            "_lectura": (
                "si al anadir muertos el diferencial BAJA en todos los "
                "escenarios, el universo de supervivientes estaba "
                "favoreciendo a la estrategia que selecciona. Si sube, "
                "favorecia a la referencia. Si cambia de signo, depende del "
                "escenario y no se puede afirmar ninguna de las dos cosas."
            ),
        }
    return salida
