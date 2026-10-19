"""
Snapshots mensuales de datos y ranking, persistidos.

POR QUE EXISTE

`live_engine._INST_SERIES_TR`, `_INST_EFECTIVO` y `_INST_RANKING` estaban a
`None` y solo se rellenaban en `tests/_replay_runner.py`. Por la ruta de
producción, M02 y M03 registraban `NO_DATA` siempre: los logs mostraban
evaluaciones, la tabla se llenaba de filas, y ninguna de esas filas contenía
una opinión. Parecía que los módulos funcionaban.

Lo irónico es que arreglé la versión de este mismo fallo que venía de las
zonas horarias, me felicité por encontrarlo, y dejé en pie la que importaba.

QUE HACE

Una tarea mensual que descarga las series diarias total-return, construye el
ranking 12−1, y lo guarda con todo lo necesario para auditarlo. El ciclo
intradía NO descarga nada: lee el snapshot de la base de datos. Descargar 15
años cada pocos minutos sería gastar cuota para obtener el mismo número.

LAS REGLAS QUE NO SE NEGOCIAN

  - `decision_time` no se mueve nunca para que un contrato pase. Esa fue
    exactamente la trampa de `max(ranking.as_of, ahora)`.
  - Se exige `max(available_at) <= decision_time`. Un dato publicado después
    de la decisión no pudo informarla.
  - `valid_until` sale del calendario del snapshot. Consultarlo no lo
    prolonga.
  - El hash cubre todos los valores y todos los identificadores. La fecha de
    descarga no basta; la longitud y el último cierre tampoco.
  - Si falta algo, el estado es `NO_DATA` o `STALE`. Nunca un permiso
    implícito.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import time

import pandas as pd

from config import DATABASE_NAME
from institucional.modulos import (
    M03_LOOKBACK,
    M03_SKIP,
    TICKER_EFECTIVO,
    VIGENCIA_RANKING_DIAS,
    _version_datos,
    m03_ranking,
)

TABLA = "snapshots_institucional"

# Política de ajuste declarada: las señales se calculan sobre nivel
# total-return. Los fills NO se simulan con estos precios.
POLITICA_AJUSTE = "total_return_auto_adjust_true"
VERSION_SNAPSHOT = "2026-10-19.snapshot.1"


class SnapshotInvalido(RuntimeError):
    """El snapshot no es usable para decidir. No es un permiso."""


def _conexion():
    conn = sqlite3.connect(DATABASE_NAME)
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_snapshots():
    with _conexion() as conn:
        conn.execute(f"""
            CREATE TABLE IF NOT EXISTS {TABLA} (
                snapshot_id       TEXT PRIMARY KEY,
                creado_en         TEXT NOT NULL,
                retrieved_at      INTEGER NOT NULL,
                observation_time  INTEGER NOT NULL,
                available_at_max  INTEGER NOT NULL,
                valid_until       INTEGER NOT NULL,
                adjustment_policy TEXT NOT NULL,
                universe_version  TEXT NOT NULL,
                strategy_version  TEXT NOT NULL,
                config_hash       TEXT NOT NULL,
                full_data_hash    TEXT NOT NULL,
                instrumentos      TEXT NOT NULL,
                ranking           TEXT NOT NULL,
                series            BLOB,
                efectivo          BLOB,
                incidencias       TEXT
            )
        """)
        conn.execute(
            f"CREATE INDEX IF NOT EXISTS idx_{TABLA}_obs "
            f"ON {TABLA}(observation_time DESC)")


def _hash_total(series: dict, efectivo, universo_version, config_hash) -> str:
    """Hash de TODO: identificadores, marcas y valores."""
    h = hashlib.sha256()
    h.update(universo_version.encode())
    h.update(config_hash.encode())
    h.update(POLITICA_AJUSTE.encode())
    for ticker in sorted(series):
        h.update(ticker.encode())
        h.update(_version_datos(series[ticker]).encode())
    if efectivo is not None:
        h.update(TICKER_EFECTIVO.encode())
        h.update(_version_datos(efectivo).encode())
    return h.hexdigest()[:16]


def construir(tickers, config_hash="", universo_version="",
              k=5, descargar=None, ahora=None) -> dict:
    """Descarga, construye el ranking y devuelve el snapshot sin guardarlo.

    `descargar(ticker) -> (df, proveedor)` se inyecta para poder probar
    esto sin red. Por defecto usa data_feed.get_serie_total_return.
    """
    if descargar is None:
        from data_feed import get_serie_total_return

        def descargar(t):
            return get_serie_total_return(t, "15y", "1d")

    ahora_ts = int(time.time()) if ahora is None else int(
        pd.Timestamp(ahora).timestamp())

    series, incidencias = {}, {}
    for t in list(tickers) + [TICKER_EFECTIVO]:
        try:
            df, proveedor = descargar(t)
            if df is None or len(df) < M03_LOOKBACK + 2:
                incidencias[t] = f"historico insuficiente ({0 if df is None else len(df)})"
                continue
            series[t] = df
        except Exception as e:
            incidencias[t] = f"{type(e).__name__}: {str(e)[:80]}"

    efectivo = series.pop(TICKER_EFECTIVO, None)
    if not series:
        raise SnapshotInvalido(
            f"ninguna serie descargada. Incidencias: {incidencias}")

    # El momento de observación es el último cierre COMUN disponible, y el
    # dato está disponible un día después de su marca: una vela diaria no
    # está cerrada hasta que acaba su día.
    ultimas = [df.index[-1] for df in series.values()]
    observacion = min(ultimas)
    disponible = int((observacion + pd.Timedelta(days=1)).timestamp())

    if disponible > ahora_ts:
        raise SnapshotInvalido(
            f"el último cierre ({observacion.date()}) aún no estaba "
            f"disponible: no se construye un snapshot con datos del futuro"
        )

    # Se recorta cada serie a lo visible en el momento de observación, para
    # que ninguna lleve velas posteriores a las de las demás.
    recortadas = {t: df.loc[df.index <= observacion] for t, df in series.items()}

    ranking = m03_ranking(recortadas,
                          pd.Timestamp(disponible, unit="s", tz="UTC"), k=k)

    data_hash = _hash_total(recortadas, efectivo, universo_version,
                            config_hash)
    snapshot_id = f"{observacion.date()}-{data_hash}"

    return {
        "snapshot_id": snapshot_id,
        "retrieved_at": ahora_ts,
        "observation_time": int(observacion.timestamp()),
        "available_at_max": disponible,
        # La vigencia sale del calendario del snapshot, no de cuándo se
        # consulte. Consultarlo no lo prolonga.
        "valid_until": disponible + VIGENCIA_RANKING_DIAS * 86400,
        "adjustment_policy": POLITICA_AJUSTE,
        "universe_version": universo_version or ",".join(sorted(recortadas)),
        "strategy_version": VERSION_SNAPSHOT,
        "config_hash": config_hash,
        "full_data_hash": data_hash,
        "instrumentos": sorted(recortadas),
        "ranking": {
            "seleccionados": list(ranking.seleccionados),
            "scores": ranking.scores,
            "excluidos": ranking.excluidos,
            "as_of": ranking.as_of,
            "dataset_version": ranking.dataset_version,
            "k": k,
            "lookback": M03_LOOKBACK,
            "skip": M03_SKIP,
        },
        "series": recortadas,
        "efectivo": efectivo,
        "incidencias": incidencias,
    }


def guardar(snap: dict):
    """Persiste el snapshot. Sobrevive a un reinicio."""
    init_snapshots()
    import pickle
    with _conexion() as conn:
        conn.execute(
            f"""INSERT OR REPLACE INTO {TABLA} (
                snapshot_id, creado_en, retrieved_at, observation_time,
                available_at_max, valid_until, adjustment_policy,
                universe_version, strategy_version, config_hash,
                full_data_hash, instrumentos, ranking, series, efectivo,
                incidencias
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                snap["snapshot_id"],
                time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                snap["retrieved_at"], snap["observation_time"],
                snap["available_at_max"], snap["valid_until"],
                snap["adjustment_policy"], snap["universe_version"],
                snap["strategy_version"], snap["config_hash"],
                snap["full_data_hash"], json.dumps(snap["instrumentos"]),
                json.dumps(snap["ranking"], default=str),
                pickle.dumps(snap["series"]),
                pickle.dumps(snap["efectivo"]),
                json.dumps(snap["incidencias"]),
            ),
        )
    return snap["snapshot_id"]


