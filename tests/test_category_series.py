import datetime

from portfolio.storage.database import (
    build_category_monthly_data,
    init_db,
    list_category_monthly_data,
    merge_category_monthly_data,
)


def test_merge_category_monthly_data_stores_price_and_return(tmp_path):
    db_path = tmp_path / "portfolio.db"
    init_db(db_path)

    points = [
        (datetime.date(2026, 6, 30), 100.0),
        (datetime.date(2026, 7, 31), 110.0),
        (datetime.date(2026, 8, 31), 105.0),
        (datetime.date(2026, 9, 14), 102.0),
    ]
    result = merge_category_monthly_data("EUCA000864", points, db_path=db_path)
    assert result == {"category_id": "EUCA000864", "inserted": 4, "skipped": 0}

    rows = list_category_monthly_data("EUCA000864", db_path=db_path)
    assert [row["date"] for row in rows] == [p[0] for p in points]
    assert rows[0]["return_pct"] is None
    assert abs(rows[1]["return_pct"] - 10.0) < 1e-9
    assert rows[-1]["partial"] is True


def test_merge_category_monthly_data_is_idempotent(tmp_path):
    db_path = tmp_path / "portfolio.db"
    init_db(db_path)

    points = [
        (datetime.date(2026, 6, 30), 100.0),
        (datetime.date(2026, 7, 31), 110.0),
        (datetime.date(2026, 8, 31), 105.0),
    ]
    first = merge_category_monthly_data("EUCA000864", points, db_path=db_path)
    second = merge_category_monthly_data("EUCA000864", points, db_path=db_path)
    assert first["inserted"] == 3
    assert second == {"category_id": "EUCA000864", "inserted": 0, "skipped": 3}
    assert len(list_category_monthly_data("EUCA000864", db_path=db_path)) == 3


def test_merge_category_monthly_data_appends_only_new_dates(tmp_path):
    db_path = tmp_path / "portfolio.db"
    init_db(db_path)

    merge_category_monthly_data(
        "EUCA000864",
        [
            (datetime.date(2026, 6, 30), 100.0),
            (datetime.date(2026, 7, 31), 110.0),
        ],
        db_path=db_path,
    )
    result = merge_category_monthly_data(
        "EUCA000864",
        [
            (datetime.date(2026, 6, 30), 100.0),
            (datetime.date(2026, 7, 31), 110.0),
            (datetime.date(2026, 8, 31), 121.0),
        ],
        db_path=db_path,
    )
    assert result["inserted"] == 1
    assert result["skipped"] == 2

    rows = list_category_monthly_data("EUCA000864", db_path=db_path)
    assert [row["date"] for row in rows] == [
        datetime.date(2026, 6, 30),
        datetime.date(2026, 7, 31),
        datetime.date(2026, 8, 31),
    ]
    assert abs(rows[-1]["return_pct"] - 10.0) < 1e-9


def test_build_category_monthly_data_skips_return_on_zero_start():
    rows = build_category_monthly_data(
        [
            (datetime.date(2026, 1, 31), 0.0),
            (datetime.date(2026, 2, 28), 10.0),
            (datetime.date(2026, 3, 31), 11.0),
        ]
    )
    assert rows[0]["return_pct"] is None
    assert rows[1]["return_pct"] is None
    assert abs(rows[2]["return_pct"] - 10.0) < 1e-9
