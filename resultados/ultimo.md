# Validacion SHARK V15

Fecha:   2026-11-07 12:34 UTC
Commit:  67baffb2
Disparo: push

## Entorno
```
pandas   3.1.1
numpy    2.4.6
yfinance 1.8.0
tzdata OK: 2025-12-31 19:00:00-05:00
```

## Tests de regresion
```
  PASA   TP mayor que SL (R:R > 1)

==============================================================
RESULTADO: 24 pruebas pasadas, 0 fallos
==============================================================
  PASA   PRIMARY_PROVIDER coherente

==============================================================
RESULTADO: 64 pruebas pasadas, 0 fallos
==============================================================
  PASA   el aviso NO depende de la variable RENDER

==============================================================
RESULTADO: 33 pruebas pasadas, 0 fallos
==============================================================
=== 4) el profit factor tambien cambia ===
  PF viejo: inf | PF nuevo: inf
  PASA   el PF con costes completos no es mejor que el incompleto

=== 5) con coste cero los dos calculos coinciden ===
  PASA   sin costes, pnl neto == pnl bruto
  PASA   sin costes, la suma cuadra exacta
  PASA   sin costes el resultado es mejor que con costes

==============================================================
RESULTADO: 12 pruebas pasadas, 0 fallos
==============================================================
  PASA   con menos velas que el warmup devuelve None

==============================================================
RESULTADO: 22 pruebas pasadas, 0 fallos
==============================================================
  PASA   guarda si bloqueo o no

==============================================================
RESULTADO: 49 pruebas pasadas, 0 fallos
==============================================================
  PASA   ida y vuelta = 2x el coste por pata

==============================================================
RESULTADO: 20 pruebas pasadas, 0 fallos
==============================================================
    con la fuga: 15 vs 15 decisiones antes del corte

==============================================================
RESULTADO: 14 pruebas pasadas, 0 fallos
==============================================================
  trades: 25 | señales: 270
  bloqueos por cooldown: 245

  PASA   sin cooldown genera trades
  PASA   el cooldown REDUCE el numero de trades
  PASA   el cooldown aparece como motivo de bloqueo
  PASA   ningun trade reentra antes de las 6h

  separacion minima entre trades: sin cooldown 1.5h | con cooldown 21.5h
  trades por dia: sin 2.65 | con 0.62

==============================================================
RESULTADO: 4 pruebas pasadas, 0 fallos
==============================================================
         que en ESTE proceso sintetico un efecto del tamano que
         reclame se confunde con el ruido.
  PASA   la potencia crece con el tamano del efecto (el contraste discrimina)
  PASA   queda registrado que un efecto de +0,72 puntos/ano es casi indetectable con esta muestra

==============================================================
RESULTADO: 19 pruebas pasadas, 0 fallos
==============================================================
  PASA   editar la lista a mano rompe el hash y se detecta
  PASA   la alerta dice que se ha editado despues de congelar

==============================================================
RESULTADO: 15 pruebas pasadas, 0 fallos
==============================================================
         proporcional. Con la tarifa que asume el backtester (8 pb
         por pata, sin minimo) no tiene nada que filtrar.

=== 6) Walk-forward ===
  PASA   el walk-forward evalua varios tramos
         R predicho medio +1.1428  realizado -0.2439  error absoluto medio 1.3387
  PASA   detecta que el pronostico falla cuando el regimen cambia
  PASA   el resumen avisa de cuando el pronostico no dice nada
  PASA   un corte sin muestra suficiente se registra como incidencia
  PASA   sin operaciones suficientes no inventa tramos

==============================================================
RESULTADO: 26 pruebas pasadas, 0 fallos
==============================================================
  N/C    I29 mas Sharpe pero menos dinero  -> es requisito del INFORME del experimento, no del codigo

==============================================================
RESULTADO: 92 pruebas pasadas, 0 fallos, 5 casos NO cubiertos
  NO CUBIERTO- I24 reserva atomica de efectivo entre dos estrategias: no hay libro multiestrategia: las propias estan desactivadas
  NO CUBIERTO- I26 recalcular parametros de un par abierto: M05 bloqueado: no hay cortos ejecutables en cuenta al contado
  NO CUBIERTO- I27 una sola pata ejecutada o prestamo retirado: M05 bloqueado por capacidades
  NO CUBIERTO- I28 balance revisado meses despues: M06 bloqueado: no hay fundamentales point-in-time
  NO CUBIERTO- I29 mas Sharpe pero menos dinero: es requisito del INFORME del experimento, no del codigo
==============================================================
  PASA   con NaN: no lanza, no bloquea, no opina
  PASA   una sola vela: no lanza, no bloquea, no opina
  PASA   indice sin tz: no lanza, no bloquea, no opina
  PASA   en ENFORCE, no tener datos bloquea (no es un permiso implicito)

==============================================================
RESULTADO: 23 pruebas pasadas, 0 fallos
==============================================================
```

## Aceptacion economica

Contratos economicos con oraculos de resultado conocido,
llamando al ejecutor real. Vienen de la auditoria del
2026-10-19.

```
  PASA   [D4] el resumen separa comisiones, nominal y coste sobre nominal
  PASA   [D5] los anos parciales se marcan como parciales

=== E) Calendario y causalidad del mensual ===
  PASA   [E1] una serie que acaba a mitad de mes no genera decision ahi
  PASA   [E2] la ejecucion ocurre DESPUES de la decision, no al mismo cierre
  PASA   [E3] el calentamiento se separa del periodo evaluado

=== F) Vigencia y trazabilidad de los snapshots ===
  PASA   [F1] un ranking de 626 dias es STALE, no READY
  PASA   [F2] un ranking con datos posteriores a la decision se rechaza
  PASA   [F3] cambiar un precio intermedio cambia la version de los datos
  PASA   [F4] existe una tarea que alimenta las series de M02/M03
  PASA   [F5] el snapshot persiste y sobrevive a un reinicio
  PASA   [F6] cargar_ultimo no devuelve un snapshot posterior a la decision
  PASA   [F6b] un snapshot creado despues del corte no pasa por captura PIT
  PASA   [F7] la vigencia sale del calendario del snapshot, no de la consulta
  PASA   [F8] el ranking se reconstruye identico desde la base de datos

=== H) M04 basico: limites de cartera ===
  PASA   [H1] el sobrante tras un tope se queda en EFECTIVO, no se redistribuye
  PASA   [H2] el tope por grupo limita cinco sectores correlacionados
  PASA   [H3] la concentracion se informa por grupo, no solo por activo
  PASA   [H4] verificar() detecta pesos que violan un tope
  PASA   [H5] una configuracion de limites imposible se rechaza al construir
  PASA   [H6] un activo sin grupo cuenta como su propio grupo, no en 'otros'
  PASA   [H7] con limites activos el identificador de la variante CAMBIA
  PASA   [H8] las politicas registran los limites para el manifiesto

=== G) La caja y los cortos ===
  PASA   [G1] la politica de caja esta declarada y por defecto NO remunera
  PASA   [G2] el libro ejecutable al contado no admite abrir cortos
  PASA   [B5] vender toda la posicion la cierra del todo, sin polvo
  PASA   [G3] una venta que reduce un largo existente SI es ejecutable
  PASA   [G4] vender mas de lo disponible no abre un corto: se limita

====================================================================
ACEPTACION: 44 pasan, 0 FALLAN
====================================================================
====================================================================
```

## Puertas de aceptacion (segunda auditoria)

Resultado exigido por PLAN_CLAUDE.md, no comportamiento
actual del codigo. Las pendientes llegan con su cambio.

```
=== CF1, CF2: comision minima por orden (hallazgo propio) ===
  PASA       [CF1] venta cuyo importe no cubre la comision fija: rechazada
  PASA       [CF2] 25 ventas pequenas con comision fija no dejan caja negativa
  PASA       [CF3] el rechazo de una venta antieconomica es politica declarada
  PASA       [CF4] fijo aditivo y minimo por orden son formulas DISTINTAS

=== V12, V13, V14: datos y snapshots ===
  PASA       [V13] 299 velas maduras mas una abierta: se usa la vista madura
  PASA       [V13b] la referencia de efectivo se recorta a la misma observacion
  PASA       [V14] un snapshot recuperado tras el corte no se da como captura anterior
  PASA       [V14b] la ruta estricta SI devuelve una captura anterior al corte
  PASA       [V12] el ciclo comprueba la caducidad aunque la cache este llena
  PASA       [V12b] un snapshot caducado se detecta por calendario, no por reloj

=== V19, V20, V21: bajas declaradas y calidad visible ===
  PASA       [V19] fondo liquidado: unidades fuera, derecho dentro, y se cobra
  PASA       [V19b] repetir el evento de liquidacion no cobra dos veces
  PASA       [V19c] politica de reinversion no implementada: error explicito
  PASA       [V20] falta la descarga de un congelado: se marca, no se borra
  PASA       [V21] precio ausente: calidad visible y el NAV se declara no fiable
  PASA       [V21b] con EXIGIR_EVENTO no se emite NAV sin evidencia del evento

=== V15, V16, V17, V18: M01 ===
  PASA       [V15] bootstrap n=10 bloque=5: bloques circulares y sin sesgo
  PASA       [V15b] cada replica tiene exactamente n valores, no menos
  PASA       [V16] dos cortes y 25 decisiones: asignacion 10+15 sin duplicados
  PASA       [V17] pronostico bruto perfecto: error bruto cero y coste aparte
  PASA       [V18] mismo coste proporcional, distinta distancia: decisiones distintas

=== NE1: la inferencia RECHAZA un NAV no evaluable ===
  PASA       [NE1] con una cartera no fiable, el contraste no se emite
  PASA       [NE1b] una cartera que falta tambien impide contrastar

=== V24: reejecucion reproducible ===
  PASA       [V24] reejecucion: NAV identico al bit, sin tolerancia
  PASA       [V24b] reejecucion: mismas decisiones y mismos fills
  PASA       [V24c] reejecucion: mismo libro final y mismas metricas
  PASA       [V24d] la corrida comparada SI opera (si no, no prueba nada)

=== Puertas de cambios posteriores ===

======================================================================
PUERTAS: 47 pasan, 0 FALLAN, 0 pendientes de su cambio
======================================================================
======================================================================
```

