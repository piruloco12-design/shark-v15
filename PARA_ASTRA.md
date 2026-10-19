# SHARK V15 — estado real, lo medido, y en qué necesito guía

**Fecha:** 2026-10-19
**Autor:** Claude (Opus 5), trabajando con Brian
**Repositorio:** `piruloco12-design/shark-v15`, rama `institucional`
**Para:** Astra, que escribió `SHARK_Especificacion_Claude_2026-10-19.md`

---

## 0. Cómo leer esto

Este documento tiene tres partes y conviene no mezclarlas:

1. **Lo que está medido.** Cifras con su procedencia y su archivo. Se puede
   reproducir.
2. **Lo que está implementado** de la sección 15 de tu documento, y lo que
   quedó bloqueado y por qué.
3. **Lo que quiero hacer y las ocho preguntas donde pido guía.** Ahí es donde
   más falta hace una segunda opinión, porque son decisiones de método, no de
   código.

Todo lo que digo que está medido tiene un archivo en `resultados/` que lo
respalda. Si una afirmación de aquí no tiene archivo detrás, está marcada
como suposición. He intentado que no haya ninguna.

Lo que **no** encontrarás: ninguna recomendación de operar con dinero real.
La extensión está en OBSERVE y ninguna estrategia tiene presupuesto.

---

## 1. Qué es el sistema y dónde corre

- **Shark V15 Sniper**: bot de señales sobre ETF y acciones, timeframe 30m,
  reglas de tendencia (EMA200 + RSI + MACD + ADX) con stop y objetivo por ATR.
- **Despliegue**: Render, worker en segundo plano, bucle cada pocos minutos.
  Alertas a Telegram. Operaciones simuladas en un broker de papel propio
  (`paper_broker.py`), SQLite en disco persistente (`/var/data`).
- **Datos**: yfinance como proveedor principal, con cascada a Finnhub, Alpha
  Vantage y Twelve Data. Coinbase para cripto. La suscripción a Polygon se
  canceló. Stooq se retiró de la cascada porque bloquea IP de centros de datos
  y por tanto nunca funciona desde Render ni desde CI.
- **No hay bróker conectado.** No existe ninguna ruta de ejecución real: el
  riesgo de una orden accidental es cero por construcción. Ver
  `CAPABILITIES.json`, que está mantenido a mano y verificado, no es una
  plantilla.
- **Restricción nueva y decisiva**: Brian opera **al contado, sin CFD**
  (decisión del 2026-10-19). No hay cortos ejecutables, ni préstamo de
  valores, ni margen.

**Validación**: GitHub Actions corre en cada push de cualquier rama, antes de
fusionar a `main`, porque Render despliega `main` automáticamente. La corrida
de hoy: **354 comprobaciones, 0 fallos.**

---

## 2. Lo medido

### 2.1 El núcleo de Shark pierde dinero

Backtest diario de 15 años, por clase de activo, criterios fijados antes de
ver los resultados (`resultados/clases.json`, `experimento_clases.txt`):

| Clase | Operaciones | Expectativa (R) | Anual | Comprar y mantener |
|---|---|---|---|---|
| Cripto | 551 | +0,3153 | +1,47% | **+58,08%** |
| Materias primas | 892 | −0,1684 | −1,11% | +1,26% |
| Renta variable | 1.265 | −0,3037 | −3,35% | +11,97% |
| Bonos | 585 | −0,9936 | −5,93% | −1,37% |
| Divisas | 572 | −0,6986 | −3,58% | −0,76% |

Renta variable en detalle: winrate 44,1%, profit factor 0,87, intervalo del
90% por bootstrap **[−0,514, −0,096]**, enteramente por debajo de cero,
P(expectativa>0) = 0,0093. Peor caída −43,7%. 89 operaciones al año.

**Ninguna clase pasa el criterio pre-registrado.** Y ninguna bate a comprar y
mantener.

### 2.2 Dónde está todo el resultado positivo: en los largos

Desglose que hice al confirmarse la restricción del contado:

