import datetime

from fastapi.testclient import TestClient

from portfolio.api.api import app
from portfolio.api.services.categories.service import category_period_returns
from portfolio.storage.database import (
    get_session,
    init_db,
    merge_category_monthly_data,
)
from portfolio.storage.models import Category, CategoryMonthlyData


def test_category_period_returns_splits_intramonth_and_windows():
    points = [
        CategoryMonthlyData(
            category_id="X",
            date=datetime.date(2026, 6, 30),
            value=100.0,
            return_pct=None,
            partial=False,
        ),
        CategoryMonthlyData(
            category_id="X",
            date=datetime.date(2026, 7, 31),
            value=110.0,
            return_pct=10.0,
            partial=False,
        ),
        CategoryMonthlyData(
            category_id="X",
            date=datetime.date(2026, 8, 31),
            value=121.0,
            return_pct=10.0,
            partial=False,
        ),
        CategoryMonthlyData(
            category_id="X",
            date=datetime.date(2026, 9, 15),
            value=123.42,
            return_pct=2.0,
            partial=True,
        ),
    ]
    returns = category_period_returns(points)
    assert returns["intramonth"] == 2.0
    assert abs(returns["1m"] - 10.0) < 1e-9
    assert abs(returns["2m"] - 21.0) < 1e-9
    assert returns["3m"] is None
    assert returns["2y"] is None
    assert returns["10y"] is None


def test_category_period_returns_multi_year_windows():
    # 24 full months of +1% each → 2y compounds the last 24 monthly returns.
    points = [
        CategoryMonthlyData(
            category_id="Y",
            date=datetime.date(2024, 1, 31),
            value=100.0,
            return_pct=None,
            partial=False,
        )
    ]
    value = 100.0
    year, month = 2024, 1
    for _ in range(24):
        month += 1
        if month > 12:
            month = 1
            year += 1
        day = 28 if month == 2 else 30 if month in (4, 6, 9, 11) else 31
        value *= 1.01
        points.append(
            CategoryMonthlyData(
                category_id="Y",
                date=datetime.date(year, month, day),
                value=value,
                return_pct=1.0,
                partial=False,
            )
        )
    returns = category_period_returns(points)
    expected_2y = ((1.01**24) - 1.0) * 100.0
    assert abs(returns["2y"] - expected_2y) < 1e-9
    assert returns["3y"] is None


def test_ranking_endpoint_returns_multi_horizon_columns(tmp_path, monkeypatch):
    db_path = tmp_path / "portfolio.db"
    monkeypatch.setattr("portfolio.storage.database.DEFAULT_DB_PATH", db_path)
    monkeypatch.setattr("portfolio.api.api.init_db", lambda: init_db(db_path))
    init_db(db_path)

    with get_session(db_path) as session:
        session.merge(
            Category(
                category_id="TESTEQ1",
                name="Test Equity A",
                fund_id="F00000AAAA",
                performance_id="0P0000AAAA",
                asset_class="equity",
            )
        )
        session.merge(
            Category(
                category_id="TESTBD1",
                name="Test Bond A",
                fund_id="F00000CCCC",
                performance_id="0P0000CCCC",
                asset_class="bond",
            )
        )
        session.commit()

    merge_category_monthly_data(
        "TESTEQ1",
        [
            (datetime.date(2026, 6, 30), 100.0),
            (datetime.date(2026, 7, 31), 110.0),
            (datetime.date(2026, 8, 31), 121.0),
            (datetime.date(2026, 9, 15), 123.42),
        ],
        db_path=db_path,
    )
    merge_category_monthly_data(
        "TESTBD1",
        [
            (datetime.date(2026, 7, 31), 100.0),
            (datetime.date(2026, 8, 31), 101.0),
        ],
        db_path=db_path,
    )

    client = TestClient(app)
    body = client.get("/api/categories/ranking").json()
    assert body["as_of"] == "2026-09-15"
    assert len(body["categories"]) == 2
    assert body["categories"][0]["name"] == "Test Equity A"
    assert body["categories"][0]["fund_id"] == "F00000AAAA"
    assert body["categories"][0]["performance_id"] == "0P0000AAAA"
    returns = body["categories"][0]["returns"]
    assert abs(returns["intramonth"] - 2.0) < 1e-6
    assert abs(returns["1m"] - 10.0) < 1e-9
    assert abs(returns["2m"] - 21.0) < 1e-9
    assert body["categories"][1]["returns"]["intramonth"] is None
    assert abs(body["categories"][1]["returns"]["1m"] - 1.0) < 1e-9


def test_ranking_endpoint_empty_when_no_monthly_data(tmp_path, monkeypatch):
    db_path = tmp_path / "portfolio.db"
    monkeypatch.setattr("portfolio.storage.database.DEFAULT_DB_PATH", db_path)
    monkeypatch.setattr("portfolio.api.api.init_db", lambda: init_db(db_path))
    init_db(db_path)

    client = TestClient(app)
    response = client.get("/api/categories/ranking")
    assert response.status_code == 200
    assert response.json() == {"as_of": None, "categories": []}
