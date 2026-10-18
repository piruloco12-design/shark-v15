# Validacion SHARK V15

Fecha:   2026-10-18 12:48 UTC
Commit:  813c222e
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
RESULTADO: 53 pruebas pasadas, 0 fallos
==============================================================
  PASA   en Render con disco montado no avisa

==============================================================
RESULTADO: 28 pruebas pasadas, 0 fallos
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
```

## Imports
```
18/18 modulos importan
```

## Diagnostico del feed
```
Timeframe 30m | Periodo 60d | MIN_BARS 220
Providers ['yfinance', 'finnhub', 'alpha_vantage', 'twelve_data']

ACTIVO  PROVIDER    VELAS  DIAS  X/DIA  HORAS ET
IWM     yfinance      780    60   13.0  [9, 10, 11, 12, 13, 14, 15]
        2026-07-24 09:30:00-04:00  ->  2026-10-16 15:30:00-04:00
NVDA    yfinance      780    60   13.0  [9, 10, 11, 12, 13, 14, 15]
        2026-07-24 09:30:00-04:00  ->  2026-10-16 15:30:00-04:00
AMZN    yfinance      780    60   13.0  [9, 10, 11, 12, 13, 14, 15]
        2026-07-24 09:30:00-04:00  ->  2026-10-16 15:30:00-04:00
META    yfinance      780    60   13.0  [9, 10, 11, 12, 13, 14, 15]
        2026-07-24 09:30:00-04:00  ->  2026-10-16 15:30:00-04:00
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
Capital:     1000.00 → 982.73  (-17.27)
Señales:     67 generadas | 14 ALLOW | 53 BLOCK
Trades:      13 cerrados | 6 wins | 7 losses
Winrate:     46.1%
Avg Trade:   -0.55
Avg Win:     5.44  |  Avg Loss: 5.70
Expectancy:  -0.55 por trade
PF:          0.82
Max DD:      28.85 (2.9%)
Avg Bars:    9 velas
Regímenes:   {'BULL_TREND': 2, 'BEAR_TREND': 8, 'TREND': 3}
Señales:     {'BUY': 2, 'SELL': 11}
Bloqueos principales:
    43x  Cooldown por activo (6h)
     1x  ADX insuficiente para sniper: 21.64 < 22.0 | Score final insuficiente para sniper: 54.78 <
     1x  ADX insuficiente para sniper: 21.41 < 22.0 | Score final insuficiente para sniper: 54.63 <
     1x  ADX insuficiente para sniper: 20.47 < 22.0 | Score final insuficiente para sniper: 54.04 <
     1x  ADX insuficiente para sniper: 20.26 < 22.0 | Score final insuficiente para sniper: 53.91 <

============================================================
NVDA | FULL | Bars: 580
============================================================
Capital:     1000.00 → 977.10  (-22.90)
Señales:     47 generadas | 19 ALLOW | 28 BLOCK
Trades:      18 cerrados | 7 wins | 11 losses
Winrate:     38.9%
Avg Trade:   -0.95
Avg Win:     5.77  |  Avg Loss: 5.22
Expectancy:  -0.95 por trade
PF:          0.70
Max DD:      33.90 (3.4%)
Avg Bars:    12 velas
Regímenes:   {'BULL_TREND': 7, 'BEAR_TREND': 7, 'TREND': 4}
Señales:     {'BUY': 10, 'SELL': 8}
Bloqueos principales:
    28x  Cooldown por activo (6h)

============================================================
AMZN | FULL | Bars: 580
============================================================
Capital:     1000.00 → 1025.87  (+25.87)
Señales:     84 generadas | 18 ALLOW | 66 BLOCK
Trades:      17 cerrados | 11 wins | 6 losses
Winrate:     64.7%
Avg Trade:   1.92
Avg Win:     5.96  |  Avg Loss: 5.49
Expectancy:  1.92 por trade
PF:          1.99
Max DD:      14.72 (1.5%)
Avg Bars:    13 velas
Regímenes:   {'BEAR_TREND': 10, 'TREND': 4, 'BULL_TREND': 3}
Señales:     {'SELL': 12, 'BUY': 5}
Bloqueos principales:
    66x  Cooldown por activo (6h)

