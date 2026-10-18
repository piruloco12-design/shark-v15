# Validacion SHARK V15

Fecha:   2026-10-18 14:37 UTC
Commit:  a7f4e8d3
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
  PASA   en Render con disco montado no avisa

==============================================================
RESULTADO: 28 pruebas pasadas, 0 fallos
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
Providers ['yfinance', 'stooq', 'finnhub', 'alpha_vantage', 'twelve_data']

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
Avg Trade:   -1.28
Avg Win:     4.74  |  Avg Loss: 6.44
Expectancy:  -1.28 por trade
PF:          0.63
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
Avg Trade:   -1.26
Avg Win:     5.44  |  Avg Loss: 5.52
Expectancy:  -1.26 por trade
PF:          0.63
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
Avg Trade:   1.54
Avg Win:     5.58  |  Avg Loss: 5.86
Expectancy:  1.54 por trade
PF:          1.75
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
Avg Trade:   0.91
Avg Win:     5.79  |  Avg Loss: 5.60
Expectancy:  0.91 por trade
PF:          1.38
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
  Avg Trade:   -0.00
  Avg Win:     5.45  |  Avg Loss: 5.82
  Expectancy:  -0.00 por trade
  PF:          1.00
  PnL total:   -1.59
  Peor DD:     33.90
  -------------------------------------------------------------
  Suma PnL trades:  -0.29   (debe cuadrar con PnL total)
  ✅ Cuadra (dif. 1.30, son costes de trades aún abiertos)
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
  Capital:     1000.00 → 975.35  (-24.65)
  Señales:     46 generadas | 9 ALLOW | 37 BLOCK
  Trades:      9 cerrados | 3 wins | 6 losses
  Winrate:     33.3%
  Avg Trade:   -2.74
  Avg Win:     4.77  |  Avg Loss: 6.49
  Expectancy:  -2.74 por trade
  PF:          0.37
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
  Avg Trade:   2.06
  Avg Win:     4.83  |  Avg Loss: 6.26
  Expectancy:  2.06 por trade
  PF:          2.31
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
  Avg Trade:   -2.21
  Avg Win:     5.45  |  Avg Loss: 5.49
  Expectancy:  -2.21 por trade
  PF:          0.43
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
  Avg Trade:   0.75
  Avg Win:     5.59  |  Avg Loss: 5.70
  Expectancy:  0.75 por trade
  PF:          1.31
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
  Avg Trade:   3.03
  Avg Win:     5.55  |  Avg Loss: 5.80
  Expectancy:  3.03 por trade
  PF:          3.35
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
  Avg Trade:   -0.91
  Avg Win:     5.48  |  Avg Loss: 5.70
  Expectancy:  -0.91 por trade
  PF:          0.72
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
  Avg Trade:   0.73
  Avg Win:     5.75  |  Avg Loss: 5.54
  Expectancy:  0.73 por trade
  PF:          1.30
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
  Avg Trade:   -1.03
  Avg Win:     5.72  |  Avg Loss: 5.54
  Expectancy:  -1.03 por trade
  PF:          0.69
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
  Avg Trade:   -0.35
  Avg Win:     5.46  |  Avg Loss: 5.85
  Expectancy:  -0.35 por trade
  PF:          0.88
  PnL total:   -13.84
  Peor DD:     33.90
  -------------------------------------------------------------
  Suma PnL trades:  -12.93   (debe cuadrar con PnL total)
  ✅ Cuadra (dif. 0.91, son costes de trades aún abiertos)
#################################################################

  VEREDICTO:
  ❌  NO HAY EDGE. Expectancy negativa.


#################################################################
  CONSOLIDADO TEST (OUT-OF-SAMPLE) — 4 activos
#################################################################
  Señales:     93 generadas | 26 ALLOW | 67 BLOCK
  Trades:      23 cerrados | 12 wins | 11 losses
  Winrate:     52.2%
  Avg Trade:   0.09
  Avg Win:     5.39  |  Avg Loss: 5.71
  Expectancy:  0.09 por trade
  PF:          1.03
  PnL total:   +0.65
  Peor DD:     14.31
  -------------------------------------------------------------
  Suma PnL trades:  +1.96   (debe cuadrar con PnL total)
  ✅ Cuadra (dif. 1.31, son costes de trades aún abiertos)
#################################################################

  VEREDICTO:
  🟡  Edge marginal. Positivo pero débil.


=================================================================
  COMPARACIÓN TRAIN vs TEST
