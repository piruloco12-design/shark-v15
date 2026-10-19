"""
Archivo histórico de velas.

PARA QUÉ SIRVE ESTO

yfinance solo da 60 días de histórico en timeframes por debajo de
una hora. Es un tope de la fuente: no hay forma de pedirle los 30m
de hace seis meses, no existen para nosotros.

Eso es el cuello de botella real del proyecto. Con 60 días de 30m y
el cooldown de 6h por activo salen unas 20-25 operaciones por
activo. Con esa muestra, ningún resultado de backtest es
concluyente: ni un buen número demuestra que hay edge, ni uno malo
demuestra que no lo hay.

Este módulo va guardando cada descarga en una base de datos local.
El bot gira cada 5 minutos; cada vez que baja velas, las nuevas se
acumulan aquí. La ventana móvil de 60 días se convierte en un
archivo que crece.

LO QUE ESTO NO HACE

No inventa el pasado. Empieza a acumular desde el día en que se
pone en marcha. Dentro de tres meses habrá tres meses de datos;
hoy hay 60 días. No hay atajo para eso con datos gratuitos.

Para validar sobre histórico largo YA, el camino es el timeframe
diario, donde yfinance da años:

    TIMEFRAME=1d PERIOD=15y python validator/shark_v15_backtester.py

AVISO SOBRE RENDER

Si DATABASE_NAME apunta a una ruta sin disco persistente montado,
este archivo se borra en cada reinicio y el módulo no sirve de
nada. Ver comprobar_persistencia().
"""

import os
import sqlite3
from datetime import datetime, timezone

import pandas as pd

from config import DATABASE_NAME

TABLA = "barras_historicas"

COLUMNAS_OHLCV = ["Open", "High", "Low", "Close", "Volume"]


def _conexion():
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def init_historial():
    """Crea la tabla si no existe. Idempotente."""
    conn = _conexion()
    cur = conn.cursor()

    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS {TABLA} (
            ticker      TEXT NOT NULL,
            timeframe   TEXT NOT NULL,
            ts          TEXT NOT NULL,
            open        REAL NOT NULL,
            high        REAL NOT NULL,
            low         REAL NOT NULL,
            close       REAL NOT NULL,
            volume      REAL,
            guardado_en TEXT NOT NULL,
            PRIMARY KEY (ticker, timeframe, ts)
        )
    """)

    # Acelera cargar() y resumen(), que filtran siempre por estos dos.
    cur.execute(f"""
        CREATE INDEX IF NOT EXISTS idx_{TABLA}_busqueda
        ON {TABLA} (ticker, timeframe, ts)
    """)

    conn.commit()
    conn.close()


def _a_utc(indice):
    """Normaliza cualquier índice de fechas a UTC."""
    if indice.tz is None:
        return indice.tz_localize("UTC")
    return indice.tz_convert("UTC")


def guardar(ticker, timeframe, df):
    """
    Guarda las velas de df en el archivo.

    Las velas que ya existían se sobrescriben (la fuente puede
    corregir una vela al cerrarla). Devuelve cuántas filas se
    escribieron.
    """
    if df is None or len(df) == 0:
        return 0

    faltan = [c for c in ["Open", "High", "Low", "Close"] if c not in df.columns]
    if faltan:
        raise ValueError(f"Faltan columnas para guardar historial: {faltan}")

    if not isinstance(df.index, pd.DatetimeIndex):
        raise ValueError("El DataFrame necesita un DatetimeIndex para guardarse")

    init_historial()

    trabajo = df.copy()
    trabajo.index = _a_utc(trabajo.index)

    if "Volume" not in trabajo.columns:
        trabajo["Volume"] = 0.0

    ahora = datetime.now(timezone.utc).isoformat()
    ticker = str(ticker).upper()
    timeframe = str(timeframe)

    filas = []
    for ts, fila in trabajo.iterrows():
        try:
            filas.append((
                ticker,
                timeframe,
                ts.isoformat(),
                float(fila["Open"]),
                float(fila["High"]),
                float(fila["Low"]),
                float(fila["Close"]),
                float(fila["Volume"]) if pd.notna(fila["Volume"]) else 0.0,
                ahora,
            ))
        except (TypeError, ValueError):
            # Una vela corrupta no debe tumbar el guardado de las demás.
            continue

    if not filas:
        return 0

    conn = _conexion()
    conn.executemany(
        f"""INSERT OR REPLACE INTO {TABLA}
            (ticker, timeframe, ts, open, high, low, close, volume, guardado_en)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        filas,
    )
    conn.commit()
    conn.close()

    return len(filas)


