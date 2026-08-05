"""Seed and sync macro health check description rows from the JSON fixture."""

import datetime
from pathlib import Path

from sqlmodel import delete, select

from portfolio.storage.models import MacroHealthCheck, MacroHealthCheckDescription
from portfolio.common.health_check_descriptions import (
    HEALTH_CHECK_ROLE,
    load_health_check_description_fixture,
)


def _description_from_row(row: dict) -> MacroHealthCheckDescription:
    threshold = row.get("threshold")
    operator = row.get("operator")
    raw_series_start = row.get("series_start")
    series_start = None
    if raw_series_start:
        series_start = datetime.date.fromisoformat(str(raw_series_start))
    return MacroHealthCheckDescription(
        code=str(row["code"]),
        description=str(row["description"]),
        source=str(row.get("source", "fred")),
        series_id=row.get("series_id"),
        series_start=series_start,
        threshold=None if threshold is None else float(threshold),
        operator=None if operator is None else str(operator),
        role=str(row.get("role") or HEALTH_CHECK_ROLE),
        domain=None if row.get("domain") is None else str(row["domain"]),
    )


def seed_health_check_descriptions(
    session,
    fixture_path: Path | None = None,
) -> None:
    for row in load_health_check_description_fixture(fixture_path):
        session.merge(_description_from_row(row))


def insert_health_check_descriptions_from_fixture(
    session,
    fixture_path: Path | None = None,
) -> None:
    for row in load_health_check_description_fixture(fixture_path):
        session.add(_description_from_row(row))


def sync_health_check_catalog_from_fixture(
    session,
    fixture_path: Path | None = None,
) -> None:
    fixture_codes = {
        str(row["code"])
        for row in load_health_check_description_fixture(fixture_path)
    }
    for description in session.exec(select(MacroHealthCheckDescription)).all():
        if description.code in fixture_codes:
            continue
        session.exec(
            delete(MacroHealthCheck).where(MacroHealthCheck.code == description.code)
        )
        session.delete(description)
    seed_health_check_descriptions(session, fixture_path)
