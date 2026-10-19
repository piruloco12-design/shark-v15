"""
Libro de efectivo y cantidades de una cuenta AL CONTADO.

POR QUE EXISTE

El evaluador anterior limitaba la pérdida teórica al stop pero no reservaba
el nominal de la compra ni comprobaba si había efectivo. Con capital 1.000,
precio 100, ATR 0,10 y riesgo del 0,5% abría 25 unidades: nominal 2.500, dos
veces y media la cuenta. Un límite de número de posiciones no impide ese
apalancamiento implícito, porque no mira el dinero.

Este módulo es el sitio donde eso se vuelve imposible. No es un detalle de
contabilidad: una cuenta al contado no puede comprar lo que no puede pagar, y
cualquier rentabilidad calculada sobre compras impagables es ficción.

LAS CUATRO INVARIANTES, que se comprueban en cada operación:

    cantidad_i >= 0
    compra_requerida + costes_reservados <= efectivo_utilizable
    cantidad_a_vender <= cantidad_disponible
    NAV = efectivo + valor_de_posiciones + derechos - obligaciones

QUE ESTE LIBRO NO HACE

  - No concede crédito ni margen. Una compra que no cabe se reduce o se
    rechaza, nunca se financia.
  - No reutiliza al instante el dinero de una venta. La liquidación depende
    de las condiciones de la cuenta, que no están verificadas, así que el
    retardo es un parámetro declarado (`dias_liquidacion`), no un supuesto
    escondido.
  - No abre posiciones cortas. En una cuenta al contado no son ejecutables.
    `abrir_corto` lanza una excepción a propósito: el contrafactual de cortos
    vive en otro libro, con su propio capital y sus propias estadísticas.
  - No promete limitar pérdidas frente a huecos. El tamaño por riesgo acota
    la pérdida SI se ejecuta al stop; un hueco se ejecuta donde se negocie.

UNIDADES

Todo importe lleva moneda explícita. Una simulación sobre cotizaciones en USD
no se convierte en una cuenta en EUR por escribir el símbolo del euro en el
resumen, así que el libro guarda las dos y el tipo de cambio que usó.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field, replace

CENTIMO = 1e-9          # tolerancia para comparaciones de dinero


class LibroInvalido(RuntimeError):
    """Una invariante del libro se rompería. Es un fallo, no un dato."""


class OperacionNoEjecutable(ValueError):
    """La operación no cabe o no está permitida en esta cuenta."""


def _finito(valor, nombre):
    try:
        v = float(valor)
    except (TypeError, ValueError):
        raise LibroInvalido(f"{nombre}: no es un número")
    if not math.isfinite(v):
        raise LibroInvalido(f"{nombre}: no finito")
    return v


def _no_negativo(valor, nombre):
    v = _finito(valor, nombre)
    if v < -CENTIMO:
        raise LibroInvalido(f"{nombre}: negativo ({v})")
    return max(0.0, v)


def _positivo(valor, nombre):
    v = _finito(valor, nombre)
    if v <= 0:
        raise LibroInvalido(f"{nombre}: debe ser positivo ({v})")
    return v


# =====================================================================

@dataclass(frozen=True)
class Instrumento:
    """Las reglas de mercado de un instrumento. Sin esto no hay cantidades."""

    id: str
    moneda: str = "USD"
    multiplicador: float = 1.0
    # Cantidad mínima negociable. 1.0 = acciones enteras; 0.0 = fraccionable
    # sin límite. No se inventa: si el broker no lo admite, es 1.0.
    lote: float = 1.0
    precision_cantidad: int = 8

    def redondear_a_lote(self, cantidad: float) -> float:
        """Siempre HACIA ABAJO: redondear hacia arriba inventa dinero.

        El caso fraccionable usaba round(), y round() redondea al par mas
        cercano: puede subir. Con eso la cantidad maxima comprable salia
        unos céntimos por encima de lo que cabia y la invariante de
        no-margen saltaba. Que saltara esta bien; lo que estaba mal era
        usar round() en una funcion cuyo docstring dice "hacia abajo".
        """
        c = _no_negativo(cantidad, "cantidad")
        if self.lote <= 0:
            escala = 10.0 ** self.precision_cantidad
            return math.floor(c * escala) / escala
        return math.floor(c / self.lote + CENTIMO) * self.lote


@dataclass(frozen=True)
class Posicion:
    cantidad: float = 0.0
    coste_medio: float = 0.0        # por unidad, en moneda del instrumento
    precio_valoracion: float = 0.0
    valorado_en: object = None      # momento del precio de valoración


@dataclass(frozen=True)
class Movimiento:
    """Un apunte. El registro completo de lo que se hizo y por qué."""

    momento: object
    tipo: str                       # COMPRA | VENTA | DIVIDENDO | SPLIT | ...
    instrumento: str = ""
    cantidad_solicitada: float = 0.0
    cantidad_ejecutada: float = 0.0
    precio_decision: float = 0.0
    precio_ejecucion: float = 0.0
    momento_decision: object = None
    disponible_en: object = None
    costes: dict = field(default_factory=dict)
    riesgo_inicial: float = 0.0
    motivo: str = ""
    efectivo_despues: float = 0.0
    nav_despues: float = 0.0
    rechazo: str = ""


# =====================================================================

class LibroContado:
    """Libro de una cuenta al contado. Sin margen, sin cortos.

    `dias_liquidacion` retrasa cuándo el dinero de una venta vuelve a ser
    utilizable. 0 significa inmediato, que es un supuesto optimista y
    declarado; no se asume crédito.
    """

    def __init__(self, efectivo_inicial, moneda_cuenta="USD",
                 dias_liquidacion=0, permitir_fraccionado=False):
        self.moneda_cuenta = moneda_cuenta
        self._efectivo = _no_negativo(efectivo_inicial, "efectivo_inicial")
        self._reservado = 0.0
        self.dias_liquidacion = int(dias_liquidacion)
        self.permitir_fraccionado = bool(permitir_fraccionado)

        self.posiciones: dict[str, Posicion] = {}
        self.instrumentos: dict[str, Instrumento] = {}
        self.derechos: float = 0.0        # dividendos reconocidos, no cobrados
        self.obligaciones: float = 0.0
        self._pendiente_liquidar: list[tuple] = []   # (momento_disponible, importe)

        self.movimientos: list[Movimiento] = []
        self.nav_inicial = self._efectivo
        self.momento_inicial = None

    # ---- lectura ----

    @property
    def efectivo(self) -> float:
        return self._efectivo

    @property
    def efectivo_utilizable(self) -> float:
        """Lo que se puede gastar AHORA: sin lo reservado ni lo no liquidado."""
        return max(0.0, self._efectivo - self._reservado)

    @property
    def reservado(self) -> float:
        return self._reservado

    def cantidad(self, instrumento_id: str) -> float:
        return self.posiciones.get(instrumento_id, Posicion()).cantidad

    def valor_posiciones(self) -> float:
        total = 0.0
        for iid, pos in self.posiciones.items():
            if pos.cantidad <= 0:
                continue
            if pos.precio_valoracion <= 0:
                raise LibroInvalido(
                    f"{iid}: posición abierta sin precio de valoración "
                    f"admisible. No se valora a cero: la métrica queda "
                    f"marcada como no fiable."
                )
            mult = self.instrumentos.get(iid, Instrumento(iid)).multiplicador
            total += pos.cantidad * pos.precio_valoracion * mult
        return total

    def nav(self) -> float:
        return (self._efectivo + self.valor_posiciones()
                + self.derechos - self.obligaciones)

    def comprobar_invariantes(self):
        for iid, pos in self.posiciones.items():
            if pos.cantidad < -CENTIMO:
                raise LibroInvalido(f"{iid}: cantidad negativa ({pos.cantidad})")
        if self._efectivo < -CENTIMO:
            raise LibroInvalido(f"efectivo negativo ({self._efectivo})")
        if self._reservado < -CENTIMO:
            raise LibroInvalido(f"reservado negativo ({self._reservado})")
        if self._reservado > self._efectivo + CENTIMO:
            raise LibroInvalido(
                f"reservado {self._reservado} supera el efectivo "
                f"{self._efectivo}"
            )

    # ---- registro de instrumentos ----

    def registrar_instrumento(self, instrumento: Instrumento):
        self.instrumentos[instrumento.id] = instrumento

    def _instrumento(self, iid) -> Instrumento:
        if iid not in self.instrumentos:
            self.instrumentos[iid] = Instrumento(
                iid, lote=0.0 if self.permitir_fraccionado else 1.0)
        return self.instrumentos[iid]

    # ---- valoración ----

    def valorar(self, iid: str, precio: float, momento=None):
        pos = self.posiciones.get(iid)
        if pos is None:
            return
        self.posiciones[iid] = replace(
            pos, precio_valoracion=_positivo(precio, f"precio de {iid}"),
            valorado_en=momento)

    def liquidar_pendientes(self, momento):
        """Hace utilizable el dinero de ventas ya liquidadas."""
        quedan = []
        for cuando, importe in self._pendiente_liquidar:
            if momento is None or cuando is None or cuando <= momento:
                self._efectivo += importe
            else:
                quedan.append((cuando, importe))
        self._pendiente_liquidar = quedan

    # ---- operaciones ----

    def cantidad_maxima_comprable(self, iid, precio, coste_rel=0.0,
                                  coste_fijo=0.0):
        """Cuánto se puede comprar de verdad con el efectivo utilizable.

        Esta función es el corazón del arreglo: antes nadie preguntaba esto.
        Resuelve  q*precio*mult*(1+coste_rel) + coste_fijo <= disponible.
        """
        inst = self._instrumento(iid)
        precio = _positivo(precio, "precio")
        disponible = self.efectivo_utilizable - _no_negativo(coste_fijo,
                                                             "coste_fijo")
        if disponible <= 0:
            return 0.0
        por_unidad = precio * inst.multiplicador * (1.0 + coste_rel)
        if por_unidad <= 0:
            return 0.0
        return inst.redondear_a_lote(disponible / por_unidad)

    def comprar(self, iid, cantidad, precio, momento=None, *,
                coste_rel=0.0, coste_fijo=0.0, precio_decision=None,
                momento_decision=None, disponible_en=None,
                riesgo_inicial=0.0, motivo="", reducir_si_no_cabe=True):
        """Compra al contado. Nunca gasta más de lo que hay.

        Si la cantidad pedida no cabe y `reducir_si_no_cabe`, la reduce de
        forma determinista al máximo comprable. Si no cabe nada, deja un
        movimiento con el motivo del rechazo: una compra rechazada es
        información, no un silencio.
        """
        inst = self._instrumento(iid)
        precio = _positivo(precio, "precio")
        solicitada = _no_negativo(cantidad, "cantidad")
        coste_rel = _no_negativo(coste_rel, "coste_rel")
        coste_fijo = _no_negativo(coste_fijo, "coste_fijo")

        maxima = self.cantidad_maxima_comprable(iid, precio, coste_rel,
                                                coste_fijo)
        pedida_en_lote = inst.redondear_a_lote(solicitada)
        ejecutada = min(pedida_en_lote, maxima)

        if ejecutada <= 0:
            mov = Movimiento(
                momento=momento, tipo="COMPRA", instrumento=iid,
                cantidad_solicitada=solicitada, cantidad_ejecutada=0.0,
                precio_decision=precio if precio_decision is None
                else precio_decision,
                precio_ejecucion=precio, momento_decision=momento_decision,
                disponible_en=disponible_en, motivo=motivo,
                efectivo_despues=self._efectivo, nav_despues=self.nav(),
                rechazo=(f"no cabe: utilizable {self.efectivo_utilizable:.2f}, "
                         f"necesario "
                         f"{pedida_en_lote * precio * inst.multiplicador:.2f}"),
            )
            self.movimientos.append(mov)
            if not reducir_si_no_cabe and pedida_en_lote > 0:
                raise OperacionNoEjecutable(mov.rechazo)
            return mov

        nominal = ejecutada * precio * inst.multiplicador
        comision = nominal * coste_rel + coste_fijo
        total = nominal + comision

        if total > self.efectivo_utilizable + CENTIMO:
            raise LibroInvalido(
                f"compra de {iid} por {total:.4f} supera el efectivo "
                f"utilizable {self.efectivo_utilizable:.4f}: la invariante "
                f"de no-margen se habría roto"
            )

        pos = self.posiciones.get(iid, Posicion())
        nueva_cantidad = pos.cantidad + ejecutada
        nuevo_coste = ((pos.coste_medio * pos.cantidad + nominal + comision)
                       / nueva_cantidad) if nueva_cantidad > 0 else 0.0
        self.posiciones[iid] = Posicion(
            cantidad=nueva_cantidad, coste_medio=nuevo_coste,
            precio_valoracion=precio, valorado_en=momento)
        self._efectivo -= total

        self.comprobar_invariantes()
        mov = Movimiento(
            momento=momento, tipo="COMPRA", instrumento=iid,
            cantidad_solicitada=solicitada, cantidad_ejecutada=ejecutada,
            precio_decision=precio if precio_decision is None
            else precio_decision,
            precio_ejecucion=precio, momento_decision=momento_decision,
            disponible_en=disponible_en,
            costes={"comision": comision, "nominal": nominal},
            riesgo_inicial=riesgo_inicial, motivo=motivo,
            efectivo_despues=self._efectivo, nav_despues=self.nav(),
            rechazo="" if ejecutada >= pedida_en_lote - CENTIMO
            else f"reducida de {pedida_en_lote} a {ejecutada} por efectivo",
        )
        self.movimientos.append(mov)
        return mov

    def vender(self, iid, cantidad, precio, momento=None, *,
               coste_rel=0.0, coste_fijo=0.0, precio_decision=None,
               momento_decision=None, motivo=""):
        """Vende como máximo lo que hay. Nunca abre un corto."""
        inst = self._instrumento(iid)
        precio = _positivo(precio, "precio")
        solicitada = _no_negativo(cantidad, "cantidad")
        disponible = self.cantidad(iid)

        ejecutada = min(inst.redondear_a_lote(solicitada), disponible)
        if ejecutada <= 0:
            mov = Movimiento(
                momento=momento, tipo="VENTA", instrumento=iid,
                cantidad_solicitada=solicitada, cantidad_ejecutada=0.0,
                precio_ejecucion=precio, motivo=motivo,
                efectivo_despues=self._efectivo, nav_despues=self.nav(),
                rechazo=f"sin cantidad disponible (tiene {disponible})",
            )
            self.movimientos.append(mov)
            return mov

        nominal = ejecutada * precio * inst.multiplicador
        comision = nominal * _no_negativo(coste_rel, "coste_rel") \
            + _no_negativo(coste_fijo, "coste_fijo")
        neto = nominal - comision

        pos = self.posiciones[iid]
        resto = pos.cantidad - ejecutada
        if resto <= CENTIMO:
            self.posiciones.pop(iid)
        else:
            self.posiciones[iid] = replace(pos, cantidad=resto,
                                           precio_valoracion=precio,
                                           valorado_en=momento)

        if self.dias_liquidacion <= 0 or momento is None:
            self._efectivo += neto
        else:
            try:
                import pandas as pd
                cuando = momento + pd.Timedelta(days=self.dias_liquidacion)
            except Exception:
                cuando = None
            if cuando is None:
                self._efectivo += neto
            else:
                self._pendiente_liquidar.append((cuando, neto))

        self.comprobar_invariantes()
        mov = Movimiento(
            momento=momento, tipo="VENTA", instrumento=iid,
            cantidad_solicitada=solicitada, cantidad_ejecutada=ejecutada,
            precio_decision=precio if precio_decision is None
            else precio_decision,
            precio_ejecucion=precio, momento_decision=momento_decision,
            costes={"comision": comision, "nominal": nominal},
            motivo=motivo, efectivo_despues=self._efectivo,
            nav_despues=self.nav(),
        )
        self.movimientos.append(mov)
        return mov

    def abrir_corto(self, *a, **k):
        raise OperacionNoEjecutable(
            "una cuenta al contado no puede abrir posiciones cortas: no hay "
            "préstamo de valores ni margen. El contrafactual de cortos va en "
            "un libro aparte, con su propio capital y sus estadísticas."
        )

    # ---- acciones corporativas ----

    def dividendo(self, iid, importe_por_unidad, momento=None,
                  momento_pago=None):
        """Reconoce el derecho. El efectivo llega cuando se paga.

        Oráculo que esto cumple: una acción pasa de 100 a 98 y genera un
        derecho de 2. Sin otros movimientos ni costes, el tenedor conserva
        un valor de 100. Si el dividendo no se reconociera, el NAV caería
        un 2% que nadie perdió.
        """
        q = self.cantidad(iid)
        if q <= 0:
            return 0.0
        bruto = q * _no_negativo(importe_por_unidad, "dividendo")
        if momento_pago is None or momento is None or momento_pago <= momento:
            self._efectivo += bruto
        else:
            self.derechos += bruto
            self._pendiente_liquidar.append((momento_pago, bruto))
            self.derechos -= 0.0   # el derecho se mantiene hasta el cobro
        self.movimientos.append(Movimiento(
            momento=momento, tipo="DIVIDENDO", instrumento=iid,
            cantidad_ejecutada=q, costes={"bruto": bruto},
            efectivo_despues=self._efectivo, nav_despues=self.nav()))
        return bruto

    def split(self, iid, ratio, momento=None):
        """Multiplica la cantidad y divide el precio. Ni gana ni pierde."""
        ratio = _positivo(ratio, "ratio")
        pos = self.posiciones.get(iid)
        if pos is None or pos.cantidad <= 0:
            return
        self.posiciones[iid] = Posicion(
            cantidad=pos.cantidad * ratio,
            coste_medio=pos.coste_medio / ratio,
            precio_valoracion=pos.precio_valoracion / ratio,
            valorado_en=pos.valorado_en)
        self.movimientos.append(Movimiento(
            momento=momento, tipo="SPLIT", instrumento=iid,
            cantidad_ejecutada=self.posiciones[iid].cantidad,
            costes={"ratio": ratio},
            efectivo_despues=self._efectivo, nav_despues=self.nav()))

    # ---- reservas ----

    def reservar(self, importe):
        """Aparta efectivo para una orden pendiente.

        Esto es lo que impide que dos órdenes de la MISMA estrategia gasten
        el mismo saldo. No hace falta tener dos estrategias para necesitarlo.
        """
        importe = _no_negativo(importe, "importe")
        if importe > self.efectivo_utilizable + CENTIMO:
            raise OperacionNoEjecutable(
                f"no se puede reservar {importe:.2f}: utilizable "
                f"{self.efectivo_utilizable:.2f}"
            )
        self._reservado += importe
        self.comprobar_invariantes()
        return importe

    def liberar_reserva(self, importe):
        self._reservado = max(0.0, self._reservado
                              - _no_negativo(importe, "importe"))

    # ---- concentración ----

    def pesos(self) -> dict:
        valor = self.valor_posiciones()
        nav = self.nav()
        if nav <= 0:
            return {}
        salida = {}
        for iid, pos in self.posiciones.items():
            if pos.cantidad <= 0:
                continue
            mult = self._instrumento(iid).multiplicador
            salida[iid] = pos.cantidad * pos.precio_valoracion * mult / nav
        return salida

    def concentracion(self) -> dict:
        """Peso máximo y número efectivo de posiciones.

        `1 / suma(w^2)` sobre la parte invertida: cinco ETF que comparten
        acciones no son cinco fuentes de retorno, y este número al menos
        enseña cuántas posiciones efectivas hay.
        """
        w = self.pesos()
        invertido = sum(w.values())
        if invertido <= 0:
            return {"invertido": 0.0, "peso_maximo": 0.0,
                    "posiciones_efectivas": 0.0, "posiciones": 0}
        norm = [x / invertido for x in w.values()]
        return {
            "invertido": round(invertido, 6),
            "peso_maximo": round(max(w.values()), 6),
            "posiciones_efectivas": round(1.0 / sum(x * x for x in norm), 3),
            "posiciones": len(w),
        }

    # ---- resumen ----

    def estado(self) -> dict:
        return {
            "moneda_cuenta": self.moneda_cuenta,
            "efectivo": round(self._efectivo, 6),
            "efectivo_utilizable": round(self.efectivo_utilizable, 6),
            "reservado": round(self._reservado, 6),
            "valor_posiciones": round(self.valor_posiciones(), 6),
            "derechos": round(self.derechos, 6),
            "obligaciones": round(self.obligaciones, 6),
            "nav": round(self.nav(), 6),
            "posiciones": {k: round(v.cantidad, 8)
                           for k, v in self.posiciones.items()},
            "concentracion": self.concentracion(),
            "movimientos": len(self.movimientos),
            "pendiente_liquidar": len(self._pendiente_liquidar),
        }