## Integracion de la ruta viva

Caja, inventario y reservas de la ruta que de verdad
opera, comprobados entrando por su apertura y su cierre.

```
  PASA   [I4b] fraccion SOLO con la capacidad declarada explicitamente

=== I5: fill repetido ===
PAPER BROKER | Trade abierto | REP | BUY | Entry: 100.0000 | SL: 98.0000 | TP: 104.0000 | Size: 3.0000 (pedida 3.0000) | Caja utilizable: 699.76
  PASA   [I5] repetir el mismo fill no cambia saldos ni cantidades
  PASA   [I5b] el mismo event_id con OTRO contenido da conflicto, no silencio

=== I6: cancelar una orden no toca la reserva de otra ===
  PASA   [I6] cancelar A deja intacta la reserva de B

=== I7: reiniciar reconstruye el MISMO estado ===
PAPER BROKER | Trade abierto | R1 | BUY | Entry: 100.0000 | SL: 98.0000 | TP: 104.0000 | Size: 3.0000 (pedida 3.0000) | Caja utilizable: 699.76
PAPER BROKER | Trade setup inválido en R2, no se abre trade
  PASA   [I7] reiniciar: estado contable identico, derivado de los eventos
  PASA   [I7b] la reserva viva sobrevive al reinicio

=== I8: los dos saldos no divergen al cerrar ===
PAPER BROKER | Trade abierto | CIE | BUY | Entry: 100.0000 | SL: 98.0000 | TP: 104.0000 | Size: 5.0000 (pedida 5.0000) | Caja utilizable: 499.60
PAPER BROKER | Trade cerrado | CIE | BUY | Motivo: TAKE_PROFIT | Exit: 104.0000 | PnL neto: 19.18 | comisiones: 0.82 | Capital: 1019.18
  PASA   [I8] tras cerrar: caja, espejo e inventario cuadran
  PASA   [I8b] cada pata se cobra UNA vez en su propio fill

=== I9: un fill fallido no envenena el registro ===
  PASA   [I9] un fill que fallo no rompe la reconstruccion
  PASA   [I9b] y el intento queda como incidencia, no borrado

======================================================================
INTEGRACION DE LA RUTA VIVA: 15 pasan, 0 FALLAN
======================================================================
======================================================================
```

## Seguimiento de divulgaciones (modo OBSERVE)

```
  PASA   [D3] y dice que HOY ese dato tiene 130 dias
  PASA   [D4] un 13F de 130 dias NO se etiqueta como reciente
  PASA   [D5] el Form 4 avisa de que es un directivo, no el gestor

=== La etiqueta 'tiempo real' no existe ===
  PASA   [D6] ninguna etiqueta de vigencia dice tiempo real, con ningun plazo
  PASA   [D7] ni con 0 dias de antiguedad en la via mas rapida

=== El modulo no puede emitir una orden ===
  PASA   [D8] modo OBSERVE: pedirle una senal lanza, no devuelve una orden

=== No se inventan identificadores de gestor ===
  PASA   [D9] sin red no se resuelve un CIK de memoria

=== Una lista vacia no significa 'no hay movimientos' ===
  PASA   [D10] el resumen vacio distingue 'no publicado' de 'no ocurrido'
  PASA   [D11] el resumen dice cual es el dato mas fresco y que no es vivo

======================================================================
DIVULGACIONES: 11 pasan, 0 FALLAN
======================================================================
Probado contra fixtures. NINGUNA comprobacion contra la SEC real:
el proxy de este contenedor bloquea sec.gov.
======================================================================
```

## Imports
```
39/39 modulos importan
```

## Diagnostico del feed
```
Timeframe 30m | Periodo 60d | MIN_BARS 220
Providers ['yfinance', 'finnhub', 'alpha_vantage', 'twelve_data']

ACTIVO  PROVIDER    VELAS  DIAS  X/DIA  HORAS ET
IWM     yfinance      780    60   13.0  [9, 10, 11, 12, 13, 14, 15]
        2026-08-14 09:30:00-04:00  ->  2026-11-06 15:30:00-05:00
NVDA    yfinance      780    60   13.0  [9, 10, 11, 12, 13, 14, 15]
        2026-08-14 09:30:00-04:00  ->  2026-11-06 15:30:00-05:00
AMZN    yfinance      780    60   13.0  [9, 10, 11, 12, 13, 14, 15]
        2026-08-14 09:30:00-04:00  ->  2026-11-06 15:30:00-05:00
META    yfinance      780    60   13.0  [9, 10, 11, 12, 13, 14, 15]
        2026-08-14 09:30:00-04:00  ->  2026-11-06 15:30:00-05:00
```

