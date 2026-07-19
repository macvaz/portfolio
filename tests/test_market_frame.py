import pandas as pd

from portfolio.common.market import align_market_dataframe, load_market_dataframe
from portfolio.common.indexes import save_index_csv
from portfolio.common.series import save_series_csv


def test_align_market_dataframe_ffills_onto_sp500_calendar():
    sp500 = pd.DataFrame(
        {"SP500": [100.0, 101.0, 102.0]},
        index=pd.to_datetime(["2024-01-02", "2024-01-03", "2024-01-04"]),
    )
    unrate = pd.DataFrame(
        {"Unemployment_Rate": [3.7]},
        index=pd.to_datetime(["2024-01-02"]),
    )

    frame = align_market_dataframe(sp500, [unrate])

    assert list(frame.index) == list(sp500.index)
    assert frame["Unemployment_Rate"].tolist() == [3.7, 3.7, 3.7]
    assert "SP500_Death_Cross" in frame.columns


def test_load_market_dataframe_matches_align_helper(tmp_path):
    series_dir = tmp_path / "series"
    indexes_dir = tmp_path / "indexes"
    save_series_csv(
        "UNRATE",
        pd.DataFrame(
            {"Unemployment_Rate": [4.0]},
            index=pd.to_datetime(["2024-06-03"]),
        ),
        column_name="Unemployment_Rate",
        series_dir=series_dir,
    )
    save_index_csv(
        "SP500",
        pd.DataFrame(
            {"SP500": [5000.0, 5010.0]},
            index=pd.to_datetime(["2024-06-03", "2024-06-04"]),
        ),
        column_name="SP500",
        indexes_dir=indexes_dir,
    )

    loaded = load_market_dataframe(series_dir, indexes_dir)
    assert loaded.loc["2024-06-04", "Unemployment_Rate"] == 4.0
    assert loaded.loc["2024-06-04", "SP500"] == 5010.0
