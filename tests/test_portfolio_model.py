from portfolio.api.database import (
    create_user,
    init_db,
    list_user_portfolio,
    list_users,
    save_fund,
    save_user_portfolio,
)
from portfolio.api.models import User
from portfolio.api.database import get_session


def test_save_user_portfolio_persists_positions(tmp_path):
    db_path = tmp_path / "portfolio.db"
    init_db(db_path)
    user = create_user("Growth", db_path)

    save_fund("ES0182527038", "Test Fund", "F0GBR04KHC", db_path=db_path)
    save_fund("IE00BYX5NX33", "World Fund", "F00001019E", db_path=db_path)

    saved = save_user_portfolio(
        user.id,
        [
            {"isin": "ES0182527038", "weighted_assets": 0.4},
            {"isin": "IE00BYX5NX33", "weighted_assets": 0.6},
        ],
        db_path,
    )

    assert saved == [
        {
            "isin": "ES0182527038",
            "name": "Test Fund",
            "fund_id": "F0GBR04KHC",
            "performance_id": None,
            "universe": None,
            "weighted_assets": 0.4,
        },
        {
            "isin": "IE00BYX5NX33",
            "name": "World Fund",
            "fund_id": "F00001019E",
            "performance_id": None,
            "universe": None,
            "weighted_assets": 0.6,
        },
    ]
    assert list_user_portfolio(user.id, db_path) == saved


def test_list_users_includes_default_flag(tmp_path):
    db_path = tmp_path / "portfolio.db"
    init_db(db_path)
    miguel = create_user("Miguel_Agresiva", db_path)
    other = create_user("Other", db_path)

    with get_session(db_path) as session:
        miguel_user = session.get(User, miguel.id)
        miguel_user.is_default = True
        session.add(miguel_user)
        session.commit()

    assert list_users(db_path) == [
        {"id": miguel.id, "name": "Miguel_Agresiva", "is_default": True},
        {"id": other.id, "name": "Other", "is_default": False},
    ]


def test_user_is_default_migration_sets_miguel_agresiva(tmp_path):
    db_path = tmp_path / "portfolio.db"
    from portfolio.api.database import get_engine

    engine = get_engine(db_path)
    with engine.connect() as connection:
        connection.exec_driver_sql(
            "CREATE TABLE user (id INTEGER NOT NULL PRIMARY KEY, name VARCHAR NOT NULL)"
        )
        connection.exec_driver_sql(
            "INSERT INTO user (id, name) VALUES (1, 'Miguel_Agresiva')"
        )
        connection.exec_driver_sql("INSERT INTO user (id, name) VALUES (2, 'Other')")
        connection.commit()

    init_db(db_path)

    assert list_users(db_path) == [
        {"id": 1, "name": "Miguel_Agresiva", "is_default": True},
        {"id": 2, "name": "Other", "is_default": False},
    ]
