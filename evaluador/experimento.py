"""
Medición con el motor corregido, con todos los artefactos reproducibles.

ORDEN DE EJECUCION, y el orden importa

  1. Se escribe el REGISTRO con la familia, la métrica y el umbral. En
     disco, con su hash, ANTES de calcular nada.
  2. Se descargan los datos y se guarda el panel exacto que se consumió.
  3. Se corre el evaluador corregido sobre el libro de efectivo.
  4. Se guardan decisiones, órdenes, posiciones diarias y NAV diario.
  5. Solo entonces se calculan p-valores y se aplica Holm.

Si el paso 1 fuera después del 5, el registro no valdría nada: se podría
elegir la familia viendo los resultados. Esa es la diferencia entre
pre-registrar y decir que se pre-registró.

QUE NO PUEDE CONCLUIR ESTO, medido y no supuesto

Con 15 años de datos mensuales, el contraste detecta una ventaja de +0,72%
anual el 12% de las veces, y rechaza en falso el 7,5%. Es decir: por debajo
de un 3-4% anual de diferencial, no se puede distinguir una ventaja real de
la suerte. Un «no rechaza» aquí significa «indetectable con esta muestra»,
NO «no hay ventaja». Y un «rechaza» por los pelos tampoco demuestra mucho.

Esa es la resolución del aparato, no un defecto del código, y ninguna
corrección la mejora. Está medida en tests/test_inferencia.py.

ADEMAS

El universo es el de hoy: los ETF que cerraron no están. Va etiquetado
`EXPLORATORY_SURVIVOR_UNIVERSE` y no es una validación. Y los datos son los
mismos que ya miré antes de la auditoría, así que el estado es
EXPLORATORIO: un tramo ya observado no recupera su condición de prueba
final por renombrarlo.
"""

from __future__ import annotations

import json
import os
import sys
import time

_AQUI = os.path.dirname(os.path.abspath(__file__))
_RAIZ = os.path.dirname(_AQUI)
for _r in (_RAIZ, _AQUI):
    if _r not in sys.path:
        sys.path.insert(0, _r)

import numpy as np
import pandas as pd

from evaluador import registro as REG
from evaluador.inferencia import contraste_diferencial, sensibilidad_bloque
from evaluador.mensual import (
    ComprarYMantener,
    EvaluadorMensual,
    M02Tendencia,
    M03Momentum,
    Politicas,
    RebalanceoEquiponderado,
    SinDatosSuficientes,
)

# v3, NO v2. El plan es explicito: "No sobrescribas resultados/v2/ ni su
# registro. Genera resultados/v3/ con otro identificador, panel exacto,
# hashes completos y explicacion de diferencias." Las cifras de v2 quedan
# superadas por los cambios 1 a 4, y una correccion no recupera un
# holdout ya observado: siguen ahi, identificadas y no pisadas.
SALIDA = os.getenv("SALIDA_EXP", "resultados/v3")


RUN_ID = "sin_identificar"


def _identificador_corrida() -> str:
    """Identidad de ESTA corrida: instante UTC y commit.

    El registro no se sobrescribe, asi que cada corrida necesita el suyo.
    Antes todas escribian en experiment_registry.json y la segunda pisaba
    a la primera: si la familia o el umbral cambiaban entre corridas, no
    quedaba rastro.
    """
    import subprocess
    sello = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    try:
        commit = subprocess.run(
            ["git", "rev-parse", "--short=8", "HEAD"],
            capture_output=True, text=True, timeout=5).stdout.strip()
    except Exception:
        commit = ""
    return f"{sello}-{commit or 'sin_commit'}"
PERIODO = os.getenv("PERIODO_EXP", "15y")

# ---- universos, fijados aquí ----
RENTA_VARIABLE = ["SPY", "QQQ", "IWM", "DIA", "MDY", "XLE", "XLF", "XLK",
                  "XLV", "XLI", "XLP", "XLY", "XLU", "XLB"]
OTROS = ["GLD", "SLV", "USO", "DBC", "DBA", "UNG", "PPLT",
         "TLT", "IEF", "LQD", "HYG", "SHY",
         "FXE", "FXY", "FXB", "FXF", "UUP"]
