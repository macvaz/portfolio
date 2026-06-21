import pandas as pd

from fredapi import Fred

def init_client(api_key: str) -> Fred:
    return Fred(api_key=api_key)

def download_fred_data(
    fred_client, series_id, column_name, start_date, end_date
) -> pd.DataFrame:
    """Downloads a time series from FRED and returns a clean DataFrame."""
    try:
        series = fred_client.get_series(
            series_id, observation_start=start_date, observation_end=end_date
        )
        df = pd.DataFrame(series, columns=[column_name])
        df.index = pd.to_datetime(df.index)
        return df
    except Exception as e:
        print(f"Error downloading series {series_id} from FRED: {e}")
        return pd.DataFrame()
