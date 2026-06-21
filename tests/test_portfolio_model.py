from portfolio.api.auth import hash_password
from portfolio.api.database import (
    create_user,
    init_db,
    list_user_portfolio,
    save_fund,
    save_user_portfolio,
)


def test_save_user_portfolio_persists_positions(tmp_path):
    db_path = tmp_path / "portfolio.db"
    init_db(db_path)
    user = create_user("user@example.com", hash_password("secretpass"), db_path)

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
