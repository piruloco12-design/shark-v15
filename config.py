import os
from dotenv import load_dotenv

load_dotenv()

# ==========================================
# SHARK V15 SNIPER CONFIG
# ==========================================

DATABASE_NAME = os.getenv("DATABASE_NAME", "shark_v8.db")

CAPITAL = 1000
RISK_PER_TRADE = 0.005

TIMEFRAME = "30m"

# yfinance limita timeframes intradía a ventanas más cortas
if TIMEFRAME in ["1m", "5m", "15m", "30m"]:
    PERIOD = "60d"
elif TIMEFRAME in ["60m", "1h"]:
    PERIOD = "730d"
else:
    PERIOD = "6mo"

LOOP_INTERVAL = 120

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

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# ==========================================
# DATA FEED
# ==========================================

PRIMARY_PROVIDER = os.getenv("PRIMARY_PROVIDER", "yfinance")

DATA_PROVIDER_ORDER = [
    "yfinance",
    "twelve_data",
    "alpha_vantage",
    "finnhub"
]

TWELVE_DATA_API_KEY = os.getenv("TWELVE_DATA_API_KEY", "")
ALPHA_VANTAGE_API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY", "")
FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY", "")

REQUEST_TIMEOUT = 15

# ==========================================
# RISK CONTROL
# ==========================================

MAX_OPEN_TRADES = 2
MAX_DAILY_LOSS_PCT = 0.015
MAX_DRAWDOWN_PCT = 0.10
COOLDOWN_HOURS_PER_ASSET = 6
BLOCK_DUPLICATE_SIGNALS = True

# ==========================================
# SETUP WATCH
# ==========================================

SETUP_ALERTS_ENABLED = True
SETUP_ALERT_COOLDOWN_MINUTES = 180

# ==========================================
# SNIPER FILTERS
# ==========================================

SNIPER_MODE = True
SNIPER_ALLOWED_REGIMES = ["BULL_TREND", "BEAR_TREND", "TREND"]
SNIPER_MIN_ADX = 24
SNIPER_MIN_AI_SCORE = 60
SNIPER_MIN_CONTEXT_SCORE = 58
SNIPER_MIN_FINAL_SCORE = 60

# ==========================================
# DASHBOARD
# ==========================================

PORT = int(os.getenv("PORT", "8501"))