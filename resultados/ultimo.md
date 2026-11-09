# Validacion SHARK V15

Fecha:   2026-11-09 18:25 UTC
Commit:  4486a7e6
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
IWM     yfinance      775    60   12.9  [9, 10, 11, 12, 13, 14, 15]
        2026-08-17 09:30:00-04:00  ->  2026-11-09 13:00:00-05:00
NVDA    yfinance      775    60   12.9  [9, 10, 11, 12, 13, 14, 15]
        2026-08-17 09:30:00-04:00  ->  2026-11-09 13:00:00-05:00
AMZN    yfinance      775    60   12.9  [9, 10, 11, 12, 13, 14, 15]
        2026-08-17 09:30:00-04:00  ->  2026-11-09 13:00:00-05:00
META    yfinance      775    60   12.9  [9, 10, 11, 12, 13, 14, 15]
        2026-08-17 09:30:00-04:00  ->  2026-11-09 13:00:00-05:00
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
  OK | yfinance | 775 velas
Descargando NVDA...
  OK | yfinance | 775 velas
Descargando AMZN...
  OK | yfinance | 775 velas
Descargando META...
  OK | yfinance | 775 velas

=================================================================
  FASE 1: BACKTEST COMPLETO (todo el período)
=================================================================

============================================================
IWM | FULL | Bars: 575
============================================================
Capital:     1000.00 → 986.63  (-13.37)
Señales:     54 generadas | 13 ALLOW | 41 BLOCK
Trades:      13 cerrados | 6 wins | 7 losses
Winrate:     46.1%
Avg Trade:   -1.03
Avg Win:     6.47  |  Avg Loss: 7.45
Expectancy:  -1.03 por trade
PF:          0.74
Max DD:      26.80 (2.7%)
Avg Bars:    12 velas
Regímenes:   {'BEAR_TREND': 7, 'TREND': 6}
Señales:     {'SELL': 12, 'BUY': 1}
Bloqueos principales:
    39x  Cooldown por activo (6h)
     1x  ADX insuficiente para sniper: 20.88 < 22.0 | Score final insuficiente para sniper: 54.30 <
     1x  ADX insuficiente para sniper: 21.95 < 22.0 | Score final insuficiente para sniper: 54.97 <

============================================================
NVDA | FULL | Bars: 575
============================================================
Capital:     1000.00 → 982.22  (-17.78)
Señales:     64 generadas | 20 ALLOW | 44 BLOCK
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
AMZN | FULL | Bars: 575
============================================================
Capital:     1000.00 → 971.32  (-28.68)
Señales:     82 generadas | 21 ALLOW | 61 BLOCK
Trades:      20 cerrados | 8 wins | 12 losses
Winrate:     40.0%
Avg Trade:   -1.42
Avg Win:     5.54  |  Avg Loss: 6.07
Expectancy:  -1.42 por trade
PF:          0.61
Max DD:      52.53 (5.2%)
Avg Bars:    12 velas
Regímenes:   {'TREND': 7, 'BEAR_TREND': 9, 'BULL_TREND': 4}
Señales:     {'SELL': 14, 'BUY': 6}
Bloqueos principales:
    60x  Cooldown por activo (6h)
     1x  ADX insuficiente para sniper: 21.70 < 22.0 | Score final insuficiente para sniper: 54.81 <

============================================================
META | FULL | Bars: 575
============================================================
Capital:     1000.00 → 1047.97  (+47.97)
Señales:     60 generadas | 15 ALLOW | 45 BLOCK
Trades:      14 cerrados | 11 wins | 3 losses
Winrate:     78.6%
Avg Trade:   3.44
Avg Win:     5.94  |  Avg Loss: 5.71
Expectancy:  3.44 por trade
PF:          3.81
Max DD:      11.48 (1.1%)
Avg Bars:    18 velas
Regímenes:   {'BULL_TREND': 8, 'TREND': 1, 'BEAR_TREND': 5}
Señales:     {'BUY': 8, 'SELL': 6}
Bloqueos principales:
    45x  Cooldown por activo (6h)


#################################################################
  CONSOLIDADO FULL PERIOD — 4 activos
#################################################################
  Señales:     260 generadas | 69 ALLOW | 191 BLOCK
  Trades:      66 cerrados | 33 wins | 33 losses
  Winrate:     50.0%
  Avg Trade:   -0.17
  Avg Win:     6.22  |  Avg Loss: 6.56
  Expectancy:  -0.17 por trade
  PF:          0.95
  PnL total:   -11.86
  Peor DD:     52.53
  -------------------------------------------------------------
  Suma PnL trades:  -11.33   (debe cuadrar con PnL total)
  ✅ Cuadra (dif. 0.53, son costes de trades aún abiertos)
#################################################################

  VEREDICTO:
  ❌  NO HAY EDGE. Expectancy negativa.


=================================================================
  FASE 2: WALK-FORWARD (70% train / 30% test)
=================================================================

