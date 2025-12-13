"""
Data decimation algorithms for high-frequency data visualization.

LTTB (Largest Triangle Three Buckets) preserves visual shape while
dramatically reducing point count.
"""

import polars as pl
import numpy as np
from typing import Optional


def lttb_downsample(
    df: pl.DataFrame,
    time_col: str = "time",
    value_col: str = "value",
    target_points: int = 1000,
) -> pl.DataFrame:
    """
    Downsample time series data using LTTB algorithm.

    LTTB (Largest Triangle Three Buckets) is a downsampling algorithm
    that preserves the visual shape of the data by selecting points
    that form the largest triangle area with their neighbors.

    This is ideal for:
    - High-frequency tick data
    - Long time series that would be slow to render
    - Zoom-dependent detail levels

    Args:
        df: Polars DataFrame with time and value columns
        time_col: Name of the time column
        value_col: Name of the value column
        target_points: Desired number of output points

    Returns:
        Downsampled DataFrame with same columns

    Example:
        >>> import wrchart as wrc
        >>> import polars as pl
        >>>
        >>> # 1 million tick data points
        >>> ticks = pl.DataFrame({
        ...     "time": range(1_000_000),
        ...     "price": np.random.randn(1_000_000).cumsum()
        ... })
        >>>
        >>> # Downsample to 2000 points for display
        >>> display_data = wrc.lttb_downsample(ticks, "time", "price", 2000)
    """
    n = len(df)

    # If already small enough, return as-is
    if n <= target_points:
        return df

    # Extract numpy arrays for fast processing
    times = df[time_col].to_numpy()
    values = df[value_col].to_numpy()

    # Handle datetime conversion
    if df[time_col].dtype == pl.Datetime:
        times = times.astype(np.int64)

    # LTTB algorithm
    selected_indices = _lttb_indices(times, values, target_points)

    # Return filtered dataframe
    return df[selected_indices]


def _lttb_indices(
    times: np.ndarray, values: np.ndarray, target_points: int
) -> np.ndarray:
    """
    Core LTTB algorithm returning indices of selected points.

    Args:
        times: Array of time values
        values: Array of data values
        target_points: Number of points to select

    Returns:
        Array of indices to keep
    """
    n = len(times)

    if n <= target_points:
        return np.arange(n)

    # Always keep first and last points
    selected = [0]

    # Bucket size
    bucket_size = (n - 2) / (target_points - 2)

    # Previous selected point
    prev_idx = 0

    for i in range(target_points - 2):
        # Current bucket bounds
        bucket_start = int((i + 1) * bucket_size) + 1
        bucket_end = int((i + 2) * bucket_size) + 1
        bucket_end = min(bucket_end, n - 1)

        # Next bucket average (for triangle calculation)
        next_bucket_start = bucket_end
        next_bucket_end = int((i + 3) * bucket_size) + 1
        next_bucket_end = min(next_bucket_end, n)

        if next_bucket_start < next_bucket_end:
            avg_time = np.mean(times[next_bucket_start:next_bucket_end])
            avg_value = np.mean(values[next_bucket_start:next_bucket_end])
        else:
            avg_time = times[-1]
            avg_value = values[-1]

        # Find point in current bucket that forms largest triangle
        max_area = -1
        max_idx = bucket_start

        prev_time = times[prev_idx]
        prev_value = values[prev_idx]

        for j in range(bucket_start, bucket_end):
            # Triangle area calculation (simplified, no sqrt needed for comparison)
            area = abs(
                (prev_time - avg_time) * (values[j] - prev_value)
                - (prev_time - times[j]) * (avg_value - prev_value)
            )

            if area > max_area:
                max_area = area
                max_idx = j

        selected.append(max_idx)
        prev_idx = max_idx

    # Always include last point
    selected.append(n - 1)

    return np.array(selected)


def adaptive_downsample(
    df: pl.DataFrame,
    time_col: str = "time",
    value_col: str = "value",
    viewport_start: Optional[float] = None,
    viewport_end: Optional[float] = None,
    target_points: int = 1000,
    min_bucket_size: int = 1,
) -> pl.DataFrame:
    """
    Adaptively downsample based on viewport.

    Provides higher resolution in the visible viewport and lower
    resolution outside it.

    Args:
        df: Polars DataFrame
        time_col: Name of time column
        value_col: Name of value column
        viewport_start: Start of visible range (optional)
        viewport_end: End of visible range (optional)
        target_points: Total target points
        min_bucket_size: Minimum points per bucket

    Returns:
        Adaptively downsampled DataFrame
    """
    if viewport_start is None or viewport_end is None:
        # No viewport, use regular LTTB
        return lttb_downsample(df, time_col, value_col, target_points)

    # Split data into viewport and outside
    in_viewport = df.filter(
        (pl.col(time_col) >= viewport_start) & (pl.col(time_col) <= viewport_end)
    )
    before_viewport = df.filter(pl.col(time_col) < viewport_start)
    after_viewport = df.filter(pl.col(time_col) > viewport_end)

    # Allocate more points to viewport
    viewport_ratio = 0.8
    viewport_points = int(target_points * viewport_ratio)
    outside_points = target_points - viewport_points

    before_points = int(outside_points * len(before_viewport) / max(1, len(before_viewport) + len(after_viewport)))
    after_points = outside_points - before_points

    # Downsample each section
    results = []

    if len(before_viewport) > 0:
        results.append(
            lttb_downsample(before_viewport, time_col, value_col, max(2, before_points))
        )

    if len(in_viewport) > 0:
        results.append(
            lttb_downsample(in_viewport, time_col, value_col, max(2, viewport_points))
        )

    if len(after_viewport) > 0:
        results.append(
            lttb_downsample(after_viewport, time_col, value_col, max(2, after_points))
        )

    if results:
        return pl.concat(results)
    else:
        return df
