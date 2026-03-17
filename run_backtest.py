from config import ASSETS, TIMEFRAME, PERIOD
from data_feed import get_data
from indicators import add_indicators
from walk_forward import run_walk_forward
from market_regime import detect_market_regime

print("\n=== SHARK V8 WALK-FORWARD + REGIME + ROTATION + CORRELATION ===\n")

data_dict = {}

# =========================================================
# 1. Cargar y preparar datos
# =========================================================
for ticker in ASSETS:
    print(f"Cargando datos de {ticker}...")

    try:
        df = get_data(ticker, TIMEFRAME, PERIOD)
        df = add_indicators(df)
        data_dict[ticker] = df

        current_regime = detect_market_regime(df)

        print(f"{ticker} | Filas: {len(df)} | Regime actual: {current_regime}")

    except Exception as e:
        print(f"Error cargando {ticker}: {e}")

    print("-" * 80)

# =========================================================
# 2. Walk-forward con rotación y correlación
# =========================================================
results = run_walk_forward(
    data_dict=data_dict,
    train_ratio=0.7,
    max_positions=3,
    use_rotation=True,
    rotation_lookback=50,
    rotation_top_n=3,
    use_correlation_filter=True,
    correlation_lookback=50,
    max_corr=0.80
)

# =========================================================
# 3. Mostrar resultados del TRAIN
# =========================================================
print("\n=== TRAIN RESULTS (IN-SAMPLE) ===\n")

for ticker, r in results["train_results"].items():
    print(
        f"{ticker} | "
        f"PF: {r['profit_factor']:.2f} | "
        f"Capital: {r['final_capital']:.2f} | "
        f"Trades: {r['total_trades']}"
    )

print("\n=== BEST ASSETS SELECTED FROM TRAIN ===\n")

if results["best_assets"]:
    for asset in results["best_assets"]:
        print(asset)
else:
    print("Ningún activo superó el filtro de train.")

# =========================================================
# 4. Mostrar resultados del TEST
# =========================================================
test_results = results["portfolio_test_results"]

print("\n=== TEST RESULTS (OUT-OF-SAMPLE PORTFOLIO) ===\n")

print(f"Activos seleccionados: {test_results['selected_assets']}")
print(f"Trades cerrados: {test_results['closed_trades']}")
print(f"Wins: {test_results['wins']}")
print(f"Losses: {test_results['losses']}")
print(f"Winrate: {test_results['winrate']:.2f}%")
print(f"Avg Trade: {test_results['avg_trade']:.2f}")
print(f"Profit Factor: {test_results['profit_factor']:.2f}")
print(f"Max Drawdown: {test_results['max_drawdown']:.2f}")
print(f"Capital Final Portfolio: {test_results['final_capital']:.2f}")
print(f"Avg Open Positions: {test_results['avg_open_positions']:.2f}")