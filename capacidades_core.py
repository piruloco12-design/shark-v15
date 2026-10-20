"""
CAPACIDADES DE EJECUCION DEL CORE — declaradas, no verificadas.

El plan de la segunda auditoria lo exige antes de conectar el core:

    "Antes de conectar el core, declara capacidades comprobadas: moneda,
     lotes/fracciones, comisiones, liquidacion, cortos y calendario. No
     extrapoles fills sinteticos ajustados a acciones reales."

Y aqui va la parte incomoda: NO hay ninguna capacidad *comprobada*. No
existe conexion con un broker, ni credenciales, ni una sola orden real
enviada. Todo lo que sigue es un SUPUESTO declarado. Decirlo asi es el
unico informe honesto que puedo dar; rellenar esta tabla con un
"verificado" seria inventarlo.

Que significa cada estado:

  SUPUESTA   el motor se comporta como si esto fuera cierto, y nadie lo
             ha confirmado contra un broker.
  BLOQUEADA  el motor se niega a operar si la condicion no se cumple, asi
             que un supuesto equivocado da un error, no un numero falso.

La diferencia importa: una capacidad SUPUESTA puede estar mal y producir
un resultado creible. Una BLOQUEADA, si esta mal, para la maquina.
"""

CAPACIDADES = {
    "moneda": {
        "supuesto": "cuenta en USD; todo instrumento cotiza en USD",
        "estado": "BLOQUEADA",
        "mecanismo": "libro.LibroContado._exigir_moneda rechaza la orden "
                     "antes de tocar el libro. No se asume paridad 1:1.",
    },
    "lotes_y_fracciones": {
        "supuesto": "acciones enteras (lote 1) en el core; el evaluador "
                    "permite fraccionado como escenario aparte",
        "estado": "SUPUESTA",
        "mecanismo": "Instrumento.redondear_a_lote, siempre hacia abajo. "
                     "Si el broker real no admite fraccionado, el "
                     "escenario fraccionado del evaluador no es ejecutable.",
    },
    "comisiones": {
        "supuesto": "0,0008 por pata, sin minimo por orden "
                    "(config.COSTE_POR_PATA y COSTE_FIJO_POR_ORDEN)",
        "estado": "SUPUESTA",
        "mecanismo": "paper_broker.contabilizar_cierre cobra las dos patas. "
                     "La tarifa no esta contrastada con ningun broker, y un "
                     "minimo por orden cambiaria las conclusiones de M01.",
    },
    "liquidacion": {
        "supuesto": "el dinero de una venta es utilizable el mismo dia "
                    "(dias_liquidacion = 0 en el core)",
        "estado": "SUPUESTA",
        "mecanismo": "Es el supuesto OPTIMISTA. El libro ya sabe diferir "
                     "con derechos de cobro tipados, asi que subirlo a T+1 "
                     "o T+2 es configuracion, no obra nueva.",
    },
    "cortos": {
        "supuesto": "no hay prestamo de valores ni margen",
        "estado": "BLOQUEADA",
        "mecanismo": "libro.abrir_corto lanza OperacionNoEjecutable. Una "
                     "venta que reduce un largo si es ejecutable; abrir "
                     "corto no.",
    },
    "calendario": {
        "supuesto": "las sesiones son las fechas que trae el proveedor de "
                    "datos; la zona de mercado se resuelve por "
                    "zona_mercado.resolver()",
        "estado": "SUPUESTA",
        "mecanismo": "No hay calendario oficial de festivos. Un dia sin "
                     "precio se trata como dia sin negociacion, y eso NO "
                     "demuestra que el mercado estuviera cerrado.",
    },
}

# Identificador de la modalidad de ejecucion. Existe para que no se mezcle
# el rendimiento de B1 historica (sin costes en el capital, sin tope de
# efectivo) con el de B1 ejecutada al contado. El plan lo pide explicito:
# "No transfieras el rendimiento de una modalidad a otra".
VARIANTE_EJECUCION = "B1_AL_CONTADO_v1"


def resumen_texto() -> str:
    lineas = [f"Variante de ejecucion: {VARIANTE_EJECUCION}", ""]
    for nombre, d in CAPACIDADES.items():
        lineas.append(f"[{d['estado']:<9}] {nombre}: {d['supuesto']}")
    bloqueadas = sum(1 for d in CAPACIDADES.values()
                     if d["estado"] == "BLOQUEADA")
    lineas.append("")
    lineas.append(f"{bloqueadas} de {len(CAPACIDADES)} capacidades paran la "
                  f"maquina si el supuesto falla. El resto, no.")
    lineas.append("Ninguna esta verificada contra un broker real.")
    return "\n".join(lineas)


if __name__ == "__main__":
    print(resumen_texto())
