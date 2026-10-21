"""
Arnes de pruebas de los arreglos aplicados a SHARK V15.

No usa yfinance ni ta (no instalables en este entorno): construye
las velas e indicadores a mano con pandas para poder ejercitar los
caminos de codigo que se han cambiado.
"""
import os
import sys
import tempfile
import types

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

# Base de datos temporal: no tocar ninguna real.
_tmpdb = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_tmpdb.close()
os.environ["DATABASE_NAME"] = _tmpdb.name
os.environ["TELEGRAM_TOKEN"] = ""
os.environ["TELEGRAM_CHAT_ID"] = ""

# data_feed importa yfinance a nivel de modulo y aqui no existe.
# Lo stubeamos para poder probar _recortar_a_rth y _normalize_df.
_stub_yf = types.ModuleType("yfinance")
_stub_yf.download = lambda *a, **k: None
sys.modules.setdefault("yfinance", _stub_yf)

from datetime import timedelta, timezone as _tzinfo

import pandas as pd
import numpy as np

# Este sandbox no tiene el paquete tzdata, asi que "US/Eastern" no
# existe. Usamos un offset fijo -05:00 (EST) para poder ejercitar la
# logica de recorte. Esto prueba el recorte, NO el cambio de horario
# de verano: eso hay que verificarlo donde tzdata este instalado.
TZ_EST = _tzinfo(timedelta(hours=-5))
HAY_TZDATA = True
try:
    pd.Timestamp("2026-01-01", tz="UTC").tz_convert("US/Eastern")
except Exception:
    HAY_TZDATA = False

import config
import data_feed
import storage
import paper_broker
from risk_management import calculate_trade_levels

OK = 0
FALLOS = []


def check(nombre, condicion, detalle=""):
    global OK
    if condicion:
        OK += 1
        print(f"  PASA   {nombre}")
    else:
        FALLOS.append(f"{nombre} {detalle}")
        print(f"  FALLA  {nombre}  {detalle}")


def velas(n=300, precio=100.0, atr=1.0):
    """DataFrame sintetico con las columnas que espera el bot."""
    idx = pd.date_range("2026-01-02 09:30", periods=n, freq="30min", tz=TZ_EST)
    df = pd.DataFrame({
        "Open": precio, "High": precio + atr, "Low": precio - atr,
        "Close": precio, "Volume": 1000.0, "atr": atr,
        "rsi": 55.0, "adx": 25.0, "ema200": precio - 1,
        "macd": 0.5, "macd_signal": 0.2,
    }, index=idx)
    return df


print("\n=== 1) risk_management: NaN y casos degenerados ===")

s = calculate_trade_levels(velas(), "BUY", 1000, 0.005)
check("BUY normal da setup valido", s["stop_loss"] < s["entry"] < s["take_profit"],
      f"-> {s['stop_loss']:.2f} / {s['entry']:.2f} / {s['take_profit']:.2f}")
check("BUY size correcto", abs(s["position_size"] - (5.0 / 2.0)) < 1e-9,
      f"-> {s['position_size']}")
check("BUY R:R = 1.25", abs(s["rr_ratio"] - 1.25) < 1e-9, f"-> {s['rr_ratio']}")

s = calculate_trade_levels(velas(), "SELL", 1000, 0.005)
check("SELL normal da setup valido", s["take_profit"] < s["entry"] < s["stop_loss"])

df_nan = velas()
df_nan.loc[df_nan.index[-1], "atr"] = np.nan
s = calculate_trade_levels(df_nan, "BUY", 1000, 0.005)
check("ATR NaN -> size 0 (antes daba NaN que pasaba validaciones)",
      s["position_size"] == 0 and s["stop_loss"] is None, f"-> {s}")

df_nan2 = velas()
df_nan2.loc[df_nan2.index[-1], "Close"] = np.nan
s = calculate_trade_levels(df_nan2, "BUY", 1000, 0.005)
check("Close NaN -> size 0", s["position_size"] == 0)

s = calculate_trade_levels(velas(atr=0.0), "BUY", 1000, 0.005)
check("ATR 0 -> size 0", s["position_size"] == 0)