--- IWM TRAIN ---
  ============================================================
  IWM | TRAIN | Bars: 342
  ============================================================
  Capital:     1000.00 → 997.18  (-2.82)
  Señales:     33 generadas | 8 ALLOW | 25 BLOCK
  Trades:      8 cerrados | 4 wins | 4 losses
  Winrate:     50.0%
  Avg Trade:   -0.35
  Avg Win:     6.76  |  Avg Loss: 7.47
  Expectancy:  -0.35 por trade
  PF:          0.91
  Max DD:      26.80 (2.7%)
  Avg Bars:    9 velas
  Regímenes:   {'BEAR_TREND': 5, 'TREND': 3}
  Señales:     {'SELL': 8}
  Bloqueos principales:
      24x  Cooldown por activo (6h)
       1x  ADX insuficiente para sniper: 20.88 < 22.0 | Score final insuficiente para sniper: 54.30 <

--- IWM TEST ---
  ============================================================
  IWM | TEST | Bars: 233
  ============================================================
  Capital:     1000.00 → 982.97  (-17.03)
  Señales:     21 generadas | 6 ALLOW | 15 BLOCK
  Trades:      6 cerrados | 2 wins | 4 losses
  Winrate:     33.3%
  Avg Trade:   -2.84
  Avg Win:     5.85  |  Avg Loss: 7.18
  Expectancy:  -2.84 por trade
  PF:          0.41
  Max DD:      17.78 (1.8%)
  Avg Bars:    14 velas
  Regímenes:   {'BEAR_TREND': 3, 'TREND': 3}
  Señales:     {'SELL': 5, 'BUY': 1}
  Bloqueos principales:
      14x  Cooldown por activo (6h)
       1x  ADX insuficiente para sniper: 21.95 < 22.0 | Score final insuficiente para sniper: 54.97 <

--- NVDA TRAIN ---
  ============================================================
  NVDA | TRAIN | Bars: 342
  ============================================================
  Capital:     1000.00 → 993.95  (-6.05)
  Señales:     35 generadas | 11 ALLOW | 24 BLOCK
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
  NVDA | TEST | Bars: 233
  ============================================================
  Capital:     1000.00 → 997.97  (-2.03)
  Señales:     31 generadas | 9 ALLOW | 22 BLOCK
  Trades:      8 cerrados | 4 wins | 4 losses
  Winrate:     50.0%
  Avg Trade:   -0.24
  Avg Win:     7.60  |  Avg Loss: 8.08
  Expectancy:  -0.24 por trade
  PF:          0.94
  Max DD:      14.52 (1.4%)
  Avg Bars:    8 velas
  Regímenes:   {'BEAR_TREND': 8}
  Señales:     {'SELL': 8}
  Bloqueos principales:
      21x  Cooldown por activo (6h)
       1x  ADX insuficiente para sniper: 20.36 < 22.0 | Score final insuficiente para sniper: 53.97 <

--- AMZN TRAIN ---
  ============================================================
  AMZN | TRAIN | Bars: 342
  ============================================================
  Capital:     1000.00 → 1012.64  (+12.64)
  Señales:     49 generadas | 11 ALLOW | 38 BLOCK
  Trades:      11 cerrados | 7 wins | 4 losses
  Winrate:     63.6%
  Avg Trade:   1.15
  Avg Win:     5.52  |  Avg Loss: 6.50
  Expectancy:  1.15 por trade
  PF:          1.49
  Max DD:      15.94 (1.6%)
  Avg Bars:    15 velas
  Regímenes:   {'TREND': 4, 'BEAR_TREND': 4, 'BULL_TREND': 3}
  Señales:     {'SELL': 7, 'BUY': 4}
  Bloqueos principales:
      38x  Cooldown por activo (6h)

--- AMZN TEST ---
  ============================================================
  AMZN | TEST | Bars: 233
  ============================================================
  Capital:     1000.00 → 969.83  (-30.17)
  Señales:     33 generadas | 10 ALLOW | 23 BLOCK
  Trades:      9 cerrados | 2 wins | 7 losses
  Winrate:     22.2%
  Avg Trade:   -3.33
  Avg Win:     5.51  |  Avg Loss: 5.86
  Expectancy:  -3.33 por trade
  PF:          0.27
  Max DD:      40.43 (4.0%)
  Avg Bars:    9 velas
  Regímenes:   {'BEAR_TREND': 5, 'TREND': 3, 'BULL_TREND': 1}
  Señales:     {'SELL': 7, 'BUY': 2}
  Bloqueos principales:
      22x  Cooldown por activo (6h)
       1x  ADX insuficiente para sniper: 21.70 < 22.0 | Score final insuficiente para sniper: 54.81 <

--- META TRAIN ---
  ============================================================
  META | TRAIN | Bars: 342
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
  Regímenes:   {'BULL_TREND': 7, 'TREND': 1}
  Señales:     {'BUY': 7, 'SELL': 1}
  Bloqueos principales:
      29x  Cooldown por activo (6h)

--- META TEST ---
  ============================================================
  META | TEST | Bars: 233
  ============================================================
  Capital:     1000.00 → 1023.64  (+23.64)
  Señales:     23 generadas | 7 ALLOW | 16 BLOCK
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
  Señales:     154 generadas | 38 ALLOW | 116 BLOCK
  Trades:      37 cerrados | 21 wins | 16 losses
  Winrate:     56.8%
  Avg Trade:   0.75
  Avg Win:     6.30  |  Avg Loss: 6.52
  Expectancy:  0.75 por trade
  PF:          1.27
  PnL total:   +27.54
  Peor DD:     26.80
  -------------------------------------------------------------
  Suma PnL trades:  +27.90   (debe cuadrar con PnL total)
  ✅ Cuadra (dif. 0.36, son costes de trades aún abiertos)
