"""Unit tests for filesystem risk-report caching."""

import pandas as pd

from portfolio.api.services.portfolio.risk_report import (
    build_user_risk_report_html,
    warm_all_risk_report_caches,
    warm_user_risk_report_cache,
)
from portfolio.api.services.portfolio.risk_report_cache import (
    nav_stamp,
    positions_fingerprint,
    read_cached_risk_report,
    write_cached_risk_report,
)
from portfolio.common.navs import save_fund_nav_csv
from portfolio.storage.database import create_user, init_db, save_fund, save_user_portfolio


def _seed(tmp_path, monkeypatch):
    db_path = tmp_path / "portfolio.db"
    funds_dir = tmp_path / "funds"
    reports_dir = tmp_path / "risk_reports"
    monkeypatch.setattr("portfolio.storage.database.DEFAULT_DB_PATH", db_path)
    monkeypatch.setattr("portfolio.common.navs.DEFAULT_FUNDS_DIR", funds_dir)
    init_db(db_path)
    save_fund("ES0182527038", "Test Fund", "F0GBR04KHC", db_path=db_path)
    df = pd.DataFrame(
        {"value": [100.0, 101.0, 102.0, 103.0, 104.0]},
        index=pd.to_datetime(
            ["2024-01-01", "2024-01-02", "2024-01-03", "2024-01-04", "2024-01-05"]
        ),
    )
    save_fund_nav_csv("ES0182527038", df, funds_dir=funds_dir)
    save_fund_nav_csv("IE00BYX5MX67", df, funds_dir=funds_dir)
    user_id = create_user("Growth", db_path=db_path).id
    positions = [{"isin": "ES0182527038", "weighted_assets": 1.0}]
    save_user_portfolio(user_id, positions, db_path=db_path)
    return db_path, funds_dir, reports_dir, user_id, positions


def test_positions_fingerprint_is_order_independent():
    a = [{"isin": "AAA", "weighted_assets": 0.4}, {"isin": "BBB", "weighted_assets": 0.6}]
    b = [{"isin": "BBB", "weighted_assets": 0.6}, {"isin": "AAA", "weighted_assets": 0.4}]
    assert positions_fingerprint(a) == positions_fingerprint(b)
    c = [{"isin": "AAA", "weighted_assets": 0.5}, {"isin": "BBB", "weighted_assets": 0.5}]
    assert positions_fingerprint(a) != positions_fingerprint(c)


def test_build_user_risk_report_caches_full_period(tmp_path, monkeypatch):
    db_path, funds_dir, reports_dir, user_id, _ = _seed(tmp_path, monkeypatch)
    calls = {"n": 0}

    def mock_report_html(portfolio_returns, benchmark_returns):
        calls["n"] += 1
        return "<html>cached</html>"

    monkeypatch.setattr(
        "portfolio.api.services.portfolio.risk_report.generate_performance_report_html",
        mock_report_html,
    )

    first = build_user_risk_report_html(
        user_id, db_path=db_path, funds_dir=funds_dir, reports_dir=reports_dir
    )
    second = build_user_risk_report_html(
        user_id, db_path=db_path, funds_dir=funds_dir, reports_dir=reports_dir
    )
    assert first == second == "<html>cached</html>"
    assert calls["n"] == 1
    assert list(reports_dir.glob("*.html"))


def test_nav_stamp_change_misses_cache(tmp_path, monkeypatch):
    db_path, funds_dir, reports_dir, user_id, positions = _seed(tmp_path, monkeypatch)
    write_cached_risk_report(
        user_id,
        positions,
        "<html>old</html>",
        funds_dir=funds_dir,
        reports_dir=reports_dir,
    )
    assert (
        read_cached_risk_report(
            user_id, positions, funds_dir=funds_dir, reports_dir=reports_dir
        )
        == "<html>old</html>"
    )

    path = funds_dir / "ES0182527038.csv"
    path.touch()
    assert (
        read_cached_risk_report(
            user_id, positions, funds_dir=funds_dir, reports_dir=reports_dir
        )
        is None
    )
    assert nav_stamp(positions, funds_dir)


def test_warm_all_risk_report_caches(tmp_path, monkeypatch):
    db_path, funds_dir, reports_dir, user_id, _ = _seed(tmp_path, monkeypatch)
    monkeypatch.setattr(
        "portfolio.api.services.portfolio.risk_report.generate_performance_report_html",
        lambda *args, **kwargs: "<html>warm</html>",
    )
    warmed = warm_all_risk_report_caches(
        db_path=db_path, funds_dir=funds_dir, reports_dir=reports_dir
    )
    assert warmed == 1
    assert (
        build_user_risk_report_html(
            user_id, db_path=db_path, funds_dir=funds_dir, reports_dir=reports_dir
        )
        == "<html>warm</html>"
    )


def test_warm_empty_portfolio_clears_cache(tmp_path, monkeypatch):
    db_path, funds_dir, reports_dir, user_id, positions = _seed(tmp_path, monkeypatch)
    write_cached_risk_report(
        user_id,
        positions,
        "<html>stale</html>",
        funds_dir=funds_dir,
        reports_dir=reports_dir,
    )
    save_user_portfolio(user_id, [], db_path=db_path)
    assert (
        warm_user_risk_report_cache(
            user_id, db_path=db_path, funds_dir=funds_dir, reports_dir=reports_dir
        )
        is None
    )
    assert list(reports_dir.glob("*.html")) == []
