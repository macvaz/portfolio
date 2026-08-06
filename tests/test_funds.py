from portfolio.storage.database import get_fund, init_db, list_funds, save_fund
from portfolio.storage.fixtures.funds import load_fund_fixture
from portfolio.datasource.morningstar import (
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


def test_init_db_syncs_funds_from_fixture(tmp_path):
    db_path = tmp_path / "portfolio.db"
    init_db(db_path)

    fixture_rows = load_fund_fixture()
    funds = list_funds(db_path)
    assert len(funds) == len(fixture_rows)
    assert {fund["isin"] for fund in funds} == {
        str(row["isin"]).upper() for row in fixture_rows
    }


def test_init_db_merges_fixture_over_existing_funds(tmp_path):
    db_path = tmp_path / "portfolio.db"
    init_db(db_path)
    save_fund(
        "ES0182527038",
        "Custom Fund",
        "CUSTOM_ID",
        db_path=db_path,
    )

    init_db(db_path)

    fixture_row = next(
        row for row in load_fund_fixture() if row["isin"] == "ES0182527038"
    )
    fund = get_fund("ES0182527038", db_path)
    assert fund["name"] == fixture_row["name"]
    assert fund["security_id"] == fixture_row["fund_id"]
    assert len(list_funds(db_path)) == len(load_fund_fixture())


def test_init_db_keeps_funds_not_in_fixture(tmp_path):
    db_path = tmp_path / "portfolio.db"
    init_db(db_path)
    save_fund(
        "XX0000000001",
        "Legacy Fund",
        "LEGACY",
        db_path=db_path,
    )

    init_db(db_path)

    fund = get_fund("XX0000000001", db_path)
    assert fund is not None
    assert fund["name"] == "Legacy Fund"
    assert len(list_funds(db_path)) == len(load_fund_fixture()) + 1


def test_save_fund_roundtrip_for_non_fixture_isin(tmp_path):
    db_path = tmp_path / "portfolio.db"
    init_db(db_path)
    save_fund(
        "XX0000000002",
        "Test Fund",
        "F0GBR04KHC",
        "0P000068Z4",
        "FO",
        ter=0.5,
        db_path=db_path,
    )

    assert get_fund("XX0000000002", db_path) == {
        "isin": "XX0000000002",
        "name": "Test Fund",
        "security_id": "F0GBR04KHC",
        "performance_id": "0P000068Z4",
        "universe": "FO",
        "ter": 0.5,
    }


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
