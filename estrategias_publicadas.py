"""
ESTRATEGIAS PUBLICADAS — implementadas como CANDIDATAS A MEDIR.

Brian pidio "las estrategias mas rentables" de internet. Esto es lo que
hay: las tres mas documentadas y mas faciles de encontrar buscando, con la
regla exacta tal y como la publico su autor, su fuente, y **el resultado
que el paper reclama**, escrito aqui al lado de la regla.

Por que el reclamo va en el codigo: para que la medicion sobre el panel
real se pueda comparar con lo que prometia, y la diferencia quede a la
vista en vez de en mi memoria.

Lo que la evidencia dice de antemano, y conviene leer antes de mirar
cualquier numero de aqui:

  McLean y Pontiff (Journal of Finance, 2016) siguieron 97 predictores de
  97 variables publicadas en 79 estudios revisados por pares. Los
  retornos caen un 26% fuera de muestra y un 58% tras publicarse. En media
  mensual larga-corta: 0,582% en muestra, 0,402% fuera de muestra, 0,264%
  despues de publicarse.

  Ese 0,264% mensual son unos 3,2 puntos anuales BRUTOS. Sobre una cuenta
  de 1.000 con comision minima por orden, nosotros medimos que las
  comisiones se comen entre 3 y 8 puntos anuales. O sea: la ventaja media
  de un predictor publicado es MENOR que el coste de operarlo a este
  tamano. Eso no es una opinion sobre estas tres estrategias; es el punto
  de partida con el que hay que leerlas.

Ninguna de estas clases decide nada por si sola. Son candidatas que el
evaluador mide, con su identificador y su registro, igual que M02 y M03.
"""
from __future__ import annotations

import math


def _sma(valores, ventana):
    if len(valores) < ventana:
        return None
    trozo = valores[-ventana:]
    return sum(trozo) / float(ventana)


def _retorno(valores, periodos):
    if len(valores) < periodos + 1:
        return None
    a, b = float(valores[-periodos - 1]), float(valores[-1])
    if not (a > 0) or not (b > 0):
        return None
    return b / a - 1.0


def _vol(valores, ventana):
    if len(valores) < ventana + 1:
        return None
    rs = []
    for i in range(len(valores) - ventana, len(valores)):
        a, b = float(valores[i - 1]), float(valores[i])
        if a > 0 and b > 0:
            rs.append(b / a - 1.0)
    if len(rs) < 2:
        return None
    m = sum(rs) / len(rs)
    var = sum((r - m) ** 2 for r in rs) / (len(rs) - 1)
    return math.sqrt(var) * math.sqrt(252.0)


# =====================================================================

class FaberTiempoMercado:
    """Faber: comprar si el cierre mensual supera su media de 10 meses.

    FUENTE
        Mebane T. Faber, "A Quantitative Approach to Tactical Asset
        Allocation", Journal of Wealth Management, 2007; revisado en
        Journal of Portfolio Management 2017, 44(2):156-167, "Revisited
        10 Years Later".

    REGLA, literal del paper
        Comprar cuando el precio mensual > media simple de 10 meses.
        Vender y pasar a efectivo cuando el precio mensual < esa media.
        La senal se mira SOLO al cierre del ultimo dia de cada mes, y la
        entrada y la salida son a ese cierre.

        En la version de cartera (QTAA), cinco clases al 20% cada una, y
        cada clase se temporiza por separado: o se tiene, o su 20% se
        queda en EFECTIVO.

    EL DETALLE QUE CASI TODO EL MUNDO FALSEA
        El 20% de una clase que esta bajo su media NO se reparte entre las
        demas. Se queda en efectivo. Repartirlo convierte la estrategia en
        otra cosa, con mas concentracion y mas riesgo, y suele mejorar el
        backtest. Aqui se implementa como la publico: peso 1/N fijo por
        activo, y lo que no esta invertido es caja.

    LO QUE RECLAMA
        El paper original (datos hasta 2005) dice que temporizar mejora el
        retorno compuesto reduciendo riesgo y caidas. La revision del
        propio autor a diez anos dice tambien que:
          - los retornos fuera de muestra fueron "muy inferiores";
          - tras el mercado bajista de 2008-2009, el modelo quedo POR
            DEBAJO de las acciones americanas en SEIS de los OCHO anos
            siguientes;
          - la caida maxima del comprar y mantener se duplico fuera de
            muestra.
        Y declara que excluye impuestos, comisiones y deslizamiento.

    O sea: su propio autor documenta que despues de publicarse el modelo
    fue sobre todo un reductor de volatilidad, no de retorno.
    """

    solo_primera_decision = False
    fuente = "Faber 2007; revisado JPM 2017 44(2):156-167"

    def __init__(self, meses_sma=10, dias_por_mes=21):
        self.meses_sma = meses_sma
        self.ventana = int(meses_sma * dias_por_mes)
        self.id = f"PUB_faber_sma{meses_sma}m"

    def __call__(self, vista, elegibles, libro):
        scores, excluidos, encima = {}, {}, []
        n = len(elegibles)
        if n == 0:
            return {}, scores, excluidos
        for t in sorted(elegibles):
            serie = vista[t].dropna()
            if len(serie) < self.ventana:
                excluidos[t] = f"historico {len(serie)} < {self.ventana}"
                continue
            valores = serie.tolist()
            media = _sma(valores, self.ventana)
            if media is None or media <= 0:
                excluidos[t] = "media no admisible"
                continue
            ultimo = float(valores[-1])
            scores[t] = round(ultimo / media - 1.0, 6)
            if ultimo > media:
                encima.append(t)
        # Peso 1/N FIJO. Lo que no cumple la regla se queda en caja: la
        # suma de pesos es menor que 1 a proposito.
        peso = 1.0 / n
        return {t: peso for t in encima}, scores, excluidos


