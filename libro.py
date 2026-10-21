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


def comision_explicita(nominal, coste_rel=0.0, coste_fijo=0.0,
                       coste_minimo=0.0):
    """Comision de UNA pata, con los componentes SEPARADOS.

        comision = max(coste_minimo, coste_rel * nominal) + coste_fijo

    Las tres cosas son distintas y mezclarlas fue un error mio que la
    tercera revision tuvo que corregir. Yo medi `coste_rel * N + coste_fijo`
    y lo llame "minimo por orden". No es lo mismo:

        N = 200, coste_rel = 0,0008, minimo = fijo = 0,50
          aditivo  -> 0,0008*200 + 0,50 = 0,66
          minimo   -> max(0,50; 0,16)   = 0,50

    Lo que NO entra aqui, y hay que decirlo porque su ausencia no es un
    cero: terceros (tasas por instrumento, lado y fecha), FX (sobre los
    flujos REALMENTE convertidos, no sobre todo el nominal), horquilla y
    deslizamiento. Esos dos ultimos van en el PRECIO de ejecucion, no en
    la comision, y si se usa bid/ask observado no se suma otra vez media
    horquilla.
    """
    n = abs(float(nominal))
    proporcional = max(0.0, float(coste_rel)) * n
    minimo = max(0.0, float(coste_minimo))
    return max(minimo, proporcional) + max(0.0, float(coste_fijo))


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
class Derecho:
    """Dinero reconocido que todavia no es caja.

    Campos exigidos por el plan de la segunda auditoria (cambio 1). La
    version anterior guardaba `(cuando, importe)` en una lista anonima que
    NO sabia si su importe estaba contado en `derechos`. De ahi salian dos
    errores opuestos con la misma raiz: la venta diferida no lo contaba y
    el NAV perdia el dinero entre la venta y el cobro; el dividendo lo
    contaba y nunca lo daba de baja, y el NAV lo ganaba dos veces.

    Con el derecho tipado los dos son imposibles por construccion: todo
    importe diferido es un Derecho, `derechos` es su SUMA (no un escalar
    paralelo que pueda desincronizarse) y liquidar mueve exactamente un
    derecho a caja.
    """

    event_id: str
    tipo: str                       # VENTA_DIFERIDA | DIVIDENDO | LIQUIDACION_FONDO
    instrumento: str
    moneda: str
    importe: float
    fecha_reconocimiento: object = None
    fecha_exigible: object = None
    fecha_liquidacion: object = None
    estado: str = "RECONOCIDO"      # RECONOCIDO | LIQUIDADO
    fuente: str = ""
    version_datos: str = ""


