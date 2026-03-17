import os
from dotenv import load_dotenv

load_dotenv()

# ==========================================
# SHARK V15 SNIPER CONFIG
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
    "SPY",
    "QQQ",
    "DIA",
    "IWM",
    "MSFT",
    "NVDA",
    "AMZN",
    "META",
    "TSLA",
]

# ==========================================
# TELEGRAM / AI
# ==========================================

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "").strip()
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()

# ==========================================
# DATA PROVIDERS
# ==========================================

PRIMARY_PROVIDER = os.getenv("PRIMARY_PROVIDER", "twelve_data").strip().lower()

DATA_PROVIDER_ORDER = [
    "twelve_data",
    "yfinance",
    "finnhub",
    "alpha_vantage"
]

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
# SNIPER FILTERS (MODO AUDITORÍA CONTROLADA)
# ==========================================

SNIPER_MODE = os.getenv("SNIPER_MODE", "true").strip().lower() == "true"

SNIPER_ALLOWED_REGIMES = [
    "BULL_TREND",
    "BEAR_TREND",
    "TREND",
    "RANGE"
]

SNIPER_MIN_ADX = float(os.getenv("SNIPER_MIN_ADX", "18"))
SNIPER_MIN_AI_SCORE = float(os.getenv("SNIPER_MIN_AI_SCORE", "50"))
SNIPER_MIN_CONTEXT_SCORE = float(os.getenv("SNIPER_MIN_CONTEXT_SCORE", "50"))
SNIPER_MIN_FINAL_SCORE = float(os.getenv("SNIPER_MIN_FINAL_SCORE", "50"))

# ==========================================
# NORMAL MODE FILTERS
# ==========================================

NORMAL_MIN_FINAL_SCORE = float(os.getenv("NORMAL_MIN_FINAL_SCORE", "50"))

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