=================================================================

  IWM:
    TRAIN: 9 trades | WR 33.3% | PF 0.37 | Exp -2.74
    TEST:  4 trades | WR 75.0% | PF 2.31 | Exp 2.06
    ⚠️  Pocos trades para comparar

  NVDA:
    TRAIN: 10 trades | WR 30.0% | PF 0.43 | Exp -2.21
    TEST:  7 trades | WR 57.1% | PF 1.31 | Exp 0.75
    ✅  Consistente entre train y test

  AMZN:
    TRAIN: 9 trades | WR 77.8% | PF 3.35 | Exp 3.03
    TEST:  7 trades | WR 42.9% | PF 0.72 | Exp -0.91
    ⚠️  Degradación significativa train→test

  META:
    TRAIN: 9 trades | WR 55.6% | PF 1.30 | Exp 0.73
    TEST:  5 trades | WR 40.0% | PF 0.69 | Exp -1.03
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
Capital:     1000.00 → 932.83  (-67.17)
Señales:     180 generadas | 104 ALLOW | 76 BLOCK
Trades:      103 cerrados | 42 wins | 61 losses
Winrate:     40.8%
Avg Trade:   -0.65
Avg Win:     5.89  |  Avg Loss: 5.15
Expectancy:  -0.65 por trade
PF:          0.79
Max DD:      101.75 (10.2%)
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
NVDA | FULL | Bars: 3572
============================================================
Capital:     1000.00 → 1168.13  (+168.13)
Señales:     214 generadas | 136 ALLOW | 78 BLOCK
Trades:      136 cerrados | 76 wins | 60 losses
Winrate:     55.9%
Avg Trade:   1.24
Avg Win:     6.49  |  Avg Loss: 5.42
Expectancy:  1.24 por trade
PF:          1.52
Max DD:      35.48 (3.5%)
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
AMZN | FULL | Bars: 3572
============================================================
Capital:     1000.00 → 1006.90  (+6.90)
Señales:     218 generadas | 131 ALLOW | 87 BLOCK
Trades:      131 cerrados | 61 wins | 70 losses
Winrate:     46.6%
Avg Trade:   0.05
Avg Win:     6.24  |  Avg Loss: 5.33
Expectancy:  0.05 por trade
PF:          1.02
Max DD:      69.68 (7.0%)
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
META | FULL | Bars: 3424
============================================================
Capital:     1000.00 → 1035.71  (+35.71)
Señales:     182 generadas | 127 ALLOW | 55 BLOCK
Trades:      126 cerrados | 61 wins | 65 losses
Winrate:     48.4%
Avg Trade:   0.28
Avg Win:     6.19  |  Avg Loss: 5.26
Expectancy:  0.28 por trade
PF:          1.10
Max DD:      60.29 (6.0%)
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
  Avg Trade:   0.29
  Avg Win:     6.24  |  Avg Loss: 5.29
  Expectancy:  0.29 por trade
  PF:          1.11
  PnL total:   +143.57
  Peor DD:     101.75
  -------------------------------------------------------------
  Suma PnL trades:  +143.76   (debe cuadrar con PnL total)
  ✅ Cuadra (dif. 0.20, son costes de trades aún abiertos)
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
  Capital:     1000.00 → 986.90  (-13.10)
  Señales:     130 generadas | 75 ALLOW | 55 BLOCK
  Trades:      75 cerrados | 34 wins | 41 losses
  Winrate:     45.3%
  Avg Trade:   -0.17
  Avg Win:     5.94  |  Avg Loss: 5.25
  Expectancy:  -0.17 por trade
  PF:          0.94
  Max DD:      56.62 (5.7%)
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
  Capital:     1000.00 → 945.21  (-54.79)
  Señales:     50 generadas | 29 ALLOW | 21 BLOCK
  Trades:      28 cerrados | 8 wins | 20 losses
  Winrate:     28.6%
  Avg Trade:   -1.95
  Avg Win:     5.73  |  Avg Loss: 5.03
  Expectancy:  -1.95 por trade
  PF:          0.46
  Max DD:      68.17 (6.8%)
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
  NVDA | TRAIN | Bars: 2440
  ============================================================
  Capital:     1000.00 → 1082.41  (+82.41)
  Señales:     154 generadas | 97 ALLOW | 57 BLOCK
  Trades:      96 cerrados | 51 wins | 45 losses
  Winrate:     53.1%
  Avg Trade:   0.86
  Avg Win:     6.28  |  Avg Loss: 5.29
  Expectancy:  0.86 por trade
  PF:          1.35
  Max DD:      35.48 (3.5%)
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
  Capital:     1000.00 → 1067.08  (+67.08)
  Señales:     63 generadas | 40 ALLOW | 23 BLOCK
  Trades:      40 cerrados | 24 wins | 16 losses
  Winrate:     60.0%
  Avg Trade:   1.68
  Avg Win:     6.33  |  Avg Loss: 5.30
  Expectancy:  1.68 por trade
  PF:          1.79
  Max DD:      17.79 (1.8%)
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
  AMZN | TRAIN | Bars: 2440
  ============================================================
  Capital:     1000.00 → 1017.29  (+17.29)
  Señales:     164 generadas | 95 ALLOW | 69 BLOCK
  Trades:      94 cerrados | 45 wins | 49 losses
  Winrate:     47.9%
  Avg Trade:   0.18
  Avg Win:     6.24  |  Avg Loss: 5.38
  Expectancy:  0.18 por trade
  PF:          1.07
  Max DD:      56.27 (5.6%)
  Avg Bars:    12 velas
  Regímenes:   {'BULL_TREND': 52, 'BEAR_TREND': 18, 'TREND': 24}
  Señales:     {'BUY': 67, 'SELL': 27}
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
  Capital:     1000.00 → 994.82  (-5.18)
  Señales:     54 generadas | 36 ALLOW | 18 BLOCK
  Trades:      36 cerrados | 16 wins | 20 losses
  Winrate:     44.4%
  Avg Trade:   -0.14
  Avg Win:     6.15  |  Avg Loss: 5.18
  Expectancy:  -0.14 por trade
  PF:          0.95
  Max DD:      35.22 (3.5%)
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
  META | TRAIN | Bars: 2336
  ============================================================
  Capital:     1000.00 → 997.78  (-2.22)
  Señales:     119 generadas | 83 ALLOW | 36 BLOCK
  Trades:      83 cerrados | 38 wins | 45 losses
  Winrate:     45.8%
  Avg Trade:   -0.03
  Avg Win:     6.14  |  Avg Loss: 5.23
  Expectancy:  -0.03 por trade
  PF:          0.99
  Max DD:      48.04 (4.8%)
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
  Capital:     1000.00 → 1038.02  (+38.02)
  Señales:     63 generadas | 44 ALLOW | 19 BLOCK
  Trades:      43 cerrados | 23 wins | 20 losses
  Winrate:     53.5%
  Avg Trade:   0.89
  Avg Win:     6.28  |  Avg Loss: 5.32
  Expectancy:  0.89 por trade
  PF:          1.36
  Max DD:      43.85 (4.4%)
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
  Trades:      348 cerrados | 168 wins | 180 losses
  Winrate:     48.3%
  Avg Trade:   0.24
  Avg Win:     6.17  |  Avg Loss: 5.29
  Expectancy:  0.24 por trade
  PF:          1.09
  PnL total:   +84.38
  Peor DD:     56.62
  -------------------------------------------------------------
  Suma PnL trades:  +84.47   (debe cuadrar con PnL total)
  ✅ Cuadra (dif. 0.09, son costes de trades aún abiertos)
