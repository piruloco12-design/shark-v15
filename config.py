import os
from dotenv import load_dotenv

load_dotenv()


def _env(nombre, defecto):
    """
    Lee una variable de entorno tratando el valor vacío como
    "no definida".

    os.getenv("X", defecto) devuelve "" cuando la variable existe
    pero está vacía, no el valor por defecto. Eso rompió el bot en
    CI: GitHub Actions pasa "" a las entradas no rellenadas, ASSETS
    quedó en lista vacía y el backtest abortó sin activos.
    """
    valor = os.getenv(nombre)
    if valor is None or not valor.strip():
        return defecto
    return valor.strip()

# ==========================================
# SHARK V15 SNIPER — yfinance
# ==========================================

APP_NAME = "SHARK V15 SNIPER"
APP_ENV = os.getenv("APP_ENV", "production").strip().lower()

# ==========================================
# DATABASE
# ==========================================

DATABASE_NAME = _env("DATABASE_NAME", "shark_v8.db")

# ==========================================
# CAPITAL / RISK
# ==========================================

CAPITAL = float(os.getenv("CAPITAL", "1000"))
RISK_PER_TRADE = float(os.getenv("RISK_PER_TRADE", "0.005"))

MAX_OPEN_TRADES = int(os.getenv("MAX_OPEN_TRADES", "2"))

# Múltiplos de ATR para stop y objetivo. Estaban fijos dentro de
# risk_management.py; aquí se pueden barrer para comprobar si el
# resultado es un pico (sobreajuste) o una meseta (quizá real).
SL_ATR_MULT = float(os.getenv("SL_ATR_MULT", "2.0"))
TP_ATR_MULT = float(os.getenv("TP_ATR_MULT", "2.5"))
MAX_DAILY_LOSS_PCT = float(os.getenv("MAX_DAILY_LOSS_PCT", "0.015"))
MAX_DRAWDOWN_PCT = float(os.getenv("MAX_DRAWDOWN_PCT", "0.10"))
COOLDOWN_HOURS_PER_ASSET = int(os.getenv("COOLDOWN_HOURS_PER_ASSET", "6"))
BLOCK_DUPLICATE_SIGNALS = os.getenv("BLOCK_DUPLICATE_SIGNALS", "true").strip().lower() == "true"

# ==========================================
# MARKET DATA
# ==========================================

TIMEFRAME = _env("TIMEFRAME", "30m")

# Histórico por defecto según el timeframe. Son los topes de
# yfinance, no decisiones nuestras:
#   intradía por debajo de 1h -> 60 días como máximo
#   1h                        -> 730 días
#   diario                    -> años (sin tope práctico)
if TIMEFRAME in ["1m", "5m", "15m", "30m"]:
    _PERIOD_DEFECTO = "60d"
elif TIMEFRAME in ["60m", "1h"]:
    _PERIOD_DEFECTO = "730d"
else:
    _PERIOD_DEFECTO = "15y"

# Se puede forzar por entorno para validar sobre histórico largo
# sin tocar código:  TIMEFRAME=1d PERIOD=15y
PERIOD = _env("PERIOD", _PERIOD_DEFECTO)

LOOP_INTERVAL = int(os.getenv("LOOP_INTERVAL", "300"))
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "15"))

# ==========================================
# ACTIVOS CORE
# ==========================================

_ASSETS_DEFECTO = "IWM,NVDA,AMZN,META"

# Configurable por entorno para poder validar sobre una cesta
# distinta sin tocar código:  ASSETS=SPY,QQQ,AAPL,MSFT
ASSETS = [
    a.strip().upper()
    for a in _env("ASSETS", _ASSETS_DEFECTO).split(",")
    if a.strip()
]

# ==========================================
# TELEGRAM / AI
# ==========================================

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "").strip()
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()

