# Respuesta a la segunda auditoría (2026-10-20)

**Estado:** las 24 puertas de `PLAN_CLAUDE.md` pasan, desplegadas en 41
comprobaciones. 499 comprobaciones propias en verde, 0 fallos. De vuestros
15 oráculos cumplen **13**; los dos que quedan están explicados abajo con
medidas, no con excusas.

Orden de trabajo: el vuestro, sin saltarme nada. Cinco cambios, cada uno
en su commit, citando qué contrato repara y con el caso que fallaba antes
medido **antes** de tocar el código.

---

## 1. Lo primero: cuatro afirmaciones mías que eran falsas

Antes del trabajo, porque son cosas que dije con seguridad.

**«M03 estaba casi siempre con sus cinco posiciones dentro del mismo
grupo.»** Falso. El grupo mayor tuvo 5 posiciones en **40 de 168**
decisiones; 4 en 54, 3 en 60, 2 en 13, 1 en 1. Las cinco coinciden de
grupo el **23,81%** de las veces. Las 155 que yo cité eran los recortes, y
con cinco posiciones iguales un grupo pasa del 40% con solo **tres**
dentro. Salté del recorte al mecanismo teniendo el CSV delante.

**«Con 8 pb M01 no tiene nada que filtrar.»** Falso, y vuestro O08 lo
demuestra: mismo modelo, precio 100, 10 unidades, ida y vuelta 1,60; con
stop a 0,5 el margen es −1,10 y rechaza, con stop a 4 es +2,40 y acepta.
Mi prueba mantuvo la distancia fija en 2,0 y solo movió el tamaño. El
tamaño **sí** se cancela con costes proporcionales. La distancia no. Probé
la única variable que no discrimina y concluí que no había decisión.

**El signo del sesgo de supervivencia.** Dije que los escenarios mostraban
que el sesgo favorecía a comprar y mantener y que corregirlo subiría a
M03. Los seis escenarios siguen dando de +0,07 a +2,07 puntos, pero **no
identifican el signo real**: son escenarios que yo declaré, no una cota
del sesgo verdadero. Retiro la dirección. Las salidas se conservan con la
interpretación corregida, como pedís.

**«Por debajo de un 3-4% anual no se distingue de la suerte.»** No es una
ley universal y la retiro como tal. Son 40 simulaciones por efecto: el 12%
es 5/40 (intervalo de Wilson 5,5–26,1%) y el 60% es 24/40 (44,6–73,7%).
Los falsos positivos, 15/200 = 7,5% (4,6–12,0%), compatibles con el 5%
nominal. Y la curva **no** incluye la corrección de Holm, así que
sobreestima la potencia del procedimiento que de verdad se aplica. La idea
de fondo aguanta; la cifra con dos decimales no.

Y una quinta, de aritmética: `rotacion_anual_nominal` dividía todo el
nominal negociado por el capital **inicial**. Los 14,477 publicados son
5,297 sobre patrimonio medio. Ahora las dos columnas existen con nombres
que dicen lo que son, porque no son comparables.

---

## 2. Cambio 1 — contabilidad, NAV de cierre y retornos

Medido antes de tocar nada:

| Caso | Daba | Contrato |
|---|---|---|
| Vender 5 de 10 a 100, liquidación a 2 días | NAV **500** | 1.000 |
| Cobrar un dividendo de 20 ya devengado | NAV **1.020** | 1.000 |
| Comprar 10 a 100, cierre del mismo día a 110 | NAV **1.000,0** | 1.100,0 |
| 100 el 31-dic, 110 la primera sesión de enero | **0%** anual | +10% |

Los dos primeros eran el mismo defecto: `_pendiente_liquidar` era una
lista de `(cuándo, importe)` que no sabía si su importe estaba contado en
`derechos`. La venta no lo contaba y el dinero desaparecía del NAV entre
la venta y el cobro; el dividendo lo contaba y nunca lo daba de baja, así
que el NAV lo ganaba dos veces. Ahora todo importe diferido es un
`Derecho` tipado con `event_id` y las once columnas que pedís, `derechos`
es su **suma calculada** —no un escalar paralelo que mantener a mano— y
liquidar mueve exactamente un derecho a caja marcándolo `LIQUIDADO`, así
que es idempotente.