#################################################################

  VEREDICTO:
  🟡  Edge marginal. Positivo pero débil.


#################################################################
  CONSOLIDADO TEST (OUT-OF-SAMPLE) — 4 activos
#################################################################
  Señales:     230 generadas | 149 ALLOW | 81 BLOCK
  Trades:      147 cerrados | 71 wins | 76 losses
  Winrate:     48.3%
  Avg Trade:   0.31
  Avg Win:     6.20  |  Avg Loss: 5.20
  Expectancy:  0.31 por trade
  PF:          1.11
  PnL total:   +45.12
  Peor DD:     68.17
  -------------------------------------------------------------
  Suma PnL trades:  +45.32   (debe cuadrar con PnL total)
  ✅ Cuadra (dif. 0.20, son costes de trades aún abiertos)
#################################################################

  VEREDICTO:
  🟡  Edge marginal. Positivo pero débil.


=================================================================
  COMPARACIÓN TRAIN vs TEST
=================================================================

  IWM:
    TRAIN: 75 trades | WR 45.3% | PF 0.94 | Exp -0.17
    TEST:  28 trades | WR 28.6% | PF 0.46 | Exp -1.95
    ⚠️  Degradación significativa train→test

  NVDA:
    TRAIN: 96 trades | WR 53.1% | PF 1.35 | Exp 0.86
    TEST:  40 trades | WR 60.0% | PF 1.79 | Exp 1.68
    ✅  Consistente entre train y test

  AMZN:
    TRAIN: 94 trades | WR 47.9% | PF 1.07 | Exp 0.18
    TEST:  36 trades | WR 44.4% | PF 0.95 | Exp -0.14
    ✅  Consistente entre train y test

  META:
    TRAIN: 83 trades | WR 45.8% | PF 0.99 | Exp -0.03
    TEST:  43 trades | WR 53.5% | PF 1.36 | Exp 0.89
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

