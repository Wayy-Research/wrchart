"""
Range Bar chart transformation.

Range bars create new bars based on price range, not time.
Each bar has the same high-low range.
"""

import polars as pl
from typing import List, Dict, Any


def to_range_bars(
    df: pl.DataFrame,
    range_size: float,
    time_col: str = "time",
    open_col: str = "open",
    high_col: str = "high",
    low_col: str = "low",
    close_col: str = "close",
) -> pl.DataFrame:
    """
    Convert OHLC data to Range Bars.

    Range bars create a new bar only when price has moved by the
    specified range. Each bar has exactly the same height (range_size),
    regardless of how long it took to form.

    Benefits:
    - Equal-sized bars for consistent analysis
    - Filters time-based noise
    - Better visualization of volatility changes

    Args:
        df: Polars DataFrame with OHLC data
        range_size: Fixed range for each bar
        time_col: Name of time column
        open_col: Name of open price column
        high_col: Name of high price column
        low_col: Name of low price column
        close_col: Name of close price column

    Returns:
        DataFrame with Range Bar data (time, open, high, low, close)

    Example:
        >>> import wrchart as wrc
        >>> # $2 range bars
        >>> rb = wrc.to_range_bars(ohlc_data, range_size=2.0)
    """
    highs = df[high_col].to_list()
    lows = df[low_col].to_list()
    times = df[time_col].to_list()

    if len(highs) == 0:
        return pl.DataFrame(
            {"time": [], "open": [], "high": [], "low": [], "close": []}
        )

    bars: List[Dict[str, Any]] = []
    max_bars = 500  # Safety limit

    # Initialize with first candle's midpoint
    open_price = (highs[0] + lows[0]) / 2
    range_high = open_price
    range_low = open_price
    bar_start_time = times[0]

    for i in range(len(highs)):
        if len(bars) >= max_bars:
            break

        high = highs[i]
        low = lows[i]
        time = times[i]

        # Update range tracking
        if high > range_high:
            range_high = high
        if low < range_low:
            range_low = low

        # Keep creating bars while conditions are met
        bars_created = True
        while bars_created and len(bars) < max_bars:
            bars_created = False

            # Check for up bar: high moved enough from open
            if range_high - open_price >= range_size:
                bar_close = open_price + range_size
                bars.append({
                    "time": bar_start_time,
                    "open": open_price,
                    "high": bar_close,
                    "low": open_price,
                    "close": bar_close,
                })
                open_price = bar_close
                range_high = max(range_high, bar_close)
                range_low = bar_close
                bar_start_time = time
                bars_created = True

            # Check for down bar: low moved enough from open
            elif open_price - range_low >= range_size:
                bar_close = open_price - range_size
                bars.append({
                    "time": bar_start_time,
                    "open": open_price,
                    "high": open_price,
                    "low": bar_close,
                    "close": bar_close,
                })
                open_price = bar_close
                range_low = min(range_low, bar_close)
                range_high = bar_close
                bar_start_time = time
                bars_created = True

    if not bars:
        # Not enough movement, return empty with proper schema
        return pl.DataFrame(
            {"time": [], "open": [], "high": [], "low": [], "close": []}
        ).cast({"time": df[time_col].dtype})

    return pl.DataFrame(bars)
