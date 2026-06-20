import sqlite3

from portfolio.api.database import init_db, list_funds


def test_migrate_legacy_funds_table(tmp_path):
    db_path = tmp_path / "portfolio.db"
    connection = sqlite3.connect(db_path)
    connection.execute(
        "CREATE TABLE funds (isin TEXT PRIMARY KEY, name TEXT NOT NULL, fund_id TEXT NOT NULL)"
    )
    connection.execute(
        "INSERT INTO funds (isin, name, fund_id) VALUES (?, ?, ?)",
        ("ES0182527038", "Cartesio Y FI", "F0GBR04VSJ"),
    )
    connection.execute(
        "INSERT INTO funds (isin, name, fund_id) VALUES (?, ?, ?)",
        ("IE00BYX5NX33", "World Fund", "F00001019E"),
    )
    connection.commit()
    connection.close()

    init_db(db_path)

    assert list_funds(db_path) == [
        {
            "isin": "ES0182527038",
            "name": "Cartesio Y FI",
            "fund_id": "F0GBR04VSJ",
        },
        {
            "isin": "IE00BYX5NX33",
            "name": "World Fund",
            "fund_id": "F00001019E",
        },
    ]

    connection = sqlite3.connect(db_path)
    tables = {
        row[0]
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
    }
    connection.close()

    assert "funds" not in tables
    assert "fund" in tables
