# Portfolio

A small Python library to download and process time series (fund prices) from Morningstar and macroeconomic data from FRED, compute portfolio returns, and generate performance reports.

## Project structure

```
portfolio/
├── api.py                          # Starting the API server
├── job.py                          # Downloading data points from morningstar and fred
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
│   ├── __init__.py                 # Package exports and process_macro_data()
│   ├── get_data.py                 # Data job orchestration
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
│   ├── datasources/
│   │   ├── fred.py                 # FRED time series download
│   │   └── morningstar.py          # ISIN lookup and NAV download
│   └── finance/
│       ├── metrics.py              # Fund/portfolio metric computation
│       ├── navs.py                 # NAV CSV storage
│       ├── quantstats.py           # QuantStats HTML reports
│       ├── returns.py              # Buy-and-hold return calculation
│       └── signals.py              # Macro and market signal calculations
└── tests/
    ├── test_api.py
    ├── test_curve.py
    ├── test_funds.py
    ├── test_get_navs.py
    ├── test_metrics.py
    ├── test_nav_files.py
    ├── test_portfolio.py
    └── test_portfolio_model.py
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
