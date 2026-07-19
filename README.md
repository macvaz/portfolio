# Portfolio

Python library to download and process mutual fund prices from Morningstar and macroeconomic series from FRED. It allows creating different investment portfolios while computing returns and risk reports. Additionally, it triggers low-frequency market and financial alarms to detect real worsening of economic and financial conditions.

## Project structure

```
portfolio/
├── api.py                          # Wrapper to start the API server
├── batch.py                        # Batch pipeline entry point
├── bin/
│   ├── api.sh                      # Start API via Docker Compose
│   └── job.sh                      # Run data job via Docker Compose
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
│   └── fixtures/                   # Alert catalog JSON fixture
├── html/                           # Web UI (served by FastAPI)
├── src/portfolio/
│   ├── storage/                    # Shared persistence (models + DB)
│   │   ├── models.py               # SQLModel tables
│   │   ├── database.py             # Engine, migrations, CRUD
│   │   └── fixtures/
│   │       └── alerts.py           # Seed/sync alert descriptions
│   ├── api/                        # HTTP app only
│   │   ├── api.py                  # FastAPI app shell
│   │   └── services/
│   │       ├── portfolio/          # Funds, positions, curve, metrics, risk
│   │       └── alerts/             # Tactical alerts + history
│   ├── common/                     # Shared pure helpers (no api/batch/storage imports)
│   │   ├── navs.py                 # NAV CSV I/O + single-fund download
│   │   ├── series.py               # FRED macro series CSV I/O
│   │   ├── indexes.py              # Market index CSV I/O
│   │   ├── equity.py               # Buy-and-hold / benchmark returns
│   │   ├── metrics.py              # Metric computation only
│   │   ├── signals.py              # Death-cross calculation
│   │   ├── macro_constants.py      # Alert / series column names
│   │   └── alert_descriptions.py   # Fixture load + threshold helpers
│   ├── datasource/                # External vendors (no DB)
│   │   ├── fred.py
│   │   └── morningstar.py
│   └── batch/                      # Offline / batch pipeline
│       ├── download.py             # Pipeline orchestration
│       ├── signals.py              # FRED + SP500 download pipeline
│       ├── sp500.py                # Long-term SP500 via Morningstar
│       ├── navs.py                 # Bulk NAV download from DB funds
│       ├── metrics.py              # Persist computed fund metrics
│       └── alert_storage.py        # Persist latest tactical alerts
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
- **`storage/`** — SQLModel models, SQLite access, migrations, and alert-catalog seeding. Shared by `api` and `batch`. Must **not** import `api` or `batch`.
- **`batch/`** — offline pipeline (download signals, NAVs, refresh metrics, store alerts). May use `common`, `datasource`, and `storage`. Must **not** import `api`.
- **`api/`** — FastAPI app and HTTP services. May use `common`, `datasource`, and `storage`. Must **not** import `batch`.

The CLI entrypoint is `batch.py` / `bin/batch.sh`; they call into `portfolio.batch`.

## Install

Install dependencies with [uv](https://docs.astral.sh/uv/):

```bash
uv sync
```

This installs runtime dependencies plus dev tools (ruff, ty, pytest, httpx).

## Batch pipeline

`batch.py` downloads macro signals from FRED, fund NAVs from Morningstar, and recomputes stored fund metrics for all funds in the database.

**Environment**

Create a `.env` file in the project root with your FRED API key:

```
FRED_API_KEY=your_key_here
```

If `FRED_API_KEY` is not set, the batch pipeline skips the macro signals step and continues with fund NAV downloads.

**Run the batch pipeline:**

```bash
uv run batch.py
```

Fund NAV files are written to `data/funds/{ISIN}.csv`. Add funds first via the web UI or Morningstar JSON import before running the batch pipeline.

## Macro signals

The batch pipeline downloads macroeconomic series from FRED, aligns them to S&P 500 trading days, and runs a metadata-driven pipeline of indicator functions.

**Pipeline**

1. `batch.py` defines which FRED series to download (`FRED_SERIES`).
2. `signals.py` downloads the series, forward-fills gaps on the SP500 calendar, and pipes the DataFrame through each macro function.
3. Market signals (SP500 moving averages and death cross) are computed on top of the macro output.

**Current macro indicators**

| Indicator | Input series | Alert / output |
|-----------|--------------|----------------|
| Inverted curve | 10Y–3M yield spread (`T10Y3M`) | `Alert_Inverted_Curve` when spread < 0 |
| Sahm rule | FRED real-time indicator (`SAHMREALTIME`) | `SAHM_RULE` when indicator ≥ 0.5 pp |
| Financial stress | STL Financial Stress Index (`STLFSI4`) | `FINANCIAL_STRESS` when index ≥ 1.0 |

The Sahm rule is tracked as an informational alert and does not gate other signals.

**Files**

- `macro_constants.py` — column names for macro and market signals.
- `batch.py` — wires FRED series IDs to column names.
- `data/fixtures/alert_description.json` — alert thresholds and metadata.

**Adding a new FRED series / alert**

1. Add the column name to `macro_constants.py`.
2. Add the FRED series to `FRED_SERIES` in `batch.py`.
3. Add the alert definition to `data/fixtures/alert_description.json`.

When the batch pipeline runs, the latest macro and market signals are printed to the console.

## API and web UI

Fund ISINs and portfolios are stored in `data/portfolio.db` (SQLite).

**Start the API server:**

```bash
uv run api.py
```

Open http://localhost:8000 to manage portfolios, funds, metrics, risk reports, and tactical alerts.

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

One image holds Python dependencies; **application code is mounted from the host** at runtime (`src/`, `html/`, `api.py`, `batch.py`, and `data/`). Rebuild the image only when dependencies change.

Pass `api` or `batch` as the command (default is `api`).

**Scripts** (from the repository root):

```bash
./bin/api.sh          # start API on http://localhost:8000
./bin/batch.sh        # run batch pipeline once
```

Build the image:

```bash
docker build -f docker/Dockerfile -t portfolio .
```

**Docker Compose** (same as the scripts):

```bash
docker compose -f docker/docker-compose.yml up --build
docker compose -f docker/docker-compose.yml --profile batch run --rm batch
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

The API does not use `.env` today. The batch pipeline requires `FRED_API_KEY` for the macro signals step; without it, the batch pipeline skips FRED and continues with fund NAV downloads.

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
