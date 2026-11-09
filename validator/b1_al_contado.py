"""
B1 POR EL LIBRO DE CAJA CORREGIDO — la medicion que faltaba.

Lo que Astra dejo pendiente en su primera auditoria y seguia sin hacer:
"Experimento del Shark al contado: conectar las senales de B1 al ejecutor
corregido como variante separada e identificada."

## Por que hacia falta

Las cifras publicadas de B1 salen de `shark_v15_backtester.py`, que lleva
su propia contabilidad y tiene los mismos dos defectos que tenia la ruta
viva antes de arreglarla:

1. **No descuenta el nominal.** Hace `entry_cost = precio * coste * size`
   y `capital -= entry_cost`: cobra la comision pero NUNCA resta el
   dinero que queda inmovilizado en la posicion. El capital no refleja lo
   que hay comprado.
2. **No comprueba si cabe.** Nadie pregunta si el nominal entra en la
   cuenta, asi que puede abrir posiciones que no se podrian pagar.
3. **Un capital por activo.** `run_v16_backtest_single_asset` arranca
   cada activo con su propio capital y `print_consolidated` SUMA los
   resultados. Con cuatro activos a 1.000, el capital desplegado son
   4.000, no 1.000.

Aqui se corre la MISMA senal --`check_signal`, el escaner, los filtros y
el motor de decision final, importados tal cual-- pero cada orden pasa
por `CuentaContado`: caja real compartida entre todos los activos, lotes
enteros, admision antes de escribir y las dos comisiones cobradas en su
propio fill.

## Lo que esta medicion NO es

- **No es el marco temporal del bot.** El bot corre en velas de 30
  minutos y yfinance solo da ~60 dias de ese intervalo. Esto es DIARIO,
  15 anos. Es otra pregunta, con mucha mas muestra.
- **No es el universo del bot.** De sus cuatro activos (IWM, NVDA, AMZN,
  META) el panel guardado solo tiene IWM. Aqui corre sobre los 32 ETF del
  panel.
- **El filtro de IA esta simulado**, igual que en el backtester original:
  `_simulate_ai_result` devuelve un valor fijo. El filtro real necesita
  llamadas a una API. Eso esta declarado alli y se conserva aqui.

Asi que esto mide la LOGICA de B1 con contabilidad correcta sobre datos
reales. No predice lo que hara el bot en su marco. Decirlo al principio
es mas util que ponerlo en una nota al pie.

Uso:  python validator/b1_al_contado.py
"""
import io
import json
import os
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)
sys.path.insert(0, os.path.join(REPO, "tests"))
os.environ.setdefault("TELEGRAM_TOKEN", "")
os.environ.setdefault("CAPITAL", "1000")

import types
sys.modules.setdefault("yfinance", types.ModuleType("yfinance"))
try:
    import _ta_stub
    _ta_stub.instalar_si_falta()
except Exception:
    pass

import numpy as np
import pandas as pd

from indicators import add_indicators
from market_regime import detect_market_regime
from signals import check_signal
from opportunity_scanner import scan_smart_opportunity
from risk_management import calculate_trade_levels
from session_volatility_intelligence import (evaluate_session_filter,
                                             evaluate_volatility_filter)
from final_decision_engine import evaluate_final_decision
from paper_broker import _decidir_cierre
from libro import comision_explicita
from validator.shark_v15_backtester import (_simulate_ai_result,
                                            _simulate_context_result,
                                            _simulate_risk_result)
from cuenta_contado import CuentaContado
from config import COSTE_POR_PATA, RISK_PER_TRADE

PANEL = os.path.join(REPO, "resultados/v2/prices_snapshot.csv")
CALENTAMIENTO = 250
MAX_ABIERTAS = 2          # igual que MAX_OPEN_TRADES del bot
VARIANTE = "B1_AL_CONTADO_diario_v1"
# 0 = sin filtro (comportamiento actual del bot). >0 = exigir que el
# objetivo supere ese multiplo del coste de ida y vuelta.
MULTIPLO_VIABILIDAD = float(os.environ.get("B1_VIABILIDAD", "0") or 0)


