import datetime
from pathlib import Path

from portfolio.batch.categories import (
    download_category_monthly_data,
    resolve_access_token,
)
from portfolio.datasource.errors import DownloadError
from portfolio.storage.database import init_db, list_category_monthly_data


def test_resolve_access_token_reads_ms_bearer_token_path(tmp_path, monkeypatch):
    token_file = tmp_path / "morningstar.token"
    token_file.write_text("eyJ-test-token\n", encoding="utf-8")
    monkeypatch.delenv("MORNINGSTAR_ACCESS_TOKEN", raising=False)
    monkeypatch.setenv("MS_BEARER_TOKEN_PATH", str(token_file))
    assert resolve_access_token() == "eyJ-test-token"


def test_resolve_access_token_prefers_env_over_file(tmp_path, monkeypatch):
    token_file = tmp_path / "morningstar.token"
    token_file.write_text("from-file", encoding="utf-8")
    monkeypatch.setenv("MS_BEARER_TOKEN_PATH", str(token_file))
    monkeypatch.setenv("MORNINGSTAR_ACCESS_TOKEN", "from-env")
    assert resolve_access_token() == "from-env"


def test_download_category_monthly_data_persists_rows(tmp_path, monkeypatch):
    db_path = tmp_path / "portfolio.db"
    init_db(db_path)

    def fake_fetch(share_class_id, *, access_token):
        assert access_token == "tok"
        assert share_class_id  # representative fund
        return {
            "graphData": {
                "category": [
                    {"date": "2026-07-31", "value": 100.0},
                    {"date": "2026-08-31", "value": 110.0},
                    {"date": "2026-09-14", "value": 105.0},
                ]
            }
        }

    monkeypatch.setattr(
        "portfolio.batch.categories.fetch_performance_chart",
        fake_fetch,
    )

    # Limit to one known category from the fixture.
    summary = download_category_monthly_data(
        "tok",
        db_path=db_path,
        limit=1,
        sleep_s=0,
    )
    assert summary["ok"] == 1
    assert summary["failed"] == 0

    # Discover which category was processed (first with fund_id in catalog order).
    from portfolio.storage.database import list_categories

    category_id = next(c["category_id"] for c in list_categories(db_path) if c["fund_id"])
    rows = list_category_monthly_data(category_id, db_path=db_path)
    assert len(rows) == 3
    assert rows[0]["return_pct"] is None
    assert abs(rows[1]["return_pct"] - 10.0) < 1e-9
    assert rows[-1]["partial"] is True

    # Second run is idempotent: no duplicate rows.
    summary2 = download_category_monthly_data(
        "tok",
        db_path=db_path,
        limit=1,
        sleep_s=0,
    )
    assert summary2["ok"] == 1
    assert len(list_category_monthly_data(category_id, db_path=db_path)) == 3


def test_download_category_monthly_data_aborts_on_unauthorized(tmp_path, monkeypatch):
    db_path = tmp_path / "portfolio.db"
    init_db(db_path)

    def boom(*_args, **_kwargs):
        raise DownloadError("Morningstar SAL chart unauthorized — refresh the access token")

    monkeypatch.setattr(
        "portfolio.batch.categories.fetch_performance_chart",
        boom,
    )

    try:
        download_category_monthly_data("bad", db_path=db_path, limit=1, sleep_s=0)
        assert False, "expected DownloadError"
    except DownloadError:
        pass