#################################################################

  VEREDICTO:
  ✅  HAY EDGE. Expectancy positiva, PF > 1.2, winrate razonable.


#################################################################
  CONSOLIDADO TEST (OUT-OF-SAMPLE) — 4 activos
#################################################################
  Señales:     108 generadas | 32 ALLOW | 76 BLOCK
  Trades:      29 cerrados | 13 wins | 16 losses
  Winrate:     44.8%
  Avg Trade:   -0.86
  Avg Win:     6.34  |  Avg Loss: 6.72
  Expectancy:  -0.86 por trade
  PF:          0.77
  PnL total:   -25.59
  Peor DD:     40.43
  -------------------------------------------------------------
  Suma PnL trades:  -25.06   (debe cuadrar con PnL total)
  ✅ Cuadra (dif. 0.52, son costes de trades aún abiertos)
#################################################################

  VEREDICTO:
  ❌  NO HAY EDGE. Expectancy negativa.


=================================================================
  COMPARACIÓN TRAIN vs TEST
=================================================================

  IWM:
    TRAIN: 8 trades | WR 50.0% | PF 0.91 | Exp -0.35
    TEST:  6 trades | WR 33.3% | PF 0.41 | Exp -2.84
    ⚠️  Degradación significativa train→test

  NVDA:
    TRAIN: 10 trades | WR 40.0% | PF 0.85 | Exp -0.57
    TEST:  8 trades | WR 50.0% | PF 0.94 | Exp -0.24
    ✅  Consistente entre train y test

  AMZN:
    TRAIN: 11 trades | WR 63.6% | PF 1.49 | Exp 1.15
    TEST:  9 trades | WR 22.2% | PF 0.27 | Exp -3.33
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
  OK | yfinance | 3771 velas
Descargando NVDA...
  OK | yfinance | 3771 velas
Descargando AMZN...
  OK | yfinance | 3771 velas
Descargando META...
  OK | yfinance | 3640 velas

=================================================================
  FASE 1: BACKTEST COMPLETO (todo el período)
=================================================================

============================================================
IWM | FULL | Bars: 3571
============================================================
Capital:     1000.00 → 918.45  (-81.55)
Señales:     182 generadas | 106 ALLOW | 76 BLOCK
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
NVDA | FULL | Bars: 3571
============================================================
Capital:     1000.00 → 1195.28  (+195.28)
Señales:     216 generadas | 137 ALLOW | 79 BLOCK
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
AMZN | FULL | Bars: 3571
============================================================
Capital:     1000.00 → 1024.37  (+24.37)
Señales:     220 generadas | 131 ALLOW | 89 BLOCK
Trades:      131 cerrados | 61 wins | 70 losses
Winrate:     46.6%
Avg Trade:   0.19
Avg Win:     7.17  |  Avg Loss: 5.90
Expectancy:  0.19 por trade
PF:          1.06
Max DD:      83.42 (8.3%)
Avg Bars:    12 velas
Regímenes:   {'BULL_TREND': 66, 'BEAR_TREND': 33, 'TREND': 32}
Señales:     {'BUY': 88, 'SELL': 43}
Bloqueos principales:
    49x  Cooldown por activo (6h)
    11x  Volatilidad no válida: Volatilidad demasiado comprimida
     1x  ADX insuficiente para sniper: 21.91 < 22.0 | Score final insuficiente para sniper: 54.95 <
     1x  ADX insuficiente para sniper: 21.50 < 22.0 | Score final insuficiente para sniper: 54.69 <
     1x  ADX insuficiente para sniper: 20.18 < 22.0 | Score final insuficiente para sniper: 53.86 <

============================================================
META | FULL | Bars: 3440
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
  Señales:     801 generadas | 502 ALLOW | 299 BLOCK
  Trades:      499 cerrados | 241 wins | 258 losses
  Winrate:     48.3%
  Avg Trade:   0.42
  Avg Win:     6.87  |  Avg Loss: 5.61
  Expectancy:  0.42 por trade
  PF:          1.14
  PnL total:   +207.71
  Peor DD:     106.35
  -------------------------------------------------------------
  Suma PnL trades:  +207.92   (debe cuadrar con PnL total)
  ✅ Cuadra (dif. 0.21, son costes de trades aún abiertos)
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
  Señales:     131 generadas | 75 ALLOW | 56 BLOCK
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
  Capital:     1000.00 → 929.30  (-70.70)
  Señales:     51 generadas | 31 ALLOW | 20 BLOCK
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
       1x  ADX insuficiente para sniper: 20.92 < 22.0 | Score final insuficiente para sniper: 54.32 <
       1x  ADX insuficiente para sniper: 20.38 < 22.0 | Score final insuficiente para sniper: 53.99 <
       1x  ADX insuficiente para sniper: 20.19 < 22.0 | Score final insuficiente para sniper: 53.87 <
       1x  ADX insuficiente para sniper: 20.65 < 22.0 | Score final insuficiente para sniper: 54.16 <

