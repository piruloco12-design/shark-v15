"""
M01: el estimador mínimo legítimo de ganancia bruta esperada.

DE DONDE SALE

Pregunté cuál sería el estimador mínimo admisible para el umbral económico
de M01. La respuesta de la auditoría:

    «Una media histórica de ganancia bruta normalizada, calculada solo con
     etiquetas maduras anteriores a la decisión, es un punto de partida
     legítimo. Que sea legítima no significa que sea suficientemente precisa
     para filtrar operaciones.»

Y un aviso que hay que comprobar, no asumir:

    «Si todas las operaciones reciben el mismo pronóstico y el mismo coste
     relativo, el filtro será prácticamente "todas o ninguna".»

Eso es contrastable y se contrasta en tests/test_m01.py. Si el filtro es
todo-o-nada, no discrimina, y un filtro que no discrimina no es un filtro:
es un interruptor de encendido disfrazado.

LAS DEFINICIONES, de la sección P6

    riesgo_inicial_j = cantidad_j * abs(precio_entrada_j - stop_inicial_j)
    R_bruto_j        = P&L_bruto_j / riesgo_inicial_j
    R_neto_j         = (P&L_bruto_j - costes_totales_j) / riesgo_inicial_j

El denominador se fija A LA ENTRADA. No se redefine con un stop movido
después: si se recalculara con el stop final, una operación que movió el
stop a favor tendría un denominador pequeño y un R enorme, y el estimador
premiaría justo lo que no debe.

Las observaciones con riesgo cero o desconocido no son utilizables. No se
rellenan con la media ni se tratan como cero: se descartan y se cuentan.

MADUREZ

Una etiqueta solo entra en el entrenamiento si la operación CERRÓ antes del
corte. No basta con que se abriera antes: una operación abierta el día antes
del corte y cerrada un mes después contiene información posterior al corte,
y usarla es fuga. Esto se comprueba con un oráculo en las pruebas.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

VERSION = "2026-10-19.m01.1"


class DatosInsuficientes(RuntimeError):
    """No hay muestra para estimar. El estado correcto es NO_DATA."""


@dataclass(frozen=True)
class Operacion:
    """Una operación cerrada, con lo necesario para normalizar su resultado."""

    id: str
    abierta_en: object
    cerrada_en: object
    cantidad: float
    precio_entrada: float
    stop_inicial: float          # el de la ENTRADA, no el movido después
    pnl_bruto: float
    costes_totales: float
    moneda: str = "USD"
    estrategia: str = ""
    direccion: str = "BUY"

    @property
    def riesgo_inicial(self) -> float:
        return abs(float(self.cantidad)) * abs(
            float(self.precio_entrada) - float(self.stop_inicial))

    @property
    def utilizable(self) -> bool:
        r = self.riesgo_inicial
        return bool(math.isfinite(r) and r > 0
                    and math.isfinite(float(self.pnl_bruto))
                    and math.isfinite(float(self.costes_totales)))

    @property
    def R_bruto(self) -> float:
        if not self.utilizable:
            raise DatosInsuficientes(
                f"{self.id}: riesgo inicial {self.riesgo_inicial}, no "
                f"utilizable. No se rellena con la media ni se trata como "
                f"cero.")
        return float(self.pnl_bruto) / self.riesgo_inicial

    @property
    def R_neto(self) -> float:
        if not self.utilizable:
            raise DatosInsuficientes(f"{self.id}: no utilizable")
        return ((float(self.pnl_bruto) - float(self.costes_totales))
                / self.riesgo_inicial)


# =====================================================================

@dataclass(frozen=True)
class ModeloR:
    """El modelo más simple que es legítimo: una media y su cota inferior."""

    modelo_id: str
    mu_R: float                  # media de R bruto
    L_R: float                   # cota inferior de esa media
    n: int
    descartadas: int
    desde: object
    hasta: object
    moneda: str
    estrategia: str
    direccion: str
    metodo_cota: str

    def a_dict(self):
        return {
            "modelo_id": self.modelo_id, "mu_R": round(self.mu_R, 6),
            "L_R": round(self.L_R, 6), "n": self.n,
            "descartadas": self.descartadas,
            "desde": str(self.desde), "hasta": str(self.hasta),
            "moneda": self.moneda, "estrategia": self.estrategia,
            "direccion": self.direccion, "metodo_cota": self.metodo_cota,
            "version": VERSION,
        }


METODO_REMUESTREO = "bloques circulares de longitud fija"


def _indices_bloques_circulares(n, bloque, rng):
    """Indices de UNA replica: bloques circulares, exactamente n.

    El pseudocodigo del plan, literal:

        mientras longitud(indices) < n:
            inicio = uniforme_entero(0, n-1)
            anadir [(inicio+j) mod n para j=0..bloque-1]
        muestra = valores[indices[:n]]

    El `mod n` es lo que faltaba. La version anterior hacia
    `v[i:i + bloque]`, y numpy TRUNCA al final del array: un bloque que
    empieza en 7 con bloque 5 devolvia [7,8,9] en vez de envolver a
    [7,8,9,0,1]. Se perdian los valores del principio, la replica salia
    con menos de n valores y la media subia. Medido sobre 0..9 con
    bloque 5: la media remuestreada daba 5,62 cuando la verdadera es 4,50.
    Una cota inferior calculada sobre medias sesgadas al alza es una cota
    que no acota.
    """
    n = int(n)
    bloque = max(1, min(int(bloque), n))
    idx = []
    while len(idx) < n:
        inicio = int(rng.integers(0, n))
        idx.extend((inicio + j) % n for j in range(bloque))
    return idx[:n]


def medias_remuestreadas(valores, *, bloque=5, remuestras=2000,
                         semilla=90210):
    """Las medias de cada replica. Expuesta para poder comprobarla.

    El sesgo del remuestreo anterior no se veia desde fuera: la funcion
    solo devolvia un percentil. Devolver las medias permite comprobar que
    el remuestreo esta centrado en la media verdadera, que es la
    propiedad que importa y la que estaba rota.
    """
    v = np.asarray(valores, dtype="float64")
    n = len(v)
    rng = np.random.default_rng(semilla)
    medias = np.empty(int(remuestras), dtype="float64")
    for r in range(int(remuestras)):
        idx = _indices_bloques_circulares(n, bloque, rng)
        medias[r] = v[np.asarray(idx, dtype="int64")].mean()
    return medias


def _cota_inferior_bloques(valores, *, confianza=0.90, bloque=5,
                           remuestras=2000, semilla=90210) -> float:
    """Cota inferior de la media, remuestreando BLOQUES circulares.

    Las operaciones de un sistema de tendencia se agrupan: varias seguidas
    caen en la misma racha. Remuestrearlas una a una supondría
    independencia y daría una cota demasiado optimista. Se remuestrean
    bloques de operaciones consecutivas, y de forma CIRCULAR para que cada
    operación tenga la misma probabilidad de entrar.

    Aviso que el plan exige y que no se puede omitir: este algoritmo no
    garantiza cobertura válida en cualquier régimen. La cobertura hay que
    medirla para el proceso temporal que toque, y aquí no está medida para
    el proceso real de las operaciones de Shark.
    """
    v = np.asarray(valores, dtype="float64")
    n = len(v)
    if n < 10:
        raise DatosInsuficientes(
            f"solo {n} operaciones utilizables: con esta muestra la cota no "
            f"significa nada")
    medias = medias_remuestreadas(v, bloque=bloque, remuestras=remuestras,
                                  semilla=semilla)
    return float(np.percentile(medias, (1.0 - confianza) * 100))


def ajustar(operaciones, *, corte=None, estrategia="", direccion="",
            confianza=0.90, bloque=5) -> ModeloR:
    """Ajusta el modelo SOLO con etiquetas maduras anteriores al corte.

    Madura significa CERRADA antes del corte. Una operación abierta antes y
    cerrada después contiene información posterior al corte: usarla es fuga,
    y es el error más fácil de cometer aquí.
    """
    candidatas, descartadas = [], 0
    for op in operaciones:
        if estrategia and op.estrategia != estrategia:
            continue
        if direccion and op.direccion != direccion:
            continue
        if corte is not None and not (op.cerrada_en is not None
                                      and op.cerrada_en < corte):
            continue
        if not op.utilizable:
            descartadas += 1
            continue
        candidatas.append(op)

    if len(candidatas) < 10:
        raise DatosInsuficientes(
            f"solo {len(candidatas)} operaciones maduras y utilizables "
            f"antes del corte ({descartadas} descartadas por riesgo inicial "
            f"invalido). El estado correcto es NO_DATA, no una estimacion.")

    monedas = {op.moneda for op in candidatas}
    if len(monedas) > 1:
        raise DatosInsuficientes(
            f"operaciones en varias monedas {monedas}: no se promedian R de "
            f"monedas distintas sin normalizar")

    candidatas.sort(key=lambda o: o.cerrada_en)
    R = [op.R_bruto for op in candidatas]
    mu = float(np.mean(R))
    L = _cota_inferior_bloques(R, confianza=confianza, bloque=bloque)

    return ModeloR(
        modelo_id=f"M01_mean_gross_R_v1/{estrategia or 'todas'}"
                  f"/{direccion or 'ambas'}/n{len(R)}",
        mu_R=mu, L_R=L, n=len(R), descartadas=descartadas,
        desde=candidatas[0].cerrada_en, hasta=candidatas[-1].cerrada_en,
        moneda=monedas.pop(), estrategia=estrategia or "todas",
        direccion=direccion or "ambas",
        metodo_cota=f"bootstrap por bloques de {bloque}, percentil "
                    f"{(1-confianza)*100:.0f}",
    )


# =====================================================================

def ganancia_bruta_estimable(cantidad, distancia_stop, modelo: ModeloR) -> float:
    """q * distancia_stop * mu_R. En moneda, no en R."""
    return (abs(float(cantidad)) * abs(float(distancia_stop))
            * float(modelo.mu_R))


def margen_conservador(cantidad, distancia_stop, modelo: ModeloR,
                       coste_ida_vuelta) -> float:
    """q * distancia_stop * L_R - coste_ida_vuelta.

    Usa la COTA INFERIOR, no la media. Que sea positivo no garantiza
    beneficio en esa operación: el error del modelo y la no estacionariedad
    siguen ahí. Es un umbral, no una promesa.
    """
    return (abs(float(cantidad)) * abs(float(distancia_stop))
            * float(modelo.L_R) - float(coste_ida_vuelta))


def decidir(cantidad, distancia_stop, modelo: ModeloR | None,
            coste_ida_vuelta, reserva=0.0) -> dict:
    """La puerta de M01. Sin modelo devuelve UNSUPPORTED, no un permiso."""
    if modelo is None:
        return {
            "estado": "UNSUPPORTED",
            "permite": None,
            "motivo": "sin modelo de ganancia esperada validado fuera de "
                      "muestra; no se sustituye por RSI ni por momentum",
        }
    bruta = ganancia_bruta_estimable(cantidad, distancia_stop, modelo)
    margen = margen_conservador(cantidad, distancia_stop, modelo,
                                coste_ida_vuelta)
    return {
        "estado": "READY",
        "permite": bool(margen > float(reserva)),
        "ganancia_bruta_estimable": round(bruta, 6),
        "margen_conservador": round(margen, 6),
        "coste_ida_vuelta": round(float(coste_ida_vuelta), 6),
        "reserva_exigida": float(reserva),
        "modelo_id": modelo.modelo_id,
        "mu_R": round(modelo.mu_R, 6),
        "L_R": round(modelo.L_R, 6),
        "_aviso": ("un margen positivo NO es una cota de beneficio por "
                   "operacion ni una probabilidad de ganar"),
    }


# =====================================================================

def walk_forward(operaciones, cortes, *, estrategia="", direccion="",
                 confianza=0.90, bloque=5, corte_final=None,
                 minimo_por_tramo=5) -> dict:
    """Ajusta antes de cada corte y evalúa su ventana, SIN solapar.

    Lo que hacía antes: cada corte evaluaba todas las operaciones abiertas
    después, HASTA EL FINAL. Con dos cortes y 25 operaciones futuras, el
    primer tramo veía las 25 y el segundo 15: 40 evaluaciones sobre 25
    operaciones. Eso es promediar prefijos del mismo futuro y presentarlos
    como pruebas independientes.

    Ahora cada operación cae en UNA ventana [corte_i, corte_i+1), por su
    fecha de APERTURA, y se sigue hasta madurar aunque cierre fuera de la
    ventana. El último tramo acaba en un corte final explícito, y las
    etiquetas que no han madurado a esa fecha se cuentan como PENDIENTES
    en vez de colarse en la media.

    Y los errores: antes se restaba un realizado NETO de un pronóstico
    BRUTO, lo que fabrica un error del tamaño del coste. Con un pronóstico
    bruto perfecto y un coste de 0,2 R, el error salía -0,2 R y parecía
    del modelo. Ahora bruto se compara con bruto, neto con neto, y el
    coste va en su propia columna.
    """
    salida = {"version": VERSION, "tramos": [], "incidencias": [],
              "metodo_remuestreo": METODO_REMUESTREO}
    # Sin convertir a pandas: este modulo trabaja con lo que le pasen y
    # solo exige que sea comparable. Convertir aqui introduciria lios de
    # zona horaria entre naive y tz-aware que no son de este problema.
    cortes = sorted(cortes)

    if corte_final is None:
        cerradas = [op.cerrada_en for op in operaciones
                    if op.cerrada_en is not None]
        corte_final = max(cerradas) if cerradas else None
        salida["corte_final_derivado"] = True
        salida["incidencias"].append({
            "corte": "final",
            "motivo": "no se declaró un corte final: se deriva del último "
                      "cierre. El plan pide declararlo explícitamente."})
    else:
        salida["corte_final_derivado"] = False
    salida["corte_final"] = str(corte_final)

    limites = list(cortes) + [corte_final]
    vistas = set()
    pendientes_total = 0

    for i, corte in enumerate(cortes):
        try:
            modelo = ajustar(operaciones, corte=corte, estrategia=estrategia,
                             direccion=direccion, confianza=confianza,
                             bloque=bloque)
        except DatosInsuficientes as e:
            salida["incidencias"].append({"corte": str(corte),
                                          "motivo": str(e)[:160]})
            continue

        # VENTANA propia: [corte_i, corte_i+1). Cada operacion cae en una
        # sola, por su fecha de apertura. Si se tomaran las abiertas antes
        # y cerradas despues, el tramo contendria operaciones que el
        # entrenamiento ya vio empezar.
        fin = limites[i + 1]
        ventana = [op for op in operaciones
                   if op.abierta_en is not None
                   and corte <= op.abierta_en < fin
                   and op.utilizable
                   and (not estrategia or op.estrategia == estrategia)
                   and (not direccion or op.direccion == direccion)]

        # Se siguen hasta madurar aunque cierren fuera de la ventana. Lo
        # que NO ha cerrado al corte final es etiqueta pendiente: no entra
        # en la media, y se cuenta.
        maduras, pendientes = [], 0
        for op in ventana:
            if op.cerrada_en is None or op.cerrada_en > corte_final:
                pendientes += 1
            else:
                maduras.append(op)
        pendientes_total += pendientes

        if len(maduras) < minimo_por_tramo:
            salida["incidencias"].append({
                "corte": str(corte),
                "motivo": f"solo {len(maduras)} operaciones maduras en "
                          f"[{corte}, {fin})"})
            continue

        vistas.update(op.id for op in maduras)
        R_bruto = [op.R_bruto for op in maduras]
        R_neto = [op.R_neto for op in maduras]
        coste_R = float(np.mean(np.asarray(R_bruto) - np.asarray(R_neto)))
        # El pronostico del modelo es BRUTO. El pronostico NETO es ese
        # bruto menos el coste previsto, y se compara con el neto
        # realizado. Magnitudes homogeneas a cada lado.
        pronostico_neto = modelo.mu_R - coste_R
        salida["tramos"].append({
            "corte": str(corte),
            "ventana": [str(corte), str(fin)],
            "modelo": modelo.a_dict(),
            "n_posteriores": len(maduras),
            "etiquetas_pendientes": pendientes,
            "R_bruto_medio_posterior": round(float(np.mean(R_bruto)), 6),
            "R_neto_medio_posterior": round(float(np.mean(R_neto)), 6),
            "R_neto_mediana_posterior": round(float(np.median(R_neto)), 6),
            "coste_R_medio": round(coste_R, 6),
            "pronostico_bruto": round(modelo.mu_R, 6),
            "pronostico_neto": round(pronostico_neto, 6),
            "error_pronostico_bruto": round(
                float(np.mean(R_bruto)) - modelo.mu_R, 6),
            "error_pronostico_neto": round(
                float(np.mean(R_neto)) - pronostico_neto, 6),
            # Clave conservada para el arnes de la auditoria, que la lee
            # por nombre. Ahora vale el error BRUTO contra BRUTO, que es
            # lo que su expectativa pide. La version contaminada
            # (realizado neto menos pronostico bruto) ya no existe: no se
            # conserva un numero equivocado por compatibilidad.
            "error_del_pronostico": round(
                float(np.mean(R_bruto)) - modelo.mu_R, 6),
        })

    salida["operaciones_unicas"] = len(vistas)
    salida["etiquetas_pendientes"] = pendientes_total
    if salida["tramos"]:
        errores = [t["error_pronostico_bruto"] for t in salida["tramos"]]
        errores_netos = [t["error_pronostico_neto"] for t in salida["tramos"]]
        realizados = [t["R_neto_medio_posterior"] for t in salida["tramos"]]
        predichos = [t["modelo"]["mu_R"] for t in salida["tramos"]]
        salida["resumen"] = {
            "tramos_evaluados": len(errores),
            "operaciones_unicas": len(vistas),
            "error_medio_bruto": round(float(np.mean(errores)), 6),
            "error_absoluto_medio": round(
                float(np.mean(np.abs(errores))), 6),
            "error_medio_neto": round(float(np.mean(errores_netos)), 6),
            "coste_R_medio": round(float(np.mean(
                [t["coste_R_medio"] for t in salida["tramos"]])), 6),
            "R_predicho_medio": round(float(np.mean(predichos)), 6),
            "R_realizado_medio": round(float(np.mean(realizados)), 6),
            "_lectura": (
                "si el error absoluto medio es del orden del propio R "
                "predicho, el estimador no esta diciendo nada util: su "
                "pronostico y el ruido son del mismo tamano, igual que pasa "
                "con el contraste de rentabilidad"
            ),
        }
    return salida
