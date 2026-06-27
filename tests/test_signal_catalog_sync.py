import datetime

from sqlmodel import select

from portfolio.api.database import get_session, init_db
from portfolio.api.models import Signal, SignalDimension
from portfolio.common.signal_dimensions import load_signal_dimension_fixture


def test_init_db_prunes_removed_signal_dimensions(tmp_path):
    db_path = tmp_path / "portfolio.db"
    init_db(db_path)

    with get_session(db_path) as session:
        session.add(
            SignalDimension(
                code="MACRO_CRISIS_VOTES",
                description="Legacy",
                threshold=2.0,
                kind="alert",
            )
        )
        session.flush()
        session.add(
            Signal(
                code="MACRO_CRISIS_VOTES",
                date=datetime.date(2024, 6, 4),
                value=0.0,
            )
        )
        session.commit()

    init_db(db_path)

    fixture_codes = {row["code"] for row in load_signal_dimension_fixture()}
    with get_session(db_path) as session:
        dimensions = session.exec(select(SignalDimension)).all()
        signals = session.exec(select(Signal)).all()

    assert {dimension.code for dimension in dimensions} == fixture_codes
    assert all(signal.code in fixture_codes for signal in signals)
    assert "MACRO_CRISIS_VOTES" not in {dimension.code for dimension in dimensions}
