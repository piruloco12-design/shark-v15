"""
Genera las tablas del informe DESDE el resultado. Nunca a mano.

Por que existe: en la entrega anterior escribi "13,77%" en el texto donde
el resultado decia 13,7614%, y "pasan 2 dictamenes" enumerando cuatro en
la misma frase. Las dos veces el numero salio de mi memoria en vez del
archivo. El plan lo pide explicito:

    "Genera tablas y cifras del texto automaticamente desde el resultado
     final."

Asi que las cifras de los documentos salen de aqui, y si el resultado
cambia, cambian con el.

Uso:
    python evaluador/informe_tablas.py resultados/v3/report.json
    python evaluador/informe_tablas.py resultados/v3/report.json --salida tablas.md
"""
from __future__ import annotations

import argparse
import io
import json
import os


def _f(valor, decimales=4, sufijo=""):
    """Un numero, o una raya si no hay. Nunca un cero inventado."""
    if valor is None:
        return "—"
    try:
        return f"{float(valor):.{decimales}f}{sufijo}"
    except (TypeError, ValueError):
        return str(valor)


def _pct(valor, decimales=4):
    if valor is None:
        return "—"
    try:
        return f"{float(valor) * 100:.{decimales}f}%"
    except (TypeError, ValueError):
        return str(valor)


def tabla_rendimiento(informe: dict) -> str:
    resumenes = informe.get("resumenes", {})
    por_universo: dict = {}
    for clave, r in resumenes.items():
        universo = clave.split("/")[0]
        por_universo.setdefault(universo, []).append((clave, r))

    lineas = []
    for universo in sorted(por_universo):
        lineas.append(f"\n**{universo}**\n")
        lineas.append("| Estrategia | CAGR | Retorno total | Caida maxima | "
                      "NAV final | Decisiones | Rechazadas | NAV fiable |")
        lineas.append("|---|---|---|---|---|---|---|---|")
        # La referencia primero, y el resto por CAGR. El orden no decide
        # nada, pero leer la referencia arriba evita comparar de memoria.
        filas = sorted(por_universo[universo],
                       key=lambda kv: (0 if "comprar_y_mantener" in kv[0] else 1,
                                       -(kv[1].get("cagr") or -9e9)))
        for clave, r in filas:
            nombre = clave.split("/", 1)[1]
            fiable = r.get("nav_fiable")
            marca = {True: "si", False: "**NO**", None: "—"}.get(fiable, str(fiable))
            lineas.append(
                f"| {nombre} | {_pct(r.get('cagr'))} | "
                f"{_pct(r.get('retorno_total'))} | "
                f"{_pct(r.get('max_drawdown_diario'))} | "
                f"{_f(r.get('nav_final'), 6)} | "
                f"{r.get('decisiones', '—')} | "
                f"{r.get('intenciones_rechazadas', '—')} | {marca} |")
    return "\n".join(lineas)


def tabla_diferenciales(informe: dict) -> str:
    """Cada candidata frente a comprar y mantener de SU universo."""
    resumenes = informe.get("resumenes", {})
    lineas = ["| Universo | Estrategia | CAGR | Referencia | Diferencia (pts/ano) |",
              "|---|---|---|---|---|"]
    for clave, r in sorted(resumenes.items()):
        universo, nombre = clave.split("/", 1)
        if "comprar_y_mantener" in nombre:
            continue
        ref = resumenes.get(f"{universo}/comprar_y_mantener", {})
        cagr, cagr_ref = r.get("cagr"), ref.get("cagr")
        if cagr is None or cagr_ref is None:
            dif = "—"
        else:
            dif = f"{(cagr - cagr_ref) * 100:+.4f}"
        lineas.append(f"| {universo} | {nombre} | {_pct(cagr)} | "
                      f"{_pct(cagr_ref)} | {dif} |")
    return "\n".join(lineas)


def tabla_contrastes(informe: dict) -> str:
    contrastes = informe.get("contrastes", {})
    holm = informe.get("holm", {})
    lineas = ["| Hipotesis | Obs. | Diferencial medio | p-valor | "
              "Umbral Holm | Rechaza |", "|---|---|---|---|---|---|"]
    for clave in sorted(contrastes):
        c = contrastes[clave]
        h = holm.get(clave, {})
        rechaza = h.get("rechaza_nula")
        lineas.append(
            f"| {clave} | {c.get('observaciones', '—')} | "
            f"{_f(c.get('diferencial_medio_periodico'), 8)} | "
            f"{_f(c.get('p_valor_una_cola'), 6)} | "
            f"{_f(h.get('umbral'), 6)} | "
            f"{'SI' if rechaza else 'no'} |")
    if contrastes:
        metodo = list(contrastes.values())[0]
        lineas.append("")
        lineas.append(f"Metodo: {metodo.get('metodo', '—')}. "
                      f"Bloque medio {_f(metodo.get('longitud_bloque_media'), 1)}, "
                      f"{metodo.get('remuestras', '—')} remuestras, "
                      f"semilla {metodo.get('semilla', '—')}.")
    return "\n".join(lineas)