============================================================
META | FULL | Bars: 580
============================================================
Capital:     1000.00 → 1012.71  (+12.71)
Señales:     66 generadas | 14 ALLOW | 52 BLOCK
Trades:      14 cerrados | 8 wins | 6 losses
Winrate:     57.1%
Avg Trade:   1.16
Avg Win:     6.02  |  Avg Loss: 5.32
Expectancy:  1.16 por trade
PF:          1.51
Max DD:      22.82 (2.3%)
Avg Bars:    17 velas
Regímenes:   {'TREND': 3, 'BEAR_TREND': 2, 'BULL_TREND': 9}
Señales:     {'SELL': 4, 'BUY': 10}
Bloqueos principales:
    52x  Cooldown por activo (6h)


#################################################################
  CONSOLIDADO FULL PERIOD — 4 activos
#################################################################
  Señales:     264 generadas | 65 ALLOW | 199 BLOCK
  Trades:      62 cerrados | 32 wins | 30 losses
  Winrate:     51.6%
  Avg Trade:   0.40
  Avg Win:     5.84  |  Avg Loss: 5.40
  Expectancy:  0.40 por trade
  PF:          1.15
  PnL total:   -1.59
  Peor DD:     33.90
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
  Capital:     1000.00 → 975.35  (-24.65)
  Señales:     46 generadas | 9 ALLOW | 37 BLOCK
  Trades:      9 cerrados | 3 wins | 6 losses
  Winrate:     33.3%
  Avg Trade:   -1.99
  Avg Win:     5.48  |  Avg Loss: 5.73
  Expectancy:  -1.99 por trade
  PF:          0.48
  Max DD:      25.44 (2.5%)
  Avg Bars:    8 velas
  Regímenes:   {'BULL_TREND': 2, 'BEAR_TREND': 6, 'TREND': 1}
  Señales:     {'BUY': 2, 'SELL': 7}
  Bloqueos principales:
      28x  Cooldown por activo (6h)
       1x  ADX insuficiente para sniper: 21.64 < 22.0 | Score final insuficiente para sniper: 54.78 <
       1x  ADX insuficiente para sniper: 21.41 < 22.0 | Score final insuficiente para sniper: 54.63 <
       1x  ADX insuficiente para sniper: 20.47 < 22.0 | Score final insuficiente para sniper: 54.04 <
       1x  ADX insuficiente para sniper: 20.26 < 22.0 | Score final insuficiente para sniper: 53.91 <

--- IWM TEST ---
  ============================================================
  IWM | TEST | Bars: 234
  ============================================================
  Capital:     1000.00 → 1007.57  (+7.57)
  Señales:     21 generadas | 5 ALLOW | 16 BLOCK
  Trades:      4 cerrados | 3 wins | 1 losses
  Winrate:     75.0%
  Avg Trade:   2.75
  Avg Win:     5.55  |  Avg Loss: 5.65
  Expectancy:  2.75 por trade
  PF:          2.95
  Max DD:      8.54 (0.8%)
  Avg Bars:    9 velas
  Regímenes:   {'BEAR_TREND': 2, 'TREND': 2}
  Señales:     {'SELL': 4}
  Bloqueos principales:
      15x  Cooldown por activo (6h)
       1x  ADX insuficiente para sniper: 20.88 < 22.0 | Score final insuficiente para sniper: 54.30 <

--- NVDA TRAIN ---
  ============================================================
  NVDA | TRAIN | Bars: 346
  ============================================================
  Capital:     1000.00 → 977.53  (-22.47)
  Señales:     27 generadas | 11 ALLOW | 16 BLOCK
  Trades:      10 cerrados | 3 wins | 7 losses
  Winrate:     30.0%
  Avg Trade:   -1.92
  Avg Win:     5.76  |  Avg Loss: 5.21
  Expectancy:  -1.92 por trade
  PF:          0.47
  Max DD:      33.90 (3.4%)
  Avg Bars:    11 velas
  Regímenes:   {'BULL_TREND': 5, 'BEAR_TREND': 3, 'TREND': 2}
  Señales:     {'BUY': 6, 'SELL': 4}
  Bloqueos principales:
      16x  Cooldown por activo (6h)

