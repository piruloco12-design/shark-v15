# AVISO: los resultados económicos de esta carpeta NO son válidos

**Fecha del aviso:** 2026-10-19
**Motivo:** auditoría externa (`SHARK_Auditoria_para_Claude_2026-10-19.md`), con
hallazgos reproducidos y confirmados por mí mismo.

---

## Qué queda invalidado

**`institucional.json` y `experimento_institucional.txt`: todas sus cifras
económicas.** Incluye las que presenté como resultado principal:

- «M03 momentum 12−1 da +13,32% anual frente a +12,60% de comprar y mantener»
- «+9,92% frente a +6,29% en multiactivo»
- «pasa los criterios registrados en las dos mitades de la muestra»
- los Sharpe, las caídas máximas, la exposición y el coste por intención
- la diferencia de 1,49–2,11 puntos entre series ajustadas y sin ajustar

No es que el número esté algo desviado. **El comparador no comparaba lo que
decía comparar.**

## Por qué (comprobado, no aceptado de palabra)

### El «comprar y mantener» no era comprar y mantener

`simular()` guardaba los pesos objetivo y no los dejaba derivar con los
precios. Cada mes comparaba los objetivos nuevos con los objetivos
anteriores, no con la cartera que de verdad se tendría.

Reproducción, verificada:

```
A: 100 -> 200 -> 100   B: 100 plano
Comprar ambos a partes iguales y mantenerlos  ->  1,0000
Lo que devolvía el motor                      ->  1,1250
Con 8 pb por pata                             ->  1,1241, y solo 2 intenciones
```

1,1250 es el resultado de **rebalancear al 50/50 cada mes**, que es otra
estrategia, y además la cobraba casi gratis: solo registraba las dos compras
iniciales. El fallo afecta a los dos lados de la comparación, así que **no se
sabe en qué dirección se mueve el diferencial** hasta recalcularlo.

### El CAGR cuenta un rendimiento cuyo tiempo no cuenta

La curva empieza *después* de aplicar el primer retorno, pero el primer
retorno ya está dentro del patrimonio. Verificado: 3,0572% contra 2,9813% en
un ejemplo de un solo movimiento.

### El «Sharpe» no es un Sharpe

Calculaba CAGR dividido por volatilidad anualizada. Un Sharpe es media de
retornos **diferenciales** frente a una referencia, dividida por su
desviación. Ni resta la referencia ni usa la media.

### El cierre mensual podía caer a mitad de mes

`cierres_mensuales` toma la última fila de cada mes. Si la serie termina el 13
de febrero, elige el 13 de febrero como «cierre mensual». Verificado.

### La caja libre cobraba el rendimiento de BIL

El dinero no invertido recibía el interés de un ETF de letras, cuando la
cuenta real no está remunerada.

## Lo que NO queda invalidado por esto

- Las **238 pruebas de regresión anteriores** y las **114 nuevas** siguen
  pasando. Son pruebas de contabilidad y contratos, no resultados de
  inversión.
- Que **OFF y OBSERVE producen las mismas decisiones** en el escenario
  probado. La auditoría lo confirmó de forma independiente.
- Los **fallos encontrados** siguen siendo fallos reales: almacenamiento
  efímero, filtro de sesión, NaN, cooldown, zona horaria, velas diarias sin
  zona.

## Lo que queda en duda, no refutado

`clases.json` (el histórico de Shark por clase de activo) **no fue el objeto
principal de la auditoría**, pero comparte código de evaluación con lo
anterior y arrastra al menos tres defectos confirmados:

- el tamaño por ATR abre nominal 2.500 con capital 1.000 (verificado), lo que
  no es ejecutable en una cuenta al contado
- los stops se ejecutan al nivel exacto incluso cuando la barra siguiente
  abre por debajo: verificado, sale a 99 cuando el máximo de la barra fue 95
- la «expectativa R» es en realidad la media del P&L en unidades monetarias
  del simulador, no un múltiplo de riesgo

Así que sus cifras tampoco deben citarse como medición económica firme.

## Dos correcciones a lo que dije

1. **Pasan 4 dictámenes, no 2.** En `PARA_ASTRA.md` escribí «pasan 2» y acto
   seguido enumeré cuatro. Son M03 y M02+M03, en multiactivo y en renta
   variable.
2. **«Pierde en las cinco clases» es falso.** Pierde dinero en cuatro. En
   cripto gana +1,47% anual, muy por debajo de su referencia (+58,08%), pero
   no pierde. No batir una referencia no es lo mismo que perder dinero.

