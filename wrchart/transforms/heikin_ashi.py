"""
Heikin-Ashi transformation.

Heikin-Ashi candles smooth price action by averaging prices,
making trends easier to identify.
"""

import polars as pl


def to_heikin_ashi(
    df: pl.DataFrame,
    time_col: str = "time",
    open_col: str = "open",
    high_col: str = "high",
    low_col: str = "low",
    close_col: str = "close",
) -> pl.DataFrame:
    """
    Convert OHLC data to Heikin-Ashi candles.

    Heikin-Ashi ("average bar" in Japanese) smooths price action:
    - HA Close = (Open + High + Low + Close) / 4
    - HA Open = (Previous HA Open + Previous HA Close) / 2
    - HA High = max(High, HA Open, HA Close)
    - HA Low = min(Low, HA Open, HA Close)

    Benefits:
    - Clearer trend identification
    - Reduced noise
    - Better support/resistance visualization

    Args:
        df: Polars DataFrame with OHLC columns
        time_col: Name of time column
        open_col: Name of open price column
        high_col: Name of high price column
        low_col: Name of low price column
        close_col: Name of close price column

    Returns:
        DataFrame with Heikin-Ashi OHLC values

    Example:
        >>> import wrchart as wrc
        >>> ha_data = wrc.to_heikin_ashi(ohlc_data)
        >>> chart = wrc.Chart()
        >>> chart.add_candlestick(ha_data)
    """
    # Calculate HA Close first (simple average)
    ha_close = (
        pl.col(open_col) + pl.col(high_col) + pl.col(low_col) + pl.col(close_col)
    ) / 4

    # Calculate HA Open iteratively (depends on previous values)
    # First bar: HA Open = (Open + Close) / 2
    # Subsequent: HA Open = (Previous HA Open + Previous HA Close) / 2

    # We need to compute this row by row due to the recursive dependency
    # For efficiency, we'll use a cumulative approach

    # Calculate HA close and extract original values
    result = df.select([
        pl.col(time_col),
        ha_close.alias("ha_close"),
        pl.col(high_col).alias("orig_high"),
        pl.col(low_col).alias("orig_low"),
        pl.col(open_col).alias("orig_open"),
    ])

    # Convert to list for iterative calculation
    ha_closes = result["ha_close"].to_list()
    orig_opens = result["orig_open"].to_list()
    orig_highs = result["orig_high"].to_list()
    orig_lows = result["orig_low"].to_list()

    n = len(ha_closes)
    ha_opens = [0.0] * n
    ha_highs = [0.0] * n
    ha_lows = [0.0] * n

    # First bar
    ha_opens[0] = (orig_opens[0] + ha_closes[0]) / 2
    ha_highs[0] = max(orig_highs[0], ha_opens[0], ha_closes[0])
    ha_lows[0] = min(orig_lows[0], ha_opens[0], ha_closes[0])

    # Subsequent bars
    for i in range(1, n):
        ha_opens[i] = (ha_opens[i - 1] + ha_closes[i - 1]) / 2
        ha_highs[i] = max(orig_highs[i], ha_opens[i], ha_closes[i])
        ha_lows[i] = min(orig_lows[i], ha_opens[i], ha_closes[i])

    # Build result DataFrame
    return pl.DataFrame(
        {
            time_col: df[time_col],
            "open": ha_opens,
            "high": ha_highs,
            "low": ha_lows,
            "close": ha_closes,
        }
    )
