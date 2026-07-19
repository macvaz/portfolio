from unittest.mock import MagicMock

import pandas as pd
import pytest

from portfolio.datasource.errors import DownloadError
from portfolio.datasource.fred import download_fred_data


def test_download_fred_data_rejects_deprecated_sp500():
    with pytest.raises(ValueError, match="SP500.*deprecated"):
        download_fred_data(None, "SP500", "SP500", "2000-01-01", "2024-01-01")


def test_download_fred_data_raises_on_client_error():
    client = MagicMock()
    client.get_series.side_effect = RuntimeError("boom")

    with pytest.raises(DownloadError, match="UNRATE"):
        download_fred_data(client, "UNRATE", "Unemployment_Rate", "2020-01-01", "2020-02-01")


def test_download_fred_data_raises_on_empty_series():
    client = MagicMock()
    client.get_series.return_value = pd.Series(dtype=float)

    with pytest.raises(DownloadError, match="no observations"):
        download_fred_data(client, "UNRATE", "Unemployment_Rate", "2020-01-01", "2020-02-01")