Operaciones totales con la config actual: 62

==============================================================
1) BOOTSTRAP DE LA EXPECTATIVA
==============================================================
Operaciones:            62
Expectativa observada:  -0.0047 € por operación
Intervalo 90%:          -1.1911  a  +1.1424
Prob. expectativa > 0:  49.5%

LECTURA: INDECISO. El cero está dentro del intervalo, así que
         esta muestra no distingue la estrategia de una moneda.
         No significa que no funcione: significa que todavía no
         se sabe. La única cura es más operaciones.

==============================================================
2) MONTE CARLO DE LA CURVA DE CAPITAL
==============================================================
Capital inicial:   1000.00 €
Operaciones:       62

A) MISMAS OPERACIONES, OTRO ORDEN
   (el capital final no cambia al barajar; solo el camino)
   Drawdown mediano:        4.37%
   Drawdown percentil 95:   6.59%
   Peor drawdown simulado:  9.55%
   Capital final (fijo):    999.71 €

B) REMUESTREO: si las próximas operaciones salieran de
   esta misma distribución
   Capital final, percentil 5:   927.91 €
   Capital final, mediana:       999.66 €
   Capital final, percentil 95:  1071.68 €
   Drawdown percentil 95:        9.16%
   Prob. terminar en pérdida:    50.4%
   Prob. perder la mitad:        0.0%

LECTURA: el drawdown que hay que estar dispuesto a aguantar es
         del 6.6%, no el que salió en el histórico: el orden
         de las operaciones es azar y la racha mala no tiene por
         qué haber caído dentro del periodo de prueba.
         El remuestreo da 50% de probabilidad de acabar
         en pérdida sobre otras 62 operaciones.

==============================================================
3) BARRIDO DE PARÁMETROS (SL / TP)
==============================================================

   SL    TP   R:R   OPS    WR%    EXPECT     PF  VEREDICTO
--------------------------------------------------------------
  1.5   2.0  1.33    74   43.2   -1.0278   0.70
  1.5   2.5  1.67    70   41.4   -0.5514   0.84
  1.5   3.0  2.00    64   40.6   -0.0192   0.99
  1.5   3.5  2.33    62   38.7 +  0.3381   1.09
  2.0   2.0  1.00    69   52.2   -0.5876   0.79
  2.0   2.5  1.25    62   51.6   -0.0047   1.00 <-- CONFIG ACTUAL
  2.0   3.0  1.50    58   50.0 +  0.4205   1.14
  2.0   3.5  1.75    58   43.1 +  0.0923   1.03
  2.5   2.0  0.80    68   57.4   -0.4915   0.80
  2.5   2.5  1.00    62   56.5   -0.0131   0.99
  2.5   3.0  1.20    57   54.4 +  0.3172   1.12
  2.5   3.5  1.40    56   46.4   -0.0963   0.97
  3.0   2.0  0.67    66   60.6   -0.4968   0.77
  3.0   2.5  0.83    60   60.0   -0.0520   0.98
  3.0   3.0  1.00    57   56.1 +  0.0606   1.02
  3.0   3.5  1.17    54   50.0   -0.1321   0.95

Combinaciones con expectativa positiva: 5 de 16
Configuración actual (SL 2.0 / TP 2.5): expectativa -0.0047, PF 1.00
Vecinos inmediatos con expectativa positiva: 2 de 8

LECTURA: la configuración actual no tiene expectativa positiva
         en este periodo. Si otras combinaciones sí, ojo: elegir
         ahora la mejor de la tabla ES sobreajustar.

==============================================================
4) ECONOMÍA REAL: ¿QUÉ SIGNIFICA ESTO EN DINERO?
==============================================================
Periodo cubierto:       0.2 años
Operaciones:            62  ->  260.4 al año
Riesgo por operación:   5.00 € (0.5% de 1000 €)
Expectativa en riesgo:  -0.001 R por operación

RENTABILIDAD ANUAL SOBRE 1000 €
  pesimista (p05)  :  -310.15 €/año  =  -31.02% anual
  central          :    -1.23 €/año  =   -0.12% anual
  optimista (p95)  :  +297.48 €/año  =  +29.75% anual

CAPITAL NECESARIO PARA SACAR 1.000 €/MES (12.000 €/año)
  pesimista (p05)  : imposible, la expectativa es negativa
  central          : imposible, la expectativa es negativa
  optimista (p95)  :         40,339 €

LECTURA: con expectativa central negativa no hay capital que
         arregle esto. El problema no es el tamaño de la cuenta.

JSON escrito en resultados/robustez_30m.json

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

