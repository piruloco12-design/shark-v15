def select_best_assets(results, min_profit_factor=1.0):

    selected = []

    for ticker, data in results.items():

        pf = data["profit_factor"]

        if pf >= min_profit_factor:
            selected.append(ticker)

    return selected