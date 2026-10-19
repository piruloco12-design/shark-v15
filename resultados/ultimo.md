# Validacion SHARK V15

Fecha:   2026-10-19 19:03 UTC
Commit:  4ce4eda0
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
RESULTADO: 61 pruebas pasadas, 0 fallos
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
         MISMO tamano. Ninguna correccion del motor arregla eso:
         es la resolucion del aparato, no un fallo del codigo.
  PASA   la potencia crece con el tamano del efecto (el contraste discrimina)
  PASA   queda registrado que un efecto de +0,72 puntos/ano es casi indetectable con esta muestra

==============================================================
RESULTADO: 19 pruebas pasadas, 0 fallos
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
  PASA   [B3] el recorte por efectivo queda DICHO en el setup, no escondido
  PASA   [B4] B1 queda intacto: sin declarar efectivo, el tamano no cambia

=== C) Los stops no pueden ejecutar a precios que no existieron ===
  PASA   [C1] un hueco por debajo del stop ejecuta en la barra, no en el stop
  PASA   [C2] lo mismo en el lado corto del contrafactual
  PASA   [C3] el cierre acepta la apertura de la barra, que es lo que decide un hueco

=== D) Métricas con el nombre y la unidad correctos ===
  PASA   [D1] el CAGR usa el intervalo completo, incluido el primer periodo
  PASA   [D2] el Sharpe sale de retornos diferenciales y declara su referencia
  PASA   [D3] la caida maxima diaria ve lo que la mensual no ve
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
  PASA   [F7] la vigencia sale del calendario del snapshot, no de la consulta
  PASA   [F8] el ranking se reconstruye identico desde la base de datos

=== G) La caja y los cortos ===
  PASA   [G1] la politica de caja esta declarada y por defecto NO remunera
  PASA   [G2] el libro ejecutable al contado no admite abrir cortos
  PASA   [G3] una venta que reduce un largo existente SI es ejecutable
  PASA   [G4] vender mas de lo disponible no abre un corto: se limita

====================================================================
ACEPTACION: 32 pasan, 0 FALLAN
====================================================================
====================================================================
```

## Imports
```
32/32 modulos importan
```

## Diagnostico del feed
```
Timeframe 30m | Periodo 60d | MIN_BARS 220
Providers ['yfinance', 'finnhub', 'alpha_vantage', 'twelve_data']

ACTIVO  PROVIDER    VELAS  DIAS  X/DIA  HORAS ET
IWM     yfinance      779    60   13.0  [9, 10, 11, 12, 13, 14, 15]
        2026-07-27 09:30:00-04:00  ->  2026-10-19 15:00:00-04:00
NVDA    yfinance      779    60   13.0  [9, 10, 11, 12, 13, 14, 15]
        2026-07-27 09:30:00-04:00  ->  2026-10-19 15:00:00-04:00
AMZN    yfinance      779    60   13.0  [9, 10, 11, 12, 13, 14, 15]
        2026-07-27 09:30:00-04:00  ->  2026-10-19 15:00:00-04:00
META    yfinance      779    60   13.0  [9, 10, 11, 12, 13, 14, 15]
        2026-07-27 09:30:00-04:00  ->  2026-10-19 15:00:00-04:00
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
  OK | yfinance | 779 velas
Descargando NVDA...
  OK | yfinance | 779 velas
Descargando AMZN...
  OK | yfinance | 779 velas
Descargando META...
  OK | yfinance | 779 velas

=================================================================
  FASE 1: BACKTEST COMPLETO (todo el período)
=================================================================

============================================================
IWM | FULL | Bars: 579
============================================================
Capital:     1000.00 → 988.07  (-11.93)
Señales:     64 generadas | 13 ALLOW | 51 BLOCK
Trades:      12 cerrados | 6 wins | 6 losses
Winrate:     50.0%
Avg Trade:   -0.94
Avg Win:     6.06  |  Avg Loss: 7.94
Expectancy:  -0.94 por trade
PF:          0.76
Max DD:      29.53 (3.0%)
Avg Bars:    9 velas
Regímenes:   {'BULL_TREND': 1, 'BEAR_TREND': 8, 'TREND': 3}
Señales:     {'BUY': 1, 'SELL': 11}
Bloqueos principales:
    43x  Cooldown por activo (6h)
     1x  ADX insuficiente para sniper: 20.47 < 22.0 | Score final insuficiente para sniper: 54.04 <
     1x  ADX insuficiente para sniper: 20.26 < 22.0 | Score final insuficiente para sniper: 53.91 <
     1x  ADX insuficiente para sniper: 20.09 < 22.0 | Score final insuficiente para sniper: 53.80 <
     1x  ADX insuficiente para sniper: 21.51 < 22.0 | Score final insuficiente para sniper: 54.69 <

