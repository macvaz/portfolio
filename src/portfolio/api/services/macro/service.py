from portfolio.storage.database import get_latest_health_checks
from portfolio.api.services.macro.schemas import MacroHistory, MacroSnapshotResponse
from portfolio.api.services.macro.history import build_monthly_macro_history


def fetch_latest_macro_snapshot() -> MacroSnapshotResponse:
    history_payload = build_monthly_macro_history()
    history = MacroHistory(**history_payload)
    snapshot = get_latest_health_checks()
    if snapshot is None:
        return MacroSnapshotResponse(
            date=None,
            series=[],
            context=[],
            items=[],
            history=history,
        )
    return MacroSnapshotResponse(
        date=snapshot.get("date"),
        series=snapshot.get("series") or [],
        context=snapshot.get("context") or [],
        items=snapshot.get("items") or [],
        history=history,
    )