def cargar(ticker, timeframe, desde=None, hasta=None):
    """
    Devuelve el histórico acumulado como DataFrame con las mismas
    columnas y el mismo formato de índice que data_feed.get_data,
    para que el resto del bot no note la diferencia.

    Devuelve un DataFrame vacío si no hay nada guardado.
    """
    init_historial()

    consulta = f"""
        SELECT ts, open, high, low, close, volume
        FROM {TABLA}
        WHERE ticker = ? AND timeframe = ?
    """
    parametros = [str(ticker).upper(), str(timeframe)]

    if desde is not None:
        consulta += " AND ts >= ?"
        parametros.append(pd.Timestamp(desde, tz="UTC").isoformat())

    if hasta is not None:
        consulta += " AND ts <= ?"
        parametros.append(pd.Timestamp(hasta, tz="UTC").isoformat())

    consulta += " ORDER BY ts ASC"

    conn = _conexion()
    filas = conn.execute(consulta, parametros).fetchall()
    conn.close()

    if not filas:
        return pd.DataFrame(columns=COLUMNAS_OHLCV)

    df = pd.DataFrame(
        [dict(f) for f in filas]
    ).rename(columns={
        "open": "Open",
        "high": "High",
        "low": "Low",
        "close": "Close",
        "volume": "Volume",
    })

    df["ts"] = pd.to_datetime(df["ts"], utc=True, format="ISO8601")
    df = df.set_index("ts").sort_index()
    df.index.name = None

    return df[COLUMNAS_OHLCV]


def fusionar(ticker, timeframe, df_nuevo):
    """
    Guarda df_nuevo en el archivo y devuelve la unión de todo lo
    acumulado para ese activo y timeframe.

    Esta es la función que convierte la ventana móvil de 60 días en
    un histórico que crece. Si el archivo está vacío, devuelve
    df_nuevo tal cual.
    """
    guardar(ticker, timeframe, df_nuevo)

    completo = cargar(ticker, timeframe)

    if len(completo) == 0:
        return df_nuevo

    return completo


def resumen():
    """
    Qué hay guardado: filas, rango de fechas y días distintos por
    activo y timeframe. Para saber cuánto histórico se ha
    acumulado ya.
    """
    init_historial()

    conn = _conexion()
    filas = conn.execute(f"""
        SELECT ticker, timeframe,
               COUNT(*)  AS velas,
               MIN(ts)   AS primera,
               MAX(ts)   AS ultima
        FROM {TABLA}
        GROUP BY ticker, timeframe
        ORDER BY ticker, timeframe
    """).fetchall()
    conn.close()

    salida = []
    for f in filas:
        primera = pd.Timestamp(f["primera"])
        ultima = pd.Timestamp(f["ultima"])
        salida.append({
            "ticker": f["ticker"],
            "timeframe": f["timeframe"],
            "velas": f["velas"],
            "primera": f["primera"],
            "ultima": f["ultima"],
            "dias_calendario": (ultima - primera).days,
        })

    return salida


def comprobar_persistencia():
    """
    Avisa si la base de datos está en una ruta que se borra al
    reiniciar.

    En Render, un worker sin bloque `disk:` en render.yaml tiene
    sistema de ficheros efímero: cada deploy o reinicio deja la
    base de datos en blanco. Eso borra el histórico de trades, el
    capital acumulado y este archivo de velas.

    Devuelve (es_persistente, mensaje).
    """
    ruta = os.path.abspath(DATABASE_NAME)

    # Rutas donde Render monta discos persistentes.
    montajes_persistentes = ["/var/data", "/data", "/mnt"]

    en_disco_montado = any(
        ruta.startswith(m + os.sep) or ruta == m
        for m in montajes_persistentes
    )

    if en_disco_montado:
        return True, f"Base de datos en disco persistente: {ruta}"

    # Antes esto dependia de detectar Render por variable de
    # entorno: si Render no definia RENDER ni RENDER_SERVICE_ID,
    # la funcion decia "fuera de Render" y callaba, aunque la base
    # de datos estuviera en almacenamiento efimero.
    #
    # Un diagnostico no deberia depender de adivinar donde corre.
    # Ahora se avisa SIEMPRE que la ruta no este bajo un punto de
    # montaje conocido, y el mensaje lleva la ruta real para que
    # se pueda comprobar a simple vista.
    if not os.path.isabs(DATABASE_NAME):
        return False, (
            f"AVISO: DATABASE_NAME es una ruta RELATIVA "
            f"({DATABASE_NAME!r}), que se resuelve a {ruta}. "
            f"En Render eso es almacenamiento efímero y se borra en "
            f"cada reinicio. Falta la barra inicial: "
            f"DATABASE_NAME=/var/data/shark_v8.db"
        )

    return False, (
        f"AVISO: la base de datos está en {ruta}, que no está bajo "
        f"ningún disco montado ({', '.join(montajes_persistentes)}). "
        f"Si esto corre en Render se borra en cada reinicio: se pierden "
        f"el histórico de trades, el capital acumulado y el archivo de "
        f"velas."
    )


if __name__ == "__main__":
    persistente, mensaje = comprobar_persistencia()
    print(mensaje)
    print()

    datos = resumen()
    if not datos:
        print("El archivo histórico está vacío.")
        print("Se llena solo: cada ciclo del bot guarda las velas que descarga.")
    else:
        print(f"{'ACTIVO':8} {'TF':5} {'VELAS':>7} {'DIAS':>6}  RANGO")
        for d in datos:
            print(
                f"{d['ticker']:8} {d['timeframe']:5} {d['velas']:7} "
                f"{d['dias_calendario']:6}  {d['primera'][:16]} -> {d['ultima'][:16]}"
            )