============================================================
NVDA | FULL | Bars: 579
============================================================
Capital:     1000.00 → 946.14  (-53.86)
Señales:     48 generadas | 19 ALLOW | 29 BLOCK
Trades:      19 cerrados | 7 wins | 12 losses
Winrate:     36.8%
Avg Trade:   -2.83
Avg Win:     5.93  |  Avg Loss: 7.95
Expectancy:  -2.83 por trade
PF:          0.44
Max DD:      60.63 (6.1%)
Avg Bars:    12 velas
Regímenes:   {'BULL_TREND': 7, 'BEAR_TREND': 7, 'TREND': 5}
Señales:     {'BUY': 10, 'SELL': 9}
Bloqueos principales:
    29x  Cooldown por activo (6h)

============================================================
AMZN | FULL | Bars: 579
============================================================
Capital:     1000.00 → 994.64  (-5.36)
Señales:     85 generadas | 18 ALLOW | 67 BLOCK
Trades:      18 cerrados | 9 wins | 9 losses
Winrate:     50.0%
Avg Trade:   -0.30
Avg Win:     5.63  |  Avg Loss: 6.23
Expectancy:  -0.30 por trade
PF:          0.90
Max DD:      24.19 (2.4%)
Avg Bars:    14 velas
Regímenes:   {'BEAR_TREND': 9, 'BULL_TREND': 4, 'TREND': 5}
Señales:     {'SELL': 13, 'BUY': 5}
Bloqueos principales:
    67x  Cooldown por activo (6h)

============================================================
META | FULL | Bars: 579
============================================================
Capital:     1000.00 → 1009.45  (+9.45)
Señales:     71 generadas | 16 ALLOW | 55 BLOCK
Trades:      15 cerrados | 8 wins | 7 losses
Winrate:     53.3%
Avg Trade:   0.65
Avg Win:     6.14  |  Avg Loss: 5.64
Expectancy:  0.65 por trade
PF:          1.25
Max DD:      24.49 (2.5%)
Avg Bars:    13 velas
Regímenes:   {'BEAR_TREND': 4, 'TREND': 2, 'BULL_TREND': 9}
Señales:     {'SELL': 5, 'BUY': 10}
Bloqueos principales:
    55x  Cooldown por activo (6h)


#################################################################
  CONSOLIDADO FULL PERIOD — 4 activos
#################################################################
  Señales:     268 generadas | 66 ALLOW | 202 BLOCK
  Trades:      64 cerrados | 30 wins | 34 losses
  Winrate:     46.9%
  Avg Trade:   -0.95
  Avg Win:     5.92  |  Avg Loss: 7.01
  Expectancy:  -0.95 por trade
  PF:          0.75
  PnL total:   -61.70
  Peor DD:     60.63
  -------------------------------------------------------------
  Suma PnL trades:  -60.81   (debe cuadrar con PnL total)
  ✅ Cuadra (dif. 0.89, son costes de trades aún abiertos)
#################################################################

  VEREDICTO:
  ❌  NO HAY EDGE. Expectancy negativa.


=================================================================
  FASE 2: WALK-FORWARD (70% train / 30% test)
=================================================================

--- IWM TRAIN ---
  ============================================================
  IWM | TRAIN | Bars: 345
  ============================================================
  Capital:     1000.00 → 974.15  (-25.85)
  Señales:     44 generadas | 9 ALLOW | 35 BLOCK
  Trades:      8 cerrados | 3 wins | 5 losses
  Winrate:     37.5%
  Avg Trade:   -3.16
  Avg Win:     5.42  |  Avg Loss: 8.30
  Expectancy:  -3.16 por trade
  PF:          0.39
  Max DD:      27.61 (2.8%)
  Avg Bars:    8 velas
  Regímenes:   {'BULL_TREND': 1, 'BEAR_TREND': 6, 'TREND': 1}
  Señales:     {'BUY': 1, 'SELL': 7}
  Bloqueos principales:
      28x  Cooldown por activo (6h)
       1x  ADX insuficiente para sniper: 20.47 < 22.0 | Score final insuficiente para sniper: 54.04 <
       1x  ADX insuficiente para sniper: 20.26 < 22.0 | Score final insuficiente para sniper: 53.91 <
       1x  ADX insuficiente para sniper: 20.09 < 22.0 | Score final insuficiente para sniper: 53.80 <
       1x  ADX insuficiente para sniper: 21.51 < 22.0 | Score final insuficiente para sniper: 54.69 <

--- IWM TEST ---
  ============================================================
  IWM | TEST | Bars: 234
  ============================================================
  Capital:     1000.00 → 1012.55  (+12.55)
  Señales:     20 generadas | 5 ALLOW | 15 BLOCK
  Trades:      4 cerrados | 3 wins | 1 losses
  Winrate:     75.0%
  Avg Trade:   3.30
  Avg Win:     6.49  |  Avg Loss: 6.26
  Expectancy:  3.30 por trade
  PF:          3.11
  Max DD:      8.53 (0.8%)
  Avg Bars:    7 velas
  Regímenes:   {'BEAR_TREND': 2, 'TREND': 2}
  Señales:     {'SELL': 4}
  Bloqueos principales:
      14x  Cooldown por activo (6h)
       1x  ADX insuficiente para sniper: 20.88 < 22.0 | Score final insuficiente para sniper: 54.30 <

