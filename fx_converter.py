import yfinance as yf


def _get_fx_rate(symbol):
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period="2d", interval="1d")

        if df.empty:
            return None

        rate = float(df["Close"].iloc[-1])

        if rate <= 0:
            return None

        return rate

    except Exception:
        return None


def usd_to_eur(price):
    rate = _get_fx_rate("EURUSD=X")
    if rate is None:
        return None
    return round(float(price) / rate, 2)


def usd_to_gbp(price):
    rate = _get_fx_rate("GBPUSD=X")
    if rate is None:
        return None
    return round(float(price) / rate, 2)


def eur_to_usd(price):
    rate = _get_fx_rate("EURUSD=X")
    if rate is None:
        return None
    return round(float(price) * rate, 2)


def gbp_to_usd(price):
    rate = _get_fx_rate("GBPUSD=X")
    if rate is None:
        return None
    return round(float(price) * rate, 2)


def convert_from_usd(price_usd, target_currency):
    target_currency = str(target_currency).upper()

    if target_currency == "USD":
        return round(float(price_usd), 2)

    if target_currency == "EUR":
        return usd_to_eur(price_usd)

    if target_currency == "GBP":
        return usd_to_gbp(price_usd)

    return None


def format_price_for_asset(price_usd, ticker, quote_currency_getter):
    """
    Convierte desde USD a la moneda configurada del instrumento.
    """
    quote_ccy = quote_currency_getter(ticker)

    converted = convert_from_usd(price_usd, quote_ccy)

    if converted is None:
        return f"{float(price_usd):.2f} USD"

    if quote_ccy == "USD":
        return f"{converted:.2f} USD"

    return f"{converted:.2f} {quote_ccy} aprox"