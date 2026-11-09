"""
Mide B1 sobre el panel REAL del bot en vivo, no sobre el snapshot de ETFs.

POR QUE EXISTE
--------------
Todas las mediciones de `b1_al_contado.py` usan el panel de 32 ETFs de
`resultados/v2/prices_snapshot.csv`. De los cuatro instrumentos que el bot
opera de verdad (`config.ASSETS` = IWM, NVDA, AMZN, META) ahi solo aparece
IWM.

Consecuencia que esto obliga a asumir: el hallazgo de las 180 operaciones
condenadas --objetivo de beneficio menor que la comision de ida y vuelta,
179 de ellas en BIL-- es un artefacto de ESE panel. BIL es un fondo de
letras del Tesoro con un recorrido diario mediano del 0,011% y NO esta en
el panel en vivo. El filtro de viabiliad sigue siendo correcto como regla
general, pero sobre NVDA, AMZN y META casi no bloqueara nada.

Este validador mide el bot que existe.

QUE COMPARA
-----------
30m contra 1d, con el MISMO motor de medicion (`b1_al_contado.correr`), la
MISMA contabilidad por `CuentaContado` y la MISMA reconciliacion. Si el
dano esta en el marco temporal --el stop comido por el ruido en barras de
30 minutos-- se vera en la esperanza NETA por operacion.

LIMITE DURO DE DATOS
--------------------
Yahoo solo sirve ~60 dias de intradia. Asi que las dos ramas NO cubren la
misma ventana: 30m cubre semanas y 1d cubre anos. Por eso la cifra que se
compara es la esperanza NETA POR OPERACION, que es homogenea entre
ventanas distintas, y NO el NAV, que depende del largo de la ventana.

Para quitar el confundido de "ventanas distintas = mercados distintos", se
reporta ademas el subconjunto de operaciones diarias abiertas DENTRO de la
ventana de 30m. Es un recorte posterior de la lista de operaciones, no
otra corrida, asi que no necesita calentamiento aparte.

NO SE PUEDE CORRER EN EL CONTENEDOR DE CLAUDE
---------------------------------------------
El proxy bloquea Yahoo y Stooq (403) y pip no alcanza PyPI, asi que
`yfinance` no esta instalado. Por eso `data_feed` se importa TARDE, dentro
de `_descargar`: asi este modulo se puede importar y probar sin red, y la
descarga la ejecuta el CI de GitHub, que si tiene red abierta.

`PV_SINTETICO=1` genera series sinteticas con volatilidades realistas para
ejercitar todo el camino de medicion sin red. Sirve para verificar la
fontaneria, NO para sacar conclusiones de mercado.
"""

import io
import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

import numpy as np
import pandas as pd

from validator.b1_al_contado import (correr, CALENTAMIENTO,
                                     MULTIPLO_VIABILIDAD)
from config import COSTE_POR_PATA

COLUMNAS = ["Open", "High", "Low", "Close", "Volume"]

MARCOS = [m.strip() for m in
          os.environ.get("PV_MARCOS", "30m,1d").split(",") if m.strip()]
PERIODOS = {
    "30m": os.environ.get("PV_PERIODO_30M", "60d"),
    "1h": os.environ.get("PV_PERIODO_1H", "60d"),
    "1d": os.environ.get("PV_PERIODO_1D", "5y"),
}
SINTETICO = os.environ.get("PV_SINTETICO") == "1"

# Volatilidad diaria mediana aproximada, SOLO para el modo sintetico.
# No son mediciones: son ordenes de magnitud para que la fontaneria se
# ejercite con rangos realistas.
VOL_SINTETICA = {"NVDA": 0.030, "META": 0.025, "AMZN": 0.020,
                 "IWM": 0.009, "SPY": 0.005, "BIL": 0.0001}


def _descargar(activos, marco, periodo):
    """Baja OHLCV por activo. Importa data_feed TARDE a proposito."""
    from data_feed import get_data          # requiere red; no en Claude
    series, fallos = {}, {}
    for t in activos:
        try:
            df, fuente = get_data(t, marco, periodo)
            df = df[[c for c in COLUMNAS if c in df.columns]].copy()
            df = df.sort_index()
            if len(df) <= CALENTAMIENTO + 50:
                fallos[t] = (f"solo {len(df)} barras; hacen falta mas de "
                             f"{CALENTAMIENTO + 50}")
                continue
            series[t] = df
            print(f"    {t:6} {marco:4} {len(df):>6} barras desde {fuente}"
                  f"  [{df.index[0]} .. {df.index[-1]}]")
        except Exception as e:
            fallos[t] = f"{type(e).__name__}: {str(e)[:120]}"
            print(f"    {t:6} {marco:4} FALLO  {fallos[t]}")
    return series, fallos


