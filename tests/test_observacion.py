"""
LA PRUEBA QUE PROTEGE AL BOT EN VIVO.

El documento (seccion 15.11, paso 2) exige: "Ejecutar la reproduccion de
B1 con extensiones OFF y OBSERVE, exigiendo igualdad de decisiones/
estados relevantes."

Eso es esto. Corre un ciclo completo de live_engine dos veces, en
procesos separados, con datos sinteticos identicos:

    corrida 1: INSTITUCIONAL_MODO=OFF
    corrida 2: INSTITUCIONAL_MODO=OBSERVE

Y exige que las senales, las operaciones, el estado del broker, los
eventos de riesgo y el log de decisiones sean IDENTICOS. Lo unico que
debe diferir es la tabla de observacion, que en OFF no existe.

Procesos separados a proposito: varios modulos leen DATABASE_NAME al
importarse. En un solo proceso la primera corrida contaminaria la
segunda y la prueba pasaria por el motivo equivocado.

Ademas:
  - barrido de TODAS las combinaciones de estado de los modulos,
    comprobando que en OBSERVE nunca se bloquea
  - datos basura, para que un modulo que revienta no se convierta en
    un veto
"""
import itertools
import json
import os
import subprocess
import sys
import tempfile
import types

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

os.environ.setdefault("TELEGRAM_TOKEN", "")
sys.modules.setdefault("yfinance", types.ModuleType("yfinance"))

import _ta_stub
_ta_stub.instalar_si_falta()

import pandas as pd

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


# =====================================================================
print("\n=== 1) OFF vs OBSERVE: las decisiones deben ser identicas ===")
# =====================================================================

RUNNER = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                      "_replay_runner.py")

resultados = {}
tmp = tempfile.mkdtemp(prefix="shark-replay-")

for modo in ("OFF", "OBSERVE"):
    db = os.path.join(tmp, f"{modo}.db")
    salida = os.path.join(tmp, f"{modo}.json")
    proc = subprocess.run(
        [sys.executable, RUNNER, db, modo, salida],
        capture_output=True, text=True, cwd=REPO, timeout=300,
    )
    if proc.returncode != 0:
        print(proc.stdout[-3000:])
        print(proc.stderr[-3000:])
        check(f"la corrida {modo} termina sin error", False,
              f"-> codigo {proc.returncode}")
        resultados[modo] = None
        continue
    check(f"la corrida {modo} termina sin error", True)
    with open(salida) as f:
        resultados[modo] = json.load(f)
    print(f"         {proc.stdout.strip().splitlines()[-1]}")

off, obs = resultados.get("OFF"), resultados.get("OBSERVE")

