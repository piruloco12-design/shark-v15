ASSET_METADATA = {
    "SPY": {
        "name": "SPDR S&P 500 ETF",
        "quote_currency": "USD"
    },
    "QQQ": {
        "name": "Invesco QQQ ETF",
        "quote_currency": "USD"
    },
    "DIA": {
        "name": "SPDR Dow Jones Industrial Average ETF",
        "quote_currency": "USD"
    },
    "IWM": {
        "name": "iShares Russell 2000 ETF",
        "quote_currency": "USD"
    },
    "AAPL": {
        "name": "Apple",
        "quote_currency": "USD"
    },
    "MSFT": {
        "name": "Microsoft",
        "quote_currency": "USD"
    },
    "NVDA": {
        "name": "NVIDIA",
        "quote_currency": "USD"
    },
    "AMD": {
        "name": "AMD",
        "quote_currency": "USD"
    },
    "META": {
        "name": "Meta",
        "quote_currency": "USD"
    },
    "GOOGL": {
        "name": "Alphabet",
        "quote_currency": "USD"
    },
    "AMZN": {
        "name": "Amazon",
        "quote_currency": "USD"
    },
    "TSLA": {
        "name": "Tesla",
        "quote_currency": "USD"
    },
    "NFLX": {
        "name": "Netflix",
        "quote_currency": "USD"
    },
    "BABA": {
        "name": "Alibaba",
        "quote_currency": "USD"
    },
    "INTC": {
        "name": "Intel",
        "quote_currency": "USD"
    },
    "CRM": {
        "name": "Salesforce",
        "quote_currency": "USD"
    },
    "GC=F": {
        "name": "Oro",
        "quote_currency": "USD"
    },
    "CL=F": {
        "name": "Petróleo WTI",
        "quote_currency": "USD"
    },

    # plantilla futura para instrumentos no USD
    "JPN225": {
        "name": "Japón 225",
        "quote_currency": "EUR"
    },
    "DE40": {
        "name": "Alemania 40",
        "quote_currency": "EUR"
    },
    "UK100": {
        "name": "Reino Unido 100",
        "quote_currency": "GBP"
    }
}


def get_asset_label(ticker):
    return ASSET_METADATA.get(ticker, {}).get("name", ticker)


def get_asset_label_with_ticker(ticker):
    label = get_asset_label(ticker)
    if label == ticker:
        return ticker
    return f"{label} ({ticker})"


def get_asset_quote_currency(ticker):
    return ASSET_METADATA.get(ticker, {}).get("quote_currency", "USD")