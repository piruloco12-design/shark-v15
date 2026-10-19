"""
Pruebas de la ampliacion institucional (seccion 15 del documento).

Tres bloques:

  A) Las 18 pruebas del archivo de referencia de Astra, reconstruidas
     aqui para que corran en CI. Son identicas a proposito: si alguien
     toca institucional/referencia.py, estas fallan.

  B) Contratos, configuracion, vista as-of y los tres modulos.

  C) Los casos I19-I30 del documento. Los que NO se pueden probar
     porque el modulo esta bloqueado por capacidades, o porque la
     infraestructura no existe todavia, se declaran NO CUBIERTO en
     voz alta. Un caso no cubierto contado como pasado seria peor que
     no tener la prueba.
"""
import os
import sys
import types
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

os.environ.setdefault("TELEGRAM_TOKEN", "")
sys.modules.setdefault("yfinance", types.ModuleType("yfinance"))

import pandas as pd

from institucional import contratos as C
from institucional import configuracion as CFG
from institucional import modulos as M
from institucional.referencia import (
    DataError, Fill, Point, asof_values, buffered_target, capped_inverse_vol,
    clears_cost_hurdle, estimated_trade_cost, implementation_shortfall,
    momentum_score, rank_positive, scale_weights_down, trend_signal,
)
from institucional.vista import cierres_mensuales, recortar_disponible

OK = 0
FALLOS = []
NO_CUBIERTO = []


def check(nombre, cond, detalle=""):
    global OK
    if cond:
        OK += 1
        print(f"  PASA   {nombre}")
    else:
        FALLOS.append(nombre)
        print(f"  FALLA  {nombre}  {detalle}")


def no_cubierto(nombre, motivo):
    NO_CUBIERTO.append((nombre, motivo))
    print(f"  N/C    {nombre}  -> {motivo}")


# OJO: una exponencial PERFECTA tiene retornos diarios constantes, asi
# que su desviacion muestral es cero y trend_signal la rechaza por
# "volatilidad degenerada". Eso esta BIEN: no se puede dimensionar una
# posicion dividiendo por cero. Las series de prueba llevan ruido
# determinista para parecerse a un activo de verdad.
def _ruido(i, amplitud=0.004):
    """Oscilacion reproducible, sin random: mismo resultado siempre."""
    return 1.0 + amplitud * ((i * 7919 % 101) / 100.0 - 0.5)


def serie(valores, inicio="2024-01-01", freq="B"):
    valores = list(valores)
    idx = pd.date_range(inicio, periods=len(valores), freq=freq, tz="UTC")
    s = pd.Series([float(v) for v in valores], index=idx)
    return pd.DataFrame({"Open": s, "High": s, "Low": s, "Close": s,
                         "Volume": 1e6}, index=idx)


# =====================================================================
print("\n=== A) Las 18 pruebas del archivo de referencia ===")
# =====================================================================

