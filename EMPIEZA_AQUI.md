# Por dónde empezar

**Para Astra, 2026-10-20, tras tu segunda auditoría.**

## Los dos archivos que importan

1. **`PARA_ASTRA_LO_QUE_NECESITO.md`** — lo único que no puedo resolver
   yo. Diez puntos, cada uno con la medida que lo enmarca, lo que haría
   por defecto si no contestas, y escrito para que puedas responder en una
   línea. Si solo vas a leer uno, lee este.

2. **`RESPUESTA_A_LA_SEGUNDA_AUDITORIA.md`** — el estado completo. Los
   cinco cambios de `PLAN_CLAUDE.md` en orden, cada uno con el caso que
   fallaba **medido antes** de tocar el código; mis cuatro afirmaciones
   retiradas; los dos oráculos que siguen en rojo y por qué; y lo que
   falta.

## El estado en tres líneas

Las **24 puertas** de tu plan pasan, desplegadas en 43 comprobaciones. De
tus 15 oráculos cumplen **13**: O09 porque su criterio no lee mi código, y
O13 porque su criterio ejecutable y su prosa piden cosas incompatibles.
499 comprobaciones propias en verde.

## Lo que más te va a interesar, y no te gustará

Los arreglos de contabilidad **no mueven el titular**. El CAGR de M03 en
renta variable sigue en 13,7614% y comprar y mantener en 13,7509%. Los
tres contratos que estaban roto —dinero que desaparecía del NAV, dividendo
cobrado dos veces, NAV mezclando precios de dos instantes— están
arreglados y demostrados, y su efecto agregado sobre estas cifras está en
el cuarto decimal. El §8 de la respuesta explica por qué, sin
escaquearse: la venta diferida solo muerde con días de liquidación > 0 y
el experimento corre con 0; el dividendo doble solo muerde si se pasan
dividendos como eventos y el experimento usa retorno total; y el NAV de
los días con fill afecta a días intermedios, mientras el CAGR sale de los
extremos.

Arreglar la contabilidad no rescató la estrategia. La contabilidad buena
dice lo mismo que la mala, y ahora se puede demostrar que lo dice bien.

## Y una medición que cambia el cuadro

Con el panel real y 1.000 de capital, el diferencial de CAGR de M03 frente
a comprar y mantener:

| Tarifa | Multiactivo | Renta variable |
|---|---|---|
| 8 pb sin mínimo *(el escenario declarado)* | +1,3335 | +0,0105 |
| 8 pb + mínimo de 0,50 por orden | **−1,0690** | **−1,7535** |
| 8 pb + mínimo de 2,00 por orden | **−21,4850** | **−8,5542** |

La ventaja no se reduce con una tarifa de minorista: **cambia de signo con
un mínimo de medio euro por orden**. Comprar y mantener emite 14 órdenes
en catorce años; M03 emite 967, y a ese número las comisiones solas
superan el capital inicial. Detalle en el §«La tarifa decide el resultado»
de la respuesta, y es la pregunta B2.

## Dos cosas que encontré sin buscarlas

**CI llevaba siete corridas pisando `resultados/v2/`**, la entrega que
auditaste: el paso de validación corría el experimento con salida por
defecto ahí y commiteaba el resultado. Nada se perdió —estaba en el
historial— y la carpeta está restaurada al estado de `037d373`, el que
viajó en el paquete que viste, con `resultados/v2/LEEME_SOBRESCRITURAS.md`
y las cifras de las siete corridas. Lo descubrí por casualidad generando
tablas.

**Con comisión mínima por orden el libro se iba a efectivo negativo.**
Salió al medir la sensibilidad a la tarifa sobre el panel real: `vender`
hacía `neto = nominal - comision` sin guarda, y con un mínimo de 2 una
venta de 0,60 de nominal dejaba un neto de −1,40. Arreglado, puertas CF1 y
CF2, con la evidencia del antes en
`resultados/v3/sensibilidad_tarifa_ANTES_del_arreglo.txt`. Es la pregunta
B2 del otro documento, y creo que es la más importante de todas: con 1.000
de capital, un mínimo de 1 por orden son 50 pb por pata sobre una posición
de 200, no los 8 pb declarados.

## Para comprobarlo tú

```bash
# Las 24 puertas de tu plan, desplegadas en 43 comprobaciones
python tests/test_puertas.py

# El experimento COMPLETO de punta a punta, sin red
python tests/test_experimento_humo.py

# Toda la bateria: 499 comprobaciones
for t in tests/test_*.py; do python "$t"; done

# Tus propios oraculos contra este arbol (oraculos_v2.py es TUYO: viene
# en tu paquete de auditoria, no en este zip)
python oraculos_v2.py --repo . --salida mis_oraculos.json

# Las tablas, generadas DESDE el resultado y nunca a mano
python evaluador/informe_tablas.py resultados/v3/report.json
```

## La evidencia del antes y el después

En `resultados/v3/`:

| Archivo | Contiene |
|---|---|
| `puertas_ANTES_cambio1.txt` | las 12 puertas del cambio 1, once fallando |
| `puertas_DESPUES_cambio*.txt` | el estado tras cada cambio |
| `oraculos_astra_antes.json` | tus 15 oráculos con 1 en verde |
| `oraculos_astra_tras_cambio*.json` | la progresión hasta 13 |
| `o13_tres_conductas.json` | las cuatro conductas de O13, medidas |
| `sensibilidad_tarifa.json` | el efecto de la comisión mínima, panel real |
| `sensibilidad_tarifa_ANTES_del_arreglo.txt` | la corrida que abortaba |

`resultados/v2/` es la entrega que auditaste, restaurada, con su aviso de
sobrescrituras.

## Lo que no está en el zip

Ni `.env`, ni bases de datos, ni historial de git: se exporta con
`git archive` sobre los archivos rastreados.

Tampoco va `.env.example`: el `.gitignore` tiene un patrón `.env.*` que lo
atrapa, así que nunca estuvo rastreado. En la entrega anterior escribí que
sus claves «están vacías», lo que daba a entender que viajaba en el
paquete. No viajaba. Lo dejo así a propósito en vez de añadir una
excepción a una regla que ignora archivos de entorno: es una plantilla de
despliegue y no hace falta para auditar nada.

Y el aviso de seguridad de la vez anterior sigue vigente: el repositorio
contiene, en commits anteriores al 2026-10-19, una cadena con la forma
exacta de una clave de Google en un test de censura. Está revocada y no
está en el árbol actual, pero sigue en el historial.

## Lo que no está hecho

`resultados/v3/report.json` **no está generado con datos reales**. El
experimento necesita red para 31 activos y 15 años, y el entorno donde
trabajo no la tiene: ni pip resuelve DNS. Lo genera CI, y el último
intento falló por un KeyError mío en un `print` —ya arreglado, con la
prueba de humo que lo habría cazado en segundos—. Las cifras que cito
salen de `resultados/v2/` y de las mediciones sobre su panel guardado, que
es real.
