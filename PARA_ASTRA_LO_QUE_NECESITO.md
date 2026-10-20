# Lo que necesito de ti

**De:** Claude · **Para:** Astra · **2026-10-20**

Documento técnico. Las 24 puertas de `PLAN_CLAUDE.md` pasan y el estado
completo está en `RESPUESTA_A_LA_SEGUNDA_AUDITORIA.md`. Esto es solo lo
que **no puedo resolver yo**, con la medida que enmarca cada punto y lo
que haría por defecto si no contestas. Cada pregunta está escrita para que
puedas responderla en una línea.

Las clasifico por lo que son, porque no todas son del mismo tipo:
decisiones de política que no me corresponden, especificaciones que me
faltan, datos que no tengo, y una pregunta de diseño que decide si el
proyecto puede producir evidencia.

---

## A. Decisiones de política: tu criterio ejecutable contra tu prosa

### A1. O13 — `cantidad('MUERTO') == 0` contra «no inventes pérdida total»

Tu criterio ejecutable es `result['_libro'].cantidad('MUERTO') == 0`. Tu
nota en el mismo oráculo dice «si solo falta una cotización no se debe
inventar la liquidación: debe degradarse la calidad y exigir evidencia del
evento». Y el plan, cambio 3: «Sin esa información, marca incertidumbre;
no inventes pérdida total ni venta al último cierre».

Retirar las unidades sin cobro **es** una pérdida total. Tu fixture no
declara ningún evento. Las dos exigencias no son simultáneamente
satisfacibles con solo las series.

Implementé las cuatro conductas y las medí sobre tu fixture exacto
(`resultados/v3/o13_tres_conductas.json`):

| | unidades | NAV final | `nav_fiable` |
|---|---|---|---|
| A — sin evento, `MARCAR_INCERTIDUMBRE` | 4,8387 | 865,5451 | **false**, 55 días no evaluables |
| B — sin evento, `EXIGIR_EVENTO` | — | no emite NAV | — |
| C — evento declarado, 50/unidad, cobro T+5 | 0 | 865,5451 | true |
| D — evento declarado, cobro 0 | 0 | **623,6096** | true |

A y C dan el mismo NAV con estatus epistémico opuesto. C y D difieren en
241,94, que es la distancia entre «repartió 50 por unidad» y «no repartió
nada». El motor no puede elegir entre C y D desde la serie.

**Lo que necesito:** cuál de las cuatro es la conducta por defecto que
quieres, o si el criterio ejecutable de O13 debe reescribirse para exigir
un evento en el fixture. Por defecto dejo A (NAV marcado no fiable) y O13
en rojo.

### A2. O09 — el criterio no lee mi código

`all(n==10 for n,_ in samples)`, donde `samples` es tu reconstrucción del
algoritmo roto escrita a mano con `np.arange(10)[a:a+5]`. No invoca mi
función para medir longitudes, así que es falso por construcción.

Lo único que lee mi código es `media_bootstrap_funcion`: **5,6214 →
4,5100** sobre una media verdadera de 4,50. Expuse
`m01_estimador.medias_remuestreadas(valores, bloque, remuestras, semilla)`
y `_indices_bloques_circulares(n, bloque, rng)` precisamente para que el
oráculo pueda medir longitudes y centrado contra el código real.

**Lo que necesito:** confirmación de que los bloques circulares de
longitud fija satisfacen el requisito, y si vas a reapuntar el oráculo a
`medias_remuestreadas`. Por defecto lo dejo en rojo y documentado.

---

## B. Especificaciones que me faltan

### B1. Cobertura del bootstrap: ¿contra qué proceso?

El plan dice: «Evalúa cobertura para los procesos temporales pertinentes;
el algoritmo no garantiza inferencia válida en cualquier régimen». No
está medida y no voy a inventarme el proceso generador, porque ese es
exactamente el error que cometí con los escenarios de supervivencia:
declaré supuestos propios y luego los traté como si acotaran algo real.

Lo que tengo: la calibración empírica del contraste sobre el panel real
(200 simulaciones sin ventaja → 7,5% de rechazo al 5% nominal, intervalo
4,6–12,0%).

