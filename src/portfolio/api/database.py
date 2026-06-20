from collections.abc import Generator
from pathlib import Path

from sqlalchemy import text
from sqlmodel import Session, SQLModel, create_engine, delete, select

from portfolio.api.models import Fund, Portfolio, User

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


def init_db(db_path: Path | None = None) -> None:
    path = _resolve_db_path(db_path)
    engine = get_engine(path)
    SQLModel.metadata.create_all(engine)
    _migrate_legacy_funds_table(db_path)


def create_user(
    email: str, hashed_password: str, db_path: Path | None = None
) -> User:
    init_db(db_path)
    with get_session(db_path) as session:
        user = User(email=email, hashed_password=hashed_password)
        session.add(user)
        session.commit()
        session.refresh(user)
        return user


def get_fund(isin: str, db_path: Path | None = None) -> dict | None:
    init_db(db_path)
    with get_session(db_path) as session:
        fund = session.get(Fund, isin)
    if fund is None:
        return None
    return {"isin": fund.isin, "name": fund.name, "security_id": fund.fund_id}


def list_funds(db_path: Path | None = None) -> list[dict]:
    init_db(db_path)
    with get_session(db_path) as session:
        funds = session.exec(select(Fund).order_by(Fund.name)).all()
    return [{"isin": fund.isin, "name": fund.name, "fund_id": fund.fund_id} for fund in funds]


def save_fund(
    isin: str, name: str, fund_id: str, db_path: Path | None = None
) -> None:
    init_db(db_path)
    with get_session(db_path) as session:
        session.merge(Fund(isin=isin, name=name, fund_id=fund_id))
        session.commit()


def delete_fund(isin: str, db_path: Path | None = None) -> bool:
    init_db(db_path)
    with get_session(db_path) as session:
        fund = session.get(Fund, isin)
        if fund is None:
            return False
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