--- NVDA TRAIN ---
  ============================================================
  NVDA | TRAIN | Bars: 2439
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
  Capital:     1000.00 → 1083.53  (+83.53)
  Señales:     63 generadas | 41 ALLOW | 22 BLOCK
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
  AMZN | TRAIN | Bars: 2439
  ============================================================
  Capital:     1000.00 → 1031.83  (+31.83)
  Señales:     167 generadas | 96 ALLOW | 71 BLOCK
  Trades:      95 cerrados | 45 wins | 50 losses
  Winrate:     47.4%
  Avg Trade:   0.34
  Avg Win:     7.35  |  Avg Loss: 5.98
  Expectancy:  0.34 por trade
  PF:          1.11
  Max DD:      70.25 (7.0%)
  Avg Bars:    12 velas
  Regímenes:   {'BULL_TREND': 52, 'BEAR_TREND': 19, 'TREND': 24}
  Señales:     {'BUY': 68, 'SELL': 27}
  Bloqueos principales:
      40x  Cooldown por activo (6h)
       8x  Volatilidad no válida: Volatilidad demasiado comprimida
       1x  ADX insuficiente para sniper: 21.91 < 22.0 | Score final insuficiente para sniper: 54.95 <
       1x  ADX insuficiente para sniper: 21.50 < 22.0 | Score final insuficiente para sniper: 54.69 <
       1x  ADX insuficiente para sniper: 20.18 < 22.0 | Score final insuficiente para sniper: 53.86 <

--- AMZN TEST ---
  ============================================================
  AMZN | TEST | Bars: 1132
  ============================================================
  Capital:     1000.00 → 986.63  (-13.37)
  Señales:     53 generadas | 35 ALLOW | 18 BLOCK
  Trades:      35 cerrados | 15 wins | 20 losses
  Winrate:     42.9%
  Avg Trade:   -0.38
  Avg Win:     6.46  |  Avg Loss: 5.51
  Expectancy:  -0.38 por trade
  PF:          0.88
  Max DD:      39.29 (3.9%)
  Avg Bars:    12 velas
  Regímenes:   {'BEAR_TREND': 13, 'BULL_TREND': 14, 'TREND': 8}
  Señales:     {'SELL': 15, 'BUY': 20}
  Bloqueos principales:
       9x  Cooldown por activo (6h)
       3x  Volatilidad no válida: Volatilidad demasiado comprimida
       1x  ADX insuficiente para sniper: 21.56 < 22.0 | Score final insuficiente para sniper: 54.72 <
       1x  ADX insuficiente para sniper: 20.63 < 22.0 | Score final insuficiente para sniper: 54.14 <
       1x  ADX insuficiente para sniper: 20.23 < 22.0 | Score final insuficiente para sniper: 53.89 <

--- META TRAIN ---
  ============================================================
  META | TRAIN | Bars: 2348
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
  Señales:     571 generadas | 351 ALLOW | 220 BLOCK
  Trades:      348 cerrados | 168 wins | 180 losses
  Winrate:     48.3%
  Avg Trade:   0.37
  Avg Win:     6.76  |  Avg Loss: 5.59
  Expectancy:  0.37 por trade
  PF:          1.13
  PnL total:   +129.32
  Peor DD:     70.25
  -------------------------------------------------------------
  Suma PnL trades:  +129.43   (debe cuadrar con PnL total)
  ✅ Cuadra (dif. 0.11, son costes de trades aún abiertos)
#################################################################

  VEREDICTO:
  🟡  Edge marginal. Positivo pero débil.


#################################################################
  CONSOLIDADO TEST (OUT-OF-SAMPLE) — 4 activos
#################################################################
  Señales:     230 generadas | 151 ALLOW | 79 BLOCK
  Trades:      148 cerrados | 71 wins | 77 losses
  Winrate:     48.0%
  Avg Trade:   0.41
  Avg Win:     6.84  |  Avg Loss: 5.51
  Expectancy:  0.41 por trade
  PF:          1.14
  PnL total:   +60.84
  Peor DD:     74.11
  -------------------------------------------------------------
  Suma PnL trades:  +61.05   (debe cuadrar con PnL total)
  ✅ Cuadra (dif. 0.20, son costes de trades aún abiertos)
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
    TRAIN: 95 trades | WR 47.4% | PF 1.11 | Exp 0.34
    TEST:  35 trades | WR 42.9% | PF 0.88 | Exp -0.38
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
  IWM     yfinance      775 velas
  NVDA    yfinance      775 velas
  AMZN    yfinance      775 velas
  META    yfinance      775 velas

Operaciones totales con la config actual: 66

==============================================================
1) BOOTSTRAP DE LA EXPECTATIVA
==============================================================
Operaciones:            66
Expectativa observada:  -0.1716 € por operación
Intervalo 90%:          -1.5118  a  +1.1618
Prob. expectativa > 0:  41.7%

LECTURA: INDECISO. El cero está dentro del intervalo, así que
         esta muestra no distingue la estrategia de una moneda.
         No significa que no funcione: significa que todavía no
         se sabe. La única cura es más operaciones.

