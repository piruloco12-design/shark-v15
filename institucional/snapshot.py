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


FORMATO_CREADO = "%Y-%m-%dT%H:%M:%SZ"


def _creado_texto(ts=None):
    """`creado_en` en el formato EXACTO con el que se guarda.

    Es texto, no entero, y de ancho fijo: por eso se compara
    lexicograficamente. Comparar esta columna con un entero en SQLite no
    da un error, da SIEMPRE falso, porque un INTEGER siempre ordena antes
    que un TEXT. Un filtro asi no es estricto: rechaza todo.
    """
    return time.strftime(FORMATO_CREADO,
                         time.gmtime(time.time() if ts is None else ts))


def _creado_ts(valor):
    """De `creado_en` a segundos. 0 si no se puede leer."""
    try:
        t = pd.Timestamp(str(valor))
        if t.tz is None:
            t = t.tz_localize("UTC")
        return int(t.timestamp())
    except Exception:
        return 0


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

    # El momento de observación es el último cierre COMUN que YA ESTABA
    # DISPONIBLE. Una vela diaria no está cerrada hasta que acaba su día,
    # así que su dato está disponible el día siguiente.
    #
    # Lo que hacía antes: tomaba `min(ultimas)` y, si ese último cierre aún
    # no estaba disponible, lanzaba SnapshotInvalido y tiraba el snapshot
    # ENTERO. Con 299 velas maduras y una abierta se quedaba sin ninguna.
    # Una vela que todavía no ha cerrado se RECORTA; no invalida la
    # historia que sí cerró.
    #
    # Y la observación sale de la INTERSECCION real de calendarios, no de
    # `min(ultimas)`: con huecos o festivos distintos, el mínimo de los
    # últimos cierres puede ser una fecha que alguna serie no tiene.
    def _disponible_en(fecha):
        return int((fecha + pd.Timedelta(days=1)).timestamp()) <= ahora_ts

    comun = None
    for df in series.values():
        fechas = set(df.index)
        comun = fechas if comun is None else (comun & fechas)
    candidatas = sorted(f for f in (comun or set()) if _disponible_en(f))

    interseccion_real = bool(candidatas)
    if candidatas:
        observacion = candidatas[-1]
    else:
        # Sin fecha común a todas las series. Se usa el mínimo de los
        # últimos cierres DISPONIBLES de cada una, y queda dicho que no
        # hubo intersección en vez de pasar por una.
        ultimos = []
        for t, df in series.items():
            d = [f for f in df.index if _disponible_en(f)]
            if d:
                ultimos.append(d[-1])
            else:
                incidencias[t] = "ninguna vela cerrada y disponible"
        if not ultimos:
            raise SnapshotInvalido(
                f"ninguna serie tiene una vela cerrada y disponible a "
                f"{pd.Timestamp(ahora_ts, unit='s', tz='UTC').date()}. "
                f"Incidencias: {incidencias}"
            )
        observacion = min(ultimos)
        incidencias["_calendario"] = (
            "sin fecha común a todas las series: la observación sale del "
            "mínimo de los últimos cierres disponibles")

    disponible = int((observacion + pd.Timedelta(days=1)).timestamp())

    # Se recorta cada serie a lo visible en el momento de observación, para
    # que ninguna lleve velas posteriores a las de las demás. La referencia
    # de EFECTIVO se recorta igual: si conserva velas posteriores, la señal
    # mira el futuro por ese lado y nadie lo nota.
    recortadas = {t: df.loc[df.index <= observacion] for t, df in series.items()}
    if efectivo is not None and len(efectivo):
        efectivo = efectivo.loc[efectivo.index <= observacion]

    # Tras recortar, una serie puede quedarse sin historia suficiente. Se
    # retira de ESTE snapshot con su motivo; no se silencia.
    cortas = {t: len(df) for t, df in recortadas.items()
              if len(df) < M03_LOOKBACK + 2}
    for t, n in cortas.items():
        incidencias[t] = f"historico insuficiente tras recortar ({n})"
        recortadas.pop(t)
    if not recortadas:
        raise SnapshotInvalido(
            f"ninguna serie conserva histórico suficiente tras recortar a "
            f"{observacion.date()}. Incidencias: {incidencias}")

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
        # Periodo de señal, disponibilidad y recuperación van SEPARADOS, y
        # la cobertura queda dicha en vez de supuesta.
        "interseccion_real": interseccion_real,
        "filas_por_instrumento": {t: int(len(df))
                                  for t, df in sorted(recortadas.items())},
        "filas_efectivo": int(len(efectivo)) if efectivo is not None else 0,
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
                # Si el snapshot declara su propio momento de creacion se
                # respeta: una captura historica reconstruida tiene que
                # poder decir CUANDO se creo, en vez de sellarse con la
                # hora de hoy y quedar inservible como evidencia.
                snap.get("creado_en") or _creado_texto(),
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


def cargar_ultimo(decision_time=None, permitir_replay_revisado=False) -> dict | None:
    """El snapshot que ESTABA DISPONIBLE y YA SE HABIA RECUPERADO al decidir.

    Nunca devuelve uno cuyos datos sean posteriores a la decisión. Es la
    comprobación que `max(ranking.as_of, ahora)` había desactivado.

    Y ahora exige las TRES fechas, no solo una: disponibilidad,
    recuperación y creación. Antes filtraba por `available_at_max` a secas,
    así que un snapshot descargado el 16 de marzo se devolvía para una
    decisión del 26 de febrero. Los datos eran anteriores al corte, sí,
    pero la REVISION de esos datos no se conocía entonces: un proveedor
    revisa precios hacia atrás, y usar la revisión posterior es mirar el
    futuro con otro nombre.

    `permitir_replay_revisado=True` lo devuelve de todos modos, marcado con
    `replay_revisado=True`. Sirve para reconstruir, no para afirmar qué se
    sabía en esa fecha, y por eso hay que pedirlo explícitamente.
    """
    init_snapshots()
    import pickle
    corte = (int(time.time()) if decision_time is None
             else int(pd.Timestamp(decision_time).timestamp()))
    with _conexion() as conn:
        conn.row_factory = sqlite3.Row
        if permitir_replay_revisado:
            fila = conn.execute(
                f"""SELECT * FROM {TABLA}
                    WHERE available_at_max <= ?
                    ORDER BY observation_time DESC LIMIT 1""",
                (corte,),
            ).fetchone()
        else:
            fila = conn.execute(
                f"""SELECT * FROM {TABLA}
                    WHERE available_at_max <= ?
                      AND retrieved_at <= ?
                      AND creado_en <= ?
                    ORDER BY observation_time DESC LIMIT 1""",
                (corte, corte, _creado_texto(corte)),
            ).fetchone()
    if fila is None:
        return None
    d = dict(fila)
    d["replay_revisado"] = bool(
        permitir_replay_revisado
        and (int(d.get("retrieved_at") or 0) > corte
             or _creado_ts(d.get("creado_en")) > corte))
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
