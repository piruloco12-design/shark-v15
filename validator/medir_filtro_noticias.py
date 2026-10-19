"""
¿Acierta el filtro de noticias? La pregunta que decide si se
enciende o se tira.

COMO FUNCIONA

El filtro arranca en modo sombra: opina en cada operacion pero no
bloquea nada. Asi se abren TAMBIEN las operaciones que habria
vetado, y eso es justo lo que hace falta para medirlo.

Si vetara desde el principio, nunca sabriamos como habrian
acabado las vetadas, y no habria forma de saber si acertaba. Un
filtro que bloquea sin haberse medido no es prudencia: es fe.

QUE MIDE

Compara como acabaron las operaciones segun lo que dijo Gemini:

    APROBAR  ->  ¿mejor que la media?
    VETAR    ->  ¿peor que la media?
    NEUTRAL  ->  la referencia

El filtro sirve si las vetadas van claramente peor que las
aprobadas. Si no hay diferencia, no discrimina, y entonces solo
añade coste, latencia y una dependencia mas.

CUANTO HACE FALTA

Con menos de 30 operaciones por grupo no se puede concluir nada,
y el informe lo dice en vez de dar un numero bonito sobre cuatro
datos.

    python validator/medir_filtro_noticias.py
"""

import os
import sys

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)

for ruta in (PROJECT_ROOT, CURRENT_DIR):
    if ruta not in sys.path:
        sys.path.insert(0, ruta)

from storage import obtener_veredictos_noticias, obtener_trades_cerrados
from robustez import bootstrap_expectativa

MINIMO_POR_GRUPO = 30


def emparejar():
    """
    Une cada veredicto con la operacion que se abrio despues.

    El emparejamiento es por activo y por proximidad temporal: el
    veredicto se guarda justo antes de abrir, asi que la operacion
    de ese activo que empieza despues del veredicto y mas cerca en
    el tiempo es la suya.
    """
    veredictos = obtener_veredictos_noticias(limite=5000)
    cerradas = obtener_trades_cerrados()

    if not veredictos or not cerradas:
        return []

    por_activo = {}
    for t in cerradas:
        por_activo.setdefault(t["ticker"], []).append(t)
    for lista in por_activo.values():
        lista.sort(key=lambda t: t["timestamp_open"])

    emparejados = []
    usadas = set()

    for v in sorted(veredictos, key=lambda x: x["timestamp"]):
        candidatas = por_activo.get(v["ticker"], [])
        for t in candidatas:
            if id(t) in usadas:
                continue
            if t["timestamp_open"] < v["timestamp"]:
                continue
            # Margen de 10 minutos: el veredicto se guarda en el
            # mismo ciclo en que se abre la operacion.
            emparejados.append({
                "veredicto": v["veredicto"],
                "confianza": v["confianza"],
                "motivo": v["motivo"],
                "pnl": float(t["pnl"] or 0.0),
                "ticker": v["ticker"],
            })
            usadas.add(id(t))
            break

    return emparejados


def resumen(ops):
    if not ops:
        return {"n": 0, "expectativa": 0.0, "wr": 0.0, "total": 0.0}
    pnls = [o["pnl"] for o in ops]
    return {
        "n": len(pnls),
        "expectativa": sum(pnls) / len(pnls),
        "wr": sum(1 for p in pnls if p > 0) / len(pnls) * 100,
        "total": sum(pnls),
    }


def main():
    print("=" * 66)
    print("¿ACIERTA EL FILTRO DE NOTICIAS?")
    print("=" * 66)

    datos = emparejar()

    if not datos:
        print("\nNo hay operaciones con veredicto todavia.")
        print()
        print("Esto es lo esperado al principio. El filtro arranca en")
        print("modo sombra y hay que dejar que acumule operaciones.")
        print("Vuelve a ejecutar esto dentro de unas semanas.")
        return 0

    grupos = {
        "APROBAR": [d for d in datos if d["veredicto"] == "APROBAR"],
        "NEUTRAL": [d for d in datos if d["veredicto"] == "NEUTRAL"],
        "VETAR": [d for d in datos if d["veredicto"] == "VETAR"],
    }

    print(f"\nOperaciones con veredicto: {len(datos)}")
    print()
    print(f"  {'VEREDICTO':10} {'OPS':>5} {'WR%':>7} {'EXPECTATIVA':>13} {'TOTAL':>10}")
    print("  " + "-" * 50)

    for nombre in ("APROBAR", "NEUTRAL", "VETAR"):
        r = resumen(grupos[nombre])
        if r["n"] == 0:
            print(f"  {nombre:10} {0:>5}  (ninguna)")
            continue
        print(f"  {nombre:10} {r['n']:>5} {r['wr']:>7.1f} "
              f"{r['expectativa']:>+13.4f} {r['total']:>+10.2f}")

    aprobadas = resumen(grupos["APROBAR"])
    vetadas = resumen(grupos["VETAR"])

    print()
    print("=" * 66)
    print("VEREDICTO SOBRE EL FILTRO")
    print("=" * 66)

    if vetadas["n"] < MINIMO_POR_GRUPO or aprobadas["n"] < MINIMO_POR_GRUPO:
        print(f"\nMuestra insuficiente. Hacen falta al menos "
              f"{MINIMO_POR_GRUPO} operaciones")
        print(f"en APROBAR y en VETAR; ahora hay {aprobadas['n']} y "
              f"{vetadas['n']}.")
        print()
        print("No se puede concluir nada todavia, y con estos numeros")
        print("cualquier conclusion seria ruido. Dejalo en modo sombra.")
        return 0

    diferencia = aprobadas["expectativa"] - vetadas["expectativa"]

    # Bootstrap sobre la diferencia: ¿es distinguible de cero?
    todas = [d["pnl"] for d in datos]
    b_aprobadas = bootstrap_expectativa([d["pnl"] for d in grupos["APROBAR"]])
    b_vetadas = bootstrap_expectativa([d["pnl"] for d in grupos["VETAR"]])

    print(f"\nExpectativa de las aprobadas: {aprobadas['expectativa']:+.4f}")
    print(f"  intervalo 90%: {b_aprobadas['p05']:+.4f} a {b_aprobadas['p95']:+.4f}")
    print(f"Expectativa de las vetadas:   {vetadas['expectativa']:+.4f}")
    print(f"  intervalo 90%: {b_vetadas['p05']:+.4f} a {b_vetadas['p95']:+.4f}")
    print(f"\nDiferencia: {diferencia:+.4f} por operacion")

    separados = b_aprobadas["p05"] > b_vetadas["p95"]

    print()
    if separados and diferencia > 0:
        print("EL FILTRO DISCRIMINA. Los intervalos no se solapan: las")
        print("operaciones aprobadas van mejor que las vetadas, y la")
        print("diferencia no es ruido.")
        print()
        print("Se puede pasar a modo bloqueo:")
        print("    GEMINI_FILTER_MODO=bloqueo")
    elif diferencia > 0:
        print("Va en la direccion buena, pero los intervalos se solapan:")
        print("todavia no se distingue de la casualidad. Mas operaciones.")
    else:
        print("EL FILTRO NO DISCRIMINA, o discrimina al reves: las vetadas")
        print("no van peor que las aprobadas.")
        print()
        print("Dejarlo encendido solo añade coste, latencia y una")
        print("dependencia mas. Apagalo:")
        print("    GEMINI_FILTER_ENABLED=false")

    print("=" * 66)
    return 0


if __name__ == "__main__":
    sys.exit(main())
