"""
Unified Chart class for wrchart.

Provides a single API that automatically selects the optimal rendering
backend based on data characteristics.
"""

from typing import Any, Dict, List, Optional, Union
import uuid

import polars as pl
import numpy as np

from wrchart.core.schema import DataSchema
from wrchart.core.themes import Theme, WayyTheme, resolve_theme
from wrchart.core.backends.base import Backend, BackendType, RenderConfig
from wrchart.core.backends.lightweight import LightweightChartsBackend
from wrchart.core.backends.webgl import WebGLBackend
from wrchart.core.backends.canvas import CanvasBackend
from wrchart.core.backends.multipanel import MultiPanelBackend


class Chart:
    """
    Unified chart with automatic backend selection.

    Pass your data and the chart figures out the best rendering approach:
    - Small OHLC data → Interactive Lightweight Charts
    - Large datasets (100k+) → GPU-accelerated WebGL
    - Forecast paths → Canvas density visualization
    - Multiple DataFrames → Multi-panel grid layout

    Example:
        >>> import wrchart as wrc
        >>> import polars as pl
        >>>
        >>> # Just pass your data - column names are auto-detected
        >>> df = pl.read_csv("prices.csv")
        >>> chart = wrc.Chart(df)
        >>> chart.show()
        >>>
        >>> # Or build incrementally
        >>> chart = wrc.Chart()
        >>> chart.add_candlestick(df)
        >>> chart.add_volume(df)
        >>> chart.show()
    """

    def __init__(
        self,
        data: Union[pl.DataFrame, List[pl.DataFrame], Dict, None] = None,
        width: int = 800,
        height: int = 600,
        theme: Union[str, Theme, None] = None,
        title: Optional[str] = None,
        backend: str = "auto",
    ):
        """
        Initialize a chart.

        Args:
            data: DataFrame, list of DataFrames, or forecast dict (optional)
            width: Chart width in pixels
            height: Chart height in pixels
            theme: Theme name ("wayy", "dark", "light") or Theme instance
            title: Optional chart title
            backend: Backend selection ("auto", "lightweight", "webgl", "canvas", "multipanel")
        """
        self._id = str(uuid.uuid4())[:8]
        self.width = width
        self.height = height
        self.theme = resolve_theme(theme)
        self.title = title

        # Create render config
        self._config = RenderConfig(
            width=width,
            height=height,
            theme=self.theme,
            title=title,
            chart_id=self._id,
        )

        # Select and create backend
        self._backend_type = Backend.select_backend(data, backend)
        self._backend = self._create_backend()

        # Auto-plot if data is provided
        if data is not None:
            self._auto_plot(data)

    def _create_backend(self) -> Backend:
        """Create the appropriate backend instance."""
        if self._backend_type == BackendType.LIGHTWEIGHT:
            return LightweightChartsBackend(self._config)
        elif self._backend_type == BackendType.WEBGL:
            return WebGLBackend(self._config)
        elif self._backend_type == BackendType.CANVAS:
            return CanvasBackend(self._config)
        elif self._backend_type == BackendType.MULTIPANEL:
            return MultiPanelBackend(self._config)
        else:
            return LightweightChartsBackend(self._config)

    def _auto_plot(self, data: Union[pl.DataFrame, List[pl.DataFrame], Dict]) -> None:
        """Automatically add data to the chart."""
        if isinstance(data, list) and all(isinstance(d, pl.DataFrame) for d in data):
            # Multi-panel: add each DataFrame as a panel
            for i, df in enumerate(data):
                chart_type = DataSchema.infer_chart_type(df)
                schema = DataSchema.detect(df)
                if chart_type == "candlestick":
                    cols = DataSchema.get_ohlc_cols(df)
                    self._backend.add_series(
                        df, "candlestick",
                        time_col=cols["time"],
                        open_col=cols["open"],
                        high_col=cols["high"],
                        low_col=cols["low"],
                        close_col=cols["close"],
                    )
                else:
                    self._backend.add_series(
                        df, "line",
                        time_col=DataSchema.get_time_col(df),
                        value_col=DataSchema.get_value_col(df),
                    )
        elif isinstance(data, dict) and "paths" in data:
            # Forecast data
            if isinstance(self._backend, CanvasBackend):
                historical = data.get("historical", np.zeros(10))
                paths = data["paths"]
                probs = data.get("probabilities")
                weighted = data.get("weighted_forecast")
                self._backend.set_forecast_data(historical, paths, probs, weighted)
        elif isinstance(data, pl.DataFrame):
            # Single DataFrame - detect type and plot
            chart_type = DataSchema.infer_chart_type(data)
            if chart_type == "candlestick":
                cols = DataSchema.get_ohlc_cols(data)
                self._backend.add_series(
                    data, "candlestick",
                    time_col=cols["time"],
                    open_col=cols["open"],
                    high_col=cols["high"],
                    low_col=cols["low"],
                    close_col=cols["close"],
                )
            elif chart_type == "line":
                self._backend.add_series(
                    data, "line",
                    time_col=DataSchema.get_time_col(data),
                    value_col=DataSchema.get_value_col(data),
                )

    # -------------------------------------------------------------------------
    # Series Methods
    # -------------------------------------------------------------------------

    def add_candlestick(
        self,
        data: pl.DataFrame,
        time_col: Optional[str] = None,
        open_col: Optional[str] = None,
        high_col: Optional[str] = None,
        low_col: Optional[str] = None,
        close_col: Optional[str] = None,
        **options,
    ) -> "Chart":
        """
        Add a candlestick series.

        Column names are auto-detected if not specified.

        Args:
            data: DataFrame with OHLC data
            time_col: Time column (auto-detected if None)
            open_col: Open column (auto-detected if None)
            high_col: High column (auto-detected if None)
            low_col: Low column (auto-detected if None)
            close_col: Close column (auto-detected if None)
            **options: Additional series options

        Returns:
            Self for chaining
        """
        cols = DataSchema.get_ohlc_cols(
            data,
            time=time_col,
            open_=open_col,
            high=high_col,
            low=low_col,
            close=close_col,
        )
        self._backend.add_series(
            data, "candlestick",
            time_col=cols["time"],
            open_col=cols["open"],
            high_col=cols["high"],
            low_col=cols["low"],
            close_col=cols["close"],
            **options,
        )
        return self

    def add_line(
        self,
        data: pl.DataFrame,
        time_col: Optional[str] = None,
        value_col: Optional[str] = None,
        **options,
    ) -> "Chart":
        """
        Add a line series.

        Args:
            data: DataFrame with time-value data
            time_col: Time column (auto-detected if None)
            value_col: Value column (auto-detected if None)
            **options: Additional series options

        Returns:
            Self for chaining
        """
        time_c = DataSchema.get_time_col(data, time_col)
        value_c = DataSchema.get_value_col(data, value_col)
        self._backend.add_series(data, "line", time_col=time_c, value_col=value_c, **options)
        return self

    def add_area(
        self,
        data: pl.DataFrame,
        time_col: Optional[str] = None,
        value_col: Optional[str] = None,
        **options,
    ) -> "Chart":
        """
        Add an area series.

        Args:
            data: DataFrame with time-value data
            time_col: Time column (auto-detected if None)
            value_col: Value column (auto-detected if None)
            **options: Additional series options

        Returns:
            Self for chaining
        """
        time_c = DataSchema.get_time_col(data, time_col)
        value_c = DataSchema.get_value_col(data, value_col)
        self._backend.add_series(data, "area", time_col=time_c, value_col=value_c, **options)
        return self

    def add_histogram(
        self,
        data: pl.DataFrame,
        time_col: Optional[str] = None,
        value_col: Optional[str] = None,
        color_col: Optional[str] = None,
        **options,
    ) -> "Chart":
        """
        Add a histogram series.

        Args:
            data: DataFrame with time-value data
            time_col: Time column (auto-detected if None)
            value_col: Value column (auto-detected if None)
            color_col: Optional column for per-bar colors
            **options: Additional series options

        Returns:
            Self for chaining
        """
        time_c = DataSchema.get_time_col(data, time_col)
        value_c = DataSchema.get_value_col(data, value_col)
        self._backend.add_series(
            data, "histogram",
            time_col=time_c,
            value_col=value_c,
            color_col=color_col,
            **options,
        )
        return self

    def add_volume(
        self,
        data: pl.DataFrame,
        time_col: Optional[str] = None,
        volume_col: Optional[str] = None,
        open_col: Optional[str] = None,
        close_col: Optional[str] = None,
        up_color: Optional[str] = None,
        down_color: Optional[str] = None,
    ) -> "Chart":
        """
        Add a volume histogram with up/down coloring.

        Args:
            data: DataFrame with OHLCV data
            time_col: Time column (auto-detected if None)
            volume_col: Volume column (auto-detected if None)
            open_col: Open column for color determination
            close_col: Close column for color determination
            up_color: Color for up bars
            down_color: Color for down bars

        Returns:
            Self for chaining
        """
        schema = DataSchema.detect(data)
        time_c = time_col or schema["time"] or "time"
        vol_c = volume_col or schema["volume"] or "volume"
        open_c = open_col or schema["open"] or "open"
        close_c = close_col or schema["close"] or "close"

        if isinstance(self._backend, LightweightChartsBackend):
            self._backend.add_volume(
                data,
                time_col=time_c,
                volume_col=vol_c,
                open_col=open_c,
                close_col=close_c,
                up_color=up_color,
                down_color=down_color,
            )
        return self

    # -------------------------------------------------------------------------
    # Annotation Methods
    # -------------------------------------------------------------------------

    def add_marker(
        self,
        time: Any,
        position: str = "aboveBar",
        shape: str = "circle",
        color: Optional[str] = None,
        text: str = "",
        size: int = 1,
    ) -> "Chart":
        """
        Add a marker to the chart.

        Args:
            time: Time value for the marker
            position: Marker position (aboveBar, belowBar, inBar)
            shape: Marker shape (circle, square, arrowUp, arrowDown)
            color: Marker color
            text: Marker text
            size: Marker size multiplier

        Returns:
            Self for chaining
        """
        self._backend.add_marker(time, position, shape, color, text, size)
        return self

    def add_horizontal_line(
        self,
        price: float,
        color: Optional[str] = None,
        line_width: int = 1,
        line_style: int = 0,
        label: str = "",
        label_visible: bool = True,
    ) -> "Chart":
        """
        Add a horizontal price line.

        Args:
            price: Price level
            color: Line color
            line_width: Line width in pixels
            line_style: Line style (0=solid, 1=dotted, 2=dashed)
            label: Label text
            label_visible: Whether to show the label

        Returns:
            Self for chaining
        """
        self._backend.add_horizontal_line(price, color, line_width, line_style, label, label_visible)
        return self

    def add_drawing(self, drawing: Any) -> "Chart":
        """
        Add a drawing annotation.

        Args:
            drawing: Drawing object (TrendLine, Rectangle, etc.)

        Returns:
            Self for chaining
        """
        self._backend.add_drawing(drawing)
        return self

    # -------------------------------------------------------------------------
    # Output Methods
    # -------------------------------------------------------------------------

    def to_json(self) -> str:
        """Generate JSON configuration."""
        return self._backend.to_json()

    def to_html(self) -> str:
        """Generate HTML for rendering."""
        return self._backend.to_html()

    def _repr_html_(self) -> str:
        """Jupyter notebook HTML representation."""
        return self._backend.to_html()

    def show(self) -> None:
        """
        Display the chart.

        In Jupyter, renders inline. Outside Jupyter, opens in browser.
        """
        self._backend.show()

    def streamlit(self, height: Optional[int] = None) -> None:
        """
        Display the chart in Streamlit.

        Args:
            height: Optional height override
        """
        self._backend.streamlit(height)


