# SHARK V15 SNIPER

Bot de señales sobre acciones e índices USA en timeframe de 30
minutos. Corre en Render como worker, opera en papel y avisa por
Telegram.

## Estado honesto

El bot **funciona**: descarga datos, evalúa la cadena de filtros,
abre y cierra operaciones en papel, persiste y avisa.

Lo que **todavía no está demostrado** es que tenga ventaja
estadística. Los resultados hasta ahora son ambiguos y la razón
principal es el tamaño de muestra, no el código:

- yfinance da 60 días de histórico en 30m. Es un tope de la fuente.
- Con el cooldown de 6h por activo salen ~20-25 operaciones por
  activo en esos 60 días.
- Con 25 operaciones, el intervalo de confianza de la expectativa
  es tan ancho que casi cualquier conclusión cabe dentro.

`validator/robustez.py` existe para medir exactamente eso en lugar
de adivinarlo.

**No subir dinero real a esto hasta que la muestra sea grande.**

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

validator/shark_v15_backtester.py   backtest walk-forward fiel
validator/robustez.py               bootstrap, Monte Carlo, barrido
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