class Referencia(unittest.TestCase):
    def test_future_observations_do_not_change_past(self):
        past = [Point(1, 1, 100), Point(2, 2, 102)]
        expected = asof_values(past, [1, 2], 2)
        for future_price in (1.0, 1000000.0):
            self.assertEqual(expected, asof_values(
                past + [Point(3, 3, future_price)], [1, 2], 2))

    def test_late_publication_is_not_available(self):
        with self.assertRaises(DataError):
            asof_values([Point(1, 1, 100), Point(2, 3, 102)], [1, 2], 2)

    def test_missing_session_is_not_forward_filled(self):
        with self.assertRaises(DataError):
            asof_values([Point(1, 1, 100), Point(3, 3, 102)], [1, 2, 3], 3)

    def test_duplicate_and_invalid_calendar_are_rejected(self):
        for points, expected, now in (
            ([Point(1, 1, 100), Point(1, 1, 101)], [1], 1),
            ([Point(1, 1, 100)], [2, 1], 2),
            ([Point(1, 1, 100)], [1, 2], 1),
        ):
            with self.subTest(expected=expected, now=now):
                with self.assertRaises(DataError):
                    asof_values(points, expected, now)

    def test_trend_compares_cash_and_never_creates_short(self):
        cash = [100, 101, 102, 103, 105]
        up = trend_signal([100, 101, 100, 103, 110], cash, 4, 3)
        self.assertEqual(up.side, 1)
        self.assertAlmostEqual(up.trailing_excess_return, 0.05)
        below_cash = trend_signal([100, 101, 100, 101, 102], cash, 4, 3)
        self.assertEqual(below_cash.side, 0)

    def test_degenerate_vol_is_not_infinite_position(self):
        with self.assertRaises(DataError):
            trend_signal([100] * 5, [100] * 5, 4, 3)
        with self.assertRaises(DataError):
            capped_inverse_vol(["A"], {"A": 0}, 0.5, 0.5, 0.05)

    def test_momentum_endpoint_and_skip_are_exact(self):
        p = [100, 102, 104, 110, 500]
        self.assertAlmostEqual(momentum_score(p, 4, 1), 0.10)
        self.assertAlmostEqual(momentum_score(p[:-1] + [1], 4, 1), 0.10)

    def test_ranking_is_stable_and_excludes_nonpositive(self):
        self.assertEqual(rank_positive({"B": .2, "C": -.1, "A": .2, "D": 0}, 3),
                         ("A", "B"))

    def test_inverse_vol_respects_budget_and_leaves_cap_residual_cash(self):
        w = capped_inverse_vol(["A", "B"], {"A": .1, "B": .2}, .4, .2, .05)
        self.assertAlmostEqual(w["A"], .2)
        self.assertAlmostEqual(w["B"], .4 / 3)
        self.assertLess(sum(w.values()), .4)

    def test_vol_cap_never_increases_weights(self):
        w = {"A": .2, "B": .1}
        self.assertEqual(scale_weights_down(w, .05, .10), w)
        scaled = scale_weights_down(w, .20, .10)
        self.assertAlmostEqual(scaled["A"], .1)
        self.assertAlmostEqual(scaled["B"], .05)

    def test_band_uses_nearest_edge(self):
        self.assertAlmostEqual(buffered_target(.11, .10, .02), .11)
        self.assertAlmostEqual(buffered_target(.15, .10, .02), .12)
        self.assertAlmostEqual(buffered_target(.05, .10, .02), .08)

    def test_exit_and_forced_reduction_bypass_band(self):
        self.assertEqual(buffered_target(.01, 0, .02), 0)
        self.assertEqual(buffered_target(.15, .10, .02, forced_reduction=True), .10)
        with self.assertRaises(DataError):
            buffered_target(.1, .2, .02, forced_reduction=True)

    def test_cost_units_and_no_order_no_fee(self):
        cost = estimated_trade_cost(1000, 10, .5, .02, 1000000, 1)
        self.assertAlmostEqual(cost, 2.132455532033676)
        self.assertEqual(estimated_trade_cost(0, 10, .5, .02, 1000000, 1), 0)
        self.assertEqual(cost, estimated_trade_cost(-1000, 10, .5, .02, 1000000, 1))

    def test_cost_hurdle_is_strict(self):
        self.assertFalse(clears_cost_hurdle(3, 2, 1))
        self.assertTrue(clears_cost_hurdle(3.01, 2, 1))
        self.assertFalse(clears_cost_hurdle(-1, 0, 0))

    def test_shortfall_counts_unfilled_opportunity(self):
        r = implementation_shortfall(1, 10, 100, [Fill(6, 101, .2)], 102)
        self.assertAlmostEqual(r.execution_cost, 6.2)
        self.assertAlmostEqual(r.opportunity_cost, 8)
        self.assertAlmostEqual(r.total_cost, 14.2)
        self.assertAlmostEqual(r.total_bps, 142)
        self.assertAlmostEqual(r.fill_ratio, .6)

    def test_shortfall_sell_sign_and_full_fill(self):
        r = implementation_shortfall(-1, 10, 100, [Fill(10, 99, .5)], 80)
        self.assertAlmostEqual(r.total_cost, 10.5)
        self.assertEqual(r.opportunity_cost, 0)
        self.assertEqual(r.fill_ratio, 1)

    def test_shortfall_no_fill_is_not_free_good_execution(self):
        r = implementation_shortfall(1, 10, 100, [], 102)
        self.assertEqual(r.total_cost, 20)
        self.assertEqual(r.fill_ratio, 0)

    def test_overfill_and_nan_are_rejected(self):
        with self.assertRaises(DataError):
            implementation_shortfall(1, 10, 100, [Fill(11, 100, 0)], 100)
        with self.assertRaises(DataError):
            rank_positive({"A": float("nan")}, 1)
        with self.assertRaises(DataError):
            estimated_trade_cost(100, 1, None, .1, 10000, 1)


