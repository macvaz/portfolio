# Portfolio

Python system (API + batch jobs) to download and process mutual fund prices from Morningstar and macroeconomic series from FRED. It allows creating different investment portfolios while computing returns and risk reports. Additionally, it evaluates low-frequency macro health checks to detect real worsening of economic and financial conditions.

## Project structure

```
portfolio/
├── api.py                          # Wrapper to start the API server
├── batch.py                        # Batch pipeline entry point
├── bin/
│   └── batch.sh                    # Run batch pipeline in the portfolio container
├── docker/
│   ├── Dockerfile
│   ├── docker-compose.yml
│   └── entrypoint.sh
├── pyproject.toml
├── uv.lock
├── data/
│   ├── portfolio.db                # SQLite storage (created at runtime)
│   ├── funds/                      # NAV CSV files ({ISIN}.csv)
│   ├── series/                     # FRED macro series CSVs
│   ├── indexes/                    # Market index CSVs (e.g. SP500)
│   └── fixtures/                   # Metadata for master tables (funds and health-checks among others)
├── html/                           # Web UI (served by FastAPI)
├── src/portfolio/
│   ├── storage/                    # Shared persistence (models + DB)
│   │   ├── models.py               # SQLModel tables
│   │   ├── database.py             # Engine, schema 1.0 bootstrap, CRUD
│   │   └── fixtures/
│   │       ├── macro_health_checks.py  # Seed/sync macro health check catalog
│   │       └── funds.py                # Sync funds catalog from fixture
│   ├── api/                        # HTTP app only
│   │   ├── api.py                  # FastAPI app shell
│   │   └── services/
│   │       ├── management/         # Funds, positions, curve, metrics
│   │       ├── risk/               # QuantStats risk reports + cache
│   │       └── macro/              # Macro health series + history
│   ├── common/                     # Shared pure helpers (no api/batch/storage imports)
│   │   ├── navs.py                 # NAV CSV I/O + single-fund download
│   │   ├── series.py               # FRED macro series CSV I/O
│   │   ├── indexes.py              # Market index CSV I/O
│   │   ├── market.py               # Shared SP500-aligned market frame + indicators
│   │   ├── equity.py               # Buy-and-hold / benchmark returns
│   │   ├── metrics.py              # Metric computation only
│   │   ├── macro_constants.py      # Macro / series column names
│   │   └── health_check_descriptions.py  # Fixture load + threshold helpers
│   ├── datasource/                # External vendors (no DB)
│   │   ├── fred.py
│   │   └── morningstar.py
│   └── batch/                      # Offline / batch pipeline
│       ├── download.py             # Pipeline orchestration
│       ├── macro.py                # FRED + SP500 download pipeline
│       ├── sp500.py                # Long-term SP500 via Morningstar
│       ├── navs.py                 # Bulk NAV download from DB funds
│       ├── metrics.py              # Persist computed fund metrics
│       └── health_check_storage.py # Persist latest macro health data
└── tests/
```

## Package architecture of backend code

Package dependencies flow **inward** toward shared code. Arrows mean “imports / depends on”:

```
datasource   ←  common  ←  batch
                 ↑          ↑
                api      storage
                 ↑__________/
```

Rules:

- **`datasource/`** — vendor HTTP clients only (FRED, Morningstar). No DB, no `api`/`batch`/`storage` imports.
- **`common/`** — pure helpers and CSV I/O. May use `datasource`. Must **not** import `api`, `batch`, or `storage`.
- **`storage/`** — SQLModel models (schema 1.0), SQLite access, and fixture sync for health-check and fund catalogs. Shared by `api` and `batch`. Must **not** import `api` or `batch`.
- **`batch/`** — offline pipeline (download macro series, NAVs, refresh metrics, store health checks). May use `common`, `datasource`, and `storage`. Must **not** import `api`.
- **`api/`** — FastAPI app and HTTP services. May use `common`, `datasource`, and `storage`. Must **not** import `batch`.

The CLI entrypoint is `batch.py` / `bin/batch.sh`; they call into `portfolio.batch`.

