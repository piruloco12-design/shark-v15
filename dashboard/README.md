# Dashboard

Panel local con los resultados medidos. **No necesita servidor:**
los datos van incrustados en el HTML, así que basta abrir el
fichero con doble clic.

```bash
python dashboard/generar.py      # regenera index.html
```

Luego abre `dashboard/index.html` en el navegador.

## De dónde salen los datos

El generador lee los JSON que escriben los validadores:

| Fichero | Lo escribe |
|---|---|
| `resultados/clases.json` | `validator/experimento_clases.py` |
| `resultados/universo.json` | `validator/experimento_universo.py` |
| `resultados/robustez_1d.json` | `validator/robustez.py` con `TIMEFRAME=1d` |
| `resultados/robustez_30m.json` | `validator/robustez.py` con `TIMEFRAME=30m` |

Si falta alguno, esa sección aparece como "sin datos" en lugar de
romper la generación. Para rellenarlos todos:

```bash
pip install -r requirements.txt
TIMEFRAME=1d PERIOD=15y python validator/robustez.py
python validator/experimento_universo.py
python validator/experimento_clases.py
python dashboard/generar.py
```

Cada push a `main` los regenera en GitHub Actions y commitea el
resultado, así que `git pull` también trae el dashboard al día.

## Por qué los datos van incrustados

Un dashboard que cargue los JSON con `fetch` no funciona desde
`file://`: el navegador lo bloquea por CORS. Habría que levantar un
servidor para verlo. Incrustando los datos en el HTML, el fichero
funciona en cualquier sitio, se puede enviar por correo y sigue
funcionando sin conexión.

## Qué mirar

- **Intervalos de confianza** es la sección que importa. Si la
  barra cruza el cero, el resultado no distingue la estrategia de
  una moneda. Si queda entera a un lado, es concluyente.
- **Anual bot vs anual B&H**: comprar y mantener es la referencia
  honesta. Un bot que no la bate no aporta nada salvo riesgo.
- El botón **Ver tablas** cambia a la vista numérica de todo.
