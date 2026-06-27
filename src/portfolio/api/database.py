from collections.abc import Generator
import datetime
from pathlib import Path

from sqlalchemy import func, text
from sqlmodel import Session, SQLModel, create_engine, delete, select

from portfolio.api.models import Alert, AlertDescription, Fund, Metric, Portfolio, User
from portfolio.common.alert_descriptions import (
    insert_alert_descriptions_from_fixture,
    sync_alert_catalog_from_fixture,
)

CANONICAL_DB_PATH = Path("data/portfolio.db")
DEFAULT_DB_PATH = CANONICAL_DB_PATH

_engines: dict[str, object] = {}


def _resolve_db_path(db_path: Path | None) -> Path:
    return db_path or DEFAULT_DB_PATH


def get_engine(db_path: Path | None = None):
    path = _resolve_db_path(db_path)
    key = str(path.resolve())
    if key not in _engines:
        path.parent.mkdir(parents=True, exist_ok=True)
        _engines[key] = create_engine(
            f"sqlite:///{path}",
            connect_args={"check_same_thread": False},
        )
    return _engines[key]


def get_session(db_path: Path | None = None) -> Session:
    return Session(get_engine(db_path))


def get_db(db_path: Path | None = None) -> Generator[Session, None, None]:
    init_db(db_path)
    with get_session(db_path) as session:
        yield session


def _migrate_legacy_funds_table(db_path: Path | None = None) -> None:
    """Move rows from the legacy ``funds`` table into ``fund``."""
    engine = get_engine(db_path)
    with engine.connect() as connection:
        tables = {
            row[0]
            for row in connection.execute(
                text("SELECT name FROM sqlite_master WHERE type='table'")
            )
        }
        if "funds" not in tables:
            return

        rows = connection.execute(
            text("SELECT isin, name, fund_id FROM funds")
        ).fetchall()
        if rows:
            for isin, name, fund_id in rows:
                connection.execute(
                    text(
                        "INSERT OR IGNORE INTO fund (isin, name, fund_id) "
                        "VALUES (:isin, :name, :fund_id)"
                    ),
                    {"isin": isin, "name": name, "fund_id": fund_id},
                )
        connection.execute(text("DROP TABLE funds"))
        connection.commit()


def _migrate_fund_performance_id(db_path: Path | None = None) -> None:
    """Add ``performance_id`` to ``fund`` when upgrading an existing database."""
    engine = get_engine(db_path)
    with engine.connect() as connection:
        columns = {
            row[1] for row in connection.execute(text("PRAGMA table_info(fund)"))
        }
        if "performance_id" not in columns:
            connection.execute(text("ALTER TABLE fund ADD COLUMN performance_id TEXT"))
            connection.commit()


def _migrate_fund_universe(db_path: Path | None = None) -> None:
    """Add ``universe`` to ``fund`` when upgrading an existing database."""
    engine = get_engine(db_path)
    with engine.connect() as connection:
        columns = {
            row[1] for row in connection.execute(text("PRAGMA table_info(fund)"))
        }
        if "universe" not in columns:
            connection.execute(text("ALTER TABLE fund ADD COLUMN universe TEXT"))
            connection.commit()


def _migrate_drop_user_password(db_path: Path | None = None) -> None:
    """Remove ``hashed_password`` from ``user`` when upgrading an existing database."""
    engine = get_engine(db_path)
    with engine.connect() as connection:
        tables = {
            row[0]
            for row in connection.execute(
                text("SELECT name FROM sqlite_master WHERE type='table'")
            )
        }
        if "user" not in tables:
            return

        columns = {
            row[1] for row in connection.execute(text("PRAGMA table_info(user)"))
        }
        if "hashed_password" not in columns:
            return

        connection.execute(
            text(
                "CREATE TABLE user_new ("
                "id INTEGER NOT NULL PRIMARY KEY, "
                "email VARCHAR NOT NULL"
                ")"
            )
        )
        connection.execute(
            text("INSERT INTO user_new (id, email) SELECT id, email FROM user")
        )
        connection.execute(text("DROP TABLE user"))
        connection.execute(text("ALTER TABLE user_new RENAME TO user"))
        connection.execute(
            text("CREATE UNIQUE INDEX IF NOT EXISTS ix_user_email ON user (email)")
        )
        connection.commit()


