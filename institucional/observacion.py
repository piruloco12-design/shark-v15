"""
Punto de union con el nucleo, y almacenamiento SEPARADO de la evidencia.

Esta es la pieza peligrosa: es la unica que toca el camino del bot en
vivo. Por eso esta escrita para que sea estructuralmente imposible que
bloquee algo en modo OBSERVE, no solo "poco probable":

    if extension.solo_observa:
        return SIN_BLOQUEO, evaluaciones

El return esta antes de cualquier lectura de allow_new_entry. Aunque
los tres modulos digan que no, en OBSERVE la funcion devuelve False.
La prueba tests/test_observacion.py recorre todas las combinaciones de
estado para confirmarlo.

Tampoco llama a ninguna funcion del nucleo. Solo lee DataFrames que el
nucleo ya tenia en la mano. El documento avisa de esto expresamente:
"No llamar dos veces a una funcion del nucleo que ademas de devolver
senales cambie cooldowns, posiciones o indicadores."

Y nunca lanza. Un fallo aqui se registra y se sigue; que la ampliacion
tumbe el bot en vivo seria el peor resultado posible.
"""

from __future__ import annotations

import json
import sqlite3
import time

from config import DATABASE_NAME
from institucional import contratos as C
from institucional import modulos as M

SIN_BLOQUEO = False

TABLA = "observacion_institucional"


def _conexion():
    conn = sqlite3.connect(DATABASE_NAME)
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_observacion():
    """Crea la tabla propia. No toca ninguna tabla del nucleo."""
    with _conexion() as conn:
        conn.execute(f"""
            CREATE TABLE IF NOT EXISTS {TABLA} (
                id                INTEGER PRIMARY KEY AUTOINCREMENT,
                registrado_en     TEXT NOT NULL,
                base_signal_id    TEXT,
                ticker            TEXT,
                signal            TEXT,
                regime            TEXT,
                module_id         TEXT NOT NULL,
                status            TEXT NOT NULL,
                allow_new_entry   INTEGER,
                size_multiplier   REAL,
                as_of             INTEGER,
                valid_until       INTEGER,
                config_hash       TEXT,
                dataset_version   TEXT,
                modo              TEXT,
                exigido           INTEGER,
                habria_bloqueado  INTEGER,
                bloqueo_aplicado  INTEGER,
                reason_codes      TEXT,
                diagnostics       TEXT
            )
        """)
        conn.execute(
            f"CREATE INDEX IF NOT EXISTS idx_{TABLA}_ticker "
            f"ON {TABLA}(ticker, module_id, registrado_en)"
        )


_TABLA_LISTA = False
_FALLOS_REGISTRO = []


def _asegurar_tabla():
    """Crea la tabla la primera vez, sin depender de quien arranque.

    Antes esto dependia de que alguien llamara a init_observacion() en
    el arranque. Quien llamara a run_live_cycle() directamente escribia
    en una tabla que no existia, el INSERT fallaba, y como registrar()
    se come las excepciones la evidencia se perdia EN SILENCIO: los
    logs mostraban las evaluaciones y la tabla estaba vacia. Ese es el
    peor fallo posible en un modulo cuyo unico trabajo es dejar
    constancia.
    """
    global _TABLA_LISTA
    if _TABLA_LISTA:
        return
    init_observacion()
    _TABLA_LISTA = True


def fallos_de_registro():
    """Fallos al guardar evidencia. Si no esta vacio, falta evidencia."""
    return list(_FALLOS_REGISTRO)


