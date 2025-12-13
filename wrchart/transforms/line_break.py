"""
Three Line Break chart transformation.

Line Break charts show reversals based on breaking previous highs/lows,
ignoring time.
"""

import polars as pl
from typing import List, Dict, Any


def to_line_break(
    df: pl.DataFrame,
    num_lines: int = 3,
    time_col: str = "time",
    close_col: str = "close",
) -> pl.DataFrame:
    """
    Convert price data to Three Line Break (or N-Line Break) chart.

    Line Break charts create a new line when the closing price exceeds
    the high or low of the previous N lines. This filters out minor
    price movements and highlights significant reversals.

    Benefits:
    - Filters noise without arbitrary box sizes
    - Self-adjusting to market volatility
    - Clear trend identification

    Args:
        df: Polars DataFrame with price data
        num_lines: Number of previous lines to check for reversal (default 3)
        time_col: Name of time column
        close_col: Name of close price column

    Returns:
        DataFrame with Line Break data (time, open, high, low, close, direction)
        direction: 1 for up (white/green), -1 for down (black/red)

    Example:
        >>> import wrchart as wrc
        >>> # Standard 3-line break
        >>> lb = wrc.to_line_break(price_data)
        >>>
        >>> # 2-line break (more sensitive)
        >>> lb = wrc.to_line_break(price_data, num_lines=2)
    """
    closes = df[close_col].to_list()
    times = df[time_col].to_list()

    if len(closes) < 2:
        return pl.DataFrame(
            {
                "time": times,
                "open": closes,
                "high": closes,
                "low": closes,
                "close": closes,
                "direction": [1] * len(closes),
            }
        )

    lines: List[Dict[str, Any]] = []

    # First line
    first_open = closes[0]
    first_close = closes[1] if len(closes) > 1 else closes[0]
    first_direction = 1 if first_close >= first_open else -1

    lines.append(
        {
            "time": times[1] if len(times) > 1 else times[0],
            "open": first_open,
            "high": max(first_open, first_close),
            "low": min(first_open, first_close),
            "close": first_close,
            "direction": first_direction,
        }
    )

    for i in range(2, len(closes)):
        close = closes[i]
        time = times[i]

        # Get the high/low of the last num_lines lines
        lookback = lines[-num_lines:] if len(lines) >= num_lines else lines
        recent_high = max(line["high"] for line in lookback)
        recent_low = min(line["low"] for line in lookback)

        last_line = lines[-1]
        current_direction = last_line["direction"]

        new_line = None

        if current_direction == 1:  # Currently in uptrend
            if close > last_line["high"]:
                # Continue up - new white line
                new_line = {
                    "time": time,
                    "open": last_line["close"],
                    "high": close,
                    "low": last_line["close"],
                    "close": close,
                    "direction": 1,
                }
            elif close < recent_low:
                # Reversal down - new black line
                new_line = {
                    "time": time,
                    "open": last_line["close"],
                    "high": last_line["close"],
                    "low": close,
                    "close": close,
                    "direction": -1,
                }
        else:  # Currently in downtrend
            if close < last_line["low"]:
                # Continue down - new black line
                new_line = {
                    "time": time,
                    "open": last_line["close"],
                    "high": last_line["close"],
                    "low": close,
                    "close": close,
                    "direction": -1,
                }
            elif close > recent_high:
                # Reversal up - new white line
                new_line = {
                    "time": time,
                    "open": last_line["close"],
                    "high": close,
                    "low": last_line["close"],
                    "close": close,
                    "direction": 1,
                }

        if new_line:
            lines.append(new_line)

    return pl.DataFrame(lines)
