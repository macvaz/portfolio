import pandas as pd

from portfolio.common.series import (
    load_series_csv,
    save_series_csv,
    series_dataframe_to_csv,
    series_path,
)


def test_series_dataframe_to_csv_normalizes_timestamp_index():
    df = pd.DataFrame(
        {"Unemployment_Rate": [3.5, 3.6]},
        index=pd.to_datetime(["2024-01-01", "2024-02-01"]),
    )

    out = series_dataframe_to_csv(df, "Unemployment_Rate")

    assert list(out.columns) == ["date", "value"]
    assert out["date"].tolist() == ["2024-01-01", "2024-02-01"]
    assert out["value"].tolist() == [3.5, 3.6]


def test_save_and_load_series_csv_roundtrip(tmp_path):
    series_dir = tmp_path / "series"
    df = pd.DataFrame(
        {"Financial_Stress_Index": [0.5, 0.8, 1.1]},
        index=pd.to_datetime(["2023-06-01", "2023-06-08", "2023-06-15"]),
    )

    path = save_series_csv(
        "STLFSI4",
        df,
        column_name="Financial_Stress_Index",
        series_dir=series_dir,
    )
    assert path == series_path("STLFSI4", series_dir=series_dir)
    assert path.exists()

    loaded = load_series_csv("STLFSI4", series_dir=series_dir)
    assert list(loaded.columns) == ["STLFSI4"]
    assert len(loaded) == 3
    assert loaded["STLFSI4"].tolist() == [0.5, 0.8, 1.1]
