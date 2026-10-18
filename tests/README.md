# Tests

Pruebas de regresión de los arreglos aplicados el 2026-10-18.
No necesitan conexión a internet ni claves de API.

```bash
python3 tests/test_arreglos.py
python3 tests/test_cooldown.py
```

Ambos devuelven código de salida 0 si todo pasa.

## Qué cubre `test_arreglos.py` (52 comprobaciones)

- **NaN en el setup de trade.** Un ATR NaN producía stop, target y
  tamaño de posición NaN. En Python `float('nan') <= 0` es `False`,
  así que esos NaN atravesaban todas las validaciones y se
  guardaban en la base de datos como un trade imposible de cerrar.
- **Coherencia direccional.** Un BUY con el stop por encima de la
  entrada se rechaza.
- **Cierre intravela.** El stop y el target se detectan con el
  máximo y el mínimo de la vela, no solo con el cierre, y la
  salida se ejecuta en el nivel exacto. Cuando la vela toca los
  dos, se asume el stop (supuesto pesimista, el mismo del
  backtester).
- **Recorte a horario regular.** 13 velas de 30m por día,
  09:30–15:30, sin fines de semana.
- **Mínimo de velas.** Por debajo de 220 se rechaza la descarga,
  porque `ema200` necesita 200 velas y sin ellas el bot deja de
  señalizar en silencio.
- **Filtro de sesión a prueba de fallos.** Si la zona horaria no se
  puede resolver, bloquea en vez de dejar pasar todo.

## Qué cubre `test_cooldown.py`

Que el backtester aplique el cooldown de 6 horas por activo que el
bot aplica de verdad en producción. Antes no lo aplicaba, y eso
infla el número de trades: sobre un activo sintético en tendencia
perfecta, 106 trades sin cooldown contra 25 con cooldown.

Los resultados de backtest anteriores al 2026-10-18 contaban unas
4 veces más trades de los que el bot puede ejecutar en real.

## Nota sobre el entorno

Estos tests sustituyen `yfinance` y `ta` por módulos vacíos y
construyen las velas e indicadores a mano, para poder ejercitar la
lógica sin red. Si en tu máquina falta el paquete `tzdata`, las
comprobaciones que dependen de `US/Eastern` se omiten y lo avisan
por pantalla; `tzdata` ya está en `requirements.txt`.