| Clase | Largos | Cortos | % cortos | Exp. largos | Exp. cortos |
|---|---|---|---|---|---|
| Cripto | 362 | 189 | 34,3% | +0,8026 | −0,6180 |
| Materias primas | 480 | 412 | 46,2% | −0,1527 | −0,1866 |
| Renta variable | 856 | 409 | 32,3% | +0,0613 | **−1,0676** |
| Bonos | 239 | 346 | 59,1% | −1,2276 | −0,8319 |
| Divisas | 266 | 306 | 53,5% | −1,0258 | −0,4142 |

Los cortos pierden en las cinco clases. Y **entre el 32% y el 59% de las
señales que el bot genera hoy no son ejecutables** en una cuenta al contado.
El bot las sigue generando y simulando en papel.

### 2.3 M03 (momentum 12−1) sí pasa los criterios

Experimento nuevo (`validator/experimento_institucional.py`,
`resultados/institucional.json`). Solo largos, mensual, 31 activos, ~14,9
años (2011-11 a 2026-10), coste 8 pb por pata, K=5, criterios escritos en la
cabecera del archivo **antes** de correrlo.

**Universo multiactivo (31 ETF, sin cripto):**

| Variante | Anual | Sharpe | Peor caída | Exposición | Rotación/año |
|---|---|---|---|---|---|
| Comprar y mantener | +6,29% | 0,72 | −16,6% | 93,3% | 0,07 |
| M02 tendencia | +6,23% | 0,66 | −22,3% | 93,3% | 3,78 |
| **M03 momentum 12−1** | **+9,92%** | 0,62 | −27,2% | 93,3% | 5,87 |
| M02 + M03 | +9,89% | 0,62 | −27,9% | 93,3% | 5,80 |
| M03 con banda ±2 pts | +9,16% | 0,63 | −24,5% | 84,1% | 5,29 |
| Efectivo (BIL) | +1,53% | 2,76 | −0,4% | — | — |

**Renta variable (los mismos 14 ETF donde Shark pierde 3,35% al año):**

| Variante | Anual | Sharpe | Peor caída |
|---|---|---|---|
| Comprar y mantener | +12,60% | 0,92 | −23,3% |
| M02 tendencia | +12,38% | 0,95 | −19,1% |
| **M03 momentum 12−1** | **+13,32%** | **1,03** | **−16,0%** |
| M02 + M03 | +13,44% | 1,01 | −16,0% |

Train/test, corte 2020-10-15:

| Bloque | Train (estrategia vs comprar) | Test (estrategia vs comprar) |
|---|---|---|
| Multiactivo M03 | +7,06% vs +3,84% (+3,22) | +10,02% vs +6,40% (+3,62) |
| Renta variable M03 | +12,91% vs +11,31% (+1,60) | +9,99% vs +8,97% (+1,01) |

Mismo signo en las dos mitades, en los dos bloques.

**Veredictos:** de 18 dictámenes (6 bloques × 3 variantes), **pasan 2**:
multiactivo/M03 y multiactivo/M02+M03, más renta_variable/M03 y
renta_variable/M02+M03. M02 solo falla en casi todas partes. Materias primas,
bonos, divisas y cripto: ninguna variante pasa.

### 2.4 El sesgo de los precios sin ajustar, cuantificado

Shark corre con `auto_adjust=False`, o sea precios **sin ajustar** por
dividendos ni splits. Medido sobre el mismo universo:

| | Ajustado | Sin ajustar | Diferencia |
|---|---|---|---|
| Comprar y mantener | +6,29% | +4,80% | **+1,49 pts/año** |
| M03 momentum | +9,92% | +7,81% | **+2,11 pts/año** |

El sesgo perjudica a los largos (un dividendo aparece como caída que el
tenedor no sufrió, porque cobró el dividendo) y favorece a los cortos. Sobre
el +0,96% anual que habíamos medido en Shark, es **del mismo orden de
magnitud que todo el efecto**.

### 2.5 Otras mediciones previas

- **Barrido SL/TP**: 14 de 16 combinaciones positivas, 6 de 8 vecinas →
  meseta, no pico. Exonera la optimización de junio de ser curve-fitting.
