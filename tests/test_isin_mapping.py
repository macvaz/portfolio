from portfolio.funds import resolve_fund_by_isin
from portfolio.isin_mapping import load_isin_mapping, save_isin_mapping


def test_load_returns_empty_dict_when_file_missing(tmp_path):
    assert load_isin_mapping(tmp_path / "missing.json") == {}


def test_save_and_load_roundtrip(tmp_path):
    path = tmp_path / "isin_mapping.json"
    mapping = {
        "ES0182527038": {
            "security_id": "F0GBR04KHC",
            "name": "Test Fund",
        }
    }
    save_isin_mapping(mapping, path)

    assert load_isin_mapping(path) == mapping


def test_resolve_fund_by_isin_uses_cached_mapping(tmp_path, monkeypatch):
    path = tmp_path / "isin_mapping.json"
    save_isin_mapping(
        {
            "ES0182527038": {
                "security_id": "F0GBR04KHC",
                "name": "Cached Fund",
            }
        },
        path,
    )

    def fail_search(_isin):
        raise AssertionError("Morningstar search should not be called for cached ISIN")

    monkeypatch.setattr("portfolio.funds.search_by_isin", fail_search)

    fund = resolve_fund_by_isin("ES0182527038", mapping_path=path)

    assert fund == {
        "security_id": "F0GBR04KHC",
        "name": "Cached Fund",
        "isin": "ES0182527038",
    }


def test_resolve_fund_by_isin_fetches_and_persists_new_isin(tmp_path, monkeypatch):
    path = tmp_path / "isin_mapping.json"

    def mock_search(isin):
        return {
            "security_id": "F0GBR04KHC",
            "name": "Fetched Fund",
            "isin": isin,
        }

    monkeypatch.setattr("portfolio.funds.search_by_isin", mock_search)

    fund = resolve_fund_by_isin("IE00BYX5NX33", mapping_path=path)

    assert fund == {
        "security_id": "F0GBR04KHC",
        "name": "Fetched Fund",
        "isin": "IE00BYX5NX33",
    }
    assert load_isin_mapping(path) == {
        "IE00BYX5NX33": {
            "security_id": "F0GBR04KHC",
            "name": "Fetched Fund",
        }
    }