El NAV de cierre: el bucle valoraba **antes** de los fills y el propio
fill reescribía `precio_valoracion` con su precio de ejecución. Reordenado
a vuestra secuencia: acciones corporativas, liquidación, ejecución con la
vista observable *ahora* (la apertura de hoy y marcas anteriores, nunca el
cierre de la sesión en curso), marca de cierre de **todas** las
posiciones, decisión, y guardar caja, derechos, obligaciones, reservas,
cantidades y NAV.

`por_ano_natural` encadena ahora con el último NAV anterior al año, los
años parciales se informan marcados en vez de borrarse, y
`identidad_de_factores` comprueba **dentro de la librería** que el
producto de factores reproduce `NAV_final/NAV_inicial`.

Y las capacidades que no existen se rechazan: instrumento en otra moneda
antes de tocar el libro, sin asumir paridad 1:1; `politica_terminal` era
un campo que nadie leía, y ahora `LIQUIDAR` está implementada y cobra la
salida, `MARCAR` declara su supuesto optimista y cualquier otra da
`ConfiguracionInvalida`.

**Oráculos:** O01, O02, O03, O04, O05 y O07 pasan de `false` a `true`.

---

## 3. Cambio 2 — admisión de órdenes y ejecutor del core

**O14, medido antes:** objetivo del 40% fijado con un cierre de 100, la
sesión siguiente abre a 200, y las cuatro unidades compradas son el
**80%** del patrimonio, informado como tope duro del 40%. El tope solo
tocaba el objetivo mensual y nadie lo recomprobaba al ejecutar.

Las tres cosas quedan nombradas por separado, como pedís: **objetivo
mensual**, **límite de admisión** (recomprobado con el precio ejecutable,
por instrumento, grupo, exposición total y número de posiciones, siempre
redondeando hacia abajo) y **límite continuo**, que NO está implementado y
no se declara como si lo estuviera: exigiría rebalanceo diario, que es
otra estrategia con su identificador, sus costes y su experimento.

Declarado y no escondido: redimensionar con la apertura supone que la
orden se envía **después** de observar ese precio, así que rellenarla
exactamente a la apertura es un supuesto optimista, no un hecho.

**O06, medido antes:** capital 100, se piden 2 unidades a 100 con la
reducción desactivada, y compraba 1. La bandera se honraba solo cuando no
cabía *nada*. Y las reservas: `reservar` movía un escalar anónimo, así que
liberar el importe de una orden podía liberar el de otra y reintentar la
misma reservaba dos veces. Ahora van por `order_id`, atómicas, con
liberación individual e idempotente.

**El ejecutor del core.** Esto era lo más serio y no estaba en vuestra
lista de oráculos: el capital del paper trading crecía con el PnL
**bruto**. `pnl = (salida − entrada) × size`, y `capital += pnl`. No había
ninguna constante de coste en el core: los 0,0008 por pata vivían en seis
copias repartidas por el backtester y los validadores y ninguna llegaba a
la ruta viva, así que cambiar la tarifa no cambiaba nada en el bot. Ahora
`contabilizar_cierre` cobra las dos patas y devuelve el desglose, y
`live_engine` llama al dimensionado declarando efectivo y coste: el
parámetro existía desde vuestra primera auditoría y nadie lo llamaba, así
que con capital 1.000, precio 100 y ATR 0,10 el bot abría nominal 2.500.

Lo que **no** cambia a propósito: `capital` sigue siendo el configurado
como base de riesgo de B1. Moverla sería cambiar la estrategia, y vuestro
plan dice «no cambies señales al reparar contabilidad». El efectivo de la
cuenta es una restricción contable y va por su propio parámetro.

`capacidades_core.py` declara las seis capacidades con la parte incómoda
dicha: **ninguna está verificada contra un broker**. No hay conexión, ni
credenciales, ni una orden real enviada. Moneda y cortos están
BLOQUEADAS: si el supuesto falla, para la máquina. Lotes, comisiones,
liquidación y calendario son SUPUESTAS: si están mal, producen un
resultado creíble, que es peor.

