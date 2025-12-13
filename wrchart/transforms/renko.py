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
        high_col: Name of high price column (for wick calculation)
        low_col: Name of low price column (for wick calculation)
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

    closes = df[close_col].to_list()
    times = df[time_col].to_list()

    if len(closes) == 0:
        return pl.DataFrame(
            {"time": [], "open": [], "high": [], "low": [], "close": []}
        )

    # Initialize with first price
    current_price = closes[0]
    # Round to nearest brick
    base_price = round(current_price / brick_size) * brick_size

    bricks = []
    brick_times = []
    last_direction = 0  # 1 for up, -1 for down, 0 for initial

    for i, close in enumerate(closes):
        # Calculate how many bricks to add
        price_diff = close - base_price

        if abs(price_diff) >= brick_size:
            num_bricks = int(abs(price_diff) / brick_size)
            direction = 1 if price_diff > 0 else -1

            # Check for reversal (requires 2 bricks in opposite direction)
            if last_direction != 0 and direction != last_direction:
                if num_bricks < 2:
                    continue  # Not enough movement for reversal
                num_bricks -= 1  # Reversal costs one brick

            for _ in range(num_bricks):
                brick_open = base_price
                brick_close = base_price + (direction * brick_size)

                bricks.append(
                    {
                        "open": brick_open,
                        "close": brick_close,
                        "high": max(brick_open, brick_close),
                        "low": min(brick_open, brick_close),
                    }
                )
                brick_times.append(times[i])

                base_price = brick_close
                last_direction = direction

    if not bricks:
        # No bricks formed, return single brick from first to last price
        return pl.DataFrame(
            {
                "time": [times[0]],
                "open": [closes[0]],
                "high": [max(closes)],
                "low": [min(closes)],
                "close": [closes[-1]],
            }
        )

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
