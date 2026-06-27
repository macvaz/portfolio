import sqlite3

from portfolio.api.database import init_db


def test_migrate_signal_alert_codes_when_new_code_already_exists(tmp_path):
    db_path = tmp_path / "portfolio.db"
    connection = sqlite3.connect(db_path)
    connection.execute(
        "CREATE TABLE signal_dimension ("
        "code VARCHAR NOT NULL PRIMARY KEY, "
        "description VARCHAR NOT NULL, "
        "threshold REAL, "
        "kind VARCHAR NOT NULL DEFAULT 'alert', "
        "series_id VARCHAR"
        ")"
    )
    connection.execute(
        "CREATE TABLE signal ("
        "id INTEGER NOT NULL PRIMARY KEY, "
        "code VARCHAR NOT NULL, "
        "date DATE NOT NULL, "
        "value REAL NOT NULL, "
        "UNIQUE (code, date)"
        ")"
    )
    connection.execute(
        "INSERT INTO signal_dimension (code, description, threshold, kind) "
        "VALUES ('Alert_Inverted_Curve', 'Old', 0.0, 'alert')"
    )
    connection.execute(
        "INSERT INTO signal_dimension (code, description, threshold, kind) "
        "VALUES ('INVERTED_CURVE', 'New', 0.0, 'alert')"
    )
    connection.execute(
        "INSERT INTO signal (id, code, date, value) "
        "VALUES (1, 'Alert_Inverted_Curve', '2024-06-04', 1.0)"
    )
    connection.execute(
        "INSERT INTO signal (id, code, date, value) "
        "VALUES (2, 'INVERTED_CURVE', '2024-06-04', 0.0)"
    )
    connection.commit()
    connection.close()

    init_db(db_path)

    connection = sqlite3.connect(db_path)
    dimensions = {
        row[0]
        for row in connection.execute("SELECT code FROM signal_dimension").fetchall()
    }
    signals = connection.execute(
        "SELECT code, value FROM signal ORDER BY code"
    ).fetchall()
    connection.close()

    assert "Alert_Inverted_Curve" not in dimensions
    assert "INVERTED_CURVE" in dimensions
    assert signals == [("INVERTED_CURVE", 0.0)]


def test_migrate_signal_alert_codes_renames_legacy_rows(tmp_path):
    db_path = tmp_path / "portfolio.db"
    connection = sqlite3.connect(db_path)
    connection.execute(
        "CREATE TABLE signal_dimension ("
        "code VARCHAR NOT NULL PRIMARY KEY, "
        "description VARCHAR NOT NULL, "
        "threshold REAL, "
        "kind VARCHAR NOT NULL DEFAULT 'alert', "
        "series_id VARCHAR"
        ")"
    )
    connection.execute(
        "CREATE TABLE signal ("
        "id INTEGER NOT NULL PRIMARY KEY, "
        "code VARCHAR NOT NULL, "
        "date DATE NOT NULL, "
        "value REAL NOT NULL, "
        "UNIQUE (code, date)"
        ")"
    )
    connection.execute(
        "INSERT INTO signal_dimension (code, description, threshold, kind) "
        "VALUES ('Sahm_Value', 'Old', 0.5, 'alert')"
    )
    connection.execute(
        "INSERT INTO signal (id, code, date, value) "
        "VALUES (1, 'Sahm_Value', '2024-06-04', 0.32)"
    )
    connection.commit()
    connection.close()

    init_db(db_path)

    connection = sqlite3.connect(db_path)
    row = connection.execute(
        "SELECT code FROM signal_dimension WHERE code = 'SAHM_RULE'"
    ).fetchone()
    signal = connection.execute(
        "SELECT code FROM signal WHERE date = '2024-06-04'"
    ).fetchone()
    connection.close()

    assert row == ("SAHM_RULE",)
    assert signal == ("SAHM_RULE",)