--- NVDA TEST ---
  ============================================================
  NVDA | TEST | Bars: 234
  ============================================================
  Capital:     1000.00 → 1004.97  (+4.97)
  Señales:     20 generadas | 8 ALLOW | 12 BLOCK
  Trades:      7 cerrados | 4 wins | 3 losses
  Winrate:     57.1%
  Avg Trade:   1.09
  Avg Win:     5.94  |  Avg Loss: 5.38
  Expectancy:  1.09 por trade
  PF:          1.47
  Max DD:      14.31 (1.4%)
  Avg Bars:    15 velas
  Regímenes:   {'BULL_TREND': 1, 'TREND': 2, 'BEAR_TREND': 4}
  Señales:     {'BUY': 3, 'SELL': 4}
  Bloqueos principales:
      12x  Cooldown por activo (6h)

--- AMZN TRAIN ---
  ============================================================
  AMZN | TRAIN | Bars: 346
  ============================================================
  Capital:     1000.00 → 1026.87  (+26.87)
  Señales:     49 generadas | 10 ALLOW | 39 BLOCK
  Trades:      9 cerrados | 7 wins | 2 losses
  Winrate:     77.8%
  Avg Trade:   3.40
  Avg Win:     5.92  |  Avg Loss: 5.40
  Expectancy:  3.40 por trade
  PF:          3.84
  Max DD:      12.59 (1.3%)
  Avg Bars:    12 velas
  Regímenes:   {'BEAR_TREND': 7, 'TREND': 2}
  Señales:     {'SELL': 7, 'BUY': 2}
  Bloqueos principales:
      39x  Cooldown por activo (6h)

--- AMZN TEST ---
  ============================================================
  AMZN | TEST | Bars: 234
  ============================================================
  Capital:     1000.00 → 993.27  (-6.73)
  Señales:     28 generadas | 8 ALLOW | 20 BLOCK
  Trades:      7 cerrados | 3 wins | 4 losses
  Winrate:     42.9%
  Avg Trade:   -0.55
  Avg Win:     5.86  |  Avg Loss: 5.36
  Expectancy:  -0.55 por trade
  PF:          0.82
  Max DD:      14.25 (1.4%)
  Avg Bars:    16 velas
  Regímenes:   {'BEAR_TREND': 3, 'TREND': 1, 'BULL_TREND': 3}
  Señales:     {'SELL': 4, 'BUY': 3}
  Bloqueos principales:
      20x  Cooldown por activo (6h)

--- META TRAIN ---
  ============================================================
  META | TRAIN | Bars: 346
  ============================================================
  Capital:     1000.00 → 1006.41  (+6.41)
  Señales:     36 generadas | 10 ALLOW | 26 BLOCK
  Trades:      9 cerrados | 5 wins | 4 losses
  Winrate:     55.6%
  Avg Trade:   0.98
  Avg Win:     5.98  |  Avg Loss: 5.27
  Expectancy:  0.98 por trade
  PF:          1.42
  Max DD:      22.82 (2.3%)
  Avg Bars:    15 velas
  Regímenes:   {'TREND': 3, 'BEAR_TREND': 1, 'BULL_TREND': 5}
  Señales:     {'SELL': 3, 'BUY': 6}
  Bloqueos principales:
      26x  Cooldown por activo (6h)

--- META TEST ---
  ============================================================
  META | TEST | Bars: 234
  ============================================================
  Capital:     1000.00 → 994.83  (-5.17)
  Señales:     24 generadas | 5 ALLOW | 19 BLOCK
  Trades:      5 cerrados | 2 wins | 3 losses
  Winrate:     40.0%
  Avg Trade:   -0.77
  Avg Win:     5.97  |  Avg Loss: 5.27
  Expectancy:  -0.77 por trade
  PF:          0.76
  Max DD:      9.49 (0.9%)
  Avg Bars:    17 velas
  Regímenes:   {'BULL_TREND': 4, 'BEAR_TREND': 1}
  Señales:     {'BUY': 4, 'SELL': 1}
  Bloqueos principales:
      19x  Cooldown por activo (6h)


#################################################################
  CONSOLIDADO TRAIN (IN-SAMPLE) — 4 activos