## Backtest intradia
```

=================================================================
  SHARK V16 SNIPER — BACKTESTER FIEL
  Usa la misma lógica que live_engine.py
  Timeframe: 30m | Período: 60d
  Capital: 1000.0 | Risk/trade: 0.005
  Sniper mode: True | Min ADX: 22.0
  Min AI Score: 50.0 | Min Context Score: 55.0
  Min Final Score: 55.0
  Trading cost total: 0.08%
  Activos: ['IWM', 'NVDA', 'AMZN', 'META']
=================================================================

Descargando IWM...
  OK | yfinance | 780 velas
Descargando NVDA...
  OK | yfinance | 780 velas
Descargando AMZN...
  OK | yfinance | 780 velas
Descargando META...
  OK | yfinance | 780 velas

=================================================================
  FASE 1: BACKTEST COMPLETO (todo el período)
=================================================================

============================================================
IWM | FULL | Bars: 580
============================================================
Capital:     1000.00 → 991.91  (-8.09)
Señales:     46 generadas | 13 ALLOW | 33 BLOCK
Trades:      12 cerrados | 6 wins | 6 losses
Winrate:     50.0%
Avg Trade:   -0.65
Avg Win:     6.47  |  Avg Loss: 7.76
Expectancy:  -0.65 por trade
PF:          0.83
Max DD:      26.80 (2.7%)
Avg Bars:    11 velas
Regímenes:   {'BEAR_TREND': 6, 'TREND': 6}
Señales:     {'SELL': 11, 'BUY': 1}
Bloqueos principales:
    31x  Cooldown por activo (6h)
     1x  ADX insuficiente para sniper: 20.88 < 22.0 | Score final insuficiente para sniper: 54.30 <
     1x  ADX insuficiente para sniper: 21.95 < 22.0 | Score final insuficiente para sniper: 54.97 <

============================================================
NVDA | FULL | Bars: 580
============================================================
Capital:     1000.00 → 982.33  (-17.67)
Señales:     63 generadas | 19 ALLOW | 44 BLOCK
Trades:      19 cerrados | 8 wins | 11 losses
Winrate:     42.1%
Avg Trade:   -0.93
Avg Win:     7.08  |  Avg Loss: 6.76
Expectancy:  -0.93 por trade
PF:          0.76
Max DD:      27.05 (2.7%)
Avg Bars:    12 velas
Regímenes:   {'BEAR_TREND': 13, 'TREND': 4, 'BULL_TREND': 2}
Señales:     {'SELL': 14, 'BUY': 5}
Bloqueos principales:
    42x  Cooldown por activo (6h)
     1x  ADX insuficiente para sniper: 21.76 < 22.0 | Score final insuficiente para sniper: 54.85 <
     1x  ADX insuficiente para sniper: 20.36 < 22.0 | Score final insuficiente para sniper: 53.97 <

============================================================
AMZN | FULL | Bars: 580
============================================================
Capital:     1000.00 → 983.37  (-16.63)
Señales:     85 generadas | 20 ALLOW | 65 BLOCK
Trades:      20 cerrados | 9 wins | 11 losses
Winrate:     45.0%
Avg Trade:   -0.83
Avg Win:     5.62  |  Avg Loss: 6.11
Expectancy:  -0.83 por trade
PF:          0.75
Max DD:      51.99 (5.2%)
Avg Bars:    11 velas
Regímenes:   {'TREND': 6, 'BEAR_TREND': 10, 'BULL_TREND': 4}
Señales:     {'SELL': 14, 'BUY': 6}
Bloqueos principales:
    64x  Cooldown por activo (6h)
     1x  ADX insuficiente para sniper: 21.75 < 22.0 | Score final insuficiente para sniper: 54.84 <

============================================================
META | FULL | Bars: 580
============================================================
Capital:     1000.00 → 1048.20  (+48.20)
Señales:     59 generadas | 14 ALLOW | 45 BLOCK
Trades:      14 cerrados | 11 wins | 3 losses
Winrate:     78.6%
Avg Trade:   3.44
Avg Win:     5.94  |  Avg Loss: 5.71
Expectancy:  3.44 por trade
PF:          3.81
Max DD:      11.48 (1.1%)
Avg Bars:    18 velas
Regímenes:   {'BULL_TREND': 8, 'BEAR_TREND': 6}
Señales:     {'BUY': 8, 'SELL': 6}
Bloqueos principales:
    45x  Cooldown por activo (6h)


#################################################################
  CONSOLIDADO FULL PERIOD — 4 activos
#################################################################
  Señales:     253 generadas | 66 ALLOW | 187 BLOCK
  Trades:      65 cerrados | 34 wins | 31 losses
  Winrate:     52.3%
  Avg Trade:   0.09
  Avg Win:     6.22  |  Avg Loss: 6.62
  Expectancy:  0.09 por trade
  PF:          1.03
  PnL total:   +5.80
  Peor DD:     51.99
  -------------------------------------------------------------
  Suma PnL trades:  +6.11   (debe cuadrar con PnL total)
  ✅ Cuadra (dif. 0.31, son costes de trades aún abiertos)
#################################################################

  VEREDICTO:
  🟡  Edge marginal. Positivo pero débil.


=================================================================
  FASE 2: WALK-FORWARD (70% train / 30% test)
=================================================================

--- IWM TRAIN ---
  ============================================================
  IWM | TRAIN | Bars: 346
  ============================================================
  Capital:     1000.00 → 986.83  (-13.17)
  Señales:     25 generadas | 8 ALLOW | 17 BLOCK
  Trades:      7 cerrados | 3 wins | 4 losses
  Winrate:     42.9%
  Avg Trade:   -1.75
  Avg Win:     5.87  |  Avg Loss: 7.47
  Expectancy:  -1.75 por trade
  PF:          0.59
  Max DD:      26.80 (2.7%)
  Avg Bars:    9 velas
  Regímenes:   {'BEAR_TREND': 4, 'TREND': 3}
  Señales:     {'SELL': 7}
  Bloqueos principales:
      16x  Cooldown por activo (6h)
       1x  ADX insuficiente para sniper: 20.88 < 22.0 | Score final insuficiente para sniper: 54.30 <

--- IWM TEST ---
  ============================================================
  IWM | TEST | Bars: 234
  ============================================================
  Capital:     1000.00 → 999.51  (-0.49)
  Señales:     16 generadas | 6 ALLOW | 10 BLOCK
  Trades:      5 cerrados | 3 wins | 2 losses
  Winrate:     60.0%
  Avg Trade:   -0.04
  Avg Win:     5.55  |  Avg Loss: 8.42
  Expectancy:  -0.04 por trade
  PF:          0.99
  Max DD:      14.10 (1.4%)
  Avg Bars:    13 velas
  Regímenes:   {'BEAR_TREND': 2, 'TREND': 3}
  Señales:     {'SELL': 4, 'BUY': 1}
  Bloqueos principales:
       9x  Cooldown por activo (6h)
       1x  ADX insuficiente para sniper: 21.95 < 22.0 | Score final insuficiente para sniper: 54.97 <

--- NVDA TRAIN ---
  ============================================================
  NVDA | TRAIN | Bars: 346
  ============================================================
  Capital:     1000.00 → 994.31  (-5.69)
  Señales:     34 generadas | 10 ALLOW | 24 BLOCK
  Trades:      10 cerrados | 4 wins | 6 losses
  Winrate:     40.0%
  Avg Trade:   -0.57
  Avg Win:     7.84  |  Avg Loss: 6.17
  Expectancy:  -0.57 por trade
  PF:          0.85
  Max DD:      23.27 (2.3%)
  Avg Bars:    15 velas
  Regímenes:   {'BEAR_TREND': 4, 'TREND': 4, 'BULL_TREND': 2}
  Señales:     {'SELL': 5, 'BUY': 5}
  Bloqueos principales:
      23x  Cooldown por activo (6h)
       1x  ADX insuficiente para sniper: 21.76 < 22.0 | Score final insuficiente para sniper: 54.85 <

--- NVDA TEST ---
  ============================================================
  NVDA | TEST | Bars: 234
  ============================================================
  Capital:     1000.00 → 987.95  (-12.05)
  Señales:     29 generadas | 9 ALLOW | 20 BLOCK
  Trades:      9 cerrados | 4 wins | 5 losses
  Winrate:     44.4%
  Avg Trade:   -1.34
  Avg Win:     6.36  |  Avg Loss: 7.50
  Expectancy:  -1.34 por trade
  PF:          0.68
  Max DD:      19.90 (2.0%)
  Avg Bars:    8 velas
  Regímenes:   {'BEAR_TREND': 9}
  Señales:     {'SELL': 9}
  Bloqueos principales:
      19x  Cooldown por activo (6h)
       1x  ADX insuficiente para sniper: 20.36 < 22.0 | Score final insuficiente para sniper: 53.97 <

--- AMZN TRAIN ---
  ============================================================
  AMZN | TRAIN | Bars: 346
  ============================================================
  Capital:     1000.00 → 1030.47  (+30.47)
  Señales:     50 generadas | 11 ALLOW | 39 BLOCK
  Trades:      10 cerrados | 8 wins | 2 losses
  Winrate:     80.0%
  Avg Trade:   3.08
  Avg Win:     5.60  |  Avg Loss: 7.00
  Expectancy:  3.08 por trade
  PF:          3.20
  Max DD:      16.13 (1.6%)
  Avg Bars:    11 velas
  Regímenes:   {'TREND': 3, 'BEAR_TREND': 5, 'BULL_TREND': 2}
  Señales:     {'SELL': 7, 'BUY': 3}
  Bloqueos principales:
      38x  Cooldown por activo (6h)
       1x  ADX insuficiente para sniper: 21.75 < 22.0 | Score final insuficiente para sniper: 54.84 <

--- AMZN TEST ---
  ============================================================
  AMZN | TEST | Bars: 234
  ============================================================
  Capital:     1000.00 → 972.44  (-27.56)
  Señales:     31 generadas | 9 ALLOW | 22 BLOCK
  Trades:      9 cerrados | 2 wins | 7 losses
  Winrate:     22.2%
  Avg Trade:   -3.06
  Avg Win:     6.77  |  Avg Loss: 5.87
  Expectancy:  -3.06 por trade
  PF:          0.33
  Max DD:      39.36 (3.9%)
  Avg Bars:    9 velas
  Regímenes:   {'BEAR_TREND': 5, 'TREND': 3, 'BULL_TREND': 1}
  Señales:     {'SELL': 7, 'BUY': 2}
  Bloqueos principales:
      22x  Cooldown por activo (6h)

--- META TRAIN ---
  ============================================================
  META | TRAIN | Bars: 346
  ============================================================
  Capital:     1000.00 → 1023.77  (+23.77)
  Señales:     37 generadas | 8 ALLOW | 29 BLOCK
  Trades:      8 cerrados | 6 wins | 2 losses
  Winrate:     75.0%
  Avg Trade:   2.97
  Avg Win:     5.88  |  Avg Loss: 5.75
  Expectancy:  2.97 por trade
  PF:          3.07
  Max DD:      9.62 (1.0%)
  Avg Bars:    19 velas
  Regímenes:   {'BULL_TREND': 7, 'BEAR_TREND': 1}
  Señales:     {'BUY': 7, 'SELL': 1}
  Bloqueos principales:
      29x  Cooldown por activo (6h)

--- META TEST ---
  ============================================================
  META | TEST | Bars: 234
  ============================================================
  Capital:     1000.00 → 1023.86  (+23.86)
  Señales:     22 generadas | 6 ALLOW | 16 BLOCK
  Trades:      6 cerrados | 5 wins | 1 losses
  Winrate:     83.3%
  Avg Trade:   3.98
  Avg Win:     5.87  |  Avg Loss: 5.50
  Expectancy:  3.98 por trade
  PF:          5.34
  Max DD:      9.25 (0.9%)
  Avg Bars:    16 velas
  Regímenes:   {'BULL_TREND': 1, 'BEAR_TREND': 5}
  Señales:     {'BUY': 1, 'SELL': 5}
  Bloqueos principales:
      16x  Cooldown por activo (6h)


#################################################################
  CONSOLIDADO TRAIN (IN-SAMPLE) — 4 activos
#################################################################
  Señales:     146 generadas | 37 ALLOW | 109 BLOCK
  Trades:      35 cerrados | 21 wins | 14 losses
  Winrate:     60.0%
  Avg Trade:   1.05
  Avg Win:     6.14  |  Avg Loss: 6.60
  Expectancy:  1.05 por trade
  PF:          1.40
  PnL total:   +35.38
  Peor DD:     26.80
  -------------------------------------------------------------
  Suma PnL trades:  +36.61   (debe cuadrar con PnL total)
  ✅ Cuadra (dif. 1.23, son costes de trades aún abiertos)
#################################################################

  VEREDICTO:
  ✅  HAY EDGE. Expectancy positiva, PF > 1.2, winrate razonable.


#################################################################
  CONSOLIDADO TEST (OUT-OF-SAMPLE) — 4 activos
#################################################################
  Señales:     98 generadas | 30 ALLOW | 68 BLOCK
  Trades:      29 cerrados | 14 wins | 15 losses
  Winrate:     48.3%
  Avg Trade:   -0.55
  Avg Win:     6.07  |  Avg Loss: 6.73
  Expectancy:  -0.55 por trade
  PF:          0.84
  PnL total:   -16.25
  Peor DD:     39.36
  -------------------------------------------------------------
  Suma PnL trades:  -15.94   (debe cuadrar con PnL total)
  ✅ Cuadra (dif. 0.31, son costes de trades aún abiertos)
#################################################################

  VEREDICTO:
  ❌  NO HAY EDGE. Expectancy negativa.


=================================================================
  COMPARACIÓN TRAIN vs TEST
=================================================================

  IWM:
    TRAIN: 7 trades | WR 42.9% | PF 0.59 | Exp -1.75
    TEST:  5 trades | WR 60.0% | PF 0.99 | Exp -0.04
    ⚠️  Pocos trades para comparar

  NVDA:
    TRAIN: 10 trades | WR 40.0% | PF 0.85 | Exp -0.57
    TEST:  9 trades | WR 44.4% | PF 0.68 | Exp -1.34
    ✅  Consistente entre train y test

  AMZN:
    TRAIN: 10 trades | WR 80.0% | PF 3.20 | Exp 3.08
    TEST:  9 trades | WR 22.2% | PF 0.33 | Exp -3.06
    ⚠️  Degradación significativa train→test

  META:
    TRAIN: 8 trades | WR 75.0% | PF 3.07 | Exp 2.97
    TEST:  6 trades | WR 83.3% | PF 5.34 | Exp 3.98
    ✅  Consistente entre train y test


=================================================================
  BACKTEST COMPLETO
=================================================================

```

