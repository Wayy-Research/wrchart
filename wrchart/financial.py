"""
wrchart.financial - Financial chart helpers

High-level chart functions for common financial visualizations:
- returns_distribution: Histogram of returns with statistics
- price_with_indicator: Price line with indicator overlay
- indicator_panels: Stacked indicator panels
"""

import numpy as np
import polars as pl
from typing import Optional, List, Dict, Any, Tuple, Union

from wrchart.core.chart import Chart
from wrchart.core.themes import WayyTheme, Theme


def _to_numpy(data) -> np.ndarray:
    """Convert to numpy array."""
    if hasattr(data, 'to_numpy'):
        return data.to_numpy()
    elif hasattr(data, 'values'):
        return data.values
    elif isinstance(data, list):
        return np.array(data)
    return np.asarray(data)


def _to_timestamps(timestamps) -> list:
    """Convert timestamps to Unix seconds."""
    if timestamps is None:
        return None

    ts = _to_numpy(timestamps)

    if np.issubdtype(ts.dtype, np.number):
        return [int(t) for t in ts]

    if np.issubdtype(ts.dtype, np.datetime64):
        return [int(t.astype('datetime64[s]').astype(int)) for t in ts]

    try:
        return [int(t.timestamp()) for t in ts]
    except:
        return list(range(len(ts)))


def returns_distribution(
    returns,
    bins: int = 100,
    title: Optional[str] = None,
    width: int = 900,
    height: int = 300,
    color: str = "#2196F3",
    theme: Optional[Theme] = None,
) -> Chart:
    """
    Create a returns distribution histogram.

    Args:
        returns: Array of returns
        bins: Number of histogram bins
        title: Chart title (auto-generated with stats if None)
        width: Chart width
        height: Chart height
        color: Histogram color
        theme: Chart theme (defaults to DarkTheme)

    Returns:
        wrchart.Chart

    Example:
        returns = prices.pct_change().dropna()
        returns_distribution(returns, title="Daily Returns").show()
    """
    returns_arr = _to_numpy(returns)

    # Compute statistics
    mean_ret = np.mean(returns_arr)
    std_ret = np.std(returns_arr)

    # Compute histogram
    counts, bin_edges = np.histogram(returns_arr, bins=bins)
    bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2

    # Auto-generate title with stats
    if title is None:
        title = f"Returns Distribution | Mean: {mean_ret:.4%} | Std: {std_ret:.4%}"

    # Create dataframe
    df = pl.DataFrame({
        "time": list(range(len(bin_centers))),
        "count": counts.astype(float)
    })

    chart = Chart(width=width, height=height, theme=theme or WayyTheme, title=title)
    chart.add_histogram(df, time_col="time", value_col="count", color=color)

    return chart


def price_with_indicator(
    prices,
    timestamps=None,
    indicators: Optional[Dict[str, Tuple[Any, str]]] = None,
    title: str = "Price",
    width: int = 900,
    height: int = 400,
    price_color: str = "#2196F3",
    theme: Optional[Theme] = None,
) -> Chart:
    """
    Create a price chart with indicator overlays.

    Args:
        prices: Price array
        timestamps: Optional timestamps
        indicators: Dict of {name: (values, color)} for overlay indicators
        title: Chart title
        width: Chart width
        height: Chart height
        price_color: Color for price line
        theme: Chart theme

    Returns:
        wrchart.Chart

    Example:
        price_with_indicator(
            prices, timestamps,
            indicators={'KAMA': (kama_values, '#E53935'), 'SMA': (sma_values, '#00C853')}
        ).show()
    """
    prices_arr = _to_numpy(prices)
    n = len(prices_arr)
    ts = _to_timestamps(timestamps) if timestamps is not None else list(range(n))

    df = pl.DataFrame({"time": ts, "price": prices_arr})

    chart = Chart(width=width, height=height, theme=theme or WayyTheme, title=title)
    chart.add_line(df, time_col="time", value_col="price", color=price_color)

    # Add indicators
    if indicators:
        for name, (values, color) in indicators.items():
            ind_arr = _to_numpy(values)
            df_ind = pl.DataFrame({"time": ts, name: ind_arr})
            chart.add_line(df_ind, time_col="time", value_col=name, color=color)

    return chart


