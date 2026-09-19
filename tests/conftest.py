"""Shared pytest fixtures for isolated test databases."""

from pathlib import Path

import pytest


@pytest.fixture
def empty_fund_catalog(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Skip seeding production fund fixtures so isolation tests stay self-contained."""
    empty = tmp_path / "empty_funds.json"
    empty.write_text("[]\n", encoding="utf-8")
    monkeypatch.setattr(
        "portfolio.storage.fixtures.funds.DEFAULT_FUND_FIXTURE",
        empty,
    )
    return empty
