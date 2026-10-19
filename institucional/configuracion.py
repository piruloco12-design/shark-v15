"""
Configuracion de la ampliacion institucional (seccion 15.11).

Dos reglas del documento que el validador hace cumplir de verdad:

  1. `new_strategy_capital_budget: null` es deliberado. Una estrategia
     independiente operativa sin presupuesto explicito se RECHAZA. null
     no significa "toda la cuenta", significa "sin autorizacion".

  2. Un `enabled` aqui no permite enviar ordenes. OBSERVE solo recoge
     evidencia. Para que un modulo bloquee algo hace falta, ademas,
     enforce=True y que el modo no sea OBSERVE.

Este objeto no cambia ningun limite existente de Shark. Los limites de
capital, perdida, nominal, concentracion y numero de posiciones se
heredan de config.py y no se tocan desde aqui.
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass, field

OFF = "OFF"
OBSERVE = "OBSERVE"
ENFORCE = "ENFORCE"

MODOS_VALIDOS = (OFF, OBSERVE, ENFORCE)

# Modulos de contexto: solo pueden vetar o reducir ENTRADAS nuevas.
MODULOS_CONTEXTO = ("M01_costs", "M02_trend_context", "M03_candidate_ranking",
                    "M04_portfolio_risk")
# Estrategias propias: capital, posiciones y salidas propias.
MODULOS_ESTRATEGIA = ("M02_standalone", "M03_standalone", "M05_pairs",
                      "M06_fundamental")

DEFECTO = {
    "institutional_extension": {
        "mode": OBSERVE,
        "base_strategy_preservation_required": True,
        "auto_live_promotion": False,
        "cross_strategy_netting": False,
        "new_strategy_capital_budget": None,
        "modules": {
            "M01_costs": {"enabled": True, "enforce": False},
            "M02_trend_context": {"enabled": True, "enforce": False},
            "M03_candidate_ranking": {"enabled": True, "enforce": False},
            "M04_portfolio_risk": {"enabled": True, "enforce": False},
            "M02_standalone": {"enabled": False},
            "M03_standalone": {"enabled": False},
            "M05_pairs": {"enabled": False},
            "M06_fundamental": {"enabled": False},
        },
    }
}

# Capacidades que cada estrategia condicional exige para ser EJECUTABLE.
# No se simulan como si ya existieran (seccion 15.2, "no se simulan como
# si esos requisitos ya existieran").
CAPACIDADES_EXIGIDAS = {
    "M05_pairs": ("cortos_ejecutables", "prestamo_de_valores",
                  "margen_modelado", "ejecucion_coordinada_dos_patas"),
    "M06_fundamental": ("fundamentales_point_in_time", "universo_historico"),
}


class ConfiguracionInvalida(ValueError):
    pass


@dataclass(frozen=True)
class Extension:
    mode: str = OBSERVE
    base_strategy_preservation_required: bool = True
    auto_live_promotion: bool = False
    cross_strategy_netting: bool = False
    new_strategy_capital_budget: float | None = None
    modules: dict = field(default_factory=dict)

    # ---- lectura ----

    def habilitado(self, modulo: str) -> bool:
        if self.mode == OFF:
            return False
        return bool(self.modules.get(modulo, {}).get("enabled", False))

    def exige(self, modulo: str) -> bool:
        """Si el modulo puede bloquear de verdad, no solo observar."""
        if self.mode != ENFORCE:
            return False
        cfg = self.modules.get(modulo, {})
        return bool(cfg.get("enabled", False) and cfg.get("enforce", False))

    @property
    def solo_observa(self) -> bool:
        return self.mode == OBSERVE

    def config_hash(self) -> str:
        crudo = json.dumps(self.a_dict(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(crudo.encode()).hexdigest()[:12]

    def a_dict(self) -> dict:
        return {
            "mode": self.mode,
            "base_strategy_preservation_required": self.base_strategy_preservation_required,
            "auto_live_promotion": self.auto_live_promotion,
            "cross_strategy_netting": self.cross_strategy_netting,
            "new_strategy_capital_budget": self.new_strategy_capital_budget,
            "modules": {k: dict(v) for k, v in sorted(self.modules.items())},
        }


def validar(bruto: dict, capacidades: dict | None = None) -> Extension:
    """Valida y normaliza. Lanza ConfiguracionInvalida si algo no cuadra."""
    capacidades = capacidades or {}

    if "institutional_extension" in bruto:
        bruto = bruto["institutional_extension"]

    modo = str(bruto.get("mode", OBSERVE)).upper()
    if modo not in MODOS_VALIDOS:
        raise ConfiguracionInvalida(f"mode desconocido: {modo}")

    if bruto.get("auto_live_promotion"):
        raise ConfiguracionInvalida(
            "auto_live_promotion no esta admitido en esta entrega: la "
            "promocion a live no es automatica"
        )

    if bruto.get("cross_strategy_netting"):
        raise ConfiguracionInvalida(
            "cross_strategy_netting desactivado: exigiria contabilidad de "
            "transferencias internas, asignacion de costes, reservas, riesgo "
            "y salidas. No basta sumar senales opuestas."
        )

    if not bruto.get("base_strategy_preservation_required", True):
        raise ConfiguracionInvalida(
            "base_strategy_preservation_required no puede desactivarse aqui; "
            "cambiar B1 exige una variante explicita y su propia medicion"
        )

    presupuesto = bruto.get("new_strategy_capital_budget", None)
    if presupuesto is not None:
        presupuesto = float(presupuesto)
        if not (0.0 < presupuesto <= 1.0):
            raise ConfiguracionInvalida(
                f"new_strategy_capital_budget fuera de (0,1]: {presupuesto}"
            )

    modulos_bruto = bruto.get("modules", {})
    modulos = {}
    conocidos = set(MODULOS_CONTEXTO) | set(MODULOS_ESTRATEGIA)
    for nombre, cfg in modulos_bruto.items():
        if nombre not in conocidos:
            raise ConfiguracionInvalida(f"modulo desconocido: {nombre}")
        if not isinstance(cfg, dict):
            raise ConfiguracionInvalida(f"{nombre}: se esperaba un objeto")
        entrada = {"enabled": bool(cfg.get("enabled", False))}
        if nombre in MODULOS_CONTEXTO:
            entrada["enforce"] = bool(cfg.get("enforce", False))
        elif "enforce" in cfg:
            raise ConfiguracionInvalida(
                f"{nombre} es una estrategia propia, no un filtro: no tiene "
                "enforce. Decide sobre SUS posiciones, no sobre entradas "
                "del nucleo."
            )
        modulos[nombre] = entrada

    for nombre in conocidos:
        modulos.setdefault(
            nombre,
            {"enabled": False, "enforce": False} if nombre in MODULOS_CONTEXTO
            else {"enabled": False},
        )

    # Una estrategia propia habilitada y operativa necesita presupuesto.
    if modo != OFF:
        activas = [n for n in MODULOS_ESTRATEGIA if modulos[n]["enabled"]]
        if activas and presupuesto is None:
            raise ConfiguracionInvalida(
                f"estrategias independientes habilitadas {activas} sin "
                "new_strategy_capital_budget. Un presupuesto no especificado "
                "es ausencia de autorizacion operativa, no el 100% de la "
                "cuenta."
            )
        # Y las condicionales necesitan capacidades reales.
        for nombre, exigidas in CAPACIDADES_EXIGIDAS.items():
            if not modulos[nombre]["enabled"]:
                continue
            faltan = [c for c in exigidas if not capacidades.get(c, False)]
            if faltan:
                raise ConfiguracionInvalida(
                    f"{nombre} habilitado sin capacidades: {faltan}. El "
                    "documento lo marca UNSUPPORTED; no se simula como si "
                    "esos requisitos existieran."
                )

    return Extension(
        mode=modo,
        base_strategy_preservation_required=True,
        auto_live_promotion=False,
        cross_strategy_netting=False,
        new_strategy_capital_budget=presupuesto,
        modules=modulos,
    )


def desde_entorno() -> Extension:
    """Lee INSTITUCIONAL_* del entorno. Por defecto: OBSERVE, nada exige."""
    bruto = json.loads(json.dumps(DEFECTO))["institutional_extension"]

    modo = os.getenv("INSTITUCIONAL_MODO", "").strip().upper()
    if modo:
        bruto["mode"] = modo

    presupuesto = os.getenv("INSTITUCIONAL_PRESUPUESTO", "").strip()
    if presupuesto:
        bruto["new_strategy_capital_budget"] = float(presupuesto)

    crudo = os.getenv("INSTITUCIONAL_MODULOS", "").strip()
    if crudo:
        bruto["modules"].update(json.loads(crudo))

    return validar(bruto, capacidades=capacidades_reales())


def capacidades_reales() -> dict[str, bool]:
    """Lo que esta cuenta puede hacer HOY. Todo False salvo prueba.

    No es una lista de deseos. Cada True tiene que corresponder a algo
    verificado: un broker que lo ofrece, un dataset que existe.
    """
    return {
        # Brian opera al contado, sin CFD: no hay cortos ejecutables.
        "cortos_ejecutables": False,
        "prestamo_de_valores": False,
        "margen_modelado": False,
        "ejecucion_coordinada_dos_patas": False,
        # No tenemos proveedor de fundamentales point-in-time.
        # yfinance da ratios ACTUALES, que no sirven para un backtest.
        "fundamentales_point_in_time": False,
        "universo_historico": False,
        # Lo que si tenemos.
        "cierres_diarios": True,
        "volumen": True,
        "ejecucion_en_papel": True,
    }