def cargar(ruta):
    d = pd.read_csv(ruta, parse_dates=["fecha"])
    salida = {}
    for t, g in d.groupby("instrumento"):
        df = g.set_index("fecha").sort_index()[
            ["Open", "High", "Low", "Close", "Volume"]]
        if len(df) > CALENTAMIENTO + 50:
            salida[t] = df
    return salida


def correr(coste_rel, coste_minimo, capital=1000.0, etiqueta="",
           series=None):
    # `series` inyectable: el mismo motor de medicion vale para el panel
    # de 32 ETFs del snapshot y para el panel REAL del bot en vivo
    # (IWM, NVDA, AMZN, META), que se descarga en otro validador. Sin
    # esto habria que duplicar el motor, y entonces las dos mediciones ya
    # no serian comparables.
    if series is None:
        series = cargar(PANEL)
    con_ind = {}
    for t, df in series.items():
        try:
            con_ind[t] = add_indicators(df.copy())
        except Exception as e:
            print(f"  (sin indicadores para {t}: {type(e).__name__})")
    fechas = sorted(set().union(*[set(df.index) for df in con_ind.values()]))

    tmp = tempfile.mkdtemp(prefix="b1contado_")
    c = CuentaContado(os.path.join(tmp, "c.sqlite"), moneda="USD", lote=1.0,
                      permitir_fraccionado=False, dias_liquidacion=0)
    c.arrancar(capital, motivo=f"{VARIANTE} {etiqueta}")

    abiertas: dict = {}
    operaciones: list = []
    senales = permitidas = bloqueadas = no_admitidas = 0
    # Desglose: 'no admitida' agrupaba causas muy distintas y eso
    # escondia que la mayoria son VENTAS que una cuenta al contado no
    # puede ejecutar (cantidad >= 0, sin cortos).
    motivos_no_adm: dict = {}
    def _na(causa):
        motivos_no_adm[causa] = motivos_no_adm.get(causa, 0) + 1
    fallos: dict = {}
    nav_diario: dict = {}
    n_orden = 0

    for i, fecha in enumerate(fechas):
        if i < CALENTAMIENTO:
            continue
        precios_hoy = {}

        # --- cierres primero: liberan caja para las entradas de hoy ---
        for t in list(abiertas):
            df = con_ind.get(t)
            if df is None or fecha not in df.index:
                continue
            fila = df.loc[fecha]
            pos = abiertas[t]
            cerrar, precio_salida, motivo = _decidir_cierre(
                pos["signal"], pos["stop_loss"], pos["take_profit"],
                float(fila["Close"]), float(fila["High"]), float(fila["Low"]),
                open_=float(fila["Open"]))
            if not cerrar:
                continue
            n_orden += 1
            oid = f"sell-{n_orden}"
            inv = c.cantidad(t)
            if inv <= 0:
                abiertas.pop(t, None)
                continue
            adm = c.admitir(order_id=oid, instrumento=t, lado="SELL",
                            cantidad=min(pos["cantidad"], inv),
                            precio=precio_salida, coste_rel=coste_rel,
                            coste_minimo=coste_minimo)
            if not adm["admitida"]:
                no_admitidas += 1
                continue
            r = c.aplicar_fill(event_id=f"f-{oid}", order_id=oid,
                               instrumento=t, lado="SELL",
                               cantidad=adm["cantidad"], precio=precio_salida,
                               coste_rel=coste_rel, coste_minimo=coste_minimo,
                               momento=str(fecha), motivo=motivo)
            if not r.get("aplicado"):
                no_admitidas += 1
                continue
            bruto = (precio_salida - pos["entrada"]) * adm["cantidad"]
            riesgo = abs(pos["entrada"] - pos["stop_loss"]) * adm["cantidad"]
            # La comision de la pierna de venta con la MISMA formula que
            # cobra la cuenta, no una estimacion mia.
            com_venta = comision_explicita(
                precio_salida * adm["cantidad"], coste_rel=coste_rel,
                coste_fijo=0.0, coste_minimo=coste_minimo)
            com_compra = float(pos.get("comision", 0.0))
            neto = bruto - com_venta - com_compra
            operaciones.append({
                "instrumento": t, "entrada": pos["entrada"],
                "salida": precio_salida, "cantidad": adm["cantidad"],
                "pnl_bruto": bruto, "motivo": motivo,
                "comision_compra": com_compra, "comision_venta": com_venta,
                "pnl_neto": neto,
                "R_bruto": (bruto / riesgo) if riesgo > 0 else None,
                "R_neto": (neto / riesgo) if riesgo > 0 else None,
                "abierta_en": str(pos["fecha"]), "cerrada_en": str(fecha),
                "conviccion": pos.get("conviccion", {}),
            })
            abiertas.pop(t, None)

        # --- entradas ---
        for t in sorted(con_ind):
            df = con_ind[t]
            if fecha not in df.index:
                continue
            fila = df.loc[fecha]
            precios_hoy[t] = float(fila["Close"])
            if t in abiertas or len(abiertas) >= MAX_ABIERTAS:
                continue
            hasta = df.loc[:fecha]
            if len(hasta) < CALENTAMIENTO:
                continue
            try:
                regimen = detect_market_regime(hasta)
                base = check_signal(hasta)
                senal = base
                if base == "NO_SIGNAL":
                    info = scan_smart_opportunity(hasta)
                    if info.get("signal") in ("BUY", "SELL"):
                        senal = info["signal"]
                if senal not in ("BUY", "SELL"):
                    continue
                senales += 1
                context_result_cache = _simulate_context_result()
                final = evaluate_final_decision(
                    ai_result=_simulate_ai_result(),
                    context_result=context_result_cache,
                    session_result=evaluate_session_filter(hasta, regimen),
                    volatility_result=evaluate_volatility_filter(hasta, regimen),
                    risk_result=_simulate_risk_result(),
                    adx=float(fila["adx"]), regime=regimen, data=hasta,
                    ticker=t)
                if final.get("decision") != "ALLOW":
                    bloqueadas += 1
                    continue
                permitidas += 1
                if senal == "SELL":
                    # Cuenta al contado: un SELL sin inventario no abre
                    # corto. Se cuenta como permitida y no ejecutable.
                    no_admitidas += 1
                    _na("SELL sin inventario (cuenta al contado, sin cortos)")
                    continue
                setup = calculate_trade_levels(
                    df=hasta, signal=senal, capital=capital,
                    risk_per_trade=RISK_PER_TRADE,
                    efectivo_disponible=c.efectivo_utilizable,
                    coste_rel=coste_rel)
                # FILTRO DE VIABILIDAD ECONOMICA.
                #
                # 180 de 413 operaciones que tocaron su take-profit
                # perdieron dinero igualmente: el objetivo era MENOR que la
                # comision de ida y vuelta. 179 de ellas eran BIL, un fondo
                # de letras del Tesoro cuyo recorrido entero es mas pequeno
                # que el coste de operarlo.
                #
                # Esto NO es "evitar ADX alto porque perdio", que seria
                # sobreajuste. Es una condicion comprobable ANTES de abrir y
                # sin ver el resultado: si el objetivo no supera el coste, la
                # operacion no puede ganar dinero. El ratio es casi
                # invariante al tamano, porque comision y beneficio son
                # ambos proporcionales a la cantidad.
                objetivo = abs(float(setup["take_profit"])
                               - float(setup["entry"]))
                cant_prev = float(setup.get("position_size", 0) or 0)
                if MULTIPLO_VIABILIDAD > 0 and cant_prev > 0:
                    ganancia = objetivo * cant_prev
                    coste_ida_vuelta = (
                        comision_explicita(float(setup["entry"]) * cant_prev,
                                           coste_rel, 0.0, coste_minimo)
                        + comision_explicita(
                            float(setup["take_profit"]) * cant_prev,
                            coste_rel, 0.0, coste_minimo))
                    if ganancia < MULTIPLO_VIABILIDAD * coste_ida_vuelta:
                        no_admitidas += 1
                        _na("objetivo no supera el coste de ida y vuelta")
                        continue
                cant = float(setup.get("position_size", 0) or 0)
                if cant <= 0:
                    no_admitidas += 1
                    _na("tamano calculado 0 (riesgo/lote/caja)")
                    continue
                n_orden += 1
                oid = f"buy-{n_orden}"
                adm = c.admitir(order_id=oid, instrumento=t, lado="BUY",
                                cantidad=cant, precio=float(setup["entry"]),
                                coste_rel=coste_rel, coste_minimo=coste_minimo)
                if not adm["admitida"]:
                    no_admitidas += 1
                    # La causa se normaliza a una etiqueta ESTABLE. Meter
                    # la cantidad dentro hacia que cada rechazo fuera una
                    # causa distinta y el desglose no agrupaba nada.
                    m = str(adm.get("motivo", "?"))
                    if "lote" in m:
                        causa = ("compra rechazada: el tamano por riesgo no "
                                 "llega a 1 participacion entera")
                    elif "no cabe" in m:
                        causa = "compra rechazada: no cabe en la caja utilizable"
                    else:
                        causa = f"compra rechazada: {m[:40]}"
                    _na(causa)
                    continue
                r = c.aplicar_fill(event_id=f"f-{oid}", order_id=oid,
                                   instrumento=t, lado="BUY",
                                   cantidad=adm["cantidad"],
                                   precio=float(setup["entry"]),
                                   coste_rel=coste_rel,
                                   coste_minimo=coste_minimo,
                                   momento=str(fecha), motivo=f"{VARIANTE}")
                if not r.get("aplicado"):
                    no_admitidas += 1
                    continue
                # Scores de la decision al ENTRAR. Sirven para contestar
                # la pregunta que decide el tamano variable: predice la
                # conviccion el resultado? Si no, variar el tamano solo
                # anade varianza.
                # OJO: ai_score viene del simulador, es constante y NO
                # informa. Los demas son reales.
                abiertas[t] = {
                    "conviccion": {
                        "puntuacion_final": final.get("score"),
                        "motivo": str(final.get("reason", ""))[:40],
                        "adx": float(fila["adx"]),
                        "regimen": regimen,
                    },
                    "signal": senal, "entrada": float(setup["entry"]),
                    "stop_loss": float(setup["stop_loss"]),
                    "take_profit": float(setup["take_profit"]),
                    "cantidad": adm["cantidad"], "fecha": fecha,
                    "comision": comision_explicita(
                        float(setup["entry"]) * adm["cantidad"],
                        coste_rel=coste_rel, coste_fijo=0.0,
                        coste_minimo=coste_minimo),
                }
            except Exception as e:
                # NO se tragan los errores. Un `except: continue` aqui me
                # dio una corrida con 15.539 senales permitidas y CERO
                # operaciones, con el NAV clavado en 1000,00, y lo presente
                # como si fuera un resultado. Es el mismo patron que las
                # auditorias ya me cazaron: la evidencia perdida en
                # silencio parece un dato.
                fallos[f"{type(e).__name__}: {str(e)[:70]}"] = (
                    fallos.get(f"{type(e).__name__}: {str(e)[:70]}", 0) + 1)
                continue

        nav = c.nav(precios_hoy)
        if nav.get("evaluable"):
            nav_diario[fecha] = nav["nav"]

    serie = pd.Series(nav_diario).sort_index()
    pnls = [o["pnl_bruto"] for o in operaciones]
    netos = [o["pnl_neto"] for o in operaciones]
    comisiones = sum(o["comision_compra"] + o["comision_venta"]
                     for o in operaciones)
    rs = [o["R_bruto"] for o in operaciones if o["R_bruto"] is not None]
    rs_netas = [o["R_neto"] for o in operaciones if o["R_neto"] is not None]
    anos = (serie.index[-1] - serie.index[0]).days / 365.25 if len(serie) > 1 else 0
    nav_final = float(serie.iloc[-1]) if len(serie) else capital
    cagr = (nav_final / capital) ** (1 / anos) - 1 if anos > 0 and nav_final > 0 else None
    est = c.estado()
    return {
        "variante": VARIANTE, "etiqueta": etiqueta,
        "coste_rel": coste_rel, "coste_minimo": coste_minimo,
        "operaciones": len(operaciones),
        "senales": senales, "permitidas": permitidas,
        "bloqueadas": bloqueadas, "no_admitidas": no_admitidas,
        "no_admitidas_por_causa": motivos_no_adm,
        "esperanza_por_operacion": (sum(pnls) / len(pnls)) if pnls else None,
        "esperanza_en_R": (sum(rs) / len(rs)) if rs else None,
        "esperanza_neta_por_operacion": (sum(netos) / len(netos)) if netos else None,
        "esperanza_neta_en_R": (sum(rs_netas) / len(rs_netas)) if rs_netas else None,
        "comisiones_totales": comisiones,
        "comision_media_ida_y_vuelta": (comisiones / len(operaciones)) if operaciones else None,
        "pnl_bruto_total": sum(pnls), "pnl_neto_total": sum(netos),
        "ganadoras": sum(1 for p in pnls if p > 0),
        "perdedoras": sum(1 for p in pnls if p <= 0),
        "ganadoras_netas": sum(1 for p in netos if p > 0),
        "perdedoras_netas": sum(1 for p in netos if p <= 0),
        "nav_final": nav_final, "cagr": cagr, "anos": round(anos, 2),
        "caja_final": est.get("efectivo"),
        "fallos_en_entrada": fallos,
        "posiciones_abiertas_al_final": len(abiertas),
        "_nav": serie, "_operaciones": operaciones,
    }


