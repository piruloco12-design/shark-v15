# Validacion SHARK V15

Fecha:   2026-10-19 14:26 UTC
Commit:  0a637e44
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
  N/C    I29 mas Sharpe pero menos dinero  -> es requisito del INFORME del experimento, no del codigo

==============================================================
RESULTADO: 85 pruebas pasadas, 0 fallos, 5 casos NO cubiertos
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

## Imports
```
28/28 modulos importan
```

## Diagnostico del feed
```
Timeframe 30m | Periodo 60d | MIN_BARS 220
Providers ['yfinance', 'finnhub', 'alpha_vantage', 'twelve_data']

ACTIVO  PROVIDER    VELAS  DIAS  X/DIA  HORAS ET
IWM     yfinance      769    60   12.8  [9, 10, 11, 12, 13, 14, 15]
        2026-07-27 09:30:00-04:00  ->  2026-10-19 10:00:00-04:00
NVDA    yfinance      769    60   12.8  [9, 10, 11, 12, 13, 14, 15]
        2026-07-27 09:30:00-04:00  ->  2026-10-19 10:00:00-04:00
AMZN    yfinance      769    60   12.8  [9, 10, 11, 12, 13, 14, 15]
        2026-07-27 09:30:00-04:00  ->  2026-10-19 10:00:00-04:00
META    yfinance      769    60   12.8  [9, 10, 11, 12, 13, 14, 15]
        2026-07-27 09:30:00-04:00  ->  2026-10-19 10:00:00-04:00
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
  OK | yfinance | 769 velas
Descargando NVDA...
  OK | yfinance | 769 velas
Descargando AMZN...
  OK | yfinance | 769 velas
Descargando META...
  OK | yfinance | 769 velas

=================================================================
  FASE 1: BACKTEST COMPLETO (todo el período)
=================================================================

============================================================
IWM | FULL | Bars: 569
============================================================
Capital:     1000.00 → 989.50  (-10.50)
Señales:     64 generadas | 13 ALLOW | 51 BLOCK
Trades:      12 cerrados | 6 wins | 6 losses
Winrate:     50.0%
Avg Trade:   -0.82
Avg Win:     4.77  |  Avg Loss: 6.42
Expectancy:  -0.82 por trade
PF:          0.74
Max DD:      24.42 (2.4%)
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
NVDA | FULL | Bars: 569
============================================================
Capital:     1000.00 → 971.87  (-28.13)
Señales:     48 generadas | 19 ALLOW | 29 BLOCK
Trades:      19 cerrados | 7 wins | 12 losses
Winrate:     36.8%
Avg Trade:   -1.48
Avg Win:     5.44  |  Avg Loss: 5.52
Expectancy:  -1.48 por trade
PF:          0.58
Max DD:      33.79 (3.4%)
Avg Bars:    12 velas
Regímenes:   {'BULL_TREND': 7, 'BEAR_TREND': 7, 'TREND': 5}
Señales:     {'BUY': 10, 'SELL': 9}
Bloqueos principales:
    29x  Cooldown por activo (6h)

============================================================
AMZN | FULL | Bars: 569
============================================================
Capital:     1000.00 → 997.84  (-2.16)
Señales:     78 generadas | 18 ALLOW | 60 BLOCK
Trades:      18 cerrados | 9 wins | 9 losses
Winrate:     50.0%
Avg Trade:   -0.12
Avg Win:     5.48  |  Avg Loss: 5.72
Expectancy:  -0.12 por trade
PF:          0.96
Max DD:      24.19 (2.4%)
Avg Bars:    14 velas
Regímenes:   {'BEAR_TREND': 9, 'BULL_TREND': 4, 'TREND': 5}
Señales:     {'SELL': 13, 'BUY': 5}
Bloqueos principales:
    60x  Cooldown por activo (6h)

============================================================
META | FULL | Bars: 569
============================================================
Capital:     1000.00 → 1006.62  (+6.62)
Señales:     71 generadas | 16 ALLOW | 55 BLOCK
Trades:      15 cerrados | 8 wins | 7 losses
Winrate:     53.3%
Avg Trade:   0.46
Avg Win:     5.77  |  Avg Loss: 5.61
Expectancy:  0.46 por trade
PF:          1.17
Max DD:      24.43 (2.4%)
Avg Bars:    13 velas
Regímenes:   {'BEAR_TREND': 4, 'TREND': 2, 'BULL_TREND': 9}
Señales:     {'SELL': 5, 'BUY': 10}
Bloqueos principales:
    55x  Cooldown por activo (6h)


#################################################################
  CONSOLIDADO FULL PERIOD — 4 activos
#################################################################
  Señales:     261 generadas | 66 ALLOW | 195 BLOCK
  Trades:      64 cerrados | 30 wins | 34 losses
  Winrate:     46.9%
  Avg Trade:   -0.52
  Avg Win:     5.40  |  Avg Loss: 5.75
  Expectancy:  -0.52 por trade
  PF:          0.83
  PnL total:   -34.16
  Peor DD:     33.79
  -------------------------------------------------------------
  Suma PnL trades:  -33.27   (debe cuadrar con PnL total)
  ✅ Cuadra (dif. 0.89, son costes de trades aún abiertos)
#################################################################

  VEREDICTO:
  ❌  NO HAY EDGE. Expectancy negativa.


=================================================================
  FASE 2: WALK-FORWARD (70% train / 30% test)
=================================================================

--- IWM TRAIN ---
  ============================================================
  IWM | TRAIN | Bars: 338
  ============================================================
  Capital:     1000.00 → 981.46  (-18.54)
  Señales:     44 generadas | 9 ALLOW | 35 BLOCK
  Trades:      8 cerrados | 3 wins | 5 losses
  Winrate:     37.5%
  Avg Trade:   -2.24
  Avg Win:     4.80  |  Avg Loss: 6.47
  Expectancy:  -2.24 por trade
  PF:          0.45
  Max DD:      21.58 (2.2%)
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
  IWM | TEST | Bars: 231
  ============================================================
  Capital:     1000.00 → 1007.51  (+7.51)
  Señales:     21 generadas | 5 ALLOW | 16 BLOCK
  Trades:      4 cerrados | 3 wins | 1 losses
  Winrate:     75.0%
  Avg Trade:   2.04
  Avg Win:     4.81  |  Avg Loss: 6.26
  Expectancy:  2.04 por trade
  PF:          2.30
  Max DD:      8.53 (0.8%)
  Avg Bars:    8 velas
  Regímenes:   {'BEAR_TREND': 2, 'TREND': 2}
  Señales:     {'SELL': 4}
  Bloqueos principales:
      15x  Cooldown por activo (6h)
       1x  ADX insuficiente para sniper: 20.88 < 22.0 | Score final insuficiente para sniper: 54.30 <

--- NVDA TRAIN ---
  ============================================================
  NVDA | TRAIN | Bars: 338
  ============================================================
  Capital:     1000.00 → 972.22  (-27.78)
  Señales:     28 generadas | 11 ALLOW | 17 BLOCK
  Trades:      11 cerrados | 3 wins | 8 losses
  Winrate:     27.3%
  Avg Trade:   -2.53
  Avg Win:     5.45  |  Avg Loss: 5.52
  Expectancy:  -2.53 por trade
  PF:          0.37
  Max DD:      33.79 (3.4%)
  Avg Bars:    11 velas
  Regímenes:   {'BULL_TREND': 6, 'BEAR_TREND': 3, 'TREND': 2}
  Señales:     {'BUY': 7, 'SELL': 4}
  Bloqueos principales:
      17x  Cooldown por activo (6h)

--- NVDA TEST ---
  ============================================================
  NVDA | TEST | Bars: 231
  ============================================================
  Capital:     1000.00 → 999.64  (-0.36)
  Señales:     20 generadas | 8 ALLOW | 12 BLOCK
  Trades:      8 cerrados | 4 wins | 4 losses
  Winrate:     50.0%
  Avg Trade:   -0.04
  Avg Win:     5.59  |  Avg Loss: 5.68
  Expectancy:  -0.04 por trade
  PF:          0.98
  Max DD:      17.35 (1.7%)
  Avg Bars:    13 velas
  Regímenes:   {'BULL_TREND': 1, 'TREND': 3, 'BEAR_TREND': 4}
  Señales:     {'BUY': 3, 'SELL': 5}
  Bloqueos principales:
      12x  Cooldown por activo (6h)

--- AMZN TRAIN ---
  ============================================================
  AMZN | TRAIN | Bars: 338
  ============================================================
  Capital:     1000.00 → 1010.13  (+10.13)
  Señales:     45 generadas | 10 ALLOW | 35 BLOCK
  Trades:      10 cerrados | 6 wins | 4 losses
  Winrate:     60.0%
  Avg Trade:   1.01
  Avg Win:     5.47  |  Avg Loss: 5.67
  Expectancy:  1.01 por trade
  PF:          1.45
  Max DD:      24.19 (2.4%)
  Avg Bars:    14 velas
  Regímenes:   {'BEAR_TREND': 6, 'BULL_TREND': 1, 'TREND': 3}
  Señales:     {'SELL': 8, 'BUY': 2}
  Bloqueos principales:
      35x  Cooldown por activo (6h)

--- AMZN TEST ---
  ============================================================
  AMZN | TEST | Bars: 231
  ============================================================
  Capital:     1000.00 → 987.91  (-12.09)
  Señales:     30 generadas | 8 ALLOW | 22 BLOCK
  Trades:      8 cerrados | 3 wins | 5 losses
  Winrate:     37.5%
  Avg Trade:   -1.51
  Avg Win:     5.46  |  Avg Loss: 5.70
  Expectancy:  -1.51 por trade
  PF:          0.58
  Max DD:      19.58 (2.0%)
  Avg Bars:    14 velas
  Regímenes:   {'BEAR_TREND': 3, 'TREND': 2, 'BULL_TREND': 3}
  Señales:     {'SELL': 5, 'BUY': 3}
  Bloqueos principales:
      22x  Cooldown por activo (6h)

--- META TRAIN ---
  ============================================================
  META | TRAIN | Bars: 338
  ============================================================
  Capital:     1000.00 → 1000.61  (+0.61)
  Señales:     40 generadas | 11 ALLOW | 29 BLOCK
  Trades:      10 cerrados | 5 wins | 5 losses
  Winrate:     50.0%
  Avg Trade:   0.08
  Avg Win:     5.73  |  Avg Loss: 5.57
  Expectancy:  0.08 por trade
  PF:          1.03
  Max DD:      24.43 (2.4%)
  Avg Bars:    9 velas
  Regímenes:   {'BEAR_TREND': 3, 'TREND': 2, 'BULL_TREND': 5}
  Señales:     {'SELL': 4, 'BUY': 6}
  Bloqueos principales:
      29x  Cooldown por activo (6h)

--- META TEST ---
  ============================================================
  META | TEST | Bars: 231
  ============================================================
  Capital:     1000.00 → 994.59  (-5.41)
  Señales:     25 generadas | 6 ALLOW | 19 BLOCK
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
  Señales:     157 generadas | 41 ALLOW | 116 BLOCK
  Trades:      39 cerrados | 17 wins | 22 losses
  Winrate:     43.6%
  Avg Trade:   -0.89
  Avg Win:     5.42  |  Avg Loss: 5.77
  Expectancy:  -0.89 por trade
  PF:          0.73
  PnL total:   -35.58
  Peor DD:     33.79
  -------------------------------------------------------------
  Suma PnL trades:  -34.82   (debe cuadrar con PnL total)
  ✅ Cuadra (dif. 0.76, son costes de trades aún abiertos)
#################################################################

  VEREDICTO:
  ❌  NO HAY EDGE. Expectancy negativa.


#################################################################
  CONSOLIDADO TEST (OUT-OF-SAMPLE) — 4 activos
#################################################################
  Señales:     96 generadas | 27 ALLOW | 69 BLOCK
  Trades:      25 cerrados | 12 wins | 13 losses
  Winrate:     48.0%
  Avg Trade:   -0.38
  Avg Win:     5.38  |  Avg Loss: 5.70
  Expectancy:  -0.38 por trade
  PF:          0.87
  PnL total:   -10.35
  Peor DD:     19.58
  -------------------------------------------------------------
  Suma PnL trades:  -9.45   (debe cuadrar con PnL total)
  ✅ Cuadra (dif. 0.90, son costes de trades aún abiertos)
#################################################################

  VEREDICTO:
  ❌  NO HAY EDGE. Expectancy negativa.


=================================================================
  COMPARACIÓN TRAIN vs TEST
=================================================================

  IWM:
    TRAIN: 8 trades | WR 37.5% | PF 0.45 | Exp -2.24
    TEST:  4 trades | WR 75.0% | PF 2.30 | Exp 2.04
    ⚠️  Pocos trades para comparar

  NVDA:
    TRAIN: 11 trades | WR 27.3% | PF 0.37 | Exp -2.53
    TEST:  8 trades | WR 50.0% | PF 0.98 | Exp -0.04
    ✅  Consistente entre train y test

  AMZN:
    TRAIN: 10 trades | WR 60.0% | PF 1.45 | Exp 1.01
    TEST:  8 trades | WR 37.5% | PF 0.58 | Exp -1.51
    ⚠️  Degradación significativa train→test

  META:
    TRAIN: 10 trades | WR 50.0% | PF 1.03 | Exp 0.08
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
NVDA | FULL | Bars: 3571
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
AMZN | FULL | Bars: 3571
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
META | FULL | Bars: 3425
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
  IWM | TRAIN | Bars: 2439
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
  NVDA | TRAIN | Bars: 2439
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
  AMZN | TRAIN | Bars: 2439
  ============================================================
  Capital:     1000.00 → 1012.15  (+12.15)
  Señales:     164 generadas | 95 ALLOW | 69 BLOCK
  Trades:      95 cerrados | 45 wins | 50 losses
  Winrate:     47.4%
  Avg Trade:   0.13
  Avg Win:     6.24  |  Avg Loss: 5.37
  Expectancy:  0.13 por trade
  PF:          1.05
  Max DD:      56.73 (5.7%)
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
  META | TRAIN | Bars: 2337
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
  Trades:      349 cerrados | 168 wins | 181 losses
  Winrate:     48.1%
  Avg Trade:   0.23
  Avg Win:     6.17  |  Avg Loss: 5.29
  Expectancy:  0.23 por trade
  PF:          1.08
  PnL total:   +79.24
  Peor DD:     56.73
  -------------------------------------------------------------
  Suma PnL trades:  +79.27   (debe cuadrar con PnL total)
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
    TRAIN: 95 trades | WR 47.4% | PF 1.05 | Exp 0.13
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
  IWM     yfinance      769 velas
  NVDA    yfinance      769 velas
  AMZN    yfinance      769 velas
  META    yfinance      769 velas

Operaciones totales con la config actual: 64

==============================================================
1) BOOTSTRAP DE LA EXPECTATIVA
==============================================================
Operaciones:            64
Expectativa observada:  -0.5199 € por operación
Intervalo 90%:          -1.6682  a  +0.6633
Prob. expectativa > 0:  23.0%

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
   Drawdown mediano:        5.98%
   Drawdown percentil 95:   8.38%
   Peor drawdown simulado:  11.17%
   Capital final (fijo):    966.73 €

B) REMUESTREO: si las próximas operaciones salieran de
   esta misma distribución
   Capital final, percentil 5:   894.66 €
   Capital final, mediana:       967.05 €
   Capital final, percentil 95:  1041.31 €
   Drawdown percentil 95:        12.08%
   Prob. terminar en pérdida:    76.7%
   Prob. perder la mitad:        0.0%

LECTURA: el drawdown que hay que estar dispuesto a aguantar es
         del 8.4%, no el que salió en el histórico: el orden
         de las operaciones es azar y la racha mala no tiene por
         qué haber caído dentro del periodo de prueba.
         El remuestreo da 77% de probabilidad de acabar
         en pérdida sobre otras 64 operaciones.

==============================================================
3) BARRIDO DE PARÁMETROS (SL / TP)
==============================================================

   SL    TP   R:R   OPS    WR%    EXPECT     PF  VEREDICTO
--------------------------------------------------------------
  1.5   2.0  1.33    75   40.0   -1.3798   0.61
  1.5   2.5  1.67    71   36.6   -1.1679   0.69
  1.5   3.0  2.00    66   34.8   -0.8468   0.78
  1.5   3.5  2.33    64   32.8   -0.6174   0.85
  2.0   2.0  1.00    70   47.1   -1.0706   0.65
  2.0   2.5  1.25    64   46.9   -0.5199   0.83 <-- CONFIG ACTUAL
  2.0   3.0  1.50    60   45.0   -0.1830   0.94
  2.0   3.5  1.75    60   38.3   -0.5423   0.85
  2.5   2.0  0.80    69   52.2   -0.9391   0.65
  2.5   2.5  1.00    64   51.6   -0.4841   0.82
  2.5   3.0  1.20    59   49.2   -0.2389   0.92
  2.5   3.5  1.40    58   41.4   -0.6815   0.79
  3.0   2.0  0.67    65   56.9   -0.7911   0.66
  3.0   2.5  0.83    60   56.7   -0.3442   0.85
  3.0   3.0  1.00    58   51.7   -0.3609   0.86
  3.0   3.5  1.17    55   45.5   -0.6030   0.80

Combinaciones con expectativa positiva: 0 de 16
Configuración actual (SL 2.0 / TP 2.5): expectativa -0.5199, PF 0.83
Vecinos inmediatos con expectativa positiva: 0 de 8

LECTURA: la configuración actual no tiene expectativa positiva
         en este periodo. Si otras combinaciones sí, ojo: elegir
         ahora la mejor de la tabla ES sobreajustar.

==============================================================
4) ECONOMÍA REAL: ¿QUÉ SIGNIFICA ESTO EN DINERO?
==============================================================
Periodo cubierto:       0.2 años
Operaciones:            64  ->  272.6 al año
Riesgo por operación:   5.00 € (0.5% de 1000 €)
Expectativa en riesgo:  -0.104 R por operación

RENTABILIDAD ANUAL SOBRE 1000 €
  pesimista (p05)  :  -454.82 €/año  =  -45.48% anual
  central          :  -141.75 €/año  =  -14.17% anual
  optimista (p95)  :  +180.85 €/año  =  +18.09% anual

CAPITAL NECESARIO PARA SACAR 1.000 €/MES (12.000 €/año)
  pesimista (p05)  : imposible, la expectativa es negativa
  central          : imposible, la expectativa es negativa
  optimista (p95)  :         66,353 €

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

