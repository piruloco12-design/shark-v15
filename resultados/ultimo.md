# Validacion SHARK V15

Fecha:   2026-10-21 07:50 UTC
Commit:  6b17b29f
Disparo: push

## Entorno
```
pandas   3.0.6
numpy    2.4.6
yfinance 1.7.0
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
  PASA       [V23] las comisiones mueven el PnL neto y el capital del core
  PASA       [V23b] la capacidad responde al efectivo disponible
  PASA       [V23c] el core llama al dimensionado declarando efectivo y coste

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

=== V24: reejecucion reproducible ===
  PASA       [V24] reejecucion: NAV identico al bit, sin tolerancia
  PASA       [V24b] reejecucion: mismas decisiones y mismos fills
  PASA       [V24c] reejecucion: mismo libro final y mismas metricas
  PASA       [V24d] la corrida comparada SI opera (si no, no prueba nada)

=== Puertas de cambios posteriores ===

======================================================================
PUERTAS: 45 pasan, 0 FALLAN, 0 pendientes de su cambio
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
        2026-07-28 09:30:00-04:00  ->  2026-10-20 15:30:00-04:00
NVDA    yfinance      780    60   13.0  [9, 10, 11, 12, 13, 14, 15]
        2026-07-28 09:30:00-04:00  ->  2026-10-20 15:30:00-04:00
AMZN    yfinance      780    60   13.0  [9, 10, 11, 12, 13, 14, 15]
        2026-07-28 09:30:00-04:00  ->  2026-10-20 15:30:00-04:00
META    yfinance      780    60   13.0  [9, 10, 11, 12, 13, 14, 15]
        2026-07-28 09:30:00-04:00  ->  2026-10-20 15:30:00-04:00
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
Capital:     1000.00 → 975.88  (-24.12)
Señales:     65 generadas | 14 ALLOW | 51 BLOCK
Trades:      14 cerrados | 6 wins | 8 losses
Winrate:     42.9%
Avg Trade:   -1.72
Avg Win:     6.02  |  Avg Loss: 7.53
Expectancy:  -1.72 por trade
PF:          0.60
Max DD:      36.07 (3.6%)
Avg Bars:    9 velas
Regímenes:   {'BULL_TREND': 1, 'TREND': 5, 'BEAR_TREND': 8}
Señales:     {'BUY': 2, 'SELL': 12}
Bloqueos principales:
    47x  Cooldown por activo (6h)
     1x  ADX insuficiente para sniper: 21.24 < 22.0 | Score final insuficiente para sniper: 54.53 <
     1x  ADX insuficiente para sniper: 20.99 < 22.0 | Score final insuficiente para sniper: 54.37 <
     1x  ADX insuficiente para sniper: 21.13 < 22.0 | Score final insuficiente para sniper: 54.46 <
     1x  ADX insuficiente para sniper: 20.88 < 22.0 | Score final insuficiente para sniper: 54.30 <

============================================================
NVDA | FULL | Bars: 580
============================================================
Capital:     1000.00 → 960.35  (-39.65)
Señales:     49 generadas | 18 ALLOW | 31 BLOCK
Trades:      18 cerrados | 7 wins | 11 losses
Winrate:     38.9%
Avg Trade:   -2.20
Avg Win:     6.02  |  Avg Loss: 7.44
Expectancy:  -2.20 por trade
PF:          0.52
Max DD:      48.42 (4.8%)
Avg Bars:    12 velas
Regímenes:   {'BEAR_TREND': 7, 'TREND': 5, 'BULL_TREND': 6}
Señales:     {'SELL': 9, 'BUY': 9}
Bloqueos principales:
    30x  Cooldown por activo (6h)
     1x  ADX insuficiente para sniper: 20.36 < 22.0 | Score final insuficiente para sniper: 53.97 <

============================================================
AMZN | FULL | Bars: 580
============================================================
Capital:     1000.00 → 1012.67  (+12.67)
Señales:     90 generadas | 18 ALLOW | 72 BLOCK
Trades:      17 cerrados | 10 wins | 7 losses
Winrate:     58.8%
Avg Trade:   0.76
Avg Win:     5.83  |  Avg Loss: 6.48
Expectancy:  0.76 por trade
PF:          1.29
Max DD:      25.60 (2.6%)
Avg Bars:    12 velas
Regímenes:   {'BULL_TREND': 4, 'BEAR_TREND': 8, 'TREND': 5}
Señales:     {'BUY': 6, 'SELL': 11}
Bloqueos principales:
    71x  Cooldown por activo (6h)
     1x  ADX insuficiente para sniper: 20.59 < 22.0 | Score final insuficiente para sniper: 54.12 <

============================================================
META | FULL | Bars: 580
============================================================
Capital:     1000.00 → 1018.48  (+18.48)
Señales:     62 generadas | 15 ALLOW | 47 BLOCK
Trades:      15 cerrados | 9 wins | 6 losses
Winrate:     60.0%
Avg Trade:   1.23
Avg Win:     5.82  |  Avg Loss: 5.65
Expectancy:  1.23 por trade
PF:          1.55
Max DD:      18.90 (1.9%)
Avg Bars:    13 velas
Regímenes:   {'BEAR_TREND': 5, 'BULL_TREND': 10}
Señales:     {'SELL': 5, 'BUY': 10}
Bloqueos principales:
    47x  Cooldown por activo (6h)


#################################################################
  CONSOLIDADO FULL PERIOD — 4 activos
#################################################################
  Señales:     266 generadas | 65 ALLOW | 201 BLOCK
  Trades:      64 cerrados | 32 wins | 32 losses
  Winrate:     50.0%
  Avg Trade:   -0.51
  Avg Win:     5.90  |  Avg Loss: 6.91
  Expectancy:  -0.51 por trade
  PF:          0.85
  PnL total:   -32.63
  Peor DD:     48.42
  -------------------------------------------------------------
  Suma PnL trades:  -32.33   (debe cuadrar con PnL total)
  ✅ Cuadra (dif. 0.29, son costes de trades aún abiertos)
#################################################################

  VEREDICTO:
  ❌  NO HAY EDGE. Expectancy negativa.


=================================================================
  FASE 2: WALK-FORWARD (70% train / 30% test)
=================================================================

--- IWM TRAIN ---
  ============================================================
  IWM | TRAIN | Bars: 346
  ============================================================
  Capital:     1000.00 → 973.97  (-26.03)
  Señales:     49 generadas | 10 ALLOW | 39 BLOCK
  Trades:      10 cerrados | 4 wins | 6 losses
  Winrate:     40.0%
  Avg Trade:   -2.60
  Avg Win:     5.48  |  Avg Loss: 7.99
  Expectancy:  -2.60 por trade
  PF:          0.46
  Max DD:      34.16 (3.4%)
  Avg Bars:    8 velas
  Regímenes:   {'BULL_TREND': 1, 'TREND': 2, 'BEAR_TREND': 7}
  Señales:     {'BUY': 2, 'SELL': 8}
  Bloqueos principales:
      36x  Cooldown por activo (6h)
       1x  ADX insuficiente para sniper: 21.24 < 22.0 | Score final insuficiente para sniper: 54.53 <
       1x  ADX insuficiente para sniper: 20.99 < 22.0 | Score final insuficiente para sniper: 54.37 <
       1x  ADX insuficiente para sniper: 21.13 < 22.0 | Score final insuficiente para sniper: 54.46 <

--- IWM TEST ---
  ============================================================
  IWM | TEST | Bars: 234
  ============================================================
  Capital:     1000.00 → 1001.96  (+1.96)
  Señales:     16 generadas | 4 ALLOW | 12 BLOCK
  Trades:      4 cerrados | 2 wins | 2 losses
  Winrate:     50.0%
  Avg Trade:   0.49
  Avg Win:     7.27  |  Avg Loss: 6.30
  Expectancy:  0.49 por trade
  PF:          1.16
  Max DD:      10.35 (1.0%)
  Avg Bars:    11 velas
  Regímenes:   {'TREND': 3, 'BEAR_TREND': 1}
  Señales:     {'SELL': 4}
  Bloqueos principales:
      11x  Cooldown por activo (6h)
       1x  ADX insuficiente para sniper: 20.88 < 22.0 | Score final insuficiente para sniper: 54.30 <

--- NVDA TRAIN ---
  ============================================================
  NVDA | TRAIN | Bars: 346
  ============================================================
  Capital:     1000.00 → 959.03  (-40.97)
  Señales:     29 generadas | 11 ALLOW | 18 BLOCK
  Trades:      10 cerrados | 3 wins | 7 losses
  Winrate:     30.0%
  Avg Trade:   -4.06
  Avg Win:     5.38  |  Avg Loss: 8.11
  Expectancy:  -4.06 por trade
  PF:          0.28
  Max DD:      48.42 (4.8%)
  Avg Bars:    11 velas
  Regímenes:   {'BEAR_TREND': 3, 'TREND': 2, 'BULL_TREND': 5}
  Señales:     {'SELL': 4, 'BUY': 6}
  Bloqueos principales:
      18x  Cooldown por activo (6h)

--- NVDA TEST ---
  ============================================================
  NVDA | TEST | Bars: 234
  ============================================================
  Capital:     1000.00 → 1005.66  (+5.66)
  Señales:     23 generadas | 8 ALLOW | 15 BLOCK
  Trades:      8 cerrados | 4 wins | 4 losses
  Winrate:     50.0%
  Avg Trade:   0.71
  Avg Win:     7.97  |  Avg Loss: 6.56
  Expectancy:  0.71 por trade
  PF:          1.22
  Max DD:      20.82 (2.1%)
  Avg Bars:    11 velas
  Regímenes:   {'BULL_TREND': 1, 'TREND': 3, 'BEAR_TREND': 4}
  Señales:     {'BUY': 3, 'SELL': 5}
  Bloqueos principales:
      13x  Cooldown por activo (6h)
       1x  ADX insuficiente para sniper: 21.76 < 22.0 | Score final insuficiente para sniper: 54.85 <
       1x  ADX insuficiente para sniper: 20.36 < 22.0 | Score final insuficiente para sniper: 53.97 <

--- AMZN TRAIN ---
  ============================================================
  AMZN | TRAIN | Bars: 346
  ============================================================
  Capital:     1000.00 → 1035.83  (+35.83)
  Señales:     56 generadas | 10 ALLOW | 46 BLOCK
  Trades:      10 cerrados | 8 wins | 2 losses
  Winrate:     80.0%
  Avg Trade:   3.58
  Avg Win:     5.90  |  Avg Loss: 5.68
  Expectancy:  3.58 por trade
  PF:          4.15
  Max DD:      13.42 (1.3%)
  Avg Bars:    10 velas
  Regímenes:   {'BULL_TREND': 1, 'BEAR_TREND': 6, 'TREND': 3}
  Señales:     {'BUY': 3, 'SELL': 7}
  Bloqueos principales:
      45x  Cooldown por activo (6h)
       1x  ADX insuficiente para sniper: 20.59 < 22.0 | Score final insuficiente para sniper: 54.12 <

--- AMZN TEST ---
  ============================================================
  AMZN | TEST | Bars: 234
  ============================================================
  Capital:     1000.00 → 977.65  (-22.35)
  Señales:     34 generadas | 8 ALLOW | 26 BLOCK
  Trades:      7 cerrados | 2 wins | 5 losses
  Winrate:     28.6%
  Avg Trade:   -3.15
  Avg Win:     5.37  |  Avg Loss: 6.56
  Expectancy:  -3.15 por trade
  PF:          0.33
  Max DD:      24.72 (2.5%)
  Avg Bars:    15 velas
  Regímenes:   {'TREND': 2, 'BEAR_TREND': 2, 'BULL_TREND': 3}
  Señales:     {'SELL': 4, 'BUY': 3}
  Bloqueos principales:
      26x  Cooldown por activo (6h)

--- META TRAIN ---
  ============================================================
  META | TRAIN | Bars: 346
  ============================================================
  Capital:     1000.00 → 1012.54  (+12.54)
  Señales:     38 generadas | 10 ALLOW | 28 BLOCK
  Trades:      10 cerrados | 6 wins | 4 losses
  Winrate:     60.0%
  Avg Trade:   1.25
  Avg Win:     5.82  |  Avg Loss: 5.59
  Expectancy:  1.25 por trade
  PF:          1.56
  Max DD:      18.90 (1.9%)
  Avg Bars:    11 velas
  Regímenes:   {'BEAR_TREND': 3, 'BULL_TREND': 7}
  Señales:     {'SELL': 3, 'BUY': 7}
  Bloqueos principales:
      28x  Cooldown por activo (6h)

--- META TEST ---
  ============================================================
  META | TEST | Bars: 234
  ============================================================
  Capital:     1000.00 → 1005.87  (+5.87)
  Señales:     24 generadas | 5 ALLOW | 19 BLOCK
  Trades:      5 cerrados | 3 wins | 2 losses
  Winrate:     60.0%
  Avg Trade:   1.17
  Avg Win:     5.76  |  Avg Loss: 5.70
  Expectancy:  1.17 por trade
  PF:          1.51
  Max DD:      11.28 (1.1%)
  Avg Bars:    17 velas
  Regímenes:   {'BULL_TREND': 3, 'BEAR_TREND': 2}
  Señales:     {'BUY': 3, 'SELL': 2}
  Bloqueos principales:
      19x  Cooldown por activo (6h)


#################################################################
  CONSOLIDADO TRAIN (IN-SAMPLE) — 4 activos
#################################################################
  Señales:     172 generadas | 41 ALLOW | 131 BLOCK
  Trades:      40 cerrados | 21 wins | 19 losses
  Winrate:     52.5%
  Avg Trade:   -0.46
  Avg Win:     5.72  |  Avg Loss: 7.29
  Expectancy:  -0.46 por trade
  PF:          0.87
  PnL total:   -18.64
  Peor DD:     48.42
  -------------------------------------------------------------
  Suma PnL trades:  -18.26   (debe cuadrar con PnL total)
  ✅ Cuadra (dif. 0.38, son costes de trades aún abiertos)
#################################################################

  VEREDICTO:
  ❌  NO HAY EDGE. Expectancy negativa.


#################################################################
  CONSOLIDADO TEST (OUT-OF-SAMPLE) — 4 activos
#################################################################
  Señales:     97 generadas | 25 ALLOW | 72 BLOCK
  Trades:      24 cerrados | 11 wins | 13 losses
  Winrate:     45.8%
  Avg Trade:   -0.36
  Avg Win:     6.77  |  Avg Loss: 6.39
  Expectancy:  -0.36 por trade
  PF:          0.90
  PnL total:   -8.87
  Peor DD:     24.72
  -------------------------------------------------------------
  Suma PnL trades:  -8.59   (debe cuadrar con PnL total)
  ✅ Cuadra (dif. 0.28, son costes de trades aún abiertos)
#################################################################

  VEREDICTO:
  ❌  NO HAY EDGE. Expectancy negativa.


=================================================================
  COMPARACIÓN TRAIN vs TEST
=================================================================

  IWM:
    TRAIN: 10 trades | WR 40.0% | PF 0.46 | Exp -2.60
    TEST:  4 trades | WR 50.0% | PF 1.16 | Exp 0.49
    ⚠️  Pocos trades para comparar

  NVDA:
    TRAIN: 10 trades | WR 30.0% | PF 0.28 | Exp -4.06
    TEST:  8 trades | WR 50.0% | PF 1.22 | Exp 0.71
    ✅  Consistente entre train y test

  AMZN:
    TRAIN: 10 trades | WR 80.0% | PF 4.15 | Exp 3.58
    TEST:  7 trades | WR 28.6% | PF 0.33 | Exp -3.15
    ⚠️  Degradación significativa train→test

  META:
    TRAIN: 10 trades | WR 60.0% | PF 1.56 | Exp 1.25
    TEST:  5 trades | WR 60.0% | PF 1.51 | Exp 1.17
    ⚠️  Pocos trades para comparar


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
  OK | yfinance | 3770 velas
Descargando NVDA...
  OK | yfinance | 3770 velas
Descargando AMZN...
  OK | yfinance | 3770 velas
Descargando META...
  OK | yfinance | 3626 velas

=================================================================
  FASE 1: BACKTEST COMPLETO (todo el período)
=================================================================

============================================================
IWM | FULL | Bars: 3570
============================================================
Capital:     1000.00 → 928.24  (-71.76)
Señales:     180 generadas | 104 ALLOW | 76 BLOCK
Trades:      103 cerrados | 42 wins | 61 losses
Winrate:     40.8%
Avg Trade:   -0.70
Avg Win:     6.02  |  Avg Loss: 5.32
Expectancy:  -0.70 por trade
PF:          0.78
Max DD:      106.35 (10.6%)
Avg Bars:    12 velas
Regímenes:   {'TREND': 29, 'BULL_TREND': 38, 'BEAR_TREND': 36}
Señales:     {'BUY': 54, 'SELL': 49}
Bloqueos principales:
    38x  Cooldown por activo (6h)
    14x  Volatilidad no válida: Volatilidad demasiado comprimida
     2x  ADX insuficiente para sniper: 21.78 < 22.0 | Score final insuficiente para sniper: 54.86 <
     1x  ADX insuficiente para sniper: 20.09 < 22.0 | Score final insuficiente para sniper: 53.80 <
     1x  ADX insuficiente para sniper: 21.29 < 22.0 | Score final insuficiente para sniper: 54.56 <

============================================================
NVDA | FULL | Bars: 3570
============================================================
Capital:     1000.00 → 1181.95  (+181.95)
Señales:     214 generadas | 136 ALLOW | 78 BLOCK
Trades:      136 cerrados | 76 wins | 60 losses
Winrate:     55.9%
Avg Trade:   1.34
Avg Win:     6.86  |  Avg Loss: 5.66
Expectancy:  1.34 por trade
PF:          1.54
Max DD:      36.93 (3.7%)
Avg Bars:    10 velas
Regímenes:   {'BULL_TREND': 78, 'TREND': 34, 'BEAR_TREND': 24}
Señales:     {'BUY': 108, 'SELL': 28}
Bloqueos principales:
    56x  Cooldown por activo (6h)
     3x  Volatilidad no válida: Volatilidad demasiado comprimida
     1x  ADX insuficiente para sniper: 21.94 < 22.0 | Score final insuficiente para sniper: 54.96 <
     1x  ADX insuficiente para sniper: 21.59 < 22.0 | Score final insuficiente para sniper: 54.75 <
     1x  ADX insuficiente para sniper: 20.79 < 22.0 | Score final insuficiente para sniper: 54.24 <

============================================================
AMZN | FULL | Bars: 3570
============================================================
Capital:     1000.00 → 1024.31  (+24.31)
Señales:     218 generadas | 131 ALLOW | 87 BLOCK
Trades:      131 cerrados | 61 wins | 70 losses
Winrate:     46.6%
Avg Trade:   0.19
Avg Win:     7.17  |  Avg Loss: 5.90
Expectancy:  0.19 por trade
PF:          1.06
Max DD:      83.42 (8.3%)
Avg Bars:    12 velas
Regímenes:   {'BULL_TREND': 66, 'BEAR_TREND': 32, 'TREND': 33}
Señales:     {'BUY': 88, 'SELL': 43}
Bloqueos principales:
    49x  Cooldown por activo (6h)
    11x  Volatilidad no válida: Volatilidad demasiado comprimida
     1x  ADX insuficiente para sniper: 20.18 < 22.0 | Score final insuficiente para sniper: 53.86 <
     1x  ADX insuficiente para sniper: 20.15 < 22.0 | Score final insuficiente para sniper: 53.84 <
     1x  ADX insuficiente para sniper: 20.87 < 22.0 | Score final insuficiente para sniper: 54.29 <

============================================================
META | FULL | Bars: 3426
============================================================
Capital:     1000.00 → 1069.66  (+69.66)
Señales:     182 generadas | 127 ALLOW | 55 BLOCK
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
  Señales:     794 generadas | 498 ALLOW | 296 BLOCK
  Trades:      497 cerrados | 240 wins | 257 losses
  Winrate:     48.3%
  Avg Trade:   0.41
  Avg Win:     6.86  |  Avg Loss: 5.61
  Expectancy:  0.41 por trade
  PF:          1.14
  PnL total:   +204.16
  Peor DD:     106.35
  -------------------------------------------------------------
  Suma PnL trades:  +204.30   (debe cuadrar con PnL total)
  ✅ Cuadra (dif. 0.14, son costes de trades aún abiertos)
#################################################################

  VEREDICTO:
  🟡  Edge marginal. Positivo pero débil.


=================================================================
  FASE 2: WALK-FORWARD (70% train / 30% test)
=================================================================

--- IWM TRAIN ---
  ============================================================
  IWM | TRAIN | Bars: 2439
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
  IWM | TEST | Bars: 1131
  ============================================================
  Capital:     1000.00 → 939.20  (-60.80)
  Señales:     50 generadas | 29 ALLOW | 21 BLOCK
  Trades:      28 cerrados | 8 wins | 20 losses
  Winrate:     28.6%
  Avg Trade:   -2.17
  Avg Win:     5.72  |  Avg Loss: 5.32
  Expectancy:  -2.17 por trade
  PF:          0.43
  Max DD:      74.11 (7.4%)
  Avg Bars:    13 velas
  Regímenes:   {'TREND': 10, 'BEAR_TREND': 8, 'BULL_TREND': 10}
  Señales:     {'SELL': 14, 'BUY': 14}
  Bloqueos principales:
      10x  Cooldown por activo (6h)
       1x  ADX insuficiente para sniper: 21.62 < 22.0 | Score final insuficiente para sniper: 54.76 <
       1x  ADX insuficiente para sniper: 20.92 < 22.0 | Score final insuficiente para sniper: 54.32 <
       1x  ADX insuficiente para sniper: 20.38 < 22.0 | Score final insuficiente para sniper: 53.99 <
       1x  ADX insuficiente para sniper: 20.19 < 22.0 | Score final insuficiente para sniper: 53.87 <

--- NVDA TRAIN ---
  ============================================================
  NVDA | TRAIN | Bars: 2439
  ============================================================
  Capital:     1000.00 → 1090.69  (+90.69)
  Señales:     154 generadas | 97 ALLOW | 57 BLOCK
  Trades:      96 cerrados | 51 wins | 45 losses
  Winrate:     53.1%
  Avg Trade:   0.95
  Avg Win:     6.70  |  Avg Loss: 5.58
  Expectancy:  0.95 por trade
  PF:          1.36
  Max DD:      36.93 (3.7%)
  Avg Bars:    10 velas
  Regímenes:   {'BULL_TREND': 54, 'TREND': 23, 'BEAR_TREND': 19}
  Señales:     {'BUY': 76, 'SELL': 20}
  Bloqueos principales:
      41x  Cooldown por activo (6h)
       3x  Volatilidad no válida: Volatilidad demasiado comprimida
       1x  ADX insuficiente para sniper: 21.94 < 22.0 | Score final insuficiente para sniper: 54.96 <
       1x  ADX insuficiente para sniper: 21.59 < 22.0 | Score final insuficiente para sniper: 54.75 <
       1x  ADX insuficiente para sniper: 20.79 < 22.0 | Score final insuficiente para sniper: 54.24 <

--- NVDA TEST ---
  ============================================================
  NVDA | TEST | Bars: 1131
  ============================================================
  Capital:     1000.00 → 1083.64  (+83.64)
  Señales:     61 generadas | 40 ALLOW | 21 BLOCK
  Trades:      40 cerrados | 25 wins | 15 losses
  Winrate:     62.5%
  Avg Trade:   2.09
  Avg Win:     6.59  |  Avg Loss: 5.41
  Expectancy:  2.09 por trade
  PF:          2.03
  Max DD:      18.00 (1.8%)
  Avg Bars:    11 velas
  Regímenes:   {'BEAR_TREND': 6, 'BULL_TREND': 24, 'TREND': 10}
  Señales:     {'SELL': 8, 'BUY': 32}
  Bloqueos principales:
      15x  Cooldown por activo (6h)
       1x  ADX insuficiente para sniper: 20.82 < 22.0 | Score final insuficiente para sniper: 54.26 <
       1x  ADX insuficiente para sniper: 20.90 < 22.0 | Score final insuficiente para sniper: 54.31 <
       1x  ADX insuficiente para sniper: 20.41 < 22.0 | Score final insuficiente para sniper: 54.01 <
       1x  ADX insuficiente para sniper: 21.79 < 22.0 | Score final insuficiente para sniper: 54.87 <

--- AMZN TRAIN ---
  ============================================================
  AMZN | TRAIN | Bars: 2439
  ============================================================
  Capital:     1000.00 → 1031.81  (+31.81)
  Señales:     164 generadas | 95 ALLOW | 69 BLOCK
  Trades:      95 cerrados | 45 wins | 50 losses
  Winrate:     47.4%
  Avg Trade:   0.33
  Avg Win:     7.35  |  Avg Loss: 5.98
  Expectancy:  0.33 por trade
  PF:          1.11
  Max DD:      69.59 (7.0%)
  Avg Bars:    12 velas
  Regímenes:   {'BULL_TREND': 52, 'BEAR_TREND': 18, 'TREND': 25}
  Señales:     {'BUY': 68, 'SELL': 27}
  Bloqueos principales:
      40x  Cooldown por activo (6h)
       8x  Volatilidad no válida: Volatilidad demasiado comprimida
       1x  ADX insuficiente para sniper: 20.18 < 22.0 | Score final insuficiente para sniper: 53.86 <
       1x  ADX insuficiente para sniper: 20.15 < 22.0 | Score final insuficiente para sniper: 53.84 <
       1x  ADX insuficiente para sniper: 20.87 < 22.0 | Score final insuficiente para sniper: 54.29 <

--- AMZN TEST ---
  ============================================================
  AMZN | TEST | Bars: 1131
  ============================================================
  Capital:     1000.00 → 992.73  (-7.27)
  Señales:     54 generadas | 36 ALLOW | 18 BLOCK
  Trades:      36 cerrados | 16 wins | 20 losses
  Winrate:     44.4%
  Avg Trade:   -0.20
  Avg Win:     6.48  |  Avg Loss: 5.54
  Expectancy:  -0.20 por trade
  PF:          0.93
  Max DD:      39.53 (4.0%)
  Avg Bars:    12 velas
  Regímenes:   {'BEAR_TREND': 14, 'BULL_TREND': 14, 'TREND': 8}
  Señales:     {'SELL': 16, 'BUY': 20}
  Bloqueos principales:
       9x  Cooldown por activo (6h)
       3x  Volatilidad no válida: Volatilidad demasiado comprimida
       1x  ADX insuficiente para sniper: 21.56 < 22.0 | Score final insuficiente para sniper: 54.72 <
       1x  ADX insuficiente para sniper: 20.63 < 22.0 | Score final insuficiente para sniper: 54.14 <
       1x  ADX insuficiente para sniper: 20.23 < 22.0 | Score final insuficiente para sniper: 53.89 <

--- META TRAIN ---
  ============================================================
  META | TRAIN | Bars: 2338
  ============================================================
  Capital:     1000.00 → 1012.88  (+12.88)
  Señales:     119 generadas | 83 ALLOW | 36 BLOCK
  Trades:      83 cerrados | 38 wins | 45 losses
  Winrate:     45.8%
  Avg Trade:   0.16
  Avg Win:     6.70  |  Avg Loss: 5.37
  Expectancy:  0.16 por trade
  PF:          1.05
  Max DD:      48.49 (4.8%)
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
  META | TEST | Bars: 1088
  ============================================================
  Capital:     1000.00 → 1056.06  (+56.06)
  Señales:     63 generadas | 44 ALLOW | 19 BLOCK
  Trades:      44 cerrados | 23 wins | 21 losses
  Winrate:     52.3%
  Avg Trade:   1.27
  Avg Win:     7.73  |  Avg Loss: 5.80
  Expectancy:  1.27 por trade
  PF:          1.46
  Max DD:      48.16 (4.8%)
  Avg Bars:    13 velas
  Regímenes:   {'BEAR_TREND': 10, 'BULL_TREND': 26, 'TREND': 8}
  Señales:     {'SELL': 12, 'BUY': 32}
  Bloqueos principales:
      17x  Cooldown por activo (6h)
       1x  ADX insuficiente para sniper: 20.71 < 22.0 | Score final insuficiente para sniper: 54.19 <
       1x  ADX insuficiente para sniper: 21.91 < 22.0 | Score final insuficiente para sniper: 54.94 <


#################################################################
  CONSOLIDADO TRAIN (IN-SAMPLE) — 4 activos
#################################################################
  Señales:     567 generadas | 350 ALLOW | 217 BLOCK
  Trades:      349 cerrados | 168 wins | 181 losses
  Winrate:     48.1%
  Avg Trade:   0.35
  Avg Win:     6.75  |  Avg Loss: 5.58
  Expectancy:  0.35 por trade
  PF:          1.12
  PnL total:   +123.71
  Peor DD:     69.59
  -------------------------------------------------------------
  Suma PnL trades:  +123.74   (debe cuadrar con PnL total)
  ✅ Cuadra (dif. 0.03, son costes de trades aún abiertos)
#################################################################

  VEREDICTO:
  🟡  Edge marginal. Positivo pero débil.


#################################################################
  CONSOLIDADO TEST (OUT-OF-SAMPLE) — 4 activos
#################################################################
  Señales:     228 generadas | 149 ALLOW | 79 BLOCK
  Trades:      148 cerrados | 72 wins | 76 losses
  Winrate:     48.6%
  Avg Trade:   0.48
  Avg Win:     6.83  |  Avg Loss: 5.53
  Expectancy:  0.48 por trade
  PF:          1.17
  PnL total:   +71.63
  Peor DD:     74.11
  -------------------------------------------------------------
  Suma PnL trades:  +71.77   (debe cuadrar con PnL total)
  ✅ Cuadra (dif. 0.14, son costes de trades aún abiertos)
#################################################################

  VEREDICTO:
  🟡  Edge marginal. Positivo pero débil.


=================================================================
  COMPARACIÓN TRAIN vs TEST
=================================================================

  IWM:
    TRAIN: 75 trades | WR 45.3% | PF 0.95 | Exp -0.16
    TEST:  28 trades | WR 28.6% | PF 0.43 | Exp -2.17
    ⚠️  Degradación significativa train→test

  NVDA:
    TRAIN: 96 trades | WR 53.1% | PF 1.36 | Exp 0.95
    TEST:  40 trades | WR 62.5% | PF 2.03 | Exp 2.09
    ✅  Consistente entre train y test

  AMZN:
    TRAIN: 95 trades | WR 47.4% | PF 1.11 | Exp 0.33
    TEST:  36 trades | WR 44.4% | PF 0.93 | Exp -0.20
    ✅  Consistente entre train y test

  META:
    TRAIN: 83 trades | WR 45.8% | PF 1.05 | Exp 0.16
    TEST:  44 trades | WR 52.3% | PF 1.46 | Exp 1.27
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

Operaciones totales con la config actual: 64

==============================================================
1) BOOTSTRAP DE LA EXPECTATIVA
==============================================================
Operaciones:            64
Expectativa observada:  -0.5052 € por operación
Intervalo 90%:          -1.9286  a  +0.9053
Prob. expectativa > 0:  27.9%

LECTURA: INDECISO. El cero está dentro del intervalo, así que
         esta muestra no distingue la estrategia de una moneda.
         No significa que no funcione: significa que todavía no
         se sabe. La única cura es más operaciones.

==============================================================
2) MONTE CARLO DE LA CURVA DE CAPITAL
==============================================================
Capital inicial:   1000.00 €
Operaciones:       64

A) MISMAS OPERACIONES, OTRO ORDEN
   (el capital final no cambia al barajar; solo el camino)
   Drawdown mediano:        6.77%
   Drawdown percentil 95:   9.59%
   Peor drawdown simulado:  14.05%
   Capital final (fijo):    967.67 €

B) REMUESTREO: si las próximas operaciones salieran de
   esta misma distribución
   Capital final, percentil 5:   875.06 €
   Capital final, mediana:       969.35 €
   Capital final, percentil 95:  1057.85 €
   Drawdown percentil 95:        14.12%
   Prob. terminar en pérdida:    71.9%
   Prob. perder la mitad:        0.0%

LECTURA: el drawdown que hay que estar dispuesto a aguantar es
         del 9.6%, no el que salió en el histórico: el orden
         de las operaciones es azar y la racha mala no tiene por
         qué haber caído dentro del periodo de prueba.
         El remuestreo da 72% de probabilidad de acabar
         en pérdida sobre otras 64 operaciones.

==============================================================
3) BARRIDO DE PARÁMETROS (SL / TP)
==============================================================

   SL    TP   R:R   OPS    WR%    EXPECT     PF  VEREDICTO
--------------------------------------------------------------
  1.5   2.0  1.33    74   41.9   -1.8342   0.57
  1.5   2.5  1.67    71   39.4   -1.5793   0.65
  1.5   3.0  2.00    66   37.9   -1.0650   0.77
  1.5   3.5  2.33    63   34.9   -0.9853   0.80
  2.0   2.0  1.00    69   50.7   -0.9785   0.71
  2.0   2.5  1.25    64   50.0   -0.5052   0.85 <-- CONFIG ACTUAL
  2.0   3.0  1.50    60   46.7   -0.2462   0.93
  2.0   3.5  1.75    59   39.0   -0.8165   0.80
  2.5   2.0  0.80    68   55.9   -0.6002   0.79
  2.5   2.5  1.00    64   54.7   -0.1957   0.93
  2.5   3.0  1.20    59   50.8   -0.0606   0.98
  2.5   3.5  1.40    57   42.1   -0.6922   0.81
  3.0   2.0  0.67    66   59.1   -0.5898   0.77
  3.0   2.5  0.83    62   58.1   -0.2339   0.91
  3.0   3.0  1.00    59   52.5   -0.2755   0.91
  3.0   3.5  1.17    55   45.5   -0.6624   0.80

Combinaciones con expectativa positiva: 0 de 16
Configuración actual (SL 2.0 / TP 2.5): expectativa -0.5052, PF 0.85
Vecinos inmediatos con expectativa positiva: 0 de 8

LECTURA: la configuración actual no tiene expectativa positiva
         en este periodo. Si otras combinaciones sí, ojo: elegir
         ahora la mejor de la tabla ES sobreajustar.

==============================================================
4) ECONOMÍA REAL: ¿QUÉ SIGNIFICA ESTO EN DINERO?
==============================================================
Periodo cubierto:       0.2 años
Operaciones:            64  ->  268.8 al año
Riesgo por operación:   5.00 € (0.5% de 1000 €)
Expectativa en riesgo:  -0.101 R por operación

RENTABILIDAD ANUAL SOBRE 1000 €
  pesimista (p05)  :  -518.41 €/año  =  -51.84% anual
  central          :  -135.79 €/año  =  -13.58% anual
  optimista (p95)  :  +243.35 €/año  =  +24.33% anual

CAPITAL NECESARIO PARA SACAR 1.000 €/MES (12.000 €/año)
  pesimista (p05)  : imposible, la expectativa es negativa
  central          : imposible, la expectativa es negativa
  optimista (p95)  :         49,312 €

LECTURA: con expectativa central negativa no hay capital que
         arregle esto. El problema no es el tamaño de la cuenta.

JSON escrito en resultados/robustez_30m.json

==============================================================
```

