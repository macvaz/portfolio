import datetime

from sqlmodel import select

from portfolio.api.database import get_session, init_db, reset_alert_tables_from_fixture
from portfolio.api.models import Alert, AlertDescription
from portfolio.common.alert_descriptions import load_alert_description_fixture


def test_reset_alert_tables_from_fixture_reloads_catalog(tmp_path):
    db_path = tmp_path / "portfolio.db"
    init_db(db_path)

    with get_session(db_path) as session:
        session.add(
            Alert(
                code="Yield_Spread_10Y3M",
                date=datetime.date(2024, 6, 4),
                value=-0.05,
            )
        )
        session.add(
            AlertDescription(
                code="LEGACY_ALERT",
                description="Old row",
                threshold=0.0,
                source="fred",
                operator="gte",
            )
        )
        session.commit()

    reset_alert_tables_from_fixture(db_path)

    fixture_rows = load_alert_description_fixture()
    with get_session(db_path) as session:
        descriptions = session.exec(select(AlertDescription)).all()
        alerts = session.exec(select(Alert)).all()

    assert len(descriptions) == len(fixture_rows)
    assert {description.code for description in descriptions} == {
        row["code"] for row in fixture_rows
    }
    assert "LEGACY_ALERT" not in {description.code for description in descriptions}
    assert alerts == []
