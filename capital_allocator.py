from asset_ranker import calculate_asset_scores


def get_capital_allocation_map(default_assets):
    """
    Devuelve un mapa de asignación relativa por activo.
    Si no hay historial, reparte neutro.
    """

    scores = calculate_asset_scores()

    # Sin historial suficiente -> reparto neutro
    if not scores:
        equal_weight = 1.0 / len(default_assets) if default_assets else 0.0
        return {
            asset: {
                "weight": equal_weight,
                "score": 0.0,
                "reason": "Sin historial, asignación neutra"
            }
            for asset in default_assets
        }

    raw_strength = {}

    for asset in default_assets:
        if asset in scores:
            score = float(scores[asset]["score"])
            trades = int(scores[asset]["trades"])

            # pocos trades => menos confianza
            if trades < 5:
                adjusted = max(score, 10.0)
                reason = "Historial corto, peso moderado"
            else:
                adjusted = max(score, 5.0)
                reason = "Peso basado en score histórico"
        else:
            score = 0.0
            adjusted = 10.0
            reason = "Sin historial, peso neutro"

        raw_strength[asset] = {
            "adjusted_strength": adjusted,
            "score": score,
            "reason": reason
        }

    total_strength = sum(x["adjusted_strength"] for x in raw_strength.values())

    allocation = {}

    for asset, data in raw_strength.items():
        weight = data["adjusted_strength"] / total_strength if total_strength > 0 else 0.0
        allocation[asset] = {
            "weight": weight,
            "score": data["score"],
            "reason": data["reason"]
        }

    return allocation


def apply_capital_allocation(trade_setup, ticker, default_assets):
    """
    Ajusta el trade setup según la asignación de capital del activo.
    """

    allocation_map = get_capital_allocation_map(default_assets)

    asset_info = allocation_map.get(
        ticker,
        {"weight": 0.0, "score": 0.0, "reason": "Activo no encontrado"}
    )

    weight = float(asset_info["weight"])
    score = float(asset_info["score"])
    reason = asset_info["reason"]

    # Convertimos el peso en un multiplicador utilizable.
    # Con 18 activos, el peso neutro ronda ~0.055.
    # Lo normalizamos para que el factor neutro quede cerca de 1.
    neutral_weight = 1.0 / len(default_assets) if default_assets else 1.0

    if neutral_weight <= 0:
        allocation_factor = 1.0
    else:
        allocation_factor = weight / neutral_weight

    # Limitamos el factor para no volvernos locos con capital pequeño
    allocation_factor = max(0.50, min(1.50, allocation_factor))

    adjusted = dict(trade_setup)

    adjusted["position_size"] = float(trade_setup["position_size"]) * allocation_factor
    adjusted["allocated_risk_amount"] = float(
        trade_setup.get("scaled_risk_amount", trade_setup["risk_amount"])
    ) * allocation_factor

    adjusted["capital_allocation_factor"] = allocation_factor
    adjusted["capital_weight"] = weight
    adjusted["capital_score"] = score
    adjusted["capital_reason"] = reason

    return adjusted