import json
from pathlib import Path

from sqlmodel import delete, select

from portfolio.api.models import Alert, AlertDescription

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


def sync_alert_catalog_from_fixture(
    session,
    fixture_path: Path | None = None,
) -> None:
    fixture_codes = {
        str(row["code"]) for row in load_alert_description_fixture(fixture_path)
    }
    for description in session.exec(select(AlertDescription)).all():
        if description.code in fixture_codes:
            continue
        session.exec(delete(Alert).where(Alert.code == description.code))
        session.delete(description)
    seed_alert_descriptions(session, fixture_path)


def _description_from_row(row: dict) -> AlertDescription:
    threshold = row.get("threshold")
    operator = row.get("operator")
    return AlertDescription(
        code=str(row["code"]),
        description=str(row["description"]),
        source=str(row.get("source", "fred")),
        series_id=row.get("series_id"),
        threshold=None if threshold is None else float(threshold),
        operator=None if operator is None else str(operator),
    )


def seed_alert_descriptions(
    session,
    fixture_path: Path | None = None,
) -> None:
    for row in load_alert_description_fixture(fixture_path):
        session.merge(_description_from_row(row))


def insert_alert_descriptions_from_fixture(
    session,
    fixture_path: Path | None = None,
) -> None:
    for row in load_alert_description_fixture(fixture_path):
        session.add(_description_from_row(row))


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
