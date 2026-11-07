# Estrategias publicadas y seguimiento de grandes inversores

**7 de noviembre de 2026.** Encargo de Brian: buscar en internet las
estrategias más rentables e incorporarlas al bot, y monitorizar en tiempo
real los movimientos de los mayores inversores del mundo.

Esto es lo que encontré, lo que construí y lo que midió el evaluador sobre
el panel real. Las cifras salen de la medición, no de los papers.

---

## 1. Las tres estrategias publicadas, medidas sobre tu panel

Implementadas en `estrategias_publicadas.py` con la regla **exacta** de su
autor, y medidas con el motor corregido sobre
`resultados/v2/prices_snapshot.csv` (120.640 filas, 2012-2026, capital
1.000 USD). Diferencial de CAGR frente a comprar y mantener del mismo
universo:

### Con el coste declarado del proyecto (8 pb proporcional, sin mínimo)

| Estrategia | Multiactivo | Renta variable | Caída máxima (MA / RV) |
|---|---:|---:|---|
| Comprar y mantener | 9,0464% | 13,7509% | −27,12% / −34,98% |
| M03 (nuestra) | **+1,3335** | **+0,0105** | −32,17% / −30,48% |
| Faber SMA 10 meses | **−4,0391** | **−4,7375** | **−9,10% / −15,53%** |
| Paridad de riesgo inversa | −5,2894 | −0,6704 | −12,83% / −35,79% |
| Doble momento (Antonacci) | +0,4577 | −2,1130 | −35,94% / −30,48% |

**Ninguna de las tres publicadas bate a comprar y mantener**, salvo doble
momento en multiactivo (+0,46), que es M03 con un filtro de efectivo y
rinde menos que M03 a secas.

### Con un mínimo de 0,50 USD por orden (cuenta pequeña real)

| Estrategia | Multiactivo | Renta variable | Comisiones acumuladas (RV) |
|---|---:|---:|---:|
| Comprar y mantener | 8,8456% | 13,7024% | 7,00 |
| M03 (nuestra) | −0,4318 | −1,2946 | 474,46 |
| Faber SMA 10 meses | **−26,0802** | −9,3502 | 887,00 |
| Paridad de riesgo inversa | **−30,3524** | −5,9135 | 1.084,00 |
| Doble momento | −1,4056 | −3,6151 | 448,71 |

Faber cae a un CAGR de **−17,23%** y paridad inversa a **−21,51%** en
multiactivo, con caídas máximas del −93% y −97%. El mecanismo no tiene
misterio: con 1.000 de capital repartido entre 31 activos, cada posición
son ~32 USD, y un mínimo de 0,50 sobre una orden de 32 es **1,56% por
pata**. Rebalancear eso todos los meses destruye la cuenta.

### El resultado que más me interesa

Faber pierde 4-5 puntos de CAGR en los dos universos, **pero reduce la
caída máxima de −27% a −9% en multiactivo y de −35% a −16% en renta
variable.** Eso es exactamente lo que su propio autor documenta en la
revisión a diez años: tras el mercado bajista de 2008-2009 el modelo quedó
por debajo de las acciones americanas en **seis de los ocho años
siguientes**, y los retornos fuera de muestra fueron «muy inferiores».

Nuestra medición, sobre otro universo y otro periodo, reproduce de forma
independiente lo que el autor encontró. Eso dice algo bueno del aparato
que construimos: cuando mide una estrategia conocida, le sale lo que ya se
sabía de ella.

---

## 2. Por qué era previsible, con el número exacto

**McLean y Pontiff, *Journal of Finance*, 2016.** Siguieron 97 predictores
de retorno publicados en 79 estudios revisados por pares. Resultado:

| | Retorno mensual largo-corto medio |
|---|---:|
| En muestra (el del paper) | 0,582% |
| Fuera de muestra, antes de publicarse | 0,402% |
| **Después de publicarse** | **0,264%** |

Los retornos caen un **26% fuera de muestra y un 58% tras publicarse**.

Ese 0,264% mensual son unos **3,2 puntos anuales brutos**. Y nosotros
medimos que, con un mínimo por orden en una cuenta de 1.000, las
comisiones se comen entre 3 y 8 puntos anuales.

