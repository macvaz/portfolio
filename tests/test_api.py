from fastapi.testclient import TestClient

from portfolio.api.app import app
from portfolio.api.database import create_user, get_fund_metrics, init_db, save_fund, save_fund_metrics


def _create_user(db_path, name: str = "Growth") -> int:
    init_db(db_path)
    return create_user(name, db_path=db_path).id


def test_list_and_delete_funds(tmp_path, monkeypatch):
    db_path = tmp_path / "portfolio.db"
    monkeypatch.setattr("portfolio.api.database.DEFAULT_DB_PATH", db_path)
    monkeypatch.setattr("portfolio.api.app.init_db", lambda: init_db(db_path))
    init_db(db_path)
    save_fund("ES0182527038", "Test Fund", "F0GBR04KHC", db_path=db_path)

    client = TestClient(app)
    user_id = _create_user(db_path)

    response = client.get("/api/funds")
    assert response.status_code == 200
    assert response.json() == [
        {
            "isin": "ES0182527038",
            "name": "Test Fund",
            "fund_id": "F0GBR04KHC",
            "morningstar_url": None,
        }
    ]

    delete_response = client.delete("/api/funds/ES0182527038")
    assert delete_response.status_code == 204
    assert client.get("/api/funds").json() == []


def test_create_report_rejects_empty_portfolio(tmp_path, monkeypatch):
    db_path = tmp_path / "portfolio.db"
    monkeypatch.setattr("portfolio.api.database.DEFAULT_DB_PATH", db_path)
    monkeypatch.setattr("portfolio.api.app.init_db", lambda: init_db(db_path))

    client = TestClient(app)
    user_id = _create_user(db_path)

    response = client.post("/api/report", params={"portfolio_id": user_id}, json={"positions": []})
    assert response.status_code == 400


def test_get_report_rejects_empty_portfolio(tmp_path, monkeypatch):
    db_path = tmp_path / "portfolio.db"
    monkeypatch.setattr("portfolio.api.database.DEFAULT_DB_PATH", db_path)
    monkeypatch.setattr("portfolio.api.app.init_db", lambda: init_db(db_path))

    client = TestClient(app)
    user_id = _create_user(db_path)

    response = client.get("/api/report", params={"portfolio_id": user_id})
    assert response.status_code == 400
    assert response.json()["detail"] == "Portfolio is empty"


def test_get_report_returns_quantstats_html(tmp_path, monkeypatch):
    db_path = tmp_path / "portfolio.db"
    funds_dir = tmp_path / "funds"
    monkeypatch.setattr("portfolio.api.database.DEFAULT_DB_PATH", db_path)
    monkeypatch.setattr("portfolio.api.app.init_db", lambda: init_db(db_path))
    monkeypatch.setattr("portfolio.finance.nav_files.DEFAULT_FUNDS_DIR", funds_dir)
    init_db(db_path)
    save_fund("ES0182527038", "Test Fund", "F0GBR04KHC", db_path=db_path)

    import pandas as pd
    from portfolio.finance.nav_files import save_fund_nav_csv

    df = pd.DataFrame(
        {"value": [100.0, 101.0, 102.0, 103.0, 104.0]},
        index=pd.to_datetime(["2024-01-01", "2024-01-02", "2024-01-03", "2024-01-04", "2024-01-05"]),
    )
    save_fund_nav_csv("ES0182527038", df, funds_dir=funds_dir)
    save_fund_nav_csv("IE00BYX5MX67", df, funds_dir=funds_dir)

    client = TestClient(app)
    user_id = _create_user(db_path)

    client.put(
        "/api/portfolio",
        params={"portfolio_id": user_id},
        json={"positions": [{"isin": "ES0182527038", "weighted_assets": 1.0}]},
    )

    def mock_report_html(portfolio_returns, benchmark_returns):
        assert benchmark_returns.name == "S&P 500"
        return "<html><body>QuantStats report</body></html>"

    monkeypatch.setattr(
        "portfolio.api.report.generate_performance_report_html",
        mock_report_html,
    )

    response = client.get("/api/report", params={"portfolio_id": user_id})
    assert response.status_code == 200
    assert "QuantStats report" in response.text


