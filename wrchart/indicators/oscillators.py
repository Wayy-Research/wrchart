"""
Oscillator indicators (plotted in separate pane).
"""

import polars as pl
from typing import Tuple


def rsi(
    df: pl.DataFrame,
    period: int = 14,
    time_col: str = "time",
    value_col: str = "close",
    output_col: str = "rsi",
) -> pl.DataFrame:
    """
    Relative Strength Index.

    RSI measures momentum on a scale of 0-100.
    - Above 70: Overbought
    - Below 30: Oversold

    Args:
        df: DataFrame with price data
        period: RSI period (default 14)
        time_col: Name of time column
        value_col: Name of value column
        output_col: Name for output column

    Returns:
        DataFrame with time and RSI columns
    """
    # Calculate price changes
    changes = df.select([
        pl.col(time_col),
        pl.col(value_col).diff().alias("change"),
    ])

    # Separate gains and losses
    result = changes.with_columns([
        pl.when(pl.col("change") > 0)
        .then(pl.col("change"))
        .otherwise(0)
        .alias("gain"),
        pl.when(pl.col("change") < 0)
        .then(-pl.col("change"))
        .otherwise(0)
        .alias("loss"),
    ])

    # Calculate average gain/loss using EMA
    result = result.with_columns([
        pl.col("gain").ewm_mean(span=period).alias("avg_gain"),
        pl.col("loss").ewm_mean(span=period).alias("avg_loss"),
    ])

    # Calculate RSI
    result = result.with_columns([
        (100 - (100 / (1 + pl.col("avg_gain") / pl.col("avg_loss").clip(lower_bound=0.0001))))
        .alias(output_col)
    ])

    return result.select([pl.col(time_col), pl.col(output_col)])


def macd(
    df: pl.DataFrame,
    fast_period: int = 12,
    slow_period: int = 26,
    signal_period: int = 9,
    time_col: str = "time",
    value_col: str = "close",
) -> pl.DataFrame:
    """
    Moving Average Convergence Divergence.

    Returns MACD line, signal line, and histogram.

    Args:
        df: DataFrame with price data
        fast_period: Fast EMA period (default 12)
        slow_period: Slow EMA period (default 26)
        signal_period: Signal line period (default 9)
        time_col: Name of time column
        value_col: Name of value column

    Returns:
        DataFrame with time, macd, signal, histogram columns
    """
    result = df.select([
        pl.col(time_col),
        (
            pl.col(value_col).ewm_mean(span=fast_period)
            - pl.col(value_col).ewm_mean(span=slow_period)
        ).alias("macd"),
    ])

    result = result.with_columns([
        pl.col("macd").ewm_mean(span=signal_period).alias("signal"),
    ])

    result = result.with_columns([
        (pl.col("macd") - pl.col("signal")).alias("histogram"),
    ])

    return result


def stochastic(
    df: pl.DataFrame,
    k_period: int = 14,
    d_period: int = 3,
    time_col: str = "time",
    high_col: str = "high",
    low_col: str = "low",
    close_col: str = "close",
) -> pl.DataFrame:
    """
    Stochastic Oscillator.

    Returns %K and %D lines on a scale of 0-100.
    - Above 80: Overbought
    - Below 20: Oversold

    Args:
        df: DataFrame with OHLC data
        k_period: %K period (default 14)
        d_period: %D smoothing period (default 3)
        time_col: Name of time column
        high_col: Name of high column
        low_col: Name of low column
        close_col: Name of close column

    Returns:
        DataFrame with time, k, d columns
    """
    result = df.select([
        pl.col(time_col),
        pl.col(high_col).rolling_max(k_period).alias("highest_high"),
        pl.col(low_col).rolling_min(k_period).alias("lowest_low"),
        pl.col(close_col).alias("close"),
    ])

    # %K = (Close - Lowest Low) / (Highest High - Lowest Low) * 100
    result = result.with_columns([
        (
            (pl.col("close") - pl.col("lowest_low"))
            / (pl.col("highest_high") - pl.col("lowest_low")).clip(lower_bound=0.0001)
            * 100
        ).alias("k"),
    ])

    # %D = SMA of %K
    result = result.with_columns([
        pl.col("k").rolling_mean(d_period).alias("d"),
    ])

    return result.select([pl.col(time_col), pl.col("k"), pl.col("d")])