--- NVDA TRAIN ---
  ============================================================
  NVDA | TRAIN | Bars: 345
  ============================================================
  Capital:     1000.00 → 945.21  (-54.79)
  Señales:     28 generadas | 11 ALLOW | 17 BLOCK
  Trades:      11 cerrados | 3 wins | 8 losses
  Winrate:     27.3%
  Avg Trade:   -4.98
  Avg Win:     5.30  |  Avg Loss: 8.84
  Expectancy:  -4.98 por trade
  PF:          0.22
  Max DD:      60.63 (6.1%)
  Avg Bars:    11 velas
  Regímenes:   {'BULL_TREND': 6, 'BEAR_TREND': 3, 'TREND': 2}
  Señales:     {'BUY': 7, 'SELL': 4}
  Bloqueos principales:
      17x  Cooldown por activo (6h)

--- NVDA TEST ---
  ============================================================
  NVDA | TEST | Bars: 234
  ============================================================
  Capital:     1000.00 → 1000.98  (+0.98)
  Señales:     20 generadas | 8 ALLOW | 12 BLOCK
  Trades:      8 cerrados | 4 wins | 4 losses
  Winrate:     50.0%
  Avg Trade:   0.12
  Avg Win:     6.77  |  Avg Loss: 6.53
  Expectancy:  0.12 por trade
  PF:          1.04
  Max DD:      20.73 (2.1%)
  Avg Bars:    13 velas
  Regímenes:   {'BULL_TREND': 1, 'TREND': 3, 'BEAR_TREND': 4}
  Señales:     {'BUY': 3, 'SELL': 5}
  Bloqueos principales:
      12x  Cooldown por activo (6h)

--- AMZN TRAIN ---
  ============================================================
  AMZN | TRAIN | Bars: 345
  ============================================================
  Capital:     1000.00 → 1011.37  (+11.37)
  Señales:     48 generadas | 10 ALLOW | 38 BLOCK
  Trades:      10 cerrados | 6 wins | 4 losses
  Winrate:     60.0%
  Avg Trade:   1.14
  Avg Win:     5.67  |  Avg Loss: 5.67
  Expectancy:  1.14 por trade
  PF:          1.50
  Max DD:      24.19 (2.4%)
  Avg Bars:    14 velas
  Regímenes:   {'BEAR_TREND': 6, 'BULL_TREND': 1, 'TREND': 3}
  Señales:     {'SELL': 8, 'BUY': 2}
  Bloqueos principales:
      38x  Cooldown por activo (6h)

--- AMZN TEST ---
  ============================================================
  AMZN | TEST | Bars: 234
  ============================================================
  Capital:     1000.00 → 983.46  (-16.54)
  Señales:     37 generadas | 8 ALLOW | 29 BLOCK
  Trades:      8 cerrados | 3 wins | 5 losses
  Winrate:     37.5%
  Avg Trade:   -2.07
  Avg Win:     5.48  |  Avg Loss: 6.60
  Expectancy:  -2.07 por trade
  PF:          0.50
  Max DD:      23.83 (2.4%)
  Avg Bars:    14 velas
  Regímenes:   {'BEAR_TREND': 3, 'TREND': 2, 'BULL_TREND': 3}
  Señales:     {'SELL': 5, 'BUY': 3}
  Bloqueos principales:
      29x  Cooldown por activo (6h)

--- META TRAIN ---
  ============================================================
  META | TRAIN | Bars: 345
  ============================================================
  Capital:     1000.00 → 1003.49  (+3.49)
  Señales:     40 generadas | 11 ALLOW | 29 BLOCK
  Trades:      10 cerrados | 5 wins | 5 losses
  Winrate:     50.0%
  Avg Trade:   0.37
  Avg Win:     6.32  |  Avg Loss: 5.59
  Expectancy:  0.37 por trade
  PF:          1.13
  Max DD:      24.49 (2.5%)
  Avg Bars:    9 velas
  Regímenes:   {'BEAR_TREND': 3, 'TREND': 2, 'BULL_TREND': 5}
  Señales:     {'SELL': 4, 'BUY': 6}
  Bloqueos principales:
      29x  Cooldown por activo (6h)