if off and obs:
    # Lo primero: que el ciclo haya hecho ALGO. Si no hubo ni una
    # senal, las dos corridas serian identicas por vacias y la prueba
    # pasaria sin probar nada.
    check("el ciclo genero senales (si no, la prueba no probaria nada)",
          len(off["signals"] or []) > 0,
          f"-> {len(off['signals'] or [])} senales")
    check("el ciclo abrio alguna operacion",
          len(off["paper_trades"] or []) > 0,
          f"-> {len(off['paper_trades'] or [])} operaciones")

    for tabla in ("signals", "paper_trades", "paper_state", "risk_events"):
        iguales = off[tabla] == obs[tabla]
        check(f"OBSERVE no cambia la tabla {tabla}", iguales,
              f"-> OFF {len(off[tabla] or [])} filas vs "
              f"OBSERVE {len(obs[tabla] or [])} filas")
        if not iguales and off[tabla] and obs[tabla]:
            for i, (a, b) in enumerate(zip(off[tabla], obs[tabla])):
                if a != b:
                    print(f"         primera diferencia en fila {i}:")
                    for k in a:
                        if a.get(k) != b.get(k):
                            print(f"           {k}: OFF={a.get(k)!r} "
                                  f"OBSERVE={b.get(k)!r}")
                    break

    iguales = off["decisiones"] == obs["decisiones"]
    check("OBSERVE no cambia ni una linea del log de decisiones", iguales,
          f"-> OFF {len(off['decisiones'])} lineas vs "
          f"OBSERVE {len(obs['decisiones'])} lineas")
    if not iguales:
        solo_off = [l for l in off["decisiones"] if l not in obs["decisiones"]]
        solo_obs = [l for l in obs["decisiones"] if l not in off["decisiones"]]
        for l in solo_off[:5]:
            print(f"         solo en OFF:     {l[:110]}")
        for l in solo_obs[:5]:
            print(f"         solo en OBSERVE: {l[:110]}")

    # Y lo contrario: que OBSERVE si haya observado. Si la tabla sale
    # vacia, los modulos no corrieron y la igualdad de arriba es
    # trivial.
    # La exclusion de columnas tiene que ser la MISMA en las dos
    # corridas y contener solo columnas de reloj. Si no se comprueba,
    # la exclusion podria estar tapando una diferencia real.
    # Solo las tablas del NUCLEO: la de observacion existe unicamente
    # en OBSERVE, y eso es justo lo que tiene que diferir.
    TABLAS_NUCLEO = ("signals", "paper_trades", "paper_state", "risk_events")
    excl_off = {t: (off.get("columnas_excluidas") or {}).get(t)
                for t in TABLAS_NUCLEO}
    excl_obs = {t: (obs.get("columnas_excluidas") or {}).get(t)
                for t in TABLAS_NUCLEO}
    check("las dos corridas excluyen exactamente las mismas columnas",
          excl_off == excl_obs, f"-> OFF {excl_off} vs OBSERVE {excl_obs}")
    todas_excluidas = sorted({c for cols in
                              (off.get("columnas_excluidas") or {}).values()
                              for c in cols})
    print(f"         columnas excluidas de la comparacion (reloj e id): "
          f"{todas_excluidas}")
    check("solo se excluyen columnas de reloj o de id",
          all(("time" in c.lower() or "_at" in c.lower()
               or c.lower().startswith(("fecha", "hora")) or c == "id")
              for c in todas_excluidas),
          f"-> {todas_excluidas}")

    check("en OFF no se registra ninguna observacion",
          off["observacion_filas"] == 0, f"-> {off['observacion_filas']}")
    check("en OBSERVE SI se registran observaciones (si no, no corrio)",
          obs["observacion_filas"] > 0, f"-> {obs['observacion_filas']}")
    if obs.get("ta_sustituida"):
        print("         (nota: `ta` no estaba instalada, se uso el "
              "sustituto de tests/_ta_stub.py)")


# =====================================================================
print("\n=== 2) En OBSERVE no bloquea con NINGUNA combinacion ===")
# =====================================================================

from institucional import configuracion as CFG
from institucional import contratos as C
from institucional import observacion as OBSV

# Que no escriba en ninguna base real durante este barrido.
OBSV.registrar = lambda *a, **k: None


class ModuloFalso:
    """Devuelve la evaluacion que se le diga, para barrer combinaciones."""

    def __init__(self, estado, permite):
        self.estado = estado
        self.permite = permite

    def __call__(self, *a, **k):
        ahora = 1_700_000_000
        return C.ContextAssessment(
            base_signal_id="s", module_id="M02_trend_context",
            config_hash="h", dataset_version="v", as_of=ahora,
            valid_until=ahora + 1000, input_available_at_max=ahora,
            status=self.estado,
            allow_new_entry=self.permite if self.estado == C.READY else None,
        )


def df_minimo():
    idx = pd.date_range("2026-01-01", periods=300, freq="30min", tz="UTC")
    c = pd.Series([100 + (i % 11) for i in range(300)], index=idx)
    return pd.DataFrame({"Open": c, "High": c * 1.01, "Low": c * 0.99,
                         "Close": c, "Volume": 1e6}, index=idx)


ext_observe = CFG.validar(CFG.DEFECTO, CFG.capacidades_reales())
ext_enforce = CFG.validar(
    {**CFG.DEFECTO["institutional_extension"], "mode": "ENFORCE",
     "modules": {**CFG.DEFECTO["institutional_extension"]["modules"],
                 "M02_trend_context": {"enabled": True, "enforce": True}}},
    CFG.capacidades_reales())

estados = (C.READY, C.NO_DATA, C.STALE, C.UNSUPPORTED)
combinaciones = list(itertools.product(estados, (True, False)))

_m02_original = OBSV.M.m02_contexto
bloqueos_observe = []
bloqueos_enforce = []
try:
    for estado, permite in combinaciones:
        OBSV.M.m02_contexto = ModuloFalso(estado, permite)
        for ext, acumulador in ((ext_observe, bloqueos_observe),
                                (ext_enforce, bloqueos_enforce)):
            bloquear, _ = OBSV.evaluar(
                ticker="AAA", df=df_minimo(), signal="BUY", regime="TREND",
                base_signal_id="s", extension=ext,
                series_tr={"AAA": df_minimo()}, serie_efectivo=df_minimo(),
                decision_time=pd.Timestamp("2026-06-01", tz="UTC"),
            )
            acumulador.append((estado, permite, bloquear))
