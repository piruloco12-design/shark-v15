"""Las tres estrategias publicadas, medidas sobre el panel real guardado.

ESTADO: EXPLORATORIO. Este panel se ha mirado muchas veces, con varias
versiones del motor. Estas cifras son DESCRIPTIVAS, no una prueba
confirmatoria, y ningun nombre nuevo las convierte en otra cosa.

Dos escenarios de coste, con los nombres correctos:
  8 pb proporcional, sin minimo   -> el declarado del proyecto
  8 pb + minimo 0,50 por orden    -> max(0,50; 0,0008*N), el caso de
                                     minorista con cuenta pequena
"""
import os, sys, types, json, io
REPO = "/home/claude/shark-v15"
sys.path.insert(0, REPO); sys.path.insert(0, os.path.join(REPO, "tests"))
os.environ.setdefault("TELEGRAM_TOKEN", ""); os.environ.setdefault("CAPITAL", "1000")
sys.modules.setdefault("yfinance", types.ModuleType("yfinance"))
import _ta_stub; _ta_stub.instalar_si_falta()

from evaluador.experimento import (cargar_panel, RENTA_VARIABLE, MULTIACTIVO,
                                   TICKER_EFECTIVO, K, LOOKBACK, SKIP)
from evaluador.mensual import (EvaluadorMensual, Politicas, ComprarYMantener,
                               M03Momentum)
from estrategias_publicadas import (FaberTiempoMercado, AntonacciDobleMomento,
                                    ParidadRiesgoInversa)

PANEL = os.path.join(REPO, "resultados/v2/prices_snapshot.csv")
series = cargar_panel(PANEL)
efectivo = series.pop(TICKER_EFECTIVO, None)
print(f"panel: {len(series)} activos, "
      f"{len(next(iter(series.values())))} sesiones\n")

COSTES = [
    ("8pb_proporcional", 0.0008, 0.0, 0.0),
    ("8pb_con_minimo_0_50", 0.0008, 0.0, 0.50),
]
universos = {
    "multiactivo": {t: d for t, d in series.items() if t in MULTIACTIVO},
    "renta_variable": {t: d for t, d in series.items() if t in RENTA_VARIABLE},
}
salida = {"estado": "EXPLORATORIO", "panel": PANEL, "resultados": {}}

for etq_coste, c_rel, c_fijo, c_min in COSTES:
    print(f"{'='*78}\n{etq_coste}\n{'='*78}")
    for nombre_u, series_u in universos.items():
        pol = Politicas(capital_inicial=1000.0, coste_rel=c_rel,
                        coste_fijo=c_fijo, coste_minimo=c_min,
                        permitir_fraccionado=True, lote=0.0,
                        calentamiento_sesiones=253)
        ev = EvaluadorMensual(series_u, pol)
        ests = {
            "comprar_y_mantener": ComprarYMantener(),
            "M03_propia": M03Momentum(K, LOOKBACK, SKIP),
            "PUB_faber_sma10m": FaberTiempoMercado(10),
            "PUB_paridad_inversa": ParidadRiesgoInversa(63),
        }
        if efectivo is not None:
            ests["PUB_doble_momento"] = AntonacciDobleMomento(
                efectivo["Close"], k=K, lookback=LOOKBACK)
        print(f"\n--- {nombre_u} ---")
        ref = None
        filas = {}
        for clave, est in ests.items():
            try:
                r = ev.correr(est)
                filas[clave] = {
                    "cagr": r["cagr"], "retorno_total": r["retorno_total"],
                    "caida_maxima": r["max_drawdown_diario"],
                    "comisiones": r["comisiones_moneda"],
                    "intenciones": r["intenciones"],
                    "rechazadas": r["intenciones_rechazadas"],
                    "nav_final": r["nav_final"],
                    "nav_fiable": r.get("nav_fiable"),
                    "exposicion_media": (r.get("exposicion") or {}).get(
                        "exposicion_media_real"),
                }
            except Exception as e:
                filas[clave] = {"error": f"{type(e).__name__}: {str(e)[:70]}"}
        ref = filas.get("comprar_y_mantener", {}).get("cagr")
        print(f"  {'estrategia':<22} {'CAGR':>9} {'dif':>9} {'caida':>8} "
              f"{'comis':>8} {'exposic':>8}")
        for clave, v in filas.items():
            if "error" in v:
                print(f"  {clave:<22} {v['error']}")
                continue
            dif = (f"{(v['cagr']-ref)*100:+9.4f}"
                   if ref is not None and clave != "comprar_y_mantener"
                   else "        —")
            exp = v.get("exposicion_media")
            print(f"  {clave:<22} {v['cagr']*100:8.4f}% {dif} "
                  f"{v['caida_maxima']*100:7.2f}% {v['comisiones']:8.2f} "
                  f"{('—' if exp is None else f'{exp*100:7.2f}%')}")
        salida["resultados"][f"{etq_coste}/{nombre_u}"] = filas

io.open(os.path.join(REPO, "resultados/v3/estrategias_publicadas.json"), "w",
        encoding="utf-8").write(json.dumps(salida, indent=2, default=str))
print("\nguardado resultados/v3/estrategias_publicadas.json")
