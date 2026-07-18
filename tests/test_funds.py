from portfolio.api.database import get_fund, init_db, list_funds, save_fund
from portfolio.datasources.morningstar import (
    morningstar_quote_url,
    parse_morningstar_search,
)


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


def test_parse_morningstar_search():
    payload = {
        "results": [
            {
                "fields": {
                    "name": {"value": "Fetched Fund"},
                    "isin": {"value": "ie00byx5nx33"},
                },
                "meta": {
                    "securityID": "F0GBR04KHC",
                    "performanceID": "0P000068Z4",
                    "universe": "FE",
                },
            }
        ]
    }

    assert parse_morningstar_search(payload) == {
        "isin": "IE00BYX5NX33",
        "name": "Fetched Fund",
        "security_id": "F0GBR04KHC",
        "performance_id": "0P000068Z4",
        "universe": "FE",
    }