finally:
    OBSV.M.m02_contexto = _m02_original

check(f"OBSERVE no bloqueo en ninguna de las {len(combinaciones)} "
      f"combinaciones",
      not any(b for _, _, b in bloqueos_observe),
      f"-> bloqueo en {[(e, p) for e, p, b in bloqueos_observe if b]}")

# El contrapunto: en ENFORCE SI tiene que bloquear cuando toca. Si no
# bloqueara nunca, la prueba de arriba no demostraria nada.
esperados = [(e, p) for e, p in combinaciones
             if e != C.READY or p is False]
reales = [(e, p) for e, p, b in bloqueos_enforce if b]
check("ENFORCE si bloquea cuando el modulo dice que no o no sabe",
      sorted(reales) == sorted(esperados),
      f"-> esperados {len(esperados)}, reales {len(reales)}")

off_ext = CFG.validar({**CFG.DEFECTO["institutional_extension"],
                       "mode": "OFF"}, CFG.capacidades_reales())
bloquear, evs = OBSV.evaluar(
    ticker="AAA", df=df_minimo(), signal="BUY", regime="TREND",
    base_signal_id="s", extension=off_ext,
    decision_time=pd.Timestamp("2026-06-01", tz="UTC"))
check("en OFF no evalua nada y no bloquea",
      bloquear is False and evs == [])

bloquear, evs = OBSV.evaluar(
    ticker="AAA", df=df_minimo(), signal="BUY", regime="TREND",
    base_signal_id="s", extension=None,
    decision_time=pd.Timestamp("2026-06-01", tz="UTC"))
check("sin extension configurada no bloquea", bloquear is False)


# =====================================================================
print("\n=== 3) Datos basura: un modulo que revienta no es un veto ===")
# =====================================================================

basura = [
    ("DataFrame vacio", pd.DataFrame()),
    ("sin columnas", pd.DataFrame({"X": [1, 2, 3]})),
    ("con NaN", pd.DataFrame({
        "Open": [float("nan")] * 5, "High": [float("nan")] * 5,
        "Low": [float("nan")] * 5, "Close": [float("nan")] * 5,
        "Volume": [0.0] * 5},
        index=pd.date_range("2026-01-01", periods=5, freq="D", tz="UTC"))),
    ("una sola vela", df_minimo().iloc[:1]),
    ("indice sin tz", df_minimo().tz_localize(None)),
]

for nombre, df_malo in basura:
    try:
        bloquear, evs = OBSV.evaluar(
            ticker="AAA", df=df_malo, signal="BUY", regime="TREND",
            base_signal_id="s", extension=ext_observe,
            series_tr={"AAA": df_malo}, serie_efectivo=df_malo,
            decision_time=pd.Timestamp("2026-06-01", tz="UTC"))
        sin_veto = bloquear is False
        sin_opinion = all(e.allow_new_entry is None
                          for e in evs if e.status != C.READY)
        check(f"{nombre}: no lanza, no bloquea, no opina",
              sin_veto and sin_opinion,
              f"-> bloquear={bloquear} estados="
              f"{[e.status for e in evs]}")
    except Exception as e:
        check(f"{nombre}: no lanza, no bloquea, no opina", False,
              f"-> lanzo {type(e).__name__}: {e}")

# Y en ENFORCE, datos basura SI bloquean: no tener datos no es permiso.
bloquear, _ = OBSV.evaluar(
    ticker="AAA", df=pd.DataFrame(), signal="BUY", regime="TREND",
    base_signal_id="s", extension=ext_enforce,
    series_tr={}, serie_efectivo=None,
    decision_time=pd.Timestamp("2026-06-01", tz="UTC"))
check("en ENFORCE, no tener datos bloquea (no es un permiso implicito)",
      bloquear is True, f"-> {bloquear}")


print("\n" + "=" * 62)
print(f"RESULTADO: {OK} pruebas pasadas, {len(FALLOS)} fallos")
for f in FALLOS:
    print(f"  - {f}")
print("=" * 62)

sys.exit(1 if FALLOS else 0)