def _migrate_user_email_to_name(db_path: Path | None = None) -> None:
    """Rename ``email`` to ``name`` on ``user`` when upgrading an existing database."""
    engine = get_engine(db_path)
    with engine.connect() as connection:
        tables = {
            row[0]
            for row in connection.execute(
                text("SELECT name FROM sqlite_master WHERE type='table'")
            )
        }
        if "user" not in tables:
            return

        columns = {
            row[1] for row in connection.execute(text("PRAGMA table_info(user)"))
        }
        if "name" in columns or "email" not in columns:
            return

        connection.execute(text("ALTER TABLE user RENAME COLUMN email TO name"))
        connection.execute(text("DROP INDEX IF EXISTS ix_user_email"))
        connection.execute(
            text("CREATE UNIQUE INDEX IF NOT EXISTS ix_user_name ON user (name)")
        )
        connection.commit()


def _migrate_user_is_default(db_path: Path | None = None) -> None:
    """Add ``is_default`` to ``user`` and set Miguel_Agresiva as the default portfolio."""
    engine = get_engine(db_path)
    with engine.connect() as connection:
        tables = {
            row[0]
            for row in connection.execute(
                text("SELECT name FROM sqlite_master WHERE type='table'")
            )
        }
        if "user" not in tables:
            return

        columns = {
            row[1] for row in connection.execute(text("PRAGMA table_info(user)"))
        }
        if "is_default" not in columns:
            connection.execute(
                text(
                    "ALTER TABLE user ADD COLUMN is_default BOOLEAN NOT NULL DEFAULT 0"
                )
            )
            connection.execute(
                text("UPDATE user SET is_default = 1 WHERE name = 'Miguel_Agresiva'")
            )
            connection.commit()


def _migrate_signal_dimension_metadata(db_path: Path | None = None) -> None:
    """Add ``kind`` and nullable ``threshold`` to ``signal_dimension`` when upgrading."""
    engine = get_engine(db_path)
    with engine.connect() as connection:
        tables = {
            row[0]
            for row in connection.execute(
                text("SELECT name FROM sqlite_master WHERE type='table'")
            )
        }
        if "signal_dimension" not in tables:
            return

        columns = {
            row[1]: row[3]
            for row in connection.execute(text("PRAGMA table_info(signal_dimension)"))
        }
        if "kind" in columns and columns.get("threshold") == 0:
            return

        connection.execute(
            text(
                "CREATE TABLE signal_dimension_new ("
                "code VARCHAR NOT NULL PRIMARY KEY, "
                "description VARCHAR NOT NULL, "
                "threshold REAL, "
                "kind VARCHAR NOT NULL DEFAULT 'alert'"
                ")"
            )
        )
        connection.execute(
            text(
                "INSERT INTO signal_dimension_new (code, description, threshold, kind) "
                "SELECT code, description, threshold, 'alert' FROM signal_dimension"
            )
        )
        connection.execute(text("DROP TABLE signal_dimension"))
        connection.execute(
            text("ALTER TABLE signal_dimension_new RENAME TO signal_dimension")
        )
        connection.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_signal_dimension_kind "
                "ON signal_dimension (kind)"
            )
        )
        connection.commit()


def _migrate_signal_dimension_series_id(db_path: Path | None = None) -> None:
    """Add ``series_id`` to ``signal_dimension`` when upgrading an existing database."""
    engine = get_engine(db_path)
    with engine.connect() as connection:
        tables = {
            row[0]
            for row in connection.execute(
                text("SELECT name FROM sqlite_master WHERE type='table'")
            )
        }
        if "signal_dimension" not in tables:
            return

        columns = {
            row[1] for row in connection.execute(text("PRAGMA table_info(signal_dimension)"))
        }
        if "series_id" in columns:
            return

        connection.execute(
            text("ALTER TABLE signal_dimension ADD COLUMN series_id VARCHAR")
        )
        connection.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_signal_dimension_series_id "
                "ON signal_dimension (series_id)"
            )
        )
        connection.commit()