def indicator_panels(
    timestamps,
    panels: List[Dict[str, Any]],
    width: int = 900,
    panel_height: int = 200,
    theme: Optional[Theme] = None,
) -> List[Chart]:
    """
    Create multiple indicator panels.

    Each panel can have multiple series (lines, areas, histograms).

    Args:
        timestamps: Shared timestamps
        panels: List of panel configurations:
            {
                'title': str,
                'series': {name: (values, color, type)},  # type: 'line', 'area', 'histogram'
                'h_lines': [(value, color), ...],  # optional horizontal lines
                'y_range': (min, max),  # optional y-axis range
            }
        width: Chart width
        panel_height: Height per panel
        theme: Chart theme

    Returns:
        List of wrchart.Chart objects

    Example:
        panels = [
            {
                'title': 'Price vs KAMA',
                'series': {
                    'Price': (prices, '#2196F3', 'line'),
                    'KAMA': (kama, '#E53935', 'line'),
                }
            },
            {
                'title': 'Efficiency Ratio',
                'series': {'ER': (er, '#9C27B0', 'line')},
                'h_lines': [(0.5, '#666666')],
            },
            {
                'title': 'Position',
                'series': {'Signal': (signals, '#00C853', 'histogram')},
            }
        ]
        charts = indicator_panels(timestamps, panels)
        for c in charts:
            c.show()
    """
    ts = _to_timestamps(timestamps)
    chart_theme = theme or WayyTheme
    charts = []

    for panel in panels:
        title = panel.get('title', '')
        series = panel.get('series', {})
        h_lines = panel.get('h_lines', [])

        chart = Chart(width=width, height=panel_height, theme=chart_theme, title=title)

        for name, config in series.items():
            values, color, series_type = config
            values_arr = _to_numpy(values)
            df = pl.DataFrame({"time": ts, name: values_arr})

            if series_type == 'line':
                chart.add_line(df, time_col="time", value_col=name, color=color)
            elif series_type == 'area':
                chart.add_area(df, time_col="time", value_col=name,
                              line_color=color,
                              top_color=f"{color}22",
                              bottom_color=f"{color}88")
            elif series_type == 'histogram':
                chart.add_histogram(df, time_col="time", value_col=name, color=color)

        for val, color in h_lines:
            chart.add_horizontal_line(val, color=color, line_style=2)

        charts.append(chart)

    return charts


def equity_curve(
    returns,
    timestamps=None,
    benchmark_returns=None,
    title: Optional[str] = None,
    width: int = 900,
    height: int = 400,
    theme: Optional[Theme] = None,
) -> Chart:
    """
    Create an equity curve chart (starts at 0).

    Args:
        returns: Strategy returns
        timestamps: Optional timestamps
        benchmark_returns: Optional benchmark returns
        title: Chart title
        width: Chart width
        height: Chart height
        theme: Chart theme

    Returns:
        wrchart.Chart
    """
    returns_arr = _to_numpy(returns)
    n = len(returns_arr)
    ts = _to_timestamps(timestamps) if timestamps is not None else list(range(n))

    # Equity = cumsum of returns, prepend 0 so it truly starts at 0
    cumulative = np.cumsum(returns_arr)
    equity = np.concatenate([[0], cumulative])
    total_return = equity[-1] if len(equity) > 0 else 0

    # Extend timestamps to match equity length
    if len(ts) > 0:
        t0 = ts[0] - 1 if isinstance(ts[0], (int, float)) else 0
        equity_ts = [t0] + list(ts)
    else:
        equity_ts = list(range(len(equity)))

    # Sharpe
    ann = 252 * 24  # Assume hourly
    ann_ret = np.mean(returns_arr) * ann
    ann_vol = np.std(returns_arr) * np.sqrt(ann)
    sharpe = ann_ret / ann_vol if ann_vol > 0 else 0

    if title is None:
        title = f"Equity Curve | Return: {total_return:.2%} | Sharpe: {sharpe:.2f}"

    df = pl.DataFrame({"time": equity_ts, "equity": equity})

    chart = Chart(width=width, height=height, theme=theme or WayyTheme, title=title, value_format="percent")
    chart.add_line(df, time_col="time", value_col="equity", color="#22863a")  # Green for equity

    # Benchmark (also starts at 0)
    if benchmark_returns is not None:
        bench_arr = _to_numpy(benchmark_returns)
        bench_cumulative = np.cumsum(bench_arr)
        bench_equity = np.concatenate([[0], bench_cumulative])
        df_b = pl.DataFrame({"time": equity_ts, "benchmark": bench_equity})
        chart.add_line(df_b, time_col="time", value_col="benchmark", color="#888888")

    chart.add_horizontal_line(0, color="#e0e0e0", line_style=0)

    return chart


