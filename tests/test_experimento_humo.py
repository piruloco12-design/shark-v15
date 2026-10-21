"""
PRUEBA DE HUMO DEL EXPERIMENTO COMPLETO, SIN RED.

Por que existe. El experimento descarga 31 activos y 15 anos, corre ocho
carteras, guarda artefactos, hace inferencia y escribe el informe. En CI
tardaba varios minutos... y murio con un KeyError sobre
'rotacion_anual_nominal' en un `print` del resumen, DESPUES de todas las
descargas. Yo habia renombrado esa clave en el cambio 5 y no busque quien
la leia.

Ninguna de mis 499 comprobaciones toco esa ruta, porque todas prueban
funciones y ninguna corria el experimento de punta a punta. Esta si: con
series sinteticas inyectadas por `descargar`, recorre el camino COMPLETO
-- registro, carga, ocho corridas, artefactos, inferencia, Holm,
supervivencia, M04 e informe -- en segundos y sin tocar la red.

No comprueba ninguna cifra economica: para eso estan las puertas y los
contratos de aceptacion. Comprueba que el camino no se rompe, que es lo
que no estaba comprobado.

Uso:  python tests/test_experimento_humo.py
"""
import hashlib
import io
import json
import os
import shutil
import sys
import tempfile
import types

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)
sys.path.insert(0, os.path.join(REPO, "tests"))

os.environ.setdefault("TELEGRAM_TOKEN", "")
os.environ.setdefault("CAPITAL", "1000")
sys.modules.setdefault("yfinance", types.ModuleType("yfinance"))

import _ta_stub
_ta_stub.instalar_si_falta()

import numpy as np
import pandas as pd

PASA, FALLA = [], []


def check(ident, nombre, cond, detalle=""):
    if cond:
        PASA.append(ident)
        print(f"  PASA   [{ident}] {nombre}")
    else:
        FALLA.append((ident, nombre, detalle))
        print(f"  FALLA  [{ident}] {nombre}")
        if detalle:
            print(f"                 {detalle}")


# Quince anos de sesiones diarias. Cada ticker con su propia deriva y su
# propio ruido, deterministas por semilla: el experimento tiene que ser
# reproducible y una serie aleatoria sin semilla lo impediria.
IDX = pd.bdate_range("2011-01-03", periods=3800, tz="UTC")


def _semilla_estable(texto: str) -> int:
    """Semilla reproducible ENTRE PROCESOS.

    Usaba `hash(texto)`, que en Python lleva aleatorizacion por proceso
    (PYTHONHASHSEED): la misma prueba generaba series distintas en cada
    ejecucion, asi que una prueba de reproducibilidad no era reproducible
    ella misma. Lo señalo la tercera revision.
    """
    return int(hashlib.sha256(texto.encode()).hexdigest()[:8], 16)


def _serie(ticker: str) -> pd.DataFrame:
    semilla = _semilla_estable(ticker)
    rng = np.random.default_rng(semilla)
    n = len(IDX)
    deriva = 1.0 + (semilla % 13) / 20000.0
    pasos = rng.normal(0.0, 0.009, n)
    nivel = 100.0 * np.cumprod(deriva * np.exp(pasos))
    c = pd.Series(nivel, index=IDX)
    o = c.shift(1).fillna(c.iloc[0])
    alto = pd.concat([o, c], axis=1).max(axis=1) * 1.004
    bajo = pd.concat([o, c], axis=1).min(axis=1) * 0.996
    return pd.DataFrame({"Open": o, "High": alto, "Low": bajo, "Close": c,
                         "Volume": 1e6}, index=IDX)


def descarga_sintetica(ticker):
    return _serie(ticker), "sintetico_para_humo"


print("\n=== Experimento completo, series sinteticas, sin red ===")

tmp = tempfile.mkdtemp(prefix="humo_exp_")
informe = None
try:
    os.environ["SALIDA_EXP"] = tmp
    # Se importa DESPUES de fijar SALIDA_EXP: el modulo la lee al cargarse.
    for mod in [m for m in list(sys.modules) if m.startswith("evaluador.experimento")]:
        del sys.modules[mod]
    from evaluador import experimento as EXP

    check("H0", "la salida del experimento no apunta a una entrega cerrada",
          os.path.basename(os.path.normpath(EXP.SALIDA)) not in EXP.SALIDAS_CERRADAS,
          f"-> SALIDA={EXP.SALIDA}")

    EXP.main(descargar=descarga_sintetica)
    check("H1", "el experimento completo termina sin excepcion", True)
except Exception as e:
    import traceback
    check("H1", "el experimento completo termina sin excepcion", False,
          f"-> {type(e).__name__}: {str(e)[:200]}")
    traceback.print_exc()

# Cada corrida escribe en SU carpeta: resultados/<base>/<run_id>/. Antes
# los CSV y report.json reutilizaban el nombre en la base y la siguiente
# corrida los pisaba.
ruta_informe = None
try:
    carpeta = globals().get("EXP").SALIDA_CORRIDA if "EXP" in globals() else tmp
    ruta_informe = os.path.join(carpeta, "report.json")
    if os.path.exists(ruta_informe):
        informe = json.load(io.open(ruta_informe, encoding="utf-8"))
except Exception as e:
    print(f"  (no se pudo leer el informe: {e})")

