"""
Las dos interfaces de la seccion 15.3, tal cual estan definidas alli.

Son dos cosas distintas y conviene no confundirlas nunca:

  ContextAssessment   un modulo opina sobre ENTRADAS NUEVAS del nucleo.
                      No genera compras. No vende nada. No toca el stop
                      de ninguna posicion abierta.

  StrategyProposal    una estrategia propia pide exposicion con SU
                      capital, SUS posiciones y SUS salidas. No es una
                      orden: tiene que pasar validacion causal,
                      capacidades, reservas, costes, riesgo y ejecucion.

Textual del documento, y es la trampa mas facil de caer:
NO_DATA, STALE y UNSUPPORTED no son senales de venta.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# Estados de un ContextAssessment (seccion 15.3)
READY = "READY"
NO_DATA = "NO_DATA"
STALE = "STALE"
UNSUPPORTED = "UNSUPPORTED"

ESTADOS_VALIDOS = (READY, NO_DATA, STALE, UNSUPPORTED)

# Estados que NO autorizan tratar la evaluacion como una opinion util.
# Se registran; en una variante que exija el modulo, bloquean entradas
# nuevas. Nunca cierran nada.
ESTADOS_SIN_DECISION = (NO_DATA, STALE, UNSUPPORTED)


class ContratoInvalido(ValueError):
    """Un contrato mal formado es un fallo de programacion, no un dato."""


@dataclass(frozen=True)
class ContextAssessment:
    """Opinion de un modulo de contexto sobre entradas nuevas del nucleo."""

    base_signal_id: str
    module_id: str
    config_hash: str
    dataset_version: str
    as_of: int                      # epoch segundos UTC del cierre usado
    valid_until: int                # hasta cuando vale esta evaluacion
    input_available_at_max: int     # el dato mas tardio que se uso
    status: str
    allow_new_entry: bool | None = None
    size_multiplier: float | None = None
    diagnostics: dict[str, Any] = field(default_factory=dict)
    reason_codes: tuple[str, ...] = ()

    def __post_init__(self):
        if self.status not in ESTADOS_VALIDOS:
            raise ContratoInvalido(f"status desconocido: {self.status}")

        # Causalidad: no se puede decidir con un dato publicado despues
        # del momento de la decision.
        if self.input_available_at_max > self.as_of:
            raise ContratoInvalido(
                "input_available_at_max posterior a as_of: la evaluacion "
                "usa informacion que aun no estaba disponible"
            )
        if self.valid_until < self.as_of:
            raise ContratoInvalido("valid_until anterior a as_of")

        if self.size_multiplier is not None:
            m = float(self.size_multiplier)
            if not (0.0 <= m <= 1.0):
                raise ContratoInvalido(
                    f"size_multiplier fuera de [0,1]: {m}. Un modulo de "
                    "contexto no puede aumentar posicion."
                )

        # Un estado sin decision no opina. Si opinara, el llamante
        # podria leer allow_new_entry=False y tratarlo como veto real,
        # que es exactamente lo que el documento prohibe.
        if self.status in ESTADOS_SIN_DECISION and self.allow_new_entry is not None:
            raise ContratoInvalido(
                f"{self.status} no puede fijar allow_new_entry; es ausencia "
                "de decision, no un veto"
            )

    @property
    def decide(self) -> bool:
        return self.status == READY

    def veta_entrada(self, exigido: bool) -> bool:
        """Si esta evaluacion bloquea una entrada nueva.

        exigido=False (observacion): nunca bloquea, solo se registra.
        exigido=True: bloquea si dice que no, y tambien si no puede decir
        nada. Un modulo que la variante exige y no tiene datos no es un
        permiso implicito.
        """
        if not exigido:
            return False
        if self.status in ESTADOS_SIN_DECISION:
            return True
        return self.allow_new_entry is False


@dataclass(frozen=True)
class StrategyProposal:
    """Peticion de exposicion de una estrategia propia. No es una orden."""

    proposal_id: str
    execution_key: tuple           # (cuenta, estrategia, instrumento, periodo, tipo)
    strategy_id: str
    config_hash: str
    dataset_version: str
    as_of: int
    valid_until: int
    input_available_at_max: int
    account_id: str
    portfolio_mode: str
    capital_envelope_id: str | None
    instrument_ids: tuple[str, ...]
    desired_exposure: dict[str, float]
    signal_descriptor: dict[str, Any]       # descriptor, NO retorno esperado
    forecast_horizon: str
    expected_return_model_id: str | None
    exit_policy_id: str
    position_ownership_id: str
    required_capabilities: tuple[str, ...] = ()
    reason_codes: tuple[str, ...] = ()

    def __post_init__(self):
        if self.input_available_at_max > self.as_of:
            raise ContratoInvalido("propuesta construida con datos del futuro")
        if self.valid_until < self.as_of:
            raise ContratoInvalido("valid_until anterior a as_of")
        if not self.instrument_ids:
            raise ContratoInvalido("propuesta sin instrumentos")
        if self.capital_envelope_id is None:
            # El documento: un presupuesto no especificado equivale a
            # ausencia de autorizacion operativa, no al 100% de la cuenta.
            raise ContratoInvalido(
                "propuesta sin capital_envelope_id: sin presupuesto "
                "explicito no hay autorizacion operativa"
            )
        for activo, peso in self.desired_exposure.items():
            if activo not in self.instrument_ids:
                raise ContratoInvalido(f"exposicion a {activo} no declarado")
            if not (0.0 <= float(peso) <= 1.0):
                raise ContratoInvalido(f"peso fuera de [0,1] en {activo}: {peso}")
        total = sum(float(p) for p in self.desired_exposure.values())
        if total > 1.0 + 1e-9:
            raise ContratoInvalido(
                f"exposicion total {total:.4f} superior al patrimonio"
            )

    def caducada(self, ahora: int) -> bool:
        return ahora > self.valid_until