- **Pruebas de causalidad**: no se detecta look-ahead. El control negativo
  (`shift(-5)`, que mete futuro a propósito) **sí** se detecta, que es lo que
  valida la prueba.
- **Economía**: +0,058 R por operación × 33 operaciones/año = +0,96% anual.
  Para €1000/mes harían falta **€1.249.403**.

---

## 3. Lo implementado de tu sección 15

Paquete `institucional/`. Modo por defecto **OBSERVE**.

| Archivo | Qué hace |
|---|---|
| `referencia.py` | Tus funciones puras, portadas tal cual. Quité el bloque `_self_test` del runtime, como pide el documento; sus 18 pruebas viven en `tests/` y corren en CI. **Las 18 pasan.** |
| `contratos.py` | `ContextAssessment` y `StrategyProposal` de la 15.3, con validación que rechaza: una evaluación que use un dato posterior a la decisión, un `NO_DATA` disfrazado de veto, un `size_multiplier` > 1, y una propuesta sin `capital_envelope_id`. |
| `configuracion.py` | La config de la 15.11. Rechaza **por código** M05, M06, el netting, la promoción automática, desactivar la preservación de B1, y una estrategia propia sin presupuesto. |
| `vista.py` | Recorte as-of. La vela del día en curso no es visible a media sesión. `cierres_mensuales` para el calendario de M02/M03. |
| `modulos.py` | M01, M02 contexto, M03 ranking. |
| `observacion.py` | El enganche con `live_engine` y almacenamiento en tabla propia. |

### Estado por módulo

| | Estado | Nota |
|---|---|---|
| **M01 costes** | Observando | El umbral económico devuelve **UNSUPPORTED** a propósito: no tenemos estimador de ganancia esperada validado fuera de muestra, y tu documento prohíbe fabricarlo convirtiendo un RSI o un momentum. Solo deja el diagnóstico de coste. |
| **M02 tendencia** | Observando. Medido como estrategia propia: **no pasa** | |
| **M03 ranking 12−1** | Observando. Medido como estrategia propia: **pasa** | |
| **M04 riesgo de cartera** | No implementado | Ver pregunta 7 |
| **M05 pares** | **BLOQUEADO** | Exige cortos ejecutables y préstamo de valores. Cuenta al contado. La configuración lo rechaza. |
| **M06 fundamentales** | **BLOQUEADO** | Exige fundamentales point-in-time. yfinance da ratios *actuales*. Tu documento: "Si solo hay ratios actuales, M06 no tiene un backtest válido". |

### La prueba que protege al bot en vivo

`tests/test_observacion.py` cumple tu paso 2 de la 15.11: corre un ciclo
**completo** de `live_engine` dos veces, **en procesos separados** (varios
módulos leen `DATABASE_NAME` al importarse; en un solo proceso la primera
corrida contaminaría la segunda), con la extensión apagada y encendida, y
exige que sean idénticos: señales, operaciones, estado del broker, eventos de
riesgo y log de decisiones.

Más: barrido de las 8 combinaciones de estado × dirección comprobando que en
OBSERVE nunca se bloquea, el contrapunto de que en ENFORCE **sí** bloquea
cuando toca, y cinco formas de datos basura que no deben convertirse en veto.

**Esa prueba falló tres veces antes de servir de algo, y las tres veces el
fallo era real: pasaba trivialmente** porque cero operaciones llegaban al
bloque observado, así que comparaba dos cosas vacías. Ahora comprueba primero
que el ciclo abrió operaciones y que la observación registró filas; si no,
declara que no demuestra nada.

### Casos I19–I30

Cubiertos: I19, I20, I21, I22, I23, I25, I30.
**No cubiertos, y declarados en voz alta en la salida del test:**

- **I24** (reserva atómica de efectivo entre dos estrategias): no hay libro
  multiestrategia; las propias están desactivadas.
- **I26, I27**: M05 bloqueado.
- **I28**: M06 bloqueado.
- **I29** (más Sharpe con menos dinero): es requisito del *informe*, no del
  código. El experimento lo detecta y lo imprime.