def cargar_ultimo(decision_time=None) -> dict | None:
    """El snapshot más reciente que estaba DISPONIBLE al decidir.

    Nunca devuelve uno cuyos datos sean posteriores a la decisión. Es la
    comprobación que `max(ranking.as_of, ahora)` había desactivado.
    """
    init_snapshots()
    import pickle
    corte = (int(time.time()) if decision_time is None
             else int(pd.Timestamp(decision_time).timestamp()))
    with _conexion() as conn:
        conn.row_factory = sqlite3.Row
        fila = conn.execute(
            f"""SELECT * FROM {TABLA}
                WHERE available_at_max <= ?
                ORDER BY observation_time DESC LIMIT 1""",
            (corte,),
        ).fetchone()
    if fila is None:
        return None
    d = dict(fila)
    d["instrumentos"] = json.loads(d["instrumentos"])
    d["ranking"] = json.loads(d["ranking"])
    d["incidencias"] = json.loads(d["incidencias"] or "{}")
    try:
        d["series"] = pickle.loads(d["series"]) if d["series"] else {}
        d["efectivo"] = pickle.loads(d["efectivo"]) if d["efectivo"] else None
    except Exception as e:
        raise SnapshotInvalido(f"snapshot ilegible: {type(e).__name__}: {e}")
    return d


