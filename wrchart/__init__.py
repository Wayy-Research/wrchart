"""
wrchart - Interactive financial charting for Python

A Polars-native charting library with TradingView-style aesthetics,
supporting standard and non-standard chart types (Renko, Kagi, P&F, etc.)
and GPU-accelerated high-frequency data visualization.

Quick Start:
    >>> import wrchart as wrc
    >>> import polars as pl
    >>>
    >>> # Just pass your data - it figures out the rest
    >>> df = pl.read_csv("prices.csv")
    >>> wrc.Chart(df).show()
    >>>
    >>> # Or use quick-plot functions
    >>> wrc.candlestick(df).show()
    >>> wrc.line(df).show()
"""

import warnings

# Unified Chart API
from wrchart.core.chart import (
    Chart,
    # Quick-plot functions
    candlestick,
    line,
    area,
    forecast,
    dashboard,
)

# Column auto-detection
from wrchart.core.schema import DataSchema

# Themes - both class names and string shortcuts
from wrchart.core.themes import (
    Theme,
    WayyTheme,
    DarkTheme,
    LightTheme,
    WAYY,
    DARK,
    LIGHT,
    get_theme,
    resolve_theme,
)

# Series types (still available for advanced usage)
from wrchart.core.series import (
    CandlestickSeries,
    LineSeries,
    AreaSeries,
    HistogramSeries,
    ScatterSeries,
)

# Transforms
from wrchart.transforms.heikin_ashi import to_heikin_ashi
from wrchart.transforms.renko import to_renko
from wrchart.transforms.kagi import to_kagi
from wrchart.transforms.pnf import to_point_and_figure
from wrchart.transforms.line_break import to_line_break
from wrchart.transforms.range_bar import to_range_bars
from wrchart.transforms.decimation import lttb_downsample, adaptive_downsample

# Forecast visualization
from wrchart.forecast import (
    ForecastChart,
    VIRIDIS,
    PLASMA,
    INFERNO,
    HOT,
    density_to_color,
    compute_path_density,
    compute_path_colors_by_density,
)

# Multi-panel layouts
from wrchart.multipanel import (
    MultiPanelChart,
    Panel,
    LinePanel,
    BarPanel,
    HeatmapPanel,
    GaugePanel,
    AreaPanel,
)

# Financial chart helpers
from wrchart.financial import (
    returns_distribution,
    price_with_indicator,
    indicator_panels,
    equity_curve,
    drawdown_chart,
    rolling_sharpe,
)

# Drawing tools
from wrchart.drawing.tools import (
    BaseDrawing,
    HorizontalLine,
    VerticalLine,
    TrendLine,
    Ray,
    Rectangle,
    Arrow,
    Text,
    PriceRange,
    FibonacciRetracement,
    FibonacciExtension,
    export_drawings,
    import_drawings,
)


# -------------------------------------------------------------------------
# Deprecation Wrappers
# -------------------------------------------------------------------------

class WebGLChart(Chart):
    """
    Deprecated: Use Chart() which auto-selects the WebGL backend for large data.

    This class is provided for backward compatibility and will be removed
    in a future version.
    """

    def __init__(self, *args, **kwargs):
        warnings.warn(
            "WebGLChart is deprecated. Use Chart() which auto-selects the optimal backend. "
            "For explicit WebGL, use Chart(backend='webgl').",
            DeprecationWarning,
            stacklevel=2,
        )
        kwargs["backend"] = "webgl"
        super().__init__(*args, **kwargs)


# -------------------------------------------------------------------------
# Live streaming (optional - requires websockets)
# -------------------------------------------------------------------------

try:
    from wrchart.live import (
        LiveChart,
        LiveTable,
        LiveDashboard,
        LiveServer,
    )
    _HAS_LIVE = True
except ImportError:
    _HAS_LIVE = False
    LiveChart = None
    LiveTable = None
    LiveDashboard = None
    LiveServer = None


__version__ = "0.2.0"

__all__ = [
    # Core - Unified API
    "Chart",
    # Quick-plot functions
    "candlestick",
    "line",
    "area",
    "forecast",
    "dashboard",
    # Schema
    "DataSchema",
    # Themes
    "Theme",
    "WayyTheme",
    "DarkTheme",
    "LightTheme",
    "WAYY",
    "DARK",
    "LIGHT",
    "get_theme",
    "resolve_theme",
    # Series (advanced)
    "CandlestickSeries",
    "LineSeries",
    "AreaSeries",
    "HistogramSeries",
    "ScatterSeries",
    # Transforms
    "to_heikin_ashi",
    "to_renko",
    "to_kagi",
    "to_point_and_figure",
    "to_line_break",
    "to_range_bars",
    "lttb_downsample",
    "adaptive_downsample",
    # Forecast
    "ForecastChart",
    "VIRIDIS",
    "PLASMA",
    "INFERNO",
    "HOT",
    "density_to_color",
    "compute_path_density",
    "compute_path_colors_by_density",
    # Multi-panel
    "MultiPanelChart",
    "Panel",
    "LinePanel",
    "BarPanel",
    "HeatmapPanel",
    "GaugePanel",
    "AreaPanel",
    # Drawing tools
    "BaseDrawing",
    "HorizontalLine",
    "VerticalLine",
    "TrendLine",
    "Ray",
    "Rectangle",
    "Arrow",
    "Text",
    "PriceRange",
    "FibonacciRetracement",
    "FibonacciExtension",
    "export_drawings",
    "import_drawings",
    # Live streaming
    "LiveChart",
    "LiveTable",
    "LiveDashboard",
    "LiveServer",
    # Financial helpers
    "returns_distribution",
    "price_with_indicator",
    "indicator_panels",
    "equity_curve",
    "drawdown_chart",
    "rolling_sharpe",
    # Deprecated (still exported for backward compatibility)
    "WebGLChart",
]
