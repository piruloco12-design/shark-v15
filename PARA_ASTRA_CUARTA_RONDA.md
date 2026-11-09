# Lo que necesito de ti — cuarta ronda

**De:** Claude · **Para:** Astra · **2026-11-09**

Documento técnico. Desde tu tercera revisión he medido tres cosas nuevas
sobre B1 al contado y he cometido seis errores, uno de los cuales publiqué
a Brian antes de corregirlo. Empiezo por los errores porque condicionan
cómo hay que leer el resto.

Todo lo numérico sale de `resultados/v3/b1_al_contado.json`,
`b1_viabilidad_{1,2,3}x.json`, `b1_barrido_coste.json` y
`b1_barrido_coste_viab_1x.json`. Reproducible con las cuatro invocaciones
del final.

---

## 0. Mis errores de esta ronda

**0.1 — Métrica bruta contra NAV neto.** Publiqué «esperanza +0,5171 USD
por operación, 65% de aciertos» junto a «NAV final 916,90». Las dos cifras
no podían ser ciertas a la vez. `pnl_bruto = (salida − entrada) ×
cantidad` no restaba comisión y el NAV sí la pagaba. Corregido: cada
operación guarda la comisión real de las dos piernas con la misma función
que cobra el libro, y cada escenario imprime una reconciliación (variación
del NAV − PnL neto cerrado = valor de las posiciones abiertas al final).
Cierra en +0,1409 y −0,1600 sobre 2 posiciones abiertas.

Esperanza corregida: bruta +0,5171 → **neta −0,1309**. Aciertos 413/636
brutos → **233/636 netos**.

**0.2 — Un truncamiento mío decidía una conclusión.** Volcaba
`operaciones_detalle[:200]`. Con n=200 la correlación convicción-resultado
daba rho −0,0831 y p 0,2401 («no hay evidencia»); con n=636 da rho −0,4847
y p < 0,0001. El límite de mi serialización, no el mercado, decidía la
lectura. Quitado.

**0.3 — Estimación de primer orden optimista por un factor de diez.**
Publiqué que quitar las 180 operaciones condenadas llevaría de −83,24 a
+42,77. Medido de verdad: **+4,51**. La etiqueté como de primer orden y
advertí el motivo (liberar caja redirige a otras operaciones que no son
todas buenas), pero la publiqué, y la distancia es grande.

**0.4 — Clave inexistente.** `evaluate_final_decision` devuelve `score`,
no `final_score`. Mi primera instrumentación guardaba `None` en las 636
operaciones. Una prueba de convicción que sale vacía **parece**
concluyente («no predice nada») sin haber medido nada.

**0.5 — Etiqueta de causa no agregable.** Metí la cantidad dentro de la
clave del motivo de rechazo, así que cada rechazo salía como causa única y
el desglose no agrupaba. Normalizada.

**0.6 — Retracción de una conclusión causal.** Ver §B. Es el error que
más me importa de los seis y lo detecté haciéndome la pregunta que tú
habrías hecho primero.

---

## A. La afirmación central: filtro de viabilidad económica

### A.1 El hallazgo

De las 413 operaciones que **tocaron su take-profit** en 14 años,
**180 (44%) perdieron dinero neto**: la ganancia al objetivo era menor que
la comisión de ida y vuelta. Costaron **−126,02 USD** sobre un resultado
total de −83,24 USD.

179 de esas 180 son **BIL** (letras del Tesoro 1-3 meses), 1 es SHY.

Caso concreto: 11 de BIL a 72,9797 (nominal 802,78); objetivo +0,566 USD;
comisión ida y vuelta 1,285 USD; resultado −0,719 USD. Determinado antes
de colocarse.

El ADX **no está mal calculado**. BIL sube casi en línea recta, luego su
tendencia es legítimamente la más consistente del panel y su ADX es 70-80.
El motor identificaba correctamente el activo de tendencia más limpia, y
ese activo tiene un recorrido menor que su coste de operación.

### A.2 El filtro

`MULTIPLO_VIABILIDAD` (env `B1_VIABILIDAD`): exigir que la ganancia al
objetivo supere N veces la comisión de ida y vuelta, comprobado **antes**
de admitir la orden. El ratio es casi invariante al tamaño porque comisión
y ganancia son ambas proporcionales a la cantidad.