SIGNAL_CODE_RENAMES = {
    "Alert_Inverted_Curve": "Yield_Spread_10Y3M",
    "Alert_Financial_Stress": "Financial_Stress_Index",
    "Sahm_Value": "Sahm_Rule_Indicator",
    "SAHM_VALUE": "Sahm_Rule_Indicator",
    "SAHM_RULE": "Sahm_Rule_Indicator",
    "INVERTED_CURVE": "Yield_Spread_10Y3M",
    "FINANCIAL_STRESS": "Financial_Stress_Index",
    "HIGH_YIELD_SPREAD": "High_Yield_Spread",
    "UNEMPLOYMENT_RATE": "Unemployment_Rate",
    "UNEMPLOYMENT_HIGH": "Unemployment_Rate",
    "REAL_RATES": "Real_Interest_Rates",
    "REAL_YIELD_HIGH": "Real_Interest_Rates",
    "Real_Yield_10Y": "Real_Interest_Rates",
    "SP500_Death_Cross_Active": "SP500_Death_Cross",
    "SP500_DEATH_CROSS_ACTIVE": "SP500_Death_Cross",
    "SP500_Confirmed_Death_Cross": "SP500_Death_Cross",
    "SP500_CONFIRMED_DEATH_CROSS": "SP500_Death_Cross",
    "DEATH_CROSS": "SP500_Death_Cross",
}


def _migrate_signal_alert_codes(db_path: Path | None = None) -> None:
    """Rename legacy alert codes to the uppercase convention without ``Alert_``."""
    engine = get_engine(db_path)
    with engine.connect() as connection:
        tables = {
            row[0]
            for row in connection.execute(
                text("SELECT name FROM sqlite_master WHERE type='table'")
            )
        }
        if "signal_dimension" not in tables:
            return

        connection.execute(text("PRAGMA foreign_keys = OFF"))
        for old_code, new_code in SIGNAL_CODE_RENAMES.items():
            old_exists = connection.execute(
                text("SELECT 1 FROM signal_dimension WHERE code = :code"),
                {"code": old_code},
            ).fetchone()
            if old_exists is None:
                continue

            new_exists = connection.execute(
                text("SELECT 1 FROM signal_dimension WHERE code = :code"),
                {"code": new_code},
            ).fetchone()

            if new_exists is not None:
                old_signals = connection.execute(
                    text("SELECT id, date FROM signal WHERE code = :code"),
                    {"code": old_code},
                ).fetchall()
                for signal_id, signal_date in old_signals:
                    duplicate = connection.execute(
                        text(
                            "SELECT 1 FROM signal "
                            "WHERE code = :new_code AND date = :signal_date"
                        ),
                        {"new_code": new_code, "signal_date": signal_date},
                    ).fetchone()
                    if duplicate is not None:
                        connection.execute(
                            text("DELETE FROM signal WHERE id = :signal_id"),
                            {"signal_id": signal_id},
                        )
                    else:
                        connection.execute(
                            text("UPDATE signal SET code = :new_code WHERE id = :id"),
                            {"new_code": new_code, "id": signal_id},
                        )
                connection.execute(
                    text("DELETE FROM signal_dimension WHERE code = :code"),
                    {"code": old_code},
                )
                continue

            connection.execute(
                text("UPDATE signal SET code = :new_code WHERE code = :old_code"),
                {"old_code": old_code, "new_code": new_code},
            )
            connection.execute(
                text(
                    "UPDATE signal_dimension SET code = :new_code "
                    "WHERE code = :old_code"
                ),
                {"old_code": old_code, "new_code": new_code},
            )
        connection.execute(text("PRAGMA foreign_keys = ON"))
        connection.commit()


def _migrate_signal_dimension_comparison_code(db_path: Path | None = None) -> None:
    """Add ``comparison_code`` to ``signal_dimension`` when upgrading."""
    engine = get_engine(db_path)
    with engine.connect() as connection:
        tables = {
            row[0]
            for row in connection.execute(
                text("SELECT name FROM sqlite_master WHERE type='table'")
            )
        }
        if "signal_dimension" not in tables:
            return

        columns = {
            row[1] for row in connection.execute(text("PRAGMA table_info(signal_dimension)"))
        }
        if "comparison_code" in columns:
            return

        connection.execute(
            text("ALTER TABLE signal_dimension ADD COLUMN comparison_code VARCHAR")
        )
        connection.commit()


def _migrate_signal_dimension_unified(db_path: Path | None = None) -> None:
    """Add ``source`` and ``operator`` to ``signal_dimension`` when upgrading."""
    engine = get_engine(db_path)
    with engine.connect() as connection:
        tables = {
            row[0]
            for row in connection.execute(
                text("SELECT name FROM sqlite_master WHERE type='table'")
            )
        }
        if "signal_dimension" not in tables:
            return

        columns = {
            row[1]
            for row in connection.execute(text("PRAGMA table_info(signal_dimension)"))
        }
        if "source" not in columns:
            connection.execute(
                text(
                    "ALTER TABLE signal_dimension "
                    "ADD COLUMN source VARCHAR NOT NULL DEFAULT 'fred'"
                )
            )
        if "operator" not in columns:
            connection.execute(
                text("ALTER TABLE signal_dimension ADD COLUMN operator VARCHAR")
            )
        connection.commit()