s = calculate_trade_levels(velas(precio=1.0, atr=10.0), "SELL", 1000, 0.005)
check("TP negativo (precio bajo, ATR enorme) -> rechazado", s["position_size"] == 0)

s = calculate_trade_levels(None, "BUY")
check("df None no explota", s["position_size"] == 0)

s = calculate_trade_levels(velas().iloc[0:0], "BUY")
check("df vacio no explota", s["position_size"] == 0)


print("\n=== 2) paper_broker: validacion de setup ===")

v = paper_broker._is_valid_trade_setup
nan = float("nan")

check("setup con NaN rechazado",
      not v({"entry": 100, "stop_loss": nan, "take_profit": 102, "position_size": 2}, "BUY"))
check("size NaN rechazado",
      not v({"entry": 100, "stop_loss": 98, "take_profit": 102, "position_size": nan}, "BUY"))
check("infinito rechazado",
      not v({"entry": 100, "stop_loss": 98, "take_profit": float("inf"), "position_size": 2}, "BUY"))
check("BUY coherente aceptado",
      v({"entry": 100, "stop_loss": 98, "take_profit": 102.5, "position_size": 2}, "BUY"))
check("BUY con stop ARRIBA de entrada rechazado",
      not v({"entry": 100, "stop_loss": 102, "take_profit": 105, "position_size": 2}, "BUY"))
check("SELL coherente aceptado",
      v({"entry": 100, "stop_loss": 102, "take_profit": 97.5, "position_size": 2}, "SELL"))
check("SELL invertido rechazado",
      not v({"entry": 100, "stop_loss": 98, "take_profit": 102, "position_size": 2}, "SELL"))
check("sin signal sigue validando lo basico",
      v({"entry": 100, "stop_loss": 98, "take_profit": 102, "position_size": 2}))


print("\n=== 3) paper_broker: cierre intravela ===")

d = paper_broker._decidir_cierre

cerrar, px, motivo = d("BUY", 98.0, 102.5, price=100.0, high=100.5, low=97.5)
check("BUY: minimo perfora stop -> cierra EN el stop",
      cerrar and px == 98.0 and motivo == "STOP_LOSS", f"-> {cerrar} {px} {motivo}")

cerrar, px, motivo = d("BUY", 98.0, 102.5, price=100.0, high=103.0, low=99.0)
check("BUY: maximo alcanza target -> cierra EN el target",
      cerrar and px == 102.5 and motivo == "TAKE_PROFIT", f"-> {cerrar} {px} {motivo}")

cerrar, px, motivo = d("BUY", 98.0, 102.5, price=100.0, high=103.0, low=97.0)
check("BUY: vela toca ambos -> asume STOP (pesimista, igual que el backtest)",
      cerrar and px == 98.0 and motivo == "STOP_LOSS", f"-> {px} {motivo}")

cerrar, px, motivo = d("BUY", 98.0, 102.5, price=100.0, high=101.0, low=99.0)
check("BUY: vela dentro del rango -> no cierra", not cerrar)

cerrar, px, motivo = d("SELL", 102.0, 97.5, price=100.0, high=102.5, low=99.0)
check("SELL: maximo perfora stop -> cierra EN el stop",
      cerrar and px == 102.0 and motivo == "STOP_LOSS", f"-> {px} {motivo}")

cerrar, px, motivo = d("SELL", 102.0, 97.5, price=100.0, high=101.0, low=97.0)
check("SELL: minimo alcanza target -> cierra EN el target",
      cerrar and px == 97.5 and motivo == "TAKE_PROFIT", f"-> {px} {motivo}")

cerrar, px, motivo = d("SELL", 102.0, 97.5, price=100.0, high=103.0, low=97.0)
check("SELL: ambos -> asume STOP", cerrar and px == 102.0)

# Degradacion sin rango de vela: debe comportarse como antes.
cerrar, px, motivo = d("BUY", 98.0, 102.5, price=97.0, high=nan, low=nan)
check("sin high/low: cierre por debajo del stop sigue cerrando", cerrar and motivo == "STOP_LOSS")
cerrar, px, motivo = d("BUY", 98.0, 102.5, price=100.0, high=nan, low=nan)
check("sin high/low: cierre dentro de rango no cierra", not cerrar)


