"""
Renko chart transformation.

Renko charts focus on price movement, ignoring time.
Each brick represents a fixed price movement.
"""

import polars as pl
from typing import Optional


def to_renko(
    df: pl.DataFrame,
    brick_size: float,
    time_col: str = "time",
    close_col: str = "close",
    high_col: Optional[str] = "high",
    low_col: Optional[str] = "low",
    use_atr: bool = False,
    atr_period: int = 14,
) -> pl.DataFrame:
    """
    Convert price data to Renko bricks.

    Renko charts show only price movement, with each brick
    representing a fixed price change. Time is ignored - a new
    brick only forms when price moves by the brick size.

    Benefits:
    - Filters out noise and minor fluctuations
    - Clear trend identification
    - Time-independent analysis

    Args:
        df: Polars DataFrame with price data
        brick_size: Size of each brick in price units
        time_col: Name of time column
        close_col: Name of close price column
        high_col: Name of high price column (uses intraday highs)
        low_col: Name of low price column (uses intraday lows)
        use_atr: If True, calculate brick_size from ATR
        atr_period: Period for ATR calculation if use_atr=True

    Returns:
        DataFrame with Renko bricks (time, open, high, low, close)

    Example:
        >>> import wrchart as wrc
        >>> # Fixed brick size of $5
        >>> renko = wrc.to_renko(ohlc_data, brick_size=5.0)
        >>>
        >>> # Or use ATR-based brick size
        >>> renko = wrc.to_renko(ohlc_data, brick_size=0, use_atr=True)
    """
    if use_atr and high_col and low_col:
        brick_size = _calculate_atr_brick_size(df, high_col, low_col, close_col, atr_period)

    times = df[time_col].to_list()

    # Use high/low if available, otherwise fall back to close
    use_hl = high_col in df.columns and low_col in df.columns
    if use_hl:
        highs = df[high_col].to_list()
        lows = df[low_col].to_list()
    else:
        closes = df[close_col].to_list()
        highs = closes
        lows = closes

    if len(times) == 0:
        return pl.DataFrame(
            {"time": [], "open": [], "high": [], "low": [], "close": []}
        )

    # Initialize with first price
    first_price = (highs[0] + lows[0]) / 2 if use_hl else highs[0]
    # Round to nearest brick
    base_price = round(first_price / brick_size) * brick_size

    bricks = []
    brick_times = []
    last_direction = 0  # 1 for up, -1 for down, 0 for initial
    max_bricks = 500  # Safety limit

    for i in range(len(times)):
        if len(bricks) >= max_bricks:
            break

        # Process both high and low to catch intraday moves
        # Order depends on last direction to handle reversals correctly
        if last_direction >= 0:
            prices_to_check = [highs[i], lows[i]]
        else:
            prices_to_check = [lows[i], highs[i]]

        for price in prices_to_check:
            if len(bricks) >= max_bricks:
                break

            # Check for upward bricks
            while price - base_price >= brick_size and len(bricks) < max_bricks:
                # Reversal check: need 2x brick size for reversal from down
                if last_direction == -1 and price - base_price < brick_size * 2:
                    break

                brick_open = base_price
                brick_close = base_price + brick_size

                bricks.append({
                    "open": brick_open,
                    "close": brick_close,
                    "high": brick_close,
                    "low": brick_open,
                })
                brick_times.append(times[i])
                base_price = brick_close
                last_direction = 1

            # Check for downward bricks
            while base_price - price >= brick_size and len(bricks) < max_bricks:
                # Reversal check: need 2x brick size for reversal from up
                if last_direction == 1 and base_price - price < brick_size * 2:
                    break

                brick_open = base_price
                brick_close = base_price - brick_size

                bricks.append({
                    "open": brick_open,
                    "close": brick_close,
                    "high": brick_open,
                    "low": brick_close,
                })
                brick_times.append(times[i])
                base_price = brick_close
                last_direction = -1

    if not bricks:
        # No bricks formed, return empty DataFrame with proper schema
        return pl.DataFrame(
            {"time": [], "open": [], "high": [], "low": [], "close": []}
        ).cast({"time": df[time_col].dtype})

    return pl.DataFrame(
        {
            "time": brick_times,
            "open": [b["open"] for b in bricks],
            "high": [b["high"] for b in bricks],
            "low": [b["low"] for b in bricks],
            "close": [b["close"] for b in bricks],
        }
    )


def _calculate_atr_brick_size(
    df: pl.DataFrame,
    high_col: str,
    low_col: str,
    close_col: str,
    period: int,
) -> float:
    """Calculate ATR-based brick size."""
    # True Range = max(High - Low, |High - Prev Close|, |Low - Prev Close|)
    tr = df.select(
        [
            pl.col(high_col) - pl.col(low_col),
            (pl.col(high_col) - pl.col(close_col).shift(1)).abs(),
            (pl.col(low_col) - pl.col(close_col).shift(1)).abs(),
        ]
    ).select(pl.max_horizontal(pl.all()))

    # ATR = rolling mean of TR
    atr = tr.to_series().rolling_mean(period).mean()

    return atr if atr and atr > 0 else 1.0
