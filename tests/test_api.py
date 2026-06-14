from fastapi.testclient import TestClient

from portfolio.api.app import app
from portfolio.api.database import init_db, save_fund


def _register_and_login(client: TestClient, email: str, password: str) -> str:
    client.post(
        "/api/auth/register",
        json={"email": email, "password": password},
    )
    response = client.post(
        "/api/auth/token",
        data={"username": email, "password": password},
    )
    return response.json()["access_token"]


def test_list_and_delete_funds(tmp_path, monkeypatch):
    db_path = tmp_path / "portfolio.db"
    monkeypatch.setattr("portfolio.api.database.DEFAULT_DB_PATH", db_path)
    monkeypatch.setattr("portfolio.api.app.init_db", lambda: init_db(db_path))
    init_db(db_path)
    save_fund("ES0182527038", "Test Fund", "F0GBR04KHC", db_path)

    client = TestClient(app)
    token = _register_and_login(client, "user@example.com", "secretpass")
    headers = {"Authorization": f"Bearer {token}"}

    response = client.get("/api/funds", headers=headers)
    assert response.status_code == 200
    assert response.json() == [
        {
            "isin": "ES0182527038",
            "name": "Test Fund",
            "fund_id": "F0GBR04KHC",
        }
    ]

    delete_response = client.delete("/api/funds/ES0182527038", headers=headers)
    assert delete_response.status_code == 204
    assert client.get("/api/funds", headers=headers).json() == []


def test_create_report_rejects_empty_portfolio(tmp_path, monkeypatch):
    db_path = tmp_path / "portfolio.db"
    monkeypatch.setattr("portfolio.api.database.DEFAULT_DB_PATH", db_path)

    client = TestClient(app)
    token = _register_and_login(client, "user@example.com", "secretpass")
    headers = {"Authorization": f"Bearer {token}"}

    response = client.post("/api/report", json={"positions": []}, headers=headers)
    assert response.status_code == 400


def test_save_and_load_user_portfolio(tmp_path, monkeypatch):
    db_path = tmp_path / "portfolio.db"
    monkeypatch.setattr("portfolio.api.database.DEFAULT_DB_PATH", db_path)
    monkeypatch.setattr("portfolio.api.app.init_db", lambda: init_db(db_path))
    init_db(db_path)
    save_fund("ES0182527038", "Test Fund", "F0GBR04KHC", db_path)
    save_fund("IE00BYX5NX33", "World Fund", "F00001019E", db_path)

    client = TestClient(app)
    token = _register_and_login(client, "user@example.com", "secretpass")
    headers = {"Authorization": f"Bearer {token}"}

    save_response = client.put(
        "/api/portfolio",
        headers=headers,
        json={
            "positions": [
                {"isin": "ES0182527038", "weighted_assets": 0.35},
                {"isin": "IE00BYX5NX33", "weighted_assets": 0.65},
            ]
        },
    )
    assert save_response.status_code == 200
    assert save_response.json() == [
        {
            "isin": "ES0182527038",
            "name": "Test Fund",
            "fund_id": "F0GBR04KHC",
            "weighted_assets": 0.35,
        },
        {
            "isin": "IE00BYX5NX33",
            "name": "World Fund",
            "fund_id": "F00001019E",
            "weighted_assets": 0.65,
        },
    ]

    load_response = client.get("/api/portfolio", headers=headers)
    assert load_response.status_code == 200
    assert load_response.json() == save_response.json()
