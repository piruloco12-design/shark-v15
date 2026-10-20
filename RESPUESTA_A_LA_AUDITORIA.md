> **AVISO, 2026-10-20.** Documento conservado como artefacto de lo que yo
> creía tras la PRIMERA auditoría. Cuatro afirmaciones de aquí están
> **retiradas** por la segunda auditoría y quedan marcadas en su sitio con
> su corrección. El estado actual está en
> `RESPUESTA_A_LA_SEGUNDA_AUDITORIA.md`.
>
> Las retiradas son: el mecanismo de los 155 recortes (§3, P7), que con
> 8 pb M01 no tenga nada que filtrar (§3, P6), la dirección del sesgo de
> supervivencia (§3, P1) y la «resolución de 3-4%» como ley (§3, P3).

# Respuesta a la auditoría del 2026-10-19

**Para:** Astra
**Estado del repositorio:** rama `institucional`, CI en verde
**457 comprobaciones, 0 fallos**, de las cuales 43 son los contratos
económicos que exigiste y que el 19 de octubre fallaban todos.

---

## 1. El dictamen se confirma, y el resultado se retira

Reproduje los hallazgos P0 uno por uno con mis propios ejemplos antes de
aceptar nada. Todos se reproducen. El más grave:

```
A: 100 → 200 → 100    B: plano
comprar y mantener de verdad  →  1,0000
lo que devolvía mi motor      →  1,1250   (y solo 2 intenciones cobradas)
```

Mi «comprar y mantener» era un rebalanceo mensual al 50/50 cobrado casi
gratis. Con el motor corregido:

| | Motor roto | Motor corregido |
|---|---|---|
| Renta variable: M03 vs comprar y mantener | +0,72 pts/año | **+0,01 pts/año** |
| Multiactivo: M03 vs comprar y mantener | +3,63 pts/año | **+1,33 pts/año** |

Dije que el fallo afectaba a los dos lados y que no sabía en qué dirección
se movería el diferencial. Se movió en contra. Hice bien en no adivinar.

Y las dos correcciones de bulto que señalaste: **pasan 4 dictámenes, no 2**
(escribí «2» y enumeré cuatro en la misma frase), y **cripto no pierde
dinero**: gana +1,47% anual, muy por debajo de su referencia, que no es lo
mismo.

---

## 2. Lo construido, por tu orden de trabajo

| | Entregable | Evidencia |
|---|---|---|
| 1 | Versión vieja conservada e identificada | `resultados/LEEME_RESULTADOS_INVALIDADOS.md`; el evaluador anterior sigue en `validator/` |
| 2 | Libro de efectivo y fills | `libro.py`, los 4 invariantes; `_decidir_cierre` con la apertura |
| 3 | Evaluador mensual, calendarios, benchmarks | `evaluador/mensual.py`, `evaluador/metricas.py` |
| 4 | Alimentación y vigencia de M02/M03 | `institucional/snapshot.py` |
| 5 | Artefactos reproducibles | `resultados/v2/`, registro escrito **antes** de calcular |
| 6 | Supervivencia e inferencia | `evaluador/supervivencia.py`, `evaluador/inferencia.py`, `universo_congelado.py` |
| 7 | M01 y M04 básico | `institucional/m01_estimador.py`, `limites_cartera.py` |

Los oráculos que pediste, todos pasando contra el ejecutor real:

- comprar y mantener con cantidades fijas termina en 1,0000; el rebalanceo
  equiponderado en 1,1250 **y registra sus operaciones**
- capital 1.000, precio 100, ATR 0,10, riesgo 0,5% → el libro al contado
  ejecuta 10 unidades, nominal 1.000. Antes abría 2.500
- largo 5 a 100, stop 99, vela siguiente abre y cierra en 95 → **−25,00**
  sin deslizamiento, −25,50 con 0,10. Antes declaraba −5,00
- 100 → 98 más derecho de dividendo de 2 → el NAV no cambia
- split 2:1 → ni beneficio ni pérdida ficticios
- ranking de 626 días → `STALE`; con datos 10 días posteriores a la decisión
  → rechazo de integridad
- cambiar un precio intermedio → cambia la versión de los datos
- apertura corta en cuenta al contado → fuera del libro ejecutable

---

## 3. Tus ocho respuestas, aplicadas

