import sqlite3
from datetime import date

from sqlmodel import select

from portfolio.api.database import get_session, init_db
from portfolio.api.models import Alert, AlertDescription


def test_alert_tables_are_created(tmp_path):
    db_path = tmp_path / "portfolio.db"
    init_db(db_path)

    connection = sqlite3.connect(db_path)
    tables = {
        row[0]
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
    }
    connection.close()

    assert "alert_description" in tables
    assert "alert" in tables


def test_alert_description_and_alert_persist(tmp_path):
    db_path = tmp_path / "portfolio.db"
    init_db(db_path)

    with get_session(db_path) as session:
        session.add(
            Alert(
                code="Sahm_Rule_Indicator",
                date=date(2026, 6, 1),
                value=0.32,
            )
        )
        session.commit()

    with get_session(db_path) as session:
        description = session.get(AlertDescription, "Sahm_Rule_Indicator")
        alert = session.exec(select(Alert)).first()

    assert description.operator == "gte"
    assert description.threshold == 0.5
    assert alert.code == "Sahm_Rule_Indicator"
    assert alert.date == date(2026, 6, 1)
    assert alert.value == 0.32
