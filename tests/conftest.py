"""Shared pytest fixtures for isolated test databases."""

from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def _isolate_runtime_data_dirs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Path:
    """Keep tests from reading/writing production data/funds or risk_reports."""
    funds_dir = tmp_path / "isolated_funds"
    reports_dir = tmp_path / "isolated_risk_reports"
    funds_dir.mkdir()
    reports_dir.mkdir()
    monkeypatch.setattr("portfolio.common.navs.DEFAULT_FUNDS_DIR", funds_dir)
    monkeypatch.setattr(
        "portfolio.common.risk_report_cache.DEFAULT_RISK_REPORTS_DIR",
        reports_dir,
    )
    return funds_dir


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
