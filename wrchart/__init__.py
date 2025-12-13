"""
wrchart - Interactive financial charting for Python

A Polars-native charting library with TradingView-style aesthetics,
supporting standard and non-standard chart types (Renko, Kagi, P&F, etc.)
and GPU-accelerated high-frequency data visualization.
"""

from wrchart.core.chart import Chart
from wrchart.core.webgl_chart import WebGLChart
from wrchart.core.series import (
    CandlestickSeries,
    LineSeries,
    AreaSeries,
    HistogramSeries,
    ScatterSeries,
)
from wrchart.core.themes import WayyTheme, DarkTheme, LightTheme

from wrchart.transforms.heikin_ashi import to_heikin_ashi
from wrchart.transforms.renko import to_renko
from wrchart.transforms.kagi import to_kagi
from wrchart.transforms.pnf import to_point_and_figure
from wrchart.transforms.line_break import to_line_break
from wrchart.transforms.range_bar import to_range_bars
from wrchart.transforms.decimation import lttb_downsample, adaptive_downsample

__version__ = "0.1.0"

__all__ = [
    # Core
    "Chart",
    "WebGLChart",
    # Series
    "CandlestickSeries",
    "LineSeries",
    "AreaSeries",
    "HistogramSeries",
    "ScatterSeries",
    # Themes
    "WayyTheme",
    "DarkTheme",
    "LightTheme",
    # Transforms
    "to_heikin_ashi",
    "to_renko",
    "to_kagi",
    "to_point_and_figure",
    "to_line_break",
    "to_range_bars",
    "lttb_downsample",
    "adaptive_downsample",
]
