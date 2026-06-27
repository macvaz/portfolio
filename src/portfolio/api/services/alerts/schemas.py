from pydantic import BaseModel


class SeriesItem(BaseModel):
    code: str
    description: str
    value: float
    threshold: float | None = None
    active: bool | None = None
    identifier: str | None = None
    source_url: str | None = None


class AlertItem(BaseModel):
    code: str
    description: str
    value: float
    threshold: float
    active: bool
    identifier: str | None = None
    source_url: str | None = None


class AlertHistoryCell(BaseModel):
    value: float | None = None
    active: bool | None = None


class AlertHistoryRow(BaseModel):
    month: str
    values: list[AlertHistoryCell]
    active_count: int = 0


class AlertHistoryColumn(BaseModel):
    code: str
    description: str


class AlertHistory(BaseModel):
    columns: list[AlertHistoryColumn] = []
    rows: list[AlertHistoryRow] = []


class AlertSnapshotResponse(BaseModel):
    date: str | None = None
    series: list[SeriesItem] = []
    alerts: list[AlertItem] = []
    history: AlertHistory = AlertHistory()