check("H2b", "la corrida escribe en su propia carpeta, no en la base",
      ruta_informe is not None and os.path.dirname(ruta_informe) != tmp
      and os.path.basename(os.path.dirname(ruta_informe)) not in ("", None),
      f"-> informe en {ruta_informe}")

check("H2", "escribe report.json", informe is not None,
      f"-> no hay informe en {tmp}")

if informe:
    check("H3", "el informe trae las ocho carteras",
          len(informe.get("resumenes", {})) == 8,
          f"-> {len(informe.get('resumenes', {}))} resumenes: "
          f"{sorted(informe.get('resumenes', {}))}")

    # La ruta del registro es RELATIVA a la carpeta de la corrida, no a la
    # base: cada corrida tiene su carpeta y su registro dentro.
    _ruta_reg = os.path.join(os.path.dirname(ruta_informe),
                             informe.get("registro_archivo") or "")
    check("H4", "el informe enlaza con SU registro de corrida",
          bool(informe.get("run_id"))
          and bool(informe.get("registro_archivo"))
          and os.path.exists(_ruta_reg),
          f"-> run_id={informe.get('run_id')}, "
          f"registro={informe.get('registro_archivo')}, existe="
          f"{os.path.exists(_ruta_reg)}")

    # Las claves que el resumen por pantalla y las tablas LEEN. Esta es la
    # comprobacion que faltaba: la que murio fue una lectura de clave.
    faltan = {}
    for clave, r in informe.get("resumenes", {}).items():
        for k in ("cagr", "max_drawdown_diario", "intenciones",
                  "sharpe_diferencial", "nav_final", "retorno_total",
                  "rotacion_anual_sobre_patrimonio_medio",
                  "rotacion_anual_nominal_sobre_capital_inicial",
                  "rotacion_convencion", "nav_fiable", "dias_no_evaluables"):
            if k not in r:
                faltan.setdefault(clave, []).append(k)
    check("H5", "cada resumen trae las claves que leen el informe y las tablas",
          not faltan, f"-> faltan: {faltan}")

    # El ledger diario tiene que EXISTIR como archivo: se calculaba y no
    # se exportaba, asi que la exposicion media no era comprobable desde
    # los artefactos.
    _carp = os.path.dirname(ruta_informe)
    _ledgers = [f for f in os.listdir(_carp) if f.endswith(".ledger_daily.csv")]
    check("H5b", "el ledger diario se exporta como artefacto, no solo se calcula",
          len(_ledgers) == 8,
          f"-> {len(_ledgers)} archivos ledger_daily de 8 carteras: {_ledgers[:3]}")

    _arte = informe.get("artefactos", {})
    _declara_ledger = all("ledger_daily" in v for v in _arte.values()) if _arte else False
    check("H5c", "el informe no anuncia archivos que no produce",
          _declara_ledger and all(
              os.path.exists(r) for v in _arte.values() for r in v.values()),
          f"-> {len(_arte)} carteras; todas declaran ledger_daily="
          f"{_declara_ledger}")

    check("H6", "hay contrastes y correccion de Holm para la familia",
          len(informe.get("contrastes", {})) == 4
          and len(informe.get("holm", {})) == 4,
          f"-> {len(informe.get('contrastes', {}))} contrastes, "
          f"{len(informe.get('holm', {}))} en Holm")

    # El generador de tablas tiene que tragarse ESTE informe.
    try:
        from evaluador.informe_tablas import generar
        texto = generar(ruta_informe)
        ok_tablas = len(texto) > 500 and "Rendimiento por universo" in texto
        det = f"-> {len(texto)} caracteres"
    except Exception as e:
        ok_tablas = False
        det = f"-> {type(e).__name__}: {str(e)[:120]}"
    check("H7", "el generador de tablas procesa el informe recien escrito",
          ok_tablas, det)

    # Y el registro no se puede pisar: una segunda corrida con la misma
    # salida tiene que fallar al escribirlo, no sobrescribirlo.
    try:
        from evaluador import registro as REG
        REG.crear(
            nombre="prueba de no sobrescritura", familia=[{"id": "x"}],
            metrica_primaria="m", hipotesis="h", umbral_economico=0.0,
            metodo_inferencia="i", parametros_inferencia={},
            estado="EXPLORATORIO", universo_etiqueta="u", politicas={},
            variantes_ya_vistas=[], rutas_codigo=[],
            salida=_ruta_reg)
        ok_nosobre = False
    except Exception as e:
        ok_nosobre = type(e).__name__ == "RegistroYaExiste"
        det_nosobre = f"-> {type(e).__name__}"
    check("H8", "el registro de la corrida no se puede sobrescribir",
          ok_nosobre, locals().get("det_nosobre", "-> se dejo pisar"))

shutil.rmtree(tmp, ignore_errors=True)
os.environ.pop("SALIDA_EXP", None)

print("\n" + "=" * 68)
print(f"HUMO DEL EXPERIMENTO: {len(PASA)} pasan, {len(FALLA)} FALLAN")
print("=" * 68)
if FALLA:
    print("\nEl camino completo del experimento esta roto en:\n")
    for ident, nombre, _ in FALLA:
        print(f"  [{ident}] {nombre}")
    print("\nEsto se nota en CI DESPUES de descargar 31 activos y 15 anos.")
    print("Aqui se nota en segundos.")
print("=" * 68)

sys.exit(1 if FALLA else 0)
