import requests
from config import TELEGRAM_TOKEN, TELEGRAM_CHAT_ID
from asset_labels import get_asset_label_with_ticker, get_asset_quote_currency
from fx_converter import format_price_for_asset


def send_telegram_message(message):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("Telegram no configurado.")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"

    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message
    }

    try:
        response = requests.post(url, data=payload)

        if response.status_code != 200:
            print("Error enviando mensaje Telegram:", response.text)

    except Exception as e:
        print("Error Telegram:", e)


def _signal_strength(ai_result, context_result, adx, final_decision):
    ai_score = float(ai_result.get("score", 50))
    context_score = float(context_result.get("final_score", 50)) if context_result else 50.0
    adx = float(adx)

    score = (ai_score * 0.4) + (context_score * 0.35) + (min(adx, 40) / 40.0 * 25.0)

    if final_decision == "BLOCK":
        return "BAJA"

    if score >= 70:
        return "ALTA"

    if score >= 55:
        return "MEDIA"

    return "BAJA"


def format_setup_watch_message(ticker, last_row, setup_info, regime):
    asset_name = get_asset_label_with_ticker(ticker)

    close_price = float(last_row["Close"])
    rsi = float(last_row["rsi"])
    adx = float(last_row["adx"])
    macd = float(last_row["macd"])
    macd_signal = float(last_row["macd_signal"])

    direction = "BUY" if setup_info["alert_type"] == "WATCH_BUY" else "SELL"

    return f"""
⚠️ SETUP EN FORMACIÓN

Activo: {asset_name}
Posible dirección: {direction}
Precio actual: {format_price_for_asset(close_price, ticker, get_asset_quote_currency)}

RSI: {rsi:.2f}
ADX: {adx:.2f}
MACD: {macd:.2f}
MACD Signal: {macd_signal:.2f}
Regime: {regime}

Motivo:
{setup_info['reason']}
"""


def format_pro_signal_message(
    ticker,
    signal,
    trade_setup,
    last_row,
    ai_result,
    risk_result,
    regime,
    technical_reason,
    session_result,
    volatility_result,
    context_result=None
):
    asset_name = get_asset_label_with_ticker(ticker)

    entry = float(trade_setup["entry"])
    sl = float(trade_setup["stop_loss"])
    tp = float(trade_setup["take_profit"])
    size = float(trade_setup["position_size"])

    close_price = float(last_row["Close"])
    rsi = float(last_row["rsi"])
    adx = float(last_row["adx"])
    atr = float(last_row["atr"])

    asset_score = float(trade_setup.get("asset_score", 0.0))
    scale_factor = float(trade_setup.get("scale_factor", 1.0))
    capital_factor = float(trade_setup.get("capital_allocation_factor", 1.0))

    final_decision = "ALLOW" if risk_result["allow"] else "BLOCK"
    strength = _signal_strength(ai_result, context_result, adx, final_decision)

    context_score = float(context_result["final_score"]) if context_result else 50.0
    context_decision = context_result["decision"] if context_result else "NEUTRAL"

    operable_ahora = (
        risk_result["allow"]
        and session_result["allow"]
        and volatility_result["allow"]
        and ai_result["decision"] != "BLOCK"
        and context_decision != "BLOCK"
    )

    operable_text = "SÍ" if operable_ahora else "NO"

    quote_ccy = get_asset_quote_currency(ticker)

    msg = f"""
📱 SHARK EJECUCIÓN MÓVIL

Activo: {asset_name}
Dirección: {signal}
Operable ahora: {operable_text}
Fuerza: {strength}
Moneda esperada: {quote_ccy}

Precio actual: {format_price_for_asset(close_price, ticker, get_asset_quote_currency)}
Entry: {format_price_for_asset(entry, ticker, get_asset_quote_currency)}
Stop: {format_price_for_asset(sl, ticker, get_asset_quote_currency)}
Take Profit: {format_price_for_asset(tp, ticker, get_asset_quote_currency)}

R:R: {trade_setup['rr_ratio']:.2f}
Riesgo estimado: {trade_setup.get('allocated_risk_amount', trade_setup.get('scaled_risk_amount', trade_setup['risk_amount'])):.2f} €
Size: {size:.4f}

RSI: {rsi:.2f}
ADX: {adx:.2f}
ATR: {atr:.2f}
Regime: {regime}
Session: {session_result['session']}
Volatilidad: {volatility_result['volatility_state']}

AI: {ai_result['decision']} ({ai_result['score']})
Contexto: {context_decision} ({context_score})
Risk: {"ALLOW" if risk_result["allow"] else "BLOCK"}

Asset Score: {asset_score:.2f}
Scale: {scale_factor:.2f}
Capital Alloc: {capital_factor:.2f}

Motivo:
{technical_reason}
"""
    return msg


def format_open_trade_message(ticker, signal, trade_setup, capital):
    asset_name = get_asset_label_with_ticker(ticker)

    return f"""
📈 SHARK TRADE ABIERTO

Activo: {asset_name}
Dirección: {signal}

Entry: {format_price_for_asset(float(trade_setup['entry']), ticker, get_asset_quote_currency)}
Stop: {format_price_for_asset(float(trade_setup['stop_loss']), ticker, get_asset_quote_currency)}
TP: {format_price_for_asset(float(trade_setup['take_profit']), ticker, get_asset_quote_currency)}

Size: {trade_setup['position_size']:.4f}
R:R: {trade_setup['rr_ratio']:.2f}
Capital actual: {capital:.2f} €
"""


def format_close_trade_message(ticker, signal, exit_price, pnl, capital):
    asset_name = get_asset_label_with_ticker(ticker)

    return f"""
📉 SHARK TRADE CERRADO

Activo: {asset_name}
Dirección: {signal}

Exit: {format_price_for_asset(float(exit_price), ticker, get_asset_quote_currency)}
PnL: {pnl:.2f}
Capital actual: {capital:.2f} €
"""