## Backtest diario (15 anos)

Misma logica, timeframe diario. Aqui yfinance si da
anos de historico, asi que la muestra es grande y el
resultado si es estadisticamente interpretable.

```

=================================================================
  SHARK V16 SNIPER — BACKTESTER FIEL
  Usa la misma lógica que live_engine.py
  Timeframe: 1d | Período: 15y
  Capital: 1000.0 | Risk/trade: 0.005
  Sniper mode: True | Min ADX: 22.0
  Min AI Score: 50.0 | Min Context Score: 55.0
  Min Final Score: 55.0
  Trading cost total: 0.08%
  Activos: ['IWM', 'NVDA', 'AMZN', 'META']
=================================================================

Descargando IWM...
  OK | yfinance | 3772 velas
Descargando NVDA...
  OK | yfinance | 3772 velas
Descargando AMZN...
  OK | yfinance | 3772 velas
Descargando META...
  OK | yfinance | 3639 velas

=================================================================
  FASE 1: BACKTEST COMPLETO (todo el período)
=================================================================

============================================================
IWM | FULL | Bars: 3572
============================================================
Capital:     1000.00 → 918.56  (-81.44)
Señales:     181 generadas | 105 ALLOW | 76 BLOCK
Trades:      105 cerrados | 42 wins | 63 losses
Winrate:     40.0%
Avg Trade:   -0.78
Avg Win:     6.02  |  Avg Loss: 5.30
Expectancy:  -0.78 por trade
PF:          0.76
Max DD:      106.35 (10.6%)
Avg Bars:    12 velas
Regímenes:   {'TREND': 29, 'BULL_TREND': 39, 'BEAR_TREND': 37}
Señales:     {'BUY': 55, 'SELL': 50}
Bloqueos principales:
    38x  Cooldown por activo (6h)
    14x  Volatilidad no válida: Volatilidad demasiado comprimida
     2x  ADX insuficiente para sniper: 21.78 < 22.0 | Score final insuficiente para sniper: 54.86 <
     1x  ADX insuficiente para sniper: 20.09 < 22.0 | Score final insuficiente para sniper: 53.80 <
     1x  ADX insuficiente para sniper: 21.29 < 22.0 | Score final insuficiente para sniper: 54.56 <

============================================================
NVDA | FULL | Bars: 3572
============================================================
Capital:     1000.00 → 1195.33  (+195.33)
Señales:     215 generadas | 136 ALLOW | 79 BLOCK
Trades:      136 cerrados | 77 wins | 59 losses
Winrate:     56.6%
Avg Trade:   1.44
Avg Win:     6.90  |  Avg Loss: 5.70
Expectancy:  1.44 por trade
PF:          1.58
Max DD:      37.12 (3.7%)
Avg Bars:    10 velas
Regímenes:   {'TREND': 34, 'BULL_TREND': 77, 'BEAR_TREND': 25}
Señales:     {'SELL': 29, 'BUY': 107}
Bloqueos principales:
    57x  Cooldown por activo (6h)
     3x  Volatilidad no válida: Volatilidad demasiado comprimida
     1x  ADX insuficiente para sniper: 21.94 < 22.0 | Score final insuficiente para sniper: 54.96 <
     1x  ADX insuficiente para sniper: 21.59 < 22.0 | Score final insuficiente para sniper: 54.75 <
     1x  ADX insuficiente para sniper: 20.79 < 22.0 | Score final insuficiente para sniper: 54.24 <

============================================================
AMZN | FULL | Bars: 3572
============================================================
Capital:     1000.00 → 1024.09  (+24.09)
Señales:     219 generadas | 131 ALLOW | 88 BLOCK
Trades:      131 cerrados | 61 wins | 70 losses
Winrate:     46.6%
Avg Trade:   0.18
Avg Win:     7.17  |  Avg Loss: 5.91
Expectancy:  0.18 por trade
PF:          1.06
Max DD:      83.40 (8.3%)
Avg Bars:    12 velas
Regímenes:   {'BULL_TREND': 66, 'BEAR_TREND': 33, 'TREND': 32}
Señales:     {'BUY': 88, 'SELL': 43}
Bloqueos principales:
    49x  Cooldown por activo (6h)
    11x  Volatilidad no válida: Volatilidad demasiado comprimida
     1x  ADX insuficiente para sniper: 21.50 < 22.0 | Score final insuficiente para sniper: 54.69 <
     1x  ADX insuficiente para sniper: 20.18 < 22.0 | Score final insuficiente para sniper: 53.86 <
     1x  ADX insuficiente para sniper: 20.15 < 22.0 | Score final insuficiente para sniper: 53.84 <

============================================================
META | FULL | Bars: 3439
============================================================
Capital:     1000.00 → 1069.61  (+69.61)
Señales:     183 generadas | 128 ALLOW | 55 BLOCK
Trades:      127 cerrados | 61 wins | 66 losses
Winrate:     48.0%
Avg Trade:   0.55
Avg Win:     7.13  |  Avg Loss: 5.53
Expectancy:  0.55 por trade
PF:          1.19
Max DD:      55.89 (5.6%)
Avg Bars:    12 velas
Regímenes:   {'BULL_TREND': 75, 'BEAR_TREND': 31, 'TREND': 21}
Señales:     {'BUY': 94, 'SELL': 33}
Bloqueos principales:
    41x  Cooldown por activo (6h)
     2x  ADX insuficiente para sniper: 20.42 < 22.0 | Score final insuficiente para sniper: 54.01 <
     1x  ADX insuficiente para sniper: 20.81 < 22.0 | Score final insuficiente para sniper: 54.26 <
     1x  ADX insuficiente para sniper: 20.34 < 22.0 | Score final insuficiente para sniper: 53.96 <
     1x  ADX insuficiente para sniper: 21.96 < 22.0 | Score final insuficiente para sniper: 54.97 <


#################################################################
  CONSOLIDADO FULL PERIOD — 4 activos
#################################################################
  Señales:     798 generadas | 500 ALLOW | 298 BLOCK
  Trades:      499 cerrados | 241 wins | 258 losses
  Winrate:     48.3%
  Avg Trade:   0.42
  Avg Win:     6.87  |  Avg Loss: 5.62
  Expectancy:  0.42 por trade
  PF:          1.14
  PnL total:   +207.59
  Peor DD:     106.35
  -------------------------------------------------------------
  Suma PnL trades:  +207.64   (debe cuadrar con PnL total)
  ✅ Cuadra (dif. 0.05, son costes de trades aún abiertos)
#################################################################

  VEREDICTO:
  🟡  Edge marginal. Positivo pero débil.


=================================================================
  FASE 2: WALK-FORWARD (70% train / 30% test)
=================================================================

--- IWM TRAIN ---
  ============================================================
  IWM | TRAIN | Bars: 2440
  ============================================================
  Capital:     1000.00 → 988.33  (-11.67)
  Señales:     130 generadas | 75 ALLOW | 55 BLOCK
  Trades:      75 cerrados | 34 wins | 41 losses
  Winrate:     45.3%
  Avg Trade:   -0.16
  Avg Win:     6.10  |  Avg Loss: 5.34
  Expectancy:  -0.16 por trade
  PF:          0.95
  Max DD:      58.12 (5.8%)
  Avg Bars:    11 velas
  Regímenes:   {'TREND': 19, 'BULL_TREND': 28, 'BEAR_TREND': 28}
  Señales:     {'BUY': 40, 'SELL': 35}
  Bloqueos principales:
      28x  Cooldown por activo (6h)
      14x  Volatilidad no válida: Volatilidad demasiado comprimida
       1x  ADX insuficiente para sniper: 20.09 < 22.0 | Score final insuficiente para sniper: 53.80 <
       1x  ADX insuficiente para sniper: 21.29 < 22.0 | Score final insuficiente para sniper: 54.56 <
       1x  ADX insuficiente para sniper: 20.74 < 22.0 | Score final insuficiente para sniper: 54.21 <

--- IWM TEST ---
  ============================================================
  IWM | TEST | Bars: 1132
  ============================================================
  Capital:     1000.00 → 929.40  (-70.60)
  Señales:     51 generadas | 30 ALLOW | 21 BLOCK
  Trades:      30 cerrados | 8 wins | 22 losses
  Winrate:     26.7%
  Avg Trade:   -2.35
  Avg Win:     5.72  |  Avg Loss: 5.29
  Expectancy:  -2.35 por trade
  PF:          0.39
  Max DD:      74.11 (7.4%)
  Avg Bars:    13 velas
  Regímenes:   {'TREND': 10, 'BEAR_TREND': 9, 'BULL_TREND': 11}
  Señales:     {'SELL': 15, 'BUY': 15}
  Bloqueos principales:
      10x  Cooldown por activo (6h)
       1x  ADX insuficiente para sniper: 21.62 < 22.0 | Score final insuficiente para sniper: 54.76 <
       1x  ADX insuficiente para sniper: 20.92 < 22.0 | Score final insuficiente para sniper: 54.32 <
       1x  ADX insuficiente para sniper: 20.38 < 22.0 | Score final insuficiente para sniper: 53.99 <
       1x  ADX insuficiente para sniper: 20.19 < 22.0 | Score final insuficiente para sniper: 53.87 <

--- NVDA TRAIN ---
  ============================================================
  NVDA | TRAIN | Bars: 2440
  ============================================================
  Capital:     1000.00 → 1096.31  (+96.31)
  Señales:     153 generadas | 96 ALLOW | 57 BLOCK
  Trades:      95 cerrados | 51 wins | 44 losses
  Winrate:     53.7%
  Avg Trade:   1.01
  Avg Win:     6.74  |  Avg Loss: 5.62
  Expectancy:  1.01 por trade
  PF:          1.39
  Max DD:      37.12 (3.7%)
  Avg Bars:    10 velas
  Regímenes:   {'TREND': 23, 'BULL_TREND': 53, 'BEAR_TREND': 19}
  Señales:     {'SELL': 20, 'BUY': 75}
  Bloqueos principales:
      41x  Cooldown por activo (6h)
       3x  Volatilidad no válida: Volatilidad demasiado comprimida
       1x  ADX insuficiente para sniper: 21.94 < 22.0 | Score final insuficiente para sniper: 54.96 <
       1x  ADX insuficiente para sniper: 21.59 < 22.0 | Score final insuficiente para sniper: 54.75 <
       1x  ADX insuficiente para sniper: 20.79 < 22.0 | Score final insuficiente para sniper: 54.24 <

--- NVDA TEST ---
  ============================================================
  NVDA | TEST | Bars: 1132
  ============================================================
  Capital:     1000.00 → 1083.58  (+83.58)
  Señales:     62 generadas | 40 ALLOW | 22 BLOCK
  Trades:      40 cerrados | 25 wins | 15 losses
  Winrate:     62.5%
  Avg Trade:   2.09
  Avg Win:     6.57  |  Avg Loss: 5.37
  Expectancy:  2.09 por trade
  PF:          2.04
  Max DD:      17.89 (1.8%)
  Avg Bars:    11 velas
  Regímenes:   {'BEAR_TREND': 6, 'BULL_TREND': 24, 'TREND': 10}
  Señales:     {'SELL': 8, 'BUY': 32}
  Bloqueos principales:
      16x  Cooldown por activo (6h)
       1x  ADX insuficiente para sniper: 20.82 < 22.0 | Score final insuficiente para sniper: 54.26 <
       1x  ADX insuficiente para sniper: 20.90 < 22.0 | Score final insuficiente para sniper: 54.31 <
       1x  ADX insuficiente para sniper: 20.41 < 22.0 | Score final insuficiente para sniper: 54.01 <
       1x  ADX insuficiente para sniper: 21.79 < 22.0 | Score final insuficiente para sniper: 54.87 <

--- AMZN TRAIN ---
  ============================================================
  AMZN | TRAIN | Bars: 2440
  ============================================================
  Capital:     1000.00 → 1031.55  (+31.55)
  Señales:     166 generadas | 96 ALLOW | 70 BLOCK
  Trades:      95 cerrados | 45 wins | 50 losses
  Winrate:     47.4%
  Avg Trade:   0.33
  Avg Win:     7.35  |  Avg Loss: 5.98
  Expectancy:  0.33 por trade
  PF:          1.11
  Max DD:      70.23 (7.0%)
  Avg Bars:    12 velas
  Regímenes:   {'BULL_TREND': 52, 'BEAR_TREND': 19, 'TREND': 24}
  Señales:     {'BUY': 68, 'SELL': 27}
  Bloqueos principales:
      40x  Cooldown por activo (6h)
       8x  Volatilidad no válida: Volatilidad demasiado comprimida
       1x  ADX insuficiente para sniper: 21.50 < 22.0 | Score final insuficiente para sniper: 54.69 <
       1x  ADX insuficiente para sniper: 20.18 < 22.0 | Score final insuficiente para sniper: 53.86 <
       1x  ADX insuficiente para sniper: 20.15 < 22.0 | Score final insuficiente para sniper: 53.84 <

--- AMZN TEST ---
  ============================================================
  AMZN | TEST | Bars: 1132
  ============================================================
  Capital:     1000.00 → 989.93  (-10.07)
  Señales:     52 generadas | 34 ALLOW | 18 BLOCK
  Trades:      34 cerrados | 15 wins | 19 losses
  Winrate:     44.1%
  Avg Trade:   -0.30
  Avg Win:     6.48  |  Avg Loss: 5.64
  Expectancy:  -0.30 por trade
  PF:          0.91
  Max DD:      39.42 (3.9%)
  Avg Bars:    13 velas
  Regímenes:   {'BEAR_TREND': 12, 'BULL_TREND': 14, 'TREND': 8}
  Señales:     {'SELL': 14, 'BUY': 20}
  Bloqueos principales:
       9x  Cooldown por activo (6h)
       3x  Volatilidad no válida: Volatilidad demasiado comprimida
       1x  ADX insuficiente para sniper: 21.56 < 22.0 | Score final insuficiente para sniper: 54.72 <
       1x  ADX insuficiente para sniper: 20.63 < 22.0 | Score final insuficiente para sniper: 54.14 <
       1x  ADX insuficiente para sniper: 20.23 < 22.0 | Score final insuficiente para sniper: 53.89 <

--- META TRAIN ---
  ============================================================
  META | TRAIN | Bars: 2347
  ============================================================
  Capital:     1000.00 → 1012.85  (+12.85)
  Señales:     120 generadas | 84 ALLOW | 36 BLOCK
  Trades:      83 cerrados | 38 wins | 45 losses
  Winrate:     45.8%
  Avg Trade:   0.16
  Avg Win:     6.70  |  Avg Loss: 5.37
  Expectancy:  0.16 por trade
  PF:          1.05
  Max DD:      52.01 (5.2%)
  Avg Bars:    12 velas
  Regímenes:   {'BULL_TREND': 49, 'BEAR_TREND': 21, 'TREND': 13}
  Señales:     {'BUY': 62, 'SELL': 21}
  Bloqueos principales:
      24x  Cooldown por activo (6h)
       2x  ADX insuficiente para sniper: 20.42 < 22.0 | Score final insuficiente para sniper: 54.01 <
       1x  ADX insuficiente para sniper: 20.81 < 22.0 | Score final insuficiente para sniper: 54.26 <
       1x  ADX insuficiente para sniper: 20.34 < 22.0 | Score final insuficiente para sniper: 53.96 <
       1x  ADX insuficiente para sniper: 21.96 < 22.0 | Score final insuficiente para sniper: 54.97 <

--- META TEST ---
  ============================================================
  META | TEST | Bars: 1092
  ============================================================
  Capital:     1000.00 → 1061.39  (+61.39)
  Señales:     63 generadas | 44 ALLOW | 19 BLOCK
  Trades:      43 cerrados | 23 wins | 20 losses
  Winrate:     53.5%
  Avg Trade:   1.43
  Avg Win:     7.77  |  Avg Loss: 5.86
  Expectancy:  1.43 por trade
  PF:          1.52
  Max DD:      48.41 (4.8%)
  Avg Bars:    13 velas
  Regímenes:   {'BEAR_TREND': 9, 'BULL_TREND': 26, 'TREND': 8}
  Señales:     {'SELL': 11, 'BUY': 32}
  Bloqueos principales:
      17x  Cooldown por activo (6h)
       1x  ADX insuficiente para sniper: 20.71 < 22.0 | Score final insuficiente para sniper: 54.19 <
       1x  ADX insuficiente para sniper: 21.91 < 22.0 | Score final insuficiente para sniper: 54.94 <


#################################################################
  CONSOLIDADO TRAIN (IN-SAMPLE) — 4 activos
#################################################################
  Señales:     569 generadas | 351 ALLOW | 218 BLOCK
  Trades:      348 cerrados | 168 wins | 180 losses
  Winrate:     48.3%
  Avg Trade:   0.37
  Avg Win:     6.76  |  Avg Loss: 5.59
  Expectancy:  0.37 por trade
  PF:          1.13
  PnL total:   +129.04
  Peor DD:     70.23
  -------------------------------------------------------------
  Suma PnL trades:  +129.15   (debe cuadrar con PnL total)
  ✅ Cuadra (dif. 0.11, son costes de trades aún abiertos)
#################################################################

  VEREDICTO:
  🟡  Edge marginal. Positivo pero débil.


#################################################################
  CONSOLIDADO TEST (OUT-OF-SAMPLE) — 4 activos
#################################################################
  Señales:     228 generadas | 148 ALLOW | 80 BLOCK
  Trades:      147 cerrados | 71 wins | 76 losses
  Winrate:     48.3%
  Avg Trade:   0.44
  Avg Win:     6.84  |  Avg Loss: 5.55
  Expectancy:  0.44 por trade
  PF:          1.15
  PnL total:   +64.29
  Peor DD:     74.11
  -------------------------------------------------------------
  Suma PnL trades:  +64.35   (debe cuadrar con PnL total)
  ✅ Cuadra (dif. 0.05, son costes de trades aún abiertos)
#################################################################

  VEREDICTO:
  🟡  Edge marginal. Positivo pero débil.


=================================================================
  COMPARACIÓN TRAIN vs TEST
=================================================================

  IWM:
    TRAIN: 75 trades | WR 45.3% | PF 0.95 | Exp -0.16
    TEST:  30 trades | WR 26.7% | PF 0.39 | Exp -2.35
    ⚠️  Degradación significativa train→test

  NVDA:
    TRAIN: 95 trades | WR 53.7% | PF 1.39 | Exp 1.01
    TEST:  40 trades | WR 62.5% | PF 2.04 | Exp 2.09
    ✅  Consistente entre train y test

  AMZN:
    TRAIN: 95 trades | WR 47.4% | PF 1.11 | Exp 0.33
    TEST:  34 trades | WR 44.1% | PF 0.91 | Exp -0.30
    🟡  Degradación moderada

  META:
    TRAIN: 83 trades | WR 45.8% | PF 1.05 | Exp 0.16
    TEST:  43 trades | WR 53.5% | PF 1.52 | Exp 1.43
    ✅  Consistente entre train y test


=================================================================
  BACKTEST COMPLETO
=================================================================

```

