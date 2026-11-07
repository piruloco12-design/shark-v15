"""
SEGUIMIENTO DE DIVULGACIONES DE GRANDES GESTORES — en modo OBSERVE.

Brian pidio "monitorizar movimientos a tiempo real de los mas grandes
inversores del mundo, que el bot lo sepa al momento".

Lo primero que tiene que decir este modulo es que **eso no existe**, y por
que, con las fechas exactas. No por pesimismo: porque la latencia es el
dato que decide si la informacion sirve para algo, y un modulo que la
esconda seria el mismo error que ya cometimos tres veces en este
proyecto.

## Lo que de verdad se publica, y cuando

| Via        | Que contiene                          | Plazo legal |
|------------|---------------------------------------|-------------|
| 13F-HR     | posiciones LARGAS en acciones de EEUU | 45 dias naturales tras el cierre de trimestre |
| SC 13D     | participacion activista >5%           | 5 dias habiles desde cruzar el 5% |
| SC 13D/A   | cambio material en una 13D            | 2 dias habiles |
| SC 13G     | participacion pasiva >5% (QII)        | 45 dias tras el cierre de trimestre |
| SC 13G/A   | paso del 10% o cambio de >5 puntos    | 5 dias habiles tras fin de mes (QII) |
| Form 4     | operaciones de DIRECTIVOS de la empresa | 2 dias habiles |

Fuentes: plazos de 13D/13G segun las enmiendas de la SEC de octubre de
2023 (cumplimiento de 13G desde el 30-09-2024); 13F sigue en 45 dias; el
Form 4 sigue en 2 dias habiles tras las reglas finales de la Seccion 16
de febrero de 2026.

## Las tres cosas que esto implica, y que no se pueden rodear

1. **El 13F llega con meses de retraso.** Hoy, 7 de noviembre de 2026,
   las posiciones mas recientes que existen son del **30 de junio de
   2026**, publicadas el 14 de agosto. Son **130 dias**. Las del 30 de
   septiembre salen el **16 de noviembre**. Un escrito a la SeC lo
   ilustra con el caso extremo: una compra de principios de enero no es
   publica hasta el 15 de mayo.

2. **El Form 4, que si es rapido, no es de los gestores.** Es de
   directivos y consejeros de la propia empresa. Que el director
   financiero de una empresa venda acciones suyas no es que "un gran
   inversor" se mueva.

3. **Lo que mas falta es lo que no se publica.** El 13F no lleva cortos,
   ni derivados, ni bonos, ni divisas, ni materias primas, ni efectivo, ni
   nada de fuera de EEUU, ni una sola operacion intra-trimestral. Una
   cartera puede estar entera en el 13F y estar cubierta con opciones que
   no aparecen. Ver una posicion larga aislada puede dar exactamente la
   impresion contraria a la realidad.

Asi que este modulo NO emite senales. Igual que M02 y M03, es modo
OBSERVE: recoge, fecha, ETIQUETA LA LATENCIA y registra. Si algun dia
alguien quiere convertirlo en senal, tendra que ser una variante con su
identificador, su preregistro y su medicion, como todo lo demas.

## Lo que no se puede comprobar desde donde escribo esto

El contenedor donde trabajo tiene `sec.gov` bloqueado por el proxy (403
en el tunel). Asi que este modulo esta probado contra FIXTURES, no contra
datos reales de la SEC. En Render, que si tiene red, deberia funcionar;
que "deberia" no es "funciona" queda dicho aqui y no en una nota al pie.

Y los CIK no van cableados a proposito: se resuelven en ejecucion contra
EDGAR. Escribir de memoria el identificador de un fondo pondria delante
la cartera de otro gestor, y eso es peor que no tener el modulo.
"""
from __future__ import annotations

import datetime
import json
import time
import urllib.request
from dataclasses import dataclass, field

BASE_SUBMISSIONS = "https://data.sec.gov/submissions/CIK{cik:010d}.json"
BASE_TICKERS = "https://www.sec.gov/files/company_tickers.json"
BUSCAR_EMPRESA = ("https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany"
                  "&company={nombre}&type=13F-HR&dateb=&owner=include"
                  "&count=10&output=atom")

# La SEC EXIGE un User-Agent que identifique a quien consulta, con un
# contacto. Sin el, devuelve 403. No se pone el correo de Brian aqui: se
# lee de una variable de entorno para que no viaje en el repositorio.
import os
CONTACTO = os.getenv("SEC_CONTACTO", "").strip()

