"""Alert catalog fixture loading and threshold evaluation (no DB)."""

import json
from pathlib import Path

DEFAULT_ALERT_DESCRIPTION_FIXTURE = Path("data/fixtures/alert_description.json")

ALERT_LABELS = {
    "High_Yield_Spread": "High yield spread",
    "Financial_Stress_Index": "Financial stress",
    "Yield_Spread_10Y3M": "Curve inversion",
    "Real_Interest_Rates": "Real interest rate",
    "Unemployment_Rate": "Unemployment rate",
    "Breakeven_Inflation": "Breakeven inflation",
    "SP500_Death_Cross": "SP500 death cross",
    "SP500": "SP500",
    "Treasury_10Y_Yield": "10Y Treasury yield",
    "Broad_Dollar_Index": "Broad dollar index",
    "Reserve_Balances": "Reserve balances",
    "Overnight_RRP": "Overnight RRP",
    "SOFR": "SOFR",
}


def alert_label(code: str) -> str:
    return ALERT_LABELS.get(code, code.replace("_", " "))


def alert_role(row: dict) -> str:
    return str(row.get("role") or "alert")


def is_alert_role(row: dict) -> bool:
    return alert_role(row) == "alert"


def is_context_role(row: dict) -> bool:
    return alert_role(row) == "context"


def fred_series_from_fixture(
    fixture_path: Path | None = None,
) -> list[tuple[str, str]]:
    """Return ``(series_id, catalog_code)`` pairs for every FRED fixture row."""
    pairs: list[tuple[str, str]] = []
    for entry in load_alert_description_fixture(fixture_path):
        if entry.get("source") != "fred" or not entry.get("series_id"):
            continue
        pairs.append((str(entry["series_id"]), str(entry["code"])))
    return pairs


def load_alert_description_fixture(
    fixture_path: Path | None = None,
) -> list[dict[str, str | float]]:
    path = fixture_path or DEFAULT_ALERT_DESCRIPTION_FIXTURE
    with path.open(encoding="utf-8") as handle:
        rows = json.load(handle)

    if not isinstance(rows, list):
        raise ValueError(f"Expected a JSON array in {path}")

    return rows


def is_alert_active(
    value: float | None,
    threshold: float | None,
    operator: str | None,
) -> bool | None:
    if value is None or threshold is None or operator is None:
        return None

    if operator == "lt":
        return value < threshold
    if operator == "lte":
        return value <= threshold
    return value >= threshold