# -------------------------------------------------------------------------
# Quick-Plot Functions
# -------------------------------------------------------------------------

def candlestick(
    data: pl.DataFrame,
    width: int = 800,
    height: int = 600,
    theme: Union[str, Theme, None] = None,
    title: Optional[str] = None,
) -> Chart:
    """
    Create a candlestick chart from OHLC data.

    Args:
        data: DataFrame with OHLC columns
        width: Chart width
        height: Chart height
        theme: Theme name or Theme instance
        title: Chart title

    Returns:
        Chart instance
    """
    chart = Chart(width=width, height=height, theme=theme, title=title, backend="lightweight")
    chart.add_candlestick(data)
    return chart


def line(
    data: pl.DataFrame,
    width: int = 800,
    height: int = 600,
    theme: Union[str, Theme, None] = None,
    title: Optional[str] = None,
) -> Chart:
    """
    Create a line chart.

    Args:
        data: DataFrame with time-value columns
        width: Chart width
        height: Chart height
        theme: Theme name or Theme instance
        title: Chart title

    Returns:
        Chart instance
    """
    chart = Chart(width=width, height=height, theme=theme, title=title, backend="lightweight")
    chart.add_line(data)
    return chart


def area(
    data: pl.DataFrame,
    width: int = 800,
    height: int = 600,
    theme: Union[str, Theme, None] = None,
    title: Optional[str] = None,
) -> Chart:
    """
    Create an area chart.

    Args:
        data: DataFrame with time-value columns
        width: Chart width
        height: Chart height
        theme: Theme name or Theme instance
        title: Chart title

    Returns:
        Chart instance
    """
    chart = Chart(width=width, height=height, theme=theme, title=title, backend="lightweight")
    chart.add_area(data)
    return chart


