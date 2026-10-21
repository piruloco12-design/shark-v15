"""
CAPACIDADES DE LA RUTA AL CONTADO — con su estado de verificación real.

## La corrección que obliga a reescribir este archivo

La versión anterior declaraba moneda y cortos como BLOQUEADAS citando
`LibroContado`. **Era falso.** La ruta que de verdad abre posiciones es
`paper_broker.open_trade`, y no pasaba por el libro: no comprobaba moneda,
no reservaba caja, no miraba inventario y no descontaba la compra. La
tercera revisión lo reprodujo con las funciones reales:

    cuenta 1.000, precio 100, ATR 0,10, 8 pb
      comprar A  -> 9,992006 unidades, saldo reportado sigue en 1.000
      comprar B  -> otras 9,992006 unidades
      total      -> 1.998,401279 de nominal + 1,598721 de costes
                    = 2.000 USD comprometidos con 1.000 de saldo
    SELL sin inventario -> operación corta registrada

Comprobé la guarda en el módulo que había construido, no en el camino que
se ejecuta. Un archivo de capacidades que cita el módulo equivocado es
peor que no tenerlo: afirma una garantía que nadie aplica.

Ahora la ruta pasa por `cuenta_contado.CuentaContado`, que reutiliza los
contratos de `LibroContado` y los persiste como eventos. Lo que se declara
aquí está comprobado por `tests/test_integracion_core.py`, que entra por
`open_trade` y `check_and_close_trades` — no por funciones auxiliares.

## Los cinco estados

Tomados de la tercera revisión. La distinción importa porque «el motor lo
impide» y «el bróker lo permite» son afirmaciones distintas, y confundirlas
es lo que produjo el error de arriba.

  SIMULADA
      El motor lo impone en la simulación, y hay una prueba que entra por
      la ruta real. No dice nada de lo que haría un bróker.
  DOCUMENTADA
      Hay un documento público del proveedor. No se ha confirmado contra
      la cuenta concreta de Brian.
  CONFIRMADA_EN_CUENTA_SIN_ORDEN
      Verificado en la cuenta real sin enviar una orden: tarifario de la
      cuenta, previsualización, disponibilidad del instrumento.
  OBSERVADA_EN_FILL_REAL
      Medido en una ejecución real. Es el único estado que dice algo sobre
      fills y deslizamiento.
  DESCONOCIDA
      No se ha verificado. **No se convierte en permitida por defecto:** la
      ruta rechaza y registra la causa.

Hoy no hay NINGUNA capacidad en CONFIRMADA_EN_CUENTA_SIN_ORDEN ni en
OBSERVADA_EN_FILL_REAL. No hay conexión, ni credenciales, ni una orden
enviada.
"""

SIMULADA = "SIMULADA"
DOCUMENTADA = "DOCUMENTADA"
CONFIRMADA_SIN_ORDEN = "CONFIRMADA_EN_CUENTA_SIN_ORDEN"
OBSERVADA_EN_FILL = "OBSERVADA_EN_FILL_REAL"
DESCONOCIDA = "DESCONOCIDA"