---

## 4. Cambio 3 — snapshots, eventos y calidad

**O11:** `construir` tomaba `min(ultimas)` y, si ese cierre aún no estaba
disponible, lanzaba `SnapshotInvalido` y tiraba el snapshot **entero**:
con 299 velas cerradas y una abierta se quedaba sin ninguna. Ahora recorta
a la última observación disponible. Dos cosas más: la observación sale de
la **intersección real** de calendarios, no de `min(ultimas)` —que con
huecos distintos puede ser una fecha que alguna serie no tiene—, y la
referencia de **efectivo** no se recortaba *nunca*, porque se sacaba del
diccionario antes de calcular la observación: conservaba velas posteriores
a las de los activos y la señal miraba el futuro por ese lado.

**O12:** `cargar_ultimo` filtraba por `available_at_max` a secas, así que
un snapshot descargado el 16 de marzo se devolvía para una decisión del 26
de febrero. Los datos eran anteriores, sí, pero la **revisión** de esos
datos no se conocía entonces. Ahora se exigen las tres fechas, y
`permitir_replay_revisado=True` lo devuelve marcado como lo que es.

**O15:** la condición era `if ... and _INST_SERIES_TR is None`, con un
comentario encima diciendo «solo descarga si el snapshot ha caducado». El
comentario era falso: solo descargaba si la caché estaba **vacía**. El bot
arrastraba el snapshot caducado hasta que alguien reiniciara el proceso, y
M02/M03 seguían opinando con un ranking viejo sin decirlo.

**Un error mío dentro de este cambio, que conviene que leáis.** Mi primera
versión del filtro estricto comparaba la columna `creado_en` —que es TEXT
ISO— con un entero. En SQLite eso no da error: da **siempre falso**,
porque un INTEGER ordena antes que un TEXT. Mi «filtro estricto» no era
estricto: rechazaba todos los snapshots. En producción M02 y M03 habrían
vuelto a `NO_DATA` permanente sin un solo aviso, que es exactamente el
fallo que ya cometí con las zonas horarias. Y mi propia puerta lo daba por
bueno, porque esperaba `None` y recibía `None`. Lo cazó F6 de las pruebas
de aceptación —una de las dos que escribí con `or True` y luego arreglé—.
Añadí la puerta que faltaba: **la ruta estricta tiene que devolver una
captura anterior al corte**. Un filtro que rechaza todo no es estricto,
está roto, y sin esa comprobación no se distingue.

**Eventos.** `liquidar_instrumento` exige las cuatro cosas que pedís:
importe por unidad, fecha del evento, fecha de cobro y política de
reinversión. Y `EventoCorporativo` exige **fuente**: un hecho sin
procedencia no es evidencia. Una posición viva sin precio admisible y sin
evento declarado ya no produce un número limpio: el día se marca
`NO_EVALUABLE`, el resultado lleva `dias_no_evaluables` y `nav_fiable`, y
con `politica_baja=EXIGIR_EVENTO` el motor se niega a emitir NAV.

---

## 5. Cambio 4 — M01

**O09, medido:** `v[i:i + bloque]` y numpy trunca al final del array, así
que un bloque que empieza en 7 con bloque 5 devolvía `[7,8,9]` en vez de
envolver a `[7,8,9,0,1]`. Sobre `0..9`, media verdadera 4,50:

| | media remuestreada |
|---|---|
| antes | **5,6214** |
| ahora | **4,5100** |

Una cota **inferior** calculada sobre medias sesgadas al alza es una cota
que no acota. Ahora son bloques circulares de longitud fija, vuestro
pseudocódigo literal, con exactamente *n* valores por réplica. Expongo
`medias_remuestreadas` a propósito: el sesgo no se veía desde fuera porque
la función solo devolvía un percentil.

Y queda escrito el aviso que pedís: este algoritmo **no** garantiza
cobertura válida en cualquier régimen, y aquí no está medida para el
proceso real de las operaciones de Shark.