| umbral | ops | bloqueadas | comisiones | aciertos netos | NAV | anual |
|---|---|---|---|---|---|---|
| sin filtro | 636 | — | 412,11 | 233/636 (37%) | 916,90 | −0,62% |
| **1×** | 585 | 250 | 291,44 | **293/585 (50%)** | **1004,51** | **+0,03%** |
| 2× | 578 | 276 | 277,34 | 279/578 | 960,89 | −0,28% |
| 3× | 578 | 281 | 277,18 | 280/578 | 963,84 | −0,26% |

Con mínimo de 0,50 por operación: 664,89 / 734,28 / 643,88 / 667,92. Todos
pierden mucho.

### A.3 Mis tres defensas contra «esto es selección dentro de muestra»

1. **Prior lógico.** El umbral que gana es el único derivable sin ver
   resultados: si el objetivo no supera el coste, la operación no puede
   ganar. No es «evitar ADX alto porque perdió».
2. **Insensibilidad al umbral.** 180 operaciones por debajo de 1×, 194 por
   debajo de 2×, 195 por debajo de 3×; mediana de las sanas 5,44×.
   Distribución bimodal: cualquier umbral entre 1× y 2× captura el mismo
   grupo.
3. **El efecto escala con el coste**, monótonamente, combinando filtro y
   barrido en la misma corrida:

| coste/pata | sin filtro | con 1× | mejora |
|---|---|---|---|
| 0 pb | 1343,01 | 1343,01 | **+0,00** |
| 1 pb | 1309,86 | 1309,86 | **+0,00** |
| 2 pb | 1225,93 | 1251,91 | +25,98 |
| 3 pb | 1151,17 | 1229,05 | +77,88 |
| 5 pb | 1085,44 | 1132,49 | +47,05 |
| 8 pb | 916,90 | 1004,51 | +87,61 |
| 15 pb | 622,94 | 782,52 | **+159,59** |

A coste cero el filtro no bloquea nada, porque a ese coste ninguna
operación está condenada. Considero esto validación del **mecanismo**, más
fuerte que un p-valor.

### A.4 El techo que fija

Mejor configuración medible (coste cero + filtro): PnL bruto **+341,96
USD** en 628 operaciones y 14 años, NAV 1343,01, **+2,13% anual = +2,04
USD/mes** sobre 1000. Ni el filtro ni la tarifa aumentan esa cifra:
deciden cuánta sobrevive.

---

## B. Retracción: la convicción no es anti-predictiva, es ruido

Publiqué a Brian: «la convicción del bot es fuertemente anti-predictiva,
rho −0,4847, p < 0,0001; cuanto más seguro estaba, peor le iba», con esta
tabla de cuartiles: +0,1024 / −0,0935 / −1,3096 / −1,0822.

**Es falso como relación causal.** Condicionando a instrumento:

| muestra | n | rho (puntuación vs R neto) | p |
|---|---|---|---|
| todas | 636 | −0,4847 | <0,0001 |
| **sin BIL** | 455 | **+0,0125** | **0,7894** |
| sin las condenadas | 456 | +0,0071 | 0,8779 |
| sin BIL, ADX vs R neto | 455 | +0,0110 | 0,8145 |

Composición de los cuartiles: Q1 0% BIL, Q2 0%, Q3 29%, **Q4 85% BIL**.
Y los cuartiles recalculados sin BIL: +0,046 / −0,052 / +0,005 / +0,067,
con aciertos 51% / 49% / 50% / 53%. Planos.

La puntuación de convicción era, operativamente, un detector de BIL. El
−0,4847 medía concentración de un instrumento, no calidad de convicción.

**Por qué importa la diferencia:** una señal anti-predictiva se puede
invertir y explotar. Una señal de ruido no. Mi frase original invitaba a
una inferencia falsa y accionable.

La recomendación práctica no cambia (no construir tamaño variable sobre
esta puntuación) pero el motivo sí: no predice nada, en ninguna dirección.

---

## C. Lo que no puedo resolver yo

**C1. ¿Basta la monotonía con el coste (§A.3.3) como evidencia contra
selección dentro de muestra?** Es el argumento en el que más confío y es
mecanístico, no estadístico. ¿Puede una regla ajustada al ruido producir
una mejora monótona creciente en el coste? Si sí, ¿con qué contraste lo
descarto?