class AntonacciDobleMomento:
    """Doble momento: relativo para elegir, absoluto para estar dentro.

    FUENTE
        Gary Antonacci, "Dual Momentum Investing" (2014) y "Risk Premia
        Harvesting Through Dual Momentum" (Journal of Management &
        Entrepreneurship, 2017).

    REGLA
        1. Momento RELATIVO: ordenar los activos por su retorno de los
           ultimos 12 meses y quedarse con los K mejores.
        2. Momento ABSOLUTO: cada elegido se mantiene solo si su retorno
           de 12 meses supera el del efectivo en el mismo periodo. Si no,
           ese tramo va a efectivo.

        El filtro absoluto es lo que distingue esta estrategia del
        momento puro: no basta ser el mejor del grupo, hay que batir a no
        hacer nada.

    LO QUE RECLAMA
        Antonacci publica mejoras grandes de retorno ajustado por riesgo
        frente a comprar y mantener, sobre indices y en periodos largos.
        No se reproduce aqui su backtest: se mide SU REGLA sobre NUESTRO
        panel, que es otra pregunta y la unica que nos sirve.

    AVISO
        Es, en su nucleo, lo mismo que M03 mas un filtro de efectivo. Si
        sale parecida a M03, no es casualidad ni confirmacion: es que son
        casi la misma estrategia con otro nombre. Tenerlas las dos sirve
        para ver cuanto aporta el filtro absoluto, no para sumar dos
        evidencias independientes.
    """

    solo_primera_decision = False
    fuente = "Antonacci 2014, Dual Momentum Investing"

    def __init__(self, serie_efectivo, k=5, lookback=252):
        self.efectivo = serie_efectivo
        self.k, self.lookback = k, lookback
        self.id = f"PUB_doble_momento_k{k}_{lookback}"

    def __call__(self, vista, elegibles, libro):
        scores, excluidos = {}, {}
        cash = self.efectivo.loc[self.efectivo.index <= vista.index[-1]].dropna()
        r_cash = _retorno(cash.tolist(), self.lookback) if len(cash) else None
        if r_cash is None:
            return {}, scores, {"_efectivo": "sin referencia de efectivo"}
        for t in sorted(elegibles):
            serie = vista[t].dropna()
            if len(serie) < self.lookback + 1:
                excluidos[t] = f"historico {len(serie)} < {self.lookback + 1}"
                continue
            r = _retorno(serie.tolist(), self.lookback)
            if r is None:
                excluidos[t] = "retorno no admisible"
                continue
            scores[t] = round(r, 6)
        if not scores:
            return {}, scores, excluidos
        # Momento relativo: los K mejores.
        mejores = sorted(scores, key=lambda t: -scores[t])[:self.k]
        # Momento absoluto: solo si baten al efectivo.
        dentro = [t for t in mejores if scores[t] > r_cash]
        for t in mejores:
            if t not in dentro:
                excluidos[t] = (f"momento absoluto: {scores[t]:+.4f} no bate "
                                f"al efectivo {r_cash:+.4f}")
        if not dentro:
            return {}, scores, excluidos
        # Peso 1/K FIJO, como Faber: el tramo que no bate al efectivo se
        # queda en caja en vez de repartirse.
        peso = 1.0 / self.k
        return {t: peso for t in sorted(dentro)}, scores, excluidos


class ParidadRiesgoInversa:
    """Peso inversamente proporcional a la volatilidad.

    FUENTE
        Aproximacion de uso comun a la paridad de riesgo, descrita entre
        otros en Asness, Frazzini y Pedersen, "Leverage Aversion and Risk
        Parity" (Financial Analysts Journal, 2012). La version completa
        usa la matriz de covarianzas; esta usa solo volatilidades, que es
        la que circula como receta.

    REGLA
        peso_i proporcional a 1/vol_i, normalizado para sumar 1.

    LO QUE RECLAMA
        Mejor retorno por unidad de riesgo que el equiponderado, por no
        concentrar el riesgo en los activos mas volatiles.

    AVISO
        Esta version ignora las correlaciones, y por eso NO es paridad de
        riesgo: cinco activos que se mueven juntos reciben pesos como si
        fueran independientes. Es la misma confusion que ya corregimos en
        `limites_cartera.concentracion`, donde afirme que el inverso de
        Herfindahl veia el solapamiento entre ETF. No lo ve, y esto
        tampoco.
    """

    solo_primera_decision = False
    fuente = "Asness, Frazzini, Pedersen 2012 (version simplificada)"

    def __init__(self, ventana_vol=63):
        self.ventana_vol = ventana_vol
        self.id = f"PUB_paridad_inversa_{ventana_vol}"

    def __call__(self, vista, elegibles, libro):
        scores, excluidos, inversos = {}, {}, {}
        for t in sorted(elegibles):
            serie = vista[t].dropna()
            if len(serie) < self.ventana_vol + 1:
                excluidos[t] = f"historico {len(serie)} < {self.ventana_vol + 1}"
                continue
            v = _vol(serie.tolist(), self.ventana_vol)
            if v is None or v <= 0:
                excluidos[t] = "volatilidad no admisible"
                continue
            scores[t] = round(v, 6)
            inversos[t] = 1.0 / v
        if not inversos:
            return {}, scores, excluidos
        total = sum(inversos.values())
        return ({t: inversos[t] / total for t in sorted(inversos)},
                scores, excluidos)


ESTRATEGIAS = {
    "faber_sma": FaberTiempoMercado,
    "doble_momento": AntonacciDobleMomento,
    "paridad_inversa": ParidadRiesgoInversa,
}
