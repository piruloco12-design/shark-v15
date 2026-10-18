import time
from datetime import datetime, timedelta, timezone

import pandas as pd
import requests
import yfinance as yf

from config import (
    REQUEST_TIMEOUT,
    DATA_PROVIDER_ORDER,
    MIN_BARS,
    POLYGON_API_KEY,
    POLYGON_BASE_URL,
    TWELVE_DATA_API_KEY,
    ALPHA_VANTAGE_API_KEY,
    FINNHUB_API_KEY,
)

# Horario regular del mercado USA (Regular Trading Hours).
# yfinance devuelve SOLO RTH por defecto. Polygon y Finnhub
# devuelven también pre-market y after-hours, que son velas de
# muy poca liquidez: ensucian ATR, ADX y EMA200, y además el
# filtro de sesión las bloquea todas después. Hay que recortarlas
# en el origen para que todos los providers den lo mismo.
RTH_INICIO = "09:30"
RTH_FIN = "16:00"
ZONA_MERCADO = "US/Eastern"

YF_INTERVAL_MAP = {
    "1m": "1m",
    "5m": "5m",
    "15m": "15m",
    "30m": "30m",
    "60m": "60m",
    "1h": "60m",
    "1d": "1d",
}

TWELVE_INTERVAL_MAP = {
    "1m": "1min",
    "5m": "5min",
    "15m": "15min",
    "30m": "30min",
    "60m": "1h",
    "1h": "1h",
    "1d": "1day",
}

ALPHA_INTERVAL_MAP = {
    "1m": "1min",
    "5m": "5min",
    "15m": "15min",
    "30m": "30min",
    "60m": "60min",
    "1h": "60min",
}

FINNHUB_RESOLUTION_MAP = {
    "1m": "1",
    "5m": "5",
    "15m": "15",
    "30m": "30",
    "60m": "60",
    "1h": "60",
    "1d": "D",
}

# Stooq: gratis, sin clave, decadas de historico diario, e
# independiente de Yahoo. Importa porque yfinance se rompio en
# febrero de 2025 cuando Yahoo rediseno la web: depender de un
# solo raspador es un punto unico de fallo.
STOOQ_INTERVAL_MAP = {
    "5m": "5",
    "60m": "60",
    "1h": "60",
    "1d": "d",
    "1wk": "w",
    "1mo": "m",
}

# Coinbase Exchange: gratis, sin clave, historico profundo de
# cripto en cualquier timeframe. 300 velas por peticion, asi que
# hay que paginar.
COINBASE_GRANULARIDAD = {
    "1m": 60,
    "5m": 300,
    "15m": 900,
    "60m": 3600,
    "1h": 3600,
    "6h": 21600,
    "1d": 86400,
}

POLYGON_TIMESPAN_MAP = {
    "1m": (1, "minute"),
    "5m": (5, "minute"),
    "15m": (15, "minute"),
    "30m": (30, "minute"),
    "60m": (1, "hour"),
    "1h": (1, "hour"),
    "1d": (1, "day"),
}


def _normalize_df(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        raise ValueError("DataFrame vacío")

    df = df.copy()

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]

    rename_map = {
        "open": "Open",
        "high": "High",
        "low": "Low",
        "close": "Close",
        "volume": "Volume",
        "datetime": "Datetime",
        "date": "Datetime",
        "timestamp": "Datetime",
    }

    df.columns = [rename_map.get(str(c).lower(), c) for c in df.columns]

    required = ["Open", "High", "Low", "Close"]
    for col in required:
        if col not in df.columns:
            raise ValueError(f"Falta columna requerida: {col}")

    if "Volume" not in df.columns:
        df["Volume"] = 0.0

    if not isinstance(df.index, pd.DatetimeIndex):
        if "Datetime" in df.columns:
            df["Datetime"] = pd.to_datetime(df["Datetime"], errors="coerce", utc=True)
            df = df.set_index("Datetime")
        else:
            raise ValueError("No se pudo construir DatetimeIndex")

    df = df.sort_index()
    df = df[~df.index.duplicated(keep="last")]

    numeric_cols = ["Open", "High", "Low", "Close", "Volume"]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.dropna(subset=["Open", "High", "Low", "Close"])

    if len(df) < MIN_BARS:
        raise ValueError(
            f"Muy pocas velas descargadas: {len(df)} < {MIN_BARS} "
            f"(ema200 necesita 200 velas o el bot deja de señalizar en silencio)"
        )

    return df


