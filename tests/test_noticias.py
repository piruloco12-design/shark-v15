"""
Pruebas del lector de noticias y del filtro de Gemini.

Ninguna toca la red: las respuestas de las APIs se sustituyen por
objetos falsos. Lo que se comprueba es el comportamiento que
importa cuando algo va mal, que es cuando un filtro mal hecho
hace dano.
"""
import json
import os
import sys
import tempfile
import types
from datetime import datetime, timedelta, timezone

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

_tmpdb = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_tmpdb.close()
os.environ["DATABASE_NAME"] = _tmpdb.name
os.environ["TELEGRAM_TOKEN"] = ""

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


class RespuestaFalsa:
    def __init__(self, datos, codigo=200):
        self._datos = datos
        self.status_code = codigo
        self.text = json.dumps(datos) if not isinstance(datos, str) else datos

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self):
        if isinstance(self._datos, str):
            raise ValueError("no es json")
        return self._datos


import noticias
import gemini_filter


print("\n=== 1) lectura de noticias ===")

ahora = datetime.now(timezone.utc)
feed = [
    {"datetime": int((ahora - timedelta(hours=2)).timestamp()),
     "headline": "NVDA sube tras resultados", "summary": "Resumen",
     "source": "Reuters"},
    {"datetime": int((ahora - timedelta(hours=5)).timestamp()),
     "headline": "Analistas elevan precio objetivo", "summary": "",
     "source": "Bloomberg"},
    # Demasiado vieja: debe quedar fuera (HORAS_ATRAS = 48)
    {"datetime": int((ahora - timedelta(days=5)).timestamp()),
     "headline": "Noticia antigua", "summary": "", "source": "X"},
]

noticias._CACHE.clear()
noticias.FINNHUB_API_KEY = "clave-falsa"
noticias.requests = types.SimpleNamespace(get=lambda *a, **k: RespuestaFalsa(feed))

titulares, fuente, error = noticias.obtener_noticias("NVDA", usar_cache=False)
check("lee titulares de Finnhub", len(titulares) == 2, f"-> {len(titulares)}")
check("descarta las noticias de mas de 48h",
      all("antigua" not in t["titular"] for t in titulares))
check("ordena de mas nueva a mas vieja",
      titulares[0]["horas"] < titulares[1]["horas"])
check("fuente correcta", fuente == "finnhub", f"-> {fuente}")
check("sin error", error is None)

texto = noticias.formatear_para_prompt(titulares)
check("el prompt incluye los titulares", "NVDA sube" in texto)
check("el prompt incluye la antiguedad", "hace 2h" in texto)
check("sin titulares da texto explicito",
      "sin noticias" in noticias.formatear_para_prompt([]))

# Las dos fuentes caidas: no debe explotar.
noticias._CACHE.clear()
noticias.requests = types.SimpleNamespace(
    get=lambda *a, **k: (_ for _ in ()).throw(RuntimeError("red caida")))
noticias.ALPHA_VANTAGE_API_KEY = "otra-falsa"
t2, f2, e2 = noticias.obtener_noticias("NVDA", usar_cache=False)
check("si fallan todas las fuentes NO lanza excepcion", t2 == [] and f2 is None)
check("y explica el motivo", e2 is not None and "red caida" in e2)


print("\n=== 2) filtro de Gemini: comportamiento ante fallos ===")

gemini_filter.HABILITADO = True
gemini_filter.GEMINI_API_KEY = "clave-falsa"

def responder(payload):
    return RespuestaFalsa({"candidates": [{"content": {"parts": [
        {"text": json.dumps(payload)}]}}]})

CAT_MIN = {"models": [{"name": "models/gemini-2.5-flash",
                       "baseModelId": "gemini-2.5-flash",
                       "supportedGenerationMethods": ["generateContent"]}]}
def _reqs(post):
    return types.SimpleNamespace(post=post,
                                 get=lambda *a, **k: RespuestaFalsa(CAT_MIN))
gemini_filter.MODELO = "gemini-2.5-flash"
gemini_filter._MODELO_RESUELTO = "gemini-2.5-flash"
gemini_filter.requests = _reqs(lambda *a, **k: responder(
    {"veredicto": "VETAR", "confianza": 85, "motivo": "resultados malos"}))

gemini_filter.MODO = "sombra"
r = gemini_filter.verificar_operacion("NVDA", "BUY", 180.0, "TREND", "titulares")
check("lee el veredicto", r["veredicto"] == "VETAR", f"-> {r}")
check("lee la confianza", r["confianza"] == 85)
check("EN MODO SOMBRA NO BLOQUEA", r["bloquea"] is False,
      "-> bloqueo en modo sombra: el filtro no puede vetar sin medirse")

