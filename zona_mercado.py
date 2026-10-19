"""
Resolucion robusta de la zona horaria del mercado estadounidense.

POR QUE EXISTE ESTE ARCHIVO

El codigo usaba "US/Eastern" en dos sitios. Ese nombre es un ALIAS de
compatibilidad del IANA; el nombre canonico es "America/New_York". Las
dos apuntan a la misma zona, con los mismos husos y las mismas reglas
de horario de verano: cambiar de uno a otro NO cambia ninguna decision.

La diferencia esta en que muchas imagenes de contenedor traen una base
de zonas recortada, con los nombres canonicos pero sin los alias. En
una de esas, "US/Eastern" no resuelve, y como el filtro de sesion falla
CERRADO (y esta bien que falle cerrado), el bot bloquea el 100% de las
operaciones sin que nada parezca roto: los logs dicen "sesion
indeterminada", no "falta un paquete".

Hoy el bot no tiene ese problema porque tzdata esta en
requirements.txt. Esto es para que siga sin tenerlo si algun dia ese
paquete no llega, cambia la imagen base o se despliega en otro sitio.

El orden de intentos: primero el canonico, que existe en todas las
bases; luego el alias, por si acaso; y si ninguno resuelve, se lanza un
error que DICE lo que falta, en vez de dejar un bloqueo silencioso.
"""

from __future__ import annotations

# Canonico primero: presente incluso en bases de zonas recortadas.
# El alias despues, por compatibilidad con entornos antiguos.
CANDIDATAS = ("America/New_York", "US/Eastern", "EST5EDT")


class ZonaNoDisponible(RuntimeError):
    """No hay base de zonas horarias usable. Dice que instalar."""


def resolver() -> str:
    """Devuelve el primer nombre de zona que este sistema sabe resolver."""
    try:
        from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
    except ImportError as e:   # Python < 3.9, no deberia pasar
        raise ZonaNoDisponible(f"zoneinfo no disponible: {e}") from e

    intentos = []
    for nombre in CANDIDATAS:
        try:
            ZoneInfo(nombre)
            return nombre
        except (ZoneInfoNotFoundError, KeyError, ValueError) as e:
            intentos.append(f"{nombre}: {type(e).__name__}")

    raise ZonaNoDisponible(
        "ninguna zona horaria del mercado resuelve en este sistema "
        f"({'; '.join(intentos)}). Falta la base de zonas: instalar el "
        "paquete `tzdata` (ya esta en requirements.txt) o el paquete del "
        "sistema tzdata. Mientras falte, el filtro de sesion bloquea "
        "todas las operaciones por seguridad."
    )


def zona() -> str:
    """Igual que resolver(), pero cacheado."""
    global _CACHE
    if _CACHE is None:
        _CACHE = resolver()
    return _CACHE


_CACHE: str | None = None