# ==========================================
# DATA PROVIDERS
#
# yfinance es el primario. La suscripción de Polygon está
# cancelada, así que polygon queda FUERA de la cascada:
# dejarlo dentro gastaba una llamada HTTP fallida por cada
# activo y cada ciclo antes de caer al siguiente provider.
#
# El código de Polygon sigue intacto en data_feed.py. Para
# reactivarlo basta una variable de entorno en Render:
#     DATA_PROVIDER_ORDER=polygon,yfinance
#
# Límite de yfinance intradía: 60 días de histórico. Es de la
# fuente, no del bot.
# ==========================================

PRIMARY_PROVIDER = _env("PRIMARY_PROVIDER", "yfinance").lower()

# stooq va detras de yfinance: gratis, sin clave, independiente
# de Yahoo. Es el seguro contra que Yahoo vuelva a cambiar la
# web y rompa yfinance, como paso en febrero de 2025.
_ORDEN_PROVIDERS_DEFECTO = "yfinance,stooq,finnhub,alpha_vantage,twelve_data"

DATA_PROVIDER_ORDER = [
    p.strip().lower()
    for p in _env("DATA_PROVIDER_ORDER", _ORDEN_PROVIDERS_DEFECTO).split(",")
    if p.strip()
]

# ==========================================
# MÍNIMO DE VELAS
#
# ema200 necesita 200 velas. Con menos, el indicador sale NaN,
# todas las comparaciones de signals.py dan False y el bot NUNCA
# señaliza — sin error, sin aviso, sin nada. 220 deja margen.
# ==========================================

MIN_BARS = int(_env("MIN_BARS", "220"))

POLYGON_API_KEY = os.getenv("POLYGON_API_KEY", "").strip()
POLYGON_BASE_URL = os.getenv("POLYGON_BASE_URL", "https://api.polygon.io").strip().rstrip("/")

TWELVE_DATA_API_KEY = os.getenv("TWELVE_DATA_API_KEY", "").strip()
ALPHA_VANTAGE_API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY", "").strip()
FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY", "").strip()

# ==========================================
# FILTRO DE NOTICIAS (Gemini)
#
# Arranca APAGADO y, cuando se enciende, en modo sombra: opina en
# cada operacion y lo registra, pero no bloquea.
#
# No se puede backtestear: Gemini sabe lo que paso despues de
# cualquier fecha historica, asi que preguntarle por 2019 filtra
# el futuro. La unica validacion honesta es hacia delante, con
# validator/medir_filtro_noticias.py, comparando como acabaron
# las operaciones que aprobo frente a las que habria vetado.
#
# No pasar a modo bloqueo sin ese numero.
# ==========================================

GEMINI_FILTER_ENABLED = _env("GEMINI_FILTER_ENABLED", "false").lower() == "true"
GEMINI_FILTER_MODO = _env("GEMINI_FILTER_MODO", "sombra").lower()
GEMINI_MODELO = _env("GEMINI_MODELO", "gemini-2.0-flash")

# ==========================================
# TELEGRAM: evitar el aviso duplicado
#
# Al abrir una operacion se mandaban DOS mensajes: la ficha movil
# completa (con RSI, ADX, regimen y motivo) y el aviso corto del
# broker. El corto no aporta nada que no este en la ficha.
# ==========================================

MENSAJE_BROKER_AL_ABRIR = _env("MENSAJE_BROKER_AL_ABRIR", "false").lower() == "true"

# ==========================================
# SETUP WATCH
# ==========================================

SETUP_ALERTS_ENABLED = os.getenv("SETUP_ALERTS_ENABLED", "true").strip().lower() == "true"
SETUP_ALERT_COOLDOWN_MINUTES = int(os.getenv("SETUP_ALERT_COOLDOWN_MINUTES", "180"))

# ==========================================
# TELEGRAM ANTI-SPAM
# ==========================================

SIGNAL_ALERT_COOLDOWN_MINUTES = int(os.getenv("SIGNAL_ALERT_COOLDOWN_MINUTES", "90"))
ERROR_ALERT_COOLDOWN_MINUTES = int(os.getenv("ERROR_ALERT_COOLDOWN_MINUTES", "30"))
STARTUP_MESSAGE_ENABLED = os.getenv("STARTUP_MESSAGE_ENABLED", "true").strip().lower() == "true"

