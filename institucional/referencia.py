"""
Funciones matematicas puras de la ampliacion institucional (seccion 15).

Portado de SHARK_Referencia_Institucional.py (version de referencia
2026-10-19.institutional.1), entregado por Astra. Cambios respecto al
archivo original, todos deliberados:

  - se elimina el bloque _self_test y el __main__: el documento pide
    no importar el archivo de pruebas al proceso de ejecucion. Las 18
    pruebas estan en tests/test_institucional.py y corren en CI.
  - nada mas. Las funciones son identicas, a proposito: si se tocan,
    las pruebas de referencia dejan de verificar lo que verificaban.

Lo que este archivo NO es, textual del documento: no incluye
backtester, planificador, ledger, politica de prestamo, modelos
entrenados ni datos de mercado. No conecta con un broker. Los
parametros por defecto son hipotesis iniciales, no optimos.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
import statistics
from typing import Iterable, Mapping, Sequence

REFERENCE_VERSION = "2026-10-19.institutional.1"


class DataError(ValueError):
    """Entrada no apta para decidir; el adaptador debe registrar NO_DECISION."""


def _finite(value: float, name: str) -> float:
    if isinstance(value, bool):
        raise DataError(f"{name}: booleano no admitido")
    try:
        result = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise DataError(f"{name}: numero requerido") from exc
    if not math.isfinite(result):
        raise DataError(f"{name}: numero no finito")
    return result


def _nonnegative(value: float, name: str) -> float:
    result = _finite(value, name)
    if result < 0:
        raise DataError(f"{name}: negativo")
    return result


def _positive(value: float, name: str) -> float:
    result = _finite(value, name)
    if result <= 0:
        raise DataError(f"{name}: debe ser positivo")
    return result


def _integer(value: int, name: str, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise DataError(f"{name}: entero >= {minimum} requerido")
    return value


def _weight(value: float, name: str) -> float:
    result = _nonnegative(value, name)
    if result > 1:
        raise DataError(f"{name}: peso mayor que uno")
    return result


@dataclass(frozen=True)
class Point:
    event_time: int  # UTC, unidad consistente definida por el adaptador
    available_at: int
    value: float  # nivel de indice total-return, no precio de ejecucion


def asof_values(
    points: Iterable[Point], expected_events: Sequence[int], now: int
) -> tuple[float, ...]:
    """Serie completa sobre un calendario explicito, visible en now.

    Una sola version por evento. Resolver revisiones con un proveedor PIT antes
    de llamar. No rellena huecos ni considera datos publicados despues de now.
    Las sesiones esperadas deben provenir del calendario real del instrumento.
    """
    _integer(now, "now")
    expected = tuple(expected_events)
    if not expected:
        raise DataError("calendario vacio")
    for t in expected:
        _integer(t, "event_time")
    if any(a >= b for a, b in zip(expected, expected[1:])):
        raise DataError("calendario duplicado o desordenado")
    if expected[-1] > now:
        raise DataError("calendario incluye futuro")
    needed = set(expected)
    visible: dict[int, float] = {}
    for point in points:
        _integer(point.event_time, "event_time")
        _integer(point.available_at, "available_at")
        if point.available_at < point.event_time:
            raise DataError("un cierre no puede publicarse antes de ocurrir")
        if point.event_time not in needed or point.available_at > now:
            continue
        if point.event_time in visible:
            raise DataError("evento duplicado; resolver version PIT")
        visible[point.event_time] = _positive(point.value, "nivel")
    missing = needed - visible.keys()
    if missing:
        raise DataError(f"faltan {len(missing)} eventos visibles")
    return tuple(visible[t] for t in expected)


def _levels(values: Sequence[float], minimum: int) -> tuple[float, ...]:
    result = tuple(_positive(x, "nivel") for x in values)
    if len(result) < minimum:
        raise DataError(f"se requieren al menos {minimum} niveles")
    return result


def annualized_vol(
    levels: Sequence[float], window: int = 63, periods_per_year: int = 252
) -> float:
    """Desviacion muestral de window retornos simples diarios, anualizada."""
    _integer(window, "window", 2)
    _integer(periods_per_year, "periods_per_year", 1)
    p = _levels(levels, window + 1)[-(window + 1):]
    returns = [_finite(b / a - 1, "retorno") for a, b in zip(p, p[1:])]
    return _finite(statistics.stdev(returns) * math.sqrt(periods_per_year), "vol")


@dataclass(frozen=True)
class TrendSignal:
    side: int  # 1 = candidato largo; 0 = efectivo en ESTA estrategia
    trailing_excess_return: float  # descriptor historico, NO retorno esperado
    annual_vol: float


def trend_signal(
    asset_levels: Sequence[float],
    cash_levels: Sequence[float],
    lookback: int = 252,
    vol_window: int = 63,
    periods_per_year: int = 252,
) -> TrendSignal:
    """Tendencia larga/efectivo. Ambas series deben estar alineadas as-of.

    El adaptador decide calendario mensual y ejecuta despues de la observacion.
    Como filtro de Shark, side=0 veta entradas; no cierra posiciones de Shark.
    """
    _integer(lookback, "lookback", 1)
    _integer(vol_window, "vol_window", 2)
    if len(asset_levels) != len(cash_levels):
        raise DataError("series no alineadas")
    a = _levels(asset_levels, max(lookback, vol_window) + 1)
    c = _levels(cash_levels, len(a))
    excess = _finite(a[-1] / a[-1-lookback] - c[-1] / c[-1-lookback], "exceso")
    vol = annualized_vol(a, vol_window, periods_per_year)
    if vol <= 1e-12:
        raise DataError("volatilidad degenerada; revisar datos")
    return TrendSignal(int(excess > 0), excess, vol)


def momentum_score(
    levels: Sequence[float], lookback: int = 252, skip: int = 21
) -> float:
    """Retorno desde t-lookback hasta t-skip; NO prevision de rentabilidad."""
    _integer(lookback, "lookback", 1)
    _integer(skip, "skip", 0)
    if skip >= lookback:
        raise DataError("skip debe ser menor que lookback")
    p = _levels(levels, lookback + 1)
    return _finite(p[-1-skip] / p[-1-lookback] - 1, "momentum")


def rank_positive(scores: Mapping[str, float], count: int) -> tuple[str, ...]:
    """Top-k positivo; empate por identificador estable, no orden de llegada."""
    _integer(count, "count", 1)
    candidates = []
    for asset, score in scores.items():
        if not isinstance(asset, str) or not asset:
            raise DataError("identificador invalido")
        value = _finite(score, "score")
        if value > 0:
            candidates.append((asset, value))
    return tuple(x[0] for x in sorted(candidates, key=lambda x: (-x[1], x[0]))[:count])


def capped_inverse_vol(
    selected: Sequence[str],
    annual_vols: Mapping[str, float],
    budget: float,
    per_asset_cap: float,
    vol_floor: float,
) -> dict[str, float]:
    """Pesos sobre patrimonio total, sin apalancar ni redistribuir sobrantes.

    budget procede de una asignacion externa aprobada y reservada. No se suma
    automaticamente al capital ya utilizado por Shark. No es risk parity.
    """
    budget = _weight(budget, "budget")
    cap = _weight(per_asset_cap, "per_asset_cap")
    floor = _positive(vol_floor, "vol_floor")
    if len(set(selected)) != len(selected):
        raise DataError("activo duplicado")
    inverse = {}
    for asset in selected:
        if asset not in annual_vols:
            raise DataError("falta volatilidad")
        inverse[asset] = 1 / max(_positive(annual_vols[asset], "vol"), floor)
    denominator = sum(inverse.values())
    if not inverse:
        return {}
    return {a: min(cap, budget * v / denominator) for a, v in inverse.items()}


def scale_weights_down(
    weights: Mapping[str, float], forecast_vol: float, vol_cap: float
) -> dict[str, float]:
    """Reduccion uniforme de una cartera long-only; no optimiza correlaciones."""
    values = {a: _weight(w, "peso") for a, w in weights.items()}
    if sum(values.values()) > 1 + 1e-12:
        raise DataError("exposicion superior al patrimonio")
    sigma = _positive(forecast_vol, "forecast_vol")
    cap = _positive(vol_cap, "vol_cap")
    scale = min(1.0, cap / sigma)
    return {a: w * scale for a, w in values.items()}


def buffered_target(
    current: float, desired: float, half_band: float, *, forced_reduction: bool = False
) -> float:
    """Banda en pesos absolutos, aplicable solo a rebalanceos del modulo nuevo.

    Si sale de la banda, mueve al borde mas cercano. Una salida deseada a cero
    o una reduccion obligatoria no se aplaza por la banda. El caller valida
    limites agregados y lote; esto no reemplaza el gestor de riesgo.
    """
    current, desired = _weight(current, "current"), _weight(desired, "desired")
    band = _weight(half_band, "half_band")
    if forced_reduction and desired > current:
        raise DataError("una reduccion forzada no puede aumentar posicion")
    if forced_reduction or desired == 0:
        return desired
    lower, upper = max(0.0, desired - band), min(1.0, desired + band)
    return min(max(current, lower), upper)


def estimated_trade_cost(
    notional: float, linear_bps: float, fixed_fee: float,
    sigma_horizon: float, volume_notional_horizon: float, impact_coefficient: float,
) -> float:
    """Coste monetario modelado de UN lado, relativo al mid de decision.

    x, volumen y coste usan la misma moneda; sigma y volumen el mismo horizonte.
    linear_bps incluye los componentes proporcionales sin duplicacion. No usar
    este coste para descontar otra vez fricciones ya presentes en fills reales.
    Coeficientes explicitos: no se presupone que comisiones desconocidas sean 0.
    """
    x = abs(_finite(notional, "notional"))
    a = _nonnegative(linear_bps, "linear_bps") / 10000
    fee = _nonnegative(fixed_fee, "fixed_fee")
    sigma = _nonnegative(sigma_horizon, "sigma_horizon")
    volume = _positive(volume_notional_horizon, "volume_notional_horizon")
    impact = _nonnegative(impact_coefficient, "impact_coefficient")
    if x == 0:
        return 0.0
    return _finite(fee + a*x + impact*sigma*x*math.sqrt(x/volume), "coste")


def clears_cost_hurdle(
    expected_gross_gain: float, full_cost: float, uncertainty_margin: float
) -> bool:
    """Gate experimental para NUEVAS entradas; magnitudes monetarias iguales.

    expected_gross_gain debe venir de una estimacion fuera de muestra. No acepta
    un score de momentum como sustituto. Nunca usar para bloquear una salida.
    """
    gain = _finite(expected_gross_gain, "expected_gross_gain")
    cost = _nonnegative(full_cost, "full_cost")
    margin = _nonnegative(uncertainty_margin, "uncertainty_margin")
    return gain > cost + margin


@dataclass(frozen=True)
class Fill:
    quantity: float
    price: float
    fee: float


@dataclass(frozen=True)
class Shortfall:
    execution_cost: float
    opportunity_cost: float
    total_cost: float
    total_bps: float
    fill_ratio: float


def implementation_shortfall(
    side: int, requested: float, decision_mid: float,
    fills: Sequence[Fill], deadline_mid: float,
) -> Shortfall:
    """Coste de ejecucion + oportunidad al vencimiento fijo de una intencion.

    side=+1 compra, -1 venta. Precios ya incorporan spread/slippage. No anadirlos
    otra vez. Los fills deben estar deduplicados y pertenecer a esta intencion.
    No es P&L de la estrategia y no va al libro de beneficios como gasto extra.
    """
    if isinstance(side, bool) or side not in (-1, 1):
        raise DataError("side invalido")
    quantity = _positive(requested, "requested")
    arrival = _positive(decision_mid, "decision_mid")
    end = _positive(deadline_mid, "deadline_mid")
    done = 0.0
    execution = 0.0
    for fill in fills:
        q = _positive(fill.quantity, "fill.quantity")
        p = _positive(fill.price, "fill.price")
        fee = _nonnegative(fill.fee, "fill.fee")
        done += q
        execution += side*q*(p-arrival) + fee
    if done > quantity + 1e-12 * max(1.0, quantity):
        raise DataError("fills superan cantidad solicitada")
    remaining = max(0.0, quantity-done)
    opportunity = side*remaining*(end-arrival)
    total = _finite(execution + opportunity, "shortfall")
    return Shortfall(execution, opportunity, total, total/(quantity*arrival)*10000,
                     min(1.0, done/quantity))
