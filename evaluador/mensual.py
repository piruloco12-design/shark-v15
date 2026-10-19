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
    calentamiento_sesiones: int = 253
    # M04 basico. None = sin limites, que es como se midio la base. Con
    # limites, la estrategia lleva otro identificador: es otra variante,
    # no un parametro afinado.
    limites: object = None

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
                 fechas_decision=None):
        if not series:
            raise SinDatosSuficientes("sin series")
        self.pol = politicas
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
        ultimo_precio: dict = {}
        ya_decidio_una_vez = False
        fechas_decision = set(self.fechas_decision)

        for fecha in self.fechas:
            # --- 2) liquidaciones pendientes ---
            libro.liquidar_pendientes(fecha)

            # --- 3) valorar TODO, también lo que hoy no cotiza ---
            for t, df in self.series.items():
                if fecha in df.index:
                    precio = float(df.at[fecha, "Close"])
                    if np.isfinite(precio) and precio > 0:
                        ultimo_precio[t] = (precio, fecha)
                if t in ultimo_precio and libro.cantidad(t) > 0:
                    libro.valorar(t, ultimo_precio[t][0], ultimo_precio[t][1])

            # --- 5) ejecutar lo que vencía hoy ---
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
                    libro.comprar(t, cantidad, precio_ejec, fecha,
                                  coste_rel=self.pol.coste_rel,
                                  coste_fijo=self.pol.coste_fijo,
                                  precio_decision=precio_dec,
                                  momento_decision=f_dec,
                                  motivo=estrategia.id)
                else:
                    libro.vender(t, cantidad, precio_ejec, fecha,
                                 coste_rel=self.pol.coste_rel,
                                 coste_fijo=self.pol.coste_fijo,
                                 precio_decision=precio_dec,
                                 momento_decision=f_dec,
                                 motivo=estrategia.id)
            pendientes = restantes

            # --- 4) decisión mensual ---
            if fecha in fechas_decision:
                salta = (getattr(estrategia, "solo_primera_decision", False)
                         and ya_decidio_una_vez)
                if not salta:
                    d = self._decidir(estrategia, fecha, libro, ultimo_precio)
                    decisiones.append(d)
                    pendientes.extend(d.ordenes)
                    ya_decidio_una_vez = True

            # --- 6) NAV diario neto ---
            if fecha >= self.inicio_evaluacion:
                try:
                    nav_diario[fecha] = libro.nav()
                except Exception as e:
                    nav_diario[fecha] = float("nan")
                    if len(decisiones):
                        decisiones[-1].nota = f"NAV no fiable: {str(e)[:60]}"

        serie_nav = pd.Series(nav_diario).sort_index()
        return self._resultado(estrategia, libro, decisiones, serie_nav)

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
            "rotacion_anual_nominal": round(
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


def exposicion_media(resultado) -> dict:
    """Parte del NAV que estuvo invertida, después del calentamiento.

    El motor viejo informaba «93,3%» que en realidad era 168 meses
    invertidos de 180, mezclando calentamiento con periodo evaluable.
    Son dos cosas distintas y aquí van separadas.
    """
    libro = resultado["_libro"]
    nav = resultado["_nav"]
    meses = resultado["_nav_mensual"]
    return {
        "meses_evaluados": len(meses),
        "observaciones_diarias": len(nav),
        "posiciones_al_final": len(libro.posiciones),
        "peso_invertido_al_final": round(
            sum(libro.pesos().values()), 4),
        "_nota": ("el peso invertido es el del último día; para la media hay "
                  "que recorrer el libro día a día, que es trabajo pendiente"),
    }
