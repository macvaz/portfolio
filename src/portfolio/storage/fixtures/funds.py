"""Seed and sync fund rows from the JSON fixture."""

import json
from pathlib import Path

from portfolio.storage.models import Fund

DEFAULT_FUND_FIXTURE = Path("data/fixtures/fund.json")


def load_fund_fixture(fixture_path: Path | None = None) -> list[dict]:
    path = fixture_path or DEFAULT_FUND_FIXTURE
    with path.open(encoding="utf-8") as handle:
        rows = json.load(handle)

    if not isinstance(rows, list):
        raise ValueError(f"Expected a JSON array in {path}")

    return rows


def _fund_from_row(row: dict) -> Fund:
    ter = row.get("ter")
    return Fund(
        isin=str(row["isin"]).upper(),
        name=str(row["name"]),
        fund_id=str(row["fund_id"]),
        performance_id=(
            None if row.get("performance_id") is None else str(row["performance_id"])
        ),
        universe=None if row.get("universe") is None else str(row["universe"]),
        ter=None if ter is None else float(ter),
    )


def sync_funds_from_fixture(
    session,
    fixture_path: Path | None = None,
) -> None:
    """Merge all fixture funds into the DB (insert new, update existing).

    Unlike health-check sync, funds not present in the fixture are kept so
    funds added via the API/UI are not deleted on every ``init_db``.
    """
    path = fixture_path or DEFAULT_FUND_FIXTURE
    if not path.exists():
        return
    for row in load_fund_fixture(path):
        session.merge(_fund_from_row(row))