**O10, medido:** con dos cortes y 25 operaciones futuras, el primer tramo
veía las 25 y el segundo 15 — 40 evaluaciones sobre 25 operaciones.
Promediar prefijos del mismo futuro como pruebas independientes. Ahora
cada operación cae en una ventana `[corte_i, corte_i+1)` por su fecha de
apertura, se sigue hasta madurar aunque cierre fuera, el último tramo
acaba en un corte final explícito y lo que no ha madurado se cuenta como
etiqueta pendiente. Asignación 10+15, 25 únicas.

Y las magnitudes: `error_del_pronostico` restaba `media(R_NETO)` menos
`mu_R`, que es media de R **bruto**. Con un pronóstico bruto perfecto y un
coste de 0,2 R el error salía −0,2 R y parecía del modelo. Ahora bruto
contra bruto, neto contra neto, y el coste en su propia columna.

**Pendiente declarado:** medir si M01 **ayuda** exige aplicar sus
decisiones y reejecutar la cartera con la secuencia y el capital reales.
No está hecho. M01 no se activa automáticamente en ningún modo.

---

## 6. Cambio 5 — inferencia, presentación y reproducibilidad

- El registro ya no se sobrescribe: modo `x`, atómico, uno por corrida en
  `resultados/v3/registros/`. Y dice lo que **no** demuestra: la fecha. El
  archivo es local y lo escribió quien lo va a usar, así que un hash
  propio no prueba que se escribiera antes de ver los resultados. Lo más
  cercano es el commit, cuya fecha de recepción registra GitHub, que no es
  parte de este repositorio.
- La etiqueta **EXPLORATORIO** se conserva y el generador de tablas la
  imprime con un aviso: renombrar un tramo ya mirado no lo convierte en
  datos nuevos.
- Concentración desde los **pesos reales por fecha** y por grupo, en la
  trayectoria diaria. Y la exposición media ya se calcula recorriéndola,
  no reconstruyéndola del último día. El docstring de `concentracion`
  afirmaba que cinco ETF solapados podían dar posiciones efectivas
  cercanas a uno: es falso, el inverso de Herfindahl solo ve los pesos y
  cinco equiponderadas dan exactamente 5,0 por mucho que solapen.
- Rotación con su convención dicha: nominal de ambas patas, entrada
  inicial incluida, sobre patrimonio medio. Las dos columnas conviven
  porque la vieja se publicó y no son comparables.
- `evaluador/informe_tablas.py` genera las tablas **desde** el resultado.
  Escribí «13,77%» donde el archivo decía 13,7614% y «pasan 2 dictámenes»
  enumerando cuatro: las dos veces el número salió de mi memoria. Ahora
  sale del archivo.
- V24: reejecutar da NAV idéntico al bit, mismas decisiones, mismos fills,
  mismo libro y mismas métricas. Con una comprobación extra de que la
  corrida comparada **sí** opera, porque dos corridas vacías coinciden
  trivialmente.

---

## 7. `resultados/v2/` se sobrescribió siete veces

Lo descubrí al generar las tablas: el informe de la carpeta declaraba un
commit de hoy. El paso de CI corría `evaluador/experimento.py`, cuya
salida por defecto era `resultados/v2`, y commiteaba los resultados. Cada
push regeneraba la entrega que vuestro plan dice no sobrescribir.

Nada se perdió —estaba en el historial— y la carpeta está restaurada al
estado de `037d373`, el último del 19 de octubre y por tanto el que viajó
en el paquete auditado. El detalle de las siete corridas está en
`resultados/v2/LEEME_SOBRESCRITURAS.md`. La salida por defecto es ahora
`resultados/v3`, y hay un guardarraíl que se niega a escribir sobre una
entrega cerrada, porque confiar en que me acuerde es justo lo que falló.

## 8. Qué movieron los arreglos en las cifras: casi nada, y por qué

Comparando `037d373` (motor anterior) con `8d3f712` (tras los cambios 1 a
3a), renta variable / M03:

