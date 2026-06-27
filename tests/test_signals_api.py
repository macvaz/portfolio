import datetime

from fastapi.testclient import TestClient

from portfolio.api.api import app
from portfolio.api.database import init_db, upsert_alerts
from portfolio.common.alert_descriptions import is_alert_active


def test_is_alert_active_uses_threshold_direction():
    assert is_alert_active(1.2, 1.0, "gte") is True
    assert is_alert_active(0.8, 1.0, "gte") is False
    assert is_alert_active(-0.05, 0.0, "lt") is True
    assert is_alert_active(0.12, 0.0, "lt") is False
    assert is_alert_active(0.98, 1.0, "lt") is True
    assert is_alert_active(4800.0, None, None) is None


def test_list_alerts_returns_latest_snapshot(tmp_path, monkeypatch):
    db_path = tmp_path / "portfolio.db"
    monkeypatch.setattr("portfolio.api.database.DEFAULT_DB_PATH", db_path)
    monkeypatch.setattr("portfolio.api.api.init_db", lambda: init_db(db_path))
    init_db(db_path)

    observation_date = datetime.date(2024, 6, 4)
    upsert_alerts(
        {
            "Unemployment_Rate": 3.8,
            "High_Yield_Spread": 3.25,
            "Financial_Stress_Index": 1.2,
            "Yield_Spread_10Y3M": -0.05,
            "Real_Interest_Rates": 2.1,
            "SP500_Death_Cross": 0.94,
            "Sahm_Rule_Indicator": 0.32,
        },
        observation_date,
        db_path,
    )

    client = TestClient(app)
    response = client.get("/api/alerts")

    assert response.status_code == 200
    payload = response.json()
    assert payload["date"] == "2024-06-04"
    assert "history" in payload
    assert isinstance(payload["history"]["columns"], list)
    assert isinstance(payload["history"]["rows"], list)
    assert len(payload["series"]) == 6
    assert len(payload["alerts"]) == 7

    series_codes = {item["code"] for item in payload["series"]}
    assert series_codes == {
        "Unemployment_Rate",
        "High_Yield_Spread",
        "Financial_Stress_Index",
        "Yield_Spread_10Y3M",
        "Real_Interest_Rates",
        "Sahm_Rule_Indicator",
    }
    assert "SP500_Death_Cross" not in series_codes

    alerts_by_code = {item["code"]: item for item in payload["alerts"]}
    assert alerts_by_code["SP500_Death_Cross"]["active"] is True
    assert alerts_by_code["Yield_Spread_10Y3M"]["active"] is True
    assert alerts_by_code["Unemployment_Rate"]["active"] is False

    unemployment = next(
        item for item in payload["series"] if item["code"] == "Unemployment_Rate"
    )
    assert unemployment["threshold"] == 5.0
    assert unemployment["series_start"] == "1990-01-01"
    assert unemployment["active"] is False

    active_codes = {item["code"] for item in payload["alerts"] if item["active"]}
    assert active_codes == {
        "SP500_Death_Cross",
        "Financial_Stress_Index",
        "Real_Interest_Rates",
        "Yield_Spread_10Y3M",
    }


def test_list_alerts_returns_empty_snapshot_when_no_data(tmp_path, monkeypatch):
    db_path = tmp_path / "portfolio.db"
    monkeypatch.setattr("portfolio.api.database.DEFAULT_DB_PATH", db_path)
    monkeypatch.setattr("portfolio.api.api.init_db", lambda: init_db(db_path))
    init_db(db_path)

    client = TestClient(app)
    response = client.get("/api/alerts")

    assert response.status_code == 200
    payload = response.json()
    assert payload["date"] is None
    assert payload["series"] == []
    assert payload["alerts"] == []
    assert "columns" in payload["history"]
    assert "rows" in payload["history"]