FORMULARIOS = {
    "13F-HR": {"que": "posiciones largas en acciones de EEUU",
               "plazo_dias": 45, "base": "cierre_de_trimestre"},
    "13F-HR/A": {"que": "correccion de un 13F anterior",
                 "plazo_dias": 45, "base": "cierre_de_trimestre"},
    "SC 13D": {"que": "participacion activista >5%",
               "plazo_dias": 7, "base": "el_hecho"},
    "SC 13D/A": {"que": "cambio material en una 13D",
                 "plazo_dias": 2, "base": "el_hecho"},
    "SC 13G": {"que": "participacion pasiva >5%",
               "plazo_dias": 45, "base": "cierre_de_trimestre"},
    "SC 13G/A": {"que": "cambio en una participacion pasiva",
                 "plazo_dias": 7, "base": "el_hecho"},
    "4": {"que": "operacion de un DIRECTIVO de la empresa, no de un gestor",
          "plazo_dias": 2, "base": "el_hecho"},
}


class DivulgacionNoDisponible(RuntimeError):
    """No se pudo leer EDGAR. No es lo mismo que 'no hay movimientos'."""


@dataclass(frozen=True)
class Divulgacion:
    """Un hecho publicado, con su edad medida y dicha."""

    gestor: str
    cik: int
    formulario: str
    que_contiene: str
    fecha_posicion: str          # a que fecha se refiere el contenido
    fecha_publicacion: str       # cuando se hizo publico
    dias_hasta_publicarse: int   # retraso legal consumido
    dias_de_antiguedad_hoy: int  # cuanto hace que el dato es viejo, HOY
    vigencia: str                # NUNCA "tiempo real"
    enlace: str
    _nota: str = ""


def _get_json(url: str, timeout=20):
    if not CONTACTO:
        raise DivulgacionNoDisponible(
            "falta SEC_CONTACTO. La SEC exige un User-Agent con un contacto "
            "y devuelve 403 sin el. Se lee del entorno para que el correo no "
            "viaje en el repositorio.")
    req = urllib.request.Request(
        url, headers={"User-Agent": f"shark-v15 seguimiento ({CONTACTO})",
                      "Accept-Encoding": "gzip, deflate",
                      "Host": url.split("/")[2]})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            datos = r.read()
    except Exception as e:
        raise DivulgacionNoDisponible(
            f"no se pudo leer {url}: {type(e).__name__}: {e}") from None
    try:
        return json.loads(datos)
    except Exception:
        import gzip
        return json.loads(gzip.decompress(datos))


def _dias(desde: str, hasta: str) -> int:
    """Dias naturales entre dos fechas ISO.

    Usa datetime.date porque no depende del huso ni del horario de verano
    del proceso, y porque la intencion se lee: restar dos fechas.

    Nota de honestidad sobre este cambio. La version anterior usaba
    time.mktime y escribi aqui que daba 221 dias donde debia dar 130. Lo
    comprobe antes de dejarlo: las dos implementaciones dan EXACTAMENTE
    lo mismo en los tres casos que probe (130, 221 y 45 dias). El 221
    venia de MI PRUEBA, que con dos 13F en el fixture se quedaba con el
    del primer trimestre en vez del segundo. mktime no tenia nada que ver,
    y culparlo habria dejado una explicacion falsa en el codigo.
    """
    try:
        a = datetime.date.fromisoformat(desde)
        b = datetime.date.fromisoformat(hasta)
        return (b - a).days
    except Exception:
        return -1


def clasificar_vigencia(formulario: str, dias_hoy: int) -> str:
    """La etiqueta de frescura. NUNCA devuelve 'tiempo real'.

    Es deliberado: ninguna via de divulgacion lo es, asi que la etiqueta
    no existe. La mas rapida (13D/A, Form 4) son dos dias HABILES, y para
    entonces el precio ya se movio.
    """
    if dias_hoy < 0:
        return "FECHA_ILEGIBLE"
    if formulario.startswith("13F"):
        # Un 13F nunca es fresco: el contenido es del cierre de trimestre.
        if dias_hoy <= 60:
            return "TRIMESTRAL_RECIENTE"
        if dias_hoy <= 135:
            return "TRIMESTRAL_VIEJO"
        return "TRIMESTRAL_CADUCO"
    if dias_hoy <= 7:
        return "DIAS_DE_RETRASO"
    if dias_hoy <= 30:
        return "SEMANAS_DE_RETRASO"
    return "MESES_DE_RETRASO"


