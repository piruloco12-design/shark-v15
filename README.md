# SHARK V15 SNIPER

Bot de señales sobre acciones e índices USA en timeframe de 30
minutos. Corre en Render como worker, opera en papel y avisa por
Telegram.

## Estado honesto — LEER ESTO ANTES DE TOCAR NADA

El bot **funciona** como software: descarga datos, evalúa la cadena
de filtros, abre y cierra operaciones en papel, persiste y avisa.

**Pero la estrategia no tiene ventaja.** Eso está medido, no
supuesto, y el resultado es concluyente (2026-10-18):

| Universo | Operaciones | Expectativa | Intervalo 90% | P(expect > 0) | Anual |
|---|---|---|---|---|---|
| 4 activos actuales | 407 | +0.425 | — | — | +1.11% |
| 30 ETFs diversificados | 2966 | **−0.292** | −0.375 a −0.210 | **0.0%** | −13.16% |
| 14 ETFs renta variable | 1265 | **−0.304** | −0.514 a −0.097 | **0.9%** | −3.35% |

Son **las mismas reglas** en los tres casos. Lo único que cambia es
qué instrumentos. En los dos universos limpios el intervalo de
confianza del 90% queda **entero por debajo de cero**: no es
incertidumbre por muestra pequeña, es un resultado en contra.

### Por qué el resultado de los 4 activos no cuenta

Los 4 activos son IWM + NVDA, AMZN y META. Las tres últimas son
mega-caps elegidas en 2026. Backtestear NVDA 15 años atrás no mide
la estrategia: mide que se acertó el ticker mirando el resultado.

*Una lista de tickers de hoy es información del futuro.*

El +1.11% anual venía de la selección de activos, no de las reglas.

### Qué NO arregla esto

- Más indicadores
- Ajustar umbrales (ya se barrieron 16 combinaciones de SL/TP)
- Más activos (se probó: empeora)
- Más posiciones simultáneas (se probó: empeora monótonamente,
  de −2.19% con 2 huecos a −15.75% con 20)
- Subir el riesgo (multiplica las pérdidas: −25.97% anual al 1%)

Los filtros sofisticados apenas intervienen: en el experimento, el
39% de las señales se pierden por cuenta llena y el 13% por
cooldown, frente a un 2% por volatilidad. Lo que decide es la
mecánica de la cuenta, no la inteligencia de los filtros.

### Para qué sirve este repositorio ahora

Como banco de pruebas honesto. La infraestructura sí es buena y
mata una hipótesis mala en una hora en vez de en cuatro meses:

- backtester de cartera con capital compartido y límite real de
  posiciones (`validator/cartera.py`)
- universo limpio de sesgo de supervivencia
- bootstrap y Monte Carlo de significancia (`validator/robustez.py`)
- traducción a economía real: rentabilidad anual y capital
  necesario para un objetivo de ingresos
- 172 comprobaciones automáticas y validación en CI

**No poner dinero real en la estrategia actual.** No por falta de
validación: por exceso de ella.

## Arrancar

```bash
pip install -r requirements.txt
cp .env.example .env      # rellenar las claves
python main.py
```

Variables mínimas en `.env`: `TELEGRAM_TOKEN`, `TELEGRAM_CHAT_ID`.
Las de los proveedores de datos solo si se usan como fallback;
yfinance no necesita clave.

## Validar

```bash
# Tests de regresión. No necesitan red ni claves.
python tests/test_config.py
python tests/test_arreglos.py
python tests/test_historial.py
python tests/test_cooldown.py

# Backtest walk-forward con la configuración de producción
python validator/shark_v15_backtester.py

# Lo mismo sobre 15 años de histórico diario, donde la muestra
# sí es grande. Es otro timeframe, no es la misma estrategia,
# pero dice si la lógica de fondo tiene algo.
TIMEFRAME=1d PERIOD=15y python validator/shark_v15_backtester.py

# ¿El resultado significa algo o es suerte?
python validator/robustez.py

# Backtest de CARTERA: una cuenta, capital compartido, límite
# real de posiciones simultáneas
python -c "
import sys; sys.path.insert(0,'validator')
from cartera import backtest_cartera
"

# El experimento que mató la hipótesis de diversificación:
# config actual vs 30 ETFs vs 14 ETFs de renta variable
python validator/experimento_universo.py
```

Todo esto corre también en GitHub Actions
(`.github/workflows/validacion.yml`) en cada push a `main`, y deja
la salida escrita en `resultados/ultimo.md`.

