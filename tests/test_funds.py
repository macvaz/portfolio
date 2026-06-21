from portfolio.api.database import get_fund, init_db, list_funds, save_fund
from portfolio.datasources.morningstar import import_isins, morningstar_quote_url


def test_morningstar_quote_url():
    assert morningstar_quote_url("0P000068Z4", "FO") == (
        "https://global.morningstar.com/es/inversiones/fondos/0P000068Z4/cotizacion"
    )
    assert morningstar_quote_url("0P000068Z4", "FE") == (
        "https://global.morningstar.com/es/inversiones/etfs/0P000068Z4/cotizacion"
    )
    assert morningstar_quote_url("0P000068Z4") == (
        "https://global.morningstar.com/es/inversiones/fondos/0P000068Z4/cotizacion"
    )
    assert morningstar_quote_url(None, "FO") is None


def test_list_funds_empty_when_db_empty(tmp_path):
    db_path = tmp_path / "portfolio.db"
    init_db(db_path)
    assert list_funds(db_path) == []


def test_save_fund_roundtrip(tmp_path):
    db_path = tmp_path / "portfolio.db"
    save_fund(
        "ES0182527038",
        "Test Fund",
        "F0GBR04KHC",
        "0P000068Z4",
        "FO",
        db_path=db_path,
    )

    assert get_fund("ES0182527038", db_path) == {
        "isin": "ES0182527038",
        "name": "Test Fund",
        "security_id": "F0GBR04KHC",
        "performance_id": "0P000068Z4",
        "universe": "FO",
    }
    assert list_funds(db_path) == [
        {
            "isin": "ES0182527038",
            "name": "Test Fund",
            "fund_id": "F0GBR04KHC",
            "performance_id": "0P000068Z4",
            "universe": "FO",
        }
    ]


def test_import_isins_uses_cached_fund(tmp_path, monkeypatch):
    db_path = tmp_path / "portfolio.db"
    save_fund(
        "ES0182527038",
        "Cached Fund",
        "F0GBR04KHC",
        "0P000068Z4",
        "FO",
        db_path=db_path,
    )

    def fail_search(_isin):
        raise AssertionError("Morningstar search should not be called for cached ISIN")

    monkeypatch.setattr(
        "portfolio.datasources.morningstar._search_by_isin", fail_search
    )

    fund = import_isins("ES0182527038", db_path=db_path)

    assert fund == {
        "security_id": "F0GBR04KHC",
        "performance_id": "0P000068Z4",
        "universe": "FO",
        "name": "Cached Fund",
        "isin": "ES0182527038",
    }


def test_import_isins_fetches_and_persists_new_isin(tmp_path, monkeypatch):
    db_path = tmp_path / "portfolio.db"

    def mock_search(isin):
        return {
            "security_id": "F0GBR04KHC",
            "performance_id": "0P000068Z4",
            "universe": "FE",
            "name": "Fetched Fund",
            "isin": isin,
        }

    monkeypatch.setattr(
        "portfolio.datasources.morningstar._search_by_isin", mock_search
    )

    fund = import_isins("IE00BYX5NX33", db_path=db_path)

    assert fund == {
        "security_id": "F0GBR04KHC",
        "performance_id": "0P000068Z4",
        "universe": "FE",
        "name": "Fetched Fund",
        "isin": "IE00BYX5NX33",
    }
    assert get_fund("IE00BYX5NX33", db_path) == {
        "isin": "IE00BYX5NX33",
        "name": "Fetched Fund",
        "security_id": "F0GBR04KHC",
        "performance_id": "0P000068Z4",
        "universe": "FE",
    }
