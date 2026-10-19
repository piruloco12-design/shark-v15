import math

import pandas as pd

# Zona del mercado USA. Necesita la base de datos de zonas
# horarias (paquete tzdata) instalada. Sin ella, pandas no sabe
# convertir a "US/Eastern" y este módulo no puede clasificar nada.
# "US/Eastern" es un alias de compatibilidad; el canonico es
# "America/New_York". Son la MISMA zona (mismos husos, mismas reglas de
# horario de verano), asi que esto no cambia ninguna decision. Lo que
# cambia es que el canonico existe tambien en bases de zonas recortadas,
# donde el alias no, y ahi el filtro de sesion bloqueaba el 100% de las
# operaciones sin decir por que. Ver zona_mercado.py.
try:
    from zona_mercado import zona as _zona_mercado
    ZONA_MERCADO = _zona_mercado()
except Exception:
    ZONA_MERCADO = "US/Eastern"


def _a_float(valor, defecto=0.0):
    try:
        valor = float(valor)
    except (TypeError, ValueError):
        return defecto
    if not math.isfinite(valor):
        return defecto
    return valor


def _es_intradia(df):
    """
    ¿Son velas intradía o de un día o más?

    Se deduce del espaciado entre velas en vez de pedir el
    timeframe como parámetro, para no cambiar la firma de las
    funciones ni los sitios que las llaman.

    Hace falta porque el filtro de sesión solo tiene sentido
    intradía. Las velas diarias de yfinance llevan marca de
    medianoche, así que al convertirlas a hora de Nueva York dan
    las 00:00, el filtro las clasificaba como OFF_HOURS y
    bloqueaba el 100% de las señales. En un backtest diario de 15
    años: 2222 señales, 0 operaciones.

    Una vela diaria no está "dentro" de una sesión: ES la sesión
    entera. Preguntarle en qué parte del día está no tiene
    sentido.
    """
    if df is None or len(df) < 3:
        # Sin datos para decidir, se asume intradía: es lo
        # conservador, porque mantiene el filtro activo.
        return True

    if not isinstance(df.index, pd.DatetimeIndex):
        return True

    try:
        diferencias = pd.Series(df.index[1:]) - pd.Series(df.index[:-1])
        horas = diferencias.median().total_seconds() / 3600.0
    except Exception:
        return True

    if not math.isfinite(horas) or horas <= 0:
        return True

    # 20h de margen: 30m y 1h quedan claramente por debajo,
    # diario y semanal claramente por encima.
    return horas < 20.0


def classify_market_session(df):
    """
    Clasifica la sesión usando hora de New York.
    Funciona mejor para índices/acciones USA y CFDs relacionados.
    """
    if df.empty:
        return {
            "session": "UNKNOWN",
            "hour_et": None,
            "reason": "Sin datos"
        }

    # En diario o superior no hay sesión intradía que clasificar.
    if not _es_intradia(df):
        return {
            "session": "VELA_DIARIA",
            "hour_et": None,
            "reason": "Vela de un día o más: la vela es la sesión completa"
        }

    ts = df.index[-1]

    error_tz = None

    try:
        ts = pd.Timestamp(ts)
        if ts.tzinfo is None:
            ts = ts.tz_localize("UTC")
        ts_et = ts.tz_convert(ZONA_MERCADO)
        hour_et = ts_et.hour
    except Exception as e:
        hour_et = None
        error_tz = e

    if hour_et is None:
        # Esto hay que verlo en los logs, no tragárselo. Si falta
        # el paquete tzdata, TODAS las velas acaban aquí y el
        # filtro de sesión deja de filtrar.
        print(
            f"SESSION | ERROR convirtiendo a {ZONA_MERCADO}: {error_tz} "
            f"| ¿falta el paquete tzdata? El filtro de sesión va a bloquear "
            f"todo por seguridad hasta que se arregle."
        )
        return {
            "session": "UNKNOWN",
            "hour_et": None,
            "reason": f"No se pudo convertir zona horaria ({error_tz})"
        }

    if 9 <= hour_et < 11:
        session = "US_OPEN"
        reason = "Apertura americana, alta actividad"
    elif 11 <= hour_et < 14:
        session = "US_MIDDAY"
        reason = "Mediodía USA, menor impulso"
    elif 14 <= hour_et < 16:
        session = "US_CLOSE"
        reason = "Cierre americano, posible expansión"
    else:
        session = "OFF_HOURS"
        reason = "Fuera del núcleo horario USA"

    return {
        "session": session,
        "hour_et": hour_et,
        "reason": reason
    }


