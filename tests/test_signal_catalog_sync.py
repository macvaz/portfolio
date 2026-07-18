import datetime

from sqlmodel import select

from portfolio.storage.database import get_session, init_db
from portfolio.storage.models import Alert, AlertDescription
from portfolio.common.alert_descriptions import load_alert_description_fixture


def test_init_db_prunes_removed_alert_descriptions(tmp_path):
    db_path = tmp_path / "portfolio.db"
    init_db(db_path)

    with get_session(db_path) as session:
        session.add(
            AlertDescription(
                code="MACRO_CRISIS_VOTES",
                description="Legacy",
                threshold=2.0,
                source="fred",
                operator="gte",
            )
        )
        session.flush()
        session.add(
            Alert(
                code="MACRO_CRISIS_VOTES",
                date=datetime.date(2024, 6, 4),
                value=0.0,
            )
        )
        session.commit()

    init_db(db_path)

    fixture_codes = {row["code"] for row in load_alert_description_fixture()}
    with get_session(db_path) as session:
        descriptions = session.exec(select(AlertDescription)).all()
        alerts = session.exec(select(Alert)).all()

    assert {description.code for description in descriptions} == fixture_codes
    assert all(alert.code in fixture_codes for alert in alerts)
    assert "MACRO_CRISIS_VOTES" not in {description.code for description in descriptions}
