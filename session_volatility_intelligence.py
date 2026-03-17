import pandas as pd


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

    ts = df.index[-1]

    try:
        ts = pd.Timestamp(ts)
        if ts.tzinfo is None:
            ts = ts.tz_localize("UTC")
        ts_et = ts.tz_convert("US/Eastern")
        hour_et = ts_et.hour
    except Exception:
        hour_et = None

    if hour_et is None:
        return {
            "session": "UNKNOWN",
            "hour_et": None,
            "reason": "No se pudo convertir zona horaria"
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
    adx = float(last.get("adx", 0))

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