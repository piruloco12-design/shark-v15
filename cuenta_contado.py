"""
CUENTA AL CONTADO PERSISTENTE — el único libro autoritativo de la ruta viva.

Por qué existe. La tercera revisión encontró dos fallos de integración que
reproduje en este repositorio antes de aceptarlos:

    cuenta 1.000, precio 100, ATR 0,10, 8 pb
      comprar A  -> 9,992006 unidades, saldo reportado sigue en 1.000
      comprar B  -> otras 9,992006 unidades
      total       -> 1.998,401279 de nominal + 1,598721 de costes
                     = 2.000 USD comprometidos con 1.000 de saldo

    SELL de un instrumento SIN INVENTARIO -> operacion corta registrada,
                     mientras capacidades_core.py declaraba cortos BLOQUEADA

La causa: `capacidades_core.py` declaraba capacidades citando
`LibroContado`, pero la ruta que de verdad abre posiciones es
`paper_broker.open_trade` -> `storage.create_paper_trade`, que no pasa por
el libro: no comprueba moneda, no reserva caja, no descuenta la compra y
no mira inventario. Habia DOS saldos y solo uno decia la verdad.

Lo que hace este modulo: un unico servicio de caja, inventario y reservas
que **reutiliza los contratos de LibroContado** en vez de reimplementarlos
--no-margen, prohibicion de cortos, derechos de cobro tipados, redondeo de
lote hacia abajo, rechazo de otra moneda-- y los persiste como un registro
de EVENTOS. El estado no se guarda: se reconstruye reproduciendo los
eventos, asi que reiniciar da el mismo estado y cada saldo tiene su causa.

Lo que NO hace: no envia ordenes, no habla con ningun broker y no mide
slippage. Es contabilidad de una simulacion identificada.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
import time

from libro import (LibroContado, Instrumento, OperacionNoEjecutable,
                   LibroInvalido)

# Identificador de la modalidad. Va en cada evento para que no se mezcle
# con la B1 historica, que tenia otra contabilidad.
VARIANTE = "B1_AL_CONTADO_v2"

TABLA_EVENTOS = "cuenta_eventos"


class CuentaInvalida(RuntimeError):
    """La cuenta no puede atender esa operacion."""


class ConflictoDeEvento(RuntimeError):
    """Mismo event_id con contenido distinto.

    Repetir un evento identico es idempotente a proposito: un reintento no
    puede cobrar dos veces. Reutilizar el identificador con OTRO contenido
    no es un reintento, es una colision, y aceptarla en silencio dejaria el
    registro mintiendo sobre lo que paso.
    """


def _huella(payload: dict) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"),
                   default=str).encode()).hexdigest()[:16]


class CuentaContado:
    """Caja, inventario y reservas de UNA cuenta al contado, persistidas."""

    def __init__(self, ruta_db: str, moneda="USD", lote=1.0,
                 permitir_fraccionado=False, dias_liquidacion=0):
        self.ruta_db = ruta_db
        self.moneda = moneda
        self.lote = float(lote)
        self.permitir_fraccionado = bool(permitir_fraccionado)
        self.dias_liquidacion = int(dias_liquidacion)
        self._crear_tabla()
        self.libro: LibroContado | None = None
        self.arrancada = False
        self.incidencias: list = []
        self.reconstruir()

    # ---- persistencia ----

    def _conexion(self):
        return sqlite3.connect(self.ruta_db)

    def _crear_tabla(self):
        with self._conexion() as conn:
            conn.execute(f"""
                CREATE TABLE IF NOT EXISTS {TABLA_EVENTOS} (
                    event_id    TEXT PRIMARY KEY,
                    secuencia   INTEGER,
                    momento     TEXT NOT NULL,
                    tipo        TEXT NOT NULL,
                    variante    TEXT NOT NULL,
                    payload     TEXT NOT NULL,
                    huella      TEXT NOT NULL,
                    aplicado    INTEGER NOT NULL DEFAULT 0
                )
            """)
            # Migracion de registros creados antes de que existiera la
            # columna: lo ya escrito se da por aplicado, porque se aplico.
            cols = {f[1] for f in conn.execute(
                f"PRAGMA table_info({TABLA_EVENTOS})").fetchall()}
            if "aplicado" not in cols:
                conn.execute(f"ALTER TABLE {TABLA_EVENTOS} "
                             f"ADD COLUMN aplicado INTEGER NOT NULL DEFAULT 1")
            conn.execute(
                f"CREATE INDEX IF NOT EXISTS idx_{TABLA_EVENTOS}_sec "
                f"ON {TABLA_EVENTOS}(secuencia)")

    def _siguiente_secuencia(self, conn) -> int:
        fila = conn.execute(
            f"SELECT COALESCE(MAX(secuencia), 0) FROM {TABLA_EVENTOS}"
        ).fetchone()
        return int(fila[0]) + 1

    def _marcar_aplicado(self, event_id: str):
        with self._conexion() as conn:
            conn.execute(f"UPDATE {TABLA_EVENTOS} SET aplicado = 1 "
                         f"WHERE event_id = ?", (event_id,))

    def _registrar(self, event_id: str, tipo: str, payload: dict) -> bool:
        """Guarda un evento. Devuelve False si ya estaba Y SE APLICO.

        Si el mismo event_id llega con OTRO contenido, levanta conflicto:
        no es un reintento.

        La distincion entre registrado y APLICADO hacia falta. Antes un
        fill cuyo `_aplicar` fallaba dejaba su evento en el registro y
        `reconstruir()` volvia a reproducirlo, sin capturar nada: el mismo
        fallo se repetia en cada reconstruccion y la cuenta quedaba
        inservible para siempre. Un intento que no llego a mover caja ni
        inventario no es un hecho contable, es un intento, y se puede
        reintentar.
        """
        huella = _huella(payload)
        with self._conexion() as conn:
            fila = conn.execute(
                f"SELECT huella, aplicado FROM {TABLA_EVENTOS} "
                f"WHERE event_id = ?", (event_id,)).fetchone()
            if fila is not None:
                if fila[0] != huella:
                    raise ConflictoDeEvento(
                        f"el evento {event_id} ya existe con otro contenido "
                        f"(huella {fila[0]} contra {huella}). Un reintento "
                        f"repite el mismo contenido; esto no lo es.")
                # Registrado y aplicado -> repetido de verdad. Registrado y
                # NO aplicado -> fue un intento fallido: se deja reintentar.
                return not bool(fila[1])
            conn.execute(
                f"INSERT INTO {TABLA_EVENTOS} "
                f"(event_id, secuencia, momento, tipo, variante, payload, "
                f"huella, aplicado) VALUES (?,?,?,?,?,?,?,?)",
                (event_id, self._siguiente_secuencia(conn),
                 time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), tipo,
                 VARIANTE, json.dumps(payload, sort_keys=True, default=str),
                 huella, 0))
        return True

    def eventos(self) -> list[dict]:
        with self._conexion() as conn:
            conn.row_factory = sqlite3.Row
            filas = conn.execute(
                f"SELECT * FROM {TABLA_EVENTOS} ORDER BY secuencia ASC"
            ).fetchall()
        # `eventos()` devuelve TODO, aplicado o no: es el registro completo
        # y sirve de auditoria. Quien reconstruye filtra.
        salida = []
        for f in filas:
            d = dict(f)
            d["payload"] = json.loads(d["payload"])
            salida.append(d)
        return salida

    # ---- reconstruccion ----

    def reconstruir(self):
        """Rehace el estado reproduciendo los eventos APLICADOS.

        Esta es la propiedad que hacia falta: al reiniciar, el saldo no se
        lee de una fila mutable que alguien pudo tocar, se deriva de lo que
        paso. Si el saldo no cuadra, cuadra el registro o no cuadra nada.
        """
        self.libro = None
        self.arrancada = False
        self.incidencias = []
        for ev in self.eventos():
            tipo, p = ev["tipo"], ev["payload"]
            if tipo == "ARRANQUE":
                self.libro = LibroContado(
                    p["capital"], moneda_cuenta=p.get("moneda", self.moneda),
                    dias_liquidacion=p.get("dias_liquidacion",
                                           self.dias_liquidacion),
                    permitir_fraccionado=p.get("permitir_fraccionado",
                                               self.permitir_fraccionado))
                self.arrancada = True
                continue
            if self.libro is None:
                # Un evento antes del arranque no se aplica: no hay cuenta
                # sobre la que aplicarlo. Queda en el registro como
                # incidencia en vez de inventarse un saldo.
                continue
            if not ev.get("aplicado"):
                # Intento que nunca movio nada. No se reproduce: hacerlo
                # repetiria su fallo en cada reconstruccion.
                self.incidencias.append({
                    "event_id": ev["event_id"], "tipo": tipo,
                    "motivo": "registrado pero nunca aplicado: no se reproduce",
                })
                continue
            self._aplicar(tipo, p, ev["event_id"])
        return self.arrancada

    def _instrumento(self, iid, moneda=None, lote=None):
        return Instrumento(
            iid, moneda=moneda or self.moneda,
            lote=(self.lote if lote is None else float(lote)))

    def _aplicar(self, tipo: str, p: dict, event_id: str):
        L = self.libro
        if tipo == "REGISTRAR_INSTRUMENTO":
            L.registrar_instrumento(self._instrumento(
                p["instrumento"], p.get("moneda"), p.get("lote")))
        elif tipo == "RESERVA":
            L.reservar_orden(p["order_id"], p["importe"])
        elif tipo == "LIBERACION":
            L.liberar_orden(p["order_id"])
        elif tipo == "COMPRA":
            L.comprar(p["instrumento"], p["cantidad"], p["precio"],
                      momento=p.get("momento"),
                      coste_rel=p.get("coste_rel", 0.0),
                      coste_fijo=p.get("coste_fijo", 0.0),
                      riesgo_inicial=p.get("riesgo_inicial", 0.0),
                      motivo=p.get("motivo", ""),
                      reducir_si_no_cabe=False,
                      event_id=event_id, order_id=p.get("order_id"),
                      cantidad_pre_admision=p.get("cantidad_pre_admision", 0.0))
        elif tipo == "VENTA":
            L.vender(p["instrumento"], p["cantidad"], p["precio"],
                     momento=p.get("momento"),
                     coste_rel=p.get("coste_rel", 0.0),
                     coste_fijo=p.get("coste_fijo", 0.0),
                     motivo=p.get("motivo", ""), event_id=event_id)
        elif tipo == "LIQUIDAR":
            L.liquidar_pendientes(p.get("momento"))
        elif tipo == "VALORAR":
            L.valorar(p["instrumento"], p["precio"], p.get("momento"))

    # ---- arranque explicito ----

    def arrancar(self, capital: float, motivo: str, event_id=None):
        """Abre la cuenta con un saldo DECLARADO.

        No se deriva inventario de los trades de la modalidad antigua: esos
        se abrieron sin descontar caja, asi que absorberlos importaria un
        estado que nunca fue consistente. Quien quiera conciliarlos tiene
        que hacerlo con eventos explicitos, y `conciliar_modalidad_antigua`
        dice cuales quedan fuera.
        """
        if self.arrancada:
            return False
        eid = event_id or f"arranque-{VARIANTE}"
        nuevo = self._registrar(eid, "ARRANQUE", {
            "capital": float(capital), "moneda": self.moneda,
            "lote": self.lote, "permitir_fraccionado": self.permitir_fraccionado,
            "dias_liquidacion": self.dias_liquidacion, "motivo": motivo})
        # El arranque se aplica EN la reconstruccion, asi que se marca
        # antes: si no, el replay lo saltaria por no estar aplicado y la
        # cuenta no existiria nunca.
        if nuevo:
            self._marcar_aplicado(eid)
        self.reconstruir()
        return nuevo

    def _exigir_cuenta(self):
        if self.libro is None:
            raise CuentaInvalida(
                "la cuenta no esta arrancada: hace falta un evento ARRANQUE "
                "con su capital declarado y su motivo. No se supone un saldo.")

    # ---- lectura ----

    def estado(self) -> dict:
        if self.libro is None:
            return {"arrancada": False, "variante": VARIANTE}
        L = self.libro
        return {
            "arrancada": True,
            "variante": VARIANTE,
            "moneda": L.moneda_cuenta,
            "efectivo": L.efectivo,
            "efectivo_utilizable": L.efectivo_utilizable,
            "reservado": L.reservado,
            "derechos": L.derechos,
            "inventario": {k: v.cantidad for k, v in L.posiciones.items()
                           if v.cantidad > 0},
            "reservas_por_orden": dict(L._reservas),
            "eventos": len(self.eventos()),
        }

    def nav(self, precios=None) -> dict:
        """NAV con los precios dados, y dice cuando NO es evaluable.

        La valoracion no se guarda como evento: no mueve dinero, se deriva
        de los precios de ahora. Guardar una por ciclo llenaria el registro
        de hechos que no son hechos.

        Una posicion sin precio admisible NO se valora a cero ni se
        silencia: si solo hay una marca anterior se usa y se dice que es
        arrastrada; si no hay ninguna, el NAV no es evaluable.
        """
        self._exigir_cuenta()
        L = self.libro
        precios = precios or {}
        valor, arrastradas = 0.0, []
        for iid, pos in L.posiciones.items():
            if pos.cantidad <= 0:
                continue
            p = precios.get(iid)
            try:
                p = float(p)
            except (TypeError, ValueError):
                p = None
            if p is None or not (p > 0):
                if pos.precio_valoracion > 0:
                    p = pos.precio_valoracion
                    arrastradas.append(iid)
                else:
                    return {"evaluable": False,
                            "motivo": (f"{iid} tiene {pos.cantidad} unidades "
                                       f"y ninguna marca admisible"),
                            "efectivo": L.efectivo}
            mult = getattr(L.instrumentos.get(iid), "multiplicador", 1.0)
            valor += pos.cantidad * p * mult
        return {
            "evaluable": True,
            "nav": L.efectivo + valor + L.derechos - L.obligaciones,
            "efectivo": L.efectivo,
            "efectivo_utilizable": L.efectivo_utilizable,
            "valor_posiciones": valor,
            "derechos": L.derechos,
            "marcas_arrastradas": arrastradas,
        }

    @property
    def efectivo_utilizable(self) -> float:
        self._exigir_cuenta()
        return self.libro.efectivo_utilizable

    def cantidad(self, instrumento) -> float:
        return 0.0 if self.libro is None else self.libro.cantidad(instrumento)

    # ---- admision ----

    def admitir(self, *, order_id, instrumento, lado, cantidad, precio,
                coste_rel=0.0, coste_fijo=0.0, moneda=None, lote=None,
                momento=None) -> dict:
        """Comprueba TODO y reserva, o rechaza sin tocar nada.

        Lo que se comprueba antes de escribir una sola fila: identidad de la
        orden, producto registrado, moneda, inventario, lote, caja
        utilizable y direccion. Un SELL sin largo suficiente se rechaza
        aqui; en esta modalidad una senal de venta NO se convierte en
        apertura corta en ningun punto.
        """
        self._exigir_cuenta()
        if not order_id:
            return {"admitida": False, "cantidad": 0.0,
                    "motivo": "orden sin identificador"}
        if lado not in ("BUY", "SELL"):
            return {"admitida": False, "cantidad": 0.0,
                    "motivo": f"lado desconocido: {lado!r}"}
        precio = float(precio)
        if not (precio > 0):
            return {"admitida": False, "cantidad": 0.0,
                    "motivo": f"precio no admisible: {precio!r}"}

        inst = self._instrumento(instrumento, moneda, lote)
        if inst.moneda != self.libro.moneda_cuenta:
            return {"admitida": False, "cantidad": 0.0,
                    "motivo": (f"{instrumento} cotiza en {inst.moneda} y la "
                               f"cuenta esta en {self.libro.moneda_cuenta}: "
                               f"no hay FX y no se asume paridad 1:1")}
        eid_instr = f"instr-{instrumento}-{inst.moneda}-{inst.lote}"
        self._registrar(eid_instr, "REGISTRAR_INSTRUMENTO",
                        {"instrumento": instrumento, "moneda": inst.moneda,
                         "lote": inst.lote})
        self.libro.registrar_instrumento(inst)
        self._marcar_aplicado(eid_instr)

        pedida = float(cantidad)
        en_lote = inst.redondear_a_lote(max(0.0, pedida))
        if en_lote <= 0:
            return {"admitida": False, "cantidad": 0.0,
                    "motivo": (f"{pedida} no alcanza el lote minimo "
                               f"{inst.lote} de {instrumento}")}

        if lado == "SELL":
            disponible = self.libro.cantidad(instrumento)
            if disponible <= 0:
                return {"admitida": False, "cantidad": 0.0,
                        "motivo": (f"venta de {instrumento} sin inventario: "
                                   f"en una cuenta al contado eso seria abrir "
                                   f"un corto, y no esta permitido")}
            if en_lote > disponible + 1e-9:
                en_lote = inst.redondear_a_lote(disponible)
                if en_lote <= 0:
                    return {"admitida": False, "cantidad": 0.0,
                            "motivo": (f"el inventario de {instrumento} "
                                       f"({disponible}) no llega al lote")}
            return {"admitida": True, "cantidad": en_lote,
                    "cantidad_pedida": pedida, "reserva": 0.0,
                    "motivo": ("recortada al inventario disponible"
                               if en_lote < pedida - 1e-9 else "")}

        # BUY: cuanto cabe DE VERDAD con la caja utilizable, contando costes.
        maxima = self.libro.cantidad_maxima_comprable(
            instrumento, precio, coste_rel, coste_fijo)
        admisible = min(en_lote, inst.redondear_a_lote(maxima))
        if admisible <= 0:
            return {"admitida": False, "cantidad": 0.0,
                    "motivo": (f"no cabe: utilizable "
                               f"{self.libro.efectivo_utilizable:.2f}, "
                               f"necesario para {en_lote} "
                               f"{en_lote * precio * inst.multiplicador:.2f} "
                               f"mas costes")}
        nominal = admisible * precio * inst.multiplicador
        importe = nominal + nominal * coste_rel + coste_fijo
        try:
            self._registrar(f"res-{order_id}", "RESERVA",
                            {"order_id": order_id, "importe": importe})
            self.libro.reservar_orden(order_id, importe)
            # Marcada SOLO si la reserva se hizo: una reserva que no cupo
            # no es un hecho, y no debe reproducirse al reconstruir.
            self._marcar_aplicado(f"res-{order_id}")
        except OperacionNoEjecutable as e:
            return {"admitida": False, "cantidad": 0.0, "motivo": str(e)}
        return {"admitida": True, "cantidad": admisible,
                "cantidad_pedida": pedida, "reserva": importe,
                "motivo": ("recortada por caja"
                           if admisible < en_lote - 1e-9 else "")}

    def liberar(self, order_id) -> float:
        """Libera SOLO la reserva de esa orden. Repetirlo no libera mas."""
        self._exigir_cuenta()
        importe = self.libro.reserva_de(order_id)
        if importe <= 0:
            return 0.0
        self._registrar(f"lib-{order_id}", "LIBERACION", {"order_id": order_id})
        liberado = self.libro.liberar_orden(order_id)
        self._marcar_aplicado(f"lib-{order_id}")
        return liberado

    # ---- fills ----

    def aplicar_fill(self, *, event_id, order_id, instrumento, lado, cantidad,
                     precio, coste_rel=0.0, coste_fijo=0.0, momento=None,
                     riesgo_inicial=0.0, motivo="", cantidad_pre_admision=0.0):
        """Aplica el fill una sola vez. Repetir el event_id no cambia nada."""
        self._exigir_cuenta()
        payload = {
            "order_id": order_id, "instrumento": instrumento,
            "cantidad": float(cantidad), "precio": float(precio),
            "coste_rel": float(coste_rel), "coste_fijo": float(coste_fijo),
            "momento": momento, "riesgo_inicial": float(riesgo_inicial),
            "motivo": motivo,
            "cantidad_pre_admision": float(cantidad_pre_admision),
        }
        tipo = "COMPRA" if lado == "BUY" else "VENTA"
        nuevo = self._registrar(event_id, tipo, payload)
        if not nuevo:
            # Ya aplicado: ni caja ni inventario se mueven.
            return {"aplicado": False, "repetido": True,
                    "estado": self.estado()}
        try:
            self._aplicar(tipo, payload, event_id)
        except (OperacionNoEjecutable, LibroInvalido) as e:
            # El evento queda en el registro SIN marcar como aplicado, y el
            # estado se reconstruye para que no haya un libro a medio
            # aplicar. El fallo es dato, y no vuelve a reproducirse.
            self.reconstruir()
            return {"aplicado": False, "error": f"{type(e).__name__}: {e}",
                    "estado": self.estado()}
        self._marcar_aplicado(event_id)
        return {"aplicado": True, "repetido": False, "estado": self.estado()}

    # ---- conciliacion con la modalidad antigua ----

    def conciliar_modalidad_antigua(self, trades_abiertos) -> dict:
        """Dice que trades viejos NO estan en este inventario.

        No los absorbe: se abrieron sin descontar caja, asi que importarlos
        traeria un estado que nunca fue consistente. Esto los enumera para
        que la decision sea explicita y de alguien.
        """
        fuera, dentro = [], []
        for t in (trades_abiertos or []):
            tk = (t.get("ticker") if isinstance(t, dict)
                  else getattr(t, "ticker", None))
            if tk is None:
                continue
            (dentro if self.cantidad(tk) > 0 else fuera).append(tk)
        return {
            "variante": VARIANTE,
            "trades_antiguos_sin_inventario": sorted(set(fuera)),
            "trades_antiguos_con_inventario": sorted(set(dentro)),
            "_nota": ("los de la primera lista pertenecen a la modalidad "
                      "anterior, que no descontaba caja. No se importan: "
                      "hacen falta eventos explicitos para conciliarlos."),
        }
