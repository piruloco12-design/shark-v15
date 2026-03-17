import pandas as pd


def get_recent_returns(df, current_time, lookback=50):
    data = df.loc[:current_time]

    if len(data) < lookback + 1:
        return None

    recent = data["Close"].iloc[-(lookback + 1):].pct_change().dropna()

    if len(recent) < lookback:
        return None

    return recent


def calculate_pair_correlation(df1, df2, current_time, lookback=50):
    r1 = get_recent_returns(df1, current_time, lookback=lookback)
    r2 = get_recent_returns(df2, current_time, lookback=lookback)

    if r1 is None or r2 is None:
        return None

    aligned = pd.concat([r1, r2], axis=1).dropna()

    if len(aligned) < 20:
        return None

    corr = aligned.iloc[:, 0].corr(aligned.iloc[:, 1])
    return corr


def passes_correlation_filter(
    candidate_ticker,
    open_positions,
    data_dict,
    current_time,
    max_corr=0.80,
    lookback=50
):
    if not open_positions:
        return True

    candidate_df = data_dict[candidate_ticker]

    for pos in open_positions:
        open_ticker = pos["ticker"]
        open_df = data_dict[open_ticker]

        corr = calculate_pair_correlation(
            candidate_df,
            open_df,
            current_time=current_time,
            lookback=lookback
        )

        if corr is not None and abs(corr) >= max_corr:
            return False

    return True