#################################################################
  Señales:     158 generadas | 40 ALLOW | 118 BLOCK
  Trades:      37 cerrados | 18 wins | 19 losses
  Winrate:     48.6%
  Avg Trade:   0.06
  Avg Win:     5.84  |  Avg Loss: 5.41
  Expectancy:  0.06 por trade
  PF:          1.02
  PnL total:   -13.84
  Peor DD:     33.90
#################################################################

  VEREDICTO:
  🟡  Edge marginal. Positivo pero débil.


#################################################################
  CONSOLIDADO TEST (OUT-OF-SAMPLE) — 4 activos
#################################################################
  Señales:     93 generadas | 26 ALLOW | 67 BLOCK
  Trades:      23 cerrados | 12 wins | 11 losses
  Winrate:     52.2%
  Avg Trade:   0.47
  Avg Win:     5.82  |  Avg Loss: 5.37
  Expectancy:  0.47 por trade
  PF:          1.18
  PnL total:   +0.65
  Peor DD:     14.31
#################################################################

  VEREDICTO:
  🟡  Edge marginal. Positivo pero débil.


=================================================================
  COMPARACIÓN TRAIN vs TEST
=================================================================

  IWM:
    TRAIN: 9 trades | WR 33.3% | PF 0.48 | Exp -1.99
    TEST:  4 trades | WR 75.0% | PF 2.95 | Exp 2.75
    ⚠️  Pocos trades para comparar

  NVDA:
    TRAIN: 10 trades | WR 30.0% | PF 0.47 | Exp -1.92
    TEST:  7 trades | WR 57.1% | PF 1.47 | Exp 1.09
    ✅  Consistente entre train y test

  AMZN:
    TRAIN: 9 trades | WR 77.8% | PF 3.84 | Exp 3.40
    TEST:  7 trades | WR 42.9% | PF 0.82 | Exp -0.55
    ⚠️  Degradación significativa train→test

  META:
    TRAIN: 9 trades | WR 55.6% | PF 1.42 | Exp 0.98
    TEST:  5 trades | WR 40.0% | PF 0.76 | Exp -0.77
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
  OK | yfinance | 3772 velas
Descargando NVDA...
  OK | yfinance | 3772 velas
Descargando AMZN...
  OK | yfinance | 3772 velas
Descargando META...
  OK | yfinance | 3624 velas

=================================================================
  FASE 1: BACKTEST COMPLETO (todo el período)
=================================================================

============================================================
IWM | FULL | Bars: 3572
============================================================
Capital:     1000.00 → 1000.00  (+0.00)
Señales:     471 generadas | 0 ALLOW | 471 BLOCK
Trades:      0 cerrados | 0 wins | 0 losses
Winrate:     0.0%
Avg Trade:   0.00
Avg Win:     0.00  |  Avg Loss: 0.00
Expectancy:  0.00 por trade
PF:          0.00
Max DD:      0.00 (0.0%)
Avg Bars:    0 velas
Bloqueos principales:
   471x  Sesión no válida: Fuera de horario principal

============================================================
NVDA | FULL | Bars: 3572
============================================================
Capital:     1000.00 → 1000.00  (+0.00)
Señales:     589 generadas | 0 ALLOW | 589 BLOCK
Trades:      0 cerrados | 0 wins | 0 losses
Winrate:     0.0%
Avg Trade:   0.00
Avg Win:     0.00  |  Avg Loss: 0.00
Expectancy:  0.00 por trade
PF:          0.00
Max DD:      0.00 (0.0%)
Avg Bars:    0 velas
Bloqueos principales:
   589x  Sesión no válida: Fuera de horario principal

============================================================
AMZN | FULL | Bars: 3572
============================================================
Capital:     1000.00 → 1000.00  (+0.00)
Señales:     636 generadas | 0 ALLOW | 636 BLOCK
Trades:      0 cerrados | 0 wins | 0 losses
Winrate:     0.0%
Avg Trade:   0.00
Avg Win:     0.00  |  Avg Loss: 0.00
Expectancy:  0.00 por trade
PF:          0.00
Max DD:      0.00 (0.0%)
Avg Bars:    0 velas
Bloqueos principales:
   636x  Sesión no válida: Fuera de horario principal