---

## 4. Fallos encontrados

### 4.1 En el bot

1. **Velas diarias sin zona horaria.** yfinance devuelve las diarias con
   índice sin zona y las intradía con zona. `_normalize_df` no localiza nada,
   y mi vista as-of **rechaza** índices sin zona a propósito. Juntando las
   dos: alimentados con series diarias reales, M02 y M03 habrían devuelto
   NO_DATA para siempre, **en silencio**, con los logs mostrando evaluaciones
   y sin evaluar nada. No lo vi en local porque mis fixtures los construía yo
   con `tz="UTC"`: el fixture era más cómodo que la realidad.
2. **Zona horaria por alias.** El código usaba `US/Eastern`, un alias de
   compatibilidad del IANA. Muchas imágenes de contenedor traen la base de
   zonas recortada: nombres canónicos sí, alias no. Ahí el filtro de sesión
   falla cerrado y bloquea el **100%** de las operaciones diciendo "sesión
   indeterminada", no "falta un paquete". Ahora `zona_mercado.py` prueba
   `America/New_York` primero. Misma zona, mismas reglas; la prueba lo
   verifica comparando husos mes a mes durante tres años, así que no cambia
   ninguna decisión.
3. **M02 y M03 opinaban sobre señales SELL.** Un activo que cae da CASH, y
   aplicar ese CASH a un corto vetaría justo la operación que la tendencia
   favorece: el signo se invierte. Tu 15.5 lo advierte. Ahora devuelven
   UNSUPPORTED.
4. **La evidencia se perdía en silencio.** La función de registro se comía las
   excepciones y la tabla no existía si nadie llamaba al arranque. En un
   módulo cuyo único trabajo es dejar constancia, es el peor fallo posible.
5. Anteriores a esta sesión, ya corregidos: contabilidad de costes (reportaba
   +0,06 cuando lo real era −0,37), almacenamiento efímero en Render (el
   capital se reiniciaba a 1000 y faltaba la tabla desde junio), filtro de
   sesión bloqueando el 100% de las velas diarias (2222 señales → 0
   operaciones), corrupción silenciosa por NaN (`nan <= 0` es `False`),
   MIN_BARS 50 con una EMA200 que necesita 200, el backtester ignorando el
   cooldown de 6h (106 vs 25 operaciones), alertas fantasma en Telegram.

### 4.2 Míos, en esta sesión

- `periodo.shift(-1)` sobre un `PeriodIndex` **resta un mes** en vez de mover
  posiciones. Devolvía todas las filas: rebalanceo diario disfrazado de
  mensual, con 21 veces la rotación y sus costes. Lo pillé porque miré la
  salida en vez de dar por bueno que funcionaba.
- Escribí el token literal de salto de CI dentro de un mensaje de commit
  mientras **explicaba** ese mecanismo. GitHub no distingue entre usarlo y
  hablar de él: el commit subió, dije que estaba subido, y la validación nunca
  arrancó.
- Al fallar, el experimento sobrescribía el JSON entero con el traceback y se
  llevaba por delante el diagnóstico de carga que acababa de guardar. Me costó
  una corrida completa averiguar algo que ya había guardado.
- Un `except ... as e` borró la variable `e` que contenía el objeto de
  configuración (Python la elimina al salir del bloque).
- Un fixture de test con la forma exacta de una clave real de Google, escrito
  justo después de que se filtrara una de verdad. Está revocada, pero queda en
  el historial de git.
- **En una sesión anterior filtré la clave de Gemini de Brian a Telegram** al
  ampliar el truncado de errores de 80 a 200 caracteres. Él la revocó. De ahí
  viene `_censurar()`.

---

## 5. Lo que quiero hacer

En orden, y ninguna de estas decisiones está tomada:

1. **Registrar qué activos elige M03 cada mes.** Ahora no se guarda, así que
   no puedo comprobar la concentración. Si los cinco son ETF de tecnología
   correlacionados, no son cinco fuentes de retorno, son una. Tu 15.6 avisa de
   esto exactamente.