==============================================================
2) MONTE CARLO DE LA CURVA DE CAPITAL
==============================================================
Capital inicial:   1000.00 €
Operaciones:       66

A) MISMAS OPERACIONES, OTRO ORDEN
   (el capital final no cambia al barajar; solo el camino)
   Drawdown mediano:        5.68%
   Drawdown percentil 95:   8.40%
   Peor drawdown simulado:  11.63%
   Capital final (fijo):    988.67 €

B) REMUESTREO: si las próximas operaciones salieran de
   esta misma distribución
   Capital final, percentil 5:   902.34 €
   Capital final, mediana:       988.59 €
   Capital final, percentil 95:  1075.98 €
   Drawdown percentil 95:        11.95%
   Prob. terminar en pérdida:    58.3%
   Prob. perder la mitad:        0.0%

LECTURA: el drawdown que hay que estar dispuesto a aguantar es
         del 8.4%, no el que salió en el histórico: el orden
         de las operaciones es azar y la racha mala no tiene por
         qué haber caído dentro del periodo de prueba.
         El remuestreo da 58% de probabilidad de acabar
         en pérdida sobre otras 66 operaciones.

==============================================================
3) BARRIDO DE PARÁMETROS (SL / TP)
==============================================================

   SL    TP   R:R   OPS    WR%    EXPECT     PF  VEREDICTO
--------------------------------------------------------------
  1.5   2.0  1.33    80   38.8   -1.9014   0.55
  1.5   2.5  1.67    75   34.7   -1.8207   0.59
  1.5   3.0  2.00    72   31.9   -1.7016   0.65
  1.5   3.5  2.33    71   29.6   -1.6638   0.67
  2.0   2.0  1.00    74   51.4   -0.5938   0.81
  2.0   2.5  1.25    66   50.0   -0.1716   0.95 <-- CONFIG ACTUAL
  2.0   3.0  1.50    62   48.4 +  0.3287   1.10
  2.0   3.5  1.75    64   37.5   -0.7930   0.81
  2.5   2.0  0.80    73   54.8   -0.3275   0.88
  2.5   2.5  1.00    66   53.0 +  0.0173   1.01
  2.5   3.0  1.20    62   50.0 +  0.1532   1.05
  2.5   3.5  1.40    63   38.1   -0.9708   0.74
  3.0   2.0  0.67    68   60.3   -0.1636   0.93
  3.0   2.5  0.83    61   59.0 +  0.1971   1.08
  3.0   3.0  1.00    60   53.3 +  0.0538   1.02
  3.0   3.5  1.17    57   45.6   -0.4447   0.86

Combinaciones con expectativa positiva: 5 de 16
Configuración actual (SL 2.0 / TP 2.5): expectativa -0.1716, PF 0.95
Vecinos inmediatos con expectativa positiva: 3 de 8

LECTURA: la configuración actual no tiene expectativa positiva
         en este periodo. Si otras combinaciones sí, ojo: elegir
         ahora la mejor de la tabla ES sobreajustar.

==============================================================
4) ECONOMÍA REAL: ¿QUÉ SIGNIFICA ESTO EN DINERO?
==============================================================
Periodo cubierto:       0.2 años
Operaciones:            66  ->  279.0 al año
Riesgo por operación:   5.00 € (0.5% de 1000 €)
Expectativa en riesgo:  -0.034 R por operación

RENTABILIDAD ANUAL SOBRE 1000 €
  pesimista (p05)  :  -421.79 €/año  =  -42.18% anual
  central          :   -47.89 €/año  =   -4.79% anual
  optimista (p95)  :  +324.13 €/año  =  +32.41% anual

CAPITAL NECESARIO PARA SACAR 1.000 €/MES (12.000 €/año)
  pesimista (p05)  : imposible, la expectativa es negativa
  central          : imposible, la expectativa es negativa
  optimista (p95)  :         37,022 €

LECTURA: con expectativa central negativa no hay capital que
         arregle esto. El problema no es el tamaño de la cuenta.

JSON escrito en resultados/robustez_30m.json