def main():
    # BARRIDO DE COSTE. La pregunta que decide si esta estrategia sirve no
    # es "cuanto gana" sino "por debajo de que coste por pata deja de
    # perder". La esperanza BRUTA por operacion es fija; el coste la come.
    # Un unico escenario no contesta eso, un barrido si.
    if os.environ.get("B1_BARRIDO") == "1":
        escenarios = [
            ("0pb_suelo_irreal", 0.0, 0.0),
            ("1pb_por_pata", 0.0001, 0.0),
            ("2pb_por_pata", 0.0002, 0.0),
            ("3pb_por_pata", 0.0003, 0.0),
            ("5pb_por_pata", 0.0005, 0.0),
            ("8pb_por_pata", 0.0008, 0.0),
            ("15pb_por_pata_divisa_T212", 0.0015, 0.0),
        ]
    else:
        escenarios = [
            ("8pb_proporcional", COSTE_POR_PATA, 0.0),
            ("8pb_con_minimo_0_50", COSTE_POR_PATA, 0.50),
        ]
    if MULTIPLO_VIABILIDAD > 0:
        escenarios = [(f"{e}__viab_{MULTIPLO_VIABILIDAD:g}x", a, b)
                      for e, a, b in escenarios]
    salida = {"variante": VARIANTE, "panel": PANEL, "resultados": {}}
    for etq, c_rel, c_min in escenarios:
        print(f"\n{'='*74}\n{etq}\n{'='*74}")
        r = correr(c_rel, c_min, 1000.0, etq)
        print(f"  senales {r['senales']} | permitidas {r['permitidas']} | "
              f"bloqueadas {r['bloqueadas']} | no admitidas {r['no_admitidas']}")
        for causa, n in sorted(r.get("no_admitidas_por_causa", {}).items(),
                               key=lambda kv: -kv[1]):
            print(f"      {n:>5}  {causa}")
        print(f"  operaciones cerradas: {r['operaciones']} "
              f"({r['ganadoras']} ganadoras / {r['perdedoras']} perdedoras)")
        e = r["esperanza_por_operacion"]
        er = r["esperanza_en_R"]
        en = r["esperanza_neta_por_operacion"]
        ern = r["esperanza_neta_en_R"]
        print(f"  esperanza BRUTA por operacion: "
              f"{('%+.4f' % e) if e is not None else '—'} USD   "
              f"({('%+.4f' % er) if er is not None else '—'} R)")
        print(f"  comision media ida y vuelta:   "
              f"{r['comision_media_ida_y_vuelta']:.4f} USD"
              if r['comision_media_ida_y_vuelta'] is not None else "  —")
        print(f"  esperanza NETA por operacion:  "
              f"{('%+.4f' % en) if en is not None else '—'} USD   "
              f"({('%+.4f' % ern) if ern is not None else '—'} R)")
        print(f"  aciertos brutos {r['ganadoras']}/{r['operaciones']} -> "
              f"netos {r['ganadoras_netas']}/{r['operaciones']}")
        print(f"  PnL bruto {r['pnl_bruto_total']:+.2f} - comisiones "
              f"{r['comisiones_totales']:.2f} = neto "
              f"{r['pnl_neto_total']:+.2f} USD")
        print(f"  NAV final: {r['nav_final']:.2f} desde 1000 en "
              f"{r['anos']} anos")
        print(f"  CAGR: "
              f"{('%.4f%%' % (r['cagr']*100)) if r['cagr'] is not None else '—'}")
        # RECONCILIACION. Si esto no cuadra, las dos cifras de arriba no
        # describen la misma corrida y ninguna vale.
        var_nav = r["nav_final"] - 1000.0
        residuo = var_nav - r["pnl_neto_total"]
        print(f"  reconciliacion: variacion del NAV {var_nav:+.4f} - PnL "
              f"neto cerrado {r['pnl_neto_total']:+.4f} = {residuo:+.4f}")
        print(f"     (el residuo son las {r['posiciones_abiertas_al_final']} "
              f"posiciones abiertas al final, marcadas a mercado)")
        if r.get("fallos_en_entrada"):
            print(f"  FALLOS EN LA ENTRADA (no son un resultado, son un "
                  f"fallo mio):")
            for m, n in sorted(r["fallos_en_entrada"].items(),
                               key=lambda kv: -kv[1])[:6]:
                print(f"    {n:>7} x  {m}")
        limpio = {k: v for k, v in r.items() if not k.startswith("_")}
        # TODAS las operaciones en la medicion BASE, no las 200 primeras.
        # Con 200 la prueba de conviccion no tiene potencia: rho = -0,08
        # da p = 0,24 con n=200 y p ~ 0,04 con n=636. El truncamiento
        # decidia la conclusion, que es exactamente lo que no debe pasar.
        #
        # En el BARRIDO no se volca el detalle: son 7 escenarios que
        # comparten casi toda la estructura, y volcarlos todos dio un
        # fichero de 3,1 MB con 4.229 operaciones que se commitea en cada
        # corrida del CI. El detalle sirve para condicionar por
        # instrumento --asi se encontro lo de BIL-- y eso se hace sobre la
        # base. Del barrido lo que se quiere son los agregados, mas un
        # resumen por instrumento que cabe en unas lineas.
        if os.environ.get("B1_BARRIDO") == "1":
            porinst: dict = {}
            for o in r["_operaciones"]:
                a = porinst.setdefault(o["instrumento"],
                                       {"n": 0, "neto": 0.0, "ganadoras": 0})
                a["n"] += 1
                a["neto"] += o["pnl_neto"]
                a["ganadoras"] += 1 if o["pnl_neto"] > 0 else 0
            limpio["resumen_por_instrumento"] = porinst
        else:
            limpio["operaciones_detalle"] = r["_operaciones"]
        salida["resultados"][etq] = limpio
    if os.environ.get("B1_BARRIDO") == "1":
        # El barrido y el filtro se combinan: hay que saber que da el
        # mejor coste CON el filtro puesto, no solo cada uno por separado.
        nombre = ("b1_barrido_coste.json" if MULTIPLO_VIABILIDAD <= 0 else
                  f"b1_barrido_coste_viab_{MULTIPLO_VIABILIDAD:g}x.json")
    elif MULTIPLO_VIABILIDAD > 0:
        nombre = f"b1_viabilidad_{MULTIPLO_VIABILIDAD:g}x.json"
    else:
        nombre = "b1_al_contado.json"
    destino = os.path.join(REPO, "resultados/v3", nombre)
    io.open(destino, "w", encoding="utf-8").write(
        json.dumps(salida, indent=2, default=str))
    print(f"\nguardado {destino}")


if __name__ == "__main__":
    main()