_res = unittest.TextTestRunner(verbosity=0).run(
    unittest.defaultTestLoader.loadTestsFromTestCase(Referencia))
check(f"las {_res.testsRun} pruebas de referencia pasan",
      _res.wasSuccessful() and _res.testsRun == 18,
      f"-> {_res.testsRun} corridas, {len(_res.failures)} fallos, "
      f"{len(_res.errors)} errores")


# =====================================================================
print("\n=== B) Contratos ===")
# =====================================================================

base = dict(base_signal_id="s1", module_id="M02_trend_context",
            config_hash="abc", dataset_version="v1",
            as_of=1000, valid_until=2000, input_available_at_max=1000)

try:
    C.ContextAssessment(**{**base, "input_available_at_max": 1001},
                        status=C.READY, allow_new_entry=True)
    check("rechaza evaluacion con dato posterior a la decision", False)
except C.ContratoInvalido:
    check("rechaza evaluacion con dato posterior a la decision", True)

try:
    C.ContextAssessment(**base, status=C.READY, allow_new_entry=True,
                        size_multiplier=1.5)
    check("size_multiplier no puede aumentar posicion", False)
except C.ContratoInvalido:
    check("size_multiplier no puede aumentar posicion", True)

try:
    C.ContextAssessment(**base, status=C.NO_DATA, allow_new_entry=False)
    check("NO_DATA no puede hacerse pasar por veto", False)
except C.ContratoInvalido:
    check("NO_DATA no puede hacerse pasar por veto", True)

sin_datos = C.ContextAssessment(**base, status=C.NO_DATA)
check("en observacion, NO_DATA no bloquea nada",
      sin_datos.veta_entrada(exigido=False) is False)
check("exigido, NO_DATA bloquea entradas nuevas (no es permiso)",
      sin_datos.veta_entrada(exigido=True) is True)

cash = C.ContextAssessment(**base, status=C.READY, allow_new_entry=False)
check("CASH en observacion no bloquea", cash.veta_entrada(exigido=False) is False)
check("CASH exigido si bloquea", cash.veta_entrada(exigido=True) is True)

prop = dict(proposal_id="p1",
            execution_key=("cta", "M03", "SPY", "2026-10", "ENTRADA"),
            strategy_id="M03_standalone", config_hash="h", dataset_version="v",
            as_of=1000, valid_until=2000, input_available_at_max=1000,
            account_id="cta", portfolio_mode="paper",
            capital_envelope_id="sobre-1", instrument_ids=("SPY", "QQQ"),
            desired_exposure={"SPY": 0.3, "QQQ": 0.2},
            signal_descriptor={"momentum_12_1": 0.18}, forecast_horizon="1M",
            expected_return_model_id=None, exit_policy_id="rebalanceo-mensual",
            position_ownership_id="M03_standalone")
p = C.StrategyProposal(**prop)
check("propuesta valida se construye", p.instrument_ids == ("SPY", "QQQ"))

for nombre, cambio in [
    ("propuesta sin presupuesto se rechaza", {"capital_envelope_id": None}),
    ("exposicion total > patrimonio se rechaza",
     {"desired_exposure": {"SPY": 0.7, "QQQ": 0.6}}),
    ("exposicion a instrumento no declarado se rechaza",
     {"desired_exposure": {"IWM": 0.2}}),
    ("propuesta con datos del futuro se rechaza",
     {"input_available_at_max": 1001}),
]:
    try:
        C.StrategyProposal(**{**prop, **cambio})
        check(nombre, False, "-> no lanzo")
    except C.ContratoInvalido:
        check(nombre, True)


print("\n=== B) Configuracion ===")

e = CFG.validar(CFG.DEFECTO, capacidades=CFG.capacidades_reales())
check("el defecto es OBSERVE", e.mode == CFG.OBSERVE)
check("en OBSERVE ningun modulo exige nada",
      not any(e.exige(m) for m in CFG.MODULOS_CONTEXTO))
check("ninguna estrategia propia viene habilitada",
      not any(e.habilitado(m) for m in CFG.MODULOS_ESTRATEGIA))
check("sin presupuesto por defecto", e.new_strategy_capital_budget is None)
check("el hash de configuracion es estable",
      e.config_hash() == CFG.validar(CFG.DEFECTO,
                                     CFG.capacidades_reales()).config_hash())

off = CFG.validar({**CFG.DEFECTO["institutional_extension"], "mode": "OFF"},
                  CFG.capacidades_reales())