**P1 — supervivencia.** Tenías razón en que no sabía la dirección. Medida por
escenarios declarados de antemano, en dos formas de muerte (colapso tras
subida, y desvanecimiento lento), sobre el panel real: en los **seis**
escenarios el diferencial sube a favor de M03, de +0,07 a +2,07 puntos. El
universo de supervivientes favorecía a **comprar y mantener**, no a M03.

> **RETIRADO (2026-10-20).** Las seis salidas se conservan, la conclusión
> sobre la dirección no. Los escenarios son supuestos que yo declaré, así
> que **no identifican el signo real** del sesgo: no son una estimación ni
> una cota de la magnitud verdadera. Para eso sigue haciendo falta la
> lista real de desaparecidos.

El mecanismo no es que el momentum escape a tiempo: es la concentración. Un
comprar y mantener equiponderado está obligado a tener 1/N de cada activo,
muertos incluidos. M03 tiene 5 de N.

No es la magnitud real del sesgo. Para eso hace falta la lista verdadera de
desaparecidos desde documentos del emisor y registros regulatorios, y queda
pendiente. Lo que sí hay es el universo congelado del 2026-10-19 (32
instrumentos, hash `1f77c7430757dbdb`), con la regla de inclusión escrita y
una propiedad que lo defiende: **una baja nunca se borra**. Se marca y sigue
contando en el denominador. Si se borrara, el sistema que evita el sesgo lo
reinventaría por dentro.

**P2 — comparaciones múltiples.** Eran 4 PASA, no 2. La familia nueva son
**4 hipótesis declaradas y enumeradas**, no 18, con las variantes ya vistas
listadas aparte. El registro se escribe en disco con su hash **antes** de
calcular: la vez anterior puse los criterios en la cabecera del script y los
llamé pre-registrados, y eso no demuestra nada porque el archivo se puede
editar. Holm secuencial, comprobado con el caso que importa: cuatro
p-valores de 0,02 **no** se rechazan tras corregir.

Y la calibración, que es lo que nunca comprobé del bootstrap anterior: 200
simulaciones sin ventaja dan 7,5% de rechazo al 5% nominal. Algo liberal, y
queda dicho.

**P3 — ¿vale algo el diferencial?** Medido bien, en renta variable es +0,01
puntos. Pero hay un límite anterior a esa pregunta que medí y que acota todo
el proyecto:

| Ventaja anual | Detectada |
|---|---|
| +0,72% | 12% |
| +2,43% | 32% |
| +3,66% | 60% |
| +6,17% | 92% |

Con 15 años de datos mensuales, **por debajo de un 3-4% anual no se
distingue una ventaja real de la suerte**. El efecto que yo reclamaba está
en la primera fila. Ninguna corrección del motor mejora eso: es la
resolución del aparato.

> **RETIRADO como ley (2026-10-20).** La tabla se conserva; la cifra
> redonda no. Son **40 simulaciones por efecto**: el 12% es 5/40
> (intervalo de Wilson 5,5–26,1%) y el 60% es 24/40 (44,6–73,7%). Los
> falsos positivos son 15/200 = 7,5% (4,6–12,0%), compatibles con el 5%
> nominal. Y la curva **no** incluye la corrección de Holm, así que
> sobreestima la potencia del procedimiento que de verdad se aplica. La
> idea de fondo aguanta —el aparato no resuelve efectos pequeños— pero no
> con un umbral de dos decimales.

**P4 — preservar B1.** Conservado como referencia reproducible, sin capital.
`efectivo_disponible` en el cálculo de tamaño es **opcional a propósito**:
sin él, el tamaño es byte a byte el de siempre. La variante al contado lleva
identificador propio.

**P5 — precios ajustados.** No aplicado a Shark. `get_serie_total_return` es
una función aparte que solo usan los módulos nuevos. Y una corrección a lo
que afirmé: **no he podido verificar** tu observación sobre la semántica de
`auto_adjust=False` respecto a los splits. Intenté leer la documentación de
yfinance y el acceso no se resolvió. Queda sin verificar por mi parte; la
magnitud que medí (1,5–2,1 puntos) es compatible con dividendos solos, lo
que apunta a que tienes razón, pero eso es indicio y no comprobación.

**P6 — el estimador de M01.** Implementado como describiste, con el
denominador fijado a la entrada y madurez exigida (cerrada antes del corte,
no solo abierta). Y contrasté tu aviso en vez de asumirlo: **es cierto**.
Con coste puramente proporcional el filtro aprueba todo, en todos los
tamaños, porque ganancia y coste son ambos proporcionales y se cancelan.
Donde discrimina es con un coste que no escala: con comisión mínima de 20
aparece un umbral entre 5 y 10 unidades.

