from io import BytesIO
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError

import pandas as pd
import pytest

from portfolio.datasource.errors import DownloadError
from portfolio.datasource.fred import (
    _fred_http_error_detail,
    download_fred_data,
    init_client,
)


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


def test_download_fred_data_avoids_masked_none_message():
    client = MagicMock()
    client.get_series.side_effect = ValueError(None)

    with pytest.raises(DownloadError, match="ValueError with empty message"):
        download_fred_data(client, "DFII10", "Real_Interest_Rates", "2020-01-01", "2020-02-01")


def test_fred_http_error_detail_includes_status_when_message_missing():
    body = b'<error code="429"></error>'
    exc = HTTPError("https://api.stlouisfed.org/fred", 429, "Too Many Requests", hdrs=None, fp=None)
    detail = _fred_http_error_detail(exc, body)
    assert "HTTP 429" in detail
    assert "Too Many Requests" in detail


def test_init_client_fetch_preserves_http_detail():
    client = init_client("test-key")
    body = b'<error message="Rate limit exceeded"></error>'
    http_exc = HTTPError(
        "https://api.stlouisfed.org/fred",
        429,
        "Too Many Requests",
        hdrs=None,
        fp=BytesIO(body),
    )
    with patch("portfolio.datasource.fred.urlopen", side_effect=http_exc):
        with pytest.raises(ValueError, match="HTTP 429.*Rate limit exceeded"):
            client._Fred__fetch_data("https://api.stlouisfed.org/fred/series?series_id=DFII10")
