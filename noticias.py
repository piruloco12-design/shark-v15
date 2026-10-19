"""
Lector de noticias recientes por activo.

FUENTES

Finnhub como principal (la clave ya esta en el .env) y Alpha
Vantage como alternativa. Las dos tienen plan gratuito suficiente
para unos pocos activos cada 5 minutos.

Si no hay ninguna clave configurada, devuelve lista vacia sin
romper nada: el bot sigue operando igual, solo que sin contexto
de noticias.

QUE DEVUELVE

Una lista de titulares recientes, del mas nuevo al mas viejo, con
fecha y fuente. Nada mas: ni sentimiento, ni puntuacion, ni
interpretacion. Interpretar es trabajo del filtro de Gemini, y
conviene que esten separados para poder cambiar uno sin tocar el
otro.
"""

import time
from datetime import datetime, timedelta, timezone

import requests

from config import (
    REQUEST_TIMEOUT,
    FINNHUB_API_KEY,
    ALPHA_VANTAGE_API_KEY,
)

# Cache en memoria: el bot gira cada 5 minutos pero las noticias
# no cambian tan rapido, y las dos APIs tienen limite de llamadas.
_CACHE = {}
CACHE_SEGUNDOS = 900   # 15 minutos

MAX_TITULARES = 8
HORAS_ATRAS = 48


def _ahora():
    return datetime.now(timezone.utc)


def _limpiar(texto, maximo=200):
    if not texto:
        return ""
    texto = " ".join(str(texto).split())
    return texto[:maximo]


def _desde_finnhub(ticker):
    if not FINNHUB_API_KEY:
        raise ValueError("FINNHUB_API_KEY no configurada")

    hasta = _ahora()
    desde = hasta - timedelta(days=7)

    respuesta = requests.get(
        "https://finnhub.io/api/v1/company-news",
        params={
            "symbol": ticker.upper(),
            "from": desde.date().isoformat(),
            "to": hasta.date().isoformat(),
            "token": FINNHUB_API_KEY,
        },
        timeout=REQUEST_TIMEOUT,
    )
    respuesta.raise_for_status()
    datos = respuesta.json()

    if not isinstance(datos, list):
        raise ValueError(f"Finnhub devolvio algo inesperado: {str(datos)[:100]}")

    corte = hasta - timedelta(hours=HORAS_ATRAS)
    titulares = []

    for item in datos:
        try:
            cuando = datetime.fromtimestamp(int(item.get("datetime", 0)),
                                            tz=timezone.utc)
        except (TypeError, ValueError, OSError):
            continue

        if cuando < corte:
            continue

        titular = _limpiar(item.get("headline"))
        if not titular:
            continue

        titulares.append({
            "titular": titular,
            "resumen": _limpiar(item.get("summary"), 300),
            "fuente": _limpiar(item.get("source"), 40),
            "cuando": cuando.isoformat(),
            "horas": round((hasta - cuando).total_seconds() / 3600, 1),
        })

    titulares.sort(key=lambda t: t["cuando"], reverse=True)
    return titulares[:MAX_TITULARES], "finnhub"


def _desde_alpha_vantage(ticker):
    if not ALPHA_VANTAGE_API_KEY:
        raise ValueError("ALPHA_VANTAGE_API_KEY no configurada")

    respuesta = requests.get(
        "https://www.alphavantage.co/query",
        params={
            "function": "NEWS_SENTIMENT",
            "tickers": ticker.upper(),
            "limit": 50,
            "apikey": ALPHA_VANTAGE_API_KEY,
        },
        timeout=REQUEST_TIMEOUT,
    )
    respuesta.raise_for_status()
    datos = respuesta.json()

    if "feed" not in datos:
        raise ValueError(f"Alpha Vantage sin feed: {str(datos)[:120]}")

    hasta = _ahora()
    corte = hasta - timedelta(hours=HORAS_ATRAS)
    titulares = []

    for item in datos["feed"]:
        try:
            # Formato de Alpha Vantage: 20260115T143000
            cuando = datetime.strptime(
                item.get("time_published", ""), "%Y%m%dT%H%M%S"
            ).replace(tzinfo=timezone.utc)
        except (TypeError, ValueError):
            continue

        if cuando < corte:
            continue

        titular = _limpiar(item.get("title"))
        if not titular:
            continue

        titulares.append({
            "titular": titular,
            "resumen": _limpiar(item.get("summary"), 300),
            "fuente": _limpiar(item.get("source"), 40),
            "cuando": cuando.isoformat(),
            "horas": round((hasta - cuando).total_seconds() / 3600, 1),
        })

    titulares.sort(key=lambda t: t["cuando"], reverse=True)
    return titulares[:MAX_TITULARES], "alpha_vantage"


def obtener_noticias(ticker, usar_cache=True):
    """
    Titulares recientes del activo. Nunca lanza excepcion: si
    ninguna fuente responde, devuelve lista vacia y el motivo.

    Devuelve (titulares, fuente, error).
    """
    clave = ticker.upper()

    if usar_cache and clave in _CACHE:
        guardado, cuando = _CACHE[clave]
        if time.time() - cuando < CACHE_SEGUNDOS:
            return guardado

    errores = []
    for lector in (_desde_finnhub, _desde_alpha_vantage):
        try:
            titulares, fuente = lector(clave)
            resultado = (titulares, fuente, None)
            _CACHE[clave] = (resultado, time.time())
            return resultado
        except Exception as e:
            errores.append(f"{lector.__name__}: {type(e).__name__}: {str(e)[:80]}")

    resultado = ([], None, " | ".join(errores))
    # Se cachea tambien el fallo, para no machacar las APIs caidas
    # en cada ciclo de 5 minutos.
    _CACHE[clave] = (resultado, time.time())
    return resultado


def formatear_para_prompt(titulares):
    """Titulares en texto plano, para meterlos en el prompt."""
    if not titulares:
        return "(sin noticias recientes)"

    lineas = []
    for t in titulares:
        edad = f"hace {t['horas']:.0f}h" if t["horas"] >= 1 else "hace <1h"
        lineas.append(f"- [{edad}, {t['fuente']}] {t['titular']}")
    return "\n".join(lineas)


if __name__ == "__main__":
    import sys
    simbolo = sys.argv[1] if len(sys.argv) > 1 else "NVDA"
    titulares, fuente, error = obtener_noticias(simbolo)
    print(f"{simbolo}: {len(titulares)} titulares | fuente: {fuente}")
    if error:
        print(f"error: {error}")
    print(formatear_para_prompt(titulares))
