from config import V16_ALLOWED_ASSETS


def evaluate_asset_guard(ticker):
    symbol = str(ticker).strip().upper()

    if symbol not in V16_ALLOWED_ASSETS:
        return {
            "allow": False,
            "reason": f"Activo fuera del universo V16: {symbol}"
        }

    return {
        "allow": True,
        "reason": "Activo permitido en V16"
    }