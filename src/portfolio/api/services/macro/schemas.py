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


class MacroItem(BaseModel):
    code: str
    description: str
    value: float
    threshold: float
    active: bool
    identifier: str | None = None
    source_url: str | None = None


class MacroHistoryCell(BaseModel):
    value: float | None = None
    active: bool | None = None


class MacroHistoryRow(BaseModel):
    month: str
    values: list[MacroHistoryCell]
    context_values: list[MacroHistoryCell] = []
    active_count: int = 0
    eligible_count: int = 0


class MacroHistoryColumn(BaseModel):
    code: str
    label: str
    description: str
    series_start: str | None = None
    identifier: str | None = None
    source_url: str | None = None
    threshold: float | None = None
    operator: str | None = None
    domain: str | None = None


class MacroHistory(BaseModel):
    columns: list[MacroHistoryColumn] = []
    context_columns: list[MacroHistoryColumn] = []
    rows: list[MacroHistoryRow] = []


class MacroSnapshotResponse(BaseModel):
    date: str | None = None
    series: list[SeriesItem] = []
    context: list[SeriesItem] = []
    items: list[MacroItem] = []
    history: MacroHistory = MacroHistory()