def test_create_fund_downloads_nav_to_data(tmp_path, monkeypatch):
    db_path = tmp_path / "portfolio.db"
    funds_dir = tmp_path / "funds"
    monkeypatch.setattr("portfolio.api.database.DEFAULT_DB_PATH", db_path)
    monkeypatch.setattr("portfolio.api.app.init_db", lambda: init_db(db_path))
    monkeypatch.setattr("portfolio.finance.nav_files.DEFAULT_FUNDS_DIR", funds_dir)

    def mock_resolve(isin, db_path=None):
        return {
            "isin": isin,
            "name": "Test Fund",
            "security_id": "F0GBR04KHC",
            "performance_id": "0P000068Z4",
            "universe": "FO",
        }

    def mock_download(fund_id, currency, start, end, timeout=30):
        import pandas as pd

        return pd.DataFrame(
            {"value": [100.0, 101.0]},
            index=pd.to_datetime(["2024-01-01", "2024-01-02"]),
        )

    monkeypatch.setattr("portfolio.api.app.resolve_fund_by_isin", mock_resolve)
    monkeypatch.setattr(
        "portfolio.finance.nav_files.download_fund_navs",
        mock_download,
    )

    client = TestClient(app)

    response = client.post(
        "/api/funds",
        json={"isin": "ES0182527038"},
    )
    assert response.status_code == 200
    assert response.json() == {
        "isin": "ES0182527038",
        "name": "Test Fund",
        "fund_id": "F0GBR04KHC",
        "morningstar_url": (
            "https://global.morningstar.com/es/inversiones/fondos/0P000068Z4/cotizacion"
        ),
    }
    nav_path = funds_dir / "ES0182527038.csv"
    assert nav_path.exists()
    assert nav_path.read_text(encoding="utf-8").startswith("date,nav\n")
    metrics = get_fund_metrics("ES0182527038", db_path)
    assert metrics["pct_1w"] == 1.0


def test_curve_endpoint_returns_real_equity_curve(tmp_path, monkeypatch):
    db_path = tmp_path / "portfolio.db"
    funds_dir = tmp_path / "funds"
    monkeypatch.setattr("portfolio.api.database.DEFAULT_DB_PATH", db_path)
    monkeypatch.setattr("portfolio.api.app.init_db", lambda: init_db(db_path))
    monkeypatch.setattr("portfolio.finance.nav_files.DEFAULT_FUNDS_DIR", funds_dir)
    init_db(db_path)
    save_fund("ES0182527038", "Test Fund", "F0GBR04KHC", db_path=db_path)
    save_fund("IE00BYX5NX33", "World Fund", "F00001019E", db_path=db_path)

    import pandas as pd
    from portfolio.finance.nav_files import save_fund_nav_csv

    df = pd.DataFrame(
        {"value": [100.0, 110.0, 121.0]},
        index=pd.to_datetime(["2024-01-31", "2024-02-29", "2024-03-31"]),
    )
    save_fund_nav_csv("ES0182527038", df, funds_dir=funds_dir)
    save_fund_nav_csv("IE00BYX5NX33", df, funds_dir=funds_dir)

    client = TestClient(app)
    user_id = _create_user(db_path)

    client.put(
        "/api/portfolio",
        params={"portfolio_id": user_id},
        json={
            "positions": [
                {"isin": "ES0182527038", "weighted_assets": 0.5},
                {"isin": "IE00BYX5NX33", "weighted_assets": 0.5},
            ]
        },
    )

    response = client.get("/api/curve", params={"portfolio_id": user_id})
    assert response.status_code == 200
    data = response.json()
    assert data["portfolio"][0] == 0.0
    assert len(data["labels"]) >= 2
    assert data["benchmark"] == []


def test_dashboard_portfolio_uses_real_user_weights(tmp_path, monkeypatch):
    db_path = tmp_path / "portfolio.db"
    monkeypatch.setattr("portfolio.api.database.DEFAULT_DB_PATH", db_path)
    monkeypatch.setattr("portfolio.api.app.init_db", lambda: init_db(db_path))
    monkeypatch.setattr(
        "portfolio.api.mock_management.resolve_fund_by_isin",
        lambda isin, db_path=None: None,
    )
    init_db(db_path)
    save_fund("ES0182527038", "Test Fund", "F0GBR04KHC", db_path=db_path)
    save_fund("IE00BYX5NX33", "World Fund", "F00001019E", db_path=db_path)
    save_fund_metrics(
        "ES0182527038",
        {
            "beta_6m": 0.05,
            "cor_6m": 0.19,
            "vol_1y": 3.44,
            "pct_1w": 0.5,
            "pct_2w": 1.1,
            "pct_1m": 2.30,
            "pct_3m": -0.56,
            "pct_6m": 2.49,
            "pct_ytd": 5.43,
            "sr_6m": 1.58,
            "sr_1y": 1.67,
        },
        db_path,
    )

    client = TestClient(app)
    user_id = _create_user(db_path)

    client.put(
        "/api/portfolio",
        params={"portfolio_id": user_id},
        json={
            "positions": [
                {"isin": "ES0182527038", "weighted_assets": 0.35},
                {"isin": "IE00BYX5NX33", "weighted_assets": 0.65},
            ]
        },
    )

    response = client.get("/api/dashboard", params={"portfolio_id": user_id})
    assert response.status_code == 200
    data = response.json()

    assert len(data["portfolio"]) == 2
    assert data["portfolio"][0]["isin"] == "ES0182527038"
    assert data["portfolio"][0]["name"] == "Test Fund"
    assert data["portfolio"][0]["weight"] == 35.0
    assert data["portfolio"][1]["isin"] == "IE00BYX5NX33"
    assert data["portfolio"][1]["weight"] == 65.0
    assert data["portfolio_summary"]["weight"] == 100.0
    assert data["portfolio"][0]["beta_6m"] == 0.05
    assert data["favorites"] == []