## Robustez (intradia)
```
==============================================================
ANÁLISIS DE ROBUSTEZ — SHARK V15
==============================================================
Timeframe: 30m | Periodo: 60d
Activos: ['IWM', 'NVDA', 'AMZN', 'META']
Config actual: SL 2.0 ATR / TP 2.5 ATR
Bootstrap: 10000 | Monte Carlo: 5000

Descargando 30m / 60d ...
  IWM     yfinance      780 velas
  NVDA    yfinance      780 velas
  AMZN    yfinance      780 velas
  META    yfinance      780 velas

Operaciones totales con la config actual: 65

==============================================================
1) BOOTSTRAP DE LA EXPECTATIVA
==============================================================
Operaciones:            65
Expectativa observada:  +0.0940 € por operación
Intervalo 90%:          -1.2405  a  +1.4619
Prob. expectativa > 0:  55.0%

LECTURA: INDECISO. El cero está dentro del intervalo, así que
         esta muestra no distingue la estrategia de una moneda.
         No significa que no funcione: significa que todavía no
         se sabe. La única cura es más operaciones.

==============================================================
2) MONTE CARLO DE LA CURVA DE CAPITAL
==============================================================
Capital inicial:   1000.00 €
Operaciones:       65

A) MISMAS OPERACIONES, OTRO ORDEN
   (el capital final no cambia al barajar; solo el camino)
   Drawdown mediano:        4.95%
   Drawdown percentil 95:   7.47%
   Peor drawdown simulado:  12.94%
   Capital final (fijo):    1006.11 €

B) REMUESTREO: si las próximas operaciones salieran de
   esta misma distribución
   Capital final, percentil 5:   919.06 €
   Capital final, mediana:       1007.01 €
   Capital final, percentil 95:  1093.62 €
   Drawdown percentil 95:        10.55%
   Prob. terminar en pérdida:    44.7%
   Prob. perder la mitad:        0.0%

LECTURA: el drawdown que hay que estar dispuesto a aguantar es
         del 7.5%, no el que salió en el histórico: el orden
         de las operaciones es azar y la racha mala no tiene por
         qué haber caído dentro del periodo de prueba.
         El remuestreo da 45% de probabilidad de acabar
         en pérdida sobre otras 65 operaciones.

==============================================================
3) BARRIDO DE PARÁMETROS (SL / TP)
==============================================================

   SL    TP   R:R   OPS    WR%    EXPECT     PF  VEREDICTO
--------------------------------------------------------------
  1.5   2.0  1.33    79   40.5   -1.6435   0.60
  1.5   2.5  1.67    74   36.5   -1.5776   0.64
  1.5   3.0  2.00    71   33.8   -1.4328   0.70
  1.5   3.5  2.33    70   31.4   -1.3677   0.73
  2.0   2.0  1.00    73   53.4   -0.3420   0.89
  2.0   2.5  1.25    65   52.3 +  0.0940   1.03 <-- CONFIG ACTUAL
  2.0   3.0  1.50    61   50.8 +  0.6390   1.19
  2.0   3.5  1.75    63   39.7   -0.4942   0.88
  2.5   2.0  0.80    72   56.9   -0.1130   0.96
  2.5   2.5  1.00    65   55.4 +  0.2564   1.10
  2.5   3.0  1.20    61   52.5 +  0.4209   1.15
  2.5   3.5  1.40    61   41.0   -0.6162   0.83
  3.0   2.0  0.67    67   62.7 +  0.0529   1.02
  3.0   2.5  0.83    60   61.7 +  0.4464   1.20
  3.0   3.0  1.00    59   55.9 +  0.3141   1.12
  3.0   3.5  1.17    55   49.1   -0.0679   0.98

Combinaciones con expectativa positiva: 7 de 16
Configuración actual (SL 2.0 / TP 2.5): expectativa +0.0940, PF 1.03
Vecinos inmediatos con expectativa positiva: 3 de 8

LECTURA: ZONA MIXTA. Ni pico ni meseta clara. Con esta muestra
         no se puede separar señal de ruido.

==============================================================
4) ECONOMÍA REAL: ¿QUÉ SIGNIFICA ESTO EN DINERO?
==============================================================
Periodo cubierto:       0.2 años
Operaciones:            65  ->  273.0 al año
Riesgo por operación:   5.00 € (0.5% de 1000 €)
Expectativa en riesgo:  +0.019 R por operación

RENTABILIDAD ANUAL SOBRE 1000 €
  pesimista (p05)  :  -338.65 €/año  =  -33.87% anual
  central          :   +25.67 €/año  =   +2.57% anual
  optimista (p95)  :  +399.10 €/año  =  +39.91% anual

CAPITAL NECESARIO PARA SACAR 1.000 €/MES (12.000 €/año)
  pesimista (p05)  : imposible, la expectativa es negativa
  central          :        467,471 €
  optimista (p95)  :         30,068 €

LECTURA: 2.6% anual. Eso está por debajo de lo que
         da un índice sin hacer nada, y muy por debajo de lo que
         haría falta para vivir de esto con una cuenta pequeña.
         El cuello de botella no es el código ni los filtros:
         son 273 operaciones al año con una ventaja de
         0.019 R. Para cambiarlo hace falta más
         ventaja por operación o muchas más operaciones, y subir
         el riesgo solo multiplica también las pérdidas.

JSON escrito en resultados/robustez_30m.json

==============================================================
```

