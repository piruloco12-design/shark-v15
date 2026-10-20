# Aviso: CI sobrescribio esta carpeta siete veces

El plan de la segunda auditoria dice, textual:

> No sobrescribas `resultados/v2/` ni su registro.

Y se sobrescribio. No a mano: el paso de CI corria
`python evaluador/experimento.py`, cuya salida por defecto era
`resultados/v2`, y despues commiteaba los resultados al repositorio. Cada
push regeneraba la carpeta. Lo descubri al generar las tablas y ver que el
informe de la carpeta declaraba el commit `ffa71f1`, que es del cambio 3b
de hoy, y no el de la entrega.

Arreglado en el cambio 5: la salida por defecto es ahora `resultados/v3`,
el registro se escribe con el modo `x` (falla si el archivo existe, de
forma atomica) y cada corrida tiene su propio registro en
`resultados/v3/registros/`.

## Lo que habia en cada corrida

Nada se perdio: estaba en el historial de git. Renta variable, CAGR de
M03 frente a comprar y mantener; multiactivo igual.

| commit | fecha UTC | RV M03 | RV CyM | dif. | MA M03 | MA CyM | dif. |
|---|---|---|---|---|---|---|---|
| `c5cb671` | 2026-10-19 19:47 | 13,7707% | 13,7579% | +0,0128 | 10,3865% | 9,0531% | +1,3334 |
| `31917d3` | 2026-10-19 20:49 | 13,7614% | 13,7509% | +0,0105 | 10,3799% | 9,0464% | +1,3335 |
| `6f33b82` | 2026-10-19 21:01 | 13,7614% | 13,7509% | +0,0105 | 10,3799% | 9,0464% | +1,3335 |
| `66a7dfb` | 2026-10-19 21:17 | 13,7614% | 13,7509% | +0,0105 | 10,3799% | 9,0464% | +1,3335 |
| `037d373` | 2026-10-19 21:27 | 13,7614% | 13,7509% | +0,0105 | 10,3799% | 9,0464% | +1,3335 |
| `2fecbfc` | 2026-10-20 07:33 | 13,7614% | 13,7509% | +0,0105 | 10,3799% | 9,0464% | +1,3335 |
| `8d3f712` | 2026-10-20 07:52 | 13,7614% | 13,7509% | +0,0105 | 10,3799% | 9,0464% | +1,3335 |

Esta carpeta se ha restaurado al estado de **`037d373`**, que es el ultimo
del 19 de octubre y por tanto el que viajo en el paquete que se audito.

## Lo que cambiaron los cambios 1 a 3a, medido

Comparando `037d373` (motor anterior) con `8d3f712` (tras los cambios 1,
2a, 2b y 3a), ambos sobre renta variable / M03:

| Cifra | Antes | Despues |
|---|---|---|
| CAGR M03 | 13,7614% | 13,7614% |
| CAGR comprar y mantener | 13,7509% | 13,7509% |
| Caida maxima diaria | −30,4812% | −30,4812% |
| Intenciones rechazadas | 10 de 967 | 9 de 967 |
| Comisiones | 162,027295 | 162,027362 |
| p-valor RV/M03 | 0,534093 | 0,533893 |
| `nav_fiable` | no existia | `true` |
| `dias_no_evaluables` | no existia | 0 |

Los cambios SI entran: aparecen los campos nuevos, las rechazadas bajan y
el p-valor se mueve. Lo que no se mueve es el titular, y conviene decir
por que en vez de dejarlo como un misterio:

- La **venta diferida** solo muerde con `dias_liquidacion > 0`, y el
  experimento corre con 0. El fallo era real y el contrato estaba roto,
  pero esta configuracion no lo pisaba.
- El **dividendo cobrado dos veces** solo muerde si se pasan dividendos
  como eventos. El experimento usa series de retorno total, asi que nunca
  llamaba a esa funcion.
- El **NAV de los dias con fill** (A01) afecta a dias intermedios. El CAGR
  sale de los extremos, asi que no se entera salvo que el ultimo dia sea
  un dia de operacion. La caida maxima tampoco se movio porque su minimo
  no cayo en un dia de fill.

O sea: tres contratos economicos que estaban roto, arreglados y
demostrados con casos que fallaban antes, cuyo efecto agregado sobre ESTAS
cifras esta en el cuarto decimal. Las dos cosas son verdad a la vez y
ninguna cancela a la otra. Lo que no se puede decir es que los arreglos
"mejoraron el resultado": no lo mejoraron ni lo empeoraron de forma
apreciable aqui.

La conclusion de fondo no cambia: en renta variable M03 empata con
comprar y mantener, en multiactivo le saca 1,33 puntos, y ninguna de las
cuatro hipotesis se rechaza tras corregir por comparaciones multiples.
