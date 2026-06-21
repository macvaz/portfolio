from pathlib import Path

from portfolio.api.database import init_db, save_fund
from portfolio.finance.nav_files import store_fund_navs_from_db


def test_run_get_navs_stores_csv_per_fund(tmp_path, monkeypatch):
    db_path = tmp_path / "portfolio.db"
    funds_dir = tmp_path / "funds"
    init_db(db_path)
    save_fund("ES0182527038", "Test Fund", "F0GBR04KHC", db_path=db_path)
    save_fund("IE00BYX5NX33", "World Fund", "F00001019E", db_path=db_path)

    calls: list[tuple[str, str]] = []

    def mock_download(*, fund_id, start, end, currency, timeout=30):
        calls.append((fund_id, currency))
        import pandas as pd

        return pd.DataFrame(
            {"value": [100.0, 101.0]},
            index=pd.to_datetime(["2024-01-01", "2024-01-02"]),
        )

    monkeypatch.setattr(
        "portfolio.finance.nav_files.download_navs",
        mock_download,
    )

    saved = store_fund_navs_from_db(
        "2024-01-01",
        "2024-01-02",
        db_path=db_path,
        funds_dir=funds_dir,
    )

    assert len(saved) == 2
    assert (funds_dir / "ES0182527038.csv").exists()
    assert (funds_dir / "IE00BYX5NX33.csv").exists()
    assert calls == [
        ("F0GBR04KHC", "EUR"),
        ("F00001019E", "EUR"),
    ]

    content = (funds_dir / "ES0182527038.csv").read_text(encoding="utf-8")
    assert content.startswith("date,nav\n")
    assert "2024-01-01,100.0" in content


def test_run_get_navs_skips_funds_without_data(tmp_path, monkeypatch):
    db_path = tmp_path / "portfolio.db"
    funds_dir = tmp_path / "funds"
    init_db(db_path)
    save_fund("ES0182527038", "Test Fund", "F0GBR04KHC", db_path=db_path)

    import pandas as pd

    monkeypatch.setattr(
        "portfolio.finance.nav_files.download_navs",
        lambda **_kwargs: pd.DataFrame(),
    )

    saved = store_fund_navs_from_db(
        "2024-01-01",
        "2024-01-02",
        db_path=db_path,
        funds_dir=funds_dir,
    )

    assert saved == []
    assert not (funds_dir / "ES0182527038.csv").exists()
