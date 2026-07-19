from pydantic import BaseModel


class SeriesItem(BaseModel):
    code: str
    label: str | None = None
    description: str
    value: float
    threshold: float | None = None
    active: bool | None = None
    identifier: str | None = None
    source_url: str | None = None
    series_start: str | None = None
    domain: str | None = None


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
    context_values: list[AlertHistoryCell] = []
    active_count: int = 0
    eligible_count: int = 0


class AlertHistoryColumn(BaseModel):
    code: str
    label: str
    description: str
    series_start: str | None = None
    identifier: str | None = None
    source_url: str | None = None
    threshold: float | None = None
    operator: str | None = None
    domain: str | None = None


class AlertHistory(BaseModel):
    columns: list[AlertHistoryColumn] = []
    context_columns: list[AlertHistoryColumn] = []
    rows: list[AlertHistoryRow] = []


class AlertSnapshotResponse(BaseModel):
    date: str | None = None
    series: list[SeriesItem] = []
    context: list[SeriesItem] = []
    alerts: list[AlertItem] = []
    history: AlertHistory = AlertHistory()