def registrar(evaluacion: C.ContextAssessment, *, ticker, signal, regime,
              modo, exigido, bloqueo_aplicado):
    """Guarda una evaluacion. Nunca lanza, pero deja rastro si falla."""
    try:
        _asegurar_tabla()
    except Exception as e:
        _FALLOS_REGISTRO.append(f"crear tabla: {type(e).__name__}: {e}")
        return
    try:
        with _conexion() as conn:
            conn.execute(
                f"""INSERT INTO {TABLA} (
                    registrado_en, base_signal_id, ticker, signal, regime,
                    module_id, status, allow_new_entry, size_multiplier,
                    as_of, valid_until, config_hash, dataset_version,
                    modo, exigido, habria_bloqueado, bloqueo_aplicado,
                    reason_codes, diagnostics
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    evaluacion.base_signal_id, ticker, signal, regime,
                    evaluacion.module_id, evaluacion.status,
                    None if evaluacion.allow_new_entry is None
                    else int(evaluacion.allow_new_entry),
                    evaluacion.size_multiplier,
                    evaluacion.as_of, evaluacion.valid_until,
                    evaluacion.config_hash, evaluacion.dataset_version,
                    modo, int(bool(exigido)),
                    # "habria bloqueado" se calcula SIEMPRE como si el
                    # modulo exigiera: es lo que permite medir despues si
                    # vale la pena activarlo, sin activarlo.
                    int(evaluacion.veta_entrada(exigido=True)),
                    int(bool(bloqueo_aplicado)),
                    json.dumps(list(evaluacion.reason_codes)),
                    json.dumps(evaluacion.diagnostics, default=str),
                ),
            )
    except Exception as e:
        # El registro de evidencia no puede tumbar un ciclo en vivo,
        # pero tampoco puede desaparecer sin que nadie lo sepa: queda
        # en fallos_de_registro() y el motor lo saca por el log.
        _FALLOS_REGISTRO.append(
            f"{ticker}/{evaluacion.module_id}: {type(e).__name__}: "
            f"{str(e)[:120]}"
        )


def evaluar(
    *,
    ticker: str,
    df,
    signal: str,
    regime: str,
    base_signal_id: str,
    extension,
    series_tr: dict | None = None,
    serie_efectivo=None,
    ranking=None,
    decision_time=None,
    nominal: float | None = None,
) -> tuple[bool, list[C.ContextAssessment]]:
    """Evalua los modulos habilitados. Devuelve (bloquear, evaluaciones).

    En OBSERVE, bloquear es SIEMPRE False, pase lo que pase.
    """
    evaluaciones: list[C.ContextAssessment] = []

    if extension is None or extension.mode == "OFF":
        return SIN_BLOQUEO, evaluaciones

    import pandas as pd
    if decision_time is None:
        decision_time = pd.Timestamp.now(tz="UTC")
    cfg_hash = extension.config_hash()

    # ---- M02: contexto de tendencia ----
    if extension.habilitado("M02_trend_context"):
        serie = (series_tr or {}).get(ticker)
        try:
            if serie is None or serie_efectivo is None:
                ahora = int(pd.Timestamp(decision_time).timestamp())
                evaluaciones.append(C.ContextAssessment(
                    base_signal_id=base_signal_id,
                    module_id="M02_trend_context", config_hash=cfg_hash,
                    dataset_version="sin-serie-diaria", as_of=ahora,
                    valid_until=ahora, input_available_at_max=ahora,
                    status=C.NO_DATA,
                    reason_codes=("SIN_SERIE_TOTAL_RETURN",),
                ))
            else:
                evaluaciones.append(M.m02_contexto(
                    ticker, serie, serie_efectivo, decision_time,
                    base_signal_id, cfg_hash, signal=signal))
        except Exception as e:
            evaluaciones.append(_fallo("M02_trend_context", base_signal_id,
                                       cfg_hash, decision_time, e))

    # ---- M03: ranking de candidatos ----
    if extension.habilitado("M03_candidate_ranking"):
        try:
            if ranking is None:
                ahora = int(pd.Timestamp(decision_time).timestamp())
                evaluaciones.append(C.ContextAssessment(
                    base_signal_id=base_signal_id,
                    module_id="M03_candidate_ranking", config_hash=cfg_hash,
                    dataset_version="sin-ranking", as_of=ahora,
                    valid_until=ahora, input_available_at_max=ahora,
                    status=C.NO_DATA, reason_codes=("SIN_RANKING",),
                ))
            else:
                evaluaciones.append(M.m03_contexto(
                    ticker, ranking, base_signal_id, cfg_hash, decision_time,
                    signal=signal))
        except Exception as e:
            evaluaciones.append(_fallo("M03_candidate_ranking", base_signal_id,
                                       cfg_hash, decision_time, e))

    # ---- M01: coste ----
    if extension.habilitado("M01_costs"):
        try:
            precio = float(df["Close"].iloc[-1])
            volumen = float(df["Volume"].iloc[-1]) * precio
            retornos = df["Close"].pct_change().dropna()
            vol_h = float(retornos.tail(20).std()) if len(retornos) > 2 else 0.0
            evaluaciones.append(M.m01_coste(
                ticker, nominal if nominal else precio,
                volumen if volumen > 0 else 1.0, vol_h,
                base_signal_id, cfg_hash, decision_time,
                dataset_version=f"{len(df)}-{df.index[-1]}",
            ))
        except Exception as e:
            evaluaciones.append(_fallo("M01_costs", base_signal_id,
                                       cfg_hash, decision_time, e))

    # ---- registro ----
    bloquear = SIN_BLOQUEO
    if not extension.solo_observa:
        # Solo en ENFORCE se lee la opinion para bloquear de verdad.
        for ev in evaluaciones:
            if ev.veta_entrada(exigido=extension.exige(ev.module_id)):
                bloquear = True

    for ev in evaluaciones:
        registrar(ev, ticker=ticker, signal=signal, regime=regime,
                  modo=extension.mode,
                  exigido=extension.exige(ev.module_id),
                  bloqueo_aplicado=bloquear)

    return bloquear, evaluaciones


def _fallo(module_id, base_signal_id, cfg_hash, decision_time, error):
    """Un modulo que revienta queda como NO_DATA, no como veto."""
    import pandas as pd
    ahora = int(pd.Timestamp(decision_time).timestamp())
    return C.ContextAssessment(
        base_signal_id=base_signal_id, module_id=module_id,
        config_hash=cfg_hash, dataset_version="error", as_of=ahora,
        valid_until=ahora, input_available_at_max=ahora,
        status=C.NO_DATA,
        reason_codes=("EXCEPCION", type(error).__name__),
        diagnostics={"error": str(error)[:200]},
    )


def resumen_habria_bloqueado(limite: int = 500) -> dict:
    """Cuanto habria bloqueado cada modulo si estuviera activo.

    Esto es lo que permite decidir mas adelante si un modulo merece
    pasar a ENFORCE, con datos y no con intuicion.
    """
    try:
        with _conexion() as conn:
            filas = conn.execute(f"""
                SELECT module_id, status,
                       SUM(habria_bloqueado), COUNT(*)
                FROM {TABLA}
                GROUP BY module_id, status
                ORDER BY module_id, status
            """).fetchall()
    except Exception as e:
        return {"error": str(e)[:120]}

    salida = {}
    for module_id, status, bloqueos, total in filas:
        salida.setdefault(module_id, {})[status] = {
            "evaluaciones": total,
            "habria_bloqueado": int(bloqueos or 0),
        }
    return salida
