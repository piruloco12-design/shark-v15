import time
import requests
import pandas as pd
import yfinance as yf

from config import (
    REQUEST_TIMEOUT,
    DATA_PROVIDER_ORDER,
    TWELVE_DATA_API_KEY,
    ALPHA_VANTAGE_API_KEY,
    FINNHUB_API_KEY
)


YF_INTERVAL_MAP = {
    "1m": "1m",
    "5m": "5m",
    "15m": "15m",
    "30m": "30m",
    "60m": "60m",
    "1h": "60m",
    "1d": "1d"
}

TWELVE_INTERVAL_MAP = {
    "1m": "1min",
    "5m": "5min",
    "15m": "15min",
    "30m": "30min",
    "60m": "1h",
    "1h": "1h",
    "1d": "1day"
}

ALPHA_INTERVAL_MAP = {
    "1m": "1min",
    "5m": "5min",
    "15m": "15min",
    "30m": "30min",
    "60m": "60min",
    "1h": "60min"
}

FINNHUB_RESOLUTION_MAP = {
    "1m": "1",
    "5m": "5",
    "15m": "15",
    "30m": "30",
    "60m": "60",
    "1h": "60",
    "1d": "D"
}


def _normalize_df(df):
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
        "date": "Datetime"
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

    if len(df) < 50:
        raise ValueError(f"Muy pocas velas descargadas: {len(df)}")

    return df


def _is_rate_limit_error(error_text):
    text = str(error_text).lower()
    patterns = [
        "too many requests",
        "rate limited",
        "rate limit",
        "429"
    ]
    return any(p in text for p in patterns)


def _provider_pause(seconds=1.0):
    time.sleep(seconds)


def _yf_download(symbol, timeframe, period):
    interval = YF_INTERVAL_MAP.get(timeframe, "60m")

    df = yf.download(
        symbol,
        period=period,
        interval=interval,
        auto_adjust=False,
        progress=False,
        threads=False
    )

    return _normalize_df(df), "yfinance"


def _twelve_data_download(symbol, timeframe, period):
    if not TWELVE_DATA_API_KEY:
        raise ValueError("TWELVE_DATA_API_KEY no configurada")

    interval = TWELVE_INTERVAL_MAP.get(timeframe)
    if interval is None:
        raise ValueError(f"Timeframe no soportado en Twelve Data: {timeframe}")

    url = "https://api.twelvedata.com/time_series"
    params = {
        "symbol": symbol,
        "interval": interval,
        "outputsize": 500,
        "apikey": TWELVE_DATA_API_KEY,
        "format": "JSON"
    }

    response = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    data = response.json()

    if "code" in data and "message" in data:
        raise ValueError(f"Twelve Data error para {symbol}: {data.get('message')}")

    if "values" not in data:
        raise ValueError(f"Twelve Data sin values para {symbol}: {data}")

    df = pd.DataFrame(data["values"])
    df["datetime"] = pd.to_datetime(df["datetime"], errors="coerce", utc=True)
    df = df.rename(columns={
        "open": "Open",
        "high": "High",
        "low": "Low",
        "close": "Close",
        "volume": "Volume"
    })
    df = df.set_index("datetime")

    return _normalize_df(df), "twelve_data"


def _alpha_vantage_download(symbol, timeframe, period):
    if not ALPHA_VANTAGE_API_KEY:
        raise ValueError("ALPHA_VANTAGE_API_KEY no configurada")

    url = "https://www.alphavantage.co/query"

    if timeframe in ["1d"]:
        params = {
            "function": "TIME_SERIES_DAILY",
            "symbol": symbol,
            "outputsize": "full",
            "apikey": ALPHA_VANTAGE_API_KEY
        }

        response = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        data = response.json()

        if "Note" in data:
            raise ValueError(f"Alpha Vantage rate limit para {symbol}: {data['Note']}")

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
                "Volume": row["5. volume"]
            })

        df = pd.DataFrame(rows)
        df["Datetime"] = pd.to_datetime(df["Datetime"], errors="coerce", utc=True)
        df = df.set_index("Datetime")
        return _normalize_df(df), "alpha_vantage"

    interval = ALPHA_INTERVAL_MAP.get(timeframe)
    if interval is None:
        raise ValueError(f"Timeframe no soportado en Alpha Vantage: {timeframe}")

    params = {
        "function": "TIME_SERIES_INTRADAY",
        "symbol": symbol,
        "interval": interval,
        "outputsize": "full",
        "apikey": ALPHA_VANTAGE_API_KEY
    }

    response = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    data = response.json()

    if "Note" in data:
        raise ValueError(f"Alpha Vantage rate limit para {symbol}: {data['Note']}")

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
            "Volume": row["5. volume"]
        })

    df = pd.DataFrame(rows)
    df["Datetime"] = pd.to_datetime(df["Datetime"], errors="coerce", utc=True)
    df = df.set_index("Datetime")

    return _normalize_df(df), "alpha_vantage"


def _finnhub_download(symbol, timeframe, period):
    if not FINNHUB_API_KEY:
        raise ValueError("FINNHUB_API_KEY no configurada")

    resolution = FINNHUB_RESOLUTION_MAP.get(timeframe)
    if resolution is None:
        raise ValueError(f"Timeframe no soportado en Finnhub: {timeframe}")

    now_ts = int(time.time())

    if timeframe == "1m":
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
        "token": FINNHUB_API_KEY
    }

    response = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    data = response.json()

    if data.get("error"):
        raise ValueError(f"Finnhub error para {symbol}: {data.get('error')}")

    if data.get("s") != "ok":
        raise ValueError(f"Finnhub sin datos para {symbol}: {data}")

    df = pd.DataFrame({
        "Datetime": pd.to_datetime(data["t"], unit="s", utc=True),
        "Open": data["o"],
        "High": data["h"],
        "Low": data["l"],
        "Close": data["c"],
        "Volume": data["v"]
    }).set_index("Datetime")

    return _normalize_df(df), "finnhub"


def get_data(symbol, timeframe="1h", period="6mo"):
    errors = []

    for provider in DATA_PROVIDER_ORDER:
        provider = str(provider).strip().lower()

        try:
            if provider == "yfinance":
                result = _yf_download(symbol, timeframe, period)
                print(f"DATA FEED OK | {symbol} | provider=yfinance")
                return result

            if provider == "twelve_data":
                result = _twelve_data_download(symbol, timeframe, period)
                print(f"DATA FEED OK | {symbol} | provider=twelve_data")
                return result

            if provider == "alpha_vantage":
                result = _alpha_vantage_download(symbol, timeframe, period)
                print(f"DATA FEED OK | {symbol} | provider=alpha_vantage")
                return result

            if provider == "finnhub":
                result = _finnhub_download(symbol, timeframe, period)
                print(f"DATA FEED OK | {symbol} | provider=finnhub")
                return result

            errors.append(f"{provider}: provider desconocido")

        except Exception as e:
            error_text = str(e)
            errors.append(f"{provider}: {error_text}")

            print(f"DATA FEED FAIL | {symbol} | provider={provider} | error={error_text}")

            if _is_rate_limit_error(error_text):
                _provider_pause(2.0)
            else:
                _provider_pause(0.75)

            continue

    raise ValueError(
        f"No se pudo descargar {symbol} con ningún provider. Detalles: {errors}"
    )