---

**Nada de esta carpeta debe usarse para decidir sobre dinero.** Se conserva
como artefacto de lo que produjo aquel código, que es exactamente para lo que
sirve ahora.

---

# ACTUALIZACIÓN: la medición corregida, 2026-10-19

Ya está. El motor corregido (`evaluador/`, sobre `libro.py`) ha medido lo
mismo con datos reales: 31 activos, 2011-10 a 2026-10, 168 decisiones
mensuales, artefactos completos en `resultados/v2/`.

## Lo que decía con el motor roto, y lo que sale con el corregido

| | Motor roto | Motor corregido |
|---|---|---|
| Renta variable: M03 vs comprar y mantener | **+0,72 pts/año** | **+0,01 pts/año** |
| Multiactivo: M03 vs comprar y mantener | **+3,63 pts/año** | **+1,33 pts/año** |

En renta variable la ventaja era **una centésima de punto porcentual**. Es
decir: ninguna. Lo que yo presenté como el hallazgo del día era, casi en su
totalidad, el benchmark mal calculado.

Dije que el fallo afectaba a los dos lados de la comparación y que por eso
no sabía en qué dirección se movería el diferencial. Se movió en contra, y
mucho. Hice bien en no adivinar.

## Las cifras completas

| Estrategia | CAGR | Sharpe | Peor caída diaria | Rotación/año |
|---|---|---|---|---|
| **Renta variable** | | | | |
| Comprar y mantener | 13,76% | 0,86 | −35,0% | 0,07 |
| M03 momentum 12−1 | 13,77% | 0,85 | **−30,5%** | 14,47 |
| M02 tendencia | 12,80% | 0,84 | −32,3% | 10,42 |
| Rebalanceo equiponderado | 13,43% | 0,86 | −36,5% | 0,81 |
| **Multiactivo (31 activos)** | | | | |
| Comprar y mantener | 9,05% | 0,77 | −27,1% | 0,07 |
| M03 momentum 12−1 | 10,39% | 0,65 | −32,2% | 12,53 |
| M02 tendencia | 6,51% | 0,65 | −25,0% | 6,19 |
| Rebalanceo equiponderado | 6,67% | 0,73 | −23,8% | 0,63 |

Contrastes, con bootstrap estacionario y corrección de Holm sobre la familia
de 4 hipótesis registrada de antemano:

| Hipótesis | Diferencial mensual | IC 90% | p | Holm |
|---|---|---|---|---|
| multiactivo/M03 | +0,164% | [−0,306%, +0,670%] | 0,280 | no rechaza |
| renta_variable/M03 | −0,008% | [−0,153%, +0,137%] | 0,533 | no rechaza |
| multiactivo/M02 | −0,208% | [−0,467%, +0,041%] | 0,916 | no rechaza |
| renta_variable/M02 | −0,079% | [−0,179%, +0,016%] | 0,920 | no rechaza |

**Ninguna rechaza la nula.** Los cuatro intervalos del 90% contienen el cero.

## Qué significa y qué no

**No significa** que M03 no sirva. La potencia de este montaje está medida:
detecta un diferencial de +0,72% anual el 12% de las veces, y de +3,66% el
60%. Por debajo de un 3-4% anual no distingue una ventaja real de la suerte.
Un «no rechaza» aquí es «indetectable con esta muestra».

**Sí significa** que, medido bien, **M03 sobre renta variable no se separa
de comprar y mantener**: +0,01 puntos con 14,47 de rotación anual y 162 de
comisiones frente a 0,80. Paga mucho trabajo y mucha comisión para acabar en
el mismo sitio.

Lo único que M03 parece ofrecer es la caída: −30,5% frente a −35,0% en renta
variable. Ojo, que esas son caídas DIARIAS: las cifras bonitas que di antes
(−16,0% contra −23,3%) eran de puntos mensuales y subestimaban las dos.

Y una observación que no estaba en ninguna tabla anterior: el **rebalanceo
equiponderado** —la estrategia que el motor roto medía creyendo medir
comprar y mantener— rinde **peor** que comprar y mantener en los dos
universos. El motor viejo no solo comparaba contra la cosa equivocada: la
comparaba contra una cosa que además es peor.

## Estado

`EXPLORATORIO`, universo `EXPLORATORY_SURVIVOR_UNIVERSE`. Los datos son los
mismos que ya había mirado antes de la auditoría, así que un tramo ya
observado no recupera su condición de prueba final por volver a correrlo con
mejor código.