**Lo que necesito:** el proceso contra el que medir cobertura, con
parámetros. Por ejemplo AR(1) con φ declarado, o un GARCH(1,1) con
coeficientes, o remuestreo por bloques del propio panel con longitud
fijada; más la cobertura nominal objetivo y el número de réplicas que
consideras suficiente. Sin esa especificación, por defecto dejo la
cobertura **no medida** y declarada como no medida.

### B2. La tarifa: es el supuesto que puede invalidarlo todo

Escenario declarado: 0,0008 por pata, **sin mínimo por orden**. Con 1.000
de capital y cinco posiciones, cada posición son ~200. Un mínimo de 1 por
orden son 50 pb por pata sobre esa posición, no 8. Seis veces el supuesto.

He medido la sensibilidad sobre el panel real guardado
(`resultados/v3/sensibilidad_tarifa.json`): escenarios de 0 pb, 8 pb sin
mínimo, y 8 pb más mínimo de 0,50, 1 y 2 por orden, en los dos universos.

Esto importa más que cualquier otra cosa de este documento: si la ventaja
de +1,33 puntos en multiactivo no sobrevive a una tarifa de minorista al
nivel de capital real, el resultado no describe nada ejecutable, y tu
propio aviso sobre M01 pasa a ser el centro del problema en vez de una
nota al margen.

**Lo que necesito:** una tarifa de referencia que consideres defendible
para declarar como escenario base (comisión por pata, mínimo por orden,
horquilla asumida, y si procede custodia). No tengo acceso a tarifarios
reales desde aquí y no quiero inventar un número y llamarlo escenario.

### B3. Redimensionar a la apertura: ¿qué convención?

El límite de admisión recalcula la cantidad con el precio ejecutable. Lo
declaré explícito en el docstring de `limites_cartera.admitir`:
redimensionar con la apertura supone que la orden se envía **después** de
observar ese precio, así que rellenarla exactamente a la apertura es
optimista, no un hecho.

Las alternativas que veo: (a) admitir con el cierre anterior y aceptar los
rechazos cuando la apertura se mueve; (b) rellenar a apertura más k veces
la horquilla, con k declarado; (c) orden límite al precio de admisión y
registrar la no ejecución cuando el mercado se va.

**Lo que necesito:** cuál es la convención defendible. Por defecto dejo la
actual con su aviso.

### B4. Diseño de la medición de utilidad de M01

El plan: «aplica las decisiones del filtro y vuelve a ejecutar la cartera
con la secuencia y el capital reales». B1 conserva su dimensionado antiguo
a propósito, así que la comparación tiene que ser **B1 al contado filtrada
por M01** contra **B1 al contado sin filtrar** — no contra la B1
histórica, porque esa ruta tenía otra contabilidad y mezclar las dos sería
transferir rendimiento entre modalidades.

**Lo que necesito:** confirmación de ese par de comparación, y si el
riesgo inicial para el denominador de R debe salir del `stop_inicial` de
la ruta al contado o del de la B1 histórica cuando difieran por el recorte
de efectivo.

---

## C. Datos que no tengo

### C1. La lista real de ETF desaparecidos

Sin ella la supervivencia está **acotada por escenarios declarados**, que
no es una estimación ni una cota del sesgo real — ya retiré esa
afirmación. El universo congelado del 2026-10-19 (32 instrumentos, hash
`1f77c7430757dbdb`) solo evita empeorarlo desde hoy hacia adelante.

**Lo que necesito:** de dónde sale una lista de bajas defendible, con
nombre concreto de la fuente. Y si existe alguna cota defendible **sin**
esa lista, o si la respuesta correcta es que el sesgo queda sin acotar y
así debe informarse.

---

## D. La pregunta que decide si esto puede producir evidencia

### D1. No hay diseño confirmatorio posible sobre estos datos

El estado real: las series ya se han mirado, varias veces, con varias
versiones del motor. El registro está etiquetado `EXPLORATORIO` y ninguna
corrección lo cambia — renombrar un tramo ya observado no lo convierte en
datos nuevos, como tú mismo señalaste.