def _migrate_alert_description_unified(db_path: Path | None = None) -> None:
    """Add ``source`` and ``operator`` to ``alert_description`` when upgrading."""
    engine = get_engine(db_path)
    with engine.connect() as connection:
        tables = {
            row[0]
            for row in connection.execute(
                text("SELECT name FROM sqlite_master WHERE type='table'")
            )
        }
        if "alert_description" not in tables:
            return

        columns = {
            row[1]
            for row in connection.execute(text("PRAGMA table_info(alert_description)"))
        }
        if "source" not in columns:
            connection.execute(
                text(
                    "ALTER TABLE alert_description "
                    "ADD COLUMN source VARCHAR NOT NULL DEFAULT 'fred'"
                )
            )
        if "operator" not in columns:
            connection.execute(
                text("ALTER TABLE alert_description ADD COLUMN operator VARCHAR")
            )
        if "series_start" not in columns:
            connection.execute(
                text("ALTER TABLE alert_description ADD COLUMN series_start DATE")
            )
        connection.commit()


def _migrate_rename_signal_tables_to_alert(db_path: Path | None = None) -> None:
    """Rename legacy ``signal`` tables to ``alert`` / ``alert_description``."""
    engine = get_engine(db_path)
    with engine.connect() as connection:
        tables = {
            row[0]
            for row in connection.execute(
                text("SELECT name FROM sqlite_master WHERE type='table'")
            )
        }
        if "signal_dimension" in tables and "alert_description" in tables:
            connection.execute(text("DROP TABLE alert_description"))
            connection.execute(
                text("ALTER TABLE signal_dimension RENAME TO alert_description")
            )
        elif "signal_dimension" in tables:
            connection.execute(
                text("ALTER TABLE signal_dimension RENAME TO alert_description")
            )
        if "signal" in tables and "alert" in tables:
            connection.execute(text("DROP TABLE alert"))
            connection.execute(text("ALTER TABLE signal RENAME TO alert"))
        elif "signal" in tables:
            connection.execute(text("ALTER TABLE signal RENAME TO alert"))
        connection.commit()


def _migrate_sahm_rule_indicator_alerts(db_path: Path | None = None) -> None:
    """Copy legacy SAHM_RULE readings into ``Sahm_Rule_Indicator`` when missing."""
    with get_session(db_path) as session:
        legacy_rows = session.exec(
            select(Alert).where(Alert.code == "SAHM_RULE")
        ).all()
        for legacy in legacy_rows:
            existing = session.exec(
                select(Alert).where(
                    Alert.code == "Sahm_Rule_Indicator",
                    Alert.date == legacy.date,
                )
            ).first()
            if existing is not None:
                continue
            session.add(
                Alert(
                    code="Sahm_Rule_Indicator",
                    date=legacy.date,
                    value=legacy.value,
                )
            )
        session.commit()


def reset_alert_tables_from_fixture(
    db_path: Path | None = None,
    fixture_path: Path | None = None,
) -> None:
    """Clear alert data and reload ``alert_description`` from the JSON fixture."""
    path = _resolve_db_path(db_path)
    engine = get_engine(path)
    SQLModel.metadata.create_all(engine)

    with get_session(db_path) as session:
        session.exec(delete(Alert))
        session.exec(delete(AlertDescription))
        session.commit()
        insert_alert_descriptions_from_fixture(session, fixture_path)
        session.commit()


def init_db(db_path: Path | None = None) -> None:
    path = _resolve_db_path(db_path)
    engine = get_engine(path)
    SQLModel.metadata.create_all(engine)
    _migrate_legacy_funds_table(db_path)
    _migrate_fund_performance_id(db_path)
    _migrate_fund_universe(db_path)
    _migrate_drop_user_password(db_path)
    _migrate_user_email_to_name(db_path)
    _migrate_user_is_default(db_path)
    _migrate_signal_dimension_metadata(db_path)
    _migrate_signal_dimension_series_id(db_path)
    _migrate_signal_alert_codes(db_path)
    _migrate_signal_dimension_comparison_code(db_path)
    _migrate_signal_dimension_unified(db_path)
    _migrate_rename_signal_tables_to_alert(db_path)
    _migrate_alert_description_unified(db_path)
    with get_session(db_path) as session:
        sync_alert_catalog_from_fixture(session)
        session.commit()
    _migrate_sahm_rule_indicator_alerts(db_path)


