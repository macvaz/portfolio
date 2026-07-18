import pytest

from portfolio.datasource.fred import download_fred_data


def test_download_fred_data_rejects_deprecated_sp500():
    with pytest.raises(ValueError, match="SP500.*deprecated"):
        download_fred_data(None, "SP500", "SP500", "2000-01-01", "2024-01-01")