--- META TEST ---
  ============================================================
  META | TEST | Bars: 234
  ============================================================
  Capital:     1000.00 → 994.51  (-5.49)
  Señales:     25 generadas | 6 ALLOW | 19 BLOCK
  Trades:      5 cerrados | 2 wins | 3 losses
  Winrate:     40.0%
  Avg Trade:   -1.05
  Avg Win:     5.72  |  Avg Loss: 5.56
  Expectancy:  -1.05 por trade
  PF:          0.69
  Max DD:      11.61 (1.2%)
  Avg Bars:    17 velas
  Regímenes:   {'BULL_TREND': 4, 'BEAR_TREND': 1}
  Señales:     {'BUY': 4, 'SELL': 1}
  Bloqueos principales:
      19x  Cooldown por activo (6h)


#################################################################
  CONSOLIDADO TRAIN (IN-SAMPLE) — 4 activos
#################################################################
  Señales:     160 generadas | 41 ALLOW | 119 BLOCK
  Trades:      39 cerrados | 17 wins | 22 losses
  Winrate:     43.6%
  Avg Trade:   -1.67
  Avg Win:     5.75  |  Avg Loss: 7.40
  Expectancy:  -1.67 por trade
  PF:          0.60
  PnL total:   -65.78
  Peor DD:     60.63
  -------------------------------------------------------------
  Suma PnL trades:  -65.02   (debe cuadrar con PnL total)
  ✅ Cuadra (dif. 0.76, son costes de trades aún abiertos)
#################################################################

  VEREDICTO:
  ❌  NO HAY EDGE. Expectancy negativa.


#################################################################
  CONSOLIDADO TEST (OUT-OF-SAMPLE) — 4 activos
#################################################################
  Señales:     102 generadas | 27 ALLOW | 75 BLOCK
  Trades:      25 cerrados | 12 wins | 13 losses
  Winrate:     48.0%
  Avg Trade:   -0.30
  Avg Win:     6.20  |  Avg Loss: 6.31
  Expectancy:  -0.30 por trade
  PF:          0.91
  PnL total:   -8.50
  Peor DD:     23.83
  -------------------------------------------------------------
  Suma PnL trades:  -7.59   (debe cuadrar con PnL total)
  ✅ Cuadra (dif. 0.90, son costes de trades aún abiertos)
#################################################################

  VEREDICTO:
  ❌  NO HAY EDGE. Expectancy negativa.


=================================================================
  COMPARACIÓN TRAIN vs TEST
=================================================================

  IWM:
    TRAIN: 8 trades | WR 37.5% | PF 0.39 | Exp -3.16
    TEST:  4 trades | WR 75.0% | PF 3.11 | Exp 3.30
    ⚠️  Pocos trades para comparar

  NVDA:
    TRAIN: 11 trades | WR 27.3% | PF 0.22 | Exp -4.98
    TEST:  8 trades | WR 50.0% | PF 1.04 | Exp 0.12
    ✅  Consistente entre train y test

  AMZN:
    TRAIN: 10 trades | WR 60.0% | PF 1.50 | Exp 1.14
    TEST:  8 trades | WR 37.5% | PF 0.50 | Exp -2.07
    ⚠️  Degradación significativa train→test

  META:
    TRAIN: 10 trades | WR 50.0% | PF 1.13 | Exp 0.37
    TEST:  5 trades | WR 40.0% | PF 0.69 | Exp -1.05
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
  OK | yfinance | 3771 velas
Descargando NVDA...
  OK | yfinance | 3771 velas
Descargando AMZN...
  OK | yfinance | 3771 velas
Descargando META...
  OK | yfinance | 3625 velas

=================================================================
  FASE 1: BACKTEST COMPLETO (todo el período)
=================================================================

