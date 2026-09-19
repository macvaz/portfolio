from contextlib import asynccontextmanager
import logging
import os
from pathlib import Path

# Non-root containers often have no writable HOME; avoid Matplotlib writing to /.config.
Path(os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib")).mkdir(
    parents=True, exist_ok=True
)

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from portfolio.api.services.management.router import router as management_router
from portfolio.api.services.macro.router import router as macro_router
from portfolio.api.services.risk.router import router as risk_router
from portfolio.api.services.categories.router import router as categories_router
from portfolio.common.navs import DEFAULT_FUNDS_DIR, fund_nav_path
from portfolio.logging_config import configure_logging
from portfolio.storage.database import init_db, list_funds

WEB_DIR = Path(__file__).resolve().parents[3] / "html"
logger = logging.getLogger(__name__)


def _log_missing_fund_navs() -> None:
    """Startup breadcrumb: restart never deletes CSVs; log if any are already gone."""
    missing = [
        f"{fund['isin']} ({fund['name']})"
        for fund in list_funds()
        if not fund_nav_path(fund["isin"]).exists()
    ]
    funds_dir = DEFAULT_FUNDS_DIR.resolve()
    if missing:
        logger.warning(
            "Missing %s fund NAV CSV(s) under %s at startup: %s",
            len(missing),
            funds_dir,
            ", ".join(missing),
        )
    else:
        logger.info("All fund NAV CSVs present under %s", funds_dir)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    _log_missing_fund_navs()
    yield


app = FastAPI(title="Portfolio API", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")


@app.get("/")
def index() -> FileResponse:
    return FileResponse(WEB_DIR / "index.html")


app.include_router(management_router)
app.include_router(risk_router)
app.include_router(macro_router)
app.include_router(categories_router)


def main() -> None:
    import uvicorn

    configure_logging()
    host = os.getenv("PORTFOLIO_HOST", "127.0.0.1")
    port = int(os.getenv("PORTFOLIO_PORT", "8000"))
    reload = os.getenv("PORTFOLIO_RELOAD", "0") == "1"
    uvicorn.run(
        "portfolio.api.api:app",
        host=host,
        port=port,
        reload=reload,
    )