MULTIACTIVO = RENTA_VARIABLE + OTROS
TICKER_EFECTIVO = "BIL"

# ---- parámetros, hipótesis iniciales, no óptimos ----
K = 5
LOOKBACK = 252
SKIP = 21
VENTANA_VOL = 63
LONGITUD_BLOQUE = 12.0        # meses, declarada de antemano
REMUESTRAS = 5000
ALFA = 0.05
UMBRAL = 0.0                  # diferencial mensual neto > 0

# La familia COMPLETA, enumerada antes de correr. Cuatro hipótesis, no
# dieciocho: con esta muestra, más hipótesis solo reparten la potencia que
# ya es escasa.
FAMILIA = [
    {"id": "multiactivo/M03", "universo": "multiactivo",
     "estrategia": "M03_momentum_12_1", "referencia": "comprar_y_mantener"},
    {"id": "multiactivo/M02", "universo": "multiactivo",
     "estrategia": "M02_tendencia", "referencia": "comprar_y_mantener"},
    {"id": "renta_variable/M03", "universo": "renta_variable",
     "estrategia": "M03_momentum_12_1", "referencia": "comprar_y_mantener"},
    {"id": "renta_variable/M02", "universo": "renta_variable",
     "estrategia": "M02_tendencia", "referencia": "comprar_y_mantener"},
]

VARIANTES_YA_VISTAS = [
    "18 dictamenes del experimento del 2026-10-19 con el motor defectuoso "
    "(6 bloques x 3 variantes, mas una variante con banda por bloque)",
    "M03 con banda de rebalanceo 0,02",
    "bloques por clase: materias_primas, bonos, divisas, cripto",
    "comparacion ajustado vs sin ajustar",
]


def _politicas_con_limites(limites) -> Politicas:
    """Las mismas politicas base, mas los limites de M04."""
    base = _politicas()
    return Politicas(
        capital_inicial=base.capital_inicial, moneda_cuenta=base.moneda_cuenta,
        coste_rel=base.coste_rel, coste_fijo=base.coste_fijo,
        dias_liquidacion=base.dias_liquidacion,
        permitir_fraccionado=base.permitir_fraccionado, lote=base.lote,
        politica_caja=base.politica_caja,
        antiguedad_maxima_dias=base.antiguedad_maxima_dias,
        politica_terminal=base.politica_terminal,
        calentamiento_sesiones=base.calentamiento_sesiones,
        limites=limites)


def _politicas() -> Politicas:
    return Politicas(
        capital_inicial=1000.0,
        moneda_cuenta="USD",
        coste_rel=0.0008,
        coste_fijo=0.0,
        dias_liquidacion=0,
        permitir_fraccionado=True,
        lote=0.0,
        politica_caja="SIN_REMUNERAR",
        antiguedad_maxima_dias=7,
        politica_terminal="MARCAR",
        calentamiento_sesiones=LOOKBACK + 1,
    )


def cargar(tickers, descargar=None):
    """Descarga las series total-return. Devuelve (series, incidencias)."""
    if descargar is None:
        import data_feed

        def descargar(t):
            data_feed.DATA_PROVIDER_ORDER = ["yfinance"]
            return data_feed.get_serie_total_return(t, PERIODO, "1d")

    series, incidencias = {}, {}
    for t in tickers:
        try:
            df, proveedor = descargar(t)
            if df is None or len(df) < LOOKBACK + 60:
                incidencias[t] = f"historico insuficiente ({0 if df is None else len(df)})"
                continue
            series[t] = df
        except Exception as e:
            incidencias[t] = f"{type(e).__name__}: {str(e)[:90]}"
    return series, incidencias


# =====================================================================