def test_dashboard_favorites_use_real_db_funds_not_in_portfolio(tmp_path, monkeypatch):
    db_path = tmp_path / "portfolio.db"
    monkeypatch.setattr("portfolio.api.database.DEFAULT_DB_PATH", db_path)
    monkeypatch.setattr("portfolio.api.app.init_db", lambda: init_db(db_path))
    monkeypatch.setattr(
        "portfolio.api.mock_management.resolve_fund_by_isin",
        lambda isin, db_path=None: None,
    )
    init_db(db_path)
    save_fund("ES0182527038", "Test Fund", "F0GBR04KHC", db_path=db_path)
    save_fund("IE00BYX5NX33", "World Fund", "F00001019E", db_path=db_path)
    save_fund("IE00BYX5M476", "Emerging Markets", "F00001020E", db_path=db_path)

    client = TestClient(app)
    user_id = _create_user(db_path)

    client.put(
        "/api/portfolio",
        params={"portfolio_id": user_id},
        json={
            "positions": [
                {"isin": "ES0182527038", "weighted_assets": 1.0},
            ]
        },
    )

    response = client.get("/api/dashboard", params={"portfolio_id": user_id})
    data = response.json()

    assert len(data["portfolio"]) == 1
    assert data["portfolio"][0]["isin"] == "ES0182527038"
    assert len(data["favorites"]) == 2
    favorite_isins = {fund["isin"] for fund in data["favorites"]}
    assert favorite_isins == {"IE00BYX5NX33", "IE00BYX5M476"}
    assert all(fund["weight"] == 0.0 for fund in data["favorites"])
    assert data["favorites"][0]["name"] in {"World Fund", "Emerging Markets"}


def test_save_portfolio_allows_partial_weights(tmp_path, monkeypatch):
    db_path = tmp_path / "portfolio.db"
    monkeypatch.setattr("portfolio.api.database.DEFAULT_DB_PATH", db_path)
    monkeypatch.setattr("portfolio.api.app.init_db", lambda: init_db(db_path))
    init_db(db_path)
    save_fund("ES0182527038", "Test Fund", "F0GBR04KHC", db_path=db_path)

    client = TestClient(app)
    user_id = _create_user(db_path)

    response = client.put(
        "/api/portfolio",
        params={"portfolio_id": user_id},
        json={"positions": [{"isin": "ES0182527038", "weighted_assets": 0.35}]},
    )
    assert response.status_code == 200
    assert response.json()[0]["weighted_assets"] == 0.35


def test_save_and_load_user_portfolio(tmp_path, monkeypatch):
    db_path = tmp_path / "portfolio.db"
    monkeypatch.setattr("portfolio.api.database.DEFAULT_DB_PATH", db_path)
    monkeypatch.setattr("portfolio.api.app.init_db", lambda: init_db(db_path))
    init_db(db_path)
    save_fund("ES0182527038", "Test Fund", "F0GBR04KHC", db_path=db_path)
    save_fund("IE00BYX5NX33", "World Fund", "F00001019E", db_path=db_path)

    client = TestClient(app)
    user_id = _create_user(db_path)

    save_response = client.put(
        "/api/portfolio",
        params={"portfolio_id": user_id},
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
            "performance_id": None,
            "universe": None,
            "weighted_assets": 0.35,
        },
        {
            "isin": "IE00BYX5NX33",
            "name": "World Fund",
            "fund_id": "F00001019E",
            "performance_id": None,
            "universe": None,
            "weighted_assets": 0.65,
        },
    ]

    load_response = client.get("/api/portfolio", params={"portfolio_id": user_id})
    assert load_response.status_code == 200
    assert load_response.json() == save_response.json()
