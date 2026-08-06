from collections.abc import Generator
import datetime
import html
from pathlib import Path

from sqlalchemy import event, func
from sqlmodel import Session, SQLModel, create_engine, delete, select

from portfolio.storage.models import MacroHealthCheck, MacroHealthCheckDescription, Fund, Metric, Portfolio, User
from portfolio.storage.fixtures.macro_health_checks import (
    insert_health_check_descriptions_from_fixture,
    sync_health_check_catalog_from_fixture,
)
from portfolio.storage.fixtures.funds import sync_funds_from_fixture
from portfolio.common.health_check_descriptions import (
    HEALTH_CHECK_ROLE,
    health_check_label,
    is_health_check_active,
)

# Current SQLite schema version. Older in-place migrations were removed;
# create tables from SQLModel metadata and sync fixture catalogs.
SCHEMA_VERSION = "1.0"

CANONICAL_DB_PATH = Path("data/portfolio.db")
DEFAULT_DB_PATH = CANONICAL_DB_PATH

_engines: dict[str, object] = {}
_initialized_paths: set[str] = set()


def _resolve_db_path(db_path: Path | None) -> Path:
    return db_path or DEFAULT_DB_PATH


def _configure_sqlite_connection(dbapi_connection, _connection_record) -> None:
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA busy_timeout=5000")
    cursor.close()


def get_engine(db_path: Path | None = None):
    path = _resolve_db_path(db_path)
    key = str(path.resolve())
    if key not in _engines:
        path.parent.mkdir(parents=True, exist_ok=True)
        engine = create_engine(
            f"sqlite:///{path}",
            connect_args={"check_same_thread": False},
        )
        event.listen(engine, "connect", _configure_sqlite_connection)
        _engines[key] = engine
    return _engines[key]


def get_session(db_path: Path | None = None) -> Session:
    return Session(get_engine(db_path))


def get_db(db_path: Path | None = None) -> Generator[Session, None, None]:
    with get_session(db_path) as session:
        yield session


def reset_health_check_tables_from_fixture(
    db_path: Path | None = None,
    fixture_path: Path | None = None,
) -> None:
    """Clear health-check data and reload catalog from the JSON fixture."""
    path = _resolve_db_path(db_path)
    engine = get_engine(path)
    SQLModel.metadata.create_all(engine)

    with get_session(db_path) as session:
        session.exec(delete(MacroHealthCheck))
        session.exec(delete(MacroHealthCheckDescription))
        session.commit()
        insert_health_check_descriptions_from_fixture(session, fixture_path)
        session.commit()


def init_db(db_path: Path | None = None) -> None:
    """Create schema 1.0 tables if needed, then sync fixture catalogs."""
    path = _resolve_db_path(db_path)
    key = str(path.resolve())
    if key not in _initialized_paths:
        engine = get_engine(path)
        SQLModel.metadata.create_all(engine)
        _initialized_paths.add(key)

    with get_session(db_path) as session:
        sync_health_check_catalog_from_fixture(session)
        sync_funds_from_fixture(session)
        session.commit()


def create_user(name: str, db_path: Path | None = None) -> User:
    with get_session(db_path) as session:
        user = User(name=name)
        session.add(user)
        session.commit()
        session.refresh(user)
        return user


def get_user(user_id: int, db_path: Path | None = None) -> User | None:
    with get_session(db_path) as session:
        return session.get(User, user_id)


def list_users(db_path: Path | None = None) -> list[dict]:
    with get_session(db_path) as session:
        users = session.exec(select(User).order_by(User.name)).all()
    return [
        {"id": user.id, "name": user.name, "is_default": user.is_default}
        for user in users
    ]


def delete_user(user_id: int, db_path: Path | None = None) -> bool:
    with get_session(db_path) as session:
        user = session.get(User, user_id)
        if user is None:
            return False
        session.exec(delete(Portfolio).where(Portfolio.user_id == user_id))
        session.delete(user)
        session.commit()
        return True


def set_default_user(user_id: int, db_path: Path | None = None) -> dict | None:
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
        "ter": fund.ter,
    }