@dataclass(frozen=True)
class Movimiento:
    """Un apunte. El registro completo de lo que se hizo y por qué."""

    momento: object
    tipo: str                       # COMPRA | VENTA | DIVIDENDO | SPLIT | ...
    instrumento: str = ""
    cantidad_solicitada: float = 0.0
    cantidad_ejecutada: float = 0.0
    # Cantidad que la estrategia queria ANTES de que la admision la
    # recortase. Sin este campo el artefacto solo guarda lo recortado y la
    # diferencia desaparece del registro.
    cantidad_pre_admision: float = 0.0
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
                 dias_liquidacion=0, permitir_fraccionado=False,
                 politica_venta_antieconomica="RECHAZAR"):
        self.moneda_cuenta = moneda_cuenta
        # Politica DECLARADA, no una ley de ejecucion. Ver `vender`.
        if politica_venta_antieconomica not in ("RECHAZAR",
                                                "EJECUTAR_SI_HAY_CAJA"):
            raise LibroInvalido(
                f"politica_venta_antieconomica no soportada: "
                f"{politica_venta_antieconomica!r}")
        self.politica_venta_antieconomica = politica_venta_antieconomica
        self._efectivo = _no_negativo(efectivo_inicial, "efectivo_inicial")
        self._reservado = 0.0
        self.dias_liquidacion = int(dias_liquidacion)
        self.permitir_fraccionado = bool(permitir_fraccionado)

        self.posiciones: dict[str, Posicion] = {}
        self.instrumentos: dict[str, Instrumento] = {}
        # Derechos de cobro TIPADOS, indexados por event_id. `derechos` es
        # una propiedad que los suma: no existe un escalar que mantener a
        # mano, asi que no puede desincronizarse de la lista.
        self._derechos: dict[str, Derecho] = {}
        self.obligaciones: float = 0.0
        # Idempotencia: event_id -> movimiento ya aplicado. Repetir un fill
        # o un pago con el mismo identificador no vuelve a tocar el libro.
        self._eventos_aplicados: dict[str, object] = {}
        # Reservas por order_id: importe apartado para cada orden viva.
        self._reservas: dict[str, float] = {}
        self._secuencia: int = 0

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

    @property
    def derechos(self) -> float:
        """Suma de los derechos reconocidos y no cobrados."""
        return sum(d.importe for d in self._derechos.values()
                   if d.estado == "RECONOCIDO")

    def derechos_pendientes(self) -> list:
        return [d for d in self._derechos.values() if d.estado == "RECONOCIDO"]

    def _nuevo_event_id(self, prefijo: str) -> str:
        self._secuencia += 1
        return f"{prefijo}-{self._secuencia:06d}"

    def _exigir_moneda(self, inst: Instrumento):
        """Una sola moneda mientras no exista FX. No se asume paridad 1:1."""
        if inst.moneda != self.moneda_cuenta:
            raise OperacionNoEjecutable(
                f"{inst.id} cotiza en {inst.moneda} y la cuenta esta en "
                f"{self.moneda_cuenta}. No hay conversion implementada y "
                f"no se asume paridad 1:1: la orden se rechaza antes de "
                f"modificar el libro."
            )

    def _ya_aplicado(self, event_id):
        if event_id is None:
            return None
        return self._eventos_aplicados.get(event_id)

    @staticmethod
    def _exigible_en(momento, dias):
        try:
            import pandas as pd
            return momento + pd.Timedelta(days=int(dias))
        except Exception:
            return None

    def _reconocer_derecho(self, *, tipo, instrumento, importe, moneda,
                           fecha_reconocimiento, fecha_exigible,
                           fuente="", version_datos="", event_id=None):
        """Reconoce un derecho de cobro. Entra en el NAV, no en la caja."""
        importe = _no_negativo(importe, "importe del derecho")
        eid = event_id or self._nuevo_event_id(tipo.lower())
        if eid in self._derechos:
            return self._derechos[eid]
        d = Derecho(
            event_id=eid, tipo=tipo, instrumento=instrumento, moneda=moneda,
            importe=importe, fecha_reconocimiento=fecha_reconocimiento,
            fecha_exigible=fecha_exigible, fuente=fuente,
            version_datos=version_datos)
        self._derechos[eid] = d
        return d

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
        """Mueve a caja los derechos exigibles. Baja el derecho, sube la caja.

        No crea ni destruye NAV: un derecho reconocido ya contaba en el NAV.
        Y es idempotente, que es la puerta V05: el derecho cobrado cambia de
        estado a LIQUIDADO, asi que llamar dos veces no cobra dos veces.
        """
        cobrados = []
        for eid, d in list(self._derechos.items()):
            if d.estado != "RECONOCIDO":
                continue
            if (momento is not None and d.fecha_exigible is not None
                    and d.fecha_exigible > momento):
                continue
            self._efectivo += d.importe
            self._derechos[eid] = replace(d, estado="LIQUIDADO",
                                          fecha_liquidacion=momento)
            cobrados.append(eid)
            self.movimientos.append(Movimiento(
                momento=momento, tipo="LIQUIDACION", instrumento=d.instrumento,
                costes={"importe": d.importe, "event_id": eid,
                        "tipo_derecho": d.tipo},
                efectivo_despues=self._efectivo, nav_despues=self.nav()))
        if cobrados:
            self.comprobar_invariantes()
        return cobrados

    # ---- operaciones ----

    def cantidad_maxima_comprable(self, iid, precio, coste_rel=0.0,
                                  coste_fijo=0.0, coste_minimo=0.0):
        """Cuánto se puede comprar de verdad con el efectivo utilizable.

        Esta función es el corazón del arreglo: antes nadie preguntaba esto.
        Resuelve  q*precio*mult + comision(q) <= disponible, con

            comision(q) = max(coste_minimo, coste_rel*N) + coste_fijo

        que es a trozos: por debajo de cierto tamaño manda el mínimo y el
        coste no crece con la cantidad; por encima manda la parte
        proporcional. Se resuelven las dos ramas y se toma la mayor que de
        verdad cumple su propia condición.
        """
        inst = self._instrumento(iid)
        precio = _positivo(precio, "precio")
        coste_fijo = _no_negativo(coste_fijo, "coste_fijo")
        coste_minimo = _no_negativo(coste_minimo, "coste_minimo")
        unidad = precio * inst.multiplicador
        if unidad <= 0:
            return 0.0

        # Rama PROPORCIONAL: la parte porcentual supera el minimo.
        candidatos = [0.0]
        disp_prop = self.efectivo_utilizable - coste_fijo
        if disp_prop > 0:
            por_unidad = unidad * (1.0 + coste_rel)
            if por_unidad > 0:
                q = disp_prop / por_unidad
                if coste_rel * q * unidad >= coste_minimo - CENTIMO:
                    candidatos.append(q)

        # Rama del MINIMO: el coste no depende de la cantidad.
        disp_min = self.efectivo_utilizable - coste_fijo - coste_minimo
        if disp_min > 0:
            q = disp_min / unidad
            if coste_rel * q * unidad <= coste_minimo + CENTIMO:
                candidatos.append(q)

        return inst.redondear_a_lote(max(candidatos))

    def comprar(self, iid, cantidad, precio, momento=None, *,
                coste_rel=0.0, coste_fijo=0.0, coste_minimo=0.0,
                precio_decision=None,
                momento_decision=None, disponible_en=None,
                riesgo_inicial=0.0, motivo="", reducir_si_no_cabe=True,
                event_id=None, version_datos="", order_id=None,
                cantidad_pre_admision=0.0):
        """Compra al contado. Nunca gasta más de lo que hay.

        Si la cantidad pedida no cabe y `reducir_si_no_cabe`, la reduce de
        forma determinista al máximo comprable. Si no cabe nada, deja un
        movimiento con el motivo del rechazo: una compra rechazada es
        información, no un silencio.
        """
        repetido = self._ya_aplicado(event_id)
        if repetido is not None:
            return repetido
        inst = self._instrumento(iid)
        self._exigir_moneda(inst)
        precio = _positivo(precio, "precio")
        solicitada = _no_negativo(cantidad, "cantidad")
        coste_rel = _no_negativo(coste_rel, "coste_rel")
        coste_fijo = _no_negativo(coste_fijo, "coste_fijo")

        # Consumir la reserva de ESTA orden: su efectivo se aparto para
        # ella, asi que debe estar disponible para ella.
        if order_id is not None:
            self.liberar_orden(order_id)

        maxima = self.cantidad_maxima_comprable(iid, precio, coste_rel,
                                                coste_fijo, coste_minimo)
        pedida_en_lote = inst.redondear_a_lote(solicitada)
        ejecutada = min(pedida_en_lote, maxima)

        # Ejecucion COMPLETA o nada. La bandera se honraba solo cuando no
        # cabia NADA: si cabia una parte se compraba la parte y se ignoraba
        # la exigencia. Textual del plan: "si exige ejecucion completa y no
        # cabe: rechazar toda la orden".
        if not reducir_si_no_cabe and ejecutada < pedida_en_lote - CENTIMO:
            mov = self.rechazar(
                iid, solicitada, precio, momento, tipo="COMPRA",
                motivo=motivo,
                rechazo=(f"exige ejecucion completa de {pedida_en_lote} y "
                         f"solo caben {ejecutada}: se rechaza la orden "
                         f"entera, no una parte"),
                precio_decision=precio_decision,
                momento_decision=momento_decision)
            raise OperacionNoEjecutable(mov.rechazo)

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
            # El caso `not reducir_si_no_cabe` ya se rechazo arriba, antes
            # de llegar aqui: esta rama solo ve ordenes que SI admiten
            # reduccion y en las que no cabe ni una unidad.
            return mov

        nominal = ejecutada * precio * inst.multiplicador
        comision = comision_explicita(nominal, coste_rel, coste_fijo,
                                      coste_minimo)
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
            cantidad_pre_admision=cantidad_pre_admision,
            efectivo_despues=self._efectivo, nav_despues=self.nav(),
            rechazo="" if ejecutada >= pedida_en_lote - CENTIMO
            else f"reducida de {pedida_en_lote} a {ejecutada} por efectivo",
        )
        self.movimientos.append(mov)
        if event_id is not None:
            self._eventos_aplicados[event_id] = mov
        return mov

    def vender(self, iid, cantidad, precio, momento=None, *,
               coste_rel=0.0, coste_fijo=0.0, coste_minimo=0.0,
               precio_decision=None,
               momento_decision=None, motivo="", event_id=None,
               version_datos=""):
        """Vende como máximo lo que hay. Nunca abre un corto."""
        repetido = self._ya_aplicado(event_id)
        if repetido is not None:
            return repetido
        inst = self._instrumento(iid)
        self._exigir_moneda(inst)
        precio = _positivo(precio, "precio")
        solicitada = _no_negativo(cantidad, "cantidad")
        disponible = self.cantidad(iid)

        # Salida COMPLETA exacta. Redondear a lote la cantidad de una venta
        # total deja polvo: una posicion de 1,5981321917 floored a 8
        # decimales deja 1,7e-9 dentro. Con eso, M03 con K=5 acabo con 17
        # posiciones (efectivas 4,99) y generaba una orden de venta
        # imposible cada mes, que inflaba las intenciones y los rechazos.
        #
        # Vender todo lo que se tiene siempre es ejecutable: el lote limita
        # lo que se puede comprar o vender PARCIALMENTE, no cerrar del todo.
        if solicitada >= disponible - 1e-6 * max(1.0, disponible):
            ejecutada = disponible
        else:
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
        comision = comision_explicita(nominal, coste_rel, coste_fijo,
                                      coste_minimo)
        neto = nominal - comision

        # Venta cuyo importe no cubre su comision. Con comision minima por
        # orden pasa de verdad: 0,3 unidades a 2,00 son 0,60 de nominal, y
        # un minimo de 2,00 deja un neto de -1,40.
        #
        # CORRECCION de lo que afirme antes. Yo lo rechazaba siempre y lo
        # presente como consecuencia del contrato "sin margen". No lo es, y
        # la tercera revision lo demostro: con caja 999,40, una unidad
        # valorada en 0,60 y comision 2, ejecutar deja caja 998,00, que no
        # es negativa. El contrato contable para T+0 es
        #
        #     caja_utilizable + ingreso - costes >= 0
        #
        # y esa venta lo cumple. Rechazarla es una POLITICA, legitima pero
        # voluntaria: pagar mas comision que el importe destruye valor. Lo
        # que no vale es presentarla como una ley de ejecucion.
        #
        # `politica_venta_antieconomica`:
        #   RECHAZAR            no se cursa (por defecto, declarado)
        #   EJECUTAR_SI_HAY_CAJA se cursa si la caja cubre el descubierto,
        #                        que es lo contablemente correcto
        #
        # Una salida obligatoria o una reduccion de riesgo es otro caso y
        # no debe resolverse con esta politica.
        if neto <= 0 and self.politica_venta_antieconomica == "EJECUTAR_SI_HAY_CAJA":
            descubierto = -neto
            if descubierto > self.efectivo_utilizable + CENTIMO:
                mov = self.rechazar(
                    iid, solicitada, precio, momento, tipo="VENTA",
                    motivo=motivo,
                    rechazo=(f"la caja utilizable "
                             f"{self.efectivo_utilizable:.4f} no cubre el "
                             f"descubierto {descubierto:.4f} de esta venta"),
                    precio_decision=precio_decision,
                    momento_decision=momento_decision)
                return mov
        elif neto <= 0:
            mov = self.rechazar(
                iid, solicitada, precio, momento, tipo="VENTA", motivo=motivo,
                rechazo=(f"venta antieconomica: nominal {nominal:.4f} no "
                         f"cubre la comision {comision:.4f} (fijo "
                         f"{coste_fijo:.4f})"),
                precio_decision=precio_decision,
                momento_decision=momento_decision)
            return mov

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
            cuando = self._exigible_en(momento, self.dias_liquidacion)
            if cuando is None:
                self._efectivo += neto
            else:
                # El nominal neto sale de la posicion y entra en un DERECHO:
                # no es gastable todavia, pero forma parte del NAV. Antes se
                # guardaba en una lista que el NAV no leia, y el dinero
                # desaparecia de la cartera entre la venta y el cobro.
                self._reconocer_derecho(
                    tipo="VENTA_DIFERIDA", instrumento=iid, importe=neto,
                    moneda=inst.moneda, fecha_reconocimiento=momento,
                    fecha_exigible=cuando, fuente="venta",
                    version_datos=version_datos)

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
        if event_id is not None:
            self._eventos_aplicados[event_id] = mov
        return mov

    def abrir_corto(self, *a, **k):
        raise OperacionNoEjecutable(
            "una cuenta al contado no puede abrir posiciones cortas: no hay "
            "préstamo de valores ni margen. El contrafactual de cortos va en "
            "un libro aparte, con su propio capital y sus estadísticas."
        )

    # ---- acciones corporativas ----

    def dividendo(self, iid, importe_por_unidad, momento=None,
                  momento_pago=None, event_id=None, version_datos=""):
        """Reconoce el derecho. El efectivo llega cuando se paga.

        Oráculo que esto cumple: una acción pasa de 100 a 98 y genera un
        derecho de 2. Sin otros movimientos ni costes, el tenedor conserva
        un valor de 100. Si el dividendo no se reconociera, el NAV caería
        un 2% que nadie perdió.
        """
        repetido = self._ya_aplicado(event_id)
        if repetido is not None:
            return repetido.costes.get("bruto", 0.0)
        inst = self._instrumento(iid)
        self._exigir_moneda(inst)
        q = self.cantidad(iid)
        if q <= 0:
            return 0.0
        bruto = q * _no_negativo(importe_por_unidad, "dividendo")
        if momento_pago is None or momento is None or momento_pago <= momento:
            self._efectivo += bruto
        else:
            # Devengo y pago son eventos distintos. El derecho se da de baja
            # EN la liquidacion, no aqui. Antes se sumaba a `derechos` y
            # ademas a la lista de pendientes, y el cobro subia la caja sin
            # bajar el derecho: el NAV ganaba el dividendo dos veces.
            self._reconocer_derecho(
                tipo="DIVIDENDO", instrumento=iid, importe=bruto,
                moneda=inst.moneda, fecha_reconocimiento=momento,
                fecha_exigible=momento_pago, fuente="dividendo",
                version_datos=version_datos)
        mov = Movimiento(
            momento=momento, tipo="DIVIDENDO", instrumento=iid,
            cantidad_ejecutada=q, costes={"bruto": bruto},
            efectivo_despues=self._efectivo, nav_despues=self.nav())
        self.movimientos.append(mov)
        if event_id is not None:
            self._eventos_aplicados[event_id] = mov
        return bruto

    def liquidar_instrumento(self, iid, importe_por_unidad, momento=None,
                             momento_cobro=None, *, event_id=None,
                             politica_reinversion="EFECTIVO", fuente="",
                             version_datos=""):
        """Liquidacion DECLARADA: las unidades salen y entra un derecho.

        Esto no es una venta al ultimo cierre ni una perdida total
        inventada. Exige el importe por unidad que de verdad se cobra, su
        fecha y la politica de reinversion, porque son las cuatro cosas
        que el plan pide para una baja: evento, precio/cobro, fecha y
        politica. Si no se tienen, NO se llama a esta funcion: se marca
        incertidumbre y se exige evidencia del evento.

        Que una serie deje de cotizar no es evidencia de nada: puede ser
        una liquidacion con reparto, una suspension temporal o un fallo
        del proveedor, y las tres se parecen desde fuera.
        """
        repetido = self._ya_aplicado(event_id)
        if repetido is not None:
            return repetido
        inst = self._instrumento(iid)
        self._exigir_moneda(inst)
        if politica_reinversion != "EFECTIVO":
            raise OperacionNoEjecutable(
                f"politica_reinversion={politica_reinversion!r} no esta "
                f"implementada. Implementada: 'EFECTIVO'."
            )
        q = self.cantidad(iid)
        if q <= 0:
            return None
        importe = _no_negativo(importe_por_unidad, "importe_por_unidad")
        bruto = q * importe * inst.multiplicador

        self.posiciones.pop(iid, None)
        if momento_cobro is None or momento is None or momento_cobro <= momento:
            self._efectivo += bruto
        else:
            self._reconocer_derecho(
                tipo="LIQUIDACION_FONDO", instrumento=iid, importe=bruto,
                moneda=inst.moneda, fecha_reconocimiento=momento,
                fecha_exigible=momento_cobro, fuente=fuente or "liquidacion",
                version_datos=version_datos)

        self.comprobar_invariantes()
        mov = Movimiento(
            momento=momento, tipo="LIQUIDACION_FONDO", instrumento=iid,
            cantidad_solicitada=q, cantidad_ejecutada=q,
            precio_ejecucion=importe,
            costes={"bruto": bruto,
                    "politica_reinversion": politica_reinversion},
            motivo=fuente, efectivo_despues=self._efectivo,
            nav_despues=self.nav())
        self.movimientos.append(mov)
        if event_id is not None:
            self._eventos_aplicados[event_id] = mov
        return mov

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

    def reservar_orden(self, order_id, importe):
        """Aparta efectivo para UNA orden identificada.

        `reservar` movia un escalar anonimo: liberar el importe de una
        orden podia liberar el de otra, y reintentar la misma orden
        reservaba dos veces. Con order_id la reserva es atomica y la
        liberacion individual e idempotente, que es lo que el plan pide:
        "reservar por order_id de forma atomica", "no las dupliques al
        reintentar".
        """
        if order_id in self._reservas:
            return self._reservas[order_id]
        importe = _no_negativo(importe, "importe")
        if importe > self.efectivo_utilizable + CENTIMO:
            raise OperacionNoEjecutable(
                f"la orden {order_id} pide reservar {importe:.2f} y solo hay "
                f"{self.efectivo_utilizable:.2f} utilizable: dos ordenes no "
                f"pueden gastar el mismo saldo"
            )
        self._reservas[order_id] = importe
        self._reservado += importe
        self.comprobar_invariantes()
        return importe

    def liberar_orden(self, order_id):
        """Libera la reserva de una orden. Repetirlo no libera dos veces."""
        importe = self._reservas.pop(order_id, 0.0)
        if importe:
            self._reservado = max(0.0, self._reservado - importe)
        return importe

    def reserva_de(self, order_id):
        return self._reservas.get(order_id, 0.0)

    def rechazar(self, iid, cantidad, precio, momento, *, tipo, motivo="",
                 rechazo="", precio_decision=None, momento_decision=None,
                 cantidad_pre_admision=0.0):
        """Deja constancia de una orden NO ejecutada. Un rechazo es dato."""
        mov = Movimiento(
            momento=momento, tipo=tipo, instrumento=iid,
            cantidad_solicitada=_no_negativo(cantidad, "cantidad"),
            cantidad_ejecutada=0.0,
            cantidad_pre_admision=cantidad_pre_admision,
            precio_decision=precio if precio_decision is None
            else precio_decision,
            precio_ejecucion=precio, momento_decision=momento_decision,
            motivo=motivo, efectivo_despues=self._efectivo,
            nav_despues=self.nav(), rechazo=rechazo)
        self.movimientos.append(mov)
        return mov

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
            "derechos_pendientes": len(self.derechos_pendientes()),
            "derechos_liquidados": sum(
                1 for d in self._derechos.values() if d.estado == "LIQUIDADO"),
        }