def _recortar_a_rth(df: pd.DataFrame, timeframe: str) -> pd.DataFrame:
    """
    Deja solo las velas del horario regular del mercado USA.

    Sin esto, Polygon y Finnhub entregan 4:00-20:00 ET (unas 32
    velas de 30m al día) mientras yfinance entrega 9:30-16:00
    (13 velas al día). Comparar un backtest de Polygon con uno de
    yfinance sin recortar NO es comparar lo mismo: son universos
    de datos distintos.
    """
    if df is None or df.empty:
        return df

    if not isinstance(df.index, pd.DatetimeIndex):
        return df

    # En diario no hay horario intradía que recortar.
    if timeframe in ["1d", "1wk", "1mo"]:
        return df

    try:
        if df.index.tz is None:
            idx_et = df.index.tz_localize("UTC").tz_convert(ZONA_MERCADO)
        else:
            idx_et = df.index.tz_convert(ZONA_MERCADO)
    except Exception as e:
        print(
            f"FEED | AVISO: no se pudo convertir a {ZONA_MERCADO} ({e}). "
            f"Los datos van SIN recortar a horario regular. "
            f"¿falta el paquete tzdata?"
        )
        return df

    original = df.copy()
    original.index = idx_et

    # Días de semana y dentro de RTH. El cierre es exclusivo: la
    # última vela de 30m arranca a las 15:30, nunca a las 16:00.
    recortado = original[original.index.dayofweek < 5]
    recortado = recortado.between_time(RTH_INICIO, RTH_FIN, inclusive="left")

    if recortado.empty:
        return df

    return recortado


def _period_to_date_range(period: str):
    now = datetime.now(timezone.utc)
    period = (period or "60d").strip().lower()

    if period.endswith("d"):
        days = int(period[:-1])
        start = now - timedelta(days=days)
    elif period.endswith("mo"):
        months = int(period[:-2])
        start = now - timedelta(days=months * 30)
    elif period.endswith("y"):
        years = int(period[:-1])
        start = now - timedelta(days=years * 365)
    else:
        start = now - timedelta(days=60)

    return start.date().isoformat(), now.date().isoformat()


def _polygon_download(symbol: str, timeframe: str, period: str):
    if not POLYGON_API_KEY:
        raise ValueError("POLYGON_API_KEY no configurada")

    spec = POLYGON_TIMESPAN_MAP.get(timeframe)
    if spec is None:
        raise ValueError(f"Timeframe no soportado en Polygon: {timeframe}")

    multiplier, timespan = spec
    date_from, date_to = _period_to_date_range(period)

    url = (
        f"{POLYGON_BASE_URL}/v2/aggs/ticker/{symbol}/range/"
        f"{multiplier}/{timespan}/{date_from}/{date_to}"
    )

    params = {
        "adjusted": "true",
        "sort": "asc",
        "limit": 50000,
        "apiKey": POLYGON_API_KEY,
    }

    response = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    data = response.json()

    results = data.get("results", [])
    if not results:
        raise ValueError(f"Polygon sin datos para {symbol}: {data}")

    rows = []
    for item in results:
        rows.append({
            "Datetime": pd.to_datetime(item["t"], unit="ms", utc=True),
            "Open": item["o"],
            "High": item["h"],
            "Low": item["l"],
            "Close": item["c"],
            "Volume": item.get("v", 0),
        })

    df = pd.DataFrame(rows).set_index("Datetime")
    df = _recortar_a_rth(df, timeframe)
    return _normalize_df(df), "polygon"


def _sufijo_stooq(symbol: str) -> str:
    """
    Stooq usa sufijos: .us para valores de EEUU, ^ para indices,
    .f para futuros. Si el simbolo ya trae sufijo o prefijo, se
    respeta tal cual.
    """
    s = symbol.strip().lower()
    if s.startswith("^") or "." in s:
        return s
    return f"{s}.us"


def _stooq_download(symbol: str, timeframe: str, period: str):
    intervalo = STOOQ_INTERVAL_MAP.get(timeframe)
    if intervalo is None:
        raise ValueError(f"Timeframe no soportado en Stooq: {timeframe}")

    url = "https://stooq.com/q/d/l/"
    params = {"s": _sufijo_stooq(symbol), "i": intervalo}

    respuesta = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
    respuesta.raise_for_status()

    texto = respuesta.text.strip()

    # Stooq devuelve 200 con cuerpo de texto cuando no hay datos.
    if not texto or texto.lower().startswith("no data") or "<" in texto[:1]:
        raise ValueError(f"Stooq sin datos para {symbol}: {texto[:120]}")

    from io import StringIO
    df = pd.read_csv(StringIO(texto))

    if "Date" not in df.columns and "Datetime" not in df.columns:
        raise ValueError(f"Stooq devolvio columnas inesperadas: {list(df.columns)}")

    columna_fecha = "Date" if "Date" in df.columns else "Datetime"
    df[columna_fecha] = pd.to_datetime(df[columna_fecha], errors="coerce", utc=True)
    df = df.rename(columns={columna_fecha: "Datetime"}).set_index("Datetime")

    # Recorte al periodo pedido: Stooq siempre manda todo.
    inicio, _ = _period_to_date_range(period)
    df = df[df.index >= pd.Timestamp(inicio, tz="UTC")]

    df = _recortar_a_rth(df, timeframe)
    return _normalize_df(df), "stooq"