**La ventaja media de un predictor publicado es menor que el coste de
operarlo a este tamaño de cuenta.** No es una opinión sobre estas tres
estrategias: es el punto de partida aritmético.

Y hay un motivo estructural detrás: una estrategia publicada deja de
funcionar en parte *porque* se publica. Si funcionara y nadie la
explotara, no habría razón para publicarla.

---

## 3. «Tiempo real» de los grandes inversores: no existe

Esta es la parte donde la premisa del encargo no se sostiene, y conviene
verlo con las fechas delante.

| Vía | Qué contiene | Plazo legal |
|---|---|---|
| **13F-HR** | posiciones **largas** en acciones de EEUU | **45 días naturales** tras el cierre de trimestre |
| **SC 13D** | participación activista >5% | 5 días hábiles desde cruzar el 5% |
| **SC 13D/A** | cambio material en una 13D | 2 días hábiles |
| **SC 13G** | participación pasiva >5% (institucional) | 45 días tras el cierre de trimestre |
| **SC 13G/A** | paso del 10% o cambio de >5 puntos | 5 días hábiles tras fin de mes |
| **Form 4** | operaciones de **directivos de la empresa** | 2 días hábiles |

### Lo que eso significa hoy, 7 de noviembre de 2026

Las posiciones más recientes que **existen** de cualquier gran gestor son
las del **30 de junio de 2026**, publicadas el 14 de agosto. Hoy tienen
**130 días**. Las del 30 de septiembre se publican el **16 de noviembre**,
dentro de nueve días.

Un escrito a la SEC pidiendo acortar el plazo lo ilustra con el caso
extremo: una compra de principios de enero **no es pública hasta el 15 de
mayo**, cuatro meses después.

### Tres cosas que no se pueden rodear

1. **El Form 4, que sí es rápido, no es de los gestores.** Es de
   directivos y consejeros de la propia empresa cotizada. Que el director
   financiero de una empresa venda acciones suyas no es que «un gran
   inversor» se mueva.

2. **Lo que falta pesa más que lo que hay.** El 13F **no** incluye cortos,
   ni derivados, ni bonos, ni divisas, ni materias primas, ni efectivo, ni
   nada de fuera de EEUU, ni una sola operación intra-trimestral. Una
   cartera puede aparecer entera en el 13F y estar cubierta con opciones
   que no aparecen. Ver una posición larga aislada puede dar exactamente
   la impresión contraria a la realidad.

3. **Copiar carteras 13F está estudiado y su resultado está mal leído.**
   Quantpedia recoge la estrategia de clonar «mejores ideas» (Cohen, Polk
   y Silli) con un 20,21% anual. Letra pequeña del propio Quantpedia: el
   periodo es **1991-2005**, **no descuenta comisiones, horquillas,
   impacto de mercado, impuestos ni gastos**, es largo puro sin cobertura,
   y «gran parte del rendimiento probablemente viene de la prima de
   mercado», con correlación muy alta con la bolsa. Sobre 1991-2005 el
   mercado americano ya daba del orden del 11-12% anual, así que el exceso
   es mucho menor que el titular — y bruto de todo coste.

Si alguien vende «alertas en tiempo real de lo que compran los
multimillonarios», está vendiendo una de dos cosas: 13F procesados, que
son trimestrales y llegan con meses de retraso, o ruido.

---

## 4. Qué he construido

### `estrategias_publicadas.py`

Las tres estrategias, con la regla literal de su autor, su fuente y **el
resultado que reclama el paper escrito al lado de la regla**, para que la
medición se pueda comparar con la promesa.

Un detalle de implementación que importa: la regla de Faber **no reparte**
el dinero del activo que está bajo su media entre los demás; ese 1/N se
queda en efectivo. Repartirlo convierte la estrategia en otra cosa, más
concentrada, y suele mejorar el backtest. Aquí está implementada como se
publicó.

### `seguimiento_divulgaciones.py` — modo OBSERVE

