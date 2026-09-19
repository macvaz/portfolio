"""Portfolio metrics payload: funds, weights, and stored metrics from the database."""

from portfolio.storage.database import get_fund_metrics, list_funds, list_user_portfolio
from portfolio.datasource.morningstar import morningstar_quote_url
from portfolio.common.metrics import (
    PERIOD_RETURN_KEYS,
    compute_portfolio_correlation_matrix,
    compute_portfolio_metrics,
    compute_portfolio_ter,
)
from portfolio.common.navs import fund_nav_path, latest_nav_as_of


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
    as_of = latest_nav_as_of(portfolio_isins, funds_dir)

    # Period totals must use the same DB figures shown in fund rows so a missing
    # NAV CSV cannot silently drop a holding from the average.
    fund_metrics_by_isin = {
        str(row["isin"]).upper(): {key: row.get(key) for key in PERIOD_RETURN_KEYS}
        for row in portfolio
    }
    missing_nav = sorted(
        str(position["isin"]).upper()
        for position in positions
        if float(position["weighted_assets"]) > 0
        and not fund_nav_path(str(position["isin"]), funds_dir).exists()
    )

    return {
        "as_of": as_of.isoformat() if as_of else None,
        "missing_nav": missing_nav,
        "portfolio": portfolio,
        "favorites": favorites,
        "portfolio_summary": {
            "weight": total_weight,
            "ter": compute_portfolio_ter(positions),
            **compute_portfolio_metrics(
                positions,
                funds_dir,
                fund_metrics_by_isin=fund_metrics_by_isin,
            ),
        },
        "correlation_matrix": compute_portfolio_correlation_matrix(
            positions, funds_dir
        ),
    }
