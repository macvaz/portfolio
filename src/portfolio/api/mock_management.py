"""Dashboard screen payload: real funds from the database, mocked performance metrics."""

from datetime import date

from portfolio.api.database import list_funds, list_user_portfolio

DEFAULT_MOCK_METRICS = {
    "beta_6m": 0.05,
    "cor_6m": 0.19,
    "vol_1y": 3.44,
    "pct_1m": 2.30,
    "pct_3m": -0.56,
    "pct_6m": 2.49,
    "pct_ytd": 5.43,
    "sr_6m": 1.58,
    "sr_1y": 1.67,
}


def _fund_row(isin: str, name: str, *, weight: float = 0.0) -> dict:
    return {
        "isin": isin,
        "name": name,
        "weight": weight,
        **DEFAULT_MOCK_METRICS,
    }


def build_dashboard_data(user_id: int, db_path=None) -> dict:
    """Build dashboard payload with real funds/weights and mocked metrics."""
    positions = list_user_portfolio(user_id, db_path)
    portfolio_isins = {position["isin"] for position in positions}

    portfolio = [
        _fund_row(
            position["isin"],
            position["name"],
            weight=round(position["weighted_assets"] * 100, 2),
        )
        for position in positions
    ]
    favorites = [
        _fund_row(fund["isin"], fund["name"])
        for fund in list_funds(db_path)
        if fund["isin"] not in portfolio_isins
    ]
    total_weight = round(sum(fund["weight"] for fund in portfolio), 2)

    return {
        "as_of": date.today().isoformat(),
        "portfolio": portfolio,
        "favorites": favorites,
        "portfolio_summary": {
            "weight": total_weight,
            **DEFAULT_MOCK_METRICS,
        },
    }
