import pandas as pd

from portfolio.job.sp500 import (
    SP500_SECURITY_ID,
    download_sp500_history,
    save_backtest_sp500_csv,
)


def test_download_sp500_history_downloads_from_morningstar(monkeypatch):
    index = pd.to_datetime(["2000-01-03", "2000-01-04"])
    fake_history = pd.DataFrame(
        {"value": [1455.22, 1394.46]},
        index=index,
    )

    def fake_download_navs(**kwargs):
        assert kwargs["fund_id"] == SP500_SECURITY_ID
        assert kwargs["currency"] == "USD"
        assert kwargs["start"] == "2000-01-01"
        assert kwargs["end"] == "2000-01-10"
        return fake_history

    monkeypatch.setattr(
        "portfolio.job.sp500.download_navs", fake_download_navs
    )

    history = download_sp500_history(start_date="2000-01-01", end_date="2000-01-10")
    assert len(history) == 2
    assert history.iloc[0]["value"] == 1455.22
    assert history.index[0] == pd.Timestamp("2000-01-03")


def test_save_backtest_sp500_csv_writes_date_value_columns(tmp_path):
    history = pd.DataFrame(
        {"value": [1455.22, 1394.46]},
        index=pd.to_datetime(["2000-01-03", "2000-01-04"]),
    )
    path = save_backtest_sp500_csv(history, tmp_path / "sp500.csv")
    stored = pd.read_csv(path)
    assert list(stored.columns) == ["date", "value"]
    assert stored["date"].tolist() == ["2000-01-03", "2000-01-04"]


def test_load_backtest_sp500_csv_filters_date_range(tmp_path):
    path = tmp_path / "sp500.csv"
    pd.DataFrame(
        {
            "date": ["1999-12-31", "2000-01-03", "2000-01-04"],
            "value": [100.0, 1455.22, 1394.46],
        }
    ).to_csv(path, index=False)

    from portfolio.job.sp500 import load_backtest_sp500_csv

    history = load_backtest_sp500_csv(
        path,
        start_date="2000-01-01",
        end_date="2000-01-03",
    )
    assert list(history.columns) == ["SP500"]
    assert len(history) == 1
    assert history.iloc[0]["SP500"] == 1455.22