print("\n=== 4) paper_broker: ciclo completo contra sqlite ===")

storage.init_db()
cap0 = paper_broker.get_open_trade_count()
check("DB temporal arranca sin trades abiertos", cap0 == 0, f"-> {cap0}")

setup_corrupto = {"entry": 100.0, "stop_loss": nan, "take_profit": 102.5, "position_size": nan}
paper_broker.open_trade("TEST", "BUY", "TREND", setup_corrupto)
check("setup NaN no llega a la base de datos",
      paper_broker.get_open_trade_count() == 0, f"-> {paper_broker.get_open_trade_count()}")

setup_bueno = {"entry": 100.0, "stop_loss": 98.0, "take_profit": 102.5,
               "position_size": 2.5, "risk_amount": 5.0, "risk_per_unit": 2.0, "rr_ratio": 1.25}
paper_broker.open_trade("TEST", "BUY", "TREND", setup_bueno)
# Se captura AQUI la cantidad ejecutada: mas abajo el trade ya esta
# cerrado y el inventario vale cero, asi que leerlo alli no diria nada.
_cant_ejecutada = (paper_broker.cuenta().cantidad("TEST")
                   if hasattr(paper_broker, "cuenta") else None)
check("setup valido si se guarda", paper_broker.get_open_trade_count() == 1)
check("has_open_trade_for_ticker lo detecta", paper_broker.has_open_trade_for_ticker("TEST"))

paper_broker.open_trade("TEST", "BUY", "TREND", setup_bueno)
check("duplicado bloqueado", paper_broker.get_open_trade_count() == 1)

capital_antes = storage.get_paper_capital()
n = paper_broker.check_and_close_trades({"TEST": 100.2}, {"TEST": {"high": 100.5, "low": 99.5}})
check("vela dentro de rango -> no cierra nada", n == 0 and paper_broker.get_open_trade_count() == 1)
check("capital intacto si no cerro nada", storage.get_paper_capital() == capital_antes)

n = paper_broker.check_and_close_trades({"TEST": 101.0}, {"TEST": {"high": 103.0, "low": 100.0}})
check("target tocado -> cierra 1", n == 1 and paper_broker.get_open_trade_count() == 0)

# El esperado se reexpresa EN TERMINOS DEL CONTRATO, no se ajusta al
# resultado. Lo que esta prueba vigila es que la salida sea el nivel del
# TARGET (102,5) y no el Close de la vela (101,0), y eso sigue intacto.
# Lo que cambio es que el capital ya no crece con el PnL bruto: el core
# cobra las dos patas, que es el arreglo de la puerta V23.
#
#   bruto      = (102,5 - 100,0) * 2,5                    = 6,250
#   comisiones = (100,0*2,5 + 102,5*2,5) * 0,0008         = 0,405
#   neto       = 5,845
#
# Por el Close el bruto serian 2,50 en vez de 6,25, asi que la prueba
# sigue distinguiendo exactamente lo que fue escrita para distinguir: la
# diferencia entre las dos salidas (3,75) es nueve veces la comision.
from config import COSTE_POR_PATA as _CPP
# La cantidad EJECUTADA, no la pedida. El setup pide 2,5 unidades y la
# ruta al contado declara acciones enteras, asi que ejecuta 2. Antes nada
# imponia el lote en la ruta viva: se registraban 2,5 unidades mientras
# capacidades_core declaraba acciones enteras, que es el fallo que la
# tercera revision señalo con "declara acciones enteras, pero registra
# 9,992006... unidades".
_cant = _cant_ejecutada
_ejecutada = 2.0
_bruto_target = (102.5 - 100.0) * _ejecutada
_comisiones = (100.0 * _ejecutada + 102.5 * _ejecutada) * _CPP
esperado = capital_antes + _bruto_target - _comisiones
_esperado_si_usara_close = (capital_antes + (101.0 - 100.0) * _ejecutada
                            - (100.0 * _ejecutada + 101.0 * _ejecutada) * _CPP)
