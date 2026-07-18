import datetime

from sqlmodel import Field, SQLModel, UniqueConstraint


class User(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(unique=True, index=True)
    is_default: bool = Field(default=False)


class Fund(SQLModel, table=True):
    isin: str = Field(primary_key=True)
    name: str
    fund_id: str
    performance_id: str | None = None
    universe: str | None = None


class Metric(SQLModel, table=True):
    isin: str = Field(primary_key=True, foreign_key="fund.isin")
    beta_6m: float | None = None
    cor_6m: float | None = None
    vol_1y: float | None = None
    pct_1w: float | None = None
    pct_2w: float | None = None
    pct_1m: float | None = None
    pct_3m: float | None = None
    pct_6m: float | None = None
    pct_ytd: float | None = None
    sr_6m: float | None = None
    sr_1y: float | None = None


class Portfolio(SQLModel, table=True):
    __tablename__ = "portfolio"
    __table_args__ = (UniqueConstraint("user_id", "isin"),)

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    isin: str = Field(foreign_key="fund.isin", index=True)
    weighted_assets: float


class AlertDescription(SQLModel, table=True):
    __tablename__ = "alert_description"

    code: str = Field(primary_key=True)
    description: str
    source: str = Field(default="fred", index=True)
    series_id: str | None = Field(default=None, index=True)
    series_start: datetime.date | None = None
    threshold: float | None = None
    operator: str | None = None


class Alert(SQLModel, table=True):
    __tablename__ = "alert"
    __table_args__ = (UniqueConstraint("code", "date"),)

    id: int | None = Field(default=None, primary_key=True)
    code: str = Field(foreign_key="alert_description.code", index=True)
    date: datetime.date = Field(index=True)
    value: float