Operaciones totales con la config actual: 496

==============================================================
1) BOOTSTRAP DE LA EXPECTATIVA
==============================================================
Operaciones:            496
Expectativa observada:  +0.2898 € por operación
Intervalo 90%:          -0.1286  a  +0.7187
Prob. expectativa > 0:  86.6%

LECTURA: INDECISO. El cero está dentro del intervalo, así que
         esta muestra no distingue la estrategia de una moneda.
         No significa que no funcione: significa que todavía no
         se sabe. La única cura es más operaciones.

==============================================================
2) MONTE CARLO DE LA CURVA DE CAPITAL
==============================================================
Capital inicial:   1000.00 €
Operaciones:       496

A) MISMAS OPERACIONES, OTRO ORDEN
   (el capital final no cambia al barajar; solo el camino)
   Drawdown mediano:        8.76%
   Drawdown percentil 95:   13.60%
   Peor drawdown simulado:  22.34%
   Capital final (fijo):    1143.76 €

B) REMUESTREO: si las próximas operaciones salieran de
   esta misma distribución
   Capital final, percentil 5:   937.69 €
   Capital final, mediana:       1144.71 €
   Capital final, percentil 95:  1357.01 €
   Drawdown percentil 95:        18.10%
   Prob. terminar en pérdida:    13.2%
   Prob. perder la mitad:        0.0%

LECTURA: el drawdown que hay que estar dispuesto a aguantar es
         del 13.6%, no el que salió en el histórico: el orden
         de las operaciones es azar y la racha mala no tiene por
         qué haber caído dentro del periodo de prueba.
         El remuestreo da 13% de probabilidad de acabar
         en pérdida sobre otras 496 operaciones.

==============================================================
3) BARRIDO DE PARÁMETROS (SL / TP)
==============================================================

   SL    TP   R:R   OPS    WR%    EXPECT     PF  VEREDICTO
--------------------------------------------------------------
  1.5   2.0  1.33   614   45.4 +  0.1033   1.04
  1.5   2.5  1.67   551   39.2 +  0.0279   1.01
  1.5   3.0  2.00   519   34.7   -0.0216   0.99
  1.5   3.5  2.33   486   32.7 +  0.2238   1.06
  2.0   2.0  1.00   559   53.1 +  0.1645   1.07
  2.0   2.5  1.25   496   48.4 +  0.2898   1.11 <-- CONFIG ACTUAL
  2.0   3.0  1.50   466   42.1 +  0.0927   1.03
  2.0   3.5  1.75   435   39.3 +  0.2376   1.07
  2.5   2.0  0.80   525   57.5 +  0.0545   1.02
  2.5   2.5  1.00   463   51.8 +  0.0657   1.03
  2.5   3.0  1.20   424   46.0   -0.0649   0.98
  2.5   3.5  1.40   394   44.2 +  0.1773   1.06
  3.0   2.0  0.67   501   62.5 +  0.0936   1.05
  3.0   2.5  0.83   439   56.9 +  0.1076   1.05
  3.0   3.0  1.00   402   52.2 +  0.1120   1.05
  3.0   3.5  1.17   372   50.8 +  0.4022   1.16

Combinaciones con expectativa positiva: 14 de 16
Configuración actual (SL 2.0 / TP 2.5): expectativa +0.2898, PF 1.11
Vecinos inmediatos con expectativa positiva: 6 de 8

LECTURA: MESETA. La configuración actual y la mayoría de sus
         vecinos funcionan. No demuestra que haya edge, pero
         es compatible con que el efecto sea real y no el
         número exacto elegido.

==============================================================
4) ECONOMÍA REAL: ¿QUÉ SIGNIFICA ESTO EN DINERO?
==============================================================
Periodo cubierto:       15.0 años
Operaciones:            496  ->  33.1 al año
Riesgo por operación:   5.00 € (0.5% de 1000 €)
Expectativa en riesgo:  +0.058 R por operación

RENTABILIDAD ANUAL SOBRE 1000 €
  pesimista (p05)  :    -4.26 €/año  =   -0.43% anual
  central          :    +9.60 €/año  =   +0.96% anual
  optimista (p95)  :   +23.81 €/año  =   +2.38% anual

CAPITAL NECESARIO PARA SACAR 1.000 €/MES (12.000 €/año)
  pesimista (p05)  : imposible, la expectativa es negativa
  central          :      1,249,403 €
  optimista (p95)  :        503,889 €

LECTURA: 1.0% anual. Eso está por debajo de lo que
         da un índice sin hacer nada, y muy por debajo de lo que
         haría falta para vivir de esto con una cuenta pequeña.
         El cuello de botella no es el código ni los filtros:
         son 33 operaciones al año con una ventaja de
         0.058 R. Para cambiarlo hace falta más
         ventaja por operación o muchas más operaciones, y subir
         el riesgo solo multiplica también las pérdidas.

