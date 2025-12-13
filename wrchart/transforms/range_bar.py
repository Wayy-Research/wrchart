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

    # Initialize first bar
    current_open = (highs[0] + lows[0]) / 2
    current_high = current_open
    current_low = current_open
    bar_start_time = times[0]

    for i in range(len(highs)):
        high = highs[i]
        low = lows[i]
        time = times[i]

        # Update current bar's high/low
        current_high = max(current_high, high)
        current_low = min(current_low, low)

        # Check if we've exceeded the range
        while current_high - current_low >= range_size:
            # Determine bar direction based on which extreme was hit first
            # For simplicity, we'll create bars in the direction of the move

            if current_high - current_open >= range_size:
                # Bullish bar
                bar_low = current_high - range_size
                bars.append(
                    {
                        "time": bar_start_time,
                        "open": current_open,
                        "high": current_high,
                        "low": bar_low,
                        "close": current_high,
                    }
                )
                # Start new bar
                current_open = current_high
                current_low = current_high
                bar_start_time = time

            elif current_open - current_low >= range_size:
                # Bearish bar
                bar_high = current_low + range_size
                bars.append(
                    {
                        "time": bar_start_time,
                        "open": current_open,
                        "high": bar_high,
                        "low": current_low,
                        "close": current_low,
                    }
                )
                # Start new bar
                current_open = current_low
                current_high = current_low
                bar_start_time = time
            else:
                # Range exceeded but no clear direction, create bar to high
                bar_low = current_high - range_size
                bars.append(
                    {
                        "time": bar_start_time,
                        "open": current_open,
                        "high": current_high,
                        "low": bar_low,
                        "close": current_high,
                    }
                )
                current_open = current_high
                current_low = current_high
                bar_start_time = time

            # Recalculate current range with remaining data
            current_high = max(current_open, high)
            current_low = min(current_open, low)

    # Add final incomplete bar if there's any range
    if current_high > current_low:
        close = (current_high + current_low) / 2
        bars.append(
            {
                "time": bar_start_time,
                "open": current_open,
                "high": current_high,
                "low": current_low,
                "close": close,
            }
        )

    if not bars:
        # Not enough movement
        return pl.DataFrame(
            {
                "time": [times[0]],
                "open": [current_open],
                "high": [current_high],
                "low": [current_low],
                "close": [(current_high + current_low) / 2],
            }
        )

    return pl.DataFrame(bars)
