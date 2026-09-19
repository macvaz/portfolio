"""Category ranking API helpers."""

from __future__ import annotations

from collections import defaultdict

from sqlmodel import Session, select

from portfolio.storage.models import Category, CategoryMonthlyData

ASSET_CLASS_LABELS = {
    "equity": "Equity",
    "bond": "Bond",
    "mixed": "Mixed",
    "alternatives": "Alternatives",
    "real_assets": "Real assets",
    "money_market": "Money market",
    "convertibles": "Convertibles",
    "hybrid": "Hybrid",
    "capital_preservation": "Capital preservation",
    "other": "Other",
    "property": "Property",
    "commodities": "Commodities",
}

# Trailing windows over completed (non-partial) monthly returns: (column key, months).
RETURN_WINDOWS = (
    ("1m", 1),
    ("2m", 2),
    ("3m", 3),
    ("6m", 6),
    ("12m", 12),
    ("2y", 24),
    ("3y", 36),
    ("5y", 60),
    ("7y", 84),
    ("10y", 120),
)


def asset_class_label(asset_class: str | None) -> str | None:
    if not asset_class:
        return None
    key = asset_class.strip().lower()
    return ASSET_CLASS_LABELS.get(key, key.replace("_", " ").title())


def _compounded_return(pcts: list[float]) -> float:
    factor = 1.0
    for pct in pcts:
        factor *= 1.0 + pct / 100.0
    return (factor - 1.0) * 100.0


def category_period_returns(
    points: list[CategoryMonthlyData],
) -> dict[str, float | None]:
    """
    Build return columns from a category's monthly series.

    - ``intramonth``: latest partial/MTD point return, if any
    - ``1m`` / ``2y`` / …: compounded returns over the last N full months
    """
    ordered = sorted(points, key=lambda row: row.date)
    returns: dict[str, float | None] = {
        "intramonth": None,
        **{key: None for key, _months in RETURN_WINDOWS},
    }
    if not ordered:
        return returns

    latest = ordered[-1]
    if latest.partial and latest.return_pct is not None:
        returns["intramonth"] = float(latest.return_pct)

    full = [
        float(row.return_pct)
        for row in ordered
        if (not row.partial) and row.return_pct is not None
    ]
    for key, months in RETURN_WINDOWS:
        if len(full) >= months:
            returns[key] = _compounded_return(full[-months:])
    return returns


def fetch_top_categories(session: Session, *, limit: int | None = None) -> dict:
    """Rank categories with multi-horizon monthly return columns."""
    rows = session.exec(
        select(CategoryMonthlyData, Category)
        .join(Category, Category.category_id == CategoryMonthlyData.category_id)
        .where(CategoryMonthlyData.return_pct.is_not(None))
        .order_by(CategoryMonthlyData.category_id, CategoryMonthlyData.date)
    ).all()

    by_category: dict[str, list[CategoryMonthlyData]] = defaultdict(list)
    categories: dict[str, Category] = {}
    for point, category in rows:
        by_category[category.category_id].append(point)
        categories[category.category_id] = category

    if not by_category:
        return {"as_of": None, "categories": []}

    ranked = []
    as_of_dates = []
    for category_id, points in by_category.items():
        category = categories[category_id]
        returns = category_period_returns(points)
        if all(value is None for value in returns.values()):
            continue
        latest_date = max(point.date for point in points)
        as_of_dates.append(latest_date)
        ranked.append(
            {
                "category_id": category.category_id,
                "name": category.name,
                "fund_id": category.fund_id,
                "performance_id": category.performance_id,
                "asset_class": category.asset_class,
                "asset_class_name": asset_class_label(category.asset_class),
                "as_of": latest_date.isoformat(),
                "returns": returns,
            }
        )

    def sort_key(item: dict) -> tuple:
        returns = item["returns"]
        # Prefer 1m, then intramonth, then longer windows.
        for key in (
            "1m",
            "intramonth",
            "2m",
            "3m",
            "6m",
            "12m",
            "2y",
            "3y",
            "5y",
            "7y",
            "10y",
        ):
            value = returns.get(key)
            if value is not None:
                return (0, -float(value))
        return (1, 0.0)

    ranked.sort(key=sort_key)
    if limit is not None and limit > 0:
        ranked = ranked[:limit]

    return {
        "as_of": max(as_of_dates).isoformat() if as_of_dates else None,
        "categories": ranked,
    }