============================================================
META | FULL | Bars: 3424
============================================================
Capital:     1000.00 → 1000.00  (+0.00)
Señales:     526 generadas | 0 ALLOW | 526 BLOCK
Trades:      0 cerrados | 0 wins | 0 losses
Winrate:     0.0%
Avg Trade:   0.00
Avg Win:     0.00  |  Avg Loss: 0.00
Expectancy:  0.00 por trade
PF:          0.00
Max DD:      0.00 (0.0%)
Avg Bars:    0 velas
Bloqueos principales:
   526x  Sesión no válida: Fuera de horario principal


#################################################################
  CONSOLIDADO FULL PERIOD — 4 activos
#################################################################
  Señales:     2222 generadas | 0 ALLOW | 2222 BLOCK
  Trades:      0 cerrados | 0 wins | 0 losses
  Winrate:     0.0%
  Avg Trade:   0.00
  Avg Win:     0.00  |  Avg Loss: 0.00
  Expectancy:  0.00 por trade
  PF:          0.00
  PnL total:   +0.00
  Peor DD:     0.00
#################################################################

  VEREDICTO:
  ⚠️  Muy pocos trades para conclusiones fiables.


=================================================================
  FASE 2: WALK-FORWARD (70% train / 30% test)
=================================================================

--- IWM TRAIN ---
  ============================================================
  IWM | TRAIN | Bars: 2440
  ============================================================
  Capital:     1000.00 → 1000.00  (+0.00)
  Señales:     338 generadas | 0 ALLOW | 338 BLOCK
  Trades:      0 cerrados | 0 wins | 0 losses
  Winrate:     0.0%
  Avg Trade:   0.00
  Avg Win:     0.00  |  Avg Loss: 0.00
  Expectancy:  0.00 por trade
  PF:          0.00
  Max DD:      0.00 (0.0%)
  Avg Bars:    0 velas
  Bloqueos principales:
     338x  Sesión no válida: Fuera de horario principal

--- IWM TEST ---
  ============================================================
  IWM | TEST | Bars: 1132
  ============================================================
  Capital:     1000.00 → 1000.00  (+0.00)
  Señales:     133 generadas | 0 ALLOW | 133 BLOCK
  Trades:      0 cerrados | 0 wins | 0 losses
  Winrate:     0.0%
  Avg Trade:   0.00
  Avg Win:     0.00  |  Avg Loss: 0.00
  Expectancy:  0.00 por trade
  PF:          0.00
  Max DD:      0.00 (0.0%)
  Avg Bars:    0 velas
  Bloqueos principales:
     133x  Sesión no válida: Fuera de horario principal

--- NVDA TRAIN ---
  ============================================================
  NVDA | TRAIN | Bars: 2440
  ============================================================
  Capital:     1000.00 → 1000.00  (+0.00)
  Señales:     415 generadas | 0 ALLOW | 415 BLOCK
  Trades:      0 cerrados | 0 wins | 0 losses
  Winrate:     0.0%
  Avg Trade:   0.00
  Avg Win:     0.00  |  Avg Loss: 0.00
  Expectancy:  0.00 por trade
  PF:          0.00
  Max DD:      0.00 (0.0%)
  Avg Bars:    0 velas
  Bloqueos principales:
     415x  Sesión no válida: Fuera de horario principal

--- NVDA TEST ---
  ============================================================
  NVDA | TEST | Bars: 1132
  ============================================================
  Capital:     1000.00 → 1000.00  (+0.00)
  Señales:     174 generadas | 0 ALLOW | 174 BLOCK
  Trades:      0 cerrados | 0 wins | 0 losses
  Winrate:     0.0%
  Avg Trade:   0.00
  Avg Win:     0.00  |  Avg Loss: 0.00
  Expectancy:  0.00 por trade
  PF:          0.00
  Max DD:      0.00 (0.0%)
  Avg Bars:    0 velas
  Bloqueos principales:
     174x  Sesión no válida: Fuera de horario principal

--- AMZN TRAIN ---
  ============================================================
  AMZN | TRAIN | Bars: 2440
  ============================================================
  Capital:     1000.00 → 1000.00  (+0.00)
  Señales:     477 generadas | 0 ALLOW | 477 BLOCK
  Trades:      0 cerrados | 0 wins | 0 losses
  Winrate:     0.0%
  Avg Trade:   0.00
  Avg Win:     0.00  |  Avg Loss: 0.00
  Expectancy:  0.00 por trade
  PF:          0.00
  Max DD:      0.00 (0.0%)
  Avg Bars:    0 velas
  Bloqueos principales:
     477x  Sesión no válida: Fuera de horario principal

