"""
Base backend interface for chart rendering.

All backends implement this interface to provide consistent chart rendering
across different technologies (Lightweight Charts, WebGL, Canvas, etc.).
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Union

import polars as pl

from wrchart.core.themes import Theme, WayyTheme


class BackendType(Enum):
    """Types of rendering backends."""

    LIGHTWEIGHT = auto()  # TradingView's Lightweight Charts
    WEBGL = auto()  # GPU-accelerated WebGL
    CANVAS = auto()  # HTML5 Canvas (for forecasts)
    MULTIPANEL = auto()  # Multi-panel grid layout


@dataclass
class RenderConfig:
    """Configuration for chart rendering."""

    width: int = 800
    height: int = 600
    theme: Theme = field(default_factory=lambda: WayyTheme)
    title: Optional[str] = None
    chart_id: str = ""


class Backend(ABC):
    """
    Abstract base class for chart rendering backends.

    Each backend handles a specific rendering technology and provides
    methods to add data, configure options, and generate output.
    """

    def __init__(self, config: Optional[RenderConfig] = None):
        """
        Initialize the backend.

        Args:
            config: Rendering configuration
        """
        self.config = config or RenderConfig()
        self._series_data: List[Dict[str, Any]] = []
        self._markers: List[Dict[str, Any]] = []
        self._price_lines: List[Dict[str, Any]] = []
        self._drawings: List[Any] = []

    @property
    @abstractmethod
    def backend_type(self) -> BackendType:
        """Return the backend type."""
        pass

    @abstractmethod
    def add_series(
        self,
        data: pl.DataFrame,
        series_type: str,
        time_col: str,
        value_col: Optional[str] = None,
        open_col: Optional[str] = None,
        high_col: Optional[str] = None,
        low_col: Optional[str] = None,
        close_col: Optional[str] = None,
        **options,
    ) -> "Backend":
        """
        Add a data series to the chart.

        Args:
            data: Polars DataFrame with the data
            series_type: Type of series (candlestick, line, area, histogram)
            time_col: Name of time column
            value_col: Name of value column (for line/area/histogram)
            open_col: Name of open column (for candlestick)
            high_col: Name of high column (for candlestick)
            low_col: Name of low column (for candlestick)
            close_col: Name of close column (for candlestick)
            **options: Additional series options

        Returns:
            Self for chaining
        """
        pass

    def add_marker(
        self,
        time: Any,
        position: str = "aboveBar",
        shape: str = "circle",
        color: Optional[str] = None,
        text: str = "",
        size: int = 1,
    ) -> "Backend":
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
        self._markers.append({
            "time": time,
            "position": position,
            "shape": shape,
            "color": color or self.config.theme.colors.highlight,
            "text": text,
            "size": size,
        })
        return self

    def add_horizontal_line(
        self,
        price: float,
        color: Optional[str] = None,
        line_width: int = 1,
        line_style: int = 0,
        label: str = "",
        label_visible: bool = True,
    ) -> "Backend":
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
        self._price_lines.append({
            "price": price,
            "color": color or self.config.theme.colors.highlight,
            "lineWidth": line_width,
            "lineStyle": line_style,
            "title": label,
            "axisLabelVisible": label_visible,
        })
        return self

    def add_drawing(self, drawing: Any) -> "Backend":
        """
        Add a drawing annotation.

        Args:
            drawing: Drawing object (TrendLine, Rectangle, etc.)

        Returns:
            Self for chaining
        """
        self._drawings.append(drawing)
        return self

    @abstractmethod
    def to_html(self) -> str:
        """
        Generate HTML for rendering.

        Returns:
            Complete HTML string for the chart
        """
        pass

    @abstractmethod
    def to_json(self) -> str:
        """
        Generate JSON configuration.

        Returns:
            JSON string with chart configuration
        """
        pass

    def show(self) -> None:
        """Display the chart in Jupyter or browser."""
        try:
            from IPython.display import display, HTML
            display(HTML(self.to_html()))
        except ImportError:
            import tempfile
            import webbrowser

            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head><title>{self.config.title or 'Chart'}</title></head>
            <body style="margin: 0; padding: 20px; background: {self.config.theme.colors.background};">
                {self.to_html()}
            </body>
            </html>
            """

            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".html", delete=False
            ) as f:
                f.write(html_content)
                webbrowser.open(f"file://{f.name}")

    def streamlit(self, height: Optional[int] = None) -> None:
        """
        Display the chart in Streamlit.

        Args:
            height: Optional height override
        """
        import streamlit.components.v1 as components

        render_height = height or (self.config.height + 80)
        components.html(self.to_html(), height=render_height, scrolling=False)

    @staticmethod
    def select_backend(
        data: Union[pl.DataFrame, List[pl.DataFrame], Dict[str, Any], None],
        backend_hint: str = "auto",
    ) -> BackendType:
        """
        Select the optimal backend based on data characteristics.

        Args:
            data: Input data (DataFrame, list of DataFrames, or dict)
            backend_hint: Explicit backend choice ("auto", "lightweight", "webgl", "canvas", "multipanel")

        Returns:
            The selected backend type
        """
        # Explicit backend selection
        if backend_hint != "auto":
            mapping = {
                "lightweight": BackendType.LIGHTWEIGHT,
                "webgl": BackendType.WEBGL,
                "canvas": BackendType.CANVAS,
                "multipanel": BackendType.MULTIPANEL,
            }
            return mapping.get(backend_hint, BackendType.LIGHTWEIGHT)

        # Auto-detection
        if data is None:
            return BackendType.LIGHTWEIGHT

        # Multiple DataFrames → MultiPanel
        if isinstance(data, list) and all(isinstance(d, pl.DataFrame) for d in data):
            return BackendType.MULTIPANEL

        # Dict with "paths" key → Canvas (forecast)
        if isinstance(data, dict) and "paths" in data:
            return BackendType.CANVAS

        # Single DataFrame
        if isinstance(data, pl.DataFrame):
            n_rows = len(data)
            # Large datasets → WebGL
            if n_rows > 100_000:
                return BackendType.WEBGL
            # Default → Lightweight Charts
            return BackendType.LIGHTWEIGHT

        return BackendType.LIGHTWEIGHT