def guardar_artefactos(nombre, resultado, carpeta):
    """Los artefactos de la tabla 4.6: decisiones, ordenes, NAV, posiciones."""
    os.makedirs(carpeta, exist_ok=True)
    base = os.path.join(carpeta, nombre)

    # NAV diario
    resultado["_nav"].rename("nav").to_frame().to_csv(f"{base}.nav_daily.csv")

    # Decisiones: cada candidato, su score, por qué se excluyó, y el objetivo
    filas = []
    for d in resultado["_decisiones"]:
        if not d.pesos_deseados and not d.scores and not d.excluidos:
            filas.append({"fecha_decision": d.fecha_decision,
                          "instrumento": "", "score": None,
                          "peso_deseado": 0.0, "motivo_exclusion": "",
                          "seleccionado": False, "nota": d.nota})
            continue
        candidatos = set(d.pesos_deseados) | set(d.scores) | set(d.excluidos)
        for t in sorted(candidatos):
            filas.append({
                "fecha_decision": d.fecha_decision,
                "fecha_ejecucion": d.fecha_ejecucion,
                "instrumento": t,
                "score": d.scores.get(t),
                "peso_deseado": d.pesos_deseados.get(t, 0.0),
                "motivo_exclusion": d.excluidos.get(t, ""),
                "seleccionado": t in d.pesos_deseados,
                "nota": d.nota,
            })
    pd.DataFrame(filas).to_csv(f"{base}.decisions.csv", index=False)

    # Órdenes y fills, con todo lo que la auditoría pide por operación
    movs = []
    for m in resultado["_libro"].movimientos:
        movs.append({
            "momento": m.momento, "tipo": m.tipo,
            "instrumento": m.instrumento,
            "cantidad_solicitada": m.cantidad_solicitada,
            "cantidad_ejecutada": m.cantidad_ejecutada,
            "precio_decision": m.precio_decision,
            "precio_ejecucion": m.precio_ejecucion,
            "momento_decision": m.momento_decision,
            "comision": m.costes.get("comision", 0.0),
            "nominal": m.costes.get("nominal", 0.0),
            "riesgo_inicial": m.riesgo_inicial,
            "motivo": m.motivo,
            "efectivo_despues": m.efectivo_despues,
            "nav_despues": m.nav_despues,
            "rechazo": m.rechazo,
        })
    pd.DataFrame(movs).to_csv(f"{base}.orders_fills.csv", index=False)

    # El resumen, sin los objetos internos
    limpio = {k: v for k, v in resultado.items() if not k.startswith("_")}
    with open(f"{base}.resumen.json", "w") as f:
        json.dump(limpio, f, indent=2, default=str)

    return {
        "nav_daily": f"{base}.nav_daily.csv",
        "decisions": f"{base}.decisions.csv",
        "orders_fills": f"{base}.orders_fills.csv",
        "resumen": f"{base}.resumen.json",
    }


def guardar_panel(series, efectivo, carpeta):
    """El panel EXACTO que se consumió, con OHLC completo y su procedencia.

    La primera version guardaba SOLO los cierres. Al reconstruir el panel
    para el analisis de supervivencia tuve que inventar la apertura como el
    cierre anterior, y los fills salieron distintos: el diferencial base
    daba +1,51 puntos en vez de +1,33. Una diferencia pequena, pero
    significa que el artefacto NO reproducia la corrida, que es justo lo
    que un artefacto tiene que hacer.

    La ejecucion usa la apertura del dia siguiente negociable. Sin la
    apertura guardada, el panel no permite repetir el experimento.
    """
    os.makedirs(carpeta, exist_ok=True)
    trozos = []
    todas = dict(series)
    if efectivo is not None:
        todas[TICKER_EFECTIVO] = efectivo
    for t, df in sorted(todas.items()):
        d = df[["Open", "High", "Low", "Close", "Volume"]].copy()
        d.insert(0, "instrumento", t)
        d.index.name = "fecha"
        trozos.append(d)
    panel = pd.concat(trozos).sort_index(kind="stable")
    ruta = os.path.join(carpeta, "prices_snapshot.csv")
    panel.to_csv(ruta)

    import hashlib
    with open(ruta, "rb") as f:
        h = hashlib.sha256(f.read()).hexdigest()[:16]
    return {"ruta": ruta, "hash": h, "filas": len(panel),
            "instrumentos": sorted(todas),
            "columnas": list(panel.columns),
            "formato": "largo: una fila por instrumento y fecha, con OHLCV",
            "desde": str(panel.index.min().date()),
            "hasta": str(panel.index.max().date())}


