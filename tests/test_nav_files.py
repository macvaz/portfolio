import pandas as pd
import pytest

from portfolio.common.atomic_io import atomic_to_csv
from portfolio.common.navs import (
    fund_nav_path,
    latest_fund_nav_date,
    latest_nav_as_of,
    load_fund_nav_csv,
    nav_dataframe_to_csv,
    save_fund_nav_csv,
)


def test_nav_dataframe_to_csv_normalizes_timestamp_index():
    df = pd.DataFrame(
        {"value": [100.0, 101.5]},
        index=pd.to_datetime(["2024-01-01", "2024-01-02"]),
    )
    df.index.name = "timestamp"

    out = nav_dataframe_to_csv(df)

    assert list(out.columns) == ["date", "nav"]
    assert out["date"].tolist() == ["2024-01-01", "2024-01-02"]
    assert out["nav"].tolist() == [100.0, 101.5]


def test_save_and_load_fund_nav_csv_roundtrip(tmp_path):
    funds_dir = tmp_path / "funds"
    df = pd.DataFrame(
        {"value": [10.0, 10.5, 11.0]},
        index=pd.to_datetime(["2023-06-01", "2023-06-02", "2023-06-03"]),
    )

    path = save_fund_nav_csv("IE00BYX5NX33", df, funds_dir=funds_dir)
    assert path == fund_nav_path("IE00BYX5NX33", funds_dir=funds_dir)
    assert path.exists()
    assert not path.with_suffix(path.suffix + ".tmp").exists()

    loaded = load_fund_nav_csv("IE00BYX5NX33", funds_dir=funds_dir)
    assert list(loaded.columns) == ["nav"]
    assert len(loaded) == 3
    assert loaded["nav"].tolist() == [10.0, 10.5, 11.0]


def test_save_fund_nav_csv_keeps_previous_file_if_write_fails(tmp_path, monkeypatch):
    funds_dir = tmp_path / "funds"
    original = pd.DataFrame(
        {"value": [10.0, 11.0]},
        index=pd.to_datetime(["2023-06-01", "2023-06-02"]),
    )
    path = save_fund_nav_csv("ES0182527038", original, funds_dir=funds_dir)
    before = path.read_text(encoding="utf-8")

    def boom(self, *args, **kwargs):
        raise OSError("disk full")

    monkeypatch.setattr(pd.DataFrame, "to_csv", boom)

    with pytest.raises(OSError, match="disk full"):
        save_fund_nav_csv(
            "ES0182527038",
            pd.DataFrame(
                {"value": [99.0]},
                index=pd.to_datetime(["2024-01-01"]),
            ),
            funds_dir=funds_dir,
        )

    assert path.read_text(encoding="utf-8") == before
    assert not path.with_suffix(".csv.tmp").exists()


def test_atomic_to_csv_replaces_existing(tmp_path):
    path = tmp_path / "series.csv"
    atomic_to_csv(path, pd.DataFrame({"date": ["2024-01-01"], "value": [1.0]}))
    atomic_to_csv(path, pd.DataFrame({"date": ["2024-01-02"], "value": [2.0]}))
    assert "2024-01-02" in path.read_text(encoding="utf-8")
    assert not path.with_suffix(".csv.tmp").exists()


def test_latest_nav_as_of_uses_newest_fund_date(tmp_path):
    funds_dir = tmp_path / "funds"
    save_fund_nav_csv(
        "AAA",
        pd.DataFrame(
            {"value": [1.0, 2.0]},
            index=pd.to_datetime(["2024-01-01", "2024-01-10"]),
        ),
        funds_dir=funds_dir,
    )
    save_fund_nav_csv(
        "BBB",
        pd.DataFrame(
            {"value": [1.0, 2.0]},
            index=pd.to_datetime(["2024-01-01", "2024-01-15"]),
        ),
        funds_dir=funds_dir,
    )

    as_of_aaa = latest_fund_nav_date("AAA", funds_dir)
    as_of_both = latest_nav_as_of(["AAA", "BBB"], funds_dir)
    assert as_of_aaa is not None and as_of_aaa.isoformat() == "2024-01-10"
    assert as_of_both is not None and as_of_both.isoformat() == "2024-01-15"
    assert latest_nav_as_of(["MISSING"], funds_dir) is None
