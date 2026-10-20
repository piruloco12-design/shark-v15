"""
M04 básico: límites de exposición y concentración sobre el libro.

POR QUE AHORA, con una sola estrategia

Yo pregunté si M04 aportaba algo teniendo una estrategia y el 93% de
exposición. La auditoría contestó que sí, y el argumento es bueno: una
estrategia puede tener varias posiciones, activos correlacionados, y dos
órdenes que compitan por el mismo saldo. La reserva transaccional no aparece
cuando hay dos estrategias; aparece en cuanto hay dos órdenes.

Esto es la PRIMERA variante, la que no necesita estadística: efectivo,
reservas, lotes, topes por instrumento y por grupo, y concentración
observable. El control de volatilidad con covarianzas viene después, cuando
haya serie de cartera fiable, y reducir volatilidad no garantiza mejorar el
retorno neto.

LA TRAMPA QUE EVITA, textual de la auditoría:

    «No normalizar automáticamente todos los pesos otra vez al 100% después
     de aplicar topes, porque eso puede violar el límite que se acaba de
     imponer.»

Es exactamente el error que se comete al escribir esto rápido: aplicas un
tope del 20%, los pesos ya no suman uno, y «arreglas» el resto
reescalándolos — con lo que el que acabas de limitar vuelve a subir. Aquí el
sobrante se queda en efectivo, que es una salida legítima.

GRUPOS

Cinco ETF de tecnología no son cinco fuentes de retorno. Los grupos permiten
decir «no más del 40% en renta variable» sin tener que estimar una matriz de
covarianzas que con estos datos no sería fiable. Un ETF sin grupo declarado
cuenta como su propio grupo: no se mete en «otros» por descarte, porque eso
escondería concentración.
"""

from __future__ import annotations

from dataclasses import dataclass, field

TOLERANCIA = 1e-9


class LimiteInvalido(ValueError):
    """Una configuración de límites que no se puede cumplir."""


@dataclass(frozen=True)
class LimitesCartera:
    """Topes duros. No son penalizaciones que un optimizador pueda pagar."""

    # Peso máximo de un instrumento sobre el patrimonio.
    max_por_instrumento: float = 1.0
    # Peso máximo de un grupo sobre el patrimonio.
    max_por_grupo: float = 1.0
    # Exposición total máxima. Menos de 1 deja efectivo a propósito.
    max_exposicion_total: float = 1.0
    # Número máximo de posiciones simultáneas.
    max_posiciones: int = 1000
    # Reserva de efectivo que no se invierte, para costes y holgura.
    reserva_costes: float = 0.0
    # instrumento -> grupo. Lo que no esté declarado es su propio grupo.
    grupos: dict = field(default_factory=dict)

    def __post_init__(self):
        for nombre in ("max_por_instrumento", "max_por_grupo",
                       "max_exposicion_total", "reserva_costes"):
            v = float(getattr(self, nombre))
            if not (0.0 <= v <= 1.0):
                raise LimiteInvalido(f"{nombre} fuera de [0,1]: {v}")
        if self.max_posiciones < 1:
            raise LimiteInvalido("max_posiciones debe ser al menos 1")
        if self.reserva_costes + TOLERANCIA >= self.max_exposicion_total \
                and self.max_exposicion_total > 0:
            raise LimiteInvalido(
                f"la reserva de costes ({self.reserva_costes}) consume toda "
                f"la exposicion permitida ({self.max_exposicion_total}): "
                f"no quedaria nada que invertir"
            )

    def grupo_de(self, instrumento: str) -> str:
        return self.grupos.get(instrumento, f"_solo_{instrumento}")


