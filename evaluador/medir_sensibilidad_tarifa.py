"""Sensibilidad a la TARIFA, sobre el panel real guardado. Sin red.

La pregunta: el escenario declarado es 0,0008 por pata SIN minimo por
orden. Con 1.000 de capital y cinco posiciones, cada posicion son ~200, y
una comision minima de 1 por orden son 50 pb por pata sobre esa posicion,
no 8. Si la ventaja de +1,33 puntos de M03 en multiactivo no sobrevive a
una tarifa de minorista, el resultado no describe nada ejecutable.
"""
import os, sys, types, json, io
REPO = "/home/claude/shark-v15"
sys.path.insert(0, REPO); sys.path.insert(0, os.path.join(REPO, "tests"))
os.environ.setdefault("TELEGRAM_TOKEN", ""); os.environ.setdefault("CAPITAL", "1000")
sys.modules.setdefault("yfinance", types.ModuleType("yfinance"))
import _ta_stub; _ta_stub.instalar_si_falta()
import pandas as pd

from evaluador.experimento import (cargar_panel, RENTA_VARIABLE, MULTIACTIVO,
                                   TICKER_EFECTIVO, K, LOOKBACK, SKIP,
                                   VENTANA_VOL)
from evaluador.mensual import (EvaluadorMensual, Politicas, ComprarYMantener,
                               RebalanceoEquiponderado, M03Momentum,
                               M02Tendencia)

PANEL = os.path.join(REPO, "resultados/v2/prices_snapshot.csv")
series = cargar_panel(PANEL)
efectivo = series.pop(TICKER_EFECTIVO, None)
print(f"panel: {len(series)} activos, {len(next(iter(series.values())))} sesiones")

ESCENARIOS = [
    ("declarado_8pb_sin_minimo", 0.0008, 0.0),
    ("8pb_mas_minimo_0_50", 0.0008, 0.50),
    ("8pb_mas_minimo_1", 0.0008, 1.0),
    ("8pb_mas_minimo_2", 0.0008, 2.0),
    ("sin_coste", 0.0, 0.0),
]

universos = {
    "multiactivo": {t: d for t, d in series.items() if t in MULTIACTIVO},
    "renta_variable": {t: d for t, d in series.items() if t in RENTA_VARIABLE},
}

salida = {"panel": PANEL, "escenarios": {}}
for nombre, c_rel, c_fijo in ESCENARIOS:
    salida["escenarios"][nombre] = {"coste_rel": c_rel, "coste_fijo": c_fijo}
    print(f"\n=== {nombre}: {c_rel*10000:.1f} pb por pata + {c_fijo:.2f} fijo ===")
    for nombre_u, series_u in universos.items():
        pol = Politicas(capital_inicial=1000.0, coste_rel=c_rel,
                        coste_fijo=c_fijo, permitir_fraccionado=True, lote=0.0,
                        calentamiento_sesiones=253)
        ev = EvaluadorMensual(series_u, pol)
        ests = {"comprar_y_mantener": ComprarYMantener(),
                "M03_momentum_12_1": M03Momentum(K, LOOKBACK, SKIP)}
        if efectivo is not None:
            ests["M02_tendencia"] = M02Tendencia(efectivo["Close"], LOOKBACK,
                                                 VENTANA_VOL)
        fila = {}
        for clave, est in ests.items():
            try:
                r = ev.correr(est)
                fila[clave] = {
                    "cagr": r["cagr"],
                    "comisiones": r["comisiones_moneda"],
                    "intenciones": r["intenciones"],
                    "rechazadas": r["intenciones_rechazadas"],
                    "nav_final": r["nav_final"],
                }
            except Exception as e:
                fila[clave] = {"error": f"{type(e).__name__}: {str(e)[:80]}"}
        cym = fila.get("comprar_y_mantener", {}).get("cagr")
        for clave, v in fila.items():
            if "error" in v:
                print(f"  {nombre_u:15} {clave:22} {v['error']}")
                continue
            dif = (f"{(v['cagr']-cym)*100:+7.4f}"
                   if cym is not None and clave != "comprar_y_mantener" else "      —")
            print(f"  {nombre_u:15} {clave:22} CAGR {v['cagr']*100:7.4f}%  "
                  f"dif {dif}  comis {v['comisiones']:9.2f}  "
                  f"rech {v['rechazadas']:4}/{v['intenciones']}")
        salida["escenarios"][nombre][nombre_u] = fila

io.open(os.path.join(REPO, "resultados/v3/sensibilidad_tarifa.json"), "w",
        encoding="utf-8").write(json.dumps(salida, indent=2, default=str))
print("\nguardado resultados/v3/sensibilidad_tarifa.json")