real = storage.get_paper_capital()
check("PnL calculado EN el nivel del target, no en el Close",
      abs(real - esperado) < 1e-6, f"-> esperado {esperado:.4f}, real {real:.4f}")

check("y el valor NO es el que daria salir al Close",
      abs(real - _esperado_si_usara_close) > 1.0,
      f"-> real {real:.4f}, por el Close serian {_esperado_si_usara_close:.4f}")

check("el lote entero se impone en la ruta viva: 2,5 pedidas -> 2",
      abs(_cant - _ejecutada) < 1e-9,
      f"-> la cuenta registro {_cant} unidades, exigidas {_ejecutada}. "
      f"Si sale 2,5, la ruta viva no impone el lote que declara")

check("el capital del core paga las dos patas",
      abs((capital_antes + _bruto_target) - real - _comisiones) < 1e-9,
      f"-> bruto habria dado {capital_antes + _bruto_target:.4f}, real "
      f"{real:.4f}, comisiones {_comisiones:.4f}")


print("\n=== 5) data_feed: recorte a horario regular ===")

# Vela cada 30m durante 24h en UTC: simula lo que devuelve Polygon.
idx_utc = pd.date_range("2026-01-05 00:00", periods=48 * 5, freq="30min", tz="UTC")
df_ext = pd.DataFrame({"Open": 100.0, "High": 101.0, "Low": 99.0,
                       "Close": 100.0, "Volume": 10.0}, index=idx_utc)

data_feed.ZONA_MERCADO = "US/Eastern" if HAY_TZDATA else TZ_EST
rec = data_feed._recortar_a_rth(df_ext, "30m")
horas = sorted(set(rec.index.hour))
check("recorte deja solo horas 9-15 ET", horas == [9, 10, 11, 12, 13, 14, 15], f"-> {horas}")
check("recorte reduce el numero de velas", len(rec) < len(df_ext), f"-> {len(rec)} de {len(df_ext)}")
check("no quedan fines de semana", set(rec.index.dayofweek) <= {0, 1, 2, 3, 4})

primera = rec.index[0]
check("primera vela del dia es 09:30", (primera.hour, primera.minute) == (9, 30),
      f"-> {primera.hour}:{primera.minute:02d}")
ult_dia = rec[rec.index.normalize() == rec.index[0].normalize()]
ultima = ult_dia.index[-1]
check("ultima vela del dia es 15:30 (16:00 excluido)",
      (ultima.hour, ultima.minute) == (15, 30), f"-> {ultima.hour}:{ultima.minute:02d}")
check("velas por dia = 13", len(ult_dia) == 13, f"-> {len(ult_dia)}")

check("diario no se recorta", len(data_feed._recortar_a_rth(df_ext, "1d")) == len(df_ext))
check("sin DatetimeIndex no explota",
      data_feed._recortar_a_rth(pd.DataFrame({"Close": [1, 2]}), "30m") is not None)


print("\n=== 6) data_feed: minimo de velas ===")

check("MIN_BARS >= 220 (ema200 + warmup)", config.MIN_BARS >= 220, f"-> {config.MIN_BARS}")

corto = pd.DataFrame({"Open": 1.0, "High": 1.0, "Low": 1.0, "Close": 1.0, "Volume": 1.0},
                     index=pd.date_range("2026-01-01", periods=100, freq="30min", tz="UTC"))
try:
    data_feed._normalize_df(corto)
    check("100 velas rechazadas", False, "-> no lanzo excepcion")
except ValueError as e:
    check("100 velas rechazadas con mensaje claro", "220" in str(e), f"-> {e}")

largo = pd.DataFrame({"Open": 1.0, "High": 1.0, "Low": 1.0, "Close": 1.0, "Volume": 1.0},
                     index=pd.date_range("2026-01-01", periods=300, freq="30min", tz="UTC"))
try:
    data_feed._normalize_df(largo)
    check("300 velas aceptadas", True)
except ValueError as e:
    check("300 velas aceptadas", False, f"-> {e}")


print("\n=== 7) filtro de sesion: falla CERRADA ===")

import session_volatility_intelligence as svi

