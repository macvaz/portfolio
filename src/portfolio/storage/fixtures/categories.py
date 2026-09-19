"""Seed and sync Morningstar category rows from the JSON fixture."""

from __future__ import annotations

import json
from pathlib import Path

from sqlmodel import select

from portfolio.storage.models import Category

DEFAULT_CATEGORY_FIXTURE = Path("data/fixtures/categories.json")


def load_category_fixture(fixture_path: Path | None = None) -> list[dict]:
    path = fixture_path or DEFAULT_CATEGORY_FIXTURE
    with path.open(encoding="utf-8") as handle:
        rows = json.load(handle)

    if not isinstance(rows, list):
        raise ValueError(f"Expected a JSON array in {path}")

    return rows


def _category_from_row(row: dict) -> Category:
    fund_id = row.get("fund_id")
    performance_id = row.get("performance_id")
    asset_class = row.get("asset_class")
    return Category(
        category_id=str(row["category_id"]).strip(),
        name=str(row["name"]).strip(),
        fund_id=None if fund_id in (None, "") else str(fund_id).strip(),
        performance_id=(
            None if performance_id in (None, "") else str(performance_id).strip()
        ),
        asset_class=(
            None if asset_class in (None, "") else str(asset_class).strip().lower()
        ),
    )


def sync_categories_from_fixture(
    session,
    fixture_path: Path | None = None,
) -> None:
    """Replace the category catalog with the fixture contents.

    Categories are a reference list (not user-edited), so rows absent from
    the fixture are removed on sync.
    """
    path = fixture_path or DEFAULT_CATEGORY_FIXTURE
    if not path.exists():
        return

    rows = load_category_fixture(path)
    wanted_ids = {str(row["category_id"]).strip() for row in rows}

    for category in session.exec(select(Category)).all():
        if category.category_id not in wanted_ids:
            session.delete(category)

    for row in rows:
        session.merge(_category_from_row(row))