def tabla_rotacion_y_exposicion(informe: dict) -> str:
    resumenes = informe.get("resumenes", {})
    lineas = ["| Universo / estrategia | Rotacion s/ patrimonio medio | "
              "Rotacion s/ capital inicial | Nominal ejecutado | Comisiones |",
              "|---|---|---|---|---|"]
    for clave, r in sorted(resumenes.items()):
        lineas.append(
            f"| {clave} | "
            f"{_f(r.get('rotacion_anual_sobre_patrimonio_medio'), 4)} | "
            f"{_f(r.get('rotacion_anual_nominal_sobre_capital_inicial'), 4)} | "
            f"{_f(r.get('nominal_ejecutado'), 2)} | "
            f"{_f(r.get('comisiones_moneda'), 4)} |")
    lineas.append("")
    lineas.append("Convencion de rotacion: nominal de AMBAS patas, entrada "
                  "inicial incluida. Las dos columnas existen porque la "
                  "segunda es la que se publico antes y no son comparables.")
    return "\n".join(lineas)


def encabezado(informe: dict, ruta: str) -> str:
    reg = informe.get("registro", {})
    estado = reg.get("estado", "?")
    lineas = [
        "# Tablas del experimento",
        "",
        "**Generadas automaticamente. No editar a mano: se regeneran.**",
        "",
        f"- Origen: `{ruta}`",
        f"- Corrida: `{informe.get('run_id', '—')}`",
        f"- Registro: `{informe.get('registro_archivo', '—')}`",
        f"- Hash del registro: `{reg.get('hash_registro', '—')}`",
        f"- Commit: `{reg.get('commit', '—')}`",
        f"- Estado declarado: **{estado}**",
        f"- Universo: `{reg.get('universo_etiqueta', '—')}`",
        f"- Hipotesis declaradas: {reg.get('hipotesis_declaradas', '—')}",
    ]
    if estado == "EXPLORATORIO":
        lineas += [
            "",
            "> Estado EXPLORATORIO. Las series ya se han mirado antes, asi "
            "que estas cifras no son una prueba confirmatoria por mucho que "
            "la familia este declarada y corregida. Renombrar el tramo no lo "
            "convierte en datos nuevos.",
        ]
    panel = informe.get("panel", {})
    if panel:
        lineas += ["", f"- Panel: `{panel.get('archivo', '—')}`, "
                       f"{panel.get('filas', '—')} filas, hash "
                       f"`{panel.get('hash', '—')}`"]
    return "\n".join(lineas)


def generar(ruta_informe: str) -> str:
    informe = json.load(io.open(ruta_informe, encoding="utf-8"))
    partes = [
        encabezado(informe, ruta_informe),
        "\n## Rendimiento por universo\n",
        tabla_rendimiento(informe),
        "\n\n## Diferencial frente a comprar y mantener\n",
        tabla_diferenciales(informe),
        "\n\n## Contrastes y correccion familiar\n",
        tabla_contrastes(informe),
        "\n\n## Rotacion y costes\n",
        tabla_rotacion_y_exposicion(informe),
        "",
    ]
    return "\n".join(partes)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("informe", nargs="?", default="resultados/v3/report.json")
    ap.add_argument("--salida", default=None,
                    help="archivo .md donde escribir; por defecto, a pantalla")
    args = ap.parse_args()
    if not os.path.exists(args.informe):
        raise SystemExit(
            f"no existe {args.informe}. Las tablas salen del resultado: si no "
            f"hay resultado, no hay tablas. Corre evaluador/experimento.py "
            f"(necesita red) o apunta a otro informe.")
    texto = generar(args.informe)
    if args.salida:
        io.open(args.salida, "w", encoding="utf-8").write(texto)
        print(f"escrito {args.salida} ({len(texto)} caracteres)")
    else:
        print(texto)


if __name__ == "__main__":
    main()