idx_noche = pd.date_range("2026-01-05 03:00", periods=300, freq="30min", tz="UTC")
df_noche = pd.DataFrame({"Open": 100.0, "High": 101.0, "Low": 99.0, "Close": 100.0,
                         "Volume": 10.0, "atr": 1.0, "adx": 25.0}, index=idx_noche)

zona_buena = svi.ZONA_MERCADO
svi.ZONA_MERCADO = "Zona/Inexistente"
r = svi.evaluate_session_filter(df_noche, "TREND")
check("zona horaria rota -> BLOQUEA (antes dejaba pasar todo)",
      r["allow"] is False and r["session"] == "UNKNOWN", f"-> {r}")
svi.ZONA_MERCADO = zona_buena

df_nan_adx = df_noche.copy()
df_nan_adx.loc[df_nan_adx.index[-1], "adx"] = np.nan
svi.ZONA_MERCADO = "Zona/Inexistente"
r = svi.evaluate_session_filter(df_nan_adx, "TREND")
check("adx NaN no revienta el filtro", r["allow"] is False)
svi.ZONA_MERCADO = zona_buena

if HAY_TZDATA:
    r = svi.evaluate_session_filter(df_noche, "TREND")
    check("velas de madrugada bloqueadas por OFF_HOURS",
          r["allow"] is False and r["session"] == "OFF_HOURS", f"-> {r}")
else:
    print("  OMITE sesion real (sin tzdata en este entorno)")

# El filtro de sesion no aplica en diario: una vela diaria ES la
# sesion completa. Antes bloqueaba el 100% de las senales diarias
# porque yfinance las marca a medianoche -> OFF_HOURS.
# En un backtest diario de 15 anos: 2222 senales, 0 operaciones.
svi.ZONA_MERCADO = "US/Eastern" if HAY_TZDATA else TZ_EST


def _velas(freq, n=300, hora="00:00"):
    idx = pd.date_range(f"2020-01-02 {hora}", periods=n, freq=freq, tz=TZ_EST)
    return pd.DataFrame({"Open": 100.0, "High": 101.0, "Low": 99.0,
                         "Close": 100.0, "Volume": 10.0, "atr": 1.0,
                         "adx": 25.0}, index=idx)


diarias = _velas("1D")
check("velas diarias se detectan como NO intradia",
      svi._es_intradia(diarias) is False)
r = svi.evaluate_session_filter(diarias, "TREND")
check("diario a medianoche NO se bloquea por horario",
      r["allow"] is True and r["session"] == "VELA_DIARIA", f"-> {r}")

r = svi.evaluate_session_filter(_velas("1D", hora="09:30"), "TREND")
check("diario con otra marca horaria tampoco se bloquea", r["allow"] is True)

r = svi.evaluate_session_filter(_velas("7D"), "TREND")
check("semanal tampoco se bloquea", r["allow"] is True)

check("velas de 30m siguen siendo intradia",
      svi._es_intradia(_velas("30min", hora="10:00")) is True)
check("velas de 1h siguen siendo intradia",
      svi._es_intradia(_velas("1h", hora="10:00")) is True)
check("pocas velas -> se asume intradia (conservador)",
      svi._es_intradia(_velas("1D", n=2)) is True)
check("df vacio no explota", svi._es_intradia(None) is True)


print("\n=== 8) config: cascada de providers ===")

check("polygon fuera de la cascada", "polygon" not in config.DATA_PROVIDER_ORDER,
      f"-> {config.DATA_PROVIDER_ORDER}")
check("yfinance es el primero", config.DATA_PROVIDER_ORDER[0] == "yfinance",
      f"-> {config.DATA_PROVIDER_ORDER}")
check("PRIMARY_PROVIDER coherente", config.PRIMARY_PROVIDER == "yfinance")

print("\n" + "=" * 62)
print(f"RESULTADO: {OK} pruebas pasadas, {len(FALLOS)} fallos")
if FALLOS:
    print("\nFALLOS:")
    for f in FALLOS:
        print(f"  - {f}")
print("=" * 62)

os.unlink(_tmpdb.name)
sys.exit(1 if FALLOS else 0)