def a_ranking(snap: dict):
    """Reconstruye el objeto Ranking del snapshot guardado."""
    from institucional.modulos import Ranking
    r = snap["ranking"]
    return Ranking(
        seleccionados=tuple(r["seleccionados"]),
        scores=dict(r["scores"]),
        excluidos=dict(r["excluidos"]),
        as_of=int(r["as_of"]),
        dataset_version=str(r["dataset_version"]),
    )


def hace_falta_actualizar(decision_time=None) -> tuple[bool, str]:
    """Si toca reconstruir el snapshot. Lo decide el calendario, no el reloj."""
    snap = cargar_ultimo(decision_time)
    if snap is None:
        return True, "no hay ningún snapshot guardado"
    ahora = (int(time.time()) if decision_time is None
             else int(pd.Timestamp(decision_time).timestamp()))
    if ahora > snap["valid_until"]:
        dias = (ahora - snap["available_at_max"]) / 86400
        return True, f"el último tiene {dias:.0f} días y está caducado"
    return False, (f"vigente hasta "
                   f"{pd.Timestamp(snap['valid_until'], unit='s', tz='UTC').date()}")


def actualizar_si_toca(tickers, config_hash="", k=5, descargar=None,
                       decision_time=None) -> dict:
    """La tarea completa: comprueba, descarga si toca, guarda y devuelve."""
    hace_falta, motivo = hace_falta_actualizar(decision_time)
    if not hace_falta:
        return {"actualizado": False, "motivo": motivo,
                "snapshot": cargar_ultimo(decision_time)}
    snap = construir(tickers, config_hash=config_hash, k=k,
                     descargar=descargar, ahora=decision_time)
    guardar(snap)
    return {"actualizado": True, "motivo": motivo, "snapshot": snap}