JSON escrito en resultados/robustez_1d.json

==============================================================
```

## Experimento de universo (diversificacion)
```
==============================================================================================================
EXPERIMENTO DE UNIVERSO — ¿diversificar cambia la economía?
==============================================================================================================
Timeframe: 1d | Periodo: 15y | Capital: 1000 EUR

Descargando universo de produccion...
  4 de 4 activos
Descargando universo limpio...
  30 de 30 activos
  de los cuales 14 son renta variable USA

==============================================================================================================
  CONFIGURACION                      ACT  HUE  RIESGO    OPS  OPS/AÑO    WR%   EXPECT     PF   ANUAL%     DD%
==============================================================================================================

  -- universo de produccion (con sesgo de seleccion) --
  4 activos / 2 huecos (ACTUAL)        4    2  0.50%    407    28.7   49.6   +0.425   1.15    +1.11     8.7
  4 activos / 4 huecos                 4    4  0.50%    496    34.9   48.4   +0.269   1.09    +0.86    13.1

  -- universo limpio de ETFs --
  30 ETFs / 2 huecos                  30    2  0.50%    615    43.3   44.9   -0.435   0.83    -2.19    35.6
  30 ETFs / 6 huecos                  30    6  0.50%   1842   129.7   43.6   -0.376   0.79    -7.98    71.2
  30 ETFs / 12 huecos                 30   12  0.50%   2966   208.8   43.1   -0.292   0.77   -13.16    88.0
  30 ETFs / 20 huecos                 30   20  0.50%   3441   242.3   42.8   -0.265   0.78   -15.75    92.1

  -- solo renta variable USA (universo homogeneo) --
     (los umbrales del bot estan calibrados sobre acciones;
      bonos y materias primas necesitarian reescalado)
  14 ETFs accion / 2 huecos           14    2  0.50%    539    37.9   43.8   -0.365   0.86    -1.54    27.6
  14 ETFs accion / 6 huecos           14    6  0.50%   1265    89.1   44.1   -0.304   0.87    -3.35    43.7
  14 ETFs accion / 6 huecos / 0.25%   14    6  0.25%   1265    89.1   44.1   -0.163   0.88    -1.61    24.2

  -- mismo numero de huecos, riesgo ajustado --
     (mas posiciones a la vez = mas riesgo total;
      bajar el riesgo por operacion lo compensa)
  30 ETFs / 12 huecos / 0.25%         30   12  0.25%   2966   208.8   43.1   -0.210   0.78    -6.60    64.3
  30 ETFs / 12 huecos / 1.0%          30   12  1.00%   2966   208.8   43.1   -0.332   0.75   -25.97    98.9
==============================================================================================================

======================================================================
¿QUE ESTA LIMITANDO LAS OPERACIONES?
======================================================================
    1395x ( 39.2% de las señales)  Cuenta llena (6 posiciones)
     461x ( 13.0% de las señales)  Cooldown por activo (6h)
      81x (  2.3% de las señales)  Volatilidad no válida: Volatilidad demasiado comprimida
       5x (  0.1% de las señales)  ADX insuficiente para sniper: 20.19 < 22.0 | Score final ins
       5x (  0.1% de las señales)  ADX insuficiente para sniper: 20.46 < 22.0 | Score final ins
       5x (  0.1% de las señales)  ADX insuficiente para sniper: 20.11 < 22.0 | Score final ins

======================================================================
¿EL RESULTADO DEL UNIVERSO LIMPIO ES SIGNIFICATIVO?
======================================================================
  Operaciones:            1265
  Expectativa observada:  -0.3037 EUR
  Intervalo 90%:          -0.5136  a  -0.0965
  Prob. expectativa > 0:  0.9%

  LECTURA: intervalo entero por DEBAJO de cero. Esto no es
           incertidumbre: es un resultado concluyente en
           contra. Con esta muestra, la estrategia pierde
           dinero en este universo, y no por mala suerte.

======================================================================
VEREDICTO
======================================================================
  Config actual (4 activos / 2 huecos):
    28.7 ops/año | +1.11% anual | DD 8.7%
  Universo limpio diversificado:
    89.1 ops/año | -3.35% anual | DD 43.7%

  Operaciones por año: x3.1
  La diversificacion NO mejoro la rentabilidad
  (+1.11% -> -3.35%)
  Si la ventaja no se mantiene fuera de los 4 activos
  elegidos, probablemente venia de haberlos elegido.

  JSON escrito en resultados/universo.json
