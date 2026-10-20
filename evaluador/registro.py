"""
Registro de experimentos: se escribe ANTES de ver un solo resultado.

POR QUE

La auditoría fue clara en dos cosas que me afectan directamente:

  «Escribir los criterios en el archivo no prueba por sí solo cuándo se
   fijaron; hacen falta una versión y un registro fechados anteriores a los
   resultados.»

  «El presupuesto de ensayos es una regla de disciplina, no un control
   estadístico de la tasa de error.»

La vez anterior puse los criterios en la cabecera del script y los llamé
pre-registrados. Eso no demuestra nada: el archivo se puede editar después.
Aquí el registro se escribe en disco, con su hash, en un paso separado y
ANTES de correr nada. Si luego los resultados no gustan y se cambia la
familia, el hash cambia y se ve.

QUE SE REGISTRA

  - la familia exacta de hipótesis, enumerada
  - la métrica primaria y el umbral económico, fijados
  - el método de inferencia y sus parámetros (longitud de bloque incluida)
  - el estado: EXPLORATORIO o CONFIRMATORIO
  - las variantes ya vistas, que no recuperan su condición de prueba final
    por renombrarlas
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import time


def _hash_codigo(rutas) -> dict:
    """Hash de cada archivo de código que participa."""
    salida = {}
    for ruta in rutas:
        try:
            with open(ruta, "rb") as f:
                salida[os.path.basename(ruta)] = hashlib.sha256(
                    f.read()).hexdigest()[:16]
        except OSError as e:
            salida[os.path.basename(ruta)] = f"ILEGIBLE: {e}"
    return salida


def _version_dependencias() -> dict:
    versiones = {"python": sys.version.split()[0]}
    for nombre in ("pandas", "numpy"):
        try:
            mod = __import__(nombre)
            versiones[nombre] = getattr(mod, "__version__", "?")
        except ImportError:
            versiones[nombre] = "no instalado"
    return versiones


def _commit() -> str:
    try:
        r = subprocess.run(["git", "rev-parse", "HEAD"],
                           capture_output=True, text=True, timeout=10)
        sucio = subprocess.run(["git", "status", "--porcelain"],
                               capture_output=True, text=True, timeout=10)
        marca = "-sucio" if sucio.stdout.strip() else ""
        return (r.stdout.strip()[:12] + marca) if r.returncode == 0 else "?"
    except Exception:
        return "?"


class RegistroYaExiste(RuntimeError):
    """Ya hay un registro en esa ruta. No se pisa."""


def crear(
    *,
    nombre: str,
    familia: list[dict],
    metrica_primaria: str,
    hipotesis: str,
    umbral_economico: float,
    metodo_inferencia: str,
    parametros_inferencia: dict,
    estado: str,
    universo_etiqueta: str,
    politicas: dict,
    variantes_ya_vistas: list[str],
    rutas_codigo: list[str],
    salida: str,
) -> dict:
    """Escribe el registro y devuelve su contenido con el hash.

    `estado` tiene que ser EXPLORATORIO o CONFIRMATORIO. Un tramo de datos
    ya mirado no vuelve a ser prueba final por renombrarlo, así que si las
    series son las mismas de antes, esto es EXPLORATORIO y se dice.
    """
    if estado not in ("EXPLORATORIO", "CONFIRMATORIO"):
        raise ValueError(f"estado desconocido: {estado}")
    if not familia:
        raise ValueError("una familia vacía no es un registro")

    registro = {
        "nombre": nombre,
        "creado_en": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "commit": _commit(),
        "estado": estado,
        "universo_etiqueta": universo_etiqueta,
        "familia": familia,
        "hipotesis_declaradas": len(familia),
        "metrica_primaria": metrica_primaria,
        "hipotesis": hipotesis,
        "umbral_economico": umbral_economico,
        "metodo_inferencia": metodo_inferencia,
        "parametros_inferencia": parametros_inferencia,
        "politicas": politicas,
        "variantes_ya_vistas": variantes_ya_vistas,
        "hash_codigo": _hash_codigo(rutas_codigo),
        "dependencias": _version_dependencias(),
        "_aviso": (
            "Este registro se escribe ANTES de calcular los resultados, y su "
            "hash demuestra INTEGRIDAD: si la familia, la métrica o el umbral "
            "cambian después, el hash cambia y queda a la vista."
        ),
        "_lo_que_NO_demuestra": (
            "La FECHA. El archivo es local y lo escribió quien lo va a usar, "
            "así que un hash propio no prueba que se escribiera antes de ver "
            "los resultados: quien lo creó puede rehacer ambas cosas. Una "
            "fecha de preregistro solo la acredita un tercero. Lo más "
            "cercano que hay aquí es el commit anotado arriba: una vez "
            "empujado, la fecha de recepción la registra GitHub, que no es "
            "parte de este repositorio. Mientras no esté empujado, esto es "
            "una declaración de intenciones, no un preregistro."
        ),
    }
    crudo = json.dumps(registro, sort_keys=True, separators=(",", ":"))
    registro["hash_registro"] = hashlib.sha256(crudo.encode()).hexdigest()[:16]

    os.makedirs(os.path.dirname(salida) or ".", exist_ok=True)
    # Registro por ejecucion, SIN sobrescritura. El modo "x" falla si el
    # archivo existe, y lo hace de forma atomica: comprobar y luego
    # escribir deja una carrera por medio. Antes se abria en modo "w", asi
    # que una segunda corrida pisaba el registro de la primera y no
    # quedaba rastro de que la familia hubiera cambiado.
    try:
        with open(salida, "x") as f:
            json.dump(registro, f, indent=2)
    except FileExistsError:
        raise RegistroYaExiste(
            f"{salida} ya existe y un registro por ejecucion no se "
            f"sobrescribe. Si esta es otra corrida, dale otro nombre de "
            f"salida; si es la misma, el registro de la primera es el que "
            f"vale."
        ) from None
    return registro


def holm(pvalores: dict, alfa: float = 0.05) -> dict:
    """Corrección de Holm sobre la familia declarada.

    Con N hipótesis y error familiar alfa, el primer umbral es alfa/N y los
    siguientes son secuenciales: alfa/(N-i). No es «aplicar alfa/N a todas».
    En cuanto una no se rechaza, las que quedan tampoco.
    """
    if not pvalores:
        return {}
    orden = sorted(pvalores.items(), key=lambda kv: (kv[1] is None, kv[1]))
    n = len(orden)
    salida, sigue_rechazando = {}, True
    for i, (clave, p) in enumerate(orden):
        umbral = alfa / (n - i)
        if p is None:
            salida[clave] = {"p": None, "umbral_holm": round(umbral, 6),
                             "rechaza_nula": False,
                             "motivo": "p no calculable"}
            sigue_rechazando = False
            continue
        rechaza = bool(sigue_rechazando and p <= umbral)
        if not rechaza:
            sigue_rechazando = False
        salida[clave] = {"p": round(float(p), 6),
                         "umbral_holm": round(umbral, 6),
                         "rechaza_nula": rechaza,
                         "posicion": i + 1, "familia": n}
    return salida