def evaluate_session_filter(df, regime):
    """
    Decide si conviene operar según sesión + régimen.
    """
    session_info = classify_market_session(df)
    session = session_info["session"]

    if df.empty:
        return {
            "allow": False,
            "session": session,
            "reason": "Sin datos"
        }

    last = df.iloc[-1]
    adx = _a_float(last.get("adx", 0))

    # En diario el filtro de sesión no aplica: no hay un "momento
    # del día" en una vela que abarca el día entero.
    if session == "VELA_DIARIA":
        return {
            "allow": True,
            "session": session,
            "reason": session_info["reason"]
        }

    # FALLA CERRADA. Antes, una sesión UNKNOWN caía hasta el
    # "allow: True" del final: si la zona horaria no se podía
    # resolver, el filtro de sesión se apagaba por completo y el
    # bot podía abrir trades con velas de las 3 de la mañana.
    # Si no sabemos en qué sesión estamos, no se opera.
    if session == "UNKNOWN":
        return {
            "allow": False,
            "session": session,
            "reason": f"Sesión indeterminada, no se opera a ciegas ({session_info.get('reason')})"
        }

    if session == "OFF_HOURS":
        return {
            "allow": False,
            "session": session,
            "reason": "Fuera de horario principal"
        }

    if session == "US_MIDDAY" and regime in ["RANGE", "UNKNOWN"]:
        return {
            "allow": False,
            "session": session,
            "reason": "Mediodía + rango = baja calidad"
        }

    if session == "US_MIDDAY" and adx < 20:
        return {
            "allow": False,
            "session": session,
            "reason": "Mediodía con poca fuerza tendencial"
        }

    return {
        "allow": True,
        "session": session,
        "reason": session_info["reason"]
    }


def evaluate_volatility_filter(df, regime):
    """
    Evalúa si la volatilidad actual es operable o no.
    Usa ATR relativo al precio y lo compara con su propio historial.
    """
    if df.empty or "atr" not in df.columns:
        return {
            "allow": False,
            "volatility_state": "UNKNOWN",
            "atr_pct": 0.0,
            "atr_ratio": 0.0,
            "reason": "ATR no disponible"
        }

    work = df.copy()

    if "Close" not in work.columns:
        return {
            "allow": False,
            "volatility_state": "UNKNOWN",
            "atr_pct": 0.0,
            "atr_ratio": 0.0,
            "reason": "Close no disponible"
        }

    work["atr_pct"] = (work["atr"] / work["Close"]) * 100.0

    current_atr_pct = float(work["atr_pct"].iloc[-1])

    rolling_base = work["atr_pct"].rolling(50).median().iloc[-1]
    if pd.isna(rolling_base) or rolling_base <= 0:
        rolling_base = current_atr_pct

    atr_ratio = current_atr_pct / rolling_base if rolling_base > 0 else 1.0

    if atr_ratio < 0.65:
        return {
            "allow": False,
            "volatility_state": "COMPRESSED",
            "atr_pct": round(current_atr_pct, 3),
            "atr_ratio": round(atr_ratio, 3),
            "reason": "Volatilidad demasiado comprimida"
        }

    if atr_ratio > 2.50 and regime in ["RANGE", "UNKNOWN"]:
        return {
            "allow": False,
            "volatility_state": "CHAOTIC",
            "atr_pct": round(current_atr_pct, 3),
            "atr_ratio": round(atr_ratio, 3),
            "reason": "Volatilidad caótica sin tendencia clara"
        }

    if atr_ratio > 1.80:
        return {
            "allow": True,
            "volatility_state": "EXPANDED",
            "atr_pct": round(current_atr_pct, 3),
            "atr_ratio": round(atr_ratio, 3),
            "reason": "Volatilidad expandida"
        }

    return {
        "allow": True,
        "volatility_state": "NORMAL",
        "atr_pct": round(current_atr_pct, 3),
        "atr_ratio": round(atr_ratio, 3),
        "reason": "Volatilidad operable"
    }