"""
Pruebas del seguimiento de divulgaciones. Contra FIXTURES, sin red.

El contenedor donde se escribio este modulo tiene sec.gov bloqueado por
el proxy, asi que no hay ninguna comprobacion aqui contra datos reales de
la SEC. Lo que se comprueba es la aritmetica de latencia y que el modulo
no pueda presentar un dato viejo como fresco.

Uso:  python tests/test_divulgaciones.py
"""
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

import seguimiento_divulgaciones as SD

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


# Fixture con la forma real de data.sec.gov/submissions/CIK...json.
# Las fechas reproducen el calendario de 2026: el 13F del segundo
# trimestre (posiciones a 30-06) se publico el 14-08, y el del tercero
# (30-09) se publica el 16-11.
SUBMISSIONS = {
    "cik": 1067983,
    "name": "GESTOR DE PRUEBA",
    "filings": {"recent": {
        "form":            ["13F-HR",    "SC 13D/A",  "4",         "13F-HR",    "10-K"],
        "filingDate":      ["2026-08-14", "2026-10-30", "2026-11-05", "2026-05-15", "2026-02-24"],
        "reportDate":      ["2026-06-30", "2026-10-28", "2026-11-03", "2026-03-31", "2025-12-31"],
        "accessionNumber": ["0001-26-001", "0001-26-002", "0001-26-003", "0001-26-004", "0001-26-005"],
        "primaryDocument": ["f13.html",   "d13da.html", "f4.html",    "f13.html",   "k10.html"],
    }},
}
HOY = "2026-11-07"

print("\n=== Latencia medida, no supuesta ===")
lista = SD.divulgaciones("GESTOR DE PRUEBA", 1067983, hoy=HOY,
                         _submissions=SUBMISSIONS)

# El MAS RECIENTE de cada formulario. Un dict por comprension se queda
# con el ULTIMO iterado, y con dos 13F en el fixture eso era el del primer
# trimestre: la prueba medía 221 dias y culpaba al modulo de un fallo que
# estaba aqui.
por_forma = {}
for d in lista:
    if d.formulario not in por_forma:
        por_forma[d.formulario] = d

check("D1", "el 10-K no se cuela: solo las vias de divulgacion pedidas",
      "10-K" not in por_forma and len(lista) == 4,
      f"-> formularios recogidos {sorted(por_forma)}")

f13 = por_forma.get("13F-HR")
check("D2", "el 13F del 2T declara su retraso legal real (45 dias)",
      f13 is not None and f13.dias_hasta_publicarse == 45,
      f"-> posicion {f13.fecha_posicion if f13 else '—'}, publicada "
      f"{f13.fecha_publicacion if f13 else '—'}, retraso "
      f"{f13.dias_hasta_publicarse if f13 else '—'} dias (exigido 45)")

check("D3", "y dice que HOY ese dato tiene 130 dias",
      f13 is not None and f13.dias_de_antiguedad_hoy == 130,
      f"-> antiguedad hoy {f13.dias_de_antiguedad_hoy if f13 else '—'} dias "
      f"(exigido 130: del 30-06 al 07-11)")

check("D4", "un 13F de 130 dias NO se etiqueta como reciente",
      f13 is not None and f13.vigencia == "TRIMESTRAL_VIEJO",
      f"-> vigencia {f13.vigencia if f13 else '—'}")

f4 = por_forma.get("4")
check("D5", "el Form 4 avisa de que es un directivo, no el gestor",
      f4 is not None and "directivo" in (f4._nota or ""),
      f"-> nota {f4._nota if f4 else '—'!r}")

print("\n=== La etiqueta 'tiempo real' no existe ===")
etiquetas = set()
for forma in SD.FORMULARIOS:
    for d in range(0, 400, 1):
        etiquetas.add(SD.clasificar_vigencia(forma, d))
prohibidas = [e for e in etiquetas
              if "TIEMPO" in e.upper() or "REAL" in e.upper()
              or "VIVO" in e.upper() or "INSTANT" in e.upper()]
check("D6", "ninguna etiqueta de vigencia dice tiempo real, con ningun plazo",
      not prohibidas,
      f"-> etiquetas posibles {sorted(etiquetas)}; prohibidas {prohibidas}")

check("D7", "ni con 0 dias de antiguedad en la via mas rapida",
      SD.clasificar_vigencia("SC 13D/A", 0) == "DIAS_DE_RETRASO",
      f"-> con 0 dias da {SD.clasificar_vigencia('SC 13D/A', 0)!r}")

print("\n=== El modulo no puede emitir una orden ===")
try:
    SD.senal("AAPL")
    no_emite = False
except NotImplementedError:
    no_emite = True
check("D8", "modo OBSERVE: pedirle una senal lanza, no devuelve una orden",
      no_emite and SD.MODO == "OBSERVE",
      f"-> modo {SD.MODO}, lanza={no_emite}")

print("\n=== No se inventan identificadores de gestor ===")
try:
    SD.resolver_cik("berkshire")
    resolvio_sin_red = True
    detalle = "-> resolvio un CIK SIN RED: eso solo puede ser de memoria"
except SD.DivulgacionNoDisponible as e:
    resolvio_sin_red = False
    detalle = f"-> {str(e)[:70]}"
check("D9", "sin red no se resuelve un CIK de memoria",
      not resolvio_sin_red, detalle)

print("\n=== Una lista vacia no significa 'no hay movimientos' ===")
texto = SD.resumen_texto([])
check("D10", "el resumen vacio distingue 'no publicado' de 'no ocurrido'",
      "no se ha publicado" in texto.lower(),
      f"-> {texto[:90]!r}")

texto2 = SD.resumen_texto(lista)
check("D11", "el resumen dice cual es el dato mas fresco y que no es vivo",
      "MAS FRESCO" in texto2 and "tiempo real" in texto2,
      "-> el resumen no declara la frescura del mejor dato")

print("\n" + "=" * 70)
print(f"DIVULGACIONES: {len(PASA)} pasan, {len(FALLA)} FALLAN")
print("=" * 70)
if FALLA:
    for ident, nombre, _ in FALLA:
        print(f"  [{ident}] {nombre}")
print("Probado contra fixtures. NINGUNA comprobacion contra la SEC real:")
print("el proxy de este contenedor bloquea sec.gov.")
print("=" * 70)
sys.exit(1 if FALLA else 0)