## Proveedores de datos
```
PRUEBA DE PROVEEDORES — cada uno por separado
Cascada por defecto: ['yfinance', 'finnhub', 'alpha_vantage', 'twelve_data']

  OK    yfinance   SPY         3772 velas  2011-11-07 -> 2026-11-06
  FALLA stooq      SPY       ValueError: No se pudo descargar SPY con ningún provider. Detalles: ['stooq: Stooq
  OK    yfinance   BTC-USD     4435 velas  2014-09-17 -> 2026-11-07
  OK    coinbase   BTC-USD     4129 velas  2015-07-20 -> 2026-11-07
  FALLA stooq      GLD       ValueError: No se pudo descargar GLD con ningún provider. Detalles: ['stooq: Stooq

CRUCE yfinance vs stooq en SPY (ultimos cierres comunes)
  no se pudo cruzar: ValueError: No se pudo descargar SPY con ningún provider. Detalles: ['stooq: Stooq no sirvio spy.us: https://stooq.com/q/d/l/: sin datos (<!DOCTYPE html><html><head><meta charset="utf-8"><meta name=) | https://stooq.pl/q/d/l/: sin datos (<!DOCTYPE html><html><head><meta charset="utf-8"><meta name=)']
```

## Medicion v2 (motor corregido)

El registro de la familia se escribe ANTES de calcular.
Familia de 4 hipotesis con correccion de Holm. Universo
de supervivientes, estado EXPLORATORIO.