def create_user(name: str, db_path: Path | None = None) -> User:
    init_db(db_path)
    with get_session(db_path) as session:
        user = User(name=name)
        session.add(user)
        session.commit()
        session.refresh(user)
        return user


def get_user(user_id: int, db_path: Path | None = None) -> User | None:
    init_db(db_path)
    with get_session(db_path) as session:
        return session.get(User, user_id)


def list_users(db_path: Path | None = None) -> list[dict]:
    init_db(db_path)
    with get_session(db_path) as session:
        users = session.exec(select(User).order_by(User.name)).all()
    return [
        {"id": user.id, "name": user.name, "is_default": user.is_default}
        for user in users
    ]


def delete_user(user_id: int, db_path: Path | None = None) -> bool:
    init_db(db_path)
    with get_session(db_path) as session:
        user = session.get(User, user_id)
        if user is None:
            return False
        session.exec(delete(Portfolio).where(Portfolio.user_id == user_id))
        session.delete(user)
        session.commit()
        return True


def set_default_user(user_id: int, db_path: Path | None = None) -> dict | None:
    init_db(db_path)
    with get_session(db_path) as session:
        user = session.get(User, user_id)
        if user is None:
            return None
        for existing in session.exec(select(User)).all():
            existing.is_default = existing.id == user_id
            session.add(existing)
        session.commit()
        session.refresh(user)
        return {"id": user.id, "name": user.name, "is_default": user.is_default}


def get_fund(isin: str, db_path: Path | None = None) -> dict | None:
    init_db(db_path)
    with get_session(db_path) as session:
        fund = session.get(Fund, isin)
    if fund is None:
        return None
    return {
        "isin": fund.isin,
        "name": fund.name,
        "security_id": fund.fund_id,
        "performance_id": fund.performance_id,
        "universe": fund.universe,
    }


def list_funds(db_path: Path | None = None) -> list[dict]:
    init_db(db_path)
    with get_session(db_path) as session:
        funds = session.exec(select(Fund).order_by(Fund.name)).all()
    return [
        {
            "isin": fund.isin,
            "name": fund.name,
            "fund_id": fund.fund_id,
            "performance_id": fund.performance_id,
            "universe": fund.universe,
        }
        for fund in funds
    ]


def save_fund(
    isin: str,
    name: str,
    fund_id: str,
    performance_id: str | None = None,
    universe: str | None = None,
    db_path: Path | None = None,
) -> None:
    init_db(db_path)
    isin = isin.upper()
    with get_session(db_path) as session:
        existing = session.get(Fund, isin)
        if existing is not None:
            if performance_id is None:
                performance_id = existing.performance_id
            if universe is None:
                universe = existing.universe
        session.merge(
            Fund(
                isin=isin,
                name=name,
                fund_id=fund_id,
                performance_id=performance_id,
                universe=universe,
            )
        )
        session.commit()


def get_fund_metrics(isin: str, db_path: Path | None = None) -> dict[str, float | None]:
    init_db(db_path)
    with get_session(db_path) as session:
        metric = session.get(Metric, isin.upper())
    if metric is None:
        return {
            "beta_6m": None,
            "cor_6m": None,
            "vol_1y": None,
            "pct_1w": None,
            "pct_2w": None,
            "pct_1m": None,
            "pct_3m": None,
            "pct_6m": None,
            "pct_ytd": None,
            "sr_6m": None,
            "sr_1y": None,
        }
    return {
        "beta_6m": metric.beta_6m,
        "cor_6m": metric.cor_6m,
        "vol_1y": metric.vol_1y,
        "pct_1w": metric.pct_1w,
        "pct_2w": metric.pct_2w,
        "pct_1m": metric.pct_1m,
        "pct_3m": metric.pct_3m,
        "pct_6m": metric.pct_6m,
        "pct_ytd": metric.pct_ytd,
        "sr_6m": metric.sr_6m,
        "sr_1y": metric.sr_1y,
    }


