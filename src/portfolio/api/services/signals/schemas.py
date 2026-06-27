from pydantic import BaseModel


class SignalItem(BaseModel):
    code: str
    description: str
    threshold: float | None
    value: float
    identifier: str | None = None
    source_url: str | None = None


class SignalSnapshotResponse(BaseModel):
    date: str | None = None
    series: list[SignalItem] = []
    alerts_activated: list[SignalItem] = []
    alerts_deactivated: list[SignalItem] = []
