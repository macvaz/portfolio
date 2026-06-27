import json
from pathlib import Path

from portfolio.api.models import SignalDimension

DEFAULT_SIGNAL_DIMENSION_FIXTURE = Path("data/fixtures/signal_dimension.json")

ALERT_COMPARISON_OPERATORS = {
    "INVERTED_CURVE": "lt",
    "SP500_DEATH_CROSS_ACTIVE": "lt",
    "SP500_CONFIRMED_DEATH_CROSS": "lte",
}


def load_signal_dimension_fixture(
    fixture_path: Path | None = None,
) -> list[dict[str, str | float]]:
    path = fixture_path or DEFAULT_SIGNAL_DIMENSION_FIXTURE
    with path.open(encoding="utf-8") as handle:
        rows = json.load(handle)

    if not isinstance(rows, list):
        raise ValueError(f"Expected a JSON array in {path}")

    return rows


def seed_signal_dimensions(
    session,
    fixture_path: Path | None = None,
) -> None:
    for row in load_signal_dimension_fixture(fixture_path):
        threshold = row.get("threshold")
        session.merge(
            SignalDimension(
                code=str(row["code"]),
                description=str(row["description"]),
                threshold=None if threshold is None else float(threshold),
                kind=str(row.get("kind", "alert")),
                series_id=row.get("series_id"),
                comparison_code=row.get("comparison_code"),
            )
        )


def insert_signal_dimensions_from_fixture(
    session,
    fixture_path: Path | None = None,
) -> None:
    for row in load_signal_dimension_fixture(fixture_path):
        threshold = row.get("threshold")
        session.add(
            SignalDimension(
                code=str(row["code"]),
                description=str(row["description"]),
                threshold=None if threshold is None else float(threshold),
                kind=str(row.get("kind", "alert")),
                series_id=row.get("series_id"),
                comparison_code=row.get("comparison_code"),
            )
        )


def is_alert_active(
    code: str,
    comparison_value: float | None,
    threshold: float | None,
) -> bool:
    if comparison_value is None or threshold is None:
        return False

    operator = ALERT_COMPARISON_OPERATORS.get(code, "gte")
    if operator == "lt":
        return comparison_value < threshold
    if operator == "lte":
        return comparison_value <= threshold
    return comparison_value >= threshold