def resolver_cik(nombre: str) -> int:
    """Busca el CIK por nombre contra EDGAR. No se cablea de memoria.

    Si devuelve varios, es ambiguo y lanza: elegir por mi cuenta pondria
    la cartera de otro gestor delante de quien lee.
    """
    datos = _get_json(BASE_TICKERS)
    objetivo = nombre.strip().lower()
    coincidencias = {}
    for fila in (datos.values() if isinstance(datos, dict) else datos):
        titulo = str(fila.get("title", "")).lower()
        if objetivo in titulo:
            coincidencias[int(fila["cik_str"])] = fila.get("title")
    if not coincidencias:
        raise DivulgacionNoDisponible(
            f"ningun emisor de EDGAR contiene '{nombre}'. Ojo: "
            f"company_tickers.json lista EMISORES con ticker, y muchos "
            f"gestores que presentan 13F no estan ahi. Para esos hay que "
            f"buscar por EDGAR full-text y pasar el CIK a mano.")
    if len(coincidencias) > 1:
        raise DivulgacionNoDisponible(
            f"'{nombre}' es ambiguo: {coincidencias}. Pasa el CIK exacto; "
            f"elegir yo pondria delante la cartera de otro gestor.")
    return next(iter(coincidencias))


def divulgaciones(gestor: str, cik: int, hoy: str | None = None,
                  formularios=None, maximo=40,
                  _submissions=None) -> list[Divulgacion]:
    """Las ultimas divulgaciones de un gestor, cada una con su edad.

    `_submissions` permite inyectar la respuesta para probar sin red, que
    es como esta probado este modulo: el proxy de mi contenedor bloquea
    sec.gov.
    """
    hoy = hoy or time.strftime("%Y-%m-%d")
    quiero = set(formularios or FORMULARIOS)
    datos = _submissions if _submissions is not None else _get_json(
        BASE_SUBMISSIONS.format(cik=int(cik)))
    recientes = (datos.get("filings", {}) or {}).get("recent", {}) or {}
    formas = recientes.get("form", []) or []
    salida: list[Divulgacion] = []
    for i, forma in enumerate(formas):
        if forma not in quiero:
            continue
        f_pub = (recientes.get("filingDate") or [None] * len(formas))[i]
        f_pos = (recientes.get("reportDate") or [None] * len(formas))[i] or f_pub
        acc = (recientes.get("accessionNumber") or [""] * len(formas))[i]
        doc = (recientes.get("primaryDocument") or [""] * len(formas))[i]
        meta = FORMULARIOS.get(forma, {"que": forma})
        dias_hoy = _dias(f_pos, hoy)
        salida.append(Divulgacion(
            gestor=gestor, cik=int(cik), formulario=forma,
            que_contiene=meta.get("que", forma),
            fecha_posicion=f_pos, fecha_publicacion=f_pub,
            dias_hasta_publicarse=_dias(f_pos, f_pub),
            dias_de_antiguedad_hoy=dias_hoy,
            vigencia=clasificar_vigencia(forma, dias_hoy),
            enlace=(f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/"
                    f"{acc.replace('-', '')}/{doc}" if acc else ""),
            _nota=("el Form 4 es de un directivo de la empresa, no del "
                   "gestor" if forma == "4" else ""),
        ))
        if len(salida) >= maximo:
            break
    salida.sort(key=lambda d: d.fecha_publicacion, reverse=True)
    return salida


def resumen_texto(lista: list[Divulgacion]) -> str:
    if not lista:
        return ("Sin divulgaciones en el rango pedido. Eso NO significa que "
                "no haya habido movimientos: significa que no se ha "
                "publicado ninguno todavia.")
    lineas = []
    for d in lista:
        lineas.append(
            f"[{d.vigencia:<22}] {d.gestor} · {d.formulario}\n"
            f"    {d.que_contiene}\n"
            f"    posicion a {d.fecha_posicion} · publicada "
            f"{d.fecha_publicacion} ({d.dias_hasta_publicarse} dias)\n"
            f"    HOY ese dato tiene {d.dias_de_antiguedad_hoy} dias"
            + (f"\n    AVISO: {d._nota}" if d._nota else ""))
    mas_fresco = min(d.dias_de_antiguedad_hoy for d in lista
                     if d.dias_de_antiguedad_hoy >= 0)
    lineas.append("")
    lineas.append(f"El dato MAS FRESCO de esta lista tiene {mas_fresco} dias. "
                  f"Ninguna via de divulgacion es tiempo real.")
    return "\n".join(lineas)


MODO = "OBSERVE"


def senal(*_args, **_kwargs):
    """No hay senal. A proposito.

    Convertir una divulgacion con meses de retraso en una orden es
    precisamente lo que este modulo existe para NO hacer. Si algun dia se
    quiere, sera una variante con identificador, preregistro y medicion.
    """
    raise NotImplementedError(
        "seguimiento_divulgaciones esta en modo OBSERVE y no emite senales. "
        "La latencia minima de la via mas rapida son 2 dias habiles, y la "
        "del 13F entre 45 y 135 dias.")