def aplicar(objetivos: dict, limites: LimitesCartera) -> tuple[dict, dict]:
    """Recorta los pesos deseados hasta cumplir TODOS los límites.

    Devuelve (pesos efectivos, diagnóstico). El sobrante NO se redistribuye:
    se queda en efectivo. Redistribuirlo violaría el tope que acaba de
    aplicarse, que es el error contra el que avisa la auditoría.

    El orden del recorte es determinista y está declarado: primero el tope
    por instrumento, luego el de grupo, luego el número de posiciones, y al
    final la exposición total. Si el orden fuera otro, el resultado podría
    cambiar, así que no se deja al azar del diccionario.
    """
    deseados = {t: float(w) for t, w in (objetivos or {}).items()
                if float(w) > TOLERANCIA}
    diag = {"pedido": dict(deseados), "recortes": []}

    if not deseados:
        diag["efectivo_libre"] = 1.0
        return {}, diag

    # --- 1) tope por instrumento ---
    efectivos = {}
    for t, w in deseados.items():
        if w > limites.max_por_instrumento + TOLERANCIA:
            diag["recortes"].append({
                "tipo": "instrumento", "instrumento": t,
                "de": round(w, 6), "a": round(limites.max_por_instrumento, 6)})
            w = limites.max_por_instrumento
        efectivos[t] = w

    # --- 2) tope por grupo: se recorta proporcionalmente DENTRO del grupo ---
    por_grupo: dict[str, list] = {}
    for t in efectivos:
        por_grupo.setdefault(limites.grupo_de(t), []).append(t)
    for grupo, miembros in sorted(por_grupo.items()):
        suma = sum(efectivos[t] for t in miembros)
        if suma > limites.max_por_grupo + TOLERANCIA:
            factor = limites.max_por_grupo / suma
            diag["recortes"].append({
                "tipo": "grupo", "grupo": grupo,
                "miembros": sorted(miembros),
                "de": round(suma, 6),
                "a": round(limites.max_por_grupo, 6),
                "factor": round(factor, 6)})
            for t in miembros:
                efectivos[t] *= factor

    # --- 3) número de posiciones: se quedan las de mayor peso ---
    if len(efectivos) > limites.max_posiciones:
        orden = sorted(efectivos.items(), key=lambda kv: (-kv[1], kv[0]))
        fuera = [t for t, _ in orden[limites.max_posiciones:]]
        diag["recortes"].append({
            "tipo": "numero_posiciones",
            "limite": limites.max_posiciones,
            "excluidos": sorted(fuera)})
        efectivos = {t: w for t, w in orden[:limites.max_posiciones]}

    # --- 4) exposición total, descontando la reserva de costes ---
    techo = max(0.0, limites.max_exposicion_total - limites.reserva_costes)
    suma = sum(efectivos.values())
    if suma > techo + TOLERANCIA:
        factor = techo / suma if suma > 0 else 0.0
        diag["recortes"].append({
            "tipo": "exposicion_total",
            "de": round(suma, 6), "a": round(techo, 6),
            "factor": round(factor, 6),
            "reserva_costes": limites.reserva_costes})
        efectivos = {t: w * factor for t, w in efectivos.items()}

    # El sobrante se queda en efectivo. A PROPOSITO.
    efectivos = {t: w for t, w in efectivos.items() if w > TOLERANCIA}
    diag["efectivo_libre"] = round(1.0 - sum(efectivos.values()), 6)
    diag["efectivos"] = {t: round(w, 6) for t, w in efectivos.items()}

    # Comprobación final: lo que sale tiene que cumplir todo. Si no, es un
    # fallo de este codigo, no un dato.
    verificar(efectivos, limites)
    return efectivos, diag


def verificar(pesos: dict, limites: LimitesCartera):
    """Lanza si los pesos violan algún límite. Es la red de seguridad."""
    if not pesos:
        return
    for t, w in pesos.items():
        if w > limites.max_por_instrumento + 1e-6:
            raise LimiteInvalido(
                f"{t} con peso {w:.6f} supera el tope por instrumento "
                f"{limites.max_por_instrumento}")
    por_grupo: dict[str, float] = {}
    for t, w in pesos.items():
        g = limites.grupo_de(t)
        por_grupo[g] = por_grupo.get(g, 0.0) + w
    for g, suma in por_grupo.items():
        if suma > limites.max_por_grupo + 1e-6:
            raise LimiteInvalido(
                f"el grupo {g} con {suma:.6f} supera el tope por grupo "
                f"{limites.max_por_grupo}")
    if len(pesos) > limites.max_posiciones:
        raise LimiteInvalido(
            f"{len(pesos)} posiciones superan el maximo "
            f"{limites.max_posiciones}")
    techo = limites.max_exposicion_total - limites.reserva_costes
    total = sum(pesos.values())
    if total > techo + 1e-6:
        raise LimiteInvalido(
            f"exposicion total {total:.6f} supera el techo {techo:.6f}")