check("en OFF no hay modulo habilitado",
      not any(off.habilitado(m) for m in
              list(CFG.MODULOS_CONTEXTO) + list(CFG.MODULOS_ESTRATEGIA)))

for nombre, bruto in [
    ("M05 sin cortos ejecutables",
     {"mode": "OBSERVE", "new_strategy_capital_budget": 0.1,
      "modules": {"M05_pairs": {"enabled": True}}}),
    ("M06 sin fundamentales point-in-time",
     {"mode": "OBSERVE", "new_strategy_capital_budget": 0.1,
      "modules": {"M06_fundamental": {"enabled": True}}}),
    ("estrategia propia sin presupuesto",
     {"mode": "OBSERVE", "modules": {"M03_standalone": {"enabled": True}}}),
    ("netting entre estrategias",
     {"mode": "OBSERVE", "cross_strategy_netting": True}),
    ("promocion automatica a live",
     {"mode": "OBSERVE", "auto_live_promotion": True}),
    ("desactivar la preservacion de B1",
     {"mode": "OBSERVE", "base_strategy_preservation_required": False}),
    ("enforce en una estrategia propia",
     {"mode": "OBSERVE", "new_strategy_capital_budget": 0.1,
      "modules": {"M03_standalone": {"enabled": True, "enforce": True}}}),
    ("modulo inventado",
     {"mode": "OBSERVE", "modules": {"M09_magia": {"enabled": True}}}),
    ("presupuesto mayor que la cuenta",
     {"mode": "OBSERVE", "new_strategy_capital_budget": 1.5,
      "modules": {"M03_standalone": {"enabled": True}}}),
    ("modo inventado", {"mode": "TURBO"}),
]:
    try:
        CFG.validar(bruto, capacidades=CFG.capacidades_reales())
        check(f"rechaza: {nombre}", False, "-> no lanzo")
    except CFG.ConfiguracionInvalida:
        check(f"rechaza: {nombre}", True)

caps = CFG.capacidades_reales()
check("las capacidades declaran que NO hay cortos ejecutables",
      caps["cortos_ejecutables"] is False)
check("ni prestamo de valores", caps["prestamo_de_valores"] is False)
check("ni fundamentales point-in-time",
      caps["fundamentales_point_in_time"] is False)


print("\n=== B) Vista as-of ===")

diaria = serie(range(100, 400))
try:
    recortar_disponible(diaria, pd.Timestamp("2024-03-01"), "1d")
    check("rechaza decision_time sin zona horaria", False)
except DataError:
    check("rechaza decision_time sin zona horaria", True)

sin_tz = diaria.copy()
sin_tz.index = sin_tz.index.tz_localize(None)
try:
    recortar_disponible(sin_tz, pd.Timestamp("2024-03-01", tz="UTC"), "1d")
    check("rechaza serie sin zona horaria", False)
except DataError:
    check("rechaza serie sin zona horaria", True)

try:
    recortar_disponible(diaria.iloc[::-1], pd.Timestamp("2024-06-01", tz="UTC"), "1d")
    check("rechaza indice desordenado", False)
except DataError:
    check("rechaza indice desordenado", True)

duplicada = pd.concat([diaria.iloc[:5], diaria.iloc[:5]]).sort_index()
try:
    recortar_disponible(duplicada, pd.Timestamp("2024-06-01", tz="UTC"), "1d")
    check("rechaza marcas duplicadas", False)
except DataError:
    check("rechaza marcas duplicadas", True)

hoy = diaria.index[50]
vista = recortar_disponible(diaria, hoy + pd.Timedelta(hours=12), "1d")
check("la vela del dia en curso NO es visible a media sesion",
      vista.index[-1] == diaria.index[49],
      f"-> {vista.index[-1]} vs {diaria.index[49]}")
vista = recortar_disponible(diaria, hoy + pd.Timedelta(days=1), "1d")
check("la vela de ayer SI es visible", vista.index[-1] == hoy)

antes = recortar_disponible(diaria.iloc[:60], diaria.index[55], "1d")
despues = recortar_disponible(diaria, diaria.index[55], "1d")
check("anadir velas futuras no cambia la vista pasada",
      len(antes) == len(despues)
      and float(antes["Close"].iloc[-1]) == float(despues["Close"].iloc[-1]))

mensual = cierres_mensuales(diaria)
check("cierres mensuales: uno por mes",
      len(mensual) == len(set((d.year, d.month) for d in diaria.index)),
      f"-> {len(mensual)}")
