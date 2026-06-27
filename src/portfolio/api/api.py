from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from portfolio.api.database import init_db
from portfolio.api.services.portfolio.router import router as portfolio_router
from portfolio.api.services.alerts.router import router as alerts_router

WEB_DIR = Path(__file__).resolve().parents[3] / "html"


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Portfolio API", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")


@app.get("/")
def index() -> FileResponse:
    return FileResponse(WEB_DIR / "index.html")


app.include_router(portfolio_router)
app.include_router(alerts_router)


def main() -> None:
    import uvicorn

    uvicorn.run("portfolio.api.api:app", host="0.0.0.0", port=8000, reload=True)
