import datetime

from fastapi.testclient import TestClient

from portfolio.api.api import app
from portfolio.api.database import init_db, upsert_signals
from portfolio.common.signal_dimensions import is_alert_active


def test_is_alert_active_uses_threshold_direction():
    assert is_alert_active("INVERTED_CURVE", -0.05, 0.0) is True
    assert is_alert_active("INVERTED_CURVE", 0.12, 0.0) is False
    assert is_alert_active("FINANCIAL_STRESS", 1.2, 1.0) is True
    assert is_alert_active("SAHM_RULE", 0.32, 0.5) is False
    assert is_alert_active("SP500_DEATH_CROSS_ACTIVE", 0.98, 1.0) is True
    assert is_alert_active("SP500_CONFIRMED_DEATH_CROSS", 0.94, 0.95) is True


def test_list_signals_returns_latest_snapshot(tmp_path, monkeypatch):
    db_path = tmp_path / "portfolio.db"
    monkeypatch.setattr("portfolio.api.database.DEFAULT_DB_PATH", db_path)
    monkeypatch.setattr("portfolio.api.api.init_db", lambda: init_db(db_path))
    init_db(db_path)

    observation_date = datetime.date(2024, 6, 4)
    upsert_signals(
        {
            "Unemployment_Rate": 3.8,
            "High_Yield_Spread": 3.25,
            "Financial_Stress_Index": 1.2,
            "Yield_Spread_10Y3M": -0.05,
            "SP500": 4800.0,
            "SP500_SMA_RATIO": 0.94,
            "SAHM_RULE": 0.32,
            "INVERTED_CURVE": 1.0,
            "FINANCIAL_STRESS": 1.0,
            "MACRO_CRISIS_VOTES": 2.0,
            "MACRO_SYSTEM_LOCKED": 1.0,
            "SP500_DEATH_CROSS_ACTIVE": 1.0,
            "SP500_CONFIRMED_DEATH_CROSS": 1.0,
        },
        observation_date,
        db_path,
    )

    client = TestClient(app)
    response = client.get("/api/signals")

    assert response.status_code == 200
    payload = response.json()
    assert payload["date"] == "2024-06-04"
    assert len(payload["series"]) == 5

    activated_codes = {item["code"] for item in payload["alerts_activated"]}
    deactivated_codes = {item["code"] for item in payload["alerts_deactivated"]}

    assert activated_codes == {
        "FINANCIAL_STRESS",
        "INVERTED_CURVE",
        "MACRO_CRISIS_VOTES",
        "MACRO_SYSTEM_LOCKED",
        "SP500_CONFIRMED_DEATH_CROSS",
        "SP500_DEATH_CROSS_ACTIVE",
    }
    assert deactivated_codes == {"SAHM_RULE"}

    inverted_curve = next(
        item
        for item in payload["alerts_activated"]
        if item["code"] == "INVERTED_CURVE"
    )
    assert inverted_curve["value"] == -0.05
    assert inverted_curve["threshold"] == 0.0

    sahm = next(
        item for item in payload["alerts_deactivated"] if item["code"] == "SAHM_RULE"
    )
    assert sahm["value"] == 0.32
    assert sahm["threshold"] == 0.5


def test_list_signals_returns_empty_snapshot_when_no_data(tmp_path, monkeypatch):
    db_path = tmp_path / "portfolio.db"
    monkeypatch.setattr("portfolio.api.database.DEFAULT_DB_PATH", db_path)
    monkeypatch.setattr("portfolio.api.api.init_db", lambda: init_db(db_path))
    init_db(db_path)

    client = TestClient(app)
    response = client.get("/api/signals")

    assert response.status_code == 200
    assert response.json() == {
        "date": None,
        "series": [],
        "alerts_activated": [],
        "alerts_deactivated": [],
    }
