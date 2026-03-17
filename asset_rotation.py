def rank_assets_by_momentum(data_dict, current_time, lookback=50):
    rankings = []

    for ticker, df in data_dict.items():
        data = df.loc[:current_time]

        if len(data) < lookback:
            continue

        recent = data.iloc[-lookback:]
        first_close = float(recent["Close"].iloc[0])
        last_close = float(recent["Close"].iloc[-1])

        if first_close == 0:
            continue

        momentum = (last_close - first_close) / first_close

        rankings.append((ticker, momentum))

    rankings.sort(key=lambda x: x[1], reverse=True)

    return rankings


def select_top_assets_by_rotation(data_dict, current_time, top_n=3, lookback=50):
    rankings = rank_assets_by_momentum(
        data_dict=data_dict,
        current_time=current_time,
        lookback=lookback
    )

    selected = [ticker for ticker, score in rankings[:top_n]]

    return selected