| Cifra | Antes | Después |
|---|---|---|
| CAGR M03 | 13,7614% | 13,7614% |
| CAGR comprar y mantener | 13,7509% | 13,7509% |
| Caída máxima diaria | −30,4812% | −30,4812% |
| Intenciones rechazadas | 10 de 967 | 9 de 967 |
| Comisiones | 162,027295 | 162,027362 |
| p-valor RV/M03 | 0,534093 | 0,533893 |

Los cambios entran —aparecen los campos nuevos, bajan las rechazadas, se
mueve el p-valor— pero el titular no se mueve, y el motivo es concreto:

- La venta diferida solo muerde con `dias_liquidacion > 0` y el
  experimento corre con 0.
- El dividendo doble solo muerde si se pasan dividendos como eventos, y el
  experimento usa series de retorno total.
- El NAV de los días con fill afecta a días intermedios; el CAGR sale de
  los extremos y la caída máxima no cayó en un día de operación.

Tres contratos económicos roto, arreglados, con casos que fallaban antes,
cuyo efecto agregado sobre **estas** cifras está en el cuarto decimal. Las
dos cosas son verdad a la vez. Lo que no se puede decir es que los
arreglos «mejoraron el resultado».

---

## 9. Los dos oráculos que siguen en rojo

**O09.** Su criterio ejecutable es `all(n==10 for n,_ in samples)`, y
`samples` es vuestra propia reconstrucción del algoritmo roto, escrita a
mano con `np.arange(10)[a:a+5]`. No llama a mi función para medir
longitudes, así que es falso por construcción y ningún cambio mío lo
mueve. Lo único que lee mi código es `media_bootstrap_funcion`, y ahí está
la prueba: **5,6214 → 4,5100**. Vuestro `media_bootstrap_exacta` sigue en
5,6239 porque es vuestra reconstrucción, no mi función.

**O13.** Su criterio exige `cantidad('MUERTO') == 0`. Su propia nota dice
«si solo falta una cotización no se debe inventar la liquidación». Y el
plan: «no inventes pérdida total ni venta al último cierre». Retirar las
unidades sin cobro **es** una pérdida total, así que el criterio y la
prosa piden cosas distintas sobre un fixture que no declara ningún evento.
Medido sobre vuestro fixture exacto:

| | unidades | NAV final | `nav_fiable` |
|---|---|---|---|
| A — sin evento, MARCAR_INCERTIDUMBRE | 4,8387 | 865,5451 | **false** (55 días no evaluables) |
| B — sin evento, EXIGIR_EVENTO | — | no emite NAV | — |
| C — evento declarado, 50 por unidad | 0 | 865,5451 | true |
| D — evento declarado, cobro cero | 0 | **623,6096** | true |

A y C dan **el mismo NAV** con estatus opuesto: en A es una marca rancia
que nadie confirmó, en C un cobro declarado. C contra D difieren en
**241,94**, que es la distancia entre «repartió 50 por unidad» y «no
repartió nada». El motor no puede elegir entre C y D mirando la serie;
solo el evento puede. Poner O13 en verde sin evento obliga a elegir D por
decreto, y eso es la pérdida total inventada que el plan prohíbe.

Si el criterio ejecutable manda sobre la prosa, decidlo y lo cambio: es
una línea de política, no obra.

---

## 10. Lo que sigue sin estar

- **`resultados/v3` no está generado.** El experimento necesita red para
  descargar 31 activos y 15 años, y este entorno no la tiene (ni pip
  resuelve DNS). Lo genera CI en el próximo push, con su registro por
  corrida y las tablas desde el resultado.
- La lista real de ETF desaparecidos. Sin ella la supervivencia está
  acotada por escenarios declarados, y **no** es una estimación del sesgo.
- Si M01 ayuda: exige la secuencia real de operaciones de Shark.
- El límite continuo de M04, y el optimizador estadístico.
- M05 y M06 siguen bloqueados por capacidades y datos, rechazados por
  código.
- Potencia. No se arregla con trabajo: hace falta un efecto grande o
  muchos más años.
- Ninguna capacidad del ejecutor está verificada contra un broker real.

Nada de esto autoriza capital. El modo sigue en OBSERVE y ninguna
estrategia tiene presupuesto.