def _sinteticas(activos, marco, barras=1400, semilla=20261109):
    """Series sinteticas para ejercitar el camino de medicion sin red.

    Las ventanas imitan las REALES: las dos acaban hoy, la de 30m cubre
    las ultimas semanas y la diaria varios anos, asi que se solapan. La
    primera version generaba las dos desde la misma fecha de inicio con
    frecuencia distinta, y entonces no se solapaban nunca y el recorte de
    misma ventana quedaba sin ejercitar: el trozo de codigo mas delicado
    era justo el unico que la prueba no tocaba.
    """
    rng = np.random.default_rng(semilla)
    por_dia = {"30m": 13, "1h": 7, "1d": 1}.get(marco, 1)
    dias = int(np.ceil(barras / por_dia))
    habiles = pd.bdate_range(end=pd.Timestamp.now("UTC").normalize(),
                             periods=dias, tz="UTC")
    if por_dia > 1:
        idx = pd.DatetimeIndex([
            d + pd.Timedelta(minutes=30 * k + 570)
            for d in habiles for k in range(por_dia)])[-barras:]
    else:
        idx = habiles[-barras:]
    barras = len(idx)
    series = {}
    for i, t in enumerate(activos):
        vol_dia = VOL_SINTETICA.get(t, 0.015)
        vol_barra = vol_dia / (por_dia ** 0.5)
        r = rng.normal(0.0, vol_barra, barras)
        cierre = 100.0 * np.exp(np.cumsum(r))
        apertura = np.concatenate([[cierre[0]], cierre[:-1]])
        rango = np.abs(rng.normal(0.0, vol_barra, barras)) * cierre
        alto = np.maximum(apertura, cierre) + rango
        bajo = np.minimum(apertura, cierre) - rango
        series[t] = pd.DataFrame(
            {"Open": apertura, "High": alto, "Low": bajo, "Close": cierre,
             "Volume": rng.integers(1e5, 1e7, barras)}, index=idx)
    return series, {}


def _recorte_misma_ventana(ops_diarias, series_30m):
    """Operaciones diarias abiertas dentro de la ventana de 30m."""
    if not series_30m or not ops_diarias:
        return None
    inicios = [df.index[CALENTAMIENTO] for df in series_30m.values()]
    finales = [df.index[-1] for df in series_30m.values()]
    desde, hasta = min(inicios), max(finales)
    dentro = []
    for o in ops_diarias:
        try:
            f = pd.Timestamp(o["abierta_en"])
            if f.tzinfo is None and desde.tzinfo is not None:
                f = f.tz_localize("UTC")
            elif f.tzinfo is not None and desde.tzinfo is None:
                f = f.tz_localize(None)
        except Exception:
            continue
        if desde <= f <= hasta:
            dentro.append(o)
    if not dentro:
        return {"ventana": [str(desde), str(hasta)], "operaciones": 0,
                "nota": "ninguna operacion diaria cae en la ventana de 30m"}
    netos = [o["pnl_neto"] for o in dentro]
    return {
        "ventana": [str(desde), str(hasta)],
        "operaciones": len(dentro),
        "esperanza_neta_por_operacion": sum(netos) / len(netos),
        "ganadoras_netas": sum(1 for x in netos if x > 0),
        "pnl_neto_total": sum(netos),
    }


