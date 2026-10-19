"""
M01, M02 contexto y M03 ranking. Los tres solo OBSERVAN.

Ninguno de estos modulos puede:
  - generar una compra o una venta
  - cerrar una posicion del nucleo
  - mover un stop
  - aumentar el tamano de una posicion (size_multiplier va en [0,1])

Lo unico que pueden hacer, y solo en modo ENFORCE con enforce=True, es
VETAR o REDUCIR una entrada nueva que el nucleo ya habia decidido por
su cuenta. En OBSERVE ni eso: se registra la opinion y se ejecuta la
ruta original tal cual.

Parametros por defecto: hipotesis iniciales del documento (seccion 15.5
y 15.6). No son optimos medidos. Estan aqui con nombre y version para
que un cambio sea visible y cueste un ensayo del presupuesto.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

import pandas as pd

from institucional import contratos as C
from institucional import referencia as R
from institucional.vista import (
    cierres_mensuales,
    recortar_disponible,
    ultimo_disponible_epoch,
)

VERSION_MODULOS = "2026-10-19.m01m02m03.1"

# ---- hipotesis iniciales, seccion 15.5 / 15.6 ----
M02_LOOKBACK = 252        # sesiones de la senal de tendencia
M02_VENTANA_VOL = 63      # sesiones de la volatilidad
M03_LOOKBACK = 252        # 12 meses
M03_SKIP = 21             # menos el mes mas reciente -> "12-1"
SESIONES_ANUALES = 252

# Referencia de efectivo. El documento exige que sea explicita y
# alineada, y prohibe usar cero para tapar un dato desconocido.
# BIL es un ETF de letras del Tesoro a 1-3 meses: reproducible,
# con historico largo, y es un BENCHMARK, no el interes que cobra
# la cuenta de Brian (que es 0% y hay que decirlo aparte).
TICKER_EFECTIVO = "BIL"

# Cuanto vale un ranking mensual antes de considerarse caducado. 35 dias
# cubre un mes natural con holgura de fin de semana y festivos. Pasado
# eso el estado es STALE: ni veto ni permiso, simplemente no se sabe.
VIGENCIA_RANKING_DIAS = 35


def _hash(*partes) -> str:
    crudo = "|".join(str(p) for p in partes)
    return hashlib.sha256(crudo.encode()).hexdigest()[:12]


def _version_datos(df: pd.DataFrame) -> str:
    """Identifica la serie usada: si cambia CUALQUIER valor, cambia el hash.

    La primera version usaba solo longitud, extremos temporales y ultimo
    cierre. Con eso, cambiar un precio intermedio de 105 a 500 dejaba el
    MISMO identificador: el hash no identificaba el panel, solo sus
    bordes. Un dato corregido a mitad de la serie pasaba inadvertido y
    dos corridas distintas parecian la misma.

    Ahora entran todos los valores y las marcas de tiempo. Se hace con
    los bytes del array, que es rapido incluso con 15 anos de historico.
    """
    if df is None or len(df) == 0:
        return "vacio"
    h = hashlib.sha256()
    h.update(str(len(df)).encode())
    # Marcas de tiempo
    try:
        h.update(df.index.values.tobytes())
    except (AttributeError, ValueError):
        h.update(str(list(df.index)).encode())
    # Todos los valores de las columnas que importan, en orden estable
    for col in sorted(c for c in df.columns
                      if c in ("Open", "High", "Low", "Close", "Volume")):
        h.update(col.encode())
        try:
            h.update(df[col].to_numpy(dtype="float64").tobytes())
        except (ValueError, TypeError):
            h.update(str(df[col].tolist()).encode())
    return h.hexdigest()[:12]


# =====================================================================
# M02 — tendencia lenta larga/efectivo, como CONTEXTO
# =====================================================================

def m02_contexto(
    ticker: str,
    serie_tr: pd.DataFrame,
    serie_efectivo: pd.DataFrame,
    decision_time,
    base_signal_id: str,
    config_hash: str,
    signal: str | None = None,
) -> C.ContextAssessment:
    """Estado mensual LONG/CASH del activo frente al efectivo.

    CASH no es una senal de venta. Es "esta variante no abre compras
    nuevas en este activo este mes". Las posiciones abiertas del nucleo
    siguen gestionadas por el nucleo, con sus salidas.

    Sobre una senal SELL devuelve UNSUPPORTED, no un veto. El documento
    lo dice expresamente (seccion 15.5): "Para estrategias cortas no
    reutilizar el significado de LONG/CASH; hace falta un diseno
    especifico." Un activo que cae da CASH, y aplicar eso a un corto
    seria vetar precisamente la operacion que la tendencia favorece:
    el signo se invierte y el filtro haria lo contrario de lo que
    parece. Mejor declarar que no sabe.
    """
    modulo = "M02_trend_context"
    comun = dict(base_signal_id=base_signal_id, module_id=modulo,
                 config_hash=config_hash, dataset_version="",
                 as_of=0, valid_until=0, input_available_at_max=0)

    if signal is not None and str(signal).upper() != "BUY":
        ahora = int(pd.Timestamp(decision_time).timestamp())
        return C.ContextAssessment(
            **{**comun, "as_of": ahora, "valid_until": ahora,
               "input_available_at_max": ahora,
               "dataset_version": "no-aplica"},
            status=C.UNSUPPORTED,
            reason_codes=("DIRECCION_NO_SOPORTADA", str(signal).upper()[:12]),
            diagnostics={
                "ticker": ticker,
                "motivo": "LONG/CASH no tiene significado para un corto; "
                          "haria falta un diseno propio",
            },
        )

    try:
        activo = recortar_disponible(serie_tr, decision_time, "1d")
        efectivo = recortar_disponible(serie_efectivo, decision_time, "1d")
    except R.DataError as e:
        ahora = int(pd.Timestamp(decision_time).timestamp())
        return C.ContextAssessment(
            **{**comun, "as_of": ahora, "valid_until": ahora,
               "input_available_at_max": ahora, "dataset_version": "sin-datos"},
            status=C.NO_DATA, reason_codes=("VISTA_INVALIDA", str(e)[:40]),
        )

    # Las dos series tienen que estar alineadas en las mismas sesiones.
    # No se rellenan huecos: un hueco es ausencia de dato, no un cero.
    fechas = activo.index.normalize().intersection(efectivo.index.normalize())
    a = activo[activo.index.normalize().isin(fechas)]
    e = efectivo[efectivo.index.normalize().isin(fechas)]

    as_of = int(a.index[-1].timestamp())
    disponible = ultimo_disponible_epoch(a, "1d")
    # Vale hasta el siguiente cierre mensual; despues esta STALE.
    valid_until = int((a.index[-1] + pd.Timedelta(days=35)).timestamp())
    comun.update(as_of=max(as_of, disponible), valid_until=valid_until,
                 input_available_at_max=disponible,
                 dataset_version=_version_datos(a))
    comun["valid_until"] = max(comun["valid_until"], comun["as_of"])

    minimo = max(M02_LOOKBACK, M02_VENTANA_VOL) + 1
    if len(a) < minimo:
        return C.ContextAssessment(
            **comun, status=C.NO_DATA,
            reason_codes=("HISTORICO_INSUFICIENTE",),
            diagnostics={"sesiones": len(a), "requeridas": minimo},
        )

    try:
        senal = R.trend_signal(
            a["Close"].tolist(), e["Close"].tolist(),
            lookback=M02_LOOKBACK, vol_window=M02_VENTANA_VOL,
            periods_per_year=SESIONES_ANUALES,
        )
    except R.DataError as err:
        return C.ContextAssessment(
            **comun, status=C.NO_DATA,
            reason_codes=("SENAL_NO_CALCULABLE", str(err)[:40]),
        )

    return C.ContextAssessment(
        **comun,
        status=C.READY,
        allow_new_entry=bool(senal.side == 1),
        # No reduce tamano: es un veto binario en esta version. Reducir
        # seria otra hipotesis y consumiria otro ensayo.
        size_multiplier=None,
        reason_codes=("LONG",) if senal.side == 1 else ("CASH",),
        diagnostics={
            "ticker": ticker,
            "exceso_historico": round(senal.trailing_excess_return, 6),
            "vol_anual": round(senal.annual_vol, 6),
            "sesiones": len(a),
            "cierre_usado": str(a.index[-1].date()),
            "referencia_efectivo": TICKER_EFECTIVO,
        },
    )


# =====================================================================
# M03 — fuerza relativa 12-1, como RANKING de candidatos
# =====================================================================

@dataclass(frozen=True)
class Ranking:
    seleccionados: tuple[str, ...]
    scores: dict[str, float]
    excluidos: dict[str, str]
    as_of: int
    dataset_version: str


def m03_ranking(
    series_tr: dict[str, pd.DataFrame],
    decision_time,
    k: int,
) -> Ranking:
    """Ordena candidatos por retorno 12-1. NO crea senales.

    Solo se puntuan activos que el nucleo ya propuso. Un activo con
    score alto y sin senal del nucleo no entra: el documento lo dice
    expresamente, "nunca compra solo porque haya hueco".
    """
    scores, excluidos = {}, {}
    marcas, versiones = [], []

    for ticker, serie in series_tr.items():
        try:
            vista = recortar_disponible(serie, decision_time, "1d")
        except R.DataError as e:
            excluidos[ticker] = f"vista: {str(e)[:40]}"
            continue
        if len(vista) < M03_LOOKBACK + 1:
            excluidos[ticker] = f"historico {len(vista)} < {M03_LOOKBACK + 1}"
            continue
        try:
            scores[ticker] = R.momentum_score(
                vista["Close"].tolist(),
                lookback=M03_LOOKBACK, skip=M03_SKIP,
            )
        except R.DataError as e:
            excluidos[ticker] = f"score: {str(e)[:40]}"
            continue
        marcas.append(vista.index[-1])
        versiones.append(_version_datos(vista))

    seleccionados = R.rank_positive(scores, k) if scores else ()
    as_of = int(max(marcas).timestamp()) if marcas else \
        int(pd.Timestamp(decision_time).timestamp())

    return Ranking(
        seleccionados=seleccionados,
        scores={t: round(s, 6) for t, s in scores.items()},
        excluidos=excluidos,
        as_of=as_of,
        dataset_version=_hash(*sorted(versiones)) if versiones else "sin-datos",
    )


def m03_contexto(
    ticker: str,
    ranking: Ranking,
    base_signal_id: str,
    config_hash: str,
    decision_time,
    signal: str | None = None,
) -> C.ContextAssessment:
    """Traduce el ranking a una opinion sobre UN candidato del nucleo.

    Igual que M02: sobre una senal SELL devuelve UNSUPPORTED. El
    ranking 12-1 mide fuerza relativa para COMPRAR; un activo con
    momentum alto es mal candidato a corto, no bueno. Reutilizar el
    mismo orden para las dos direcciones invertiria el significado.
    """
    modulo = "M03_candidate_ranking"
    ahora = int(pd.Timestamp(decision_time).timestamp())

    # ESTO ERA UNA TRAMPA MIA. La version anterior hacia
    #     as_of = max(ranking.as_of, ahora)
    # para que el contrato no se quejara. El contrato exige que
    # input_available_at_max <= as_of, y al mover as_of al presente
    # cualquier ranking lo cumplia: uno de 626 dias devolvia READY y
    # renovaba su vigencia, y uno con datos POSTERIORES a la decision
    # tambien. Hice pasar el validador desplazando justo lo que
    # validaba, que es peor que no tener validador: parecia que habia
    # comprobacion de causalidad y no habia ninguna.
    #
    # Ahora as_of es el momento de la DECISION y no se mueve. La
    # vigencia sale del calendario del snapshot, no de cuando se
    # consulta.
    as_of = ahora
    valid_until = ranking.as_of + VIGENCIA_RANKING_DIAS * 86400
    comun = dict(
        base_signal_id=base_signal_id, module_id=modulo,
        config_hash=config_hash, dataset_version=ranking.dataset_version,
        as_of=as_of, valid_until=max(valid_until, as_of),
        input_available_at_max=min(ranking.as_of, as_of),
    )

    # Dato del futuro: fallo de integridad, nunca READY. Un ranking
    # construido despues de la decision no pudo informarla.
    if ranking.as_of > ahora:
        return C.ContextAssessment(
            **comun, status=C.UNSUPPORTED,
            reason_codes=("INTEGRIDAD_DATO_FUTURO",),
            diagnostics={
                "ranking_as_of": str(pd.Timestamp(ranking.as_of, unit="s",
                                                  tz="UTC")),
                "decision": str(pd.Timestamp(ahora, unit="s", tz="UTC")),
                "dias_adelanto": round((ranking.as_of - ahora) / 86400, 2),
            },
        )

    # Caducado: STALE. No es un veto ni un permiso; es que no se sabe.
    antiguedad_dias = (ahora - ranking.as_of) / 86400
    if antiguedad_dias > VIGENCIA_RANKING_DIAS:
        return C.ContextAssessment(
            **comun, status=C.STALE,
            reason_codes=("RANKING_CADUCADO",),
            diagnostics={
                "antiguedad_dias": round(antiguedad_dias, 1),
                "vigencia_dias": VIGENCIA_RANKING_DIAS,
                "ranking_as_of": str(pd.Timestamp(ranking.as_of, unit="s",
                                                  tz="UTC").date()),
            },
        )

    if signal is not None and str(signal).upper() != "BUY":
        return C.ContextAssessment(
            **comun, status=C.UNSUPPORTED,
            reason_codes=("DIRECCION_NO_SOPORTADA", str(signal).upper()[:12]),
            diagnostics={
                "motivo": "el ranking 12-1 ordena candidatos a COMPRAR; "
                          "aplicarlo a un corto invertiria el significado",
            },
        )

    if ticker in ranking.excluidos:
        return C.ContextAssessment(
            **comun, status=C.NO_DATA,
            reason_codes=("NO_ELEGIBLE",),
            diagnostics={"motivo": ranking.excluidos[ticker]},
        )
    if ticker not in ranking.scores:
        return C.ContextAssessment(
            **comun, status=C.NO_DATA, reason_codes=("SIN_SCORE",),
        )

    dentro = ticker in ranking.seleccionados
    return C.ContextAssessment(
        **comun, status=C.READY, allow_new_entry=dentro,
        reason_codes=("EN_SELECCION",) if dentro else ("FUERA_DE_SELECCION",),
        diagnostics={
            "score": ranking.scores[ticker],
            "puesto": (ranking.seleccionados.index(ticker) + 1) if dentro else None,
            "seleccionados": list(ranking.seleccionados),
            "candidatos_puntuados": len(ranking.scores),
        },
    )


# =====================================================================
# M01 — coste y umbral economico
# =====================================================================

# Parametros del modelo de coste. Son ESCENARIOS declarados, no
# comisiones observadas: no tenemos fills reales todavia. El documento
# obliga a decirlo asi (seccion 15.4 B).
COSTE_FIJO = 0.0            # sin minimo por orden en el escenario base
COSTE_LINEAL_BPS = 8.0      # 0.08% por pata, el COSTE_POR_PATA de Shark
COEF_IMPACTO = 1.0          # escenario; no calibrado con fills propios


def m01_coste(
    ticker: str,
    nominal: float,
    volumen_moneda: float,
    vol_horizonte: float,
    base_signal_id: str,
    config_hash: str,
    decision_time,
    dataset_version: str,
    ganancia_bruta_esperada: float | None = None,
    modelo_retorno_id: str | None = None,
) -> C.ContextAssessment:
    """Coste modelado de una pata y, si hay estimador, umbral economico.

    Sin estimador validado fuera de muestra el estado es UNSUPPORTED y
    el modulo solo deja el diagnostico. No se convierte un momentum ni
    un RSI en ganancia esperada: el documento lo prohibe y seria la
    manera mas facil de fabricar un filtro que parece rentable.
    """
    modulo = "M01_costs"
    ahora = int(pd.Timestamp(decision_time).timestamp())
    comun = dict(
        base_signal_id=base_signal_id, module_id=modulo,
        config_hash=config_hash, dataset_version=dataset_version,
        as_of=ahora, valid_until=ahora + 86400,
        input_available_at_max=ahora,
    )

    try:
        coste_entrada = R.estimated_trade_cost(
            nominal, COSTE_LINEAL_BPS, COSTE_FIJO,
            vol_horizonte, volumen_moneda, COEF_IMPACTO,
        )
    except R.DataError as e:
        return C.ContextAssessment(
            **comun, status=C.NO_DATA,
            reason_codes=("COSTE_NO_CALCULABLE", str(e)[:40]),
        )

    # La salida puede costar distinto. No se asume que cuesta igual,
    # pero sin datos de liquidez de salida se usa el mismo escenario
    # y se declara como tal.
    coste_ida_vuelta = coste_entrada * 2
    diagnostico = {
        "ticker": ticker,
        "nominal": round(nominal, 2),
        "coste_una_pata": round(coste_entrada, 4),
        "coste_ida_vuelta": round(coste_ida_vuelta, 4),
        "coste_ida_vuelta_pct": round(coste_ida_vuelta / nominal * 100, 4)
        if nominal else None,
        "escenario": {"lineal_bps": COSTE_LINEAL_BPS, "fijo": COSTE_FIJO,
                      "coef_impacto": COEF_IMPACTO},
        "calibrado_con_fills_propios": False,
        # El documento avisa: "La salida puede tener otra liquidez y otro
        # coste: no asumir que cuesta exactamente lo mismo que entrar."
        # Aqui SI se asume, porque no hay datos de liquidez de salida.
        # Queda declarado en el registro en vez de escondido.
        "coste_salida_asumido_igual_a_entrada": True,
    }

    if ganancia_bruta_esperada is None or modelo_retorno_id is None:
        return C.ContextAssessment(
            **comun, status=C.UNSUPPORTED,
            reason_codes=("SIN_ESTIMADOR_FUERA_DE_MUESTRA",),
            diagnostics=diagnostico,
        )

    margen = coste_ida_vuelta * 0.5      # margen de incertidumbre declarado
    pasa = R.clears_cost_hurdle(ganancia_bruta_esperada, coste_ida_vuelta, margen)
    diagnostico.update(ganancia_bruta_esperada=round(ganancia_bruta_esperada, 4),
                       margen_incertidumbre=round(margen, 4),
                       modelo_retorno_id=modelo_retorno_id)
    return C.ContextAssessment(
        **comun, status=C.READY, allow_new_entry=pasa,
        reason_codes=("SUPERA_COSTE",) if pasa else ("NO_SUPERA_COSTE",),
        diagnostics=diagnostico,
    )
