"""
Universo congelado: la lista se fija hoy y se sigue hacia delante.

POR QUE ES LO UNICO QUE QUITA LA SUPERVIVENCIA

Todo lo medido hasta ahora usa los ETF que existen HOY. Los que cerraron no
están, y eso infla los resultados por un camino que no se puede corregir sin
la lista verdadera de desaparecidos. Lo medí por escenarios y da entre +0,07
y +2,07 puntos de cambio en el diferencial, pero eso son escenarios
inventados, no el sesgo real.

Esto es distinto. Si la lista se fija HOY, con su fecha, y a partir de
mañana se sigue tal cual, entonces los que cierren el año que viene
**seguirán estando en la lista**. No se pueden quitar retrospectivamente
porque la lista se escribió antes de saber quién iba a cerrar.

Lo que NO arregla: no da potencia estadística en años, no elimina otros
sesgos, y no convierte en válido nada de lo ya medido. Es empezar el
cronómetro, no un atajo.

EL REGISTRO DE INSTRUMENTOS

Cada ticker congelado queda con su fecha de alta. En cada corrida se
comprueba si sigue dando datos. Si uno deja de darlos, se registra la fecha
en que se detectó y se marca como baja candidata, **sin quitarlo de la
lista**. Esa es la parte que importa: un activo que desaparece tiene que
seguir contando en el denominador, porque si se borra en silencio se ha
reinventado el sesgo de supervivencia dentro del propio sistema que
pretendía evitarlo.

Un ticker puede dejar de dar datos por tres motivos distintos y conviene no
confundirlos: cerró el fondo, cambió de ticker, o el proveedor falló. Los
tres se registran igual, como «sin datos desde», y resolverlos exige
mirarlo a mano. No se adivina.
"""

from __future__ import annotations

import hashlib
import json
import os
import time

RUTA_POR_DEFECTO = "universo_congelado.json"

VERSION = "2026-10-19.congelado.1"


class UniversoInvalido(RuntimeError):
    pass