============================================================
IWM | FULL | Bars: 3571
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
NVDA | FULL | Bars: 3571
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
AMZN | FULL | Bars: 3571
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
META | FULL | Bars: 3425
============================================================
Capital:     1000.00 → 1075.10  (+75.10)
Señales:     182 generadas | 127 ALLOW | 55 BLOCK
Trades:      126 cerrados | 61 wins | 65 losses
Winrate:     48.4%
Avg Trade:   0.60
Avg Win:     7.13  |  Avg Loss: 5.53
Expectancy:  0.60 por trade
PF:          1.21
Max DD:      55.89 (5.6%)
Avg Bars:    12 velas
Regímenes:   {'BULL_TREND': 74, 'BEAR_TREND': 31, 'TREND': 21}
Señales:     {'BUY': 93, 'SELL': 33}
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
  Trades:      496 cerrados | 240 wins | 256 losses
  Winrate:     48.4%
  Avg Trade:   0.42
  Avg Win:     6.86  |  Avg Loss: 5.61
  Expectancy:  0.42 por trade
  PF:          1.15
  PnL total:   +209.59
  Peor DD:     106.35
  -------------------------------------------------------------
  Suma PnL trades:  +209.79   (debe cuadrar con PnL total)
  ✅ Cuadra (dif. 0.20, son costes de trades aún abiertos)
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
  IWM | TEST | Bars: 1132
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
  NVDA | TEST | Bars: 1132
  ============================================================
  Capital:     1000.00 → 1071.52  (+71.52)
  Señales:     63 generadas | 40 ALLOW | 23 BLOCK
  Trades:      40 cerrados | 24 wins | 16 losses
  Winrate:     60.0%
  Avg Trade:   1.79
  Avg Win:     6.53  |  Avg Loss: 5.33
  Expectancy:  1.79 por trade
  PF:          1.84
  Max DD:      17.80 (1.8%)
  Avg Bars:    9 velas
  Regímenes:   {'BEAR_TREND': 6, 'BULL_TREND': 24, 'TREND': 10}
  Señales:     {'SELL': 8, 'BUY': 32}
  Bloqueos principales:
      16x  Cooldown por activo (6h)
       1x  ADX insuficiente para sniper: 20.01 < 22.0 | Score final insuficiente para sniper: 53.76 <
       1x  ADX insuficiente para sniper: 20.82 < 22.0 | Score final insuficiente para sniper: 54.26 <
       1x  ADX insuficiente para sniper: 20.90 < 22.0 | Score final insuficiente para sniper: 54.31 <
       1x  ADX insuficiente para sniper: 20.41 < 22.0 | Score final insuficiente para sniper: 54.01 <

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
  AMZN | TEST | Bars: 1132
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
  META | TRAIN | Bars: 2337
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
  Capital:     1000.00 → 1061.42  (+61.42)
  Señales:     63 generadas | 44 ALLOW | 19 BLOCK
  Trades:      43 cerrados | 23 wins | 20 losses
  Winrate:     53.5%
  Avg Trade:   1.43
  Avg Win:     7.73  |  Avg Loss: 5.82
  Expectancy:  1.43 por trade
  PF:          1.53
  Max DD:      48.16 (4.8%)
  Avg Bars:    13 velas
  Regímenes:   {'BEAR_TREND': 10, 'BULL_TREND': 25, 'TREND': 8}
  Señales:     {'SELL': 12, 'BUY': 31}
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
  Señales:     230 generadas | 149 ALLOW | 81 BLOCK
  Trades:      147 cerrados | 71 wins | 76 losses
  Winrate:     48.3%
  Avg Trade:   0.44
  Avg Win:     6.82  |  Avg Loss: 5.51
  Expectancy:  0.44 por trade
  PF:          1.16
  PnL total:   +64.87
  Peor DD:     74.11
  -------------------------------------------------------------
  Suma PnL trades:  +65.07   (debe cuadrar con PnL total)
  ✅ Cuadra (dif. 0.20, son costes de trades aún abiertos)
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
    TEST:  40 trades | WR 60.0% | PF 1.84 | Exp 1.79
    ✅  Consistente entre train y test

  AMZN:
    TRAIN: 95 trades | WR 47.4% | PF 1.11 | Exp 0.33
    TEST:  36 trades | WR 44.4% | PF 0.93 | Exp -0.20
    ✅  Consistente entre train y test

  META:
    TRAIN: 83 trades | WR 45.8% | PF 1.05 | Exp 0.16
    TEST:  43 trades | WR 53.5% | PF 1.53 | Exp 1.43
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
  IWM     yfinance      779 velas
  NVDA    yfinance      779 velas
  AMZN    yfinance      779 velas
  META    yfinance      779 velas

Operaciones totales con la config actual: 64

==============================================================
1) BOOTSTRAP DE LA EXPECTATIVA
==============================================================
Operaciones:            64
Expectativa observada:  -0.9502 € por operación
Intervalo 90%:          -2.3906  a  +0.4670
Prob. expectativa > 0:  14.1%

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
   Drawdown mediano:        8.60%
   Drawdown percentil 95:   11.31%
   Peor drawdown simulado:  14.56%
   Capital final (fijo):    939.19 €

B) REMUESTREO: si las próximas operaciones salieran de
   esta misma distribución
   Capital final, percentil 5:   846.27 €
   Capital final, mediana:       940.34 €
   Capital final, percentil 95:  1030.44 €
   Drawdown percentil 95:        16.79%
   Prob. terminar en pérdida:    87.1%
   Prob. perder la mitad:        0.0%

LECTURA: el drawdown que hay que estar dispuesto a aguantar es
         del 11.3%, no el que salió en el histórico: el orden
         de las operaciones es azar y la racha mala no tiene por
         qué haber caído dentro del periodo de prueba.
         El remuestreo da 87% de probabilidad de acabar
         en pérdida sobre otras 64 operaciones.

==============================================================
3) BARRIDO DE PARÁMETROS (SL / TP)
==============================================================

   SL    TP   R:R   OPS    WR%    EXPECT     PF  VEREDICTO
