from backtester import run_backtest
from asset_selector import select_best_assets
from portfolio_backtester import run_portfolio_backtest


def split_train_test(df, train_ratio=0.7):
    split_index = int(len(df) * train_ratio)

    train_df = df.iloc[:split_index].copy()
    test_df = df.iloc[split_index:].copy()

    return train_df, test_df


def run_walk_forward(
    data_dict,
    train_ratio=0.7,
    max_positions=3,
    use_rotation=True,
    rotation_lookback=50,
    rotation_top_n=3,
    use_correlation_filter=True,
    correlation_lookback=50,
    max_corr=0.80
):
    train_results = {}
    train_data = {}
    test_data = {}

    # 1. dividir cada activo en train/test
    for ticker, df in data_dict.items():
        train_df, test_df = split_train_test(df, train_ratio=train_ratio)

        train_data[ticker] = train_df
        test_data[ticker] = test_df

    # 2. backtest individual SOLO en train
    for ticker, train_df in train_data.items():
        result = run_backtest(train_df, max_positions=5)
        train_results[ticker] = result

    # 3. elegir mejores activos con train
    best_assets = select_best_assets(train_results, min_profit_factor=1.0)

    # 4. probar portfolio SOLO en test
    portfolio_test_results = run_portfolio_backtest(
        data_dict=test_data,
        selected_assets=best_assets,
        max_positions=max_positions,
        use_rotation=use_rotation,
        rotation_lookback=rotation_lookback,
        rotation_top_n=rotation_top_n,
        use_correlation_filter=use_correlation_filter,
        correlation_lookback=correlation_lookback,
        max_corr=max_corr
    )

    return {
        "train_results": train_results,
        "best_assets": best_assets,
        "portfolio_test_results": portfolio_test_results
    }