--- AMZN TEST ---
  ============================================================
  AMZN | TEST | Bars: 1132
  ============================================================
  Capital:     1000.00 → 1000.00  (+0.00)
  Señales:     159 generadas | 0 ALLOW | 159 BLOCK
  Trades:      0 cerrados | 0 wins | 0 losses
  Winrate:     0.0%
  Avg Trade:   0.00
  Avg Win:     0.00  |  Avg Loss: 0.00
  Expectancy:  0.00 por trade
  PF:          0.00
  Max DD:      0.00 (0.0%)
  Avg Bars:    0 velas
  Bloqueos principales:
     159x  Sesión no válida: Fuera de horario principal

--- META TRAIN ---
  ============================================================
  META | TRAIN | Bars: 2336
  ============================================================
  Capital:     1000.00 → 1000.00  (+0.00)
  Señales:     339 generadas | 0 ALLOW | 339 BLOCK
  Trades:      0 cerrados | 0 wins | 0 losses
  Winrate:     0.0%
  Avg Trade:   0.00
  Avg Win:     0.00  |  Avg Loss: 0.00
  Expectancy:  0.00 por trade
  PF:          0.00
  Max DD:      0.00 (0.0%)
  Avg Bars:    0 velas
  Bloqueos principales:
     339x  Sesión no válida: Fuera de horario principal

--- META TEST ---
  ============================================================
  META | TEST | Bars: 1088
  ============================================================
  Capital:     1000.00 → 1000.00  (+0.00)
  Señales:     187 generadas | 0 ALLOW | 187 BLOCK
  Trades:      0 cerrados | 0 wins | 0 losses
  Winrate:     0.0%
  Avg Trade:   0.00
  Avg Win:     0.00  |  Avg Loss: 0.00
  Expectancy:  0.00 por trade
  PF:          0.00
  Max DD:      0.00 (0.0%)
  Avg Bars:    0 velas
  Bloqueos principales:
     187x  Sesión no válida: Fuera de horario principal


#################################################################
  CONSOLIDADO TRAIN (IN-SAMPLE) — 4 activos
#################################################################
  Señales:     1569 generadas | 0 ALLOW | 1569 BLOCK
  Trades:      0 cerrados | 0 wins | 0 losses
  Winrate:     0.0%
  Avg Trade:   0.00
  Avg Win:     0.00  |  Avg Loss: 0.00
  Expectancy:  0.00 por trade
  PF:          0.00
  PnL total:   +0.00
  Peor DD:     0.00
#################################################################

  VEREDICTO:
  ⚠️  Muy pocos trades para conclusiones fiables.


#################################################################
  CONSOLIDADO TEST (OUT-OF-SAMPLE) — 4 activos
#################################################################
  Señales:     653 generadas | 0 ALLOW | 653 BLOCK
  Trades:      0 cerrados | 0 wins | 0 losses
  Winrate:     0.0%
  Avg Trade:   0.00
  Avg Win:     0.00  |  Avg Loss: 0.00
  Expectancy:  0.00 por trade
  PF:          0.00
  PnL total:   +0.00
  Peor DD:     0.00
#################################################################

  VEREDICTO:
  ⚠️  Muy pocos trades para conclusiones fiables.


=================================================================
  COMPARACIÓN TRAIN vs TEST
=================================================================

  IWM:
    TRAIN: 0 trades | WR 0.0% | PF 0.00 | Exp 0.00
    TEST:  0 trades | WR 0.0% | PF 0.00 | Exp 0.00
    ⚠️  Pocos trades para comparar

  NVDA:
    TRAIN: 0 trades | WR 0.0% | PF 0.00 | Exp 0.00
    TEST:  0 trades | WR 0.0% | PF 0.00 | Exp 0.00
    ⚠️  Pocos trades para comparar

  AMZN:
    TRAIN: 0 trades | WR 0.0% | PF 0.00 | Exp 0.00
    TEST:  0 trades | WR 0.0% | PF 0.00 | Exp 0.00
    ⚠️  Pocos trades para comparar

  META:
    TRAIN: 0 trades | WR 0.0% | PF 0.00 | Exp 0.00
    TEST:  0 trades | WR 0.0% | PF 0.00 | Exp 0.00
    ⚠️  Pocos trades para comparar


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

