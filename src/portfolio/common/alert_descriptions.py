"""Alert catalog fixture loading and threshold evaluation (no DB)."""

import json
from pathlib import Path

DEFAULT_ALERT_DESCRIPTION_FIXTURE = Path("data/fixtures/alert_description.json")


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