def cargar_panel(ruta):
    """Reconstruye el diccionario de series desde el panel guardado.

    Esto es lo que hace que el artefacto sirva: si no se puede volver a
    cargar y obtener las MISMAS series, no es un artefacto reproducible,
    es un adorno.
    """
    panel = pd.read_csv(ruta, index_col=0, parse_dates=True)
    panel.index = (panel.index.tz_localize("UTC") if panel.index.tz is None
                   else panel.index.tz_convert("UTC"))
    salida = {}
    for t, trozo in panel.groupby("instrumento"):
        d = trozo.drop(columns=["instrumento"]).sort_index()
        salida[str(t)] = d[~d.index.duplicated(keep="last")]
    return salida


# =====================================================================

class SalidaProtegida(RuntimeError):
    """Se intento escribir sobre una entrega ya publicada."""


# Entregas cerradas. Escribir aqui destruye evidencia ya auditada, y
# confiar en acordarse no funciono: CI piso resultados/v2 siete veces
# porque la salida por defecto apuntaba ahi. Esto no depende de que yo me
# acuerde.
SALIDAS_CERRADAS = ("v2",)


def _proteger_salida(ruta):
    nombre = os.path.basename(os.path.normpath(ruta))
    if nombre in SALIDAS_CERRADAS and os.environ.get("PERMITIR_PISAR") != "si":
        raise SalidaProtegida(
            f"{ruta} es una entrega cerrada y ya auditada: no se sobrescribe. "
            f"Genera otra version (resultados/v3, v4...) o exporta "
            f"SALIDA_EXP. Si de verdad hace falta pisarla, hay que decirlo "
            f"a proposito con PERMITIR_PISAR=si."
        )


