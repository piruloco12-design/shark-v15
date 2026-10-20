"""
Evaluador mensual sobre el libro de efectivo. Versión corregida.

QUÉ ARREGLA, respecto a validator/experimento_institucional.py

Aquel motor guardaba los pesos objetivo y no los dejaba derivar con los
precios, así que cada mes comparaba objetivos nuevos contra objetivos viejos
en vez de contra la cartera real. Su «comprar y mantener» era en realidad un
rebalanceo mensual al 50/50, y encima cobraba solo la compra inicial.
Verificado: donde comprar y mantener da 1,0000, devolvía 1,1250.

Aquí no hay pesos guardados. Hay CANTIDADES en un libro de efectivo, que se
mueven solo cuando se ejecuta una orden, y valen lo que valen los precios de
cada día. Un rebalanceo cuesta dinero porque pasa por el libro.

EL ORDEN DE CADA DÍA, que es el de la sección 4.3 de la auditoría:

  1. acciones corporativas y flujos, por su fecha
  2. liquidaciones pendientes
  3. valorar TODAS las posiciones, también las que hoy no cotizan; se
     conserva el último precio conocido y su antigüedad, y no se omite el
     activo del NAV
  4. si hoy toca decisión mensual: construir la vista con lo realmente
     disponible, calcular la señal con reglas congeladas, registrar todo y
     dejar las órdenes PENDIENTES
  5. ejecutar las órdenes pendientes en el siguiente evento negociable, no
     al cierre que se acaba de observar
  6. registrar NAV diario neto

LO QUE SIGUE SIN RESOLVER, y se declara en el resultado

  - No hay fills reales ni bid/ask. El coste es un escenario declarado.
  - La ejecución es al precio de apertura del día siguiente negociable, que
    es un supuesto; no hay datos para modelar colas ni impacto.
  - El universo es el de hoy. Los instrumentos desaparecidos no están, así
    que esto es `EXPLORATORY_SURVIVOR_UNIVERSE` y no una validación.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

_AQUI = os.path.dirname(os.path.abspath(__file__))
_RAIZ = os.path.dirname(_AQUI)
if _RAIZ not in sys.path:
    sys.path.insert(0, _RAIZ)

from evaluador import metricas as M
from libro import Instrumento, LibroContado

ETIQUETA_UNIVERSO = "EXPLORATORY_SURVIVOR_UNIVERSE"


class SinDatosSuficientes(RuntimeError):
    """No hay material para medir. No es un resultado de cero."""


class ConfiguracionInvalida(ValueError):
    """Se pidio una capacidad que nadie ha implementado.

    El plan lo exige explicito: una politica no soportada tiene que dar un
    error de configuracion, no ejecutarse en silencio como si estuviera
    implementada. Antes `politica_terminal` era un campo que NADIE leia:
    se podia declarar cualquier cosa y la corrida salia igual, lo que hace
    que el campo documente una capacidad inexistente.
    """


# Lo que esta implementado de verdad, y nada mas.
# MARCAR: se valora al ultimo cierre y no se paga la salida, que es un
# supuesto OPTIMISTA y declarado. LIQUIDAR: se vende todo al ultimo cierre
# pagando comisiones, asi que el NAV final incluye el coste de salir.
POLITICAS_TERMINALES = ("MARCAR", "LIQUIDAR")
# Que hacer con una posicion cuyo precio se queda obsoleto sin que exista
# un evento de baja declarado.
#   MARCAR_INCERTIDUMBRE: se valora a la ultima marca, el dia se cuenta
#       como NO EVALUABLE y el resultado lo dice. No se inventa ni una
#       perdida total ni una venta al ultimo cierre.
#   EXIGIR_EVENTO: el motor se niega a dar un numero. Modo de
#       investigacion: si no hay evidencia del evento, no hay medicion.
POLITICAS_BAJA = ("MARCAR_INCERTIDUMBRE", "EXIGIR_EVENTO")
POLITICAS_CAJA = ("SIN_REMUNERAR",)
MONEDAS_SOPORTADAS = ("USD",)


@dataclass(frozen=True)
class EventoCorporativo:
    """Un hecho declarado, con su fuente. No se deduce de los precios.

    `LIQUIDACION` exige las cuatro cosas que el plan pide para una baja:
    importe por unidad (el cobro), fecha del evento, fecha de cobro y
    politica de reinversion. Que una serie se termine NO es un evento.
    """

    tipo: str                       # LIQUIDACION | DIVIDENDO | SPLIT
    instrumento: str
    fecha: object
    importe_por_unidad: float = 0.0
    fecha_cobro: object = None
    ratio: float = 1.0
    politica_reinversion: str = "EFECTIVO"
    fuente: str = ""
    event_id: str = ""

    def __post_init__(self):
        if self.tipo not in ("LIQUIDACION", "DIVIDENDO", "SPLIT"):
            raise ConfiguracionInvalida(
                f"tipo de evento no soportado: {self.tipo!r}")
        if not self.fuente:
            raise ConfiguracionInvalida(
                f"el evento {self.tipo} de {self.instrumento} no declara "
                f"FUENTE. Un hecho sin procedencia no es evidencia.")


@dataclass(frozen=True)
class Politicas:
    """Todo lo que hay que congelar ANTES de ver un resultado."""

    capital_inicial: float = 1000.0
    moneda_cuenta: str = "USD"
    coste_rel: float = 0.0008          # por pata, escenario declarado
    coste_fijo: float = 0.0
    dias_liquidacion: int = 0
    permitir_fraccionado: bool = True
    lote: float = 0.0                  # 0 = fraccionable
    # La caja NO se remunera: la cuenta de Brian no lo está. Para medir
    # letras hay que COMPRARLAS como una posición más, con sus costes.
    politica_caja: str = "SIN_REMUNERAR"
    # Antigüedad máxima de un precio para considerarlo admisible al decidir.
    antiguedad_maxima_dias: int = 7
    # Al final: marcar a mercado (no liquidar) salvo que se diga lo
    # contrario. Fijado antes de ver resultados.
    politica_terminal: str = "MARCAR"
    politica_baja: str = "MARCAR_INCERTIDUMBRE"
    calentamiento_sesiones: int = 253
    # M04 basico. None = sin limites, que es como se midio la base. Con
    # limites, la estrategia lleva otro identificador: es otra variante,
    # no un parametro afinado.
    limites: object = None

    def __post_init__(self):
        if self.politica_terminal not in POLITICAS_TERMINALES:
            raise ConfiguracionInvalida(
                f"politica_terminal={self.politica_terminal!r} no esta "
                f"implementada. Implementadas: {POLITICAS_TERMINALES}. "
                f"No se ejecuta una politica que nadie aplica."
            )
        if self.politica_caja not in POLITICAS_CAJA:
            raise ConfiguracionInvalida(
                f"politica_caja={self.politica_caja!r} no esta implementada. "
                f"Implementadas: {POLITICAS_CAJA}. Remunerar la caja exige "
                f"comprar el instrumento, con sus costes."
            )
        if self.politica_baja not in POLITICAS_BAJA:
            raise ConfiguracionInvalida(
                f"politica_baja={self.politica_baja!r} no esta implementada. "
                f"Implementadas: {POLITICAS_BAJA}."
            )
        if self.moneda_cuenta not in MONEDAS_SOPORTADAS:
            raise ConfiguracionInvalida(
                f"moneda_cuenta={self.moneda_cuenta!r}: no hay FX "
                f"implementado y no se asume paridad 1:1. "
                f"Soportadas: {MONEDAS_SOPORTADAS}."
            )

    def a_dict(self):
        d = {}
        for k in self.__dataclass_fields__:
            v = getattr(self, k)
            if k == "limites":
                d[k] = None if v is None else {
                    "max_por_instrumento": v.max_por_instrumento,
                    "max_por_grupo": v.max_por_grupo,
                    "max_exposicion_total": v.max_exposicion_total,
                    "max_posiciones": v.max_posiciones,
                    "reserva_costes": v.reserva_costes,
                    "grupos_declarados": len(v.grupos),
                }
            else:
                d[k] = v
        return d


@dataclass
class Decision:
    """Lo que se decidió, con todo lo necesario para auditarlo."""

    fecha_decision: pd.Timestamp
    fecha_ejecucion: pd.Timestamp | None = None
    pesos_deseados: dict = field(default_factory=dict)
    scores: dict = field(default_factory=dict)
    excluidos: dict = field(default_factory=dict)
    ordenes: list = field(default_factory=list)
    nota: str = ""


# =====================================================================
# Estrategias. Cada una recibe la vista disponible y devuelve PESOS
# deseados sobre el NAV. No tocan el libro: eso lo hace el evaluador.
# =====================================================================

class ComprarYMantener:
    """Compra una vez con cantidades fijas y no vuelve a tocar nada.

    Esto es lo que significa comprar y mantener. Las cantidades quedan
    constantes salvo acciones corporativas. No hay rebalanceo, así que no
    hay operaciones que cobrar después de la compra inicial.
    """

    id = "comprar_y_mantener"
    solo_primera_decision = True

    def __call__(self, vista, elegibles, libro):
        if not elegibles:
            return {}, {}, {}
        peso = 1.0 / len(elegibles)
        return {t: peso for t in elegibles}, {}, {}


class RebalanceoEquiponderado:
    """Vuelve a pesos iguales cada mes. Y lo paga.

    Es una estrategia DISTINTA de comprar y mantener, y es la que el motor
    viejo medía creyendo medir la otra. Aquí existe con su nombre y sus
    costes.
    """

    id = "rebalanceo_equiponderado"
    solo_primera_decision = False

    def __call__(self, vista, elegibles, libro):
        if not elegibles:
            return {}, {}, {}
        peso = 1.0 / len(elegibles)
        return {t: peso for t in elegibles}, {}, {}


class M03Momentum:
    """Los K mejores por retorno de 12 meses saltando el último."""

    solo_primera_decision = False

    def __init__(self, k=5, lookback=252, skip=21):
        self.k, self.lookback, self.skip = k, lookback, skip
        self.id = f"M03_momentum_{lookback}_{skip}_k{k}"

    def __call__(self, vista, elegibles, libro):
        from institucional.referencia import DataError, momentum_score, rank_positive
        scores, excluidos = {}, {}
        for t in elegibles:
            serie = vista[t].dropna()
            if len(serie) < self.lookback + 1:
                excluidos[t] = f"historico {len(serie)} < {self.lookback + 1}"
                continue
            try:
                scores[t] = momentum_score(serie.tolist(), self.lookback,
                                           self.skip)
            except DataError as e:
                excluidos[t] = f"score: {str(e)[:40]}"
        elegidos = rank_positive(scores, self.k) if scores else ()
        if not elegidos:
            return {}, scores, excluidos
        peso = 1.0 / len(elegidos)
        return {t: peso for t in elegidos}, scores, excluidos


class M02Tendencia:
    """Largo en cada activo cuyo exceso sobre el efectivo es positivo."""

    solo_primera_decision = False

    def __init__(self, serie_efectivo, lookback=252, ventana_vol=63):
        self.efectivo = serie_efectivo
        self.lookback, self.ventana_vol = lookback, ventana_vol
        self.id = f"M02_tendencia_{lookback}_{ventana_vol}"

    def __call__(self, vista, elegibles, libro):
        from institucional.referencia import DataError, trend_signal
        largos, scores, excluidos = [], {}, {}
        cash = self.efectivo.loc[self.efectivo.index <= vista.index[-1]].dropna()
        for t in elegibles:
            serie = vista[t].dropna()
            comun = serie.index.intersection(cash.index)
            minimo = max(self.lookback, self.ventana_vol) + 1
            if len(comun) < minimo:
                excluidos[t] = f"alineado {len(comun)} < {minimo}"
                continue
            try:
                s = trend_signal(serie.loc[comun].tolist(),
                                 cash.loc[comun].tolist(),
                                 self.lookback, self.ventana_vol, 252)
            except DataError as e:
                excluidos[t] = f"senal: {str(e)[:40]}"
                continue
            scores[t] = round(s.trailing_excess_return, 6)
            if s.side == 1:
                largos.append(t)
        if not largos:
            return {}, scores, excluidos
        peso = 1.0 / len(largos)
        return {t: peso for t in sorted(largos)}, scores, excluidos


# =====================================================================

class EvaluadorMensual:
    """Corre una estrategia mensual sobre un libro de efectivo real."""

    def __init__(self, series: dict, politicas: Politicas,
                 fechas_decision=None, eventos=None):
        if not series:
            raise SinDatosSuficientes("sin series")
        self.pol = politicas
        # Eventos corporativos DECLARADOS, agrupados por fecha. No se
        # deducen de los precios: una serie que se termina no es un evento.
        self.eventos: dict = {}
        for ev in (eventos or []):
            f = pd.Timestamp(ev.fecha)
            f = f.tz_localize("UTC") if f.tz is None else f.tz_convert("UTC")
            self.eventos.setdefault(f.normalize(), []).append(ev)
        self.series = {t: self._normalizar(df) for t, df in series.items()}

        # Calendario de precios: la unión de todas las fechas. Cada
        # instrumento solo negocia en las suyas.
        todas = sorted(set().union(*[set(df.index) for df in self.series.values()]))
        if len(todas) < politicas.calentamiento_sesiones + 40:
            raise SinDatosSuficientes(
                f"solo {len(todas)} sesiones; hacen falta al menos "
                f"{politicas.calentamiento_sesiones + 40}")
        self.fechas = todas

        # El calentamiento se usa SOLO para calcular indicadores. La
        # evaluación (y el NAV) empieza después, y empieza en la misma
        # fecha para la candidata y para los benchmarks.
        self.inicio_evaluacion = todas[politicas.calentamiento_sesiones]
        self.fechas_decision = (list(fechas_decision)
                                if fechas_decision is not None
                                else self._cierres_mensuales_validos())

    # ---- preparación ----

    @staticmethod
    def _normalizar(df):
        d = df.copy()
        if not isinstance(d.index, pd.DatetimeIndex):
            raise SinDatosSuficientes("se requiere DatetimeIndex")
        idx = d.index.normalize()
        d.index = idx.tz_localize("UTC") if idx.tz is None else idx.tz_convert("UTC")
        d = d[~d.index.duplicated(keep="last")].sort_index()
        for col in ("Open", "High", "Low", "Close"):
            if col not in d.columns:
                raise SinDatosSuficientes(f"falta la columna {col}")
        return d

    def _cierres_mensuales_validos(self):
        """Últimas sesiones de cada mes COMPLETO del calendario.

        El motor viejo tomaba la última fila de la serie como cierre
        mensual aunque cayera a día 13. Aquí el último mes se descarta si
        no está completo: una fecha a mitad de mes vale para VALORAR, no
        para decidir un rebalanceo mensual.
        """
        idx = pd.DatetimeIndex(self.fechas)
        clave = idx.year * 100 + idx.month
        ultimo_mes = clave[-1]
        salida = []
        for k in sorted(set(clave)):
            if k == ultimo_mes:
                # ¿Está completo? Hay datos posteriores a este mes solo si
                # existe otro mes después, que por definición no hay.
                # Se descarta: no sabemos si el mes acabó.
                continue
            fechas_mes = idx[clave == k]
            salida.append(fechas_mes[-1])
        return [f for f in salida if f >= self.inicio_evaluacion]

    def _precio_de(self, t, fecha, col):
        """Precio de una columna en una fecha, o None si no es admisible."""
        df = self.series[t]
        if fecha not in df.index:
            return None
        v = float(df.at[fecha, col])
        return v if np.isfinite(v) and v > 0 else None

    def _siguiente_negociable(self, instrumento, despues_de):
        """Primera fecha en la que ESE instrumento vuelve a negociar."""
        idx = self.series[instrumento].index
        posteriores = idx[idx > despues_de]
        return posteriores[0] if len(posteriores) else None

    def _vista(self, hasta):
        """Panel de cierres visible en `hasta`, inclusive, sin rellenar."""
        datos = {}
        for t, df in self.series.items():
            s = df.loc[df.index <= hasta, "Close"]
            if len(s):
                datos[t] = s
        return pd.DataFrame(datos)

    def _elegibles(self, hasta):
        """Instrumentos con precio admisible y no demasiado antiguo."""
        elegibles = []
        for t, df in self.series.items():
            s = df.loc[df.index <= hasta]
            if len(s) < 2:
                continue
            edad = (hasta - s.index[-1]).days
            if edad > self.pol.antiguedad_maxima_dias:
                continue
            if not np.isfinite(s["Close"].iloc[-1]) or s["Close"].iloc[-1] <= 0:
                continue
            elegibles.append(t)
        return sorted(elegibles)

    # ---- bucle ----

    def correr(self, estrategia) -> dict:
        libro = LibroContado(
            self.pol.capital_inicial, self.pol.moneda_cuenta,
            dias_liquidacion=self.pol.dias_liquidacion,
            permitir_fraccionado=self.pol.permitir_fraccionado)
        for t in self.series:
            libro.registrar_instrumento(Instrumento(t, lote=self.pol.lote))

        decisiones: list[Decision] = []
        pendientes: list[tuple] = []        # (fecha_ejec, instrumento, lado, cantidad)
        nav_diario: dict = {}
        ultimo_precio: dict = {}        # marca de CIERRE: t -> (precio, fecha)
        calidad_marca: dict = {}        # t -> (origen, antiguedad_dias)
        libro_diario: dict = {}         # trayectoria: caja, derechos, NAV...
        incidencias: list = []
        ya_decidio_una_vez = False
        fechas_decision = set(self.fechas_decision)

        no_evaluables: set = set()

        for fecha in self.fechas:
            # --- 1) ACCIONES CORPORATIVAS declaradas, una sola vez ---
            # Van antes de liquidar: el orden lo fija el plan. La
            # idempotencia la garantiza el event_id del libro.
            for ev in self.eventos.get(fecha, []):
                eid = ev.event_id or f"{ev.tipo}-{ev.instrumento}-{fecha.date()}"
                if ev.tipo == "LIQUIDACION":
                    libro.liquidar_instrumento(
                        ev.instrumento, ev.importe_por_unidad, fecha,
                        ev.fecha_cobro, event_id=eid,
                        politica_reinversion=ev.politica_reinversion,
                        fuente=ev.fuente)
                elif ev.tipo == "DIVIDENDO":
                    libro.dividendo(ev.instrumento, ev.importe_por_unidad,
                                    fecha, ev.fecha_cobro, event_id=eid)
                elif ev.tipo == "SPLIT":
                    libro.split(ev.instrumento, ev.ratio, fecha)

            # --- 2) liquidaciones pendientes ---
            libro.liquidar_pendientes(fecha)

            # --- 2) EVENTO DE EJECUCION: vista de precios observable AHORA ---
            # Para admitir una orden solo puede mirarse lo que existe antes
            # de enviarla: la apertura de hoy y las marcas anteriores. Nunca
            # el cierre, el maximo ni el minimo de la sesion en curso.
            # La version anterior valoraba con el CIERRE de hoy antes de
            # ejecutar, que es leer el futuro de la propia sesion.
            for t in self.series:
                if libro.cantidad(t) <= 0:
                    continue
                ap = self._precio_de(t, fecha, "Open")
                if ap is not None:
                    libro.valorar(t, ap, fecha)
                elif t in ultimo_precio:
                    libro.valorar(t, ultimo_precio[t][0], ultimo_precio[t][1])

            # --- 3) ejecutar lo que vencía hoy ---
            # (va antes de decidir: una orden decidida hoy se ejecuta
            #  mañana, nunca en la misma vela que la generó)
            restantes = []
            for f_ejec, t, lado, cantidad, f_dec, precio_dec in pendientes:
                if f_ejec != fecha:
                    restantes.append((f_ejec, t, lado, cantidad, f_dec,
                                      precio_dec))
                    continue
                if fecha not in self.series[t].index:
                    # No negoció: se reintenta en su siguiente sesión.
                    nueva = self._siguiente_negociable(t, fecha)
                    if nueva is not None:
                        restantes.append((nueva, t, lado, cantidad, f_dec,
                                          precio_dec))
                    continue
                precio_ejec = float(self.series[t].at[fecha, "Open"])
                if not np.isfinite(precio_ejec) or precio_ejec <= 0:
                    precio_ejec = float(self.series[t].at[fecha, "Close"])
                if lado == "COMPRA":
                    # LIMITE DE ADMISION: el tope se recomprueba con el
                    # precio al que de verdad se va a ejecutar, no con el
                    # del dia de la decision. Antes el tope solo tocaba el
                    # objetivo mensual: con el objetivo al 40% fijado a un
                    # cierre de 100 y una apertura a 200, las unidades
                    # compradas eran el 80% del patrimonio e iban
                    # informadas como tope duro del 40%.
                    pedida = cantidad
                    nota_adm = ""
                    if self.pol.limites is not None:
                        from limites_cartera import admitir as _admitir
                        cantidad, nota_adm = _admitir(
                            pedida, t, precio_ejec, libro, self.pol.limites,
                            coste_rel=self.pol.coste_rel)
                    if cantidad <= 0:
                        libro.rechazar(
                            t, pedida, precio_ejec, fecha, tipo="COMPRA",
                            motivo=estrategia.id,
                            rechazo=f"ADMISION: {nota_adm}",
                            precio_decision=precio_dec,
                            momento_decision=f_dec,
                            cantidad_pre_admision=pedida)
                        if nota_adm:
                            incidencias.append({
                                "fecha": str(fecha), "instrumento": t,
                                "motivo": f"admision rechazo la compra: {nota_adm}",
                            })
                        continue
                    libro.comprar(t, cantidad, precio_ejec, fecha,
                                  coste_rel=self.pol.coste_rel,
                                  coste_fijo=self.pol.coste_fijo,
                                  precio_decision=precio_dec,
                                  momento_decision=f_dec,
                                  motivo=estrategia.id,
                                  cantidad_pre_admision=pedida)
                    if nota_adm:
                        incidencias.append({
                            "fecha": str(fecha), "instrumento": t,
                            "motivo": f"admision recorto la compra: {nota_adm}",
                        })
                else:
                    libro.vender(t, cantidad, precio_ejec, fecha,
                                 coste_rel=self.pol.coste_rel,
                                 coste_fijo=self.pol.coste_fijo,
                                 precio_decision=precio_dec,
                                 momento_decision=f_dec,
                                 motivo=estrategia.id)
            pendientes = restantes

            # --- 4) CIERRE DE SESION: marcar TODAS las posiciones ---
            # Esta es la puerta V01/V02 y el hallazgo A01. Antes se valoraba
            # ANTES de los fills, y el propio fill reescribia
            # `precio_valoracion` con su precio de ejecucion: en un dia con
            # operacion, lo comprado quedaba a la apertura y el resto al
            # cierre. El NAV mezclaba precios de dos instantes y la ganancia
            # del dia llegaba un dia tarde.
            for t in self.series:
                cierre = self._precio_de(t, fecha, "Close")
                if cierre is not None:
                    ultimo_precio[t] = (cierre, fecha)
                    calidad_marca[t] = ("CIERRE", 0)
                if libro.cantidad(t) <= 0:
                    continue
                if t not in ultimo_precio:
                    # Posicion abierta sin ninguna marca admisible. No se
                    # borra la fecha para fabricar continuidad: se marca.
                    incidencias.append({
                        "fecha": str(fecha), "instrumento": t,
                        "motivo": "posicion sin precio de valoracion admisible",
                    })
                    continue
                precio_marca, fecha_marca = ultimo_precio[t]
                if cierre is None:
                    edad = int((fecha - fecha_marca).days)
                    calidad_marca[t] = ("ARRASTRE", edad)
                    if edad > self.pol.antiguedad_maxima_dias:
                        # Posicion viva sin precio admisible y SIN evento de
                        # baja declarado. No se inventa ni la perdida total
                        # ni la venta al ultimo cierre: se valora a la
                        # ultima marca y el dia queda marcado NO EVALUABLE,
                        # que es lo que el plan pide. Si no hay evidencia
                        # del evento, no hay medicion limpia.
                        calidad_marca[t] = ("NO_EVALUABLE", edad)
                        no_evaluables.add(fecha)
                        incidencias.append({
                            "fecha": str(fecha), "instrumento": t,
                            "motivo": f"marca de {edad} dias sin evento de "
                                      f"baja declarado: dia no evaluable",
                        })
                        if self.pol.politica_baja == "EXIGIR_EVENTO":
                            raise SinDatosSuficientes(
                                f"{t} lleva {edad} dias sin precio admisible "
                                f"y no hay evento de baja declarado. Con "
                                f"politica_baja=EXIGIR_EVENTO no se emite un "
                                f"NAV: hace falta el evento, su importe por "
                                f"unidad, su fecha y su fuente."
                            )
                libro.valorar(t, precio_marca, fecha_marca)

            # --- 5) decisión mensual ---
            if fecha in fechas_decision:
                salta = (getattr(estrategia, "solo_primera_decision", False)
                         and ya_decidio_una_vez)
                if not salta:
                    d = self._decidir(estrategia, fecha, libro, ultimo_precio)
                    decisiones.append(d)
                    pendientes.extend(d.ordenes)
                    ya_decidio_una_vez = True

            # --- 6) guardar caja, derechos, obligaciones, reservas,
            #        cantidades y NAV. La exposicion media exige la
            #        trayectoria: antes se reconstruia de los pesos del
            #        ultimo dia, que no es una media de nada.
            if fecha >= self.inicio_evaluacion:
                try:
                    nav = libro.nav()
                    valor_pos = libro.valor_posiciones()
                    nav_diario[fecha] = nav
                    libro_diario[fecha] = {
                        "efectivo": libro.efectivo,
                        "derechos": libro.derechos,
                        "obligaciones": libro.obligaciones,
                        "reservado": libro.reservado,
                        "valor_posiciones": valor_pos,
                        "nav": nav,
                        "posiciones": sum(1 for p in libro.posiciones.values()
                                          if p.cantidad > 0),
                        "expuesto": (valor_pos / nav) if nav > 0 else float("nan"),
                        "calidad": ";".join(
                            f"{t}:{c[0]}" for t, c in sorted(calidad_marca.items())
                            if libro.cantidad(t) > 0 and c[0] != "CIERRE") or "CIERRE",
                        "no_evaluable": fecha in no_evaluables,
                        # Concentracion desde los PESOS REALES de esta
                        # fecha, por instrumento y por grupo. Antes solo
                        # existia la del ultimo dia, y una media de la
                        # exposicion se "reconstruia" de ahi, que no es
                        # una media de nada.
                        "peso_maximo": _peso_maximo(libro, nav),
                        "peso_grupo_mayor": _peso_grupo_mayor(libro, nav),
                    }
                except Exception as e:
                    nav_diario[fecha] = float("nan")
                    libro_diario[fecha] = {"nav": float("nan"),
                                           "calidad": f"NO_EVALUABLE: {str(e)[:60]}"}
                    incidencias.append({"fecha": str(fecha), "instrumento": "",
                                        "motivo": f"NAV no fiable: {str(e)[:80]}"})
                    if len(decisiones):
                        decisiones[-1].nota = f"NAV no fiable: {str(e)[:60]}"

        # --- politica terminal ---
        # MARCAR deja las posiciones abiertas valoradas al ultimo cierre.
        # LIQUIDAR las vende y COBRA el coste de salir: el NAV final deja de
        # suponer que se sale gratis. El campo existia y nadie lo leia.
        if self.pol.politica_terminal == "LIQUIDAR" and len(self.fechas):
            fecha_fin = self.fechas[-1]
            for t in sorted(list(libro.posiciones)):
                q = libro.cantidad(t)
                if q <= 0:
                    continue
                precio = ultimo_precio.get(t, (None, None))[0]
                if precio is None:
                    incidencias.append({
                        "fecha": str(fecha_fin), "instrumento": t,
                        "motivo": "politica terminal LIQUIDAR sin precio "
                                  "admisible: la posicion queda abierta",
                    })
                    continue
                libro.vender(t, q, precio, fecha_fin,
                             coste_rel=self.pol.coste_rel,
                             coste_fijo=self.pol.coste_fijo,
                             motivo="POLITICA_TERMINAL_LIQUIDAR")
            # El dinero de la venta puede quedar como DERECHO si hay dias de
            # liquidacion. No se fuerza el cobro: inventar una fecha de
            # liquidacion que no ha ocurrido seria fabricar un hecho. El
            # derecho ya cuenta en el NAV, asi que el NAV no cambia por eso.
            if fecha_fin in nav_diario:
                nav_f = libro.nav()
                nav_diario[fecha_fin] = nav_f
                libro_diario[fecha_fin] = {
                    "efectivo": libro.efectivo, "derechos": libro.derechos,
                    "obligaciones": libro.obligaciones,
                    "reservado": libro.reservado,
                    "valor_posiciones": libro.valor_posiciones(),
                    "nav": nav_f,
                    "posiciones": sum(1 for p in libro.posiciones.values()
                                      if p.cantidad > 0),
                    "expuesto": (libro.valor_posiciones() / nav_f)
                    if nav_f > 0 else float("nan"),
                    "calidad": "TERMINAL_LIQUIDADO",
                }

        serie_nav = pd.Series(nav_diario).sort_index()
        res = self._resultado(estrategia, libro, decisiones, serie_nav)
        res["_ledger_diario"] = pd.DataFrame(libro_diario).T.sort_index()
        res["incidencias_valoracion"] = incidencias
        evaluados = [f for f in nav_diario if f >= self.inicio_evaluacion]
        dias_no_eval = sum(1 for f in evaluados if f in no_evaluables)
        res["dias_no_evaluables"] = dias_no_eval
        # Una cifra con dias no evaluables dentro no es una medicion limpia,
        # y el resultado lo dice en vez de dejarlo en una incidencia que
        # nadie lee.
        res["nav_fiable"] = bool(dias_no_eval == 0)
        res["eventos_aplicados"] = sum(len(v) for v in self.eventos.values())
        return res

    def _decidir(self, estrategia, fecha, libro, ultimo_precio) -> Decision:
        vista = self._vista(fecha)
        elegibles = self._elegibles(fecha)
        pesos, scores, excluidos = estrategia(vista, elegibles, libro)

        # M04 basico: topes por instrumento, grupo, numero de posiciones y
        # exposicion total. El sobrante se queda en EFECTIVO; redistribuirlo
        # violaria el tope que acaba de aplicarse.
        nota_limites = ""
        if self.pol.limites is not None:
            from limites_cartera import aplicar as _aplicar_limites
            pesos, diag_lim = _aplicar_limites(pesos, self.pol.limites)
            if diag_lim.get("recortes"):
                nota_limites = "M04: " + ", ".join(
                    r["tipo"] for r in diag_lim["recortes"])

        d = Decision(fecha_decision=fecha, pesos_deseados=dict(pesos),
                     scores=dict(scores), excluidos=dict(excluidos),
                     nota=nota_limites)

        nav = libro.nav()
        ordenes = []

        # Primero las VENTAS: liberan efectivo para las compras.
        for t in sorted(libro.posiciones):
            objetivo = pesos.get(t, 0.0)
            precio = ultimo_precio.get(t, (None, None))[0]
            if precio is None:
                continue
            cantidad_objetivo = (objetivo * nav / precio) if objetivo > 0 else 0.0
            exceso = libro.cantidad(t) - cantidad_objetivo
            if exceso > 1e-9:
                f = self._siguiente_negociable(t, fecha)
                if f is not None:
                    ordenes.append((f, t, "VENTA", exceso, fecha, precio))

        # Luego las COMPRAS, en orden estable.
        for t in sorted(pesos):
            objetivo = pesos[t]
            precio = ultimo_precio.get(t, (None, None))[0]
            if precio is None or objetivo <= 0:
                continue
            cantidad_objetivo = objetivo * nav / precio
            falta = cantidad_objetivo - libro.cantidad(t)
            if falta > 1e-9:
                f = self._siguiente_negociable(t, fecha)
                if f is not None:
                    ordenes.append((f, t, "COMPRA", falta, fecha, precio))

        d.ordenes = ordenes
        d.fecha_ejecucion = min((o[0] for o in ordenes), default=None)
        return d

    def _id_estrategia(self, estrategia) -> str:
        """Con limites activos es OTRA variante, y se nota en el nombre."""
        base = estrategia.id
        if self.pol.limites is None:
            return base
        lim = self.pol.limites
        return (f"{base}+M04_i{lim.max_por_instrumento:.2f}"
                f"_g{lim.max_por_grupo:.2f}_e{lim.max_exposicion_total:.2f}"
                f"_n{lim.max_posiciones}")

    def _resultado(self, estrategia, libro, decisiones, nav_diario) -> dict:
        nav_diario = nav_diario.dropna()
        if len(nav_diario) < 30:
            raise SinDatosSuficientes(
                f"solo {len(nav_diario)} observaciones de NAV")

        mensual = nav_diario.resample("ME").last().dropna()
        id_est = self._id_estrategia(estrategia)
        res = M.resumen(nav_diario, nav_mensual=mensual, etiqueta=id_est)

        intenciones = [m for m in libro.movimientos
                       if m.tipo in ("COMPRA", "VENTA")]
        ejecutadas = [m for m in intenciones if m.cantidad_ejecutada > 0]
        comisiones = sum(m.costes.get("comision", 0.0) for m in ejecutadas)
        nominal = sum(m.costes.get("nominal", 0.0) for m in ejecutadas)

        meses_invertidos = sum(1 for _, _ in mensual.items())
        pesos_fin = libro.pesos()

        res.update({
            "estrategia_id": id_est,
            "estrategia_base_id": estrategia.id,
            "universo_etiqueta": ETIQUETA_UNIVERSO,
            "politicas": self.pol.a_dict(),
            "decisiones": len(decisiones),
            "intenciones": len(intenciones),
            "intenciones_ejecutadas": len(ejecutadas),
            "intenciones_rechazadas": len(intenciones) - len(ejecutadas),
            "comisiones_moneda": round(comisiones, 6),
            "nominal_ejecutado": round(nominal, 2),
            "coste_sobre_nominal_pb": round(comisiones / nominal * 10000, 2)
            if nominal > 0 else None,
            "coste_por_intencion_moneda": round(comisiones / len(ejecutadas), 6)
            if ejecutadas else None,
            # ROTACION, con su convencion dicha. El nominal suma AMBAS
            # patas: cada compra y cada venta por su propio nominal, y la
            # entrada inicial cuenta. El denominador es el patrimonio
            # MEDIO gestionado, no el capital inicial.
            #
            # La cifra anterior dividia todo el nominal por el capital
            # INICIAL, lo que mezcla dos cosas: en una cartera que
            # multiplica por seis su patrimonio, el nominal negociado del
            # ultimo ano se compara con el capital del primer dia. Asi
            # salian 14,477 donde la rotacion sobre patrimonio es 5,297.
            # Se conserva la vieja con un nombre que dice lo que es, para
            # que no se confundan al comparar con cifras publicadas antes.
            "rotacion_convencion": ("nominal de ambas patas, entrada inicial "
                                    "incluida, sobre patrimonio medio"),
            "rotacion_anual_sobre_patrimonio_medio": round(
                nominal / res["anos"] / float(nav_diario.mean()), 3)
            if res["anos"] > 0 and float(nav_diario.mean()) > 0 else None,
            "rotacion_anual_nominal_sobre_capital_inicial": round(
                nominal / res["anos"] / self.pol.capital_inicial, 3)
            if res["anos"] > 0 else None,
            "concentracion_final": libro.concentracion(),
            "pesos_finales": {k: round(v, 5) for k, v in pesos_fin.items()},
            "estado_libro_final": libro.estado(),
            "meses_evaluados": meses_invertidos,
            "_nav": nav_diario,
            "_nav_mensual": mensual,
            "_decisiones": decisiones,
            "_libro": libro,
        })
        return res


def _peso_maximo(libro, nav) -> float:
    """Peso del instrumento mas grande sobre el patrimonio, hoy."""
    if not (nav > 0):
        return float("nan")
    mayor = 0.0
    for iid, pos in libro.posiciones.items():
        if pos.cantidad <= 0:
            continue
        mult = getattr(libro.instrumentos.get(iid), "multiplicador", 1.0)
        mayor = max(mayor, pos.cantidad * pos.precio_valoracion * mult)
    return mayor / nav


def _peso_grupo_mayor(libro, nav) -> float:
    """Peso del grupo mas grande sobre el patrimonio, hoy."""
    if not (nav > 0):
        return float("nan")
    try:
        from limites_cartera import GRUPOS_UNIVERSO as _G
    except Exception:
        _G = {}
    por_grupo: dict = {}
    for iid, pos in libro.posiciones.items():
        if pos.cantidad <= 0:
            continue
        mult = getattr(libro.instrumentos.get(iid), "multiplicador", 1.0)
        g = _G.get(iid, iid)
        por_grupo[g] = por_grupo.get(g, 0.0) + pos.cantidad * pos.precio_valoracion * mult
    return (max(por_grupo.values()) / nav) if por_grupo else 0.0


def exposicion_media(resultado) -> dict:
    """Parte del NAV que estuvo invertida, después del calentamiento.

    El motor viejo informaba «93,3%» que en realidad era 168 meses
    invertidos de 180, mezclando calentamiento con periodo evaluable.
    Son dos cosas distintas y aquí van separadas.
    """
    libro = resultado["_libro"]
    nav = resultado["_nav"]
    meses = resultado["_nav_mensual"]
    salida = {
        "meses_evaluados": len(meses),
        "observaciones_diarias": len(nav),
        "posiciones_al_final": len(libro.posiciones),
        "peso_invertido_al_final": round(
            sum(libro.pesos().values()), 4),
    }
    # Ya NO es trabajo pendiente: la trayectoria diaria existe, asi que la
    # media se calcula recorriendola en vez de reconstruirla del ultimo
    # dia, que es lo que hacia la nota anterior de este diccionario.
    ld = resultado.get("_ledger_diario")
    if ld is not None and len(ld) and "expuesto" in ld:
        exp = pd.to_numeric(ld["expuesto"], errors="coerce").dropna()
        pmax = pd.to_numeric(ld.get("peso_maximo"), errors="coerce").dropna() \
            if "peso_maximo" in ld else pd.Series(dtype="float64")
        pgrp = pd.to_numeric(ld.get("peso_grupo_mayor"), errors="coerce").dropna() \
            if "peso_grupo_mayor" in ld else pd.Series(dtype="float64")
        salida.update({
            "exposicion_media_real": round(float(exp.mean()), 6) if len(exp) else None,
            "exposicion_mediana": round(float(exp.median()), 6) if len(exp) else None,
            "dias_con_trayectoria": int(len(exp)),
            "peso_maximo_medio": round(float(pmax.mean()), 6) if len(pmax) else None,
            "peso_grupo_mayor_medio": round(float(pgrp.mean()), 6) if len(pgrp) else None,
            "peso_grupo_mayor_maximo": round(float(pgrp.max()), 6) if len(pgrp) else None,
        })
    return salida