CAPACIDADES = {
    "moneda": {
        "declara": "cuenta en USD; se rechaza cualquier instrumento que no "
                   "cotice en USD",
        "estado": SIMULADA,
        "donde": "cuenta_contado.CuentaContado.admitir",
        "prueba": "tests/test_integracion_core.py::I3",
        "limite": "El panel está en USD. Qué moneda tiene la cuenta de "
                  "Brian y qué conversión se aplicaría es DESCONOCIDO.",
    },
    "cortos": {
        "declara": "una señal SELL sin inventario se rechaza en la "
                   "admisión; no se abre corto en ningún punto",
        "estado": SIMULADA,
        "donde": "cuenta_contado.CuentaContado.admitir",
        "prueba": "tests/test_integracion_core.py::I2",
        "limite": "Antes esta misma línea decía BLOQUEADA citando un módulo "
                  "que la ruta no usaba, y la ruta registraba el corto.",
    },
    "caja_y_reservas": {
        "declara": "una compra descuenta nominal y coste; la caja se "
                   "reserva por order_id y no se puede comprometer dos "
                   "veces; el cierre devuelve el cobro a la misma cuenta",
        "estado": SIMULADA,
        "donde": "cuenta_contado + paper_broker.open_trade / "
                 "check_and_close_trades",
        "prueba": "tests/test_integracion_core.py::I1, I6, I8",
        "limite": "Qué saldo considera disponible el bróker, y si un cobro "
                  "pendiente permite otra compra, es DESCONOCIDO.",
    },
    "lotes_y_fracciones": {
        "declara": "acciones enteras (config.LOTE_CORE = 1.0); el "
                   "fraccionado es otra capacidad y hay que declararla",
        "estado": SIMULADA,
        "donde": "config.LOTE_CORE -> cuenta_contado.admitir",
        "prueba": "tests/test_integracion_core.py::I4, I4b",
        "limite": "Trading 212 publica soporte de fracciones [F9 de la "
                  "tercera revisión], lo que sería DOCUMENTADA para ese "
                  "proveedor; para esta cuenta y estos 31 instrumentos, "
                  "DESCONOCIDA.",
    },
    "comisiones": {
        "declara": "coste_rel * nominal + coste_fijo por pata "
                   "(config.COSTE_POR_PATA, COSTE_FIJO_POR_ORDEN), cobrado "
                   "en el fill de cada pata",
        "estado": SIMULADA,
        "donde": "cuenta_contado.aplicar_fill -> libro.comprar / vender",
        "prueba": "tests/test_integracion_core.py::I8b",
        "limite": "Es un coste ADITIVO, no un mínimo: max(c*N, m) es otra "
                  "fórmula y no está implementada. Trading 212 publica "
                  "comisión cero en Invest [F1], lo que haría DOCUMENTADA "
                  "una tarifa distinta de la declarada aquí. Horquilla, "
                  "deslizamiento, terceros y FX: DESCONOCIDOS.",
    },
    "liquidacion": {
        "declara": "T+0 (config.DIAS_LIQUIDACION_CORE = 0): el cobro de "
                   "una venta es utilizable el mismo día",
        "estado": SIMULADA,
        "donde": "config.DIAS_LIQUIDACION_CORE -> CuentaContado",
        "prueba": "tests/test_puertas.py::V03, V03b (derechos tipados)",
        "limite": "Es el supuesto OPTIMISTA. El libro ya sabe diferir con "
                  "derechos de cobro, así que T+1 o T+2 es configuración; "
                  "qué aplica la cuenta real es DESCONOCIDO.",
    },
    "calendario": {
        "declara": "las sesiones son las fechas que trae el proveedor; la "
                   "zona de mercado la resuelve zona_mercado.resolver()",
        "estado": DESCONOCIDA,
        "donde": "zona_mercado + data_feed",
        "prueba": "tests/test_arreglos.py (filtro de sesión, falla cerrada)",
        "limite": "No hay calendario oficial de festivos. Un día sin precio "
                  "se trata como día sin negociación, y eso NO demuestra "
                  "que el mercado estuviera cerrado. Horario extendido, "
                  "subastas y tipos de orden: DESCONOCIDOS.",
    },
    "acciones_corporativas": {
        "declara": "splits, dividendos y liquidaciones se aplican como "
                   "eventos declarados con fuente, importe y fechas",
        "estado": SIMULADA,
        "donde": "libro.dividendo / split / liquidar_instrumento",
        "prueba": "tests/test_puertas.py::V04, V05b, V19",
        "limite": "En la ruta viva NADIE inyecta todavía esos eventos: "
                  "existe el canal y no hay fuente conectada. Cambios de "
                  "ticker, fusiones y bajas: DESCONOCIDOS.",
    },
    "fills_y_deslizamiento": {
        "declara": "nada",
        "estado": DESCONOCIDA,
        "donde": "—",
        "prueba": "—",
        "limite": "No hay ninguna observación de un fill real. El precio de "
                  "ejecución simulado es un supuesto declarado, no una "
                  "medida, y ninguna prueba de este repositorio puede "
                  "cambiar eso.",
    },
}

# Identificador de la modalidad. Existe para que no se mezcle el
# rendimiento de B1 historica (sin costes en el capital, sin tope de
# efectivo, sin inventario) con el de B1 ejecutada al contado.
VARIANTE_EJECUCION = "B1_AL_CONTADO_v2"

ORDEN_DE_VERIFICACION = (
    "1. Cuenta y entidad: Invest o CFD, país, moneda principal, saldos.",
    "2. Instrumentos: ISIN, bolsa, disponibilidad de compra en esa cuenta.",
    "3. Acceso minorista: documento aplicable y restricciones (PRIIPs/KID "
    "en la UE). Una cotización pública en EEUU no acredita acceso.",
    "4. Lotes y fracciones, y tipos de orden admitidos para ese "
    "instrumento.",
    "5. Costes: tarifario de la cuenta y desglose de una previsualización, "
    "sin confirmar el envío. Terceros y FX por separado.",
    "6. Caja y liquidación: qué saldo se puede usar y cuándo se libera.",
    "7. Cortos y margen: producto y permiso efectivo.",
    "8. Sesiones, horarios y acciones corporativas.",
)


def resumen_texto() -> str:
    por_estado: dict = {}
    for nombre, d in CAPACIDADES.items():
        por_estado.setdefault(d["estado"], []).append(nombre)
    lineas = [f"Variante de ejecucion: {VARIANTE_EJECUCION}", ""]
    for nombre, d in CAPACIDADES.items():
        lineas.append(f"[{d['estado']:<32}] {nombre}")
        lineas.append(f"     declara: {d['declara']}")
        lineas.append(f"     prueba:  {d['prueba']}")
    lineas.append("")
    for estado in (SIMULADA, DOCUMENTADA, CONFIRMADA_SIN_ORDEN,
                   OBSERVADA_EN_FILL, DESCONOCIDA):
        lineas.append(f"{estado}: {len(por_estado.get(estado, []))}")
    lineas.append("")
    lineas.append("Ninguna capacidad esta confirmada en una cuenta real ni "
                  "observada en un fill real.")
    lineas.append("Una capacidad DESCONOCIDA no se vuelve permitida por "
                  "defecto: la ruta rechaza y registra la causa.")
    return "\n".join(lineas)


if __name__ == "__main__":
    print(resumen_texto())
