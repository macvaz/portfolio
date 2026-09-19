from portfolio.storage.database import get_session, init_db, list_categories
from portfolio.storage.models import Category
from sqlmodel import select


def test_init_db_syncs_categories_from_fixture(tmp_path):
    db_path = tmp_path / "portfolio.db"
    init_db(db_path)

    categories = list_categories(db_path)
    assert len(categories) >= 100
    by_id = {row["category_id"]: row for row in categories}
    flexible = by_id["EUCA000864"]
    assert flexible["name"] == "EUR Flexible Allocation"
    assert flexible["fund_id"]
    assert flexible["asset_class"] == "mixed"
    africa = by_id["EUCA000698"]
    assert africa["fund_id"] == "F00000MKF1"
    assert africa["performance_id"] == "0P0000TJ7F"
    europe = by_id["EUCA000511"]
    assert europe["name"] == "Europe Large-Cap Blend Equity"
    assert europe["asset_class"] == "equity"


def test_init_db_prunes_removed_categories(tmp_path):
    db_path = tmp_path / "portfolio.db"
    init_db(db_path)

    with get_session(db_path) as session:
        session.add(
            Category(
                category_id="TESTCA999999",
                name="Temporary Category",
                fund_id="F00000TEST",
                asset_class="other",
            )
        )
        session.commit()

    init_db(db_path)
    ids = {row["category_id"] for row in list_categories(db_path)}
    assert "TESTCA999999" not in ids
    assert "EUCA000864" in ids


def test_category_model_fields(tmp_path):
    db_path = tmp_path / "portfolio.db"
    init_db(db_path)
    with get_session(db_path) as session:
        row = session.exec(
            select(Category).where(Category.category_id == "EUCA000864")
        ).one()
    assert row.name == "EUR Flexible Allocation"
    assert row.fund_id
    assert row.asset_class == "mixed"
    africa = session.exec(
        select(Category).where(Category.category_id == "EUCA000698")
    ).one()
    assert africa.performance_id == "0P0000TJ7F"
