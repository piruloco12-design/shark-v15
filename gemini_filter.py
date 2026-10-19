"""
Verificacion de operaciones con Gemini sobre noticias recientes.

POR QUE ARRANCA EN MODO SOMBRA

Este filtro NO puede backtestearse. Gemini en 2026 sabe lo que
paso en 2019: preguntarle "aprobarias esta operacion en marzo de
2019" filtra el futuro dentro de la respuesta. Cualquier backtest
suyo saldria bien por construccion y no significaria nada.

El estudio de referencia sobre esto (Lopez-Lira y Tang, "Can
ChatGPT Forecast Stock Price Movements?") lo resolvio usando solo
titulares POSTERIORES al corte de entrenamiento del modelo. Aqui
no se puede hacer eso con historico.

Asi que arranca en modo sombra: opina en cada operacion, la
decision se guarda con su motivo, pero NO bloquea nada. Cuando
haya suficientes operaciones se podra medir si las que Gemini
aprobo fueron mejores que las que habria vetado. Ese numero
decide si se enciende, y hasta entonces no se le da poder sobre
el dinero.

    GEMINI_FILTER_ENABLED=true    lo enciende
    GEMINI_FILTER_MODO=sombra     opina y registra, no bloquea
    GEMINI_FILTER_MODO=bloqueo    puede vetar operaciones

QUE DICE LA EVIDENCIA

Lopez-Lira y Tang midieron que GPT-4 acertaba la direccion de la
reaccion inicial en el 93,3% de los dias con noticias nocturnas, y
que el arbitraje de la deriva posterior daba Sharpe 2,97 ANTES DE
COSTES. Pero:

  - exige ~190% de rotacion diaria
  - deja de ser rentable a 20 puntos basicos de ida y vuelta
  - el Sharpe cayo de 6,54 (2021) a 1,22 (2024) segun mas gente
    uso herramientas de IA

Es decir: como GENERADOR de señales a coste minorista, no sirve.
Por eso aqui se usa como VERIFICADOR de señales que ya existen,
que es una pregunta distinta y mas modesta: no "que va a hacer el
precio" sino "hay alguna noticia que contradiga abiertamente esta
operacion".
"""

import json
import re

import requests

from config import (
    GEMINI_API_KEY,
    REQUEST_TIMEOUT,
    GEMINI_FILTER_ENABLED,
    GEMINI_FILTER_MODO,
    GEMINI_MODELO,
)

MODELO = GEMINI_MODELO
URL_BASE = "https://generativelanguage.googleapis.com/v1beta/models"

HABILITADO = GEMINI_FILTER_ENABLED
MODO = GEMINI_FILTER_MODO

PROMPT = """Eres un verificador de riesgo de noticias. NO predices precios.

Tu unica tarea: decidir si alguna noticia reciente CONTRADICE
abiertamente la operacion propuesta.

Operacion propuesta:
  Activo: {ticker}
  Direccion: {direccion}
  Precio actual: {precio}
  Regimen de mercado detectado: {regimen}

Noticias de las ultimas 48 horas:
{noticias}

Responde SOLO con un JSON, sin texto alrededor:
{{"veredicto": "APROBAR" | "VETAR" | "NEUTRAL",
  "confianza": 0-100,
  "motivo": "una frase corta"}}

Criterios:
- VETAR solo si hay una noticia concreta y reciente que vaya
  claramente en contra de la direccion propuesta (por ejemplo:
  resultados malos, investigacion regulatoria, guidance recortado,
  en una operacion de compra).
- NEUTRAL si no hay noticias relevantes, o son ambiguas, o solo
  hay ruido. Es la respuesta por defecto y la mas habitual.
- APROBAR solo si hay una noticia concreta que apoye la direccion.
- Ante la duda, NEUTRAL. No inventes relaciones.
- No uses conocimiento tuyo posterior sobre lo que le paso a este
  activo: solo los titulares de arriba."""


def _neutral(motivo, fuente="interno"):
    return {
        "veredicto": "NEUTRAL",
        "confianza": 0,
        "motivo": motivo,
        "fuente": fuente,
        "bloquea": False,
    }


def _extraer_json(texto):
    """Gemini a veces envuelve el JSON en ```json ... ```."""
    if not texto:
        return None
    limpio = texto.strip()
    limpio = re.sub(r"^```(?:json)?\s*", "", limpio)
    limpio = re.sub(r"\s*```$", "", limpio)
    try:
        return json.loads(limpio)
    except json.JSONDecodeError:
        encontrado = re.search(r"\{.*\}", limpio, re.DOTALL)
        if encontrado:
            try:
                return json.loads(encontrado.group(0))
            except json.JSONDecodeError:
                return None
    return None


def verificar_operacion(ticker, direccion, precio, regimen, noticias_texto):
    """
    Pide opinion a Gemini sobre una operacion concreta.

    NUNCA lanza excepcion ni bloquea por error: si Gemini no
    responde, devuelve NEUTRAL. Un fallo de la API no puede dejar
    al bot sin operar ni, peor, operando a ciegas creyendo que ha
    sido verificado.
    """
    if not HABILITADO:
        return _neutral("filtro de Gemini desactivado")

    if not GEMINI_API_KEY:
        return _neutral("GEMINI_API_KEY no configurada")

    prompt = PROMPT.format(
        ticker=ticker,
        direccion="COMPRA" if direccion == "BUY" else "VENTA",
        precio=f"{precio:.2f}",
        regimen=regimen,
        noticias=noticias_texto,
    )

    try:
        respuesta = requests.post(
            f"{URL_BASE}/{MODELO}:generateContent",
            params={"key": GEMINI_API_KEY},
            json={
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "temperature": 0.1,
                    "maxOutputTokens": 200,
                    "responseMimeType": "application/json",
                },
            },
            timeout=REQUEST_TIMEOUT,
        )
        respuesta.raise_for_status()
        datos = respuesta.json()

        texto = (datos.get("candidates", [{}])[0]
                      .get("content", {})
                      .get("parts", [{}])[0]
                      .get("text", ""))

        analisis = _extraer_json(texto)
        if not analisis:
            return _neutral(f"respuesta ilegible: {texto[:60]}", "gemini")

        veredicto = str(analisis.get("veredicto", "NEUTRAL")).upper()
        if veredicto not in ("APROBAR", "VETAR", "NEUTRAL"):
            veredicto = "NEUTRAL"

        try:
            confianza = max(0, min(100, int(analisis.get("confianza", 0))))
        except (TypeError, ValueError):
            confianza = 0

        # En modo sombra el veredicto se registra pero no bloquea.
        bloquea = (MODO == "bloqueo" and veredicto == "VETAR" and confianza >= 60)

        return {
            "veredicto": veredicto,
            "confianza": confianza,
            "motivo": str(analisis.get("motivo", ""))[:200],
            "fuente": "gemini",
            "bloquea": bloquea,
        }

    except Exception as e:
        return _neutral(f"{type(e).__name__}: {str(e)[:80]}", "gemini")


def estado():
    """Resumen de como esta configurado, para el arranque."""
    if not HABILITADO:
        return "Filtro de noticias: APAGADO"
    if not GEMINI_API_KEY:
        return "Filtro de noticias: encendido pero SIN CLAVE de Gemini"
    return (f"Filtro de noticias: ENCENDIDO en modo {MODO.upper()} "
            f"({MODELO})"
            + ("  — opina y registra, no bloquea" if MODO == "sombra" else ""))
