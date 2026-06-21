from sqlmodel import Field, SQLModel, UniqueConstraint


class User(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True)
    hashed_password: str


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
