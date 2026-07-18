from portfolio.storage.database import get_latest_alerts
from portfolio.api.services.alerts.schemas import AlertHistory, AlertSnapshotResponse
from portfolio.api.services.alerts.history import build_monthly_alert_history


def fetch_latest_alert_snapshot() -> AlertSnapshotResponse:
    history_payload = build_monthly_alert_history()
    history = AlertHistory(**history_payload)
    snapshot = get_latest_alerts()
    if snapshot is None:
        return AlertSnapshotResponse(date=None, series=[], alerts=[], history=history)
    return AlertSnapshotResponse(**snapshot, history=history)
