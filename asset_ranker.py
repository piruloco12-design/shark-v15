import sqlite3
import pandas as pd
from config import DATABASE_NAME


def load_trade_history():
    conn = sqlite3.connect(DATABASE_NAME)

    query = """
    SELECT ticker, signal, pnl
    FROM paper_trades
    WHERE status = 'CLOSED'
    """

    df = pd.read_sql_query(query, conn)
    conn.close()

    return df


def calculate_asset_scores():
    df = load_trade_history()

    if df.empty:
        return {}

    grouped = df.groupby("ticker")
    scores = {}

    for ticker, g in grouped:
        trades = len(g)

        wins = int((g["pnl"] > 0).sum())
        winrate = wins / trades if trades > 0 else 0.0

        gross_profit = g.loc[g["pnl"] > 0, "pnl"].sum()
        gross_loss = abs(g.loc[g["pnl"] <= 0, "pnl"].sum())

        if gross_loss > 0:
            profit_factor = gross_profit / gross_loss
        else:
            profit_factor = 0.0

        pnl_total = float(g["pnl"].sum())

        # Score balanceado
        # winrate pesa bastante, PF pesa bastante, pnl total aporta menos
        score = (
            (winrate * 100 * 0.4) +
            (profit_factor * 20 * 0.4) +
            (pnl_total * 0.2)
        )

        scores[ticker] = {
            "score": round(score, 2),
            "trades": trades,
            "winrate": round(winrate * 100, 2),
            "profit_factor": round(profit_factor, 2),
            "pnl_total": round(pnl_total, 2)
        }

    return scores


def get_ranked_assets(default_assets):
    scores = calculate_asset_scores()

    if not scores:
        return list(default_assets)

    ranked = sorted(
        scores.items(),
        key=lambda x: x[1]["score"],
        reverse=True
    )

    ranked_assets = [item[0] for item in ranked]

    # añadir activos sin historial al final
    for asset in default_assets:
        if asset not in ranked_assets:
            ranked_assets.append(asset)

    return ranked_assets


def get_asset_ranking_table(default_assets):
    scores = calculate_asset_scores()

    rows = []

    for asset in default_assets:
        if asset in scores:
            rows.append({
                "ticker": asset,
                "score": scores[asset]["score"],
                "trades": scores[asset]["trades"],
                "winrate": scores[asset]["winrate"],
                "profit_factor": scores[asset]["profit_factor"],
                "pnl_total": scores[asset]["pnl_total"]
            })
        else:
            rows.append({
                "ticker": asset,
                "score": 0.0,
                "trades": 0,
                "winrate": 0.0,
                "profit_factor": 0.0,
                "pnl_total": 0.0
            })

    ranking_df = pd.DataFrame(rows)
    ranking_df = ranking_df.sort_values("score", ascending=False).reset_index(drop=True)

    return ranking_df