--------------------------------------------------------------
  1.5   2.0  1.33    76   39.5   -2.0465   0.53
  1.5   2.5  1.67    72   36.1   -1.9836   0.58
  1.5   3.0  2.00    67   34.3   -1.5475   0.68
  1.5   3.5  2.33    65   32.3   -1.3863   0.72
  2.0   2.0  1.00    70   47.1   -1.4191   0.61
  2.0   2.5  1.25    64   46.9   -0.9502   0.75 <-- CONFIG ACTUAL
  2.0   3.0  1.50    60   45.0   -0.5498   0.86
  2.0   3.5  1.75    60   38.3   -1.0152   0.76
  2.5   2.0  0.80    69   52.2   -0.9911   0.68
  2.5   2.5  1.00    64   51.6   -0.5684   0.82
  2.5   3.0  1.20    59   49.2   -0.3117   0.91
  2.5   3.5  1.40    58   41.4   -0.8473   0.78
  3.0   2.0  0.67    66   56.1   -0.8902   0.67
  3.0   2.5  0.83    61   55.7   -0.4969   0.82
  3.0   3.0  1.00    58   51.7   -0.3953   0.87
  3.0   3.5  1.17    55   45.5   -0.7167   0.79

Combinaciones con expectativa positiva: 0 de 16
Configuración actual (SL 2.0 / TP 2.5): expectativa -0.9502, PF 0.75
Vecinos inmediatos con expectativa positiva: 0 de 8

LECTURA: la configuración actual no tiene expectativa positiva
         en este periodo. Si otras combinaciones sí, ojo: elegir
         ahora la mejor de la tabla ES sobreajustar.

==============================================================
4) ECONOMÍA REAL: ¿QUÉ SIGNIFICA ESTO EN DINERO?
==============================================================
Periodo cubierto:       0.2 años
Operaciones:            64  ->  269.1 al año
Riesgo por operación:   5.00 € (0.5% de 1000 €)
Expectativa en riesgo:  -0.190 R por operación

RENTABILIDAD ANUAL SOBRE 1000 €
  pesimista (p05)  :  -643.43 €/año  =  -64.34% anual
  central          :  -255.75 €/año  =  -25.57% anual
  optimista (p95)  :  +125.70 €/año  =  +12.57% anual

CAPITAL NECESARIO PARA SACAR 1.000 €/MES (12.000 €/año)
  pesimista (p05)  : imposible, la expectativa es negativa
  central          : imposible, la expectativa es negativa
  optimista (p95)  :         95,467 €

LECTURA: con expectativa central negativa no hay capital que
         arregle esto. El problema no es el tamaño de la cuenta.

JSON escrito en resultados/robustez_30m.json