def forecast(
    paths: np.ndarray,
    historical: Union[np.ndarray, pl.Series, List],
    probabilities: Optional[np.ndarray] = None,
    weighted_forecast: Optional[np.ndarray] = None,
    width: int = 1000,
    height: int = 600,
    theme: Union[str, Theme, None] = "dark",
    title: Optional[str] = None,
) -> Chart:
    """
    Create a forecast visualization with Monte Carlo paths.

    Args:
        paths: Monte Carlo paths (n_paths, n_steps)
        historical: Historical price data
        probabilities: Path probabilities (optional)
        weighted_forecast: Weighted forecast line (optional)
        width: Chart width
        height: Chart height
        theme: Theme name or Theme instance
        title: Chart title

    Returns:
        Chart instance
    """
    data = {
        "paths": paths,
        "historical": historical,
        "probabilities": probabilities,
        "weighted_forecast": weighted_forecast,
    }
    chart = Chart(data, width=width, height=height, theme=theme, title=title, backend="canvas")
    return chart


def dashboard(
    dataframes: List[pl.DataFrame],
    rows: int = None,
    cols: int = None,
    width: int = 1200,
    height: int = 800,
    theme: Union[str, Theme, None] = None,
    title: Optional[str] = None,
) -> Chart:
    """
    Create a multi-panel dashboard from multiple DataFrames.

    Args:
        dataframes: List of DataFrames to display
        rows: Number of rows (auto-calculated if None)
        cols: Number of columns (auto-calculated if None)
        width: Total width
        height: Total height
        theme: Theme name or Theme instance
        title: Dashboard title

    Returns:
        Chart instance
    """
    n = len(dataframes)
    if cols is None:
        cols = min(3, n)
    if rows is None:
        rows = (n + cols - 1) // cols

    chart = Chart(dataframes, width=width, height=height, theme=theme, title=title, backend="multipanel")
    if isinstance(chart._backend, MultiPanelBackend):
        chart._backend.set_grid(rows=rows, cols=cols)
    return chart
