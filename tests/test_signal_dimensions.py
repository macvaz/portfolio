import json

from sqlmodel import select

from portfolio.api.database import get_session, init_db
from portfolio.api.models import SignalDimension
from portfolio.common.signal_dimensions import (
    DEFAULT_SIGNAL_DIMENSION_FIXTURE,
    load_signal_dimension_fixture,
)


def test_signal_dimension_fixture_matches_hardcoded_thresholds():
    rows = {row["code"]: row for row in load_signal_dimension_fixture()}

    assert rows["Yield_Spread_10Y3M"]["threshold"] == 0.0
    assert rows["SAHM_RULE"]["threshold"] == 0.5
    assert rows["Financial_Stress_Index"]["threshold"] == 1.0
    assert rows["INVERTED_CURVE"]["threshold"] == 0.0
    assert rows["FINANCIAL_STRESS"]["threshold"] == 1.0
    assert rows["MACRO_CRISIS_VOTES"]["threshold"] == 2.0
    assert rows["MACRO_SYSTEM_LOCKED"]["threshold"] == 2.0
    assert rows["Unemployment_Rate"]["series_id"] == "UNRATE"
    assert rows["Yield_Spread_10Y3M"]["series_id"] == "T10Y3M"
    assert rows["Unemployment_Rate"]["kind"] == "series"
    assert rows["SAHM_RULE"]["kind"] == "alert"
    assert rows["INVERTED_CURVE"]["kind"] == "alert"


def test_init_db_seeds_signal_dimensions_from_fixture(tmp_path):
    db_path = tmp_path / "portfolio.db"
    init_db(db_path)

    fixture_rows = load_signal_dimension_fixture()
    with get_session(db_path) as session:
        stored = session.exec(
            select(SignalDimension).order_by(SignalDimension.code)
        ).all()

    assert len(stored) == len(fixture_rows)
    assert [dimension.code for dimension in stored] == sorted(
        row["code"] for row in fixture_rows
    )

    fixture_by_code = {row["code"]: row for row in fixture_rows}
    for dimension in stored:
        expected = fixture_by_code[dimension.code]
        assert dimension.description == expected["description"]
        assert dimension.threshold == expected["threshold"]
        assert dimension.kind == expected["kind"]
        assert dimension.series_id == expected["series_id"]
        assert dimension.comparison_code == expected["comparison_code"]


def test_signal_dimension_fixture_is_valid_json():
    payload = json.loads(DEFAULT_SIGNAL_DIMENSION_FIXTURE.read_text(encoding="utf-8"))
    assert isinstance(payload, list)
    assert all(
        {"code", "description", "threshold", "kind", "series_id", "comparison_code"}
        <= set(row)
        for row in payload
    )
    assert all(
        "Alert_" not in row["code"]
        for row in payload
        if row["kind"] == "alert"
    )
