import pandas as pd

def calculate(dataframe: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    """
    Calculates the Relative Strength Index (RSI).

    Args:
        dataframe: A pandas DataFrame with a 'close' column.
        period: The time period for RSI calculation.

    Returns:
        A pandas DataFrame with the RSI values in a new 'rsi' column.
    """
    delta = dataframe['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()

    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    
    result_df = pd.DataFrame(index=dataframe.index)
    result_df[f'rsi_{period}'] = rsi

    return result_df