def list_funds(db_path: Path | None = None) -> list[dict]:
    with get_session(db_path) as session:
        funds = session.exec(select(Fund).order_by(Fund.name)).all()
    return [
        {
            "isin": fund.isin,
            "name": fund.name,
            "fund_id": fund.fund_id,
            "performance_id": fund.performance_id,
            "universe": fund.universe,
            "ter": fund.ter,
        }
        for fund in funds
    ]


def save_fund(
    isin: str,
    name: str,
    fund_id: str,
    performance_id: str | None = None,
    universe: str | None = None,
    ter: float | None = None,
    db_path: Path | None = None,
) -> None:
    isin = isin.upper()
    with get_session(db_path) as session:
        existing = session.get(Fund, isin)
        if existing is not None:
            if performance_id is None:
                performance_id = existing.performance_id
            if universe is None:
                universe = existing.universe
            if ter is None:
                ter = existing.ter
        session.merge(
            Fund(
                isin=isin,
                name=html.unescape(name),
                fund_id=fund_id,
                performance_id=performance_id,
                universe=universe,
                ter=ter,
            )
        )
        session.commit()


def get_fund_metrics(isin: str, db_path: Path | None = None) -> dict[str, float | None]:
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


def upsert_health_checks(
    values: dict[str, float],
    observation_date: datetime.date,
    db_path: Path | None = None,
) -> None:
    with get_session(db_path) as session:
        for code, value in values.items():
            existing = session.exec(
                select(MacroHealthCheck).where(
                    MacroHealthCheck.code == code,
                    MacroHealthCheck.date == observation_date,
                )
            ).first()
            if existing is None:
                session.add(
                    MacroHealthCheck(code=code, date=observation_date, value=value)
                )
            else:
                existing.value = value
                session.add(existing)
        session.commit()


def _series_item_from_description(
    description: MacroHealthCheckDescription,
    value: float,
) -> dict:
    identifier = description.series_id
    source_url = (
        f"https://fred.stlouisfed.org/series/{identifier}"
        if description.source == "fred" and identifier
        else None
    )
    active = is_health_check_active(
        value, description.threshold, description.operator
    )
    return {
        "code": description.code,
        "label": health_check_label(description.code),
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
        "domain": description.domain,
    }


def get_latest_health_checks(db_path: Path | None = None) -> dict | None:
    with get_session(db_path) as session:
        latest_date = session.exec(select(func.max(MacroHealthCheck.date))).one()
        if latest_date is None:
            return None

        stored = session.exec(
            select(MacroHealthCheck).where(MacroHealthCheck.date == latest_date)
        ).all()
        descriptions = session.exec(select(MacroHealthCheckDescription)).all()

    values_by_code = {row.code: row.value for row in stored}
    series: list[dict] = []
    context: list[dict] = []
    items: list[dict] = []

    for description in descriptions:
        value = values_by_code.get(description.code)
        if value is None:
            continue

        role = getattr(description, "role", HEALTH_CHECK_ROLE) or HEALTH_CHECK_ROLE
        item = _series_item_from_description(description, value)

        if role == "context":
            if description.source == "fred":
                context.append(item)
            continue

        if description.source == "fred":
            series.append(item)

        if item["active"] is not None:
            items.append(
                {
                    "code": item["code"],
                    "description": item["description"],
                    "value": item["value"],
                    "threshold": item["threshold"],
                    "active": item["active"],
                    "identifier": item["identifier"],
                    "source_url": item["source_url"],
                }
            )

    series.sort(key=lambda item: item.get("label") or item["code"])
    context.sort(key=lambda item: item.get("label") or item["code"])
    items.sort(
        key=lambda item: (not item["active"], item.get("identifier") or item["code"])
    )

    return {
        "date": latest_date.isoformat(),
        "series": series,
        "context": context,
        "items": items,
    }


def delete_fund(isin: str, db_path: Path | None = None) -> bool:
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
            "ter": fund.ter,
            "weighted_assets": position.weighted_assets,
        }
        for position, fund in rows
    ]


def save_user_portfolio(
    user_id: int, positions: list[dict[str, float | str]], db_path: Path | None = None
) -> list[dict]:
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
