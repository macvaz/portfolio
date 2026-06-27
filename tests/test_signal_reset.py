import datetime

from sqlmodel import select

from portfolio.api.database import get_session, init_db, reset_signal_tables_from_fixture
from portfolio.api.models import Signal, SignalDimension
from portfolio.common.signal_dimensions import load_signal_dimension_fixture


def test_reset_signal_tables_from_fixture_reloads_catalog(tmp_path):
    db_path = tmp_path / "portfolio.db"
    init_db(db_path)

    with get_session(db_path) as session:
        session.add(
            Signal(
                code="INVERTED_CURVE",
                date=datetime.date(2024, 6, 4),
                value=1.0,
            )
        )
        session.add(
            SignalDimension(
                code="LEGACY_ALERT",
                description="Old row",
                threshold=0.0,
                kind="alert",
            )
        )
        session.commit()

    reset_signal_tables_from_fixture(db_path)

    fixture_rows = load_signal_dimension_fixture()
    with get_session(db_path) as session:
        dimensions = session.exec(select(SignalDimension)).all()
        signals = session.exec(select(Signal)).all()

    assert len(dimensions) == len(fixture_rows)
    assert {dimension.code for dimension in dimensions} == {
        row["code"] for row in fixture_rows
    }
    assert "LEGACY_ALERT" not in {dimension.code for dimension in dimensions}
    assert signals == []