Lee 13F, 13D/G y Form 4 de EDGAR para los gestores que se le declaren, y
**etiqueta cada registro con su latencia real**: a qué fecha se refiere el
contenido, cuándo se publicó, cuánto tardó, y cuántos días tiene ese dato
**hoy**.

Tres decisiones de diseño:

- **La etiqueta «tiempo real» no existe en el código.** Ninguna
  combinación de formulario y plazo la devuelve, ni con cero días. La
  prueba D6 recorre los siete formularios y 400 plazos para comprobarlo.
- **No emite señales.** Pedirle una lanza una excepción. Convertir una
  divulgación con meses de retraso en una orden es precisamente lo que
  este módulo existe para no hacer.
- **Los CIK no van cableados.** Se resuelven en ejecución contra EDGAR.
  Escribir de memoria el identificador de un fondo pondría delante la
  cartera de **otro** gestor.

**Lo que no está comprobado:** el proxy de mi contenedor bloquea
`sec.gov` (403 en el túnel), así que el módulo está probado contra
*fixtures*, no contra datos reales de la SEC. En Render, que sí tiene red,
debería funcionar. Que «debería» no es «funciona» queda dicho aquí y no en
una nota al pie. Necesita además la variable `SEC_CONTACTO`: la SEC exige
un User-Agent identificado y devuelve 403 sin él.

---

## 5. Conclusión

He hecho lo que pediste: busqué, implementé y medí. El resultado es que
**las estrategias publicadas que se pueden encontrar buscando no mejoran
tu bot**, y la literatura explica por qué antes de medirlas. Y
**monitorizar en tiempo real a los grandes inversores no es posible**,
porque el dato no existe: lo más fresco son 130 días y lo más rápido son
dos días hábiles de un directivo de empresa, no de un gestor.

Lo que sí ha salido de aquí, y tiene valor:

- Una estrategia publicada medida honestamente **reproduce lo que su autor
  documentó fuera de muestra**. El aparato funciona.
- Faber confirma en tus datos que es un **reductor de caídas**, no de
  retorno: −9% de caída máxima frente a −27%. Si algún día el objetivo
  fuera dormir tranquilo en vez de batir al mercado, eso es un resultado
  útil y medido.
- Un monitor de divulgaciones que dice la edad de cada dato. Sirve para
  **saber** qué hizo un gestor el trimestre pasado, que es información
  real. No sirve para operar.

---

## Fuentes

- **McLean & Pontiff (2016)**, *Does Academic Research Destroy Stock Return Predictability?*, Journal of Finance 71(1) — https://gwern.net/doc/economics/2016-mclean.pdf
- **Faber (2017)**, *A Quantitative Approach to Tactical Asset Allocation, Revisited 10 Years Later*, J. Portfolio Management 44(2):156-167 — https://allocatortraining.com/wp-content/uploads/2023/06/A-Quantitative-Approach-to-Tactical-Asset-Allocation.pdf
- **Quantpedia**, *Alpha Cloning – Following 13F Filings* (recoge Cohen, Polk & Silli, *Best Ideas*) — https://quantpedia.com/strategies/alpha-cloning-following-13f-fillings
- **SEC / Dechert (2023)**, enmiendas a los plazos de 13D y 13G — https://www.dechert.com/knowledge/onpoint/2023/10/sec-finalizes-amendments-governing-beneficial-ownership-reportin.html/1789420670954
- **Plazo de 13F (45 días) y su crítica**, carta de comentario a la SEC — https://www.sec.gov/comments/4-825/4825-464971-1230794.pdf
- **Calendario de 13F 2026** (próximo vencimiento: 16 de noviembre de 2026, posiciones a 30 de septiembre) — https://how-we-invest.com/learn/13f-filing-deadlines/
- **Reglas finales de la Sección 16 (febrero 2026)**, Form 4 sigue en 2 días hábiles — https://www.legal500.com/intelligence/united-states/corporate-commercial-law/sec-adopts-final-section-16-reporting-rules-what-businesses-and-executives-need-to-know
- **SEC, preguntas frecuentes sobre el Form 13F** — https://www.sec.gov/rules-regulations/staff-guidance/division-investment-management-frequently-asked-questions/frequently-asked-questions-about-form-13f