check("cierres mensuales conservan la zona horaria",
      str(mensual.index.tz) == "UTC")
check("cada cierre mensual es la ULTIMA sesion de su mes",
      all(d == max(x for x in diaria.index
                   if (x.year, x.month) == (d.year, d.month))
          for d in mensual.index))
sin_un_mes = diaria.loc[~((diaria.index.month == 3) & (diaria.index.year == 2024))]
check("un mes que falta no se inventa",
      not any(d.month == 3 and d.year == 2024
              for d in cierres_mensuales(sin_un_mes).index))


print("\n=== B) Series diarias SIN zona horaria (el caso real) ===")

# yfinance devuelve las velas DIARIAS con indice sin zona horaria, y
# las intradia con zona. _normalize_df no localiza nada. La vista as-of
# RECHAZA un indice sin zona, a proposito. Resultado: alimentados con
# series diarias reales, M02 y M03 habrian devuelto NO_DATA para
# siempre, en silencio, pareciendo que funcionaban.
import data_feed

_sin_zona = pd.DataFrame(
    {"Open": 1.0, "High": 1.0, "Low": 1.0, "Close": 1.0, "Volume": 1.0},
    index=pd.date_range("2020-01-01", periods=300, freq="B"))
check("una serie diaria de yfinance llega SIN zona horaria "
      "(esto es el punto de partida, no un fallo)",
      _sin_zona.index.tz is None)

_localizada = data_feed._localizar_utc(_sin_zona)
check("_localizar_utc le pone zona", str(_localizada.index.tz) == "UTC")
check("y no toca los valores",
      bool((_localizada["Close"] == 1.0).all())
      and len(_localizada) == len(_sin_zona))
check("y no desplaza las fechas",
      [d.date() for d in _localizada.index[:3]]
      == [d.date() for d in _sin_zona.index[:3]])

# Sin localizar, la vista la rechaza. Con localizar, la acepta.
try:
    recortar_disponible(_sin_zona, pd.Timestamp("2021-01-01", tz="UTC"), "1d")
    check("sin localizar, la vista as-of la rechaza", False, "-> la acepto")
except DataError:
    check("sin localizar, la vista as-of la rechaza", True)

_v = recortar_disponible(_localizada, pd.Timestamp("2021-01-01", tz="UTC"), "1d")
check("localizada, la vista as-of SI la acepta", len(_v) > 200, f"-> {len(_v)}")

# Y el modulo entero, de punta a punta, sobre series localizadas.
_tr = data_feed._localizar_utc(pd.DataFrame(
    {"Open": 1.0, "High": 1.0, "Low": 1.0, "Volume": 1.0,
     "Close": [100 * (1.0008 ** i) * _ruido(i) for i in range(400)]},
    index=pd.date_range("2024-01-01", periods=400, freq="B")))
_ef = data_feed._localizar_utc(pd.DataFrame(
    {"Open": 1.0, "High": 1.0, "Low": 1.0, "Volume": 1.0,
     "Close": [100 * (1.00008 ** i) * _ruido(i, 0.0002) for i in range(400)]},
    index=pd.date_range("2024-01-01", periods=400, freq="B")))
_ev = M.m02_contexto("DIARIO", _tr, _ef,
                     _tr.index[-1] + pd.Timedelta(days=1), "s1", "h",
                     signal="BUY")
check("M02 sobre series diarias localizadas devuelve READY, no NO_DATA",
      _ev.status == C.READY, f"-> {_ev.status} {_ev.reason_codes}")


print("\n=== B) M02 contexto ===")

subida = serie([100 * (1.0008 ** i) * _ruido(i) for i in range(400)])
efectivo = serie([100 * (1.00008 ** i) * _ruido(i, 0.0002)
                  for i in range(400)])
lateral = serie([100 + (i % 7) for i in range(400)])
decision = subida.index[-1] + pd.Timedelta(days=1)
cfg_hash = "test"

a = M.m02_contexto("SUBE", subida, efectivo, decision, "s1", cfg_hash)
check("activo en tendencia por encima del efectivo -> LONG",
      a.status == C.READY and a.allow_new_entry is True,
      f"-> {a.status} {a.reason_codes}")
b = M.m02_contexto("PLANO", lateral, efectivo, decision, "s1", cfg_hash)
check("activo plano por debajo del efectivo -> CASH",
      b.status == C.READY and b.allow_new_entry is False,
      f"-> {b.status} {b.reason_codes}")