Y la potencia medida: con 15 años de datos mensuales, 40 simulaciones por
efecto, el 12% de detección a +0,72% anual (Wilson 5,5–26,1%) y el 60% a
+3,66% (44,6–73,7%), **sin** la corrección de Holm, que la empeora. El
efecto medido en renta variable es +0,0105 puntos. Está tres órdenes de
magnitud por debajo de lo que el aparato resuelve.

Las salidas que veo, con su coste:

1. **Holdout congelado hacia adelante desde hoy.** Honesto y sin fuga, y
   con esta potencia necesita décadas para decir algo sobre un efecto de
   este tamaño. El universo congelado ya está preparado para esto.
2. **Ampliar la sección transversal** (más instrumentos, más mercados)
   para ganar observaciones independientes sin esperar años. Cambia el
   universo, así que es otro experimento con su propio registro.
3. **Cambiar la clase de señal o la frecuencia.** Otro proyecto, no una
   variante.
4. **Aceptar que es exploratorio para siempre** y no volver a presentar
   ninguna cifra de aquí como evidencia de ventaja.

**Lo que necesito:** cuál de las cuatro, y sobre todo la **regla de
abandono**. Con qué resultado concreto se declara que este universo y esta
clase de señal no tienen ventaja que encontrar, y se deja de medir. Sin
esa regla escrita de antemano, cada corrección del motor se convierte en
una excusa para volver a mirar los mismos datos, que es precisamente el
bucle en el que llevo dos auditorías.

### D2. Capacidades mínimas antes de considerar capital

`capacidades_core.py` declara seis capacidades y **ninguna está
verificada** contra un broker: no hay conexión, ni credenciales, ni una
orden real enviada. Moneda y cortos están BLOQUEADAS (si el supuesto
falla, para la máquina); lotes, comisiones, liquidación y calendario son
SUPUESTAS, que es peor, porque producen un resultado creíble.

**Lo que necesito:** la lista mínima que exigirías verificada —y cómo
verificarla sin operar— antes de que tenga sentido siquiera hablar de
capital. Mi suposición es que el orden es: tarifa real con mínimos,
fraccionamiento admitido, liquidación efectiva y calendario de sesiones.

---

## E. Lo que NO necesito que revises

Para que no gastes tiempo: los cinco cambios están medidos con el caso que
fallaba antes, y los oráculos tuyos que pasan son 13 de 15. No necesito
confirmación de que A01, A02, A03, O05, O06, O07, O11, O12, O14 y O15
están arreglados — están, con el antes y el después en
`resultados/v3/puertas_*.txt` y `resultados/v3/oraculos_astra_*.json`.

Lo que sí agradezco que mires con desconfianza, porque son mis juicios y
no medidas: la decisión de **no** cambiar la base de riesgo de B1 al
reparar la contabilidad (§3 de la respuesta), y el argumento de por qué el
titular no se mueve pese a que tres contratos estaban roto (§8 de la
respuesta). Si en cualquiera de los dos he razonado hacia la conclusión
que me convenía, prefiero saberlo ahora.

---

## F. Cómo verificar todo esto

```bash
# Las 24 puertas del plan, desplegadas en 41 comprobaciones
python tests/test_puertas.py

# El experimento completo de punta a punta, SIN red, con series sinteticas
python tests/test_experimento_humo.py

# Toda la bateria: 499 comprobaciones
for t in tests/test_*.py; do python "$t"; done

# Tus oraculos contra este arbol
python oraculos_v2.py --repo . --salida mis_oraculos.json

# Las tablas, generadas DESDE el resultado y no a mano
python evaluador/informe_tablas.py resultados/v3/report.json
```

Evidencia del antes y el después de cada cambio en `resultados/v3/`:
`puertas_ANTES_cambio1.txt` frente a `puertas_DESPUES_cambio*.txt`, y
`oraculos_astra_antes.json` frente a `oraculos_astra_tras_cambio*.json`.

`resultados/v2/` está restaurado al estado de `037d373` —el que viajó en
el paquete que auditaste— con `LEEME_SOBRESCRITURAS.md` explicando que CI
lo pisó siete veces y con las cifras de cada corrida.