==============================================================
```

## Proveedores de datos
```
PRUEBA DE PROVEEDORES — cada uno por separado
Cascada por defecto: ['yfinance', 'finnhub', 'alpha_vantage', 'twelve_data']

  OK    yfinance   SPY         3771 velas  2011-10-19 -> 2026-10-19
  FALLA stooq      SPY       ValueError: No se pudo descargar SPY con ningún provider. Detalles: ['stooq: Stooq
  OK    yfinance   BTC-USD     4416 velas  2014-09-17 -> 2026-10-19
  OK    coinbase   BTC-USD     4110 velas  2015-07-20 -> 2026-10-19
  FALLA stooq      GLD       ValueError: No se pudo descargar GLD con ningún provider. Detalles: ['stooq: Stooq

CRUCE yfinance vs stooq en SPY (ultimos cierres comunes)
  no se pudo cruzar: ValueError: No se pudo descargar SPY con ningún provider. Detalles: ['stooq: Stooq no sirvio spy.us: https://stooq.com/q/d/l/: sin datos (<!DOCTYPE html><html><head><meta charset="utf-8"><meta name=) | https://stooq.pl/q/d/l/: sin datos (<!DOCTYPE html><html><head><meta charset="utf-8"><meta name=)']
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
comprar_y_mantener        6.29%    0.72   -16.6%   93.3%    0.07    2.481
M02_tendencia             6.23%    0.66   -22.3%   93.3%    3.78    2.460
M03_momentum_12_1         9.93%    0.62   -27.2%   93.3%    5.87    4.094
M02_mas_M03               9.90%    0.62   -27.9%   93.3%    5.80    4.075
M03_con_banda             9.16%    0.64   -24.5%   84.1%    5.29    3.688
efectivo (BIL)            1.53%            -0.4%
cuenta sin remunerar      0.00%   (lo que de verdad cobra la cuenta: 0%)

  CRITERIOS REGISTRADOS
  corte train/test: 2020-10-15

  M02_tendencia
    anual +6.23%  vs comprar y mantener +6.29%  -> NO bate
    train: +5.22% vs +3.84%  -> bate
    test : +4.65% vs +6.41%  -> NO bate
    VEREDICTO: NO PASA: forma peor de estar invertido

  M03_momentum_12_1
    anual +9.93%  vs comprar y mantener +6.29%  -> bate
    train: +7.06% vs +3.84%  -> bate
    test : +10.04% vs +6.41%  -> bate
    VEREDICTO: PASA

  M02_mas_M03
    anual +9.90%  vs comprar y mantener +6.29%  -> bate
    train: +6.86% vs +3.84%  -> bate
    test : +10.27% vs +6.41%  -> bate
    VEREDICTO: PASA

======================================================================
clase_renta_variable  (14 activos)
======================================================================

VARIANTE                  ANUAL  SHARPE    MAXDD   EXPOS   ROT/A    FINAL
----------------------------------------------------------------------
comprar_y_mantener       12.61%    0.92   -23.3%   93.3%    0.07    5.857
M02_tendencia            12.39%    0.95   -19.1%   93.3%    3.67    5.691
M03_momentum_12_1        13.31%    1.03   -16.0%   93.3%    4.84    6.428
M02_mas_M03              13.43%    1.01   -16.0%   93.3%    4.96    6.530
M03_con_banda            12.53%    1.04   -14.4%   86.4%    4.39    5.798
efectivo (BIL)            1.53%            -0.4%
cuenta sin remunerar      0.00%   (lo que de verdad cobra la cuenta: 0%)

  CRITERIOS REGISTRADOS
  corte train/test: 2020-10-15

  M02_tendencia
    anual +12.39%  vs comprar y mantener +12.61%  -> NO bate
    train: +11.28% vs +11.31%  -> NO bate
    test : +9.48% vs +8.99%  -> bate
    VEREDICTO: NO PASA: forma peor de estar invertido
    I29: mejor Sharpe (0.95 vs 0.92) pero MENOS dinero. No es una mejora del beneficio.

  M03_momentum_12_1
    anual +13.31%  vs comprar y mantener +12.61%  -> bate
    train: +12.91% vs +11.31%  -> bate
    test : +9.98% vs +8.99%  -> bate
    VEREDICTO: PASA

  M02_mas_M03
    anual +13.43%  vs comprar y mantener +12.61%  -> bate
    train: +12.97% vs +11.31%  -> bate
    test : +10.18% vs +8.99%  -> bate
    VEREDICTO: PASA

======================================================================
clase_materias_primas  (7 activos)
======================================================================

VARIANTE                  ANUAL  SHARPE    MAXDD   EXPOS   ROT/A    FINAL
----------------------------------------------------------------------
comprar_y_mantener        0.94%    0.06   -60.0%   93.3%    0.07    1.149
M02_tendencia            -0.77%   -0.04   -68.5%   82.8%    5.41    0.892
M03_momentum_12_1         0.54%    0.03   -56.9%   82.2%    4.73    1.083
M02_mas_M03              -0.30%   -0.01   -65.9%   80.0%    4.81    0.957
M03_con_banda             0.89%    0.05   -55.8%   80.2%    4.30    1.141
efectivo (BIL)            1.53%            -0.4%
cuenta sin remunerar      0.00%   (lo que de verdad cobra la cuenta: 0%)

  CRITERIOS REGISTRADOS
  corte train/test: 2020-10-15

  M02_tendencia
    anual -0.77%  vs comprar y mantener +0.94%  -> NO bate
    train: -9.61% vs -7.60%  -> NO bate
    test : +9.90% vs +9.62%  -> bate
    VEREDICTO: NO PASA: forma peor de estar invertido

  M03_momentum_12_1
    anual +0.54%  vs comprar y mantener +0.94%  -> NO bate
    train: -5.79% vs -7.60%  -> bate
    test : +7.78% vs +9.62%  -> NO bate
    VEREDICTO: NO PASA: forma peor de estar invertido

  M02_mas_M03
    anual -0.30%  vs comprar y mantener +0.94%  -> NO bate
    train: -7.93% vs -7.60%  -> NO bate
    test : +9.25% vs +9.62%  -> NO bate
    VEREDICTO: NO PASA: forma peor de estar invertido

======================================================================
clase_bonos  (5 activos)
======================================================================

VARIANTE                  ANUAL  SHARPE    MAXDD   EXPOS   ROT/A    FINAL
----------------------------------------------------------------------
comprar_y_mantener        1.69%    0.29   -20.5%   93.3%    0.07    1.283
M02_tendencia             1.86%    0.42   -10.3%   81.7%    3.52    1.317
M03_momentum_12_1         1.35%    0.26   -17.9%   85.6%    3.20    1.222
M02_mas_M03               1.74%    0.39   -10.4%   81.1%    4.18    1.292
M03_con_banda             1.40%    0.28   -17.6%   83.4%    2.90    1.229
efectivo (BIL)            1.53%            -0.4%
cuenta sin remunerar      0.00%   (lo que de verdad cobra la cuenta: 0%)

  CRITERIOS REGISTRADOS
  corte train/test: 2020-10-15

  M02_tendencia
    anual +1.86%  vs comprar y mantener +1.69%  -> bate
    train: +2.93% vs +3.65%  -> NO bate
    test : +0.56% vs -1.04%  -> bate
    VEREDICTO: INCONCLUSO: no se sostiene en las dos mitades

  M03_momentum_12_1
    anual +1.35%  vs comprar y mantener +1.69%  -> NO bate
    train: +2.98% vs +3.65%  -> NO bate
    test : -0.64% vs -1.04%  -> bate
    VEREDICTO: NO PASA: forma peor de estar invertido

  M02_mas_M03
    anual +1.74%  vs comprar y mantener +1.69%  -> bate
    train: +2.68% vs +3.65%  -> NO bate
    test : +0.56% vs -1.04%  -> bate
    VEREDICTO: INCONCLUSO: no se sostiene en las dos mitades

======================================================================
clase_divisas  (5 activos)
======================================================================

VARIANTE                  ANUAL  SHARPE    MAXDD   EXPOS   ROT/A    FINAL
----------------------------------------------------------------------
comprar_y_mantener       -0.55%   -0.14   -19.7%   93.3%    0.07    0.921
M02_tendencia            -0.08%   -0.01   -15.0%   93.3%    5.16    0.988
M03_momentum_12_1        -0.37%   -0.06   -15.6%   93.3%    4.16    0.946
M02_mas_M03              -0.71%   -0.11   -20.7%   92.8%    4.94    0.900
M03_con_banda            -0.37%   -0.07   -15.1%   91.3%    3.90    0.946
efectivo (BIL)            1.53%            -0.4%
cuenta sin remunerar      0.00%   (lo que de verdad cobra la cuenta: 0%)

  CRITERIOS REGISTRADOS
  corte train/test: 2020-10-15

  M02_tendencia
    anual -0.08%  vs comprar y mantener -0.55%  -> bate
    train: +0.40% vs -1.14%  -> bate
    test : -0.91% vs +0.51%  -> NO bate
    VEREDICTO: NO PASA: por debajo del efectivo

  M03_momentum_12_1
    anual -0.37%  vs comprar y mantener -0.55%  -> bate
    train: -0.78% vs -1.14%  -> bate
    test : +0.47% vs +0.51%  -> NO bate
    VEREDICTO: NO PASA: por debajo del efectivo

  M02_mas_M03
    anual -0.71%  vs comprar y mantener -0.55%  -> NO bate
    train: -0.45% vs -1.14%  -> bate
    test : -0.91% vs +0.51%  -> NO bate
    VEREDICTO: NO PASA: forma peor de estar invertido
    I29: mejor Sharpe (-0.11 vs -0.14) pero MENOS dinero. No es una mejora del beneficio.

======================================================================
cripto_sesgo_extremo  (2 activos)
======================================================================

VARIANTE                  ANUAL  SHARPE    MAXDD   EXPOS   ROT/A    FINAL
----------------------------------------------------------------------
comprar_y_mantener       62.52%    0.84   -81.3%   94.5%    0.17  334.263
M02_tendencia            52.52%    0.83   -66.3%   70.3%    1.67  156.268
M03_momentum_12_1        52.04%    0.81   -79.8%   69.7%    2.26  150.498
M02_mas_M03              50.84%    0.84   -64.8%   63.4%    1.84  136.931
M03_con_banda            51.01%    0.81   -78.7%   68.2%    2.17  138.789
efectivo (BIL)            1.53%            -0.4%
cuenta sin remunerar      0.00%   (lo que de verdad cobra la cuenta: 0%)

  CRITERIOS REGISTRADOS
  corte train/test: 2021-12-18

  M02_tendencia
    anual +52.52%  vs comprar y mantener +62.52%  -> NO bate
    train: +99.33% vs +122.27%  -> NO bate
    test : +16.81% vs +23.40%  -> NO bate
    VEREDICTO: NO PASA: forma peor de estar invertido

  M03_momentum_12_1
    anual +52.04%  vs comprar y mantener +62.52%  -> NO bate
    train: +104.17% vs +122.27%  -> NO bate
    test : +14.21% vs +23.40%  -> NO bate
    VEREDICTO: NO PASA: forma peor de estar invertido

  M02_mas_M03
    anual +50.84%  vs comprar y mantener +62.52%  -> NO bate
    train: +97.54% vs +122.27%  -> NO bate
    test : +16.83% vs +23.40%  -> NO bate
    VEREDICTO: NO PASA: forma peor de estar invertido

======================================================================
AJUSTADO vs SIN AJUSTAR — cuanto cambia por dividendos y splits
======================================================================
  comprar_y_mantener       ajustado  +6.29%  sin ajustar  +4.80%  diferencia +1.49 puntos/ano
  M03_momentum_12_1        ajustado  +9.93%  sin ajustar  +7.82%  diferencia +2.11 puntos/ano

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

