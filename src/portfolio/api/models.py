from sqlmodel import Field, SQLModel, UniqueConstraint


class User(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True)
    hashed_password: str


class Fund(SQLModel, table=True):
    isin: str = Field(primary_key=True)
    name: str
    fund_id: str


class Portfolio(SQLModel, table=True):
    __tablename__ = "portfolio"
    __table_args__ = (UniqueConstraint("user_id", "isin"),)

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    isin: str = Field(foreign_key="fund.isin", index=True)
    weighted_assets: float
