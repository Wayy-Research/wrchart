"""
Overlay indicators (plotted on price chart).
"""

import polars as pl
from typing import Tuple


def sma(
    df: pl.DataFrame,
    period: int,
    time_col: str = "time",
    value_col: str = "close",
    output_col: str = "sma",
) -> pl.DataFrame:
    """
    Simple Moving Average.

    Args:
        df: DataFrame with price data
        period: Number of periods for the average
        time_col: Name of time column
        value_col: Name of value column to average
        output_col: Name for output column

    Returns:
        DataFrame with time and SMA columns
    """
    return df.select([
        pl.col(time_col),
        pl.col(value_col).rolling_mean(period).alias(output_col),
    ])


def ema(
    df: pl.DataFrame,
    period: int,
    time_col: str = "time",
    value_col: str = "close",
    output_col: str = "ema",
) -> pl.DataFrame:
    """
    Exponential Moving Average.

    Args:
        df: DataFrame with price data
        period: Number of periods for the average
        time_col: Name of time column
        value_col: Name of value column
        output_col: Name for output column

    Returns:
        DataFrame with time and EMA columns
    """
    return df.select([
        pl.col(time_col),
        pl.col(value_col).ewm_mean(span=period).alias(output_col),
    ])


def wma(
    df: pl.DataFrame,
    period: int,
    time_col: str = "time",
    value_col: str = "close",
    output_col: str = "wma",
) -> pl.DataFrame:
    """
    Weighted Moving Average.

    More recent values have higher weights.

    Args:
        df: DataFrame with price data
        period: Number of periods
        time_col: Name of time column
        value_col: Name of value column
        output_col: Name for output column

    Returns:
        DataFrame with time and WMA columns
    """
    # Calculate weights: 1, 2, 3, ..., period
    weights = list(range(1, period + 1))
    weight_sum = sum(weights)

    # Use rolling apply with weighted calculation
    values = df[value_col].to_list()
    n = len(values)
    wma_values = [None] * n

    for i in range(period - 1, n):
        weighted_sum = sum(
            values[i - period + 1 + j] * weights[j] for j in range(period)
        )
        wma_values[i] = weighted_sum / weight_sum

    return pl.DataFrame({
        time_col: df[time_col],
        output_col: wma_values,
    })


def bollinger_bands(
    df: pl.DataFrame,
    period: int = 20,
    std_dev: float = 2.0,
    time_col: str = "time",
    value_col: str = "close",
) -> pl.DataFrame:
    """
    Bollinger Bands.

    Returns middle band (SMA), upper band, and lower band.

    Args:
        df: DataFrame with price data
        period: Period for the moving average
        std_dev: Number of standard deviations for bands
        time_col: Name of time column
        value_col: Name of value column

    Returns:
        DataFrame with time, middle, upper, lower columns
    """
    return df.select([
        pl.col(time_col),
        pl.col(value_col).rolling_mean(period).alias("middle"),
        (
            pl.col(value_col).rolling_mean(period)
            + std_dev * pl.col(value_col).rolling_std(period)
        ).alias("upper"),
        (
            pl.col(value_col).rolling_mean(period)
            - std_dev * pl.col(value_col).rolling_std(period)
        ).alias("lower"),
    ])