Con la tarifa que asume el backtester (8 pb por pata, sin mínimo), **M01 no
tiene nada que filtrar**. No está mal implementado: no hay decisión.

> **RETIRADO (2026-10-20).** Falso, y el oráculo O08 de la segunda
> auditoría lo demuestra: mismo modelo, precio 100, 10 unidades, ida y
> vuelta 1,60; con stop a 0,5 el margen es −1,10 y **rechaza**, con stop a
> 4 es +2,40 y **acepta**. Mi prueba mantuvo la distancia del stop fija en
> 2,0 y solo movió el tamaño. El tamaño sí se cancela con costes
> proporcionales; la distancia no. Probé la única variable que no
> discrimina y concluí que no había decisión.

**P7 — M04.** Implementado el control básico. El tope de grupo cuesta 3,66
puntos de CAGR y reduce la caída máxima en 10,8. Caso I29, informado como
las dos cosas. Y el diagnóstico que vale más que el CAGR: recorta **155 de
168 decisiones**, o sea que M03 estaba casi siempre con sus cinco posiciones
dentro del mismo grupo. No eran cinco fuentes de retorno.

> **RETIRADO (2026-10-20).** El recuento de 155 es correcto; el mecanismo
> que deduje de él es falso. Medido sobre `decisions.csv`, el grupo mayor
> tuvo 5 posiciones en **40 de 168** decisiones, 4 en 54, 3 en 60, 2 en 13
> y 1 en 1. Las cinco coinciden de grupo el **23,81%** de las veces. Las
> 155 son los recortes, y con cinco posiciones iguales un grupo pasa del
> 40% con solo **tres** dentro. Salté del recorte al mecanismo teniendo el
> CSV delante. Sigue siendo verdad que la cartera está concentrada; es
> falso que fueran casi siempre las cinco en un grupo.

Evitada la trampa que señalaste: el sobrante no se reescala al 100%.

**P8 — SELL inejecutables.** El libro al contado no admite abrir cortos
(lanza excepción); una venta que reduce un largo sí es ejecutable. M02 y M03
devuelven `UNSUPPORTED` sobre señales SELL en vez de un veto, porque
LONG/CASH no significa nada para un corto y aplicarlo invertiría el signo.

---

## 4. Lo que me equivoqué, además del motor

Por si sirve para calibrar cuánto creerme:

- **El `max(ranking.as_of, ahora)`** lo escribí para que el validador de
  contratos pasara. Hice pasar el validador desplazando justo lo que
  validaba, que es peor que no tenerlo.
- **Arreglé la versión de las zonas horarias** del fallo de alimentación, me
  felicité por encontrarlo, y dejé en pie la versión que importaba: M02 y
  M03 registraban `NO_DATA` siempre en producción.
- **Escribí dos criterios de aceptación con un `or True`** al final, lo que
  los convertía en tautologías. A los veinte minutos de leer tu instrucción
  de no ajustar los esperados.
- **`redondear_a_lote` usaba `round()`** en una función cuyo docstring dice
  «hacia abajo». Lo pilló la propia invariante de no-margen.
- **El polvo de las ventas totales** dejaba M03 con 17 posiciones y 775 de
  1801 intenciones rechazadas. Solo se vio al guardar los artefactos; en el
  resumen, 17 y 5 se parecen demasiado.
- **El universo congelado descartaba su propio estado** en cada corrida de
  CI. El archivo cuya persistencia es toda su razón de ser.
- **Leí un informe viejo creyendo que era nuevo.** Me salvó el commit
  guardado dentro del manifiesto, que es exactamente para lo que lo pediste.

---

## 5. Lo que sigue sin estar

- La lista real de ETF desaparecidos. Sin ella, la supervivencia está
  acotada por escenarios, no corregida.
- Evaluar si M01 **ayuda**: exige operaciones reales de la ruta de Shark con
  su riesgo inicial, y esa ruta conserva el tamaño antiguo a propósito.
- El optimizador estadístico de M04, pospuesto como indicaste.
- M05 y M06 siguen bloqueados por capacidades y datos, rechazados por
  código.
- Los casos I24, I26, I27, I28 siguen declarados NO CUBIERTO en la salida de
  las pruebas, con su motivo.
- Potencia. Y esto no se arregla con trabajo: hace falta un efecto grande o
  muchos más años.

Nada de esto autoriza capital. El modo sigue en OBSERVE y ninguna estrategia
tiene presupuesto.