check("M02 nunca aumenta tamano", a.size_multiplier is None)
check("M02 declara la referencia de efectivo que uso",
      a.diagnostics["referencia_efectivo"] == M.TICKER_EFECTIVO)

corta = serie([(100 + i) * _ruido(i) for i in range(100)])
c = M.m02_contexto("CORTA", corta, efectivo.iloc[:100], decision, "s1", cfg_hash)
check("historico insuficiente -> NO_DATA, no una opinion",
      c.status == C.NO_DATA and c.allow_new_entry is None, f"-> {c.status}")

plana = serie([100.0] * 400)
d = M.m02_contexto("PLANISIMO", plana, plana, decision, "s1", cfg_hash)
check("volatilidad degenerada -> NO_DATA, no posicion infinita",
      d.status == C.NO_DATA, f"-> {d.status} {d.reason_codes}")

a_media = M.m02_contexto("SUBE", subida, efectivo,
                         subida.index[-1] + pd.Timedelta(hours=6), "s1", cfg_hash)
check("a media sesion M02 usa el cierre ANTERIOR",
      a_media.diagnostics["cierre_usado"] == str(subida.index[-2].date()),
      f"-> {a_media.diagnostics.get('cierre_usado')} vs {subida.index[-2].date()}")


print("\n=== B) M02/M03 y la direccion de la senal ===")

# El documento (15.5): "Para estrategias cortas no reutilizar el
# significado de LONG/CASH; hace falta un diseno especifico."
# Un activo que CAE da CASH. Aplicar ese CASH a un SELL vetaria justo
# la operacion que la tendencia favorece: el signo se invierte.
for direccion in ("SELL", "sell", "SHORT"):
    ev = M.m02_contexto("PLANO", lateral, efectivo, decision, "s1", cfg_hash,
                        signal=direccion)
    check(f"M02 sobre una senal {direccion} es UNSUPPORTED, no un veto",
          ev.status == C.UNSUPPORTED and ev.allow_new_entry is None,
          f"-> {ev.status} / {ev.allow_new_entry}")

ev_buy = M.m02_contexto("SUBE", subida, efectivo, decision, "s1", cfg_hash,
                        signal="BUY")
check("M02 sobre BUY si opina", ev_buy.status == C.READY)
ev_sin = M.m02_contexto("SUBE", subida, efectivo, decision, "s1", cfg_hash)
check("sin direccion M02 se comporta como antes (compatible)",
      ev_sin.status == C.READY)


print("\n=== B) M03 ranking ===")

series = {
    "FUERTE": serie([100 * (1.002 ** i) * _ruido(i) for i in range(400)]),
    "MEDIO": serie([100 * (1.0005 ** i) * _ruido(i) for i in range(400)]),
    "FLOJO": serie([100 * (0.999 ** i) * _ruido(i) for i in range(400)]),
    "CORTO": serie([100 + i for i in range(50)]),
}
r = M.m03_ranking(series, decision, k=2)
check("ranking ordena por score descendente",
      r.seleccionados == ("FUERTE", "MEDIO"), f"-> {r.seleccionados}")
check("un activo con score negativo no entra nunca",
      "FLOJO" not in r.seleccionados and r.scores["FLOJO"] < 0)
check("un activo sin historico suficiente queda excluido, no a cero",
      "CORTO" in r.excluidos and "CORTO" not in r.scores)
check("K limita la seleccion", len(r.seleccionados) == 2)

ctx = M.m03_contexto("FUERTE", r, "s1", cfg_hash, decision)
check("el primero del ranking permite entrada",
      ctx.status == C.READY and ctx.allow_new_entry is True
      and ctx.diagnostics["puesto"] == 1)
ctx_fuera = M.m03_contexto("FLOJO", r, "s1", cfg_hash, decision)
check("fuera de seleccion: READY y allow_new_entry False",
      ctx_fuera.status == C.READY and ctx_fuera.allow_new_entry is False)
ctx_excl = M.m03_contexto("CORTO", r, "s1", cfg_hash, decision)
check("excluido por datos: NO_DATA, no un veto",
      ctx_excl.status == C.NO_DATA and ctx_excl.allow_new_entry is None)
check("activo que el ranking no vio: NO_DATA",
      M.m03_contexto("NO_EXISTE", r, "s1", cfg_hash, decision).status == C.NO_DATA)
