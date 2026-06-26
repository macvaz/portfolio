# Portfolio

A small Python library to download and process time series (fund prices) from Morningstar and macroeconomic data from FRED, compute portfolio returns, and generate performance reports.

## Project structure

```
portfolio/
├── api.py                          # Wrapper to start the API server
├── job.py                          # Data job entry point
├── bin/
│   ├── api.sh                      # Start API via Docker Compose
│   └── job.sh                      # Run data job via Docker Compose
├── docker/
│   ├── Dockerfile                  # API + job image
│   ├── docker-compose.yml          # Local API / job stack
│   └── entrypoint.sh               # Dispatches api vs job command
├── pyproject.toml
├── uv.lock
├── docs/
│   └── portfolio_performance.png   # Screenshot of the QuantStats report output
├── data/
│   ├── portfolio.db                # SQLite storage (created at runtime)
│   └── funds/                      # NAV CSV files ({ISIN}.csv)
├── html/                           # Web UI (HTML/CSS/JS served by FastAPI)
│   ├── index.html
│   ├── app.js
│   ├── api.js
│   ├── management.js
│   ├── portfolios.js
│   ├── risk.js
│   └── style.css
├── src/portfolio/
│   ├── __init__.py
│   ├── api/
│   │   ├── api.py                  # FastAPI app shell
│   │   ├── database.py             # SQLModel storage and queries
│   │   ├── models.py               # User, Fund, Portfolio tables
│   │   └── services/
│   │       ├── portfolio/
│   │       │   ├── router.py       # /api/portfolio/* endpoints
│   │       │   ├── schemas.py      # Request/response models
│   │       │   ├── curve.py        # Equity curve
│   │       │   ├── metrics.py      # Dashboard metrics payload
│   │       │   └── risk_report.py  # QuantStats risk report
│   │       └── signals/
│   │           ├── router.py       # /api/signals endpoints
│   │           └── service.py      # Tactical signals service
│   ├── common/
│   │   ├── navs.py                 # NAV CSV storage
│   │   ├── metrics.py              # Fund/portfolio metric computation
│   │   ├── quantstats.py           # QuantStats HTML reports
│   │   ├── returns.py              # Buy-and-hold return calculation
│   │   ├── macro_constants.py      # FRED series and macro column names
│   │   ├── macro_signals.py        # Macro indicator functions (metadata-driven)
│   │   └── signals.py              # FRED download and signal pipeline
│   ├── datasources/
│   │   ├── fred.py                 # FRED time series download
│   │   └── morningstar.py          # ISIN lookup and NAV download
│   └── job/
│       └── download.py             # Data job orchestration
└── tests/
    ├── test_api.py
    ├── test_curve.py
    ├── test_funds.py
    ├── test_get_navs.py
    ├── test_metrics.py
    ├── test_nav_files.py
    ├── test_portfolio.py
    ├── test_portfolio_model.py
    └── test_database_migration.py
```

## Install

