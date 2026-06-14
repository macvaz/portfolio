# Portfolio

A small Python library to download and process time series (fund prices) from Morningstar and other data sources.

**Project layout**
- **src/portfolio/**: package source
  - [src/portfolio/download.py](src/portfolio/download.py): helper to download Morningstar time series and parse into a `pandas.DataFrame`.
  - [src/portfolio/series.py](src/portfolio/series.py): FRED download helpers and series composition.
  - [src/portfolio/signals.py](src/portfolio/signals.py): signal calculations.
- **tests/**: unit tests (run with `pytest`).
- **pyproject.toml**: project metadata and dependencies.

**Technologies**
- Python 3.12+
- pandas — dataframes and date handling
- requests — HTTP client
- fredapi — FRED API client (for macroeconomic series)
- playwright — browser automation for invoking MorningStar public API calls skipping bot detection mechanicisms.

**Install**
Create and activate a virtualenv, then install the project (this will install dependencies from `pyproject.toml`):

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

**Run examples with `uv`**
This repository uses a simple runner that you can invoke with the `uv` command (as used in this workspace). Example:

```bash
# run the download example (prints a DataFrame)
uv run src/portfolio/download.py

# run the main runner
uv run src/portfolio/run.py
```

`download.py` contains `download_price_data()` which is called when executed as `__main__`.

**Tests**
Run unit tests with:

```bash
pytest -q
```

**Notes**
- The Morningstar timeseries endpoint expects the fund `id` parameter to include a suffix (kept in this code as `ID_SUFFIX` in `src/portfolio/download.py`) — omitting it returns an empty result. The code documents this behavior.

If you want, I can add a short example script showing how to call `download_price_data()` programmatically and save results to CSV.