check("el ranking no inventa candidatos",
      set(r.scores) | set(r.excluidos) == set(series))

ev_sell = M.m03_contexto("FUERTE", r, "s1", cfg_hash, decision, signal="SELL")
check("M03 sobre una senal SELL es UNSUPPORTED (el 12-1 ordena COMPRAS)",
      ev_sell.status == C.UNSUPPORTED and ev_sell.allow_new_entry is None,
      f"-> {ev_sell.status}")


print("\n=== B) Zona horaria del mercado ===")

import zona_mercado

check("la zona del mercado resuelve en este sistema",
      zona_mercado.zona() in zona_mercado.CANDIDATAS,
      f"-> {zona_mercado.zona()}")
check("el canonico America/New_York va PRIMERO en la lista",
      zona_mercado.CANDIDATAS[0] == "America/New_York",
      f"-> {zona_mercado.CANDIDATAS}")

# Las dos zonas son la MISMA: si las dos resuelven, los husos y las
# reglas de horario de verano tienen que coincidir exactamente. Si no
# coincidieran, cambiar de nombre si cambiaria decisiones.
try:
    from zoneinfo import ZoneInfo
    canon, alias = ZoneInfo("America/New_York"), ZoneInfo("US/Eastern")
    iguales = all(
        pd.Timestamp(f"{a}-{m:02d}-15 1{h}:00").tz_localize(canon).utcoffset()
        == pd.Timestamp(f"{a}-{m:02d}-15 1{h}:00").tz_localize(alias).utcoffset()
        for a in (2024, 2025, 2026) for m in (1, 3, 6, 7, 11, 12) for h in (0, 5)
    )
    check("America/New_York y US/Eastern dan el MISMO huso siempre "
          "(cambiar de nombre no cambia decisiones)", iguales)
except Exception as _err_zona:
    print(f"  N/C    comparacion de husos -> el alias US/Eastern no existe "
          f"en este sistema ({type(_err_zona).__name__})")
    NO_CUBIERTO.append(("comparacion de husos canonico vs alias",
                        "el alias no esta en esta base de zonas"))

# Si no hay NINGUNA zona, tiene que decir que falta tzdata, no fallar
# en silencio dejando el filtro de sesion bloqueando todo.
_candidatas = zona_mercado.CANDIDATAS
try:
    zona_mercado.CANDIDATAS = ("Zona/Inventada",)
    zona_mercado._CACHE = None
    try:
        zona_mercado.resolver()
        check("sin zonas disponibles lanza un error que dice que falta tzdata",
              False, "-> no lanzo")
    except zona_mercado.ZonaNoDisponible as _err_tz:
        check("sin zonas disponibles lanza un error que dice que falta tzdata",
              "tzdata" in str(_err_tz))
finally:
    zona_mercado.CANDIDATAS = _candidatas
    zona_mercado._CACHE = None


print("\n=== B) M01 coste ===")

m01 = M.m01_coste("SPY", nominal=1000.0, volumen_moneda=5e9,
                  vol_horizonte=0.01, base_signal_id="s1",
                  config_hash=cfg_hash, decision_time=decision,
                  dataset_version="v1")
check("sin estimador fuera de muestra, M01 es UNSUPPORTED",
      m01.status == C.UNSUPPORTED and m01.allow_new_entry is None,
      f"-> {m01.status}")
check("M01 declara que no esta calibrado con fills propios",
      m01.diagnostics["calibrado_con_fills_propios"] is False)
# Tolerancia 2e-4, no 1e-9: los dos valores se redondean a 4 decimales
# por separado, asi que round(2x,4) y 2*round(x,4) pueden diferir en
# 1e-4. No es un error de calculo.
check("el coste de ida y vuelta es el doble de una pata",
      abs(m01.diagnostics["coste_ida_vuelta"]
          - 2 * m01.diagnostics["coste_una_pata"]) < 2e-4,
      f"-> {m01.diagnostics['coste_una_pata']} vs "
      f"{m01.diagnostics['coste_ida_vuelta']}")
check("M01 declara que asume que salir cuesta lo mismo que entrar",
      m01.diagnostics["coste_salida_asumido_igual_a_entrada"] is True)
check("8 bps por pata sobre 1000: ida y vuelta entre 1.6 y 1.7",
      1.6 <= m01.diagnostics["coste_ida_vuelta"] < 1.7,
      f"-> {m01.diagnostics['coste_ida_vuelta']}")

