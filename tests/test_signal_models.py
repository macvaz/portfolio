import sqlite3
from datetime import date

from sqlmodel import select

from portfolio.api.database import get_session, init_db
from portfolio.api.models import Signal, SignalDimension


def test_signal_tables_are_created(tmp_path):
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

    assert "signal_dimension" in tables
    assert "signal" in tables


def test_signal_dimension_and_signal_persist(tmp_path):
    db_path = tmp_path / "portfolio.db"
    init_db(db_path)

    with get_session(db_path) as session:
        session.add(
            Signal(
                code="SAHM_RULE",
                date=date(2026, 6, 1),
                value=0.32,
            )
        )
        session.commit()

    with get_session(db_path) as session:
        dimension = session.get(SignalDimension, "SAHM_RULE")
        signal = session.exec(select(Signal)).first()

    assert dimension.comparison_code == "Sahm_Rule_Indicator"
    assert dimension.threshold == 0.5
    assert signal.code == "SAHM_RULE"
    assert signal.date == date(2026, 6, 1)
    assert signal.value == 0.32