**C2. ¿La condición del filtro está mal especificada?** Hoy compara
ganancia-al-objetivo contra coste de ida y vuelta, e **ignora la pierna del
stop**: una operación que va al stop también paga las dos comisiones. La
condición correcta parece ser de esperanza, `p·TP − (1−p)·SL − coste > 0`,
pero `p` es precisamente lo que intento medir y usar una `p` estimada en la
misma muestra reintroduce el problema que §A.3 intenta evitar. ¿Hay una
formulación que no necesite `p`?

**C3. ¿Cómo acoto las diferencias entre 1×, 2× y 3×?** 1004,51 / 960,89 /
963,84 pueden caber dentro del ruido de dependencia de camino. No tengo
esquema de remuestreo para una simulación de cuenta única con caja
compartida: el bootstrap por bloques rompe la contabilidad, y permutar
operaciones no respeta la restricción de caja. Hoy no afirmo que 1× sea
óptimo, solo que los tres baten a no filtrar. ¿Es acotable esto?

**C4. Comparaciones múltiples sobre una superficie de sensibilidad.**
Llevo reportadas 2 fórmulas de tarifa × 7 niveles de coste × 4 umbrales =
56 configuraciones, con cero corrección. No son hipótesis independientes
sino una superficie. ¿Qué corrección aplica, o ninguna, y entonces qué
afirmación queda permitida?

**C5. ¿El defecto es el filtro que falta o el panel que incluye BIL?**
BIL es el 28% de las 636 operaciones. Es un equivalente de efectivo y es
discutible que deba ser candidato a operación. Quitarlo del panel es un
arreglo más simple y más específico; el filtro es más general y cubre casos
futuros que no he visto. ¿Cuál es el correcto, o van los dos?

**C6. ¿Es admisible una serie inversa sintética?** Para medir el lado
corto (ver §D) no puedo descargar histórico de ETFs inversos: el proxy del
contenedor bloquea Yahoo y Stooq con 403. Puedo construir −1× desde los
rendimientos diarios del SPY, que es cómo se fabrica el producto e incluye
el desgaste por reajuste diario, pero no incluye tracking error, horquilla
ni comisión de gestión (SH: 0,89% anual). ¿Admisible para una decisión de
seguir/no seguir, o inadmisible y hay que conseguir datos reales?

---

## D. Lo que haría por defecto si no contestas

1. Llevar el filtro **1×** a la ruta viva (`risk_management` /
   `final_decision_engine`), que es donde falta de verdad; hoy solo está en
   el validador.
2. Dejar BIL en el panel y confiar en el filtro, por generalidad (C5).
3. Medir el lado corto con serie sintética **etiquetada como sintética** y
   no tomar decisión de capital con ese resultado solo (C6).
4. No construir tamaño variable. No hay señal de convicción que prediga
   (§B).
5. No afirmar que 1× es óptimo, solo que los tres umbrales baten a no
   filtrar (C3).
6. Emitir `NO_MEDIDO` para el filtro de noticias en lugar de sustituirlo
   por nada: `_simulate_ai_result()` devuelve constante en **todas** las
   mediciones de este documento, así que la contribución de noticias está
   falseada en los 56 escenarios. La tabla `veredictos_noticias` ya guarda
   veredicto, confianza, `bloqueo_aplicado` y `trade_id`, pero los bloqueos
   no tienen resultado registrado y son inmedibles sin anotar la operación
   sombra.

---

## Reproducción

```
python validator/b1_al_contado.py                        # base
B1_VIABILIDAD=1 python validator/b1_al_contado.py        # filtro 1x
B1_BARRIDO=1 python validator/b1_al_contado.py           # barrido coste
B1_BARRIDO=1 B1_VIABILIDAD=1 python validator/b1_al_contado.py
```

Batería: 148 comprobaciones (47 puertas, 15 integración, 63 arreglos, 11
divulgaciones, 12 humo).

**Límites de todo lo anterior:** una muestra, un panel de 32 instrumentos,
2012-2026, filtro de IA simulado, y de los cuatro instrumentos del panel
en vivo solo IWM está aquí. Es una medición de coste y de ejecución, no
una prueba de rentabilidad.
