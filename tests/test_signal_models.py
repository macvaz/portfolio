import sqlite3
from datetime import date

from sqlmodel import select

from portfolio.storage.database import get_session, init_db
from portfolio.storage.models import Alert, AlertDescription


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
                code="Breakeven_Inflation",
                date=date(2026, 6, 1),
                value=2.3,
            )
        )
        session.commit()

    with get_session(db_path) as session:
        description = session.get(AlertDescription, "Breakeven_Inflation")
        alert = session.exec(select(Alert)).first()

    assert description.operator == "gte"
    assert description.threshold == 2.5
    assert alert.code == "Breakeven_Inflation"
    assert alert.date == date(2026, 6, 1)
    assert alert.value == 2.3
