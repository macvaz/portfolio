import pandas as pd

from portfolio.batch.sp500 import SP500_SECURITY_ID, download_sp500


def test_download_sp500_downloads_from_morningstar(monkeypatch):
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
        "portfolio.batch.sp500.download_navs", fake_download_navs
    )

    history = download_sp500(start_date="2000-01-01", end_date="2000-01-10")
    assert len(history) == 2
    assert history.iloc[0]["SP500"] == 1455.22
    assert history.index[0] == pd.Timestamp("2000-01-03")