def main(descargar=None):
    _proteger_salida(SALIDA)
    os.makedirs(SALIDA, exist_ok=True)
    os.makedirs(os.path.join(SALIDA, "registros"), exist_ok=True)
    global RUN_ID
    RUN_ID = _identificador_corrida()

    # ---------- PASO 1: el registro, ANTES de calcular nada ----------
    reg = REG.crear(
        nombre="M02/M03 solo largos con el motor corregido",
        familia=FAMILIA,
        metrica_primaria=("media del retorno MENSUAL NETO diferencial frente "
                          "a comprar y mantener del mismo universo, con "
                          "cantidades fijas"),
        hipotesis=("nula: diferencial medio <= 0. alternativa: > 0. Una cola, "
                   "declarada aqui."),
        umbral_economico=UMBRAL,
        metodo_inferencia=("bootstrap estacionario Politis-Romano con bloques "
                           "simultaneos para estrategia y referencia; "
                           "p-valor con el diferencial centrado en el umbral; "
                           "correccion de Holm sobre la familia declarada"),
        parametros_inferencia={
            "longitud_bloque_media_meses": LONGITUD_BLOQUE,
            "remuestras": REMUESTRAS,
            "alfa_familiar": ALFA,
            "potencia_medida": {
                "+0,72%/ano": 0.12, "+1,21%/ano": 0.18, "+2,43%/ano": 0.32,
                "+3,66%/ano": 0.60, "+6,17%/ano": 0.92,
            },
            "tasa_falso_positivo_medida": 0.075,
            "_nota_potencia": (
                "por debajo de un 3-4% anual de diferencial, este montaje no "
                "distingue una ventaja real de la suerte. Un 'no rechaza' "
                "significa indetectable, no inexistente."
            ),
        },
        estado="EXPLORATORIO",
        universo_etiqueta="EXPLORATORY_SURVIVOR_UNIVERSE",
        politicas=_politicas().a_dict(),
        variantes_ya_vistas=VARIANTES_YA_VISTAS,
        rutas_codigo=[
            os.path.join(_RAIZ, "libro.py"),
            os.path.join(_AQUI, "mensual.py"),
            os.path.join(_AQUI, "metricas.py"),
            os.path.join(_AQUI, "inferencia.py"),
            os.path.join(_AQUI, "experimento.py"),
        ],
        salida=os.path.join(SALIDA, "registros",
                            f"experiment_registry_{RUN_ID}.json"),
    )

    print("=" * 72)
    print("MEDICION CON EL MOTOR CORREGIDO")
    print("=" * 72)
    print(f"Registro escrito ANTES de calcular: hash {reg['hash_registro']}")
    print(f"Commit: {reg['commit']}")
    print(f"Estado: {reg['estado']}  |  universo: {reg['universo_etiqueta']}")
    print(f"Familia declarada: {len(FAMILIA)} hipotesis")
    for h in FAMILIA:
        print(f"  - {h['id']}: {h['estrategia']} vs {h['referencia']}")
    print(f"\nLo que este montaje PUEDE concluir:")
    print(f"  tasa de falso positivo medida: 7,5% (nominal 5%)")
    print(f"  potencia para +0,72%/ano: 12%   para +3,66%/ano: 60%")
    print(f"  -> por debajo de ~3-4% anual, un 'no rechaza' solo significa")
    print(f"     que la muestra no lo distingue de la suerte")

    # ---------- PASO 2: datos ----------
    print(f"\n{'=' * 72}\nDATOS\n{'=' * 72}")
    todos = sorted(set(MULTIACTIVO + [TICKER_EFECTIVO]))
    series, incidencias = cargar(todos, descargar)
    efectivo = series.pop(TICKER_EFECTIVO, None)
    print(f"  cargados {len(series)}/{len(MULTIACTIVO)} activos")
    print(f"  referencia de efectivo ({TICKER_EFECTIVO}): "
          f"{'OK' if efectivo is not None else 'NO DISPONIBLE'}")
    for t, m in incidencias.items():
        print(f"  sin datos: {t}: {m}")
    if len(series) < 5:
        raise SinDatosSuficientes(
            f"solo {len(series)} activos: no hay con que medir")

    # Universo congelado: se comprueba contra la lista fijada el
    # 2026-10-19 y se registran las bajas SIN quitarlas. Un activo que
    # desaparece tiene que seguir contando en el denominador; borrarlo
    # reinventaria el sesgo de supervivencia dentro del propio sistema.
    congelado = {}
    try:
        import universo_congelado as UC
        disponibles = set(series) | ({TICKER_EFECTIVO} if efectivo is not None
                                     else set())
        congelado = UC.comprobar(disponibles)
        print()
        print("  " + UC.resumen_texto(congelado).replace("\n", "\n  "))
    except Exception as e:
        print(f"  universo congelado: no se pudo comprobar "
              f"({type(e).__name__}: {e})")
        congelado = {"error": f"{type(e).__name__}: {e}"}

    panel = guardar_panel(series, efectivo, SALIDA)
    print(f"  panel guardado: {panel['filas']} filas, "
          f"{panel['desde']} -> {panel['hasta']}, hash {panel['hash']}")

    universos = {
        "multiactivo": {t: df for t, df in series.items() if t in MULTIACTIVO},
        "renta_variable": {t: df for t, df in series.items()
                           if t in RENTA_VARIABLE},
    }

    # ---------- PASO 3 y 4: correr y guardar ----------
    resultados, artefactos = {}, {}
    pol = _politicas()

    for nombre_u, series_u in universos.items():
        print(f"\n{'=' * 72}\nUNIVERSO: {nombre_u}  ({len(series_u)} activos)"
              f"\n{'=' * 72}")
        try:
            ev = EvaluadorMensual(series_u, pol)
        except SinDatosSuficientes as e:
            print(f"  SIN DATOS: {e}")
            continue
        print(f"  calentamiento hasta {ev.inicio_evaluacion.date()}, "
              f"{len(ev.fechas_decision)} decisiones mensuales")

        estrategias = {
            "comprar_y_mantener": ComprarYMantener(),
            "rebalanceo_equiponderado": RebalanceoEquiponderado(),
            "M03_momentum_12_1": M03Momentum(K, LOOKBACK, SKIP),
        }
        if efectivo is not None:
            estrategias["M02_tendencia"] = M02Tendencia(
                efectivo["Close"], LOOKBACK, VENTANA_VOL)

        print(f"\n  {'ESTRATEGIA':26} {'CAGR':>8} {'SHARPE':>7} "
              f"{'MAXDD-D':>8} {'ROT/A':>7} {'INTENC':>7}")
        print("  " + "-" * 68)
        for clave, est in estrategias.items():
            try:
                r = ev.correr(est)
            except Exception as e:
                print(f"  {clave:26} FALLO: {type(e).__name__}: {str(e)[:40]}")
                continue
            resultados[f"{nombre_u}/{clave}"] = r
            artefactos[f"{nombre_u}/{clave}"] = guardar_artefactos(
                f"{nombre_u}.{clave}", r, SALIDA)
            # El resumen por pantalla NO puede tirar una corrida ya
            # terminada. Esto murio con KeyError sobre
            # 'rotacion_anual_nominal' DESPUES de descargar 31 activos y 15
            # anos, por un `print`. Renombre la clave en el cambio 5 y no
            # busque quien la leia; el coste de ese descuido fue una
            # corrida completa de CI. Ahora se lee con .get y si falta algo
            # se dice en la linea en vez de abortar el experimento.
            try:
                sh = r.get("sharpe_diferencial")
                rot = r.get("rotacion_anual_sobre_patrimonio_medio")
                if rot is None:
                    rot = r.get("rotacion_anual_nominal_sobre_capital_inicial")
                print(f"  {clave:26} {r['cagr']*100:7.2f}% "
                      f"{(sh if sh is not None else float('nan')):7.2f} "
                      f"{r['max_drawdown_diario']*100:7.1f}% "
                      f"{(rot if rot is not None else float('nan')):7.2f} "
                      f"{r.get('intenciones', 0):7}")
            except Exception as e:
                print(f"  {clave:26} calculado, pero el resumen por "
                      f"pantalla fallo: {type(e).__name__}: {str(e)[:50]}")

    # ---------- PASO 5: inferencia, al final ----------
    print(f"\n{'=' * 72}\nINFERENCIA (al final, sobre la familia declarada)"
          f"\n{'=' * 72}")

    contrastes, pvalores = {}, {}
    for h in FAMILIA:
        clave_e = f"{h['universo']}/{h['estrategia']}"
        clave_r = f"{h['universo']}/{h['referencia']}"
        if clave_e not in resultados or clave_r not in resultados:
            print(f"  {h['id']:24} sin resultados para contrastar")
            pvalores[h["id"]] = None
            continue
        nav_e = resultados[clave_e]["_nav_mensual"]
        nav_r = resultados[clave_r]["_nav_mensual"]
        try:
            c = contraste_diferencial(nav_e, nav_r, umbral=UMBRAL,
                                      longitud_bloque_media=LONGITUD_BLOQUE,
                                      remuestras=REMUESTRAS)
            c["sensibilidad_bloque"] = sensibilidad_bloque(
                nav_e, nav_r, umbral=UMBRAL, remuestras=1500)
            c["cagr_estrategia"] = resultados[clave_e]["cagr"]
            c["cagr_referencia"] = resultados[clave_r]["cagr"]
            c["diferencia_cagr"] = (resultados[clave_e]["cagr"]
                                    - resultados[clave_r]["cagr"])
            contrastes[h["id"]] = c
            pvalores[h["id"]] = c["p_valor_una_cola"]
            print(f"  {h['id']:24} CAGR {c['cagr_estrategia']*100:+6.2f}% vs "
                  f"{c['cagr_referencia']*100:+6.2f}%  "
                  f"dif {c['diferencia_cagr']*100:+5.2f} pts  "
                  f"p={c['p_valor_una_cola']:.4f}")
        except Exception as e:
            print(f"  {h['id']:24} no contrastable: {type(e).__name__}: {e}")
            pvalores[h["id"]] = None

    holm = REG.holm(pvalores, ALFA)
    print(f"\n  CORRECCION DE HOLM sobre {len(pvalores)} hipotesis, "
          f"error familiar {ALFA}")
    for clave, v in holm.items():
        marca = "RECHAZA la nula" if v["rechaza_nula"] else "no rechaza"
        print(f"    {clave:24} p={v['p']}  umbral={v['umbral_holm']:.5f}  "
              f"-> {marca}")

    # ---------- M04 basico: el coste de controlar la cartera ----------
    #
    # Va APARTE de la familia registrada: es otra variante, con su propio
    # identificador, y su efecto sobre el beneficio se MIDE, no se
    # presupone. La auditoria avisa (caso I29): mas control de riesgo puede
    # dar menos dinero, y eso se informa como las dos cosas que es.
    print(f"\n{'=' * 72}\nM04 BASICO: que cuesta limitar la cartera"
          f"\n{'=' * 72}")
    m04 = {}
    try:
        from limites_cartera import GRUPOS_UNIVERSO, LimitesCartera

        variantes_m04 = {
            "sin_limites": None,
            "i25_g40": LimitesCartera(max_por_instrumento=0.25,
                                      max_por_grupo=0.40,
                                      grupos=GRUPOS_UNIVERSO),
            "i25_g40_e90": LimitesCartera(max_por_instrumento=0.25,
                                          max_por_grupo=0.40,
                                          max_exposicion_total=0.90,
                                          reserva_costes=0.05,
                                          grupos=GRUPOS_UNIVERSO),
        }
        print(f"\n  {'VARIANTE':16} {'CAGR':>8} {'SHARPE':>7} {'MAXDD-D':>8} "
              f"{'INVERT':>7} {'RECORTES':>9}")
        print("  " + "-" * 62)
        for etq, lim in variantes_m04.items():
            pol_m04 = _politicas_con_limites(lim)
            try:
                ev_m04 = EvaluadorMensual(universos["multiactivo"], pol_m04)
                r_m04 = ev_m04.correr(M03Momentum(K, LOOKBACK, SKIP))
            except Exception as e:
                print(f"  {etq:16} FALLO: {type(e).__name__}: {str(e)[:35]}")
                continue
            recortes = sum(1 for d in r_m04["_decisiones"]
                           if d.nota.startswith("M04"))
            c = r_m04["concentracion_final"]
            m04[etq] = {k: v for k, v in r_m04.items()
                        if not k.startswith("_")}
            m04[etq]["decisiones_con_recorte"] = recortes
            print(f"  {etq:16} {r_m04['cagr']*100:7.2f}% "
                  f"{(r_m04['sharpe_diferencial'] or 0):7.2f} "
                  f"{r_m04['max_drawdown_diario']*100:7.1f}% "
                  f"{c['invertido']:7.3f} "
                  f"{recortes:4}/{r_m04['decisiones']:<4}")
        if "sin_limites" in m04 and "i25_g40" in m04:
            dcagr = (m04["i25_g40"]["cagr"] - m04["sin_limites"]["cagr"]) * 100
            ddd = (m04["i25_g40"]["max_drawdown_diario"]
                   - m04["sin_limites"]["max_drawdown_diario"]) * 100
            # ddd > 0 significa que la caida es MENOS profunda (de -32,2 a
            # -21,4). La version anterior imprimia -ddd y salia "mejora la
            # caida en -10,7", que se lee como que la empeora.
            print(f"\n  el tope por grupo cuesta {dcagr:+.2f} puntos de CAGR "
                  f"y {'reduce' if ddd > 0 else 'agrava'} la caida maxima en "
                  f"{abs(ddd):.1f} puntos")
            print(f"  I29: mas control, menos dinero. Es una preferencia, no "
                  f"una mejora del beneficio.")
            print(f"  Y el diagnostico que importa: recortar "
                  f"{m04['i25_g40']['decisiones_con_recorte']} de "
                  f"{m04['i25_g40']['decisiones']} decisiones significa que")
            print(f"  M03 estaba casi siempre con sus 5 posiciones en el "
                  f"mismo grupo.")
    except Exception as e:
        print(f"  no se pudo medir: {type(e).__name__}: {e}")
        m04 = {"error": f"{type(e).__name__}: {e}"}

    # ---------- supervivencia por escenarios ----------
    print(f"\n{'=' * 72}\nSESGO DE SUPERVIVENCIA, POR ESCENARIOS DECLARADOS"
          f"\n{'=' * 72}")
    print("  No es una correccion del sesgo: es cuanto se moveria el")
    print("  resultado SI el mundo hubiera sido como cada escenario dice.")
    supervivencia = {}
    try:
        from evaluador import supervivencia as SUP
        from evaluador.mensual import ComprarYMantener as _CYM
        from evaluador.mensual import M03Momentum as _M03

        supervivencia = SUP.medir(
            universos["multiactivo"], pol,
            lambda: _M03(K, LOOKBACK, SKIP), lambda: _CYM())
        base_dif = supervivencia["base"]["diferencial_cagr"]
        print(f"\n  base (solo supervivientes): diferencial "
              f"{base_dif*100:+.2f} pts")
        print(f"\n  {'ESCENARIO/FORMA':28} {'DIF':>8} {'CAMBIO':>8} "
              f"{'%SEL.MUERTA':>12}")
        print("  " + "-" * 60)
        for nombre_e, v in supervivencia["escenarios"].items():
            if "sin_datos" in v:
                print(f"  {nombre_e:28} SIN DATOS")
                continue
            print(f"  {nombre_e:28} {v['diferencial_cagr']*100:+7.2f}% "
                  f"{v['cambio_en_el_diferencial']*100:+7.2f} "
                  f"{v['pct_selecciones_muertas']:11.1f}%")
        d = supervivencia.get("dictamen", {})
        if d:
            print(f"\n  cambio en el diferencial: de "
                  f"{d['cambio_minimo_en_el_diferencial']*100:+.2f} a "
                  f"{d['cambio_maximo_en_el_diferencial']*100:+.2f} puntos")
            print(f"  favorecia a la estrategia en TODOS los escenarios: "
                  f"{d['el_sesgo_favorecia_a_la_estrategia']}")
            print(f"  favorecia a la referencia en TODOS: "
                  f"{d['el_sesgo_favorecia_a_la_referencia']}")
    except Exception as e:
        print(f"  no se pudo medir: {type(e).__name__}: {e}")
        supervivencia = {"error": f"{type(e).__name__}: {e}"}

    # ---------- informe ----------
    salida = {
        "run_id": RUN_ID,
        # El enlace va del informe AL registro, no al contrario: el
        # registro se escribe antes de que exista el panel, asi que no
        # puede contener su hash. El informe si puede nombrar el registro.
        "registro_archivo": os.path.join(
            "registros", f"experiment_registry_{RUN_ID}.json"),
        "registro": reg,
        "panel": panel,
        "universo_congelado": congelado,
        "supervivencia": supervivencia,
        "m04": m04,
        "incidencias_carga": incidencias,
        "resumenes": {k: {kk: vv for kk, vv in v.items()
                          if not kk.startswith("_")}
                      for k, v in resultados.items()},
        "contrastes": contrastes,
        "holm": holm,
        "artefactos": artefactos,
    }
    with open(os.path.join(SALIDA, "report.json"), "w") as f:
        json.dump(salida, f, indent=2, default=str)
    # Puntero a la ultima corrida. Es un puntero, no evidencia: se
    # sobrescribe a proposito, y los registros de registros/ no.
    with open(os.path.join(SALIDA, "ultima_corrida.txt"), "w") as f:
        f.write(f"{RUN_ID}\n")

    print(f"\n{'=' * 72}\nCONCLUSION\n{'=' * 72}")
    rechazadas = [k for k, v in holm.items() if v["rechaza_nula"]]
    if rechazadas:
        print(f"Rechazan la nula tras corregir: {rechazadas}")
        print("Eso NO autoriza capital. El universo es de supervivientes, el")
        print("estado es EXPLORATORIO, y los datos son los mismos que ya")
        print("habia mirado antes de la auditoria.")
    else:
        print("NINGUNA hipotesis rechaza la nula tras corregir por familia.")
        print("Con la potencia medida, eso significa que esta muestra no")
        print("distingue estas estrategias de su referencia, no que no haya")
        print("ventaja. Son dos afirmaciones distintas y solo la primera")
        print("esta respaldada.")
    print(f"\nArtefactos en {SALIDA}/")
    return salida


if __name__ == "__main__":
    import traceback
    try:
        main()
    except Exception:
        rastro = traceback.format_exc()
        print("\n" + "=" * 72)
        print("EL EXPERIMENTO FALLO")
        print("=" * 72)
        print(rastro)
        os.makedirs(SALIDA, exist_ok=True)
        with open(os.path.join(SALIDA, "fallo.json"), "w") as f:
            json.dump({"fallo": True, "traceback": rastro.splitlines()[-16:],
                       "traceback_completo": rastro}, f, indent=2)
        raise
