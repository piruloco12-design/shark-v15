#!/usr/bin/env python3
"""
Genera dashboard/index.html a partir de los JSON de resultados.

Los datos se INCRUSTAN en el HTML en lugar de cargarse con fetch,
para que el fichero funcione abriendolo con doble clic. Un fetch a
un JSON local lo bloquea el navegador por CORS cuando la pagina
viene de file://, asi que un dashboard que cargue datos aparte solo
funcionaria levantando un servidor.

Si falta algun JSON, esa seccion sale como "sin datos" en vez de
romper la generacion.

    python dashboard/generar.py
"""

import json
import os
from datetime import datetime, timezone

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
RESULTADOS = os.path.join(RAIZ, "resultados")
SALIDA = os.path.join(AQUI, "index.html")


def leer(nombre):
    ruta = os.path.join(RESULTADOS, nombre)
    try:
        with open(ruta, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def leer_texto(nombre, maximo=200000):
    ruta = os.path.join(RESULTADOS, nombre)
    try:
        with open(ruta, encoding="utf-8") as f:
            return f.read()[:maximo]
    except Exception:
        return None


def main():
    datos = {
        "generado": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "clases": leer("clases.json"),
        "universo": leer("universo.json"),
        "robustez_1d": leer("robustez_1d.json"),
        "robustez_30m": leer("robustez_30m.json"),
        "crudo": {
            "proveedores": leer_texto("proveedores.txt"),
            "clases": leer_texto("experimento_clases.txt"),
            "universo": leer_texto("experimento_universo.txt"),
            "backtest_diario": leer_texto("backtest_diario.txt"),
            "backtest_intradia": leer_texto("backtest_intradia.txt"),
        },
    }

    presentes = [k for k in ("clases", "universo", "robustez_1d", "robustez_30m")
                 if datos[k]]
    print(f"Fuentes encontradas: {presentes or 'ninguna'}")

    with open(os.path.join(AQUI, "plantilla.html"), encoding="utf-8") as f:
        plantilla = f.read()

    # </script> dentro del JSON cerraria la etiqueta antes de tiempo.
    json_seguro = (json.dumps(datos, ensure_ascii=False, default=float)
                   .replace("</", "<\\/"))

    html = plantilla.replace("/*__DATOS__*/null", json_seguro)

    with open(SALIDA, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"Dashboard escrito en {SALIDA} ({len(html) / 1024:.0f} KB)")
    print("Abrelo con doble clic: no necesita servidor.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