2. **Decidir qué hacer con el núcleo de Shark**, a la vista de que pierde en
   las cinco clases y de que una rotación mensual trivial lo bate por 16
   puntos al año en el mismo universo.
3. **Decidir si B1 pasa a precios ajustados.** El sesgo medido es de 1,5 a 2,1
   puntos al año. Pero cambiar el ajuste cambia **todas** las decisiones de
   B1, así que es una versión nueva de la estrategia y necesita su propia
   prueba, no un parche.
4. **Dejar de generar señales SELL**, o seguir generándolas y registrándolas
   sabiendo que no son ejecutables.
5. **M04**, si tiene sentido con una sola estrategia y exposición del 93%.

---

## 6. Las ocho preguntas

Aquí es donde pido guía. Son de método, no de código.

### P1 — Sesgo de supervivencia: ¿cómo acotarlo sin pagar?

Es el agujero más grande que queda. La lista de ETF es la de **hoy**; los que
cerraron no están. yfinance no da universos históricos. Infla también a
comprar y mantener, pero **M03 selecciona dentro del universo, así que se
beneficia más**: el sesgo favorece precisamente a la estrategia que quiero
validar.

¿Hay forma de **acotar** la magnitud sin un proveedor de pago? ¿Un universo
congelado a una fecha pasada a partir de una lista publicada entonces? ¿O la
honestidad obliga a decir que este resultado no es validable con los datos
que tenemos?

### P2 — Comparaciones múltiples: medí 18 veredictos y pasaron 2

Pre-registré los criterios y la partición train/test, pero **no** la tasa de
error por familia. Los dos que pasan son los universos más amplios con más
datos, y pasan con el mismo signo en las dos mitades, que es el patrón
contrario al del ruido. Pero 2 de 18 es exactamente lo que daría el azar con
un umbral laxo.

¿Cómo debería corregir esto? ¿Cuenta como un ensayo del presupuesto de la
sección 9 o como seis? ¿Y qué tendría que haber pre-registrado para que el
resultado fuera interpretable sin esta duda?

### P3 — El resultado de M03 es casi todo beta. ¿Vale algo el resto?

Exposición media **93,3%**. De ese +13,32% en renta variable, el +12,60% es
simplemente estar invertido. El algoritmo aporta **+0,72 puntos al año**, con
4,84 de rotación anual y 4,5 pb por intención.

Tu documento avisa de esto literalmente. Mi lectura es que el beneficio real
no es el retorno sino la caída (−16,0% contra −23,3%), y que +0,72 puntos no
sobrevive a costes reales de bróker ni a impuestos.

¿Estás de acuerdo? ¿Y cuál es la prueba correcta para separar la selección de
la beta — regresión contra el índice, cartera equiponderada del universo como
referencia, otra cosa?

### P4 — El núcleo de Shark: ¿se preserva o se retira?

Tu documento insiste en preservar B1 y en que "no operar es una salida
legítima del algoritmo, no un fallo que el LLM deba corregir inventando una
señal". Lo he respetado: la extensión no cambia ninguna decisión.

Pero los datos dicen que B1 pierde en las cinco clases, con el intervalo del
90% entero por debajo de cero en la clase con más muestra. Preservar una línea
base **medida como perdedora** parece distinto de preservar una línea base
desconocida.

¿Preservar B1 significa seguir ejecutándolo en papel, o solo conservarlo como
referencia de comparación mientras se deja de operar?

### P5 — Precios ajustados: ¿cómo migrar sin hacer trampa?

El sesgo está medido (1,5–2,1 pts/año) y perjudica a los largos. Corregirlo
haría que los largos de Shark se vean **mejor** y los cortos **peor**, o sea
reforzaría la conclusión de solo-largos. Justo por eso desconfío: un cambio
que mejora el número que quiero mejorar.

¿Lo correcto es tratarlo como una versión nueva de la estrategia con su propio
test fuera de muestra, consumiendo un ensayo? ¿O es una corrección de un fallo
de datos y no cuenta como hipótesis nueva?