## Install

Install dependencies with [uv](https://docs.astral.sh/uv/):

```bash
uv sync
```

This installs runtime dependencies plus dev tools (ruff, ty, pytest, httpx).

## Batch pipeline

`batch.py` downloads macro series from FRED, fund NAVs from Morningstar, and recomputes stored fund metrics for all funds in the database.

**Environment**

Create a `.env` file in the project root with your FRED API key:

```
FRED_API_KEY=your_key_here
```

If `FRED_API_KEY` is not set, the batch pipeline skips FRED downloads, still refreshes SP500 from Morningstar, and continues with fund NAV downloads. FRED or Morningstar download failures abort the batch with a clear error.

**Run the batch pipeline:**

```bash
uv run batch.py
```

Fund NAV files are written to `data/funds/{ISIN}.csv`. Add funds first via the web UI or Morningstar JSON import before running the batch pipeline.

## Macro health

The batch pipeline downloads macroeconomic series from FRED, aligns them to S&P 500 trading days, and runs a metadata-driven pipeline of indicator functions.

**Pipeline**

1. `batch.py` loads FRED series IDs from the health-check fixture (`fred_series_from_fixture()`).
2. `macro.py` downloads the series (or skips FRED when no API key), aligns macros onto the SP500 calendar with forward-fill via `common/market.py`, and stores CSVs.
3. Macro indicators (SP500 moving averages and death cross) are computed on the shared market DataFrame (also used by macro health history).

**Health checks** (`role: health_check`) — active when the threshold rule fires:

| Code | Series | Active when |
|------|--------|-------------|
| `Unemployment_Rate` | `UNRATE` | ≥ 5.0% |
| `High_Yield_Spread` | `BAMLH0A0HYM2EY` | ≥ 9.0% |
| `Financial_Stress_Index` | `STLFSI4` | ≥ 1.0 |
| `Yield_Spread_10Y3M` | `T10Y3M` | < 0 |
| `Real_Interest_Rates` | `DFII10` | ≥ 2.0% |
| `Breakeven_Inflation` | `T10YIE` | ≥ 2.5% |
| `SP500_Death_Cross` | computed (SMA50 / SMA200) | < 1.0 |

**Context series** (`role: context`) — shown for background; not counted as health-check actives:

| Code | Series | Notes |
|------|--------|-------|
| `Treasury_10Y_Yield` | `DGS10` | Threshold 4.5% (display only) |
| `Broad_Dollar_Index` | `DTWEXBGS` | No threshold |
| `Reserve_Balances` | `WRESBAL` | No threshold |
| `Overnight_RRP` | `RRPONTSYD` | No threshold |
| `SOFR` | `SOFR` | No threshold |

**Files**

- `macro_constants.py` — column names for macro series and indicators.
- `data/fixtures/macro_health_check_description.json` — catalog of series, thresholds, and roles (source of truth).
- `common/health_check_descriptions.py` — fixture load and threshold helpers.

**Adding a new FRED series / health check**

1. Add the column name to `macro_constants.py` if needed.
2. Add the check definition to `data/fixtures/macro_health_check_description.json` (including `series_id` for FRED rows).
3. Re-run the batch pipeline (and restart/reload the API if it is already up) so the catalog syncs into SQLite.

When the batch pipeline runs, the latest macro health values are printed to the console.

## API and web UI

Fund ISINs and portfolios are stored in `data/portfolio.db` (SQLite). Schema **1.0** is created from the SQLModel models on first `init_db()`; there is no in-place migration chain from older table shapes. If you have a pre-1.0 database, recreate it (or restore from backup) rather than expecting automatic upgrades.

`init_db()` runs once at **API startup** (FastAPI lifespan) and at the start of the **batch** pipeline. It creates tables if needed and syncs fund + macro health-check catalogs from `data/fixtures/`. CRUD helpers do not call `init_db()` themselves.

**Start the API server:**

```bash
uv run api.py
```

Open http://localhost:8000 to manage portfolios, funds, metrics, risk reports, and macro health.

### API endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/portfolio/portfolios` | List portfolios |
| `POST` | `/api/portfolio/portfolios` | Create a portfolio |
| `DELETE` | `/api/portfolio/portfolios/{id}` | Delete a portfolio |
| `PUT` | `/api/portfolio/portfolios/{id}/default` | Set default portfolio |
| `GET` | `/api/portfolio/funds` | List stored funds |
| `POST` | `/api/portfolio/funds` | Add a fund by ISIN |
| `DELETE` | `/api/portfolio/funds/{isin}` | Remove a fund |
| `GET` | `/api/portfolio/positions?portfolio_id=` | Saved positions for a portfolio |
| `PUT` | `/api/portfolio/positions?portfolio_id=` | Save portfolio positions |
| `GET` | `/api/portfolio/curve?portfolio_id=` | Buy-and-hold equity curve |
| `GET` | `/api/portfolio/metrics?portfolio_id=` | Portfolio metrics tables |
| `GET` | `/api/portfolio/risk_report?portfolio_id=` | QuantStats risk report (HTML) |
| `POST` | `/api/portfolio/risk_report?portfolio_id=` | Save positions and generate risk report |
| `GET` | `/api/macro` | Macro health series and monthly history |

**Save portfolio body:**

```json
{
  "positions": [
    {"isin": "IE00BYX5NX33", "weighted_assets": 0.65},
    {"isin": "IE00BYX5M476", "weighted_assets": 0.35}
  ]
}
```

## Docker

One image holds Python dependencies; **application code is mounted from the host** at runtime (`src/`, `html/`, `api.py`, `batch.py`, and `data/`). Rebuild the image only when dependencies change.

Pass `api` or `batch` as the command (default is `api`).

**Scripts** (from the repository root):

```bash
uv run api.py         # start API on http://localhost:8000
./bin/batch.sh        # run batch pipeline in the running portfolio container
```

Or with Docker Compose:

```bash
docker compose -f docker/docker-compose.yml up --build
docker compose -f docker/docker-compose.yml --profile batch run --rm batch
```

Build the image (for plain `docker run`):

```bash
docker build -f docker/Dockerfile -t portfolio .
```

**Plain `docker run`** — mount code and data explicitly:

```bash
docker run -p 8000:8000 \
  -v "$(pwd)/src:/app/src:ro" \
  -v "$(pwd)/html:/app/html:ro" \
  -v "$(pwd)/api.py:/app/api.py:ro" \
  -v "$(pwd)/batch.py:/app/batch.py:ro" \
  -v "$(pwd)/data:/app/data" \
  portfolio api

docker run \
  -v "$(pwd)/src:/app/src:ro" \
  -v "$(pwd)/html:/app/html:ro" \
  -v "$(pwd)/api.py:/app/api.py:ro" \
  -v "$(pwd)/batch.py:/app/batch.py:ro" \
  -v "$(pwd)/data:/app/data" \
  --env-file .env \
  portfolio batch
```

Open http://localhost:8000 for the API.

### Environment variables

Compose and `docker run --env-file .env` inject variables into the container environment. The batch pipeline reads `FRED_API_KEY` from there (`batch.py` also calls `load_dotenv()`, which is only needed when a `.env` file is present on disk).

If `FRED_API_KEY` is missing, FRED downloads are skipped; SP500 and fund NAVs still run. Failed downloads raise instead of writing empty files.

Local API bind defaults to `127.0.0.1` (override with `PORTFOLIO_HOST` / `PORTFOLIO_PORT`). Docker entrypoint defaults to `0.0.0.0` so published ports work. Set `PORTFOLIO_RELOAD=1` to enable uvicorn reload for local development.

Create `.env` in the project root:

```
FRED_API_KEY=your_key_here
```

## Tests

```bash
uv run pytest -q
```

## Technologies

- Python 3.12+
- pandas — dataframes and date handling
- requests — HTTP client for Morningstar API
- fredapi — FRED API client (macroeconomic series)
- quantstats — HTML performance reports
- fastapi / uvicorn — REST API and web UI
