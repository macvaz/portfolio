import pandas as pd

from portfolio.common.indexes import (
    index_dataframe_to_csv,
    index_path,
    load_index_csv,
    save_index_csv,
)


def test_index_dataframe_to_csv_normalizes_timestamp_index():
    df = pd.DataFrame(
        {"SP500": [4800.0, 4810.0]},
        index=pd.to_datetime(["2024-01-01", "2024-01-02"]),
    )

    out = index_dataframe_to_csv(df, "SP500")

    assert list(out.columns) == ["date", "value"]
    assert out["date"].tolist() == ["2024-01-01", "2024-01-02"]
    assert out["value"].tolist() == [4800.0, 4810.0]


def test_save_and_load_index_csv_roundtrip(tmp_path):
    indexes_dir = tmp_path / "indexes"
    df = pd.DataFrame(
        {"SP500": [4800.0, 4810.0, 4820.0]},
        index=pd.to_datetime(["2023-06-01", "2023-06-02", "2023-06-05"]),
    )

    path = save_index_csv(
        "SP500",
        df,
        column_name="SP500",
        indexes_dir=indexes_dir,
    )
    assert path == index_path("SP500", indexes_dir=indexes_dir)
    assert path.exists()

    loaded = load_index_csv("SP500", indexes_dir=indexes_dir)
    assert list(loaded.columns) == ["SP500"]
    assert len(loaded) == 3
    assert loaded["SP500"].tolist() == [4800.0, 4810.0, 4820.0]