Install dependencies with [uv](https://docs.astral.sh/uv/):

```bash
uv sync
```

For development (tests):

```bash
uv sync --extra dev
```

## Data job

`job.py` downloads macro signals from FRED, fund NAVs from Morningstar, backfills fund metadata, and recomputes stored fund metrics for all funds in the database.

**Environment**

Create a `.env` file in the project root with your FRED API key:

```
FRED_API_KEY=your_key_here
```

If `FRED_API_KEY` is not set, the job skips the macro signals step and continues with fund NAV downloads.

**Run the data job:**

```bash
uv run job.py
```

Fund NAV files are written to `data/funds/{ISIN}.csv`. Add funds first via the web UI or `POST /api/portfolio/funds` before running the job.

## Macro signals

The data job downloads macroeconomic series from FRED, aligns them to S&P 500 trading days, and runs a metadata-driven pipeline of indicator functions.

**Pipeline**

1. `job.py` defines which FRED series to download (`FRED_SERIES`) and which macro functions to run (`MACRO_SIGNALS`).
2. `signals.py` downloads the series, forward-fills gaps on the SP500 calendar, and pipes the DataFrame through each macro function.
3. Market signals (SP500 moving averages and death cross) are computed on top of the macro output.

**Current macro indicators**

| Indicator | Input series | Alert / output |
|-----------|--------------|----------------|
| Inverted curve | 10Y–3M yield spread (`T10Y3M`) | `Alert_Inverted_Curve` when spread < 0 |
| Sahm rule | Unemployment rate (`UNRATE`) | `Sahm_Value` and `Alert_Sahm` (informational) |
| Financial stress | STL Financial Stress Index (`STLFSI4`) | `Alert_Financial_Stress` when index ≥ 1.0 |
| Crisis votes | Selected alerts above | `Macro_Crisis_Votes` and `MACRO_SYSTEM_LOCKED` when ≥ 2 votes |

The Sahm rule is tracked but does not count toward crisis votes. Only inverted-curve and financial-stress alerts vote.

**Files**

- `macro_constants.py` — column names and `MACRO_VOTE_ALERTS` (single source of truth for string identifiers).
- `macro_signals.py` — one function per indicator; each takes a DataFrame and returns it with new columns via `.assign()`.
- `job.py` — wires FRED series IDs to column names and lists the macro functions to run.

**Adding a new macro signal**

1. Add the column name(s) to `macro_constants.py`.
2. If needed, add the FRED series to `FRED_SERIES` in `job.py`.
3. Implement a function in `macro_signals.py` (e.g. `def my_signal(df): return df.assign(...)`).
4. Append the function to `MACRO_SIGNALS` in `job.py`. To include it in crisis voting, add its alert column to `MACRO_VOTE_ALERTS` in `macro_constants.py`.

When the job runs, the latest macro and market signals are printed to the console.

## API and web UI

Fund ISINs and portfolios are stored in `data/portfolio.db` (SQLite).

**Start the API server:**

```bash
uv run api.py
```

Open http://localhost:8000 to manage portfolios, funds, metrics, risk reports, and tactical signals.

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
| `GET` | `/api/signals` | Tactical macro and market signals |

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

One image holds Python dependencies and Playwright; **application code is mounted from the host** at runtime (`src/`, `html/`, `api.py`, `job.py`, and `data/`). Rebuild the image only when dependencies change.

Pass `api` or `job` as the command (default is `api`).

**Scripts** (from the repository root):

```bash
./bin/api.sh          # start API on http://localhost:8000
./bin/job.sh          # run data job once
```

Build the image:

```bash
docker build -f docker/Dockerfile -t portfolio .
```

**Docker Compose** (same as the scripts):

```bash
docker compose -f docker/docker-compose.yml up --build
docker compose -f docker/docker-compose.yml --profile job run --rm job
```

**Plain `docker run`** — mount code and data explicitly:

```bash
docker run -p 8000:8000 \
  -v "$(pwd)/src:/app/src:ro" \
  -v "$(pwd)/html:/app/html:ro" \
  -v "$(pwd)/api.py:/app/api.py:ro" \
  -v "$(pwd)/job.py:/app/job.py:ro" \
  -v "$(pwd)/data:/app/data" \
  portfolio api

docker run \
  -v "$(pwd)/src:/app/src:ro" \
  -v "$(pwd)/html:/app/html:ro" \
  -v "$(pwd)/api.py:/app/api.py:ro" \
  -v "$(pwd)/job.py:/app/job.py:ro" \
  -v "$(pwd)/data:/app/data" \
  --env-file .env \
  portfolio job
```

Open http://localhost:8000 for the API.

### Environment variables

Compose and `docker run --env-file .env` inject variables into the container environment. The job reads `FRED_API_KEY` from there (`job.py` also calls `load_dotenv()`, which is only needed when a `.env` file is present on disk).

The API does not use `.env` today. The job requires `FRED_API_KEY` for the macro signals step; without it, the job skips FRED and continues with fund NAV downloads.

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
- requests — HTTP client for Morningstar price API
- fredapi — FRED API client (macroeconomic series)
- playwright — browser automation for Morningstar ISIN search
- quantstats — HTML performance reports
- fastapi / uvicorn — REST API and web UI