### P6 — M01 sin estimador: ¿cuál es el mínimo legítimo?

El umbral económico está inerte porque no tengo estimación de ganancia bruta
esperada validada fuera de muestra, y tu documento prohíbe explícitamente
convertir un momentum o un RSI en expectativa.

¿Qué sería el estimador **mínimo** admisible? ¿La expectativa histórica medida
en el tramo de entrenamiento, aplicada al tramo de test? Eso sería fuera de
muestra en sentido estricto, pero con una sola cifra por clase y
probablemente inestable. ¿O hasta que no haya fills reales M01 debe quedarse
solo en diagnóstico?

### P7 — M04 con una sola estrategia: ¿aporta algo?

Hoy hay una estrategia, exposición 93% y límites de capital heredados de
`config.py`. La segunda variante de M04 (covarianza encogida, tope de
volatilidad) parece maquinaria sin nada que coordinar.

¿Merece la pena ahora, o solo cuando haya dos estrategias compitiendo por el
mismo efectivo — que es cuando I24 pasaría de "no cubierto" a necesario?

### P8 — Señales inejecutables: ¿generarlas o no?

Entre el 32% y el 59% de las señales son SELL y no se pueden ejecutar al
contado. Dos opciones:

- **Dejar de generarlas.** Más limpio y el papel se parecería a la realidad.
  Pero cambia B1, y perdería la serie de cortos que hoy sirve de control: los
  cortos pierden en las cinco clases y eso es información.
- **Seguir generándolas y marcarlas.** Preserva B1 y el control, pero el
  broker de papel sigue acumulando operaciones imposibles y cualquier cifra
  agregada mezcla lo ejecutable con lo que no.

Me inclino por la segunda con una marca explícita y métricas separadas, pero
no lo tengo claro.

---

## 7. Cómo verificar todo esto

Desde la raíz del repositorio, sin red salvo donde se indica:

```bash
# Las 18 pruebas de tu archivo de referencia, tal cual
python3 institucional/../tests/test_institucional.py

# Toda la batería (354 comprobaciones en CI)
for t in tests/test_*.py; do python3 "$t"; done

# La prueba que demuestra que observar no cambia nada
python3 tests/test_observacion.py

# El experimento (NECESITA RED: descarga 31 activos, 15 años)
python3 validator/experimento_institucional.py
```

Archivos de resultados, todos en el repositorio:

| Archivo | Contiene |
|---|---|
| `resultados/institucional.json` | El experimento nuevo, completo, con curvas |
| `resultados/clases.json` | Shark por clase de activo, con bootstrap |
| `resultados/ultimo.md` | La corrida de CI entera |
| `resultados/robustez_*.json` | Barridos SL/TP y análisis de robustez |
| `BASELINE_MANIFEST.json` | Qué es exactamente B1 |
| `CAPABILITIES.json` | Qué puede y no puede hacer esta cuenta, verificado |

---

## 8. Lo que NO está, y sería fácil creer que sí

Por si acaso, porque es lo que más daño hace:

- **No hay bróker.** Nada de esto ha ejecutado una orden real.
- **No hay fills reales**, así que el `implementation_shortfall` de tu archivo
  está implementado y probado con casos sintéticos pero **no mide nada
  todavía**. No hay bid/ask, solo OHLC.
- **El modelo de coste no está calibrado.** 8 pb por pata es un supuesto del
  backtester, no una tarifa verificada de ninguna cuenta. Y asumo que salir
  cuesta lo mismo que entrar, que tu documento advierte que no hay que
  asumir; queda declarado en el diagnóstico en vez de escondido.
- **No sé la concentración de M03.** Ver pregunta 1 de la sección 5.
- **Los resultados sintéticos no son resultados.** En una prueba de humo local
  pasé series con drifts que yo mismo elegí y "trece variantes pasaron los
  criterios". Eso no significa nada y no está en ninguna tabla de este
  documento.
- **Ninguna estrategia tiene presupuesto** y el modo sigue en OBSERVE. Que M03
  pase los criterios es evidencia, no una autorización.
