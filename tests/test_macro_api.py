import datetime

from fastapi.testclient import TestClient

from portfolio.api.api import app
from portfolio.storage.database import init_db, upsert_health_checks
from portfolio.common.health_check_descriptions import is_health_check_active


def test_is_health_check_active_uses_threshold_direction():
    assert is_health_check_active(1.2, 1.0, "gte") is True
    assert is_health_check_active(0.8, 1.0, "gte") is False
    assert is_health_check_active(-0.05, 0.0, "lt") is True
    assert is_health_check_active(0.12, 0.0, "lt") is False
    assert is_health_check_active(0.98, 1.0, "lt") is True
    assert is_health_check_active(4800.0, None, None) is None


def test_get_macro_returns_latest_snapshot(tmp_path, monkeypatch):
    db_path = tmp_path / "portfolio.db"
    monkeypatch.setattr("portfolio.storage.database.DEFAULT_DB_PATH", db_path)
    monkeypatch.setattr("portfolio.api.api.init_db", lambda: init_db(db_path))
    init_db(db_path)

    observation_date = datetime.date(2024, 6, 4)
    upsert_health_checks(
        {
            "Unemployment_Rate": 3.8,
            "High_Yield_Spread": 3.25,
            "Financial_Stress_Index": 1.2,
            "Yield_Spread_10Y3M": -0.05,
            "Real_Interest_Rates": 2.1,
            "SP500_Death_Cross": 0.94,
            "Breakeven_Inflation": 2.3,
            "Treasury_10Y_Yield": 4.3,
            "SOFR": 5.3,
        },
        observation_date,
        db_path,
    )

    client = TestClient(app)
    response = client.get("/api/macro")

    assert response.status_code == 200
    payload = response.json()
    assert payload["date"] == "2024-06-04"
    assert "history" in payload
    assert isinstance(payload["history"]["columns"], list)
    assert isinstance(payload["history"]["context_columns"], list)
    assert isinstance(payload["history"]["rows"], list)
    assert len(payload["series"]) == 6
    assert len(payload["items"]) == 7
    assert "Treasury_10Y_Yield" not in {item["code"] for item in payload["series"]}
    assert "SOFR" not in {item["code"] for item in payload["items"]}

    context_codes = {item["code"] for item in payload["context"]}
    assert context_codes == {"Treasury_10Y_Yield", "SOFR"}
    assert "Treasury_10Y_Yield" not in {item["code"] for item in payload["items"]}
    sofr = next(item for item in payload["context"] if item["code"] == "SOFR")
    assert sofr["label"] == "SOFR"
    assert sofr["identifier"] == "SOFR"
    assert sofr["value"] == 5.3
    assert sofr["active"] is None
    treasury = next(
        item for item in payload["context"] if item["code"] == "Treasury_10Y_Yield"
    )
    assert treasury["threshold"] == 4.5
    assert treasury["value"] == 4.3
    assert treasury["active"] is False

    history_context_codes = [
        column["code"] for column in payload["history"]["context_columns"]
    ]
    assert history_context_codes == [
        "Treasury_10Y_Yield",
        "Broad_Dollar_Index",
        "Reserve_Balances",
        "Overnight_RRP",
        "SOFR",
    ]
    assert all("context_values" in row for row in payload["history"]["rows"])

    series_codes = {item["code"] for item in payload["series"]}
    assert series_codes == {
        "Unemployment_Rate",
        "High_Yield_Spread",
        "Financial_Stress_Index",
        "Yield_Spread_10Y3M",
        "Real_Interest_Rates",
        "Breakeven_Inflation",
    }
    assert "SP500_Death_Cross" not in series_codes

    items_by_code = {item["code"]: item for item in payload["items"]}
    assert items_by_code["SP500_Death_Cross"]["active"] is True
    assert items_by_code["Yield_Spread_10Y3M"]["active"] is True
    assert items_by_code["Unemployment_Rate"]["active"] is False

    unemployment = next(
        item for item in payload["series"] if item["code"] == "Unemployment_Rate"
    )
    assert unemployment["threshold"] == 5.0
    assert unemployment["series_start"] == "1990-01-01"
    assert unemployment["active"] is False
    assert unemployment["label"] == "Unemployment rate"

    breakeven = next(
        item for item in payload["series"] if item["code"] == "Breakeven_Inflation"
    )
    assert breakeven["label"] == "Breakeven inflation"
    assert breakeven["identifier"] == "T10YIE"

    active_codes = {item["code"] for item in payload["items"] if item["active"]}
    assert active_codes == {
        "SP500_Death_Cross",
        "Financial_Stress_Index",
        "Real_Interest_Rates",
        "Yield_Spread_10Y3M",
    }


def test_get_macro_returns_empty_snapshot_when_no_data(tmp_path, monkeypatch):
    db_path = tmp_path / "portfolio.db"
    monkeypatch.setattr("portfolio.storage.database.DEFAULT_DB_PATH", db_path)
    monkeypatch.setattr("portfolio.api.api.init_db", lambda: init_db(db_path))
    init_db(db_path)

    client = TestClient(app)
    response = client.get("/api/macro")

    assert response.status_code == 200
    payload = response.json()
    assert payload["date"] is None
    assert payload["series"] == []
    assert payload["context"] == []
    assert payload["items"] == []
    assert "columns" in payload["history"]
    assert "context_columns" in payload["history"]
    assert "rows" in payload["history"]