con_estimador = M.m01_coste("SPY", 1000.0, 5e9, 0.01, "s1", cfg_hash,
                            decision, "v1", ganancia_bruta_esperada=50.0,
                            modelo_retorno_id="walkforward-2026-10")
check("con estimador y ganancia alta, pasa el umbral",
      con_estimador.status == C.READY and con_estimador.allow_new_entry is True)
no_pasa = M.m01_coste("SPY", 1000.0, 5e9, 0.01, "s1", cfg_hash, decision, "v1",
                      ganancia_bruta_esperada=0.5,
                      modelo_retorno_id="walkforward-2026-10")
check("con ganancia por debajo de coste+margen, no pasa",
      no_pasa.allow_new_entry is False)
check("el umbral exige margen, no solo cubrir coste",
      M.m01_coste("SPY", 1000.0, 5e9, 0.01, "s1", cfg_hash, decision, "v1",
                  ganancia_bruta_esperada=m01.diagnostics["coste_ida_vuelta"] * 1.2,
                  modelo_retorno_id="m").allow_new_entry is False)


# =====================================================================
print("\n=== C) Casos I19-I30 del documento ===")
# =====================================================================

clave = ("cta", "M03_standalone", "SPY", "2026-10", "ENTRADA")
p1 = C.StrategyProposal(**{**prop, "proposal_id": "p-v1", "execution_key": clave})
p2 = C.StrategyProposal(**{**prop, "proposal_id": "p-v2", "execution_key": clave,
                           "config_hash": "otro-hash"})
check("I19 dos versiones del mismo cierre comparten clave de ejecucion",
      p1.execution_key == p2.execution_key and p1.proposal_id != p2.proposal_id)

cash_m02 = M.m02_contexto("PLANO", lateral, efectivo, decision, "s1", cfg_hash)
check("I20 CASH es un veto de ENTRADA, no una venta",
      cash_m02.allow_new_entry is False and not hasattr(cash_m02, "cerrar"))
check("I20 en observacion ni siquiera veta",
      cash_m02.veta_entrada(exigido=False) is False)

check("I21 objetivo cero cierra del todo, la banda no deja residuo",
      buffered_target(0.01, 0, 0.02) == 0 and buffered_target(0.19, 0, 0.05) == 0)

sf = implementation_shortfall(1, 10, 100, [], 102)
check("I22 no ejecutar no es ejecucion gratuita",
      sf.total_cost == 20 and sf.fill_ratio == 0)

manana = pd.Timestamp(series["FUERTE"].index[-1].date(), tz="UTC") \
    + pd.Timedelta(hours=10)
r_manana = M.m03_ranking(series, manana, k=2)
r_cierre = M.m03_ranking(series, manana + pd.Timedelta(days=1), k=2)
check("I23 el ranking de la manana no ve el cierre de ese dia",
      r_manana.as_of < r_cierre.as_of,
      f"-> manana {r_manana.as_of} vs cierre {r_cierre.as_of}")

check("I25 las estrategias propias vienen desactivadas, no comparten libro",
      not any(e.habilitado(m) for m in CFG.MODULOS_ESTRATEGIA))

check("I30 desactivar un modulo no expone ningun metodo de cierre",
      not any(hasattr(off, n) for n in ("cerrar", "liquidar", "close_all")))

no_cubierto("I24 reserva atomica de efectivo entre dos estrategias",
            "no hay libro multiestrategia: las propias estan desactivadas")
no_cubierto("I26 recalcular parametros de un par abierto",
            "M05 bloqueado: no hay cortos ejecutables en cuenta al contado")
no_cubierto("I27 una sola pata ejecutada o prestamo retirado",
            "M05 bloqueado por capacidades")
no_cubierto("I28 balance revisado meses despues",
            "M06 bloqueado: no hay fundamentales point-in-time")
no_cubierto("I29 mas Sharpe pero menos dinero",
            "es requisito del INFORME del experimento, no del codigo")


print("\n" + "=" * 62)
print(f"RESULTADO: {OK} pruebas pasadas, {len(FALLOS)} fallos, "
      f"{len(NO_CUBIERTO)} casos NO cubiertos")
for f in FALLOS:
    print(f"  FALLA      - {f}")
for n, motivo in NO_CUBIERTO:
    print(f"  NO CUBIERTO- {n}: {motivo}")
print("=" * 62)

sys.exit(1 if FALLOS else 0)