======================================================================
```

## Proveedores de datos
```
PRUEBA DE PROVEEDORES — cada uno por separado
Cascada por defecto: ['yfinance', 'stooq', 'finnhub', 'alpha_vantage', 'twelve_data']

  OK    yfinance   SPY         3772 velas  2011-10-17 -> 2026-10-16
  FALLA stooq      SPY       ValueError: No se pudo descargar SPY con ningún provider. Detalles: ['stooq: 404 C
  OK    yfinance   BTC-USD     4415 velas  2014-09-17 -> 2026-10-18
  OK    coinbase   BTC-USD     4109 velas  2015-07-20 -> 2026-10-18
  FALLA stooq      GLD       ValueError: No se pudo descargar GLD con ningún provider. Detalles: ['stooq: 404 C

CRUCE yfinance vs stooq en SPY (ultimos cierres comunes)
  no se pudo cruzar: ValueError: No se pudo descargar SPY con ningún provider. Detalles: ['stooq: 404 Client Error: Not Found for url: https://stooq.com/q/d/l/?s=spy.us&i=d']
```

## Experimento por clase de activo
```
======================================================================
EXPERIMENTO POR CLASE DE ACTIVO
======================================================================
Periodo: 15y | Capital: 1000 EUR | Timeframe: 1d

Criterio de exito, fijado ANTES de ver los resultados:
  1. intervalo del 90% del bootstrap entero por encima de cero
  2. y que bata a comprar y mantener

======================================================================
CLASE: CRIPTO
======================================================================
  24/7. BTC tiene el sesgo de supervivencia mas fuerte que existe.
  Descargando con providers: coinbase,yfinance
    BTC-USD    coinbase     4109 velas  2015-07-20 -> 2026-10-18
    ETH-USD    coinbase     3804 velas  2016-05-18 -> 2026-10-18
    LTC-USD    coinbase     3714 velas  2016-08-17 -> 2026-10-18
    BCH-USD    coinbase     3221 velas  2017-12-20 -> 2026-10-18

  4 activos | 4 huecos | 551 operaciones en 10.7 años
  Winrate 47.9% | PF 1.10 | Expectativa +0.3153
  Rentabilidad anual del bot:       +1.47%
  Comprar y mantener (referencia):  +57.85%
  Peor drawdown: 14.7%

  Bootstrap (551 ops):
    Intervalo 90%: -0.1573  a  +0.7777
    Prob. expectativa > 0: 86.6%

  Largos:  362 ops | exp +0.8026 | WR 51.7%
  Cortos:  189 ops | exp -0.6180 | WR 40.7%

  >>> NO CONCLUYENTE: el cero esta dentro del intervalo.

======================================================================
CLASE: MATERIAS PRIMAS
======================================================================
  ETFs de materias primas, todos anteriores a 2011.
  Descargando con providers: yfinance,stooq
    GLD        yfinance     3772 velas  2011-10-17 -> 2026-10-16
    SLV        yfinance     3772 velas  2011-10-17 -> 2026-10-16
    USO        yfinance     3772 velas  2011-10-17 -> 2026-10-16
    DBC        yfinance     3772 velas  2011-10-17 -> 2026-10-16
    DBA        yfinance     3772 velas  2011-10-17 -> 2026-10-16
    UNG        yfinance     3772 velas  2011-10-17 -> 2026-10-16
    PPLT       yfinance     3772 velas  2011-10-17 -> 2026-10-16

  7 activos | 6 huecos | 892 operaciones en 14.2 años
  Winrate 45.4% | PF 0.94 | Expectativa -0.1684
  Rentabilidad anual del bot:       -1.11%
  Comprar y mantener (referencia):   +1.26%
  Peor drawdown: 30.8%

  Bootstrap (892 ops):
    Intervalo 90%: -0.4670  a  +0.1292
    Prob. expectativa > 0: 17.3%

  Largos:  480 ops | exp -0.1527 | WR 46.0%
  Cortos:  412 ops | exp -0.1866 | WR 44.7%

  >>> NO CONCLUYENTE: el cero esta dentro del intervalo.

======================================================================
CLASE: RENTA VARIABLE
======================================================================
  Indices amplios y sectores. El universo que ya perdio.
  Descargando con providers: yfinance,stooq
    SPY        yfinance     3772 velas  2011-10-17 -> 2026-10-16
    QQQ        yfinance     3772 velas  2011-10-17 -> 2026-10-16
    IWM        yfinance     3772 velas  2011-10-17 -> 2026-10-16
    DIA        yfinance     3772 velas  2011-10-17 -> 2026-10-16
    MDY        yfinance     3772 velas  2011-10-17 -> 2026-10-16
    XLE        yfinance     3772 velas  2011-10-17 -> 2026-10-16
    XLF        yfinance     3772 velas  2011-10-17 -> 2026-10-16
    XLK        yfinance     3772 velas  2011-10-17 -> 2026-10-16
    XLV        yfinance     3772 velas  2011-10-17 -> 2026-10-16
    XLI        yfinance     3772 velas  2011-10-17 -> 2026-10-16
    XLP        yfinance     3772 velas  2011-10-17 -> 2026-10-16
    XLY        yfinance     3772 velas  2011-10-17 -> 2026-10-16
    XLU        yfinance     3772 velas  2011-10-17 -> 2026-10-16
    XLB        yfinance     3772 velas  2011-10-17 -> 2026-10-16

  14 activos | 6 huecos | 1265 operaciones en 14.2 años
  Winrate 44.1% | PF 0.87 | Expectativa -0.3037
  Rentabilidad anual del bot:       -3.35%
  Comprar y mantener (referencia):  +11.97%
  Peor drawdown: 43.7%

  Bootstrap (1265 ops):
    Intervalo 90%: -0.5136  a  -0.0965
    Prob. expectativa > 0: 0.9%

  Largos:  856 ops | exp +0.0613 | WR 48.5%
  Cortos:  409 ops | exp -1.0676 | WR 35.0%

  >>> CONCLUYENTE EN CONTRA: intervalo entero por debajo de cero.

======================================================================
CLASE: BONOS
======================================================================
  Renta fija. Volatilidad muy distinta a la renta variable.
  Descargando con providers: yfinance,stooq
    TLT        yfinance     3772 velas  2011-10-17 -> 2026-10-16
    IEF        yfinance     3772 velas  2011-10-17 -> 2026-10-16
    LQD        yfinance     3772 velas  2011-10-17 -> 2026-10-16
    HYG        yfinance     3772 velas  2011-10-17 -> 2026-10-16
    SHY        yfinance     3772 velas  2011-10-17 -> 2026-10-16

  5 activos | 5 huecos | 585 operaciones en 14.2 años
  Winrate 42.7% | PF 0.57 | Expectativa -0.9936
  Rentabilidad anual del bot:       -5.93%
  Comprar y mantener (referencia):   -1.37%
  Peor drawdown: 58.8%

  Bootstrap (585 ops):
    Intervalo 90%: -1.2513  a  -0.7335
    Prob. expectativa > 0: 0.0%

  Largos:  239 ops | exp -1.2276 | WR 40.6%
  Cortos:  346 ops | exp -0.8319 | WR 44.2%

  >>> CONCLUYENTE EN CONTRA: intervalo entero por debajo de cero.

======================================================================
CLASE: DIVISAS
======================================================================
  ETFs de divisas contra el dolar.
  Descargando con providers: yfinance,stooq
    FXE        yfinance     3772 velas  2011-10-17 -> 2026-10-16
    FXY        yfinance     3772 velas  2011-10-17 -> 2026-10-16
    FXB        yfinance     3772 velas  2011-10-17 -> 2026-10-16
    FXF        yfinance     3772 velas  2011-10-17 -> 2026-10-16
    UUP        yfinance     3772 velas  2011-10-17 -> 2026-10-16

  5 activos | 5 huecos | 572 operaciones en 14.2 años
  Winrate 43.4% | PF 0.74 | Expectativa -0.6986
  Rentabilidad anual del bot:       -3.58%
  Comprar y mantener (referencia):   -0.76%
  Peor drawdown: 42.2%

  Bootstrap (572 ops):
    Intervalo 90%: -1.0267  a  -0.3762
    Prob. expectativa > 0: 0.0%

  Largos:  266 ops | exp -1.0258 | WR 39.8%
  Cortos:  306 ops | exp -0.4142 | WR 46.4%

  >>> CONCLUYENTE EN CONTRA: intervalo entero por debajo de cero.

======================================================================
RESUMEN
======================================================================
  CLASE                OPS    EXPECT   ANUAL%     B&H%   P(>0)  VEREDICTO
  cripto               551   +0.3153    +1.47   +57.85   86.6%  no concluyente
  materias_primas      892   -0.1684    -1.11    +1.26   17.3%  no concluyente
  renta_variable      1265   -0.3037    -3.35   +11.97    0.9%  en contra
  bonos                585   -0.9936    -5.93    -1.37    0.0%  en contra
  divisas              572   -0.6986    -3.58    -0.76    0.0%  en contra

  Ninguna clase pasa el criterio fijado de antemano.

  JSON escrito en resultados/clases.json
======================================================================
```