==============================================================
```

## Proveedores de datos
```
PRUEBA DE PROVEEDORES — cada uno por separado
Cascada por defecto: ['yfinance', 'finnhub', 'alpha_vantage', 'twelve_data']

  OK    yfinance   SPY         3771 velas  2011-11-09 -> 2026-11-09
  FALLA stooq      SPY       ValueError: No se pudo descargar SPY con ningún provider. Detalles: ['stooq: Stooq
  OK    yfinance   BTC-USD     4437 velas  2014-09-17 -> 2026-11-09
  OK    coinbase   BTC-USD     4131 velas  2015-07-20 -> 2026-11-09
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

## Panel EN VIVO del bot (IWM, NVDA, AMZN, META)

La cifra comparable entre marcos es la esperanza NETA
por operacion, no el NAV: Yahoo solo sirve ~60 dias de
intradia, asi que 30m y 1d NO cubren la misma ventana.
El recorte "diario dentro de la ventana de 30m" quita
ese confundido.

```
======================================================================
B1 SOBRE EL PANEL EN VIVO DEL BOT
======================================================================
  activos: IWM, NVDA, AMZN, META
  marcos:  30m, 1d
  filtro de viabilidad: APAGADO

  descargando 30m (periodo 60d) ...
    IWM    30m  FALLO  ValueError: No se pudo descargar IWM con ningún provider. Detalles: ["yfinance: module 'yfinance' has no attribute 'download'", 'fin
    NVDA   30m  FALLO  ValueError: No se pudo descargar NVDA con ningún provider. Detalles: ["yfinance: module 'yfinance' has no attribute 'download'", 'fi
    AMZN   30m  FALLO  ValueError: No se pudo descargar AMZN con ningún provider. Detalles: ["yfinance: module 'yfinance' has no attribute 'download'", 'fi
    META   30m  FALLO  ValueError: No se pudo descargar META con ningún provider. Detalles: ["yfinance: module 'yfinance' has no attribute 'download'", 'fi
    SIN DATOS para 30m. No se mide.

  descargando 1d (periodo 5y) ...
    IWM    1d   FALLO  ValueError: No se pudo descargar IWM con ningún provider. Detalles: ["yfinance: module 'yfinance' has no attribute 'download'", 'fin
    NVDA   1d   FALLO  ValueError: No se pudo descargar NVDA con ningún provider. Detalles: ["yfinance: module 'yfinance' has no attribute 'download'", 'fi
    AMZN   1d   FALLO  ValueError: No se pudo descargar AMZN con ningún provider. Detalles: ["yfinance: module 'yfinance' has no attribute 'download'", 'fi
    META   1d   FALLO  ValueError: No se pudo descargar META con ningún provider. Detalles: ["yfinance: module 'yfinance' has no attribute 'download'", 'fi
    SIN DATOS para 1d. No se mide.

======================================================================
COMPARACION  (esperanza NETA por operacion: homogenea entre
              ventanas distintas; el NAV no lo es)
======================================================================
  30m   SIN DATOS: ningun activo descargado
  1d    SIN DATOS: ningun activo descargado

guardado /home/runner/work/shark-v15/shark-v15/resultados/v3/b1_panel_vivo.json

AVISO: sin datos para ['30m', '1d']. La comparacion esta incompleta.
```

### Con filtro de viabilidad 1x

```
======================================================================
B1 SOBRE EL PANEL EN VIVO DEL BOT
======================================================================
  activos: IWM, NVDA, AMZN, META
  marcos:  30m, 1d
  filtro de viabilidad: 1.0

  descargando 30m (periodo 60d) ...
    IWM    30m  FALLO  ValueError: No se pudo descargar IWM con ningún provider. Detalles: ["yfinance: module 'yfinance' has no attribute 'download'", 'fin
    NVDA   30m  FALLO  ValueError: No se pudo descargar NVDA con ningún provider. Detalles: ["yfinance: module 'yfinance' has no attribute 'download'", 'fi
    AMZN   30m  FALLO  ValueError: No se pudo descargar AMZN con ningún provider. Detalles: ["yfinance: module 'yfinance' has no attribute 'download'", 'fi
    META   30m  FALLO  ValueError: No se pudo descargar META con ningún provider. Detalles: ["yfinance: module 'yfinance' has no attribute 'download'", 'fi
    SIN DATOS para 30m. No se mide.

  descargando 1d (periodo 5y) ...
    IWM    1d   FALLO  ValueError: No se pudo descargar IWM con ningún provider. Detalles: ["yfinance: module 'yfinance' has no attribute 'download'", 'fin
    NVDA   1d   FALLO  ValueError: No se pudo descargar NVDA con ningún provider. Detalles: ["yfinance: module 'yfinance' has no attribute 'download'", 'fi
    AMZN   1d   FALLO  ValueError: No se pudo descargar AMZN con ningún provider. Detalles: ["yfinance: module 'yfinance' has no attribute 'download'", 'fi
    META   1d   FALLO  ValueError: No se pudo descargar META con ningún provider. Detalles: ["yfinance: module 'yfinance' has no attribute 'download'", 'fi
    SIN DATOS para 1d. No se mide.

======================================================================
COMPARACION  (esperanza NETA por operacion: homogenea entre
              ventanas distintas; el NAV no lo es)
======================================================================
  30m   SIN DATOS: ningun activo descargado
  1d    SIN DATOS: ningun activo descargado

guardado /home/runner/work/shark-v15/shark-v15/resultados/v3/b1_panel_vivo.json

AVISO: sin datos para ['30m', '1d']. La comparacion esta incompleta.
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
comprar_y_mantener        6.26%    0.72   -16.6%   93.3%    0.07    2.464
M02_tendencia             5.98%    0.63   -22.3%   93.3%    3.78    2.371
M03_momentum_12_1         9.24%    0.57   -27.2%   93.3%    5.83    3.717
M02_mas_M03               9.13%    0.57   -27.9%   93.3%    5.79    3.662
M03_con_banda             8.54%    0.59   -24.5%   84.1%    5.25    3.382
efectivo (BIL)            1.53%            -0.4%
cuenta sin remunerar      0.00%   (lo que de verdad cobra la cuenta: 0%)

  CRITERIOS REGISTRADOS
  corte train/test: 2020-11-05

  M02_tendencia
    anual +5.98%  vs comprar y mantener +6.26%  -> NO bate
    train: +5.27% vs +3.83%  -> bate
    test : +4.77% vs +6.87%  -> NO bate
    VEREDICTO: NO PASA: forma peor de estar invertido

  M03_momentum_12_1
    anual +9.24%  vs comprar y mantener +6.26%  -> bate
    train: +7.08% vs +3.83%  -> bate
    test : +10.71% vs +6.87%  -> bate
    VEREDICTO: PASA

  M02_mas_M03
    anual +9.13%  vs comprar y mantener +6.26%  -> bate
    train: +6.87% vs +3.83%  -> bate
    test : +10.74% vs +6.87%  -> bate
    VEREDICTO: PASA

======================================================================
clase_renta_variable  (14 activos)
======================================================================

VARIANTE                  ANUAL  SHARPE    MAXDD   EXPOS   ROT/A    FINAL
----------------------------------------------------------------------
comprar_y_mantener       12.67%    0.93   -23.3%   93.3%    0.07    5.891
M02_tendencia            12.38%    0.94   -19.1%   93.3%    3.69    5.670
M03_momentum_12_1        13.04%    1.00   -16.0%   93.3%    4.79    6.181
M02_mas_M03              13.16%    0.99   -16.0%   93.3%    4.91    6.280
M03_con_banda            12.29%    1.02   -14.4%   86.4%    4.35    5.596
efectivo (BIL)            1.53%            -0.4%
cuenta sin remunerar      0.00%   (lo que de verdad cobra la cuenta: 0%)

  CRITERIOS REGISTRADOS
  corte train/test: 2020-11-05

  M02_tendencia
    anual +12.38%  vs comprar y mantener +12.67%  -> NO bate
    train: +11.31% vs +11.32%  -> NO bate
    test : +9.90% vs +9.59%  -> bate
    VEREDICTO: NO PASA: forma peor de estar invertido
    I29: mejor Sharpe (0.94 vs 0.93) pero MENOS dinero. No es una mejora del beneficio.

  M03_momentum_12_1
    anual +13.04%  vs comprar y mantener +12.67%  -> bate
    train: +12.86% vs +11.32%  -> bate
    test : +10.10% vs +9.59%  -> bate
    VEREDICTO: PASA

  M02_mas_M03
    anual +13.16%  vs comprar y mantener +12.67%  -> bate
    train: +12.92% vs +11.32%  -> bate
    test : +10.30% vs +9.59%  -> bate
    VEREDICTO: PASA

======================================================================
clase_materias_primas  (7 activos)
======================================================================

VARIANTE                  ANUAL  SHARPE    MAXDD   EXPOS   ROT/A    FINAL
----------------------------------------------------------------------
comprar_y_mantener        0.55%    0.04   -60.1%   93.3%    0.07    1.085
M02_tendencia            -1.70%   -0.08   -68.5%   83.3%    5.49    0.775
M03_momentum_12_1         0.08%    0.00   -56.9%   82.2%    4.70    1.012
M02_mas_M03              -1.13%   -0.05   -65.9%   80.6%    4.87    0.844
M03_con_banda             0.45%    0.03   -55.8%   80.2%    4.27    1.070
efectivo (BIL)            1.53%            -0.4%
cuenta sin remunerar      0.00%   (lo que de verdad cobra la cuenta: 0%)

  CRITERIOS REGISTRADOS
  corte train/test: 2020-11-05

  M02_tendencia
    anual -1.70%  vs comprar y mantener +0.55%  -> NO bate
    train: -9.30% vs -7.76%  -> NO bate
    test : +9.15% vs +10.24%  -> NO bate
    VEREDICTO: NO PASA: forma peor de estar invertido

  M03_momentum_12_1
    anual +0.08%  vs comprar y mantener +0.55%  -> NO bate
    train: -5.58% vs -7.76%  -> bate
    test : +8.77% vs +10.24%  -> NO bate
    VEREDICTO: NO PASA: forma peor de estar invertido

  M02_mas_M03
    anual -1.13%  vs comprar y mantener +0.55%  -> NO bate
    train: -7.62% vs -7.76%  -> bate
    test : +8.98% vs +10.24%  -> NO bate
    VEREDICTO: NO PASA: forma peor de estar invertido

======================================================================
clase_bonos  (5 activos)
======================================================================

VARIANTE                  ANUAL  SHARPE    MAXDD   EXPOS   ROT/A    FINAL
----------------------------------------------------------------------
comprar_y_mantener        1.77%    0.30   -20.5%   93.3%    0.07    1.297
M02_tendencia             1.83%    0.41   -10.3%   81.1%    3.53    1.309
M03_momentum_12_1         1.36%    0.27   -17.9%   85.6%    3.20    1.223
M02_mas_M03               1.70%    0.38   -10.4%   80.6%    4.19    1.285
M03_con_banda             1.41%    0.28   -17.6%   83.4%    2.90    1.230
efectivo (BIL)            1.53%            -0.4%
cuenta sin remunerar      0.00%   (lo que de verdad cobra la cuenta: 0%)

  CRITERIOS REGISTRADOS
  corte train/test: 2020-11-05

  M02_tendencia
    anual +1.83%  vs comprar y mantener +1.77%  -> bate
    train: +2.93% vs +3.66%  -> NO bate
    test : +0.67% vs -0.87%  -> bate
    VEREDICTO: INCONCLUSO: no se sostiene en las dos mitades

  M03_momentum_12_1
    anual +1.36%  vs comprar y mantener +1.77%  -> NO bate
    train: +2.98% vs +3.66%  -> NO bate
    test : -0.44% vs -0.87%  -> bate
    VEREDICTO: NO PASA: forma peor de estar invertido

  M02_mas_M03
    anual +1.70%  vs comprar y mantener +1.77%  -> NO bate
    train: +2.68% vs +3.66%  -> NO bate
    test : +0.67% vs -0.87%  -> bate
    VEREDICTO: NO PASA: forma peor de estar invertido
    I29: mejor Sharpe (0.38 vs 0.30) pero MENOS dinero. No es una mejora del beneficio.

======================================================================
clase_divisas  (5 activos)
======================================================================

VARIANTE                  ANUAL  SHARPE    MAXDD   EXPOS   ROT/A    FINAL
----------------------------------------------------------------------
comprar_y_mantener       -0.50%   -0.13   -19.2%   93.3%    0.07    0.929
M02_tendencia            -0.08%   -0.01   -15.0%   93.3%    5.04    0.988
M03_momentum_12_1        -0.35%   -0.06   -15.6%   93.3%    4.03    0.950
M02_mas_M03              -0.70%   -0.11   -20.7%   92.8%    4.81    0.900
M03_con_banda            -0.35%   -0.06   -15.1%   91.3%    3.77    0.949
efectivo (BIL)            1.53%            -0.4%
cuenta sin remunerar      0.00%   (lo que de verdad cobra la cuenta: 0%)

  CRITERIOS REGISTRADOS
  corte train/test: 2020-11-05

  M02_tendencia
    anual -0.08%  vs comprar y mantener -0.50%  -> bate
    train: +0.55% vs -0.99%  -> bate
    test : -0.39% vs +0.66%  -> NO bate
    VEREDICTO: NO PASA: por debajo del efectivo

  M03_momentum_12_1
    anual -0.35%  vs comprar y mantener -0.50%  -> bate
    train: -0.63% vs -0.99%  -> bate
    test : +1.05% vs +0.66%  -> bate
    VEREDICTO: NO PASA: por debajo del efectivo

  M02_mas_M03
    anual -0.70%  vs comprar y mantener -0.50%  -> NO bate
    train: -0.30% vs -0.99%  -> bate
    test : -0.39% vs +0.66%  -> NO bate
    VEREDICTO: NO PASA: forma peor de estar invertido
    I29: mejor Sharpe (-0.11 vs -0.13) pero MENOS dinero. No es una mejora del beneficio.

======================================================================
cripto_sesgo_extremo  (2 activos)
======================================================================

VARIANTE                  ANUAL  SHARPE    MAXDD   EXPOS   ROT/A    FINAL
----------------------------------------------------------------------
comprar_y_mantener       60.71%    0.82   -81.3%   94.5%    0.17  300.215
M02_tendencia            52.20%    0.83   -66.3%   69.9%    1.66  156.096
M03_momentum_12_1        51.12%    0.79   -79.8%   69.9%    2.33  143.365
M02_mas_M03              50.53%    0.83   -64.8%   63.0%    1.83  136.780
M03_con_banda            50.13%    0.80   -78.7%   68.3%    2.24  132.468
efectivo (BIL)            1.53%            -0.4%
cuenta sin remunerar      0.00%   (lo que de verdad cobra la cuenta: 0%)

  CRITERIOS REGISTRADOS
  corte train/test: 2021-12-31

  M02_tendencia
    anual +52.20%  vs comprar y mantener +60.71%  -> NO bate
    train: +97.48% vs +120.08%  -> NO bate
    test : +16.85% vs +23.16%  -> NO bate
    VEREDICTO: NO PASA: forma peor de estar invertido
    I29: mejor Sharpe (0.83 vs 0.82) pero MENOS dinero. No es una mejora del beneficio.

  M03_momentum_12_1
    anual +51.12%  vs comprar y mantener +60.71%  -> NO bate
    train: +102.24% vs +120.08%  -> NO bate
    test : +13.09% vs +23.16%  -> NO bate
    VEREDICTO: NO PASA: forma peor de estar invertido

  M02_mas_M03
    anual +50.53%  vs comprar y mantener +60.71%  -> NO bate
    train: +95.71% vs +120.08%  -> NO bate
    test : +16.87% vs +23.16%  -> NO bate
    VEREDICTO: NO PASA: forma peor de estar invertido
    I29: mejor Sharpe (0.83 vs 0.82) pero MENOS dinero. No es una mejora del beneficio.

======================================================================
AJUSTADO vs SIN AJUSTAR — cuanto cambia por dividendos y splits
======================================================================
  comprar_y_mantener       ajustado  +6.26%  sin ajustar  +4.77%  diferencia +1.49 puntos/ano
  M03_momentum_12_1        ajustado  +9.24%  sin ajustar  +7.14%  diferencia +2.10 puntos/ano

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

