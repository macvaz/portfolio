from collections.abc import Generator
from pathlib import Path

from sqlalchemy import text
from sqlmodel import Session, SQLModel, create_engine, delete, select

from portfolio.api.models import Fund, Metric, Portfolio, User

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
            row[1]
            for row in connection.execute(text("PRAGMA table_info(fund)"))
        }
        if "performance_id" not in columns:
            connection.execute(
                text("ALTER TABLE fund ADD COLUMN performance_id TEXT")
            )
            connection.commit()


def _migrate_fund_universe(db_path: Path | None = None) -> None:
    """Add ``universe`` to ``fund`` when upgrading an existing database."""
    engine = get_engine(db_path)
    with engine.connect() as connection:
        columns = {
            row[1]
            for row in connection.execute(text("PRAGMA table_info(fund)"))
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
            row[1]
            for row in connection.execute(text("PRAGMA table_info(user)"))
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
            row[1]
            for row in connection.execute(text("PRAGMA table_info(user)"))
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
            row[1]
            for row in connection.execute(text("PRAGMA table_info(user)"))
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
    return [{"id": user.id, "name": user.name, "is_default": user.is_default} for user in users]


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


def get_fund_metrics(
    isin: str, db_path: Path | None = None
) -> dict[str, float | None]:
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


def list_user_portfolio(
    user_id: int, db_path: Path | None = None
) -> list[dict]:
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
