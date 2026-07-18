import datetime
import json

from sqlmodel import select

from portfolio.storage.database import get_session, init_db
from portfolio.storage.models import AlertDescription
from portfolio.common.alert_descriptions import (
    DEFAULT_ALERT_DESCRIPTION_FIXTURE,
    load_alert_description_fixture,
)


def test_alert_description_fixture_matches_expected_catalog():
    rows = {row["code"]: row for row in load_alert_description_fixture()}

    assert rows["Yield_Spread_10Y3M"]["threshold"] == 0.0
    assert rows["Yield_Spread_10Y3M"]["operator"] == "lt"
    assert rows["Sahm_Rule_Indicator"]["threshold"] == 0.5
    assert rows["Sahm_Rule_Indicator"]["series_id"] == "SAHMREALTIME"
    assert rows["Financial_Stress_Index"]["threshold"] == 1.0
    assert rows["High_Yield_Spread"]["threshold"] == 9.0
    assert rows["Unemployment_Rate"]["threshold"] == 5.0
    assert rows["Real_Interest_Rates"]["threshold"] == 2.0
    assert rows["SP500_Death_Cross"]["source"] == "computed"
    assert rows["SP500_Death_Cross"]["operator"] == "lt"
    assert rows["Unemployment_Rate"]["source"] == "fred"


def test_init_db_seeds_alert_descriptions_from_fixture(tmp_path):
    db_path = tmp_path / "portfolio.db"
    init_db(db_path)

    fixture_rows = load_alert_description_fixture()
    with get_session(db_path) as session:
        stored = session.exec(
            select(AlertDescription).order_by(AlertDescription.code)
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
        expected_start = expected.get("series_start")
        if expected_start is None:
            assert description.series_start is None
        else:
            assert description.series_start == datetime.date.fromisoformat(
                str(expected_start)
            )


def test_alert_description_fixture_is_valid_json():
    payload = json.loads(DEFAULT_ALERT_DESCRIPTION_FIXTURE.read_text(encoding="utf-8"))
    assert isinstance(payload, list)
    assert all(
        {"code", "description", "threshold", "source", "series_id", "series_start", "operator"}
        <= set(row)
        for row in payload
    )
