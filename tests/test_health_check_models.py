import sqlite3
from datetime import date

from sqlmodel import select

from portfolio.storage.database import get_session, init_db
from portfolio.storage.models import MacroHealthCheck, MacroHealthCheckDescription


def test_health_check_tables_are_created(tmp_path):
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

    assert "macro_health_check_description" in tables
    assert "macro_health_check" in tables
    assert "alert" not in tables
    assert "alert_description" not in tables


def test_health_check_description_and_check_persist(tmp_path):
    db_path = tmp_path / "portfolio.db"
    init_db(db_path)

    with get_session(db_path) as session:
        session.add(
            MacroHealthCheck(
                code="Breakeven_Inflation",
                date=date(2026, 6, 1),
                value=2.3,
            )
        )
        session.commit()

    with get_session(db_path) as session:
        description = session.get(MacroHealthCheckDescription, "Breakeven_Inflation")
        check = session.exec(select(MacroHealthCheck)).first()

    assert description.operator == "gte"
    assert description.threshold == 2.5
    assert check.code == "Breakeven_Inflation"
    assert check.date == date(2026, 6, 1)
    assert check.value == 2.3
