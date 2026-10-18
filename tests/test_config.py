"""
Pruebas de config.py.

Existe por un fallo real: os.getenv("X", defecto) devuelve "" si la
variable esta definida pero vacia, no el valor por defecto. GitHub
Actions pasa "" a las entradas que no se rellenan, asi que ASSETS
quedo en lista vacia y el backtest abortó sin activos.

Cada caso corre en un proceso aparte porque config se evalua una
sola vez al importarse.
"""
import os
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

OK = 0
FALLOS = []


def check(nombre, cond, detalle=""):
    global OK
    if cond:
        OK += 1
        print(f"  PASA   {nombre}")
    else:
        FALLOS.append(nombre)
        print(f"  FALLA  {nombre}  {detalle}")


def leer_config(entorno, expresion):
    """Importa config con un entorno dado y evalua una expresion."""
    env = dict(os.environ)
    env.update(entorno)
    env["TELEGRAM_TOKEN"] = ""
    env["PYTHONPATH"] = REPO

    r = subprocess.run(
        [sys.executable, "-c", f"import config; print(repr({expresion}))"],
        capture_output=True, text=True, env=env, cwd=REPO, timeout=60,
    )
    return r.returncode, r.stdout.strip(), r.stderr.strip()


print("\n=== 1) variables vacias caen al valor por defecto ===")

for var, expr, esperado in [
    ("ASSETS", "config.ASSETS", "['IWM', 'NVDA', 'AMZN', 'META']"),
    ("TIMEFRAME", "config.TIMEFRAME", "'30m'"),
    ("PERIOD", "config.PERIOD", "'60d'"),
    ("MIN_BARS", "config.MIN_BARS", "220"),
    ("DATABASE_NAME", "config.DATABASE_NAME", "'shark_v8.db'"),
]:
    codigo, salida, err = leer_config({var: ""}, expr)
    check(f"{var}='' -> defecto", codigo == 0 and salida == esperado,
          f"-> codigo {codigo}, salida {salida!r} {err[:120]}")

codigo, salida, _ = leer_config({"ASSETS": "   "}, "config.ASSETS")
check("ASSETS solo espacios -> defecto",
      codigo == 0 and "IWM" in salida, f"-> {salida!r}")

codigo, salida, _ = leer_config(
    {"DATA_PROVIDER_ORDER": ""}, "config.DATA_PROVIDER_ORDER")
check("DATA_PROVIDER_ORDER='' -> defecto con yfinance primero",
      codigo == 0 and salida.startswith("['yfinance'"), f"-> {salida!r}")


print("\n=== 2) variables con valor se respetan ===")

codigo, salida, _ = leer_config({"ASSETS": "spy, qqq ,aapl"}, "config.ASSETS")
check("ASSETS se parsea y normaliza a mayusculas",
      codigo == 0 and salida == "['SPY', 'QQQ', 'AAPL']", f"-> {salida!r}")

codigo, salida, _ = leer_config(
    {"TIMEFRAME": "1d"}, "(config.TIMEFRAME, config.PERIOD)")
check("timeframe diario usa historico largo por defecto",
      codigo == 0 and "15y" in salida, f"-> {salida!r}")

codigo, salida, _ = leer_config(
    {"TIMEFRAME": "1d", "PERIOD": "5y"}, "config.PERIOD")
check("PERIOD explicito manda sobre el derivado",
      codigo == 0 and salida == "'5y'", f"-> {salida!r}")

codigo, salida, _ = leer_config(
    {"DATA_PROVIDER_ORDER": "polygon,yfinance"}, "config.DATA_PROVIDER_ORDER")
check("se puede reactivar polygon sin tocar codigo",
      codigo == 0 and salida == "['polygon', 'yfinance']", f"-> {salida!r}")

codigo, salida, _ = leer_config(
    {"SL_ATR_MULT": "1.5", "TP_ATR_MULT": "3.0"},
    "(config.SL_ATR_MULT, config.TP_ATR_MULT)")
check("multiplos de SL/TP configurables",
      codigo == 0 and "1.5" in salida and "3.0" in salida, f"-> {salida!r}")


print("\n=== 3) configuraciones imposibles fallan al arrancar ===")

casos_malos = [
    ({"ASSETS": "  ,  , "}, "ASSETS solo comas"),
    ({"DATA_PROVIDER_ORDER": "inventado"}, "provider desconocido"),
    ({"MIN_BARS": "50"}, "MIN_BARS por debajo de 220"),
    ({"CAPITAL": "0"}, "capital 0"),
    ({"RISK_PER_TRADE": "0.5"}, "riesgo del 50% por trade"),
    ({"LOOP_INTERVAL": "5"}, "loop de 5 segundos"),
    ({"MAX_OPEN_TRADES": "0"}, "cero trades abiertos permitidos"),
    ({"SL_ATR_MULT": "0"}, "multiplo de stop 0"),
]

for entorno, descripcion in casos_malos:
    codigo, _, err = leer_config(entorno, "config.APP_NAME")
    check(f"{descripcion} -> error al arrancar",
          codigo != 0 and ("ValueError" in err or "Error" in err),
          f"-> codigo {codigo}")


print("\n=== 4) coherencia de los valores por defecto ===")

codigo, salida, err = leer_config({}, (
    "(config.APP_NAME, config.MIN_BARS, config.SL_ATR_MULT, "
    "config.TP_ATR_MULT, config.DATA_PROVIDER_ORDER[0], "
    "config.SNIPER_MIN_ADX)"
))
check("config por defecto carga sin errores", codigo == 0, f"-> {err[:150]}")
check("nombre de la app ya no dice V16",
      "V16" not in salida and "V15" in salida, f"-> {salida}")
check("polygon fuera de la cascada por defecto",
      "polygon" not in salida, f"-> {salida}")
check("TP mayor que SL (R:R > 1)", codigo == 0 and "2.0, 2.5" in salida,
      f"-> {salida}")

print("\n" + "=" * 62)
print(f"RESULTADO: {OK} pruebas pasadas, {len(FALLOS)} fallos")
for f in FALLOS:
    print(f"  - {f}")
print("=" * 62)

sys.exit(1 if FALLOS else 0)
