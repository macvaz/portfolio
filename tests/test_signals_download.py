from unittest.mock import patch

import pandas as pd
import pytest

from portfolio.batch.signals import download_data
from portfolio.datasource.errors import DownloadError


def test_download_data_stores_fred_series_and_index(tmp_path):
    series_dir = tmp_path / "series"
    indexes_dir = tmp_path / "indexes"

    def fake_download(_fred, series_id, column_name, _start, _end):
        return pd.DataFrame(
            {column_name: [float(len(series_id))]},
            index=pd.to_datetime(["2024-01-02"]),
        )

    with patch(
        "portfolio.batch.signals.download_fred_data", side_effect=fake_download
    ), patch(
        "portfolio.batch.signals.download_sp500",
        return_value=pd.DataFrame(
            {"SP500": [4800.0]},
            index=pd.to_datetime(["2024-01-02"]),
        ),
    ):
        download_data(
            "test-key",
            [("UNRATE", "Unemployment_Rate"), ("T10Y3M", "Yield_Spread_10Y3M")],
            "2024-01-01",
            "2024-01-31",
            series_dir=series_dir,
            indexes_dir=indexes_dir,
        )

    assert (series_dir / "UNRATE.csv").exists()
    assert (series_dir / "T10Y3M.csv").exists()
    assert (indexes_dir / "SP500.csv").exists()
    assert not (series_dir / "SP500.csv").exists()

    unemployment = pd.read_csv(series_dir / "UNRATE.csv")
    assert list(unemployment.columns) == ["date", "value"]
    assert unemployment["date"].tolist() == ["2024-01-02"]
    assert unemployment["value"].tolist() == [6.0]


def test_download_data_skips_fred_without_api_key(tmp_path):
    series_dir = tmp_path / "series"
    indexes_dir = tmp_path / "indexes"

    with patch("portfolio.batch.signals.download_fred_data") as mock_fred, patch(
        "portfolio.batch.signals.download_sp500",
        return_value=pd.DataFrame(
            {"SP500": [4800.0]},
            index=pd.to_datetime(["2024-01-02"]),
        ),
    ):
        frame = download_data(
            None,
            [("UNRATE", "Unemployment_Rate")],
            "2024-01-01",
            "2024-01-31",
            series_dir=series_dir,
            indexes_dir=indexes_dir,
        )

    mock_fred.assert_not_called()
    assert not (series_dir / "UNRATE.csv").exists()
    assert (indexes_dir / "SP500.csv").exists()
    assert list(frame.columns) == ["SP500", "SP500_Death_Cross"]


def test_download_data_raises_when_fred_series_fails(tmp_path):
    with patch(
        "portfolio.batch.signals.download_fred_data",
        side_effect=DownloadError("Failed to download FRED series 'UNRATE': boom"),
    ), patch(
        "portfolio.batch.signals.download_sp500",
        return_value=pd.DataFrame(
            {"SP500": [4800.0]},
            index=pd.to_datetime(["2024-01-02"]),
        ),
    ):
        with pytest.raises(DownloadError, match="UNRATE"):
            download_data(
                "test-key",
                [("UNRATE", "Unemployment_Rate")],
                "2024-01-01",
                "2024-01-31",
                series_dir=tmp_path / "series",
                indexes_dir=tmp_path / "indexes",
            )
