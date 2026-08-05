import datetime
import json

from sqlmodel import select

from portfolio.storage.database import get_session, init_db
from portfolio.storage.models import MacroHealthCheckDescription
from portfolio.common.health_check_descriptions import (
    DEFAULT_MACRO_HEALTH_CHECK_DESCRIPTION_FIXTURE,
    load_health_check_description_fixture,
)


def test_health_check_description_fixture_matches_expected_catalog():
    rows = {row["code"]: row for row in load_health_check_description_fixture()}

    assert rows["Yield_Spread_10Y3M"]["threshold"] == 0.0
    assert rows["Yield_Spread_10Y3M"]["operator"] == "lt"
    assert rows["Breakeven_Inflation"]["threshold"] == 2.5
    assert rows["Breakeven_Inflation"]["series_id"] == "T10YIE"
    assert rows["Financial_Stress_Index"]["threshold"] == 1.0
    assert rows["High_Yield_Spread"]["threshold"] == 9.0
    assert rows["Unemployment_Rate"]["threshold"] == 5.0
    assert rows["Real_Interest_Rates"]["threshold"] == 2.0
    assert rows["SP500_Death_Cross"]["source"] == "computed"
    assert rows["SP500_Death_Cross"]["operator"] == "lt"
    assert rows["Unemployment_Rate"]["source"] == "fred"
    assert rows["Unemployment_Rate"]["role"] == "health_check"
    assert rows["Treasury_10Y_Yield"]["series_id"] == "DGS10"
    assert rows["Treasury_10Y_Yield"]["role"] == "context"
    assert rows["Treasury_10Y_Yield"]["threshold"] == 4.5
    assert rows["Treasury_10Y_Yield"]["operator"] == "gte"
    assert rows["Broad_Dollar_Index"]["series_id"] == "DTWEXBGS"
    assert rows["Reserve_Balances"]["series_id"] == "WRESBAL"
    assert rows["Overnight_RRP"]["series_id"] == "RRPONTSYD"
    assert rows["SOFR"]["series_id"] == "SOFR"
    assert rows["SOFR"]["role"] == "context"


def test_fred_series_from_fixture_includes_context_and_health_checks():
    from portfolio.common.health_check_descriptions import fred_series_from_fixture

    pairs = fred_series_from_fixture()
    by_id = dict(pairs)
    assert by_id["UNRATE"] == "Unemployment_Rate"
    assert by_id["DGS10"] == "Treasury_10Y_Yield"
    assert by_id["DTWEXBGS"] == "Broad_Dollar_Index"
    assert by_id["WRESBAL"] == "Reserve_Balances"
    assert by_id["RRPONTSYD"] == "Overnight_RRP"
    assert by_id["SOFR"] == "SOFR"
    assert "SP500_Death_Cross" not in {code for _, code in pairs}


def test_init_db_seeds_health_check_descriptions_from_fixture(tmp_path):
    db_path = tmp_path / "portfolio.db"
    init_db(db_path)

    fixture_rows = load_health_check_description_fixture()
    with get_session(db_path) as session:
        stored = session.exec(
            select(MacroHealthCheckDescription).order_by(MacroHealthCheckDescription.code)
        ).all()

    assert len(stored) == len(fixture_rows)
    assert [description.code for description in stored] == sorted(
        row["code"] for row in fixture_rows
    )

    fixture_by_code = {row["code"]: row for row in fixture_rows}
    for description in stored:
        expected = fixture_by_code[description.code]
        assert description.description == expected["description"]
        assert description.threshold == expected["threshold"]
        assert description.source == expected["source"]
        assert description.operator == expected["operator"]
        assert description.series_id == expected["series_id"]
        assert description.role == expected.get("role", "health_check")
        assert description.domain == expected.get("domain")
        expected_start = expected.get("series_start")
        if expected_start is None:
            assert description.series_start is None
        else:
            assert description.series_start == datetime.date.fromisoformat(
                str(expected_start)
            )


def test_health_check_description_fixture_is_valid_json():
    payload = json.loads(
        DEFAULT_MACRO_HEALTH_CHECK_DESCRIPTION_FIXTURE.read_text(encoding="utf-8")
    )
    assert isinstance(payload, list)
    assert all(
        {
            "code",
            "description",
            "threshold",
            "source",
            "series_id",
            "series_start",
            "operator",
            "role",
            "domain",
        }
        <= set(row)
        for row in payload
    )
    assert {row["role"] for row in payload} == {"health_check", "context"}
    assert all(isinstance(row["domain"], str) and row["domain"] for row in payload)