Operaciones totales con la config actual: 62

==============================================================
1) BOOTSTRAP DE LA EXPECTATIVA
==============================================================
Operaciones:            62
Expectativa observada:  +0.3975 € por operación
Intervalo 90%:          -0.8136  a  +1.5188
Prob. expectativa > 0:  72.6%

LECTURA: INDECISO. El cero está dentro del intervalo, así que
         esta muestra no distingue la estrategia de una moneda.
         No significa que no funcione: significa que todavía no
         se sabe. La única cura es más operaciones.

==============================================================
2) MONTE CARLO DE LA CURVA DE CAPITAL
==============================================================
Capital inicial:              1000.00 €
Drawdown mediano:             3.57%
Drawdown percentil 95:        5.55%
Peor drawdown simulado:       8.30%

Capital final, percentil 5:   1024.64 €
Capital final, mediana:       1024.64 €
Capital final, percentil 95:  1024.64 €

Prob. terminar en pérdida:    0.0%
Prob. perder la mitad:        0.0%

LECTURA: con estas operaciones en otro orden, el drawdown que hay
         que estar dispuesto a aguantar es del 5.6%,
         no el que salió en el histórico. El orden de las
         operaciones es azar; la racha mala no tiene por qué
         haber caído dentro del periodo de prueba.

==============================================================
3) BARRIDO DE PARÁMETROS (SL / TP)
==============================================================

   SL    TP   R:R   OPS    WR%    EXPECT     PF  VEREDICTO
--------------------------------------------------------------
  1.5   2.0  1.33    74   43.2   -0.4976   0.84
  1.5   2.5  1.67    70   41.4   -0.0194   0.99
  1.5   3.0  2.00    64   40.6 +  0.5267   1.16
  1.5   3.5  2.33    62   38.7 +  0.8903   1.26
  2.0   2.0  1.00    69   52.2   -0.1893   0.93
  2.0   2.5  1.25    62   51.6 +  0.3975   1.15 <-- CONFIG ACTUAL
  2.0   3.0  1.50    58   50.0 +  0.8316   1.31
  2.0   3.5  1.75    58   43.1 +  0.5028   1.16
  2.5   2.0  0.80    68   57.4   -0.1694   0.93
  2.5   2.5  1.00    62   56.5 +  0.3110   1.13
  2.5   3.0  1.20    57   54.4 +  0.6464   1.26
  2.5   3.5  1.40    56   46.4 +  0.2326   1.08
  3.0   2.0  0.67    66   60.6   -0.2273   0.89
  3.0   2.5  0.83    60   60.0 +  0.2191   1.10
  3.0   3.0  1.00    57   56.1 +  0.3330   1.14
  3.0   3.5  1.17    54   50.0 +  0.1357   1.05

Combinaciones con expectativa positiva: 11 de 16
Configuración actual (SL 2.0 / TP 2.5): expectativa +0.3975, PF 1.15
Vecinos inmediatos con expectativa positiva: 4 de 8

LECTURA: ZONA MIXTA. Ni pico ni meseta clara. Con esta muestra
         no se puede separar señal de ruido.

==============================================================
```

## Robustez (diario, 15 anos)
```
==============================================================
ANÁLISIS DE ROBUSTEZ — SHARK V15
==============================================================
Timeframe: 1d | Periodo: 15y
Activos: ['IWM', 'NVDA', 'AMZN', 'META']
Config actual: SL 2.0 ATR / TP 2.5 ATR
Bootstrap: 10000 | Monte Carlo: 5000

Descargando 1d / 15y ...
  IWM     yfinance     3772 velas
  NVDA    yfinance     3772 velas
  AMZN    yfinance     3772 velas
  META    yfinance     3624 velas

Operaciones totales con la config actual: 0
Muy pocas operaciones para cualquier análisis estadístico.
Eso ya es el resultado: no hay nada que medir.
```