# ==========================================
# SNIPER FILTERS
# ==========================================

SNIPER_MODE = os.getenv("SNIPER_MODE", "true").strip().lower() == "true"

SNIPER_ALLOWED_REGIMES = [
    "BULL_TREND",
    "BEAR_TREND",
    "TREND",
]

# Volvemos a la calibración simple
SNIPER_MIN_ADX = float(os.getenv("SNIPER_MIN_ADX", "22"))
SNIPER_MIN_AI_SCORE = float(os.getenv("SNIPER_MIN_AI_SCORE", "50"))
SNIPER_MIN_CONTEXT_SCORE = float(os.getenv("SNIPER_MIN_CONTEXT_SCORE", "55"))
SNIPER_MIN_FINAL_SCORE = float(os.getenv("SNIPER_MIN_FINAL_SCORE", "55"))

# ==========================================
# NORMAL MODE FILTERS
# ==========================================

NORMAL_MIN_FINAL_SCORE = float(os.getenv("NORMAL_MIN_FINAL_SCORE", "58"))

# ==========================================
# DASHBOARD / SERVER
# ==========================================

PORT = int(os.getenv("PORT", "8501"))

# ==========================================
# DEBUG / AUDIT
# ==========================================

DEBUG_MODE = os.getenv("DEBUG_MODE", "false").strip().lower() == "true"
VERBOSE_LOGS = os.getenv("VERBOSE_LOGS", "true").strip().lower() == "true"
SAVE_ALL_SIGNALS = os.getenv("SAVE_ALL_SIGNALS", "true").strip().lower() == "true"

# ==========================================
# VALIDACIÓN BÁSICA
# ==========================================

if CAPITAL <= 0:
    raise ValueError("CAPITAL debe ser mayor que 0")

if RISK_PER_TRADE <= 0 or RISK_PER_TRADE > 0.05:
    raise ValueError("RISK_PER_TRADE debe estar entre 0 y 0.05")

if LOOP_INTERVAL < 30:
    raise ValueError("LOOP_INTERVAL no puede ser menor a 30 segundos")

if REQUEST_TIMEOUT < 5:
    raise ValueError("REQUEST_TIMEOUT no puede ser menor a 5 segundos")

if MAX_OPEN_TRADES < 1:
    raise ValueError("MAX_OPEN_TRADES debe ser al menos 1")

if MIN_BARS < 220:
    raise ValueError(
        "MIN_BARS no puede ser menor a 220: ema200 necesita 200 velas "
        "y por debajo de eso el bot deja de señalizar en silencio"
    )

_PROVIDERS_VALIDOS = {
    "polygon", "yfinance", "stooq", "coinbase",
    "finnhub", "alpha_vantage", "twelve_data",
}

_desconocidos = [p for p in DATA_PROVIDER_ORDER if p not in _PROVIDERS_VALIDOS]
if _desconocidos:
    raise ValueError(
        f"DATA_PROVIDER_ORDER contiene providers desconocidos: {_desconocidos}. "
        f"Válidos: {sorted(_PROVIDERS_VALIDOS)}"
    )

if not DATA_PROVIDER_ORDER:
    raise ValueError("DATA_PROVIDER_ORDER no puede estar vacío")

if GEMINI_FILTER_MODO not in ("sombra", "bloqueo"):
    raise ValueError(
        f"GEMINI_FILTER_MODO debe ser 'sombra' o 'bloqueo', no {GEMINI_FILTER_MODO!r}"
    )

if not ASSETS:
    raise ValueError(
        "ASSETS está vacío: el bot no tiene nada que vigilar. "
        "Revisa la variable de entorno ASSETS"
    )

if SL_ATR_MULT <= 0 or TP_ATR_MULT <= 0:
    raise ValueError("SL_ATR_MULT y TP_ATR_MULT deben ser mayores que 0")