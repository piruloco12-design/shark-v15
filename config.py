import os
from dotenv import load_dotenv

load_dotenv()

# ==========================================
# SHARK V15 SNIPER — yfinance
# ==========================================

APP_NAME = "SHARK V15 SNIPER"
APP_ENV = os.getenv("APP_ENV", "production").strip().lower()

# ==========================================
# DATABASE
# ==========================================

DATABASE_NAME = os.getenv("DATABASE_NAME", "shark_v8.db")

# ==========================================
# CAPITAL / RISK
# ==========================================

CAPITAL = float(os.getenv("CAPITAL", "1000"))
RISK_PER_TRADE = float(os.getenv("RISK_PER_TRADE", "0.005"))

MAX_OPEN_TRADES = int(os.getenv("MAX_OPEN_TRADES", "2"))
MAX_DAILY_LOSS_PCT = float(os.getenv("MAX_DAILY_LOSS_PCT", "0.015"))
MAX_DRAWDOWN_PCT = float(os.getenv("MAX_DRAWDOWN_PCT", "0.10"))
COOLDOWN_HOURS_PER_ASSET = int(os.getenv("COOLDOWN_HOURS_PER_ASSET", "6"))
BLOCK_DUPLICATE_SIGNALS = os.getenv("BLOCK_DUPLICATE_SIGNALS", "true").strip().lower() == "true"

# ==========================================
# MARKET DATA
# ==========================================

TIMEFRAME = os.getenv("TIMEFRAME", "30m").strip()

if TIMEFRAME in ["1m", "5m", "15m", "30m"]:
    PERIOD = "60d"
elif TIMEFRAME in ["60m", "1h"]:
    PERIOD = "730d"
else:
    PERIOD = "6mo"

LOOP_INTERVAL = int(os.getenv("LOOP_INTERVAL", "300"))
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "15"))

# ==========================================
# ACTIVOS CORE
# ==========================================

ASSETS = [
    "IWM",
    "NVDA",
    "AMZN",
    "META",
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

PRIMARY_PROVIDER = os.getenv("PRIMARY_PROVIDER", "yfinance").strip().lower()

_ORDEN_PROVIDERS_DEFECTO = "yfinance,finnhub,alpha_vantage,twelve_data"

DATA_PROVIDER_ORDER = [
    p.strip().lower()
    for p in os.getenv("DATA_PROVIDER_ORDER", _ORDEN_PROVIDERS_DEFECTO).split(",")
    if p.strip()
]

# ==========================================
# MÍNIMO DE VELAS
#
# ema200 necesita 200 velas. Con menos, el indicador sale NaN,
# todas las comparaciones de signals.py dan False y el bot NUNCA
# señaliza — sin error, sin aviso, sin nada. 220 deja margen.
# ==========================================

MIN_BARS = int(os.getenv("MIN_BARS", "220"))

POLYGON_API_KEY = os.getenv("POLYGON_API_KEY", "").strip()
POLYGON_BASE_URL = os.getenv("POLYGON_BASE_URL", "https://api.polygon.io").strip().rstrip("/")

TWELVE_DATA_API_KEY = os.getenv("TWELVE_DATA_API_KEY", "").strip()
ALPHA_VANTAGE_API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY", "").strip()
FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY", "").strip()

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

_PROVIDERS_VALIDOS = {"polygon", "yfinance", "finnhub", "alpha_vantage", "twelve_data"}

_desconocidos = [p for p in DATA_PROVIDER_ORDER if p not in _PROVIDERS_VALIDOS]
if _desconocidos:
    raise ValueError(
        f"DATA_PROVIDER_ORDER contiene providers desconocidos: {_desconocidos}. "
        f"Válidos: {sorted(_PROVIDERS_VALIDOS)}"
    )

if not DATA_PROVIDER_ORDER:
    raise ValueError("DATA_PROVIDER_ORDER no puede estar vacío")