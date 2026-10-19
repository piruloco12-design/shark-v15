"""
Pruebas del universo congelado.

Lo que tienen que proteger: que una baja NUNCA se borre de la lista. Si se
borrara, el sistema que pretende evitar el sesgo de supervivencia lo estaría
reinventando por dentro, y eso sería peor que no tenerlo, porque parecería
resuelto.
"""
import json
import os
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

import universo_congelado as U

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


TICKERS = ["SPY", "QQQ", "IWM", "GLD", "TLT", "FXE", "XLK", "DBC"]
_dir = tempfile.mkdtemp()
RUTA = os.path.join(_dir, "u.json")

print("\n=== congelar ===")
datos = U.congelar(TICKERS, regla="regla de prueba", ruta=RUTA,
                   fecha="2026-10-19")
check("congela la lista con su fecha y su hash",
      len(datos["instrumentos"]) == len(TICKERS) and len(datos["hash"]) == 16)
check("cada instrumento queda con su fecha de alta",
      all(v["alta"] == "2026-10-19" for v in datos["instrumentos"].values()))

try:
    U.congelar(TICKERS, regla="otra", ruta=RUTA)
    check("no se puede recongelar", False, "-> permitio recongelar")
except U.UniversoInvalido:
    check("no se puede recongelar (seria elegir sabiendo quien sobrevivio)",
          True)

try:
    U.congelar(["A", "B"], regla="r", ruta=os.path.join(_dir, "corto.json"))
    check("un universo de 2 instrumentos se rechaza", False)
except U.UniversoInvalido:
    check("un universo demasiado pequeno se rechaza", True)


print("\n=== seguimiento ===")
e1 = U.comprobar(TICKERS, ruta=RUTA, fecha_comprobacion="2026-10-20")
check("todos vivos al principio",
      e1["vivos"] == len(TICKERS) and not e1["bajas_candidatas"])
check("la tasa de supervivencia se informa",
      e1["tasa_supervivencia_observada"] == 1.0)

e2 = U.comprobar([t for t in TICKERS if t != "DBC"], ruta=RUTA,
                 fecha_comprobacion="2026-11-15")
check("un instrumento sin datos se marca como baja candidata",
      e2["bajas_candidatas"] == ["DBC"]
      and e2["nuevas_bajas_en_esta_corrida"] == ["DBC"])

# LA PRUEBA QUE IMPORTA
tras = U.cargar(RUTA)
check("LA BAJA SIGUE EN LA LISTA (si se borrara, se reinventaria el sesgo)",
      "DBC" in tras["instrumentos"]
      and tras["instrumentos"]["DBC"]["sin_datos_desde"] == "2026-11-15"
      and tras["instrumentos"]["DBC"]["baja_candidata"] is True,
      f"-> {tras['instrumentos'].get('DBC')}")
check("el total congelado no baja al perder un instrumento",
      e2["total_congelados"] == len(TICKERS), f"-> {e2['total_congelados']}")
check("la tasa de supervivencia refleja la perdida",
      abs(e2["tasa_supervivencia_observada"] - 7 / 8) < 1e-9)

e3 = U.comprobar(TICKERS, ruta=RUTA, fecha_comprobacion="2026-11-20")
check("si vuelve a dar datos se registra el ida y vuelta, no se borra",
      e3["resucitados"] and e3["resucitados"][0]["instrumento"] == "DBC"
      and not e3["bajas_candidatas"])
check("y queda en las observaciones del instrumento",
      "volvio" in U.cargar(RUTA)["instrumentos"]["DBC"]["observaciones"])

e4 = U.comprobar(TICKERS + ["RECIEN"], ruta=RUTA,
                 fecha_comprobacion="2026-12-01")
check("un instrumento nuevo NO se anade solo al universo congelado",
      e4["fuera_del_universo_congelado"] == ["RECIEN"]
      and "RECIEN" not in U.cargar(RUTA)["instrumentos"])


print("\n=== integridad ===")
j = json.load(open(RUTA))
j["instrumentos"].pop("DBC")
json.dump(j, open(RUTA, "w"), indent=2)
cargado = U.cargar(RUTA)
check("editar la lista a mano rompe el hash y se detecta",
      cargado["hash_coincide"] is False and "_alerta" in cargado,
      f"-> hash_coincide={cargado['hash_coincide']}")
check("la alerta dice que se ha editado despues de congelar",
      "editado" in cargado.get("_alerta", ""))

print("\n" + "=" * 62)
print(f"RESULTADO: {OK} pruebas pasadas, {len(FALLOS)} fallos")
for f in FALLOS:
    print(f"  - {f}")
print("=" * 62)
sys.exit(1 if FALLOS else 0)