## Configuración por entorno

Nada de esto necesita tocar código:

| Variable | Defecto | Para qué |
|---|---|---|
| `ASSETS` | `IWM,NVDA,AMZN,META` | Activos a vigilar |
| `TIMEFRAME` | `30m` | `30m`, `1h`, `1d` |
| `PERIOD` | según timeframe | `60d`, `730d`, `15y`... |
| `DATA_PROVIDER_ORDER` | `yfinance,finnhub,alpha_vantage,twelve_data` | Cascada de proveedores |
| `MIN_BARS` | `220` | Mínimo de velas (ema200 necesita 200) |
| `SL_ATR_MULT` | `2.0` | Stop en múltiplos de ATR |
| `TP_ATR_MULT` | `2.5` | Objetivo en múltiplos de ATR |
| `CAPITAL` | `1000` | Capital de papel |
| `RISK_PER_TRADE` | `0.005` | Riesgo por operación (0.5%) |
| `MAX_OPEN_TRADES` | `2` | Operaciones simultáneas |
| `COOLDOWN_HOURS_PER_ASSET` | `6` | Espera tras operar un activo |

Una variable definida pero vacía cuenta como no definida.

## Persistencia

**La base de datos tiene que estar en un disco persistente.** En
Render, un worker sin bloque `disk:` tiene sistema de ficheros
efímero: cada deploy o reinicio deja la base de datos en blanco y
se pierden el histórico de operaciones, el capital acumulado, el
control de duplicados y el cooldown.

`render.yaml` ya monta un disco en `/var/data` y apunta
`DATABASE_NAME` ahí. **Si el servicio de Render se creó a mano por
el panel y no como Blueprint, `render.yaml` se ignora** y el disco
hay que añadirlo desde el panel.

Al arrancar, el bot comprueba la ruta y avisa por consola y por
Telegram si está en almacenamiento efímero.

## Archivo histórico de velas

`historial_mercado.py` guarda cada descarga en SQLite. Como el bot
gira cada 5 minutos, la ventana móvil de 60 días se va convirtiendo
en un archivo que crece.

```bash
python historial_mercado.py     # qué hay acumulado
```

No inventa el pasado: empieza a acumular desde que se pone en
marcha. Dentro de tres meses habrá tres meses de datos de 30m que
hoy no se pueden conseguir de ninguna fuente gratuita.

## Estructura

```
main.py                 arranque
live_engine.py          ciclo principal
config.py               toda la configuración

data_feed.py            descarga con cascada de proveedores
indicators.py           ema200, rsi, macd, atr, adx
historial_mercado.py    archivo histórico acumulado

market_regime.py        BULL_TREND / BEAR_TREND / TREND / RANGE / HIGH_VOL
signals.py              señal base
opportunity_scanner.py  señal secundaria (breakout, pullback, continuación)

session_volatility_intelligence.py  filtros de sesión y volatilidad
risk_control_engine.py  límites de riesgo y cooldown
ai_filter.py            puntuación por historial
trade_intelligence.py   puntuación por contexto
final_decision_engine.py        decisión ALLOW / BLOCK

risk_management.py      niveles de stop, objetivo y tamaño
paper_broker.py         apertura y cierre en papel
storage.py              SQLite
telegram_alerts.py      avisos

validator/shark_v15_backtester.py   backtest walk-forward por activo
validator/cartera.py                backtest de cartera (una cuenta)
validator/robustez.py               bootstrap, Monte Carlo, barrido
validator/experimento_universo.py   prueba de diversificación
tests/                              regresión, sin red
```

## Cadena de decisión

Una señal tiene que pasar todo esto para convertirse en operación:

1. **Datos**: al menos `MIN_BARS` velas de horario regular
2. **Duplicado**: no hay ya una operación abierta en ese activo
3. **Señal**: `signals.py`, o `opportunity_scanner.py` si la
   primera no dice nada
4. **Régimen**: tiene que estar en `SNIPER_ALLOWED_REGIMES`
5. **Sesión**: horario regular del mercado USA
6. **Volatilidad**: ni comprimida ni caótica
7. **Riesgo**: máximo de abiertas, pérdida diaria, drawdown,
   cooldown
8. **Puntuación final**: `ai*0.35 + contexto*0.40 + tendencia*0.25`
   por encima de `SNIPER_MIN_FINAL_SCORE`
9. **Tamaño**: positivo y finito

Cada bloqueo se registra con su motivo en `risk_events`.
