import pandas as pd
from fredapi import Fred

def download_fred_data(fred_client, series_id, column_name, start_date, end_date) -> pd.DataFrame:
    """Downloads a time series from FRED and returns a clean DataFrame."""
    try:
        series = fred_client.get_series(series_id, observation_start=start_date, observation_end=end_date)
        df = pd.DataFrame(series, columns=[column_name])
        df.index = pd.to_datetime(df.index)
        return df
    except Exception as e:
        print(f"Error downloading series {series_id} from FRED: {e}")
        return pd.DataFrame()

def download_series(api_key: str, fred_series: list, start_date="1998-01-01", end_date=None) -> pd.DataFrame:
    """
    Downloads official macro indicators from the FRED API and calculates 
    the voting system for portfolio protection.
    """
    if api_key == "YOUR_FRED_API_KEY_HERE":
        raise ValueError("Please enter a valid FRED API Key to run the script.")

    # Default end_date to today if not provided so we fetch the most recent data
    if end_date is None:
        end_date = pd.Timestamp.now().strftime("%Y-%m-%d")

    print(f"Connecting to the official FRED API (range {start_date} -> {end_date})...")
    fred = Fred(api_key=api_key)
    
    print("Downloading time series...")
    macro_series_data = [
        download_fred_data(fred, series_id, column_name, start_date, end_date)
        for series_id, column_name in fred_series
    ]

    # 2. Synchronize calendars (We unify everything using S&P 500 trading days)
    print("Downloading SP500 data...")
    sp500 = download_fred_data(fred, "SP500", "SP500", start_date, end_date)
    
    # Create the master DataFrame indexed with actual market days
    df = pd.DataFrame(index=sp500.index)
    
    # Merge dataframes using their dates (indices)
    df = df.join(macro_series_data, how="left")
    
    # Forward fill the gaps (monthly unemployment or weekly stress data 
    # remains constant on trading days until a new data point is published)
    df.ffill(inplace=True)
    df.bfill(inplace=True) # Backward fill in case a series started slightly later

    return df

    

