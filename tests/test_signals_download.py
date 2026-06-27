from unittest.mock import patch

import pandas as pd

from portfolio.common.signals import download_data


def test_download_data_stores_fred_series(tmp_path):
    series_dir = tmp_path / "series"

    def fake_download(_fred, series_id, column_name, _start, _end):
        return pd.DataFrame(
            {column_name: [float(len(series_id))]},
            index=pd.to_datetime(["2024-01-02"]),
        )

    with patch(
        "portfolio.common.signals.download_fred_data", side_effect=fake_download
    ):
        download_data(
            "test-key",
            [("UNRATE", "Unemployment_Rate"), ("T10Y3M", "Yield_Spread_10Y3M")],
            "2024-01-01",
            "2024-01-31",
            series_dir=series_dir,
        )

    assert (series_dir / "UNRATE.csv").exists()
    assert (series_dir / "T10Y3M.csv").exists()
    assert (series_dir / "SP500.csv").exists()

    unemployment = pd.read_csv(series_dir / "UNRATE.csv")
    assert list(unemployment.columns) == ["date", "value"]
    assert unemployment["date"].tolist() == ["2024-01-02"]
    assert unemployment["value"].tolist() == [6.0]
