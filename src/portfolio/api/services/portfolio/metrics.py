"""Portfolio metrics payload: funds, weights, and stored metrics from the database."""

from datetime import date

from portfolio.api.database import get_fund_metrics, list_funds, list_user_portfolio
from portfolio.datasources.morningstar import morningstar_quote_url
from portfolio.common.metrics import compute_portfolio_metrics


def _fund_row(
    isin: str,
    name: str,
    *,
    weight: float = 0.0,
    performance_id: str | None = None,
    universe: str | None = None,
    db_path=None,
) -> dict:
    return {
        "isin": isin,
        "name": name,
        "weight": weight,
        "morningstar_url": morningstar_quote_url(performance_id, universe),
        **get_fund_metrics(isin, db_path),
    }


def get_portfolio_metrics(user_id: int, db_path=None, funds_dir=None) -> dict:
    """Build portfolio metrics payload with funds, weights, and stored metrics."""
    positions = list_user_portfolio(user_id, db_path)
    portfolio_isins = {position["isin"] for position in positions}

    portfolio = [
        _fund_row(
            position["isin"],
            position["name"],
            weight=round(position["weighted_assets"] * 100, 2),
            performance_id=position.get("performance_id"),
            universe=position.get("universe"),
            db_path=db_path,
        )
        for position in positions
    ]
    favorites = [
        _fund_row(
            fund["isin"],
            fund["name"],
            performance_id=fund.get("performance_id"),
            universe=fund.get("universe"),
            db_path=db_path,
        )
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
            **compute_portfolio_metrics(positions, funds_dir),
        },
    }