def _coinbase_download(symbol: str, timeframe: str, period: str):
    """
    Historico de cripto desde Coinbase Exchange. Gratis y sin
    clave. Devuelve 300 velas por peticion, asi que se pagina
    hacia atras hasta cubrir el periodo.

    El simbolo va en formato Coinbase: BTC-USD, ETH-USD.
    """
    granularidad = COINBASE_GRANULARIDAD.get(timeframe)
    if granularidad is None:
        raise ValueError(f"Timeframe no soportado en Coinbase: {timeframe}")

    par = symbol.strip().upper().replace("USDT", "USD")
    if "-" not in par:
        raise ValueError(
            f"Coinbase necesita el par con guion (BTC-USD), recibido: {symbol}"
        )

    inicio_str, _ = _period_to_date_range(period)
    inicio = pd.Timestamp(inicio_str, tz="UTC")
    fin = pd.Timestamp.now(tz="UTC")

    url = f"https://api.exchange.coinbase.com/products/{par}/candles"
    filas = []
    cursor = fin
    peticiones = 0
    LIMITE_PETICIONES = 400   # tope de seguridad

    while cursor > inicio and peticiones < LIMITE_PETICIONES:
        desde = cursor - pd.Timedelta(seconds=granularidad * 300)
        if desde < inicio:
            desde = inicio

        respuesta = requests.get(
            url,
            params={
                "granularity": granularidad,
                "start": desde.isoformat(),
                "end": cursor.isoformat(),
            },
            timeout=REQUEST_TIMEOUT,
        )
        peticiones += 1

        if respuesta.status_code == 429:
            time.sleep(1.0)
            continue

        respuesta.raise_for_status()
        lote = respuesta.json()

        if not isinstance(lote, list) or not lote:
            break

        # Coinbase devuelve [time, low, high, open, close, volume]
        for vela in lote:
            filas.append({
                "Datetime": pd.to_datetime(vela[0], unit="s", utc=True),
                "Low": vela[1],
                "High": vela[2],
                "Open": vela[3],
                "Close": vela[4],
                "Volume": vela[5],
            })

        cursor = desde
        time.sleep(0.12)   # cortesia con el limite de peticiones

    if not filas:
        raise ValueError(f"Coinbase sin datos para {par}")

    df = pd.DataFrame(filas).set_index("Datetime")
    df = df[~df.index.duplicated(keep="last")].sort_index()

    # Cripto cotiza 24/7: aqui NO se recorta a horario de mercado.
    return _normalize_df(df), "coinbase"


def _yf_download(symbol: str, timeframe: str, period: str):
    interval = YF_INTERVAL_MAP.get(timeframe, "60m")

    df = yf.download(
        symbol,
        period=period,
        interval=interval,
        auto_adjust=False,
        progress=False,
        threads=False,
        prepost=False,  # explícito: solo horario regular
    )

    return _normalize_df(df), "yfinance"


def _twelve_data_download(symbol: str, timeframe: str, period: str):
    if not TWELVE_DATA_API_KEY:
        raise ValueError("TWELVE_DATA_API_KEY no configurada")

    interval = TWELVE_INTERVAL_MAP.get(timeframe)
    if interval is None:
        raise ValueError(f"Timeframe no soportado en Twelve Data: {timeframe}")

    url = "https://api.twelvedata.com/time_series"
    params = {
        "symbol": symbol,
        "interval": interval,
        # 500 velas no llegaban a MIN_BARS después de recortar
        # a horario regular. Pedimos holgura.
        "outputsize": 5000,
        "apikey": TWELVE_DATA_API_KEY,
        "format": "JSON",
    }

    response = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    data = response.json()

    if "values" not in data:
        raise ValueError(f"Twelve Data sin values para {symbol}: {data}")

    df = pd.DataFrame(data["values"])
    df["datetime"] = pd.to_datetime(df["datetime"], errors="coerce", utc=True)
    df = df.rename(columns={
        "open": "Open",
        "high": "High",
        "low": "Low",
        "close": "Close",
        "volume": "Volume",
    })
    df = df.set_index("datetime")
    df = _recortar_a_rth(df, timeframe)

    return _normalize_df(df), "twelve_data"


