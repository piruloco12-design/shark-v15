"""
Pruebas del archivo historico de velas (historial_mercado.py).

Comprueba que acumula de verdad: que dos descargas solapadas no
duplican velas, que las velas nuevas se suman a las viejas, y que
el aviso de almacenamiento efimero funciona.
"""
import os
import sys
import tempfile
import types

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

_tmpdb = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_tmpdb.close()
os.environ["DATABASE_NAME"] = _tmpdb.name
os.environ["TELEGRAM_TOKEN"] = ""

_stub_yf = types.ModuleType("yfinance")
_stub_yf.download = lambda *a, **k: None
sys.modules.setdefault("yfinance", _stub_yf)

import pandas as pd

import historial_mercado as hm

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


def tramo(inicio, n, base=100.0):
    idx = pd.date_range(inicio, periods=n, freq="30min", tz="UTC")
    close = pd.Series([base + i for i in range(n)], index=idx)
    return pd.DataFrame({
        "Open": close, "High": close + 1, "Low": close - 1,
        "Close": close, "Volume": 500.0,
    }, index=idx)


print("\n=== 1) guardar y cargar ===")

hm.init_historial()
check("arranca vacio", len(hm.cargar("TEST", "30m")) == 0)

primero = tramo("2026-01-05 09:30", 50)
n = hm.guardar("TEST", "30m", primero)
check("guarda 50 velas", n == 50, f"-> {n}")

leido = hm.cargar("TEST", "30m")
check("lee las 50", len(leido) == 50, f"-> {len(leido)}")
check("columnas correctas",
      list(leido.columns) == ["Open", "High", "Low", "Close", "Volume"],
      f"-> {list(leido.columns)}")
check("indice de fechas en UTC",
      isinstance(leido.index, pd.DatetimeIndex) and str(leido.index.tz) == "UTC",
      f"-> {leido.index.tz}")
check("valores intactos",
      abs(float(leido.iloc[0]["Close"]) - 100.0) < 1e-9
      and abs(float(leido.iloc[-1]["Close"]) - 149.0) < 1e-9,
      f"-> {leido.iloc[0]['Close']} .. {leido.iloc[-1]['Close']}")
check("orden cronologico", leido.index.is_monotonic_increasing)


print("\n=== 2) acumulacion sin duplicar ===")

# Segunda descarga que SOLAPA con la primera (lo que pasa de
# verdad: cada ciclo rebaja la misma ventana de 60 dias corrida).
solapado = tramo("2026-01-05 09:30", 50)
hm.guardar("TEST", "30m", solapado)
check("reguardar lo mismo no duplica",
      len(hm.cargar("TEST", "30m")) == 50,
      f"-> {len(hm.cargar('TEST', '30m'))}")

# Tramo que solapa a medias y añade velas nuevas.
mitad_nuevo = tramo("2026-01-06 09:30", 50, base=200.0)
hm.guardar("TEST", "30m", mitad_nuevo)
total = hm.cargar("TEST", "30m")
check("las velas nuevas SI se suman", len(total) > 50, f"-> {len(total)}")
check("el histórico cubre mas dias que una sola descarga",
      total.index.normalize().nunique() >= 2,
      f"-> {total.index.normalize().nunique()} dias")

print(f"  (acumulado: {len(total)} velas, "
      f"{total.index[0]} -> {total.index[-1]})")


print("\n=== 3) separacion por activo y timeframe ===")

hm.guardar("OTRO", "30m", tramo("2026-01-05 09:30", 30, base=50.0))
hm.guardar("TEST", "1d", tramo("2026-01-05 09:30", 20, base=10.0))

check("TEST/30m no se mezcla con OTRO/30m",
      len(hm.cargar("OTRO", "30m")) == 30, f"-> {len(hm.cargar('OTRO', '30m'))}")
check("TEST/30m no se mezcla con TEST/1d",
      len(hm.cargar("TEST", "1d")) == 20, f"-> {len(hm.cargar('TEST', '1d'))}")
check("TEST/30m sigue completo", len(hm.cargar("TEST", "30m")) == len(total))


print("\n=== 4) fusionar ===")

fusionado = hm.fusionar("TEST", "30m", tramo("2026-01-07 09:30", 10, base=300.0))
check("fusionar devuelve el acumulado, no solo lo nuevo",
      len(fusionado) > 10, f"-> {len(fusionado)}")
check("fusionar incluye las velas nuevas",
      len(fusionado) == len(hm.cargar("TEST", "30m")))