## Proveedores de datos
```
PRUEBA DE PROVEEDORES — cada uno por separado
Cascada por defecto: ['yfinance', 'finnhub', 'alpha_vantage', 'twelve_data']

  OK    yfinance   SPY         3770 velas  2011-10-21 -> 2026-10-20
  FALLA stooq      SPY       ValueError: No se pudo descargar SPY con ningún provider. Detalles: ['stooq: Stooq
  OK    yfinance   BTC-USD     4418 velas  2014-09-17 -> 2026-10-21
  OK    coinbase   BTC-USD     4112 velas  2015-07-20 -> 2026-10-21
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
comprar_y_mantener        6.32%    0.72   -16.6%   93.3%    0.07    2.490
M02_tendencia             6.26%    0.66   -22.3%   93.3%    3.78    2.468
M03_momentum_12_1         9.93%    0.62   -27.2%   93.3%    5.87    4.095
M02_mas_M03               9.90%    0.62   -27.9%   93.3%    5.80    4.077
M03_con_banda             9.16%    0.64   -24.5%   84.1%    5.29    3.689
efectivo (BIL)            1.53%            -0.4%
cuenta sin remunerar      0.00%   (lo que de verdad cobra la cuenta: 0%)

  CRITERIOS REGISTRADOS
  corte train/test: 2020-10-19

  M02_tendencia
    anual +6.26%  vs comprar y mantener +6.32%  -> NO bate
    train: +5.13% vs +3.75%  -> bate
    test : +4.70% vs +6.47%  -> NO bate
    VEREDICTO: NO PASA: forma peor de estar invertido

  M03_momentum_12_1
    anual +9.93%  vs comprar y mantener +6.32%  -> bate
    train: +6.89% vs +3.75%  -> bate
    test : +10.04% vs +6.47%  -> bate
    VEREDICTO: PASA

  M02_mas_M03
    anual +9.90%  vs comprar y mantener +6.32%  -> bate
    train: +6.69% vs +3.75%  -> bate
    test : +10.27% vs +6.47%  -> bate
    VEREDICTO: PASA

======================================================================
clase_renta_variable  (14 activos)
======================================================================

VARIANTE                  ANUAL  SHARPE    MAXDD   EXPOS   ROT/A    FINAL
----------------------------------------------------------------------
comprar_y_mantener       12.65%    0.93   -23.3%   93.3%    0.07    5.893
M02_tendencia            12.43%    0.95   -19.1%   93.3%    3.67    5.721
M03_momentum_12_1        13.36%    1.03   -16.0%   93.3%    4.84    6.467
M02_mas_M03              13.48%    1.02   -16.0%   93.3%    4.96    6.570
M03_con_banda            12.57%    1.04   -14.4%   86.4%    4.39    5.829
efectivo (BIL)            1.53%            -0.4%
cuenta sin remunerar      0.00%   (lo que de verdad cobra la cuenta: 0%)

  CRITERIOS REGISTRADOS
  corte train/test: 2020-10-19

  M02_tendencia
    anual +12.43%  vs comprar y mantener +12.65%  -> NO bate
    train: +11.10% vs +11.11%  -> NO bate
    test : +9.57% vs +9.11%  -> bate
    VEREDICTO: NO PASA: forma peor de estar invertido
    I29: mejor Sharpe (0.95 vs 0.93) pero MENOS dinero. No es una mejora del beneficio.

  M03_momentum_12_1
    anual +13.36%  vs comprar y mantener +12.65%  -> bate
    train: +12.67% vs +11.11%  -> bate
    test : +10.09% vs +9.11%  -> bate
    VEREDICTO: PASA

  M02_mas_M03
    anual +13.48%  vs comprar y mantener +12.65%  -> bate
    train: +12.73% vs +11.11%  -> bate
    test : +10.29% vs +9.11%  -> bate
    VEREDICTO: PASA

======================================================================
clase_materias_primas  (7 activos)
======================================================================

VARIANTE                  ANUAL  SHARPE    MAXDD   EXPOS   ROT/A    FINAL
----------------------------------------------------------------------
comprar_y_mantener        0.94%    0.06   -60.0%   93.3%    0.07    1.150
M02_tendencia            -0.76%   -0.04   -68.5%   82.8%    5.41    0.892
M03_momentum_12_1         0.54%    0.03   -56.9%   82.2%    4.73    1.083
M02_mas_M03              -0.30%   -0.01   -65.9%   80.0%    4.80    0.957
M03_con_banda             0.89%    0.05   -55.8%   80.2%    4.30    1.141
efectivo (BIL)            1.53%            -0.4%
cuenta sin remunerar      0.00%   (lo que de verdad cobra la cuenta: 0%)

  CRITERIOS REGISTRADOS
  corte train/test: 2020-10-19

  M02_tendencia
    anual -0.76%  vs comprar y mantener +0.94%  -> NO bate
    train: -9.65% vs -7.63%  -> NO bate
    test : +9.91% vs +9.64%  -> bate
    VEREDICTO: NO PASA: forma peor de estar invertido

  M03_momentum_12_1
    anual +0.54%  vs comprar y mantener +0.94%  -> NO bate
    train: -5.84% vs -7.63%  -> bate
    test : +7.77% vs +9.64%  -> NO bate
    VEREDICTO: NO PASA: forma peor de estar invertido

  M02_mas_M03
    anual -0.30%  vs comprar y mantener +0.94%  -> NO bate
    train: -7.97% vs -7.63%  -> NO bate
    test : +9.25% vs +9.64%  -> NO bate
    VEREDICTO: NO PASA: forma peor de estar invertido

======================================================================
clase_bonos  (5 activos)
======================================================================

VARIANTE                  ANUAL  SHARPE    MAXDD   EXPOS   ROT/A    FINAL
----------------------------------------------------------------------
comprar_y_mantener        1.70%    0.29   -20.5%   93.3%    0.07    1.286
M02_tendencia             1.86%    0.42   -10.3%   81.7%    3.52    1.317
M03_momentum_12_1         1.35%    0.26   -17.9%   85.6%    3.20    1.221
M02_mas_M03               1.74%    0.39   -10.4%   81.1%    4.18    1.292
M03_con_banda             1.39%    0.28   -17.6%   83.4%    2.90    1.229
efectivo (BIL)            1.53%            -0.4%
cuenta sin remunerar      0.00%   (lo que de verdad cobra la cuenta: 0%)

  CRITERIOS REGISTRADOS
  corte train/test: 2020-10-19

  M02_tendencia
    anual +1.86%  vs comprar y mantener +1.70%  -> bate
    train: +2.88% vs +3.61%  -> NO bate
    test : +0.57% vs -1.00%  -> bate
    VEREDICTO: INCONCLUSO: no se sostiene en las dos mitades

  M03_momentum_12_1
    anual +1.35%  vs comprar y mantener +1.70%  -> NO bate
    train: +2.93% vs +3.61%  -> NO bate
    test : -0.65% vs -1.00%  -> bate
    VEREDICTO: NO PASA: forma peor de estar invertido

  M02_mas_M03
    anual +1.74%  vs comprar y mantener +1.70%  -> bate
    train: +2.63% vs +3.61%  -> NO bate
    test : +0.57% vs -1.00%  -> bate
    VEREDICTO: INCONCLUSO: no se sostiene en las dos mitades

======================================================================
clase_divisas  (5 activos)
======================================================================

VARIANTE                  ANUAL  SHARPE    MAXDD   EXPOS   ROT/A    FINAL
----------------------------------------------------------------------
comprar_y_mantener       -0.54%   -0.14   -19.7%   93.3%    0.07    0.922
M02_tendencia            -0.10%   -0.02   -15.0%   93.3%    5.16    0.985
M03_momentum_12_1        -0.36%   -0.06   -15.6%   93.3%    4.16    0.948
M02_mas_M03              -0.73%   -0.11   -20.7%   92.8%    4.94    0.897
M03_con_banda            -0.36%   -0.07   -15.1%   91.3%    3.90    0.947
efectivo (BIL)            1.53%            -0.4%
cuenta sin remunerar      0.00%   (lo que de verdad cobra la cuenta: 0%)

  CRITERIOS REGISTRADOS
  corte train/test: 2020-10-19

  M02_tendencia
    anual -0.10%  vs comprar y mantener -0.54%  -> bate
    train: +0.43% vs -1.12%  -> bate
    test : -0.96% vs +0.54%  -> NO bate
    VEREDICTO: NO PASA: por debajo del efectivo

  M03_momentum_12_1
    anual -0.36%  vs comprar y mantener -0.54%  -> bate
    train: -0.74% vs -1.12%  -> bate
    test : +0.49% vs +0.54%  -> NO bate
    VEREDICTO: NO PASA: por debajo del efectivo

  M02_mas_M03
    anual -0.73%  vs comprar y mantener -0.54%  -> NO bate
    train: -0.41% vs -1.12%  -> bate
    test : -0.96% vs +0.54%  -> NO bate
    VEREDICTO: NO PASA: forma peor de estar invertido
    I29: mejor Sharpe (-0.11 vs -0.14) pero MENOS dinero. No es una mejora del beneficio.

======================================================================
cripto_sesgo_extremo  (2 activos)
======================================================================

VARIANTE                  ANUAL  SHARPE    MAXDD   EXPOS   ROT/A    FINAL
----------------------------------------------------------------------
comprar_y_mantener       62.75%    0.85   -81.3%   94.5%    0.17  340.889
M02_tendencia            52.49%    0.83   -66.3%   70.3%    1.67  156.275
M03_momentum_12_1        52.01%    0.81   -79.8%   69.7%    2.25  150.504
M02_mas_M03              50.82%    0.84   -64.8%   63.4%    1.84  136.937
M03_con_banda            50.99%    0.81   -78.7%   68.2%    2.17  138.794
efectivo (BIL)            1.53%            -0.4%
cuenta sin remunerar      0.00%   (lo que de verdad cobra la cuenta: 0%)

  CRITERIOS REGISTRADOS
  corte train/test: 2021-12-19

  M02_tendencia
    anual +52.49%  vs comprar y mantener +62.75%  -> NO bate
    train: +99.10% vs +122.00%  -> NO bate
    test : +16.79% vs +23.88%  -> NO bate
    VEREDICTO: NO PASA: forma peor de estar invertido

  M03_momentum_12_1
    anual +52.01%  vs comprar y mantener +62.75%  -> NO bate
    train: +103.93% vs +122.00%  -> NO bate
    test : +14.19% vs +23.88%  -> NO bate
    VEREDICTO: NO PASA: forma peor de estar invertido

  M02_mas_M03
    anual +50.82%  vs comprar y mantener +62.75%  -> NO bate
    train: +97.31% vs +122.00%  -> NO bate
    test : +16.81% vs +23.88%  -> NO bate
    VEREDICTO: NO PASA: forma peor de estar invertido

======================================================================
AJUSTADO vs SIN AJUSTAR — cuanto cambia por dividendos y splits
======================================================================
  comprar_y_mantener       ajustado  +6.32%  sin ajustar  +4.83%  diferencia +1.49 puntos/ano
  M03_momentum_12_1        ajustado  +9.93%  sin ajustar  +7.83%  diferencia +2.11 puntos/ano

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