gemini_filter.MODO = "bloqueo"
r = gemini_filter.verificar_operacion("NVDA", "BUY", 180.0, "TREND", "titulares")
check("en modo bloqueo SI bloquea un veto con confianza alta", r["bloquea"] is True)

gemini_filter.requests = _reqs(lambda *a, **k: responder(
    {"veredicto": "VETAR", "confianza": 30, "motivo": "dudoso"}))
r = gemini_filter.verificar_operacion("NVDA", "BUY", 180.0, "TREND", "t")
check("un veto con poca confianza no bloquea", r["bloquea"] is False)

# API caida
gemini_filter.requests = _reqs(
    lambda *a, **k: (_ for _ in ()).throw(RuntimeError("timeout")))
r = gemini_filter.verificar_operacion("NVDA", "BUY", 180.0, "TREND", "t")
check("si Gemini falla devuelve NEUTRAL", r["veredicto"] == "NEUTRAL")
check("y NO bloquea la operacion", r["bloquea"] is False,
      "-> un fallo de la API no puede parar la cuenta")

# Respuesta ilegible
gemini_filter.requests = _reqs(lambda *a, **k: RespuestaFalsa(
    {"candidates": [{"content": {"parts": [{"text": "lo siento, no puedo"}]}}]}))
r = gemini_filter.verificar_operacion("NVDA", "BUY", 180.0, "TREND", "t")
check("respuesta ilegible -> NEUTRAL", r["veredicto"] == "NEUTRAL" and not r["bloquea"])

# JSON envuelto en markdown
gemini_filter.requests = _reqs(lambda *a, **k: RespuestaFalsa(
    {"candidates": [{"content": {"parts": [
        {"text": '```json\n{"veredicto":"APROBAR","confianza":70,"motivo":"ok"}\n```'}]}}]}))
r = gemini_filter.verificar_operacion("NVDA", "BUY", 180.0, "TREND", "t")
check("entiende el JSON envuelto en markdown", r["veredicto"] == "APROBAR", f"-> {r}")

# Veredicto inventado
gemini_filter.requests = _reqs(lambda *a, **k: responder(
    {"veredicto": "COMPRA_FUERTE", "confianza": 99, "motivo": "x"}))
r = gemini_filter.verificar_operacion("NVDA", "BUY", 180.0, "TREND", "t")
check("un veredicto inventado se trata como NEUTRAL",
      r["veredicto"] == "NEUTRAL" and not r["bloquea"])

gemini_filter.HABILITADO = False
r = gemini_filter.verificar_operacion("NVDA", "BUY", 180.0, "TREND", "t")
check("apagado devuelve NEUTRAL sin llamar a la API",
      r["veredicto"] == "NEUTRAL" and r["fuente"] == "interno")


print("\n=== 3) descubrimiento de modelo ===")

# El fallo real del 2026-10-19: el bot pedia gemini-2.0-flash y
# la API devolvia 404. Los nombres de modelo caducan, asi que
# ahora se preguntan en vez de fijarse.

CATALOGO = {"models": [
    {"name": "models/gemini-1.5-pro", "baseModelId": "gemini-1.5-pro",
     "supportedGenerationMethods": ["generateContent"]},
    {"name": "models/gemini-2.5-flash", "baseModelId": "gemini-2.5-flash",
     "supportedGenerationMethods": ["generateContent"]},
    {"name": "models/gemini-2.5-flash-preview", "baseModelId": "gemini-2.5-flash-preview",
     "supportedGenerationMethods": ["generateContent"]},
    {"name": "models/text-embedding-004", "baseModelId": "text-embedding-004",
     "supportedGenerationMethods": ["embedContent"]},
]}

gemini_filter.GEMINI_API_KEY = "clave-falsa"
gemini_filter.requests = types.SimpleNamespace(
    get=lambda *a, **k: RespuestaFalsa(CATALOGO))

disponibles = gemini_filter.listar_modelos()
check("lista solo los que generan contenido",
      set(disponibles) == {"gemini-1.5-pro", "gemini-2.5-flash",
                           "gemini-2.5-flash-preview"},
      f"-> {disponibles}")
check("descarta los de embeddings", "text-embedding-004" not in disponibles)

# Modelo configurado inexistente -> elige uno real
gemini_filter.MODELO = "gemini-2.0-flash"
gemini_filter._MODELO_RESUELTO = None
modelo, nota = gemini_filter.resolver_modelo(forzar=True)
check("si el configurado no existe, elige uno disponible",
      modelo in disponibles, f"-> {modelo} ({nota})")
check("prefiere flash sobre pro", "flash" in modelo, f"-> {modelo}")
check("evita las versiones preview", "preview" not in modelo, f"-> {modelo}")
check("la nota explica el cambio", "no existe" in nota, f"-> {nota}")