def _hash_lista(tickers, fecha, regla) -> str:
    crudo = json.dumps({"t": sorted(tickers), "f": fecha, "r": regla},
                       sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(crudo.encode()).hexdigest()[:16]


def congelar(tickers, regla: str, *, ruta=RUTA_POR_DEFECTO,
             fecha=None, notas="") -> dict:
    """Escribe la lista congelada. Falla si ya existe: no se recongela.

    Recongelar sería volver a elegir mirando quién sobrevivió, que es
    exactamente el sesgo del que se huye. Para empezar otra serie, otro
    archivo con otro nombre y otra fecha.
    """
    if os.path.exists(ruta):
        existente = cargar(ruta)
        raise UniversoInvalido(
            f"ya hay un universo congelado el {existente['fecha_congelacion']} "
            f"con {len(existente['instrumentos'])} instrumentos (hash "
            f"{existente['hash']}). No se recongela: eso seria volver a "
            f"elegir sabiendo quien sobrevivio. Para una serie nueva, usa "
            f"otro archivo."
        )
    tickers = sorted(set(str(t).strip().upper() for t in tickers if str(t).strip()))
    if len(tickers) < 5:
        raise UniversoInvalido(
            f"solo {len(tickers)} instrumentos: un universo asi no permite "
            f"ninguna seleccion con sentido")

    fecha = fecha or time.strftime("%Y-%m-%d", time.gmtime())
    datos = {
        "version": VERSION,
        "fecha_congelacion": fecha,
        "regla_de_inclusion": regla,
        "notas": notas,
        "hash": _hash_lista(tickers, fecha, regla),
        "instrumentos": {
            t: {"alta": fecha, "sin_datos_desde": None,
                "baja_candidata": False, "observaciones": ""}
            for t in tickers
        },
        "_aviso": (
            "Esta lista NO se edita para quitar instrumentos. Un activo que "
            "desaparece se marca, y sigue contando en el denominador. "
            "Borrarlo reinventaria el sesgo de supervivencia dentro del "
            "sistema que pretendia evitarlo."
        ),
    }
    with open(ruta, "w") as f:
        json.dump(datos, f, indent=2)
    return datos


def cargar(ruta=RUTA_POR_DEFECTO) -> dict:
    if not os.path.exists(ruta):
        raise UniversoInvalido(f"no hay universo congelado en {ruta}")
    with open(ruta) as f:
        datos = json.load(f)
    esperado = _hash_lista(datos["instrumentos"].keys(),
                           datos["fecha_congelacion"],
                           datos["regla_de_inclusion"])
    datos["hash_coincide"] = (esperado == datos.get("hash"))
    if not datos["hash_coincide"]:
        datos["_alerta"] = (
            f"el hash NO coincide: guardado {datos.get('hash')}, calculado "
            f"{esperado}. La lista, la fecha o la regla se han editado "
            f"despues de congelarla."
        )
    return datos


def comprobar(series_disponibles, *, ruta=RUTA_POR_DEFECTO,
              fecha_comprobacion=None) -> dict:
    """Compara lo congelado con lo que hay hoy. NO borra nada.

    `series_disponibles` es el conjunto de tickers que han devuelto datos
    utilizables en esta corrida.
    """
    datos = cargar(ruta)
    hoy = fecha_comprobacion or time.strftime("%Y-%m-%d", time.gmtime())
    disponibles = set(str(t).upper() for t in series_disponibles)

    vivos, nuevas_bajas, bajas_previas, resucitados = [], [], [], []
    for t, info in datos["instrumentos"].items():
        if t in disponibles:
            vivos.append(t)
            if info.get("sin_datos_desde"):
                # Volvió a dar datos: lo más probable es que fuera un fallo
                # del proveedor, no un cierre. Se registra el ida y vuelta
                # en vez de borrar el historial.
                resucitados.append({
                    "instrumento": t,
                    "estuvo_sin_datos_desde": info["sin_datos_desde"],
                    "volvio_el": hoy})
                info["observaciones"] = (
                    f"{info.get('observaciones','')} | sin datos "
                    f"{info['sin_datos_desde']}, volvio {hoy}").strip(" |")
                info["sin_datos_desde"] = None
                info["baja_candidata"] = False
        else:
            if info.get("sin_datos_desde"):
                bajas_previas.append(t)
            else:
                info["sin_datos_desde"] = hoy
                info["baja_candidata"] = True
                nuevas_bajas.append(t)

    # Instrumentos que hay hoy y NO estaban congelados: no se añaden solos.
    fuera_del_universo = sorted(disponibles - set(datos["instrumentos"]))

    with open(ruta, "w") as f:
        guardar = {k: v for k, v in datos.items()
                   if k not in ("hash_coincide", "_alerta")}
        json.dump(guardar, f, indent=2)

    total = len(datos["instrumentos"])
    return {
        "fecha_comprobacion": hoy,
        "fecha_congelacion": datos["fecha_congelacion"],
        "hash_coincide": datos["hash_coincide"],
        "alerta": datos.get("_alerta"),
        "total_congelados": total,
        "vivos": len(vivos),
        "bajas_candidatas": sorted(set(nuevas_bajas + bajas_previas)),
        "nuevas_bajas_en_esta_corrida": sorted(nuevas_bajas),
        "resucitados": resucitados,
        "fuera_del_universo_congelado": fuera_del_universo,
        "tasa_supervivencia_observada": round(len(vivos) / total, 4)
        if total else None,
        "_lectura": (
            "las bajas candidatas NO se quitan de la lista. Siguen contando "
            "en el denominador, y una estrategia que las habria seleccionado "
            "tiene que cargar con lo que les paso. Un ticker puede dejar de "
            "dar datos porque cerro, porque cambio de nombre o porque fallo "
            "el proveedor: los tres se registran igual y resolverlo exige "
            "mirarlo a mano."
        ),
    }


def resumen_texto(estado: dict) -> str:
    lineas = [
        f"Universo congelado el {estado['fecha_congelacion']}, "
        f"{estado['total_congelados']} instrumentos",
        f"Comprobado el {estado['fecha_comprobacion']}: "
        f"{estado['vivos']} con datos "
        f"({estado['tasa_supervivencia_observada']*100:.1f}%)",
    ]
    if not estado["hash_coincide"]:
        lineas.append(f"ALERTA: {estado['alerta']}")
    if estado["bajas_candidatas"]:
        lineas.append(f"Bajas candidatas (NO se quitan de la lista): "
                      f"{', '.join(estado['bajas_candidatas'])}")
    if estado["nuevas_bajas_en_esta_corrida"]:
        lineas.append(f"Nuevas en esta corrida: "
                      f"{', '.join(estado['nuevas_bajas_en_esta_corrida'])}")
    if estado["resucitados"]:
        lineas.append(f"Volvieron a dar datos: "
                      f"{[r['instrumento'] for r in estado['resucitados']]}")
    if estado["fuera_del_universo_congelado"]:
        lineas.append(
            f"Con datos pero FUERA del universo congelado (no se anaden "
            f"solos): {', '.join(estado['fuera_del_universo_congelado'])}")
    return "\n".join(lineas)