def save_fund_metrics(
    isin: str,
    metrics: dict[str, float | None],
    db_path: Path | None = None,
) -> None:
    init_db(db_path)
    isin = isin.upper()
    with get_session(db_path) as session:
        session.merge(
            Metric(
                isin=isin,
                beta_6m=metrics.get("beta_6m"),
                cor_6m=metrics.get("cor_6m"),
                vol_1y=metrics.get("vol_1y"),
                pct_1w=metrics.get("pct_1w"),
                pct_2w=metrics.get("pct_2w"),
                pct_1m=metrics.get("pct_1m"),
                pct_3m=metrics.get("pct_3m"),
                pct_6m=metrics.get("pct_6m"),
                pct_ytd=metrics.get("pct_ytd"),
                sr_6m=metrics.get("sr_6m"),
                sr_1y=metrics.get("sr_1y"),
            )
        )
        session.commit()


def upsert_alerts(
    alerts: dict[str, float],
    observation_date: datetime.date,
    db_path: Path | None = None,
) -> None:
    with get_session(db_path) as session:
        for code, value in alerts.items():
            existing = session.exec(
                select(Alert).where(
                    Alert.code == code,
                    Alert.date == observation_date,
                )
            ).first()
            if existing is None:
                session.add(
                    Alert(code=code, date=observation_date, value=value)
                )
            else:
                existing.value = value
                session.add(existing)
        session.commit()


from portfolio.common.alert_descriptions import is_alert_active


def get_latest_alerts(db_path: Path | None = None) -> dict | None:
    init_db(db_path)
    with get_session(db_path) as session:
        latest_date = session.exec(select(func.max(Alert.date))).one()
        if latest_date is None:
            return None

        stored_alerts = session.exec(
            select(Alert).where(Alert.date == latest_date)
        ).all()
        descriptions = session.exec(select(AlertDescription)).all()

    values_by_code = {alert.code: alert.value for alert in stored_alerts}
    series: list[dict] = []
    alerts: list[dict] = []

    for description in descriptions:
        value = values_by_code.get(description.code)
        if value is None:
            continue

        active = is_alert_active(
            value, description.threshold, description.operator
        )
        identifier = description.series_id
        source_url = (
            f"https://fred.stlouisfed.org/series/{identifier}"
            if description.source == "fred" and identifier
            else None
        )

        if description.source == "fred":
            series.append(
                {
                    "code": description.code,
                    "description": description.description,
                    "value": value,
                    "threshold": description.threshold,
                    "active": active,
                    "identifier": identifier,
                    "source_url": source_url,
                    "series_start": (
                        description.series_start.isoformat()
                        if description.series_start
                        else None
                    ),
                }
            )

        if active is not None:
            alerts.append(
                {
                    "code": description.code,
                    "description": description.description,
                    "value": value,
                    "threshold": description.threshold,
                    "active": active,
                    "identifier": identifier,
                    "source_url": source_url,
                }
            )

    series.sort(key=lambda item: item.get("identifier") or item["code"])
    alerts.sort(
        key=lambda item: (not item["active"], item.get("identifier") or item["code"])
    )

    return {
        "date": latest_date.isoformat(),
        "series": series,
        "alerts": alerts,
    }


def delete_fund(isin: str, db_path: Path | None = None) -> bool:
    init_db(db_path)
    isin = isin.upper()
    with get_session(db_path) as session:
        fund = session.get(Fund, isin)
        if fund is None:
            return False
        session.exec(delete(Portfolio).where(Portfolio.isin == isin))
        metric = session.get(Metric, isin)
        if metric is not None:
            session.delete(metric)
        session.delete(fund)
        session.commit()
    return True


def list_user_portfolio(user_id: int, db_path: Path | None = None) -> list[dict]:
    init_db(db_path)
    with get_session(db_path) as session:
        rows = session.exec(
            select(Portfolio, Fund)
            .join(Fund, Portfolio.isin == Fund.isin)
            .where(Portfolio.user_id == user_id)
            .order_by(Fund.name)
        ).all()
    return [
        {
            "isin": fund.isin,
            "name": fund.name,
            "fund_id": fund.fund_id,
            "performance_id": fund.performance_id,
            "universe": fund.universe,
            "weighted_assets": position.weighted_assets,
        }
        for position, fund in rows
    ]


def save_user_portfolio(
    user_id: int, positions: list[dict[str, float | str]], db_path: Path | None = None
) -> list[dict]:
    init_db(db_path)
    with get_session(db_path) as session:
        session.exec(delete(Portfolio).where(Portfolio.user_id == user_id))
        for position in positions:
            session.add(
                Portfolio(
                    user_id=user_id,
                    isin=str(position["isin"]).upper(),
                    weighted_assets=float(position["weighted_assets"]),
                )
            )
        session.commit()
    return list_user_portfolio(user_id, db_path)