def drawdown_chart(
    returns,
    timestamps=None,
    title: Optional[str] = None,
    width: int = 900,
    height: int = 300,
    theme: Optional[Theme] = None,
) -> Chart:
    """
    Create a drawdown chart (starts at 0).

    Args:
        returns: Strategy returns
        timestamps: Optional timestamps
        title: Chart title
        width: Chart width
        height: Chart height
        theme: Chart theme

    Returns:
        wrchart.Chart
    """
    returns_arr = _to_numpy(returns)
    n = len(returns_arr)
    ts = _to_timestamps(timestamps) if timestamps is not None else list(range(n))

    # Compute drawdown (prepend 0 so it truly starts at 0)
    cumulative = np.cumsum(returns_arr)
    equity = np.concatenate([[0], cumulative])
    running_max = np.maximum.accumulate(equity)
    drawdown = equity - running_max
    max_dd = np.min(drawdown)

    # Extend timestamps to match drawdown length
    if len(ts) > 0:
        t0 = ts[0] - 1 if isinstance(ts[0], (int, float)) else 0
        drawdown_ts = [t0] + list(ts)
    else:
        drawdown_ts = list(range(len(drawdown)))

    if title is None:
        title = f"Drawdown | Max: {max_dd:.2%}"

    df = pl.DataFrame({"time": drawdown_ts, "drawdown": drawdown})

    chart = Chart(width=width, height=height, theme=theme or WayyTheme, title=title, value_format="percent")
    chart.add_area(df, time_col="time", value_col="drawdown",
                   line_color="#E53935",
                   top_color="rgba(229,57,53,0.1)",
                   bottom_color="rgba(229,57,53,0.4)")
    chart.add_horizontal_line(0, color="#e0e0e0", line_style=0)

    return chart


def rolling_sharpe(
    returns,
    timestamps=None,
    window: int = 252 * 24,
    title: Optional[str] = None,
    width: int = 900,
    height: int = 300,
    theme: Optional[Theme] = None,
) -> Chart:
    """
    Create a rolling Sharpe ratio chart.

    Args:
        returns: Strategy returns
        timestamps: Optional timestamps
        window: Rolling window size
        title: Chart title
        width: Chart width
        height: Chart height
        theme: Chart theme

    Returns:
        wrchart.Chart
    """
    returns_arr = _to_numpy(returns)
    n = len(returns_arr)
    ts = _to_timestamps(timestamps) if timestamps is not None else list(range(n))

    ann = 252 * 24
    actual_window = min(window, n // 2)

    rolling = np.full(n, np.nan)
    for i in range(actual_window, n):
        w = returns_arr[i - actual_window:i]
        m = np.mean(w) * ann
        s = np.std(w) * np.sqrt(ann)
        if s > 0:
            rolling[i] = m / s

    # Filter valid
    mask = ~np.isnan(rolling)
    valid_ts = [ts[i] for i in range(n) if mask[i]]
    valid_sr = rolling[mask]

    if title is None:
        years = actual_window / ann
        title = f"Rolling Sharpe | {years:.1f}Y Window"

    df = pl.DataFrame({"time": valid_ts, "sharpe": valid_sr})

    chart = Chart(width=width, height=height, theme=theme or WayyTheme, title=title)
    chart.add_line(df, time_col="time", value_col="sharpe", color="#000000")
    chart.add_horizontal_line(0, color="#e0e0e0", line_style=0)
    chart.add_horizontal_line(1.0, color="#888888", line_style=2)
    chart.add_horizontal_line(2.0, color="#E53935", line_style=2)

    return chart