def concentracion(pesos: dict, limites: LimitesCartera) -> dict:
    """Concentración observable: pesos reales, máximo y posiciones efectivas.

    `1 / suma(w^2)` sobre la parte invertida: el inverso de Herfindahl de
    los PESOS.

    Correccion de lo que decia antes este docstring. Afirmaba que cinco ETF
    que comparten gran parte de sus acciones podian dar un numero de
    posiciones efectivas cercano a uno. Es falso: cinco posiciones
    equiponderadas dan exactamente 5,0 por mucho que solapen, porque esta
    medida solo ve los pesos. No ve correlaciones ni carteras compartidas.
    Para eso hace falta la composicion de cada fondo o la covarianza de sus
    retornos, y ninguna de las dos esta aqui.
    """
    if not pesos:
        return {"invertido": 0.0, "peso_maximo": 0.0, "posiciones": 0,
                "posiciones_efectivas": 0.0, "por_grupo": {}}
    invertido = sum(pesos.values())
    norm = [w / invertido for w in pesos.values()]
    por_grupo: dict[str, float] = {}
    for t, w in pesos.items():
        g = limites.grupo_de(t)
        por_grupo[g] = por_grupo.get(g, 0.0) + w
    return {
        "invertido": round(invertido, 6),
        "peso_maximo": round(max(pesos.values()), 6),
        "posiciones": len(pesos),
        "posiciones_efectivas": round(1.0 / sum(x * x for x in norm), 3),
        "por_grupo": {g: round(v, 6) for g, v in sorted(por_grupo.items())},
        "grupo_mayor": max(por_grupo.items(), key=lambda kv: kv[1])[0],
    }


# Grupos del universo que usamos. Declarados, no inferidos: un ETF sin
# grupo cuenta como su propio grupo y asi no se esconde concentracion.
GRUPOS_UNIVERSO = {
    # Renta variable amplia
    "SPY": "renta_variable", "QQQ": "renta_variable",
    "IWM": "renta_variable", "DIA": "renta_variable",
    "MDY": "renta_variable",
    # Sectores: comparten acciones con los indices amplios, asi que van
    # en el MISMO grupo a proposito.
    "XLE": "renta_variable", "XLF": "renta_variable",
    "XLK": "renta_variable", "XLV": "renta_variable",
    "XLI": "renta_variable", "XLP": "renta_variable",
    "XLY": "renta_variable", "XLU": "renta_variable",
    "XLB": "renta_variable",
    # Materias primas
    "GLD": "materias_primas", "SLV": "materias_primas",
    "USO": "materias_primas", "DBC": "materias_primas",
    "DBA": "materias_primas", "UNG": "materias_primas",
    "PPLT": "materias_primas",
    # Bonos
    "TLT": "bonos", "IEF": "bonos", "LQD": "bonos",
    "HYG": "bonos", "SHY": "bonos",
    # Divisas
    "FXE": "divisas", "FXY": "divisas", "FXB": "divisas",
    "FXF": "divisas", "UUP": "divisas",
}


# =====================================================================