# Modelo configurado que si existe -> se respeta
gemini_filter.MODELO = "gemini-1.5-pro"
gemini_filter._MODELO_RESUELTO = None
modelo, nota = gemini_filter.resolver_modelo(forzar=True)
check("si el configurado existe, se respeta", modelo == "gemini-1.5-pro",
      f"-> {modelo}")

# Prefijo: gemini-2.5-flash -> coincide exacto
gemini_filter.MODELO = "gemini-2.5"
gemini_filter._MODELO_RESUELTO = None
modelo, _ = gemini_filter.resolver_modelo(forzar=True)
check("un prefijo encuentra la version concreta",
      modelo and modelo.startswith("gemini-2.5"), f"-> {modelo}")

# Catalogo vacio
gemini_filter.requests = types.SimpleNamespace(
    get=lambda *a, **k: RespuestaFalsa({"models": []}))
gemini_filter._MODELO_RESUELTO = None
modelo, nota = gemini_filter.resolver_modelo(forzar=True)
check("catalogo vacio -> ningun modelo y lo dice", modelo is None, f"-> {nota}")

# API caida al listar
gemini_filter.requests = types.SimpleNamespace(
    get=lambda *a, **k: (_ for _ in ()).throw(RuntimeError("403 forbidden")))
gemini_filter._MODELO_RESUELTO = None
modelo, nota = gemini_filter.resolver_modelo(forzar=True)
check("si no se puede listar, lo dice sin explotar",
      modelo is None and "no se pudo listar" in nota, f"-> {nota}")

gemini_filter.MODELO = "gemini-2.5-flash"
gemini_filter._MODELO_RESUELTO = "gemini-2.5-flash"


print("\n=== 4) prueba de conexion al arrancar ===")

gemini_filter.HABILITADO = True
gemini_filter.GEMINI_API_KEY = "clave-falsa"

# Caso bueno: ante una noticia mala en una compra, veta.
def falsas(post):
    return types.SimpleNamespace(post=post,
                                 get=lambda *a, **k: RespuestaFalsa(CATALOGO))

gemini_filter.requests = falsas(lambda *a, **k: responder(
    {"veredicto": "VETAR", "confianza": 80, "motivo": "resultados malos"}))
ok, msg = gemini_filter.probar_conexion()
check("clave valida y respuesta coherente -> OK", ok is True, f"-> {msg}")

# Caso malo: aprueba una compra con una noticia claramente mala.
gemini_filter.requests = falsas(lambda *a, **k: responder(
    {"veredicto": "APROBAR", "confianza": 90, "motivo": "todo bien"}))
ok, msg = gemini_filter.probar_conexion()
check("si aprueba una compra con noticia mala -> AVISA", ok is False, f"-> {msg}")

# Clave invalida / API caida: tiene que detectarse, no pasar
# desapercibido. Es el escenario que motiva toda esta prueba.
gemini_filter.requests = falsas(
    lambda *a, **k: (_ for _ in ()).throw(RuntimeError("401 invalid key")))
ok, msg = gemini_filter.probar_conexion()
check("clave invalida se DETECTA al arrancar", ok is False, f"-> {msg}")
check("y el mensaje dice que no respondio", "no respondio" in msg.lower())

gemini_filter.GEMINI_API_KEY = ""
ok, msg = gemini_filter.probar_conexion()
check("encendido sin clave -> avisa", ok is False and "GEMINI_API_KEY" in msg)

gemini_filter.HABILITADO = False
ok, msg = gemini_filter.probar_conexion()
check("apagado no comprueba nada y no molesta", ok is True)

gemini_filter.GEMINI_API_KEY = "clave-falsa"


print("\n=== 5) los veredictos se guardan siempre ===")

import storage
storage.init_db()

for v, c in [("APROBAR", 70), ("VETAR", 90), ("NEUTRAL", 0)]:
    storage.guardar_veredicto_noticias(
        timestamp=datetime.now().isoformat(), ticker="NVDA", signal="BUY",
        regime="TREND", precio=180.0, veredicto=v, confianza=c,
        motivo="prueba", fuente="gemini", bloqueo_aplicado=False, n_titulares=2)

cuenta = storage.contar_veredictos_noticias()
check("se guardan los tres veredictos", sum(cuenta.values()) == 3, f"-> {cuenta}")
check("incluido el VETAR que no bloqueo", cuenta.get("VETAR") == 1,
      "-> sin registrar los vetos en sombra no habria nada que medir")

ultimo = storage.obtener_veredictos_noticias(1)[0]
check("guarda el motivo", ultimo["motivo"] == "prueba")
check("guarda si bloqueo o no", ultimo["bloqueo_aplicado"] == 0)

print("\n" + "=" * 62)
print(f"RESULTADO: {OK} pruebas pasadas, {len(FALLOS)} fallos")
for f in FALLOS:
    print(f"  - {f}")
print("=" * 62)

os.unlink(_tmpdb.name)
sys.exit(1 if FALLOS else 0)