vacio_antes = len(hm.cargar("NUEVO", "30m"))
f2 = hm.fusionar("NUEVO", "30m", tramo("2026-01-05 09:30", 5, base=1.0))
check("fusionar sobre activo nuevo funciona", vacio_antes == 0 and len(f2) == 5,
      f"-> {len(f2)}")


print("\n=== 5) robustez ===")

check("guardar None no explota", hm.guardar("X", "30m", None) == 0)
check("guardar vacio no explota",
      hm.guardar("X", "30m", pd.DataFrame(columns=["Open", "High", "Low", "Close"])) == 0)

try:
    hm.guardar("X", "30m", pd.DataFrame({"Close": [1.0, 2.0]}))
    check("faltar columnas da error claro", False, "-> no lanzo")
except ValueError as e:
    check("faltar columnas da error claro", "Faltan columnas" in str(e))

try:
    hm.guardar("X", "30m", pd.DataFrame({
        "Open": [1.0], "High": [1.0], "Low": [1.0], "Close": [1.0]}))
    check("sin DatetimeIndex da error claro", False, "-> no lanzo")
except ValueError as e:
    check("sin DatetimeIndex da error claro", "DatetimeIndex" in str(e))

sin_volumen = tramo("2026-02-02 09:30", 10)[["Open", "High", "Low", "Close"]]
check("sin columna Volume se rellena con 0",
      hm.guardar("SINVOL", "30m", sin_volumen) == 10)
check("volumen a 0", float(hm.cargar("SINVOL", "30m").iloc[0]["Volume"]) == 0.0)


print("\n=== 6) resumen ===")

datos = hm.resumen()
check("resumen lista todas las series", len(datos) >= 5, f"-> {len(datos)}")
fila = [d for d in datos if d["ticker"] == "TEST" and d["timeframe"] == "30m"]
check("resumen cuenta bien", fila and fila[0]["velas"] == len(hm.cargar("TEST", "30m")),
      f"-> {fila}")


print("\n=== 7) aviso de almacenamiento efimero ===")

# El aviso NO depende de detectar Render. Antes solo saltaba si
# existian las variables RENDER o RENDER_SERVICE_ID, asi que un
# entorno que no las definiera se quedaba sin aviso teniendo la
# base de datos en almacenamiento efimero.

# Caso real del 2026-10-19: el disco estaba montado en /var/data
# pero DATABASE_NAME iba sin barra inicial, asi que el bot
# escribia en la carpeta del proyecto. El disco marcaba 0 GB
# durante tres dias.
hm.DATABASE_NAME = "var/data/shark_v8.db"
persistente, mensaje = hm.comprobar_persistencia()
check("ruta relativa AVISA aunque parezca correcta",
      persistente is False, f"-> {mensaje}")
check("el aviso explica que es relativa", "RELATIVA" in mensaje)
check("y da el valor correcto", "/var/data/shark_v8.db" in mensaje)

hm.DATABASE_NAME = "shark_v8.db"
persistente, mensaje = hm.comprobar_persistencia()
check("nombre suelto tambien AVISA", persistente is False)

hm.DATABASE_NAME = "/tmp/suelta.db"
persistente, mensaje = hm.comprobar_persistencia()
check("ruta absoluta fuera de un montaje AVISA", persistente is False, f"-> {mensaje}")
check("el aviso dice bajo que montajes se espera", "/var/data" in mensaje)

hm.DATABASE_NAME = "/var/data/shark_v8.db"
persistente, mensaje = hm.comprobar_persistencia()
check("disco montado: no avisa", persistente is True, f"-> {mensaje}")
check("y confirma la ruta", "/var/data/shark_v8.db" in mensaje)

# Sin depender de variables de entorno en ningun caso
os.environ.pop("RENDER", None)
hm.DATABASE_NAME = "shark_v8.db"
sin_render, _ = hm.comprobar_persistencia()
os.environ["RENDER"] = "true"
con_render, _ = hm.comprobar_persistencia()
del os.environ["RENDER"]
check("el aviso NO depende de la variable RENDER",
      sin_render == con_render is False,
      f"-> sin RENDER: {sin_render}, con RENDER: {con_render}")


print("\n" + "=" * 62)
print(f"RESULTADO: {OK} pruebas pasadas, {len(FALLOS)} fallos")
for f in FALLOS:
    print(f"  - {f}")
print("=" * 62)

os.unlink(_tmpdb.name)
sys.exit(1 if FALLOS else 0)