def _alpha_vantage_download(symbol: str, timeframe: str, period: str):
    if not ALPHA_VANTAGE_API_KEY:
        raise ValueError("ALPHA_VANTAGE_API_KEY no configurada")

    if timeframe in ["1d"]:
        url = "https://www.alphavantage.co/query"
        params = {
            "function": "TIME_SERIES_DAILY",
            "symbol": symbol,
            "outputsize": "full",
            "apikey": ALPHA_VANTAGE_API_KEY,
        }
        response = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        data = response.json()

        key = "Time Series (Daily)"
        if key not in data:
            raise ValueError(f"Alpha Vantage sin daily series para {symbol}: {data}")

        rows = []
        for dt, row in data[key].items():
            rows.append({
                "Datetime": dt,
                "Open": row["1. open"],
                "High": row["2. high"],
                "Low": row["3. low"],
                "Close": row["4. close"],
                "Volume": row["5. volume"],
            })

        df = pd.DataFrame(rows)
        df["Datetime"] = pd.to_datetime(df["Datetime"], errors="coerce", utc=True)
        df = df.set_index("Datetime")
        return _normalize_df(df), "alpha_vantage"

    interval = ALPHA_INTERVAL_MAP.get(timeframe)
    if interval is None:
        raise ValueError(f"Timeframe no soportado en Alpha Vantage: {timeframe}")

    url = "https://www.alphavantage.co/query"
    params = {
        "function": "TIME_SERIES_INTRADAY",
        "symbol": symbol,
        "interval": interval,
        "outputsize": "full",
        "extended_hours": "false",  # solo horario regular
        "apikey": ALPHA_VANTAGE_API_KEY,
    }

    response = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    data = response.json()

    key = f"Time Series ({interval})"
    if key not in data:
        raise ValueError(f"Alpha Vantage sin intraday series para {symbol}: {data}")

    rows = []
    for dt, row in data[key].items():
        rows.append({
            "Datetime": dt,
            "Open": row["1. open"],
            "High": row["2. high"],
            "Low": row["3. low"],
            "Close": row["4. close"],
            "Volume": row["5. volume"],
        })

    df = pd.DataFrame(rows)
    df["Datetime"] = pd.to_datetime(df["Datetime"], errors="coerce", utc=True)
    df = df.set_index("Datetime")
    df = _recortar_a_rth(df, timeframe)

    return _normalize_df(df), "alpha_vantage"


def _finnhub_download(symbol: str, timeframe: str, period: str):
    if not FINNHUB_API_KEY:
        raise ValueError("FINNHUB_API_KEY no configurada")

    resolution = FINNHUB_RESOLUTION_MAP.get(timeframe)
    if resolution is None:
        raise ValueError(f"Timeframe no soportado en Finnhub: {timeframe}")

    now_ts = int(time.time())

    if timeframe in ["1m"]:
        from_ts = now_ts - 60 * 60 * 24 * 7
    elif timeframe in ["5m", "15m", "30m", "60m", "1h"]:
        from_ts = now_ts - 60 * 60 * 24 * 180
    else:
        from_ts = now_ts - 60 * 60 * 24 * 365 * 2

    url = "https://finnhub.io/api/v1/stock/candle"
    params = {
        "symbol": symbol,
        "resolution": resolution,
        "from": from_ts,
        "to": now_ts,
        "token": FINNHUB_API_KEY,
    }

    response = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    data = response.json()

    if data.get("s") != "ok":
        raise ValueError(f"Finnhub sin datos para {symbol}: {data}")

    df = pd.DataFrame({
        "Datetime": pd.to_datetime(data["t"], unit="s", utc=True),
        "Open": data["o"],
        "High": data["h"],
        "Low": data["l"],
        "Close": data["c"],
        "Volume": data["v"],
    }).set_index("Datetime")

    df = _recortar_a_rth(df, timeframe)
    return _normalize_df(df), "finnhub"


def get_data(symbol: str, timeframe: str = "1h", period: str = "6mo"):
    errors = []

    for provider in DATA_PROVIDER_ORDER:
        try:
            if provider == "polygon":
                return _polygon_download(symbol, timeframe, period)

            if provider == "yfinance":
                return _yf_download(symbol, timeframe, period)

            if provider == "stooq":
                return _stooq_download(symbol, timeframe, period)

            if provider == "coinbase":
                return _coinbase_download(symbol, timeframe, period)

            if provider == "twelve_data":
                return _twelve_data_download(symbol, timeframe, period)

            if provider == "alpha_vantage":
                return _alpha_vantage_download(symbol, timeframe, period)

            if provider == "finnhub":
                return _finnhub_download(symbol, timeframe, period)

        except Exception as e:
            errors.append(f"{provider}: {e}")

    raise ValueError(f"No se pudo descargar {symbol} con ningún provider. Detalles: {errors}")