Potencia medida: un diferencial de +0,72%/ano se detecta
el 12% de las veces. Por debajo de ~3-4% anual, un "no
rechaza" significa indetectable, no inexistente.

```
========================================================================
MEDICION CON EL MOTOR CORREGIDO
========================================================================
Registro escrito ANTES de calcular: hash 2398e570551e8dc3
Commit: 3bb3865506ff-sucio
Estado: EXPLORATORIO  |  universo: EXPLORATORY_SURVIVOR_UNIVERSE
Familia declarada: 4 hipotesis
  - multiactivo/M03: M03_momentum_12_1 vs comprar_y_mantener
  - multiactivo/M02: M02_tendencia vs comprar_y_mantener
  - renta_variable/M03: M03_momentum_12_1 vs comprar_y_mantener
  - renta_variable/M02: M02_tendencia vs comprar_y_mantener

Lo que este montaje PUEDE concluir:
  tasa de falso positivo medida: 7,5% (nominal 5%)
  potencia para +0,72%/ano: 12%   para +3,66%/ano: 60%
  -> por debajo de ~3-4% anual, un 'no rechaza' solo significa
     que la muestra no lo distingue de la suerte

========================================================================
DATOS
========================================================================
  cargados 31/31 activos
  referencia de efectivo (BIL): OK

  Universo congelado el 2026-10-19, 32 instrumentos
  Comprobado el 2026-10-20: 32 con datos (100.0%)
  panel guardado: 120640 filas, 2011-10-20 -> 2026-10-19, hash 2c25603a71b6b2ff

========================================================================
UNIVERSO: multiactivo  (31 activos)
========================================================================
  calentamiento hasta 2012-10-22, 168 decisiones mensuales

  ESTRATEGIA                     CAGR  SHARPE  MAXDD-D   ROT/A  INTENC
  --------------------------------------------------------------------
  comprar_y_mantener            9.05%    0.77   -27.1%    0.07      31
  rebalanceo_equiponderado      6.67%    0.73   -23.8%    0.63    5208
  M03_momentum_12_1            10.38%    0.65   -32.2%   12.54    1050
  M02_tendencia                 6.51%    0.65   -25.0%    6.19    3515

========================================================================
UNIVERSO: renta_variable  (14 activos)
========================================================================
  calentamiento hasta 2012-10-22, 168 decisiones mensuales

  ESTRATEGIA                     CAGR  SHARPE  MAXDD-D   ROT/A  INTENC
  --------------------------------------------------------------------
  comprar_y_mantener           13.75%    0.86   -35.0%    0.07      14
  rebalanceo_equiponderado     13.42%    0.86   -36.5%    0.81    2352
  M03_momentum_12_1            13.76%    0.85   -30.5%   14.48     967
  M02_tendencia                12.80%    0.84   -32.3%   10.43    2000

========================================================================
INFERENCIA (al final, sobre la familia declarada)
========================================================================
  multiactivo/M03          CAGR +10.38% vs  +9.05%  dif +1.33 pts  p=0.2799
  multiactivo/M02          CAGR  +6.51% vs  +9.05%  dif -2.54 pts  p=0.9158
  renta_variable/M03       CAGR +13.76% vs +13.75%  dif +0.01 pts  p=0.5341
  renta_variable/M02       CAGR +12.80% vs +13.75%  dif -0.95 pts  p=0.9186

  CORRECCION DE HOLM sobre 4 hipotesis, error familiar 0.05
    multiactivo/M03          p=0.279944  umbral=0.01250  -> no rechaza
    renta_variable/M03       p=0.534093  umbral=0.01667  -> no rechaza
    multiactivo/M02          p=0.915817  umbral=0.02500  -> no rechaza
    renta_variable/M02       p=0.918616  umbral=0.05000  -> no rechaza

========================================================================
M04 BASICO: que cuesta limitar la cartera
========================================================================

  VARIANTE             CAGR  SHARPE  MAXDD-D  INVERT  RECORTES
  --------------------------------------------------------------
  sin_limites        10.38%    0.65   -32.2%   1.000    0/168 
  i25_g40             6.71%    0.61   -21.4%   0.803  155/168 
  i25_g40_e90         6.60%    0.61   -21.4%   0.803  168/168 

  el tope por grupo cuesta -3.67 puntos de CAGR y reduce la caida maxima en 10.8 puntos
  I29: mas control, menos dinero. Es una preferencia, no una mejora del beneficio.
  Y el diagnostico que importa: recortar 155 de 168 decisiones significa que
  M03 estaba casi siempre con sus 5 posiciones en el mismo grupo.

========================================================================
SESGO DE SUPERVIVENCIA, POR ESCENARIOS DECLARADOS
========================================================================
  No es una correccion del sesgo: es cuanto se moveria el
  resultado SI el mundo hubiera sido como cada escenario dice.

  base (solo supervivientes): diferencial +1.33 pts

  ESCENARIO/FORMA                   DIF   CAMBIO  %SEL.MUERTA
  ------------------------------------------------------------
  leve/colapso                   +1.42%   +0.09         8.5%
  moderado/colapso               +2.73%   +1.39        15.9%
  severo/colapso                 +3.40%   +2.07        17.2%
  leve/desvanecimiento           +1.40%   +0.07         2.0%
  moderado/desvanecimiento       +3.25%   +1.92         2.1%
  severo/desvanecimiento         +3.38%   +2.04         0.5%

  cambio en el diferencial: de +0.07 a +2.07 puntos
  favorecia a la estrategia en TODOS los escenarios: False
  favorecia a la referencia en TODOS: True

========================================================================
CONCLUSION
========================================================================
NINGUNA hipotesis rechaza la nula tras corregir por familia.
Con la potencia medida, eso significa que esta muestra no
distingue estas estrategias de su referencia, no que no haya
ventaja. Son dos afirmaciones distintas y solo la primera
esta respaldada.

Artefactos en resultados/v2/
```

## Experimento institucional (M02/M03 como estrategias propias)

Solo largos: la cuenta es al contado, sin CFD.
Criterios fijados ANTES de ver el resultado: batir a
comprar y mantener del mismo universo, batir al efectivo,
y sostenerse en train y test por separado.