def main():
    from config import ASSETS
    # OJO: en el CI, `PV_ACTIVOS: ${{ github.event.inputs.assets }}` llega
    # como cadena VACIA en los eventos push, no sin definir. Un
    # os.environ.get(..., defecto) devuelve "" en ese caso y la lista sale
    # vacia: el validador correria sin ningun activo. De ahi el `or`.
    crudo = os.environ.get("PV_ACTIVOS", "").strip() or ",".join(ASSETS)
    activos = [a.strip().upper() for a in crudo.split(",") if a.strip()]
    if not activos:
        print("ERROR: lista de activos vacia. No se mide nada.")
        return 1

    print("=" * 70)
    print("B1 SOBRE EL PANEL EN VIVO DEL BOT")
    print("=" * 70)
    print(f"  activos: {', '.join(activos)}")
    print(f"  marcos:  {', '.join(MARCOS)}")
    print(f"  filtro de viabilidad: "
          f"{MULTIPLO_VIABILIDAD if MULTIPLO_VIABILIDAD > 0 else 'APAGADO'}")
    if SINTETICO:
        print("  *** MODO SINTETICO: fontaneria, NO resultados de mercado ***")
    print()

    salida = {"activos": activos, "sintetico": SINTETICO,
              "multiplo_viabilidad": MULTIPLO_VIABILIDAD, "resultados": {}}
    ops_por_marco, series_por_marco = {}, {}

    for marco in MARCOS:
        periodo = PERIODOS.get(marco, "1y")
        print(f"  descargando {marco} (periodo {periodo}) ...")
        if SINTETICO:
            series, fallos = _sinteticas(activos, marco)
        else:
            series, fallos = _descargar(activos, marco, periodo)
        series_por_marco[marco] = series

        if not series:
            # Fallar RUIDOSAMENTE. Un panel vacio produciria 0 operaciones
            # y un NAV de exactamente 1000, que tiene pinta de resultado.
            salida["resultados"][marco] = {
                "error": "ningun activo descargado", "fallos": fallos}
            print(f"    SIN DATOS para {marco}. No se mide.\n")
            continue

        r = correr(COSTE_POR_PATA, 0.0, etiqueta=f"panel_vivo_{marco}",
                   series=series)
        ops_por_marco[marco] = r.pop("_operaciones", [])
        r["fallos_de_descarga"] = fallos
        r["barras_por_activo"] = {t: len(df) for t, df in series.items()}
        r["ventana"] = [str(min(df.index[0] for df in series.values())),
                        str(max(df.index[-1] for df in series.values()))]
        # RECONCILIACION. Misma exigencia que en el otro validador: si
        # la variacion del NAV no cuadra con el PnL neto cerrado mas lo
        # que quede abierto, las cifras no describen la misma corrida.
        var = r["nav_final"] - 1000.0
        residuo = var - r["pnl_neto_total"]
        r["reconciliacion"] = {
            "variacion_nav": var, "pnl_neto_cerrado": r["pnl_neto_total"],
            "residuo": residuo,
            "posiciones_abiertas_al_final": r["posiciones_abiertas_al_final"]}
        print(f"    reconciliacion: NAV {var:+.4f} - neto cerrado "
              f"{r['pnl_neto_total']:+.4f} = {residuo:+.4f}  "
              f"({r['posiciones_abiertas_al_final']} abiertas al final)")
        salida["resultados"][marco] = r
        print()

    # --- comparacion ---
    print("=" * 70)
    print("COMPARACION  (esperanza NETA por operacion: homogenea entre")
    print("              ventanas distintas; el NAV no lo es)")
    print("=" * 70)
    for marco, r in salida["resultados"].items():
        if "error" in r:
            print(f"  {marco:5} SIN DATOS: {r['error']}")
            continue
        e = r.get("esperanza_neta_por_operacion")
        b = r.get("esperanza_por_operacion")
        print(f"  {marco:5} {r['operaciones']:>5} ops | "
              f"bruta {('%+.4f' % b) if b is not None else '—':>9} | "
              f"NETA {('%+.4f' % e) if e is not None else '—':>9} USD | "
              f"aciertos netos {r.get('ganadoras_netas')}/{r['operaciones']} | "
              f"NAV {r['nav_final']:.2f}")
        print(f"        ventana {r['ventana'][0]} .. {r['ventana'][1]}")

    recorte = _recorte_misma_ventana(ops_por_marco.get("1d"),
                                     series_por_marco.get("30m"))
    if recorte:
        salida["diario_en_la_ventana_de_30m"] = recorte
        print()
        print("  MISMA VENTANA (operaciones diarias dentro de la de 30m),")
        print("  para quitar el confundido de mercados distintos:")
        if recorte.get("operaciones"):
            print(f"    1d restringido: {recorte['operaciones']} ops | "
                  f"NETA {recorte['esperanza_neta_por_operacion']:+.4f} USD | "
                  f"aciertos {recorte['ganadoras_netas']}")
        else:
            print(f"    {recorte.get('nota')}")

    destino = os.path.join(REPO, "resultados/v3", "b1_panel_vivo%s.json" % (
        "_sintetico" if SINTETICO else ""))
    os.makedirs(os.path.dirname(destino), exist_ok=True)
    with io.open(destino, "w", encoding="utf-8") as f:
        json.dump(salida, f, indent=2, ensure_ascii=False, default=str)
    print(f"\nguardado {destino}")

    duros = [m for m, r in salida["resultados"].items() if "error" in r]
    if duros and not SINTETICO:
        print(f"\nAVISO: sin datos para {duros}. "
              f"La comparacion esta incompleta.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