def admitir(cantidad_pedida, instrumento, precio_ejecutable, libro,
            limites: LimitesCartera, *, coste_rel: float = 0.0):
    """Limite de ADMISION: el tope recalculado con el precio ejecutable.

    Son tres cosas distintas y el plan exige nombrarlas por separado:

    - **objetivo mensual**: el peso que la estrategia quiere al decidir,
      con el cierre del dia de la decision.
    - **limite de admision** (esto): el tope que se comprueba al aceptar
      la orden, con el precio al que de verdad va a ejecutarse.
    - **limite continuo**: un tope vigilado todos los dias. NO esta
      implementado y no se declara como si lo estuviera: exigiria
      rebalanceo diario, que es OTRA estrategia, con su identificador,
      sus costes y su experimento.

    Hacia falta porque el tope se aplicaba al objetivo y nadie volvia a
    mirarlo: con un objetivo del 40% fijado a un cierre de 100 y una
    apertura a 200, las cuatro unidades compradas eran el 80% del
    patrimonio, informado como tope duro del 40%.

    Nota de ejecucion declarada: redimensionar con la apertura supone que
    la orden se envia DESPUES de observar ese precio. Rellenarla luego
    exactamente a la apertura es un supuesto optimista, no un hecho; queda
    dicho aqui en vez de escondido en el resultado.

    Devuelve `(cantidad_admisible, motivo)`. La cantidad se redondea
    siempre HACIA ABAJO.
    """
    if cantidad_pedida <= 0:
        return 0.0, ""
    try:
        nav = float(libro.nav())
    except Exception as e:
        return 0.0, f"NAV no evaluable: {str(e)[:40]}"
    precio_ejecutable = float(precio_ejecutable)
    if not (nav > 0) or not (precio_ejecutable > 0):
        return 0.0, "NAV o precio no admisibles"

    inst = libro.instrumentos.get(instrumento)
    mult = getattr(inst, "multiplicador", 1.0) if inst is not None else 1.0
    valor_unidad = precio_ejecutable * mult
    if valor_unidad <= 0:
        return 0.0, "valor unitario no admisible"

    ya = libro.cantidad(instrumento) * valor_unidad
    grupo = limites.grupo_de(instrumento)

    valor_grupo_otros = 0.0
    expuesto_otros = 0.0
    for t, pos in libro.posiciones.items():
        if t == instrumento or pos.cantidad <= 0:
            continue
        inst_t = libro.instrumentos.get(t)
        mult_t = getattr(inst_t, "multiplicador", 1.0) if inst_t is not None else 1.0
        valor_t = pos.cantidad * pos.precio_valoracion * mult_t
        expuesto_otros += valor_t
        if limites.grupo_de(t) == grupo:
            valor_grupo_otros += valor_t

    # Numero de posiciones: una posicion NUEVA no entra si ya se alcanzo
    # el tope. Reforzar una existente no crea una posicion.
    abiertas = sum(1 for p in libro.posiciones.values() if p.cantidad > 0)
    if libro.cantidad(instrumento) <= 0 and abiertas >= limites.max_posiciones:
        return 0.0, f"max_posiciones ({limites.max_posiciones}) ya alcanzado"

    techos = {
        "max_por_instrumento": limites.max_por_instrumento * nav,
        "max_por_grupo": limites.max_por_grupo * nav - valor_grupo_otros,
        "max_exposicion_total": (
            (limites.max_exposicion_total - limites.reserva_costes) * nav
            - expuesto_otros),
    }
    nombre_tope = min(techos, key=lambda k: techos[k])
    margen = techos[nombre_tope] - ya
    if margen <= 0:
        return 0.0, f"{nombre_tope} ya consumido (margen {margen:.2f})"

    cantidad_tope = margen / (valor_unidad * (1.0 + max(0.0, coste_rel)))
    admisible = min(float(cantidad_pedida), cantidad_tope)
    if inst is not None:
        admisible = inst.redondear_a_lote(max(0.0, admisible))
    if admisible <= 0:
        return 0.0, f"{nombre_tope}: no cabe ni un lote al precio ejecutable"
    if admisible < float(cantidad_pedida) - TOLERANCIA:
        return admisible, (f"{nombre_tope}: recortada de "
                           f"{float(cantidad_pedida):.6f} a {admisible:.6f} "
                           f"con el precio ejecutable {precio_ejecutable:.4f}")
    return admisible, ""