```
======================================================================
M02 / M03 COMO ESTRATEGIAS PROPIAS — SOLO LARGOS, MENSUAL
======================================================================
Periodo 15y | coste 8 pb por pata
Lookback 252 | skip 21 | K 5
Solo largos: la cuenta es al contado, sin CFD. No hay cortos.

Cargados 31/31 activos ajustados

======================================================================
multiactivo_sin_cripto  (31 activos)
======================================================================

VARIANTE                  ANUAL  SHARPE    MAXDD   EXPOS   ROT/A    FINAL
----------------------------------------------------------------------
comprar_y_mantener        6.16%    0.71   -16.6%   93.3%    0.07    2.429
M02_tendencia             5.87%    0.62   -22.3%   93.3%    3.78    2.334
M03_momentum_12_1         9.22%    0.57   -27.2%   93.3%    5.83    3.708
M02_mas_M03               9.11%    0.56   -27.9%   93.3%    5.79    3.649
M03_con_banda             8.53%    0.59   -24.5%   84.1%    5.26    3.374
efectivo (BIL)            1.53%            -0.4%
cuenta sin remunerar      0.00%   (lo que de verdad cobra la cuenta: 0%)

  CRITERIOS REGISTRADOS
  corte train/test: 2020-11-04

  M02_tendencia
    anual +5.87%  vs comprar y mantener +6.16%  -> NO bate
    train: +5.08% vs +3.68%  -> bate
    test : +4.50% vs +6.61%  -> NO bate
    VEREDICTO: NO PASA: forma peor de estar invertido

  M03_momentum_12_1
    anual +9.22%  vs comprar y mantener +6.16%  -> bate
    train: +6.70% vs +3.68%  -> bate
    test : +10.68% vs +6.61%  -> bate
    VEREDICTO: PASA

  M02_mas_M03
    anual +9.11%  vs comprar y mantener +6.16%  -> bate
    train: +6.49% vs +3.68%  -> bate
    test : +10.69% vs +6.61%  -> bate
    VEREDICTO: PASA

======================================================================
clase_renta_variable  (14 activos)
======================================================================

VARIANTE                  ANUAL  SHARPE    MAXDD   EXPOS   ROT/A    FINAL
----------------------------------------------------------------------
comprar_y_mantener       12.50%    0.91   -23.3%   93.3%    0.07    5.750
M02_tendencia            12.21%    0.93   -19.1%   93.3%    3.69    5.535
M03_momentum_12_1        12.86%    0.99   -16.0%   93.3%    4.79    6.034
M02_mas_M03              12.98%    0.97   -16.0%   93.3%    4.91    6.129
M03_con_banda            12.13%    1.00   -14.4%   86.4%    4.35    5.476
efectivo (BIL)            1.53%            -0.4%
cuenta sin remunerar      0.00%   (lo que de verdad cobra la cuenta: 0%)

  CRITERIOS REGISTRADOS
  corte train/test: 2020-11-04

  M02_tendencia
    anual +12.21%  vs comprar y mantener +12.50%  -> NO bate
    train: +11.06% vs +11.08%  -> NO bate
    test : +9.46% vs +9.15%  -> bate
    VEREDICTO: NO PASA: forma peor de estar invertido
    I29: mejor Sharpe (0.93 vs 0.91) pero MENOS dinero. No es una mejora del beneficio.

  M03_momentum_12_1
    anual +12.86%  vs comprar y mantener +12.50%  -> bate
    train: +12.61% vs +11.08%  -> bate
    test : +9.66% vs +9.15%  -> bate
    VEREDICTO: PASA

  M02_mas_M03
    anual +12.98%  vs comprar y mantener +12.50%  -> bate
    train: +12.68% vs +11.08%  -> bate
    test : +9.86% vs +9.15%  -> bate
    VEREDICTO: PASA

======================================================================
clase_materias_primas  (7 activos)
======================================================================

VARIANTE                  ANUAL  SHARPE    MAXDD   EXPOS   ROT/A    FINAL
----------------------------------------------------------------------
comprar_y_mantener        0.46%    0.03   -60.1%   93.3%    0.07    1.070
M02_tendencia            -1.61%   -0.08   -68.5%   83.3%    5.49    0.786
M03_momentum_12_1         0.08%    0.00   -56.9%   82.2%    4.70    1.013
M02_mas_M03              -1.04%   -0.05   -65.9%   80.6%    4.87    0.857
M03_con_banda             0.45%    0.03   -55.8%   80.2%    4.27    1.070
efectivo (BIL)            1.53%            -0.4%
cuenta sin remunerar      0.00%   (lo que de verdad cobra la cuenta: 0%)

  CRITERIOS REGISTRADOS
  corte train/test: 2020-11-04

  M02_tendencia
    anual -1.61%  vs comprar y mantener +0.46%  -> NO bate
    train: -9.73% vs -7.89%  -> NO bate
    test : +9.43% vs +10.00%  -> NO bate
    VEREDICTO: NO PASA: forma peor de estar invertido

  M03_momentum_12_1
    anual +0.08%  vs comprar y mantener +0.46%  -> NO bate
    train: -6.02% vs -7.89%  -> bate
    test : +8.78% vs +10.00%  -> NO bate
    VEREDICTO: NO PASA: forma peor de estar invertido

  M02_mas_M03
    anual -1.04%  vs comprar y mantener +0.46%  -> NO bate
    train: -8.05% vs -7.89%  -> NO bate
    test : +9.26% vs +10.00%  -> NO bate
    VEREDICTO: NO PASA: forma peor de estar invertido

======================================================================
clase_bonos  (5 activos)
======================================================================

VARIANTE                  ANUAL  SHARPE    MAXDD   EXPOS   ROT/A    FINAL
----------------------------------------------------------------------
comprar_y_mantener        1.76%    0.30   -20.5%   93.3%    0.07    1.295
M02_tendencia             1.83%    0.41   -10.3%   81.1%    3.53    1.309
M03_momentum_12_1         1.36%    0.26   -17.9%   85.6%    3.21    1.221
M02_mas_M03               1.70%    0.38   -10.4%   80.6%    4.19    1.285
M03_con_banda             1.40%    0.28   -17.6%   83.4%    2.90    1.229
efectivo (BIL)            1.53%            -0.4%
cuenta sin remunerar      0.00%   (lo que de verdad cobra la cuenta: 0%)

  CRITERIOS REGISTRADOS
  corte train/test: 2020-11-04

  M02_tendencia
    anual +1.83%  vs comprar y mantener +1.76%  -> bate
    train: +2.91% vs +3.64%  -> NO bate
    test : +0.67% vs -0.89%  -> bate
    VEREDICTO: INCONCLUSO: no se sostiene en las dos mitades

  M03_momentum_12_1
    anual +1.36%  vs comprar y mantener +1.76%  -> NO bate
    train: +2.96% vs +3.64%  -> NO bate
    test : -0.46% vs -0.89%  -> bate
    VEREDICTO: NO PASA: forma peor de estar invertido

  M02_mas_M03
    anual +1.70%  vs comprar y mantener +1.76%  -> NO bate
    train: +2.66% vs +3.64%  -> NO bate
    test : +0.67% vs -0.89%  -> bate
    VEREDICTO: NO PASA: forma peor de estar invertido
    I29: mejor Sharpe (0.38 vs 0.30) pero MENOS dinero. No es una mejora del beneficio.

======================================================================
clase_divisas  (5 activos)
======================================================================

VARIANTE                  ANUAL  SHARPE    MAXDD   EXPOS   ROT/A    FINAL
----------------------------------------------------------------------
comprar_y_mantener       -0.51%   -0.13   -19.2%   93.3%    0.07    0.927
M02_tendencia            -0.05%   -0.01   -15.0%   93.3%    5.04    0.993
M03_momentum_12_1        -0.35%   -0.06   -15.6%   93.3%    4.04    0.950
M02_mas_M03              -0.68%   -0.10   -20.7%   92.8%    4.81    0.904
M03_con_banda            -0.35%   -0.06   -15.1%   91.3%    3.77    0.949
efectivo (BIL)            1.53%            -0.4%
cuenta sin remunerar      0.00%   (lo que de verdad cobra la cuenta: 0%)

  CRITERIOS REGISTRADOS
  corte train/test: 2020-11-04

  M02_tendencia
    anual -0.05%  vs comprar y mantener -0.51%  -> bate
    train: +0.44% vs -1.06%  -> bate
    test : -0.31% vs +0.63%  -> NO bate
    VEREDICTO: NO PASA: por debajo del efectivo

  M03_momentum_12_1
    anual -0.35%  vs comprar y mantener -0.51%  -> bate
    train: -0.74% vs -1.06%  -> bate
    test : +1.05% vs +0.63%  -> bate
    VEREDICTO: NO PASA: por debajo del efectivo

  M02_mas_M03
    anual -0.68%  vs comprar y mantener -0.51%  -> NO bate
    train: -0.41% vs -1.06%  -> bate
    test : -0.31% vs +0.63%  -> NO bate
    VEREDICTO: NO PASA: forma peor de estar invertido
    I29: mejor Sharpe (-0.10 vs -0.13) pero MENOS dinero. No es una mejora del beneficio.

======================================================================
cripto_sesgo_extremo  (2 activos)
======================================================================

VARIANTE                  ANUAL  SHARPE    MAXDD   EXPOS   ROT/A    FINAL
----------------------------------------------------------------------
comprar_y_mantener       61.21%    0.83   -81.3%   94.5%    0.17  310.929
M02_tendencia            52.22%    0.83   -66.3%   69.9%    1.66  156.070
M03_momentum_12_1        51.59%    0.80   -79.8%   69.9%    2.33  148.482
M02_mas_M03              50.56%    0.84   -64.8%   63.0%    1.83  136.758
M03_con_banda            50.58%    0.81   -78.7%   68.3%    2.24  136.997
efectivo (BIL)            1.53%            -0.4%
cuenta sin remunerar      0.00%   (lo que de verdad cobra la cuenta: 0%)

  CRITERIOS REGISTRADOS
  corte train/test: 2021-12-30

  M02_tendencia
    anual +52.22%  vs comprar y mantener +61.21%  -> NO bate
    train: +97.91% vs +120.57%  -> NO bate
    test : +16.58% vs +23.68%  -> NO bate
    VEREDICTO: NO PASA: forma peor de estar invertido
    I29: mejor Sharpe (0.83 vs 0.83) pero MENOS dinero. No es una mejora del beneficio.

  M03_momentum_12_1
    anual +51.59%  vs comprar y mantener +61.21%  -> NO bate
    train: +102.68% vs +120.57%  -> NO bate
    test : +13.72% vs +23.68%  -> NO bate
    VEREDICTO: NO PASA: forma peor de estar invertido

  M02_mas_M03
    anual +50.56%  vs comprar y mantener +61.21%  -> NO bate
    train: +96.14% vs +120.57%  -> NO bate
    test : +16.60% vs +23.68%  -> NO bate
    VEREDICTO: NO PASA: forma peor de estar invertido
    I29: mejor Sharpe (0.84 vs 0.83) pero MENOS dinero. No es una mejora del beneficio.

======================================================================
AJUSTADO vs SIN AJUSTAR — cuanto cambia por dividendos y splits
======================================================================
  comprar_y_mantener       ajustado  +6.16%  sin ajustar  +4.67%  diferencia +1.49 puntos/ano
  M03_momentum_12_1        ajustado  +9.22%  sin ajustar  +7.13%  diferencia +2.10 puntos/ano

  Shark corre SIN ajustar. Esa diferencia es el sesgo que
  arrastran todos los backtests diarios largos hechos hasta hoy.

Guardado en resultados/institucional.json

======================================================================
RESUMEN
======================================================================
Pasan los criterios registrados: 4
  - multiactivo_sin_cripto/M03_momentum_12_1
  - multiactivo_sin_cripto/M02_mas_M03
  - clase_renta_variable/M03_momentum_12_1
  - clase_renta_variable/M02_mas_M03

OJO: que pasen los criterios NO autoriza capital. El
documento exige presupuesto explicito y el modo sigue en
OBSERVE. Esto es evidencia, no una decision.
```

