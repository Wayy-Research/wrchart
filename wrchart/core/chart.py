"""
Main Chart class for wrchart.

Provides a Polars-native API for creating interactive financial charts.
"""

from typing import Any, Dict, List, Optional, Union
import json
import uuid

import polars as pl

from wrchart.core.series import (
    BaseSeries,
    CandlestickSeries,
    LineSeries,
    AreaSeries,
    HistogramSeries,
)
from wrchart.core.themes import Theme, WayyTheme


class Chart:
    """
    Interactive financial chart.

    Example:
        >>> import wrchart as wrc
        >>> import polars as pl
        >>>
        >>> # Create OHLCV data
        >>> df = pl.DataFrame({
        ...     "time": [...],
        ...     "open": [...],
        ...     "high": [...],
        ...     "low": [...],
        ...     "close": [...],
        ...     "volume": [...],
        ... })
        >>>
        >>> # Create chart
        >>> chart = wrc.Chart(width=800, height=600)
        >>> chart.add_candlestick(df)
        >>> chart.add_volume(df)
        >>> chart.show()
    """

    def __init__(
        self,
        width: int = 800,
        height: int = 600,
        theme: Optional[Theme] = None,
        title: Optional[str] = None,
    ):
        """
        Initialize a new chart.

        Args:
            width: Chart width in pixels
            height: Chart height in pixels
            theme: Theme to use (defaults to WayyTheme)
            title: Optional chart title
        """
        self.width = width
        self.height = height
        self.theme = theme or WayyTheme
        self.title = title
        self._id = str(uuid.uuid4())[:8]

        self._series: List[BaseSeries] = []
        self._panes: List[Dict[str, Any]] = []
        self._markers: List[Dict[str, Any]] = []

    def add_series(self, series: BaseSeries) -> "Chart":
        """
        Add a series to the chart.

        Args:
            series: Any series type (Candlestick, Line, Area, etc.)

        Returns:
            Self for chaining
        """
        series._id = f"series_{len(self._series)}"
        self._series.append(series)
        return self

    def add_candlestick(
        self,
        data: pl.DataFrame,
        time_col: str = "time",
        open_col: str = "open",
        high_col: str = "high",
        low_col: str = "low",
        close_col: str = "close",
        **options,
    ) -> "Chart":
        """
        Add a candlestick series from OHLC data.

        Args:
            data: Polars DataFrame with OHLC columns
            time_col: Name of time column
            open_col: Name of open price column
            high_col: Name of high price column
            low_col: Name of low price column
            close_col: Name of close price column
            **options: Additional series options

        Returns:
            Self for chaining
        """
        from wrchart.core.series import CandlestickOptions

        series = CandlestickSeries(
            data=data,
            time_col=time_col,
            open_col=open_col,
            high_col=high_col,
            low_col=low_col,
            close_col=close_col,
            options=CandlestickOptions(**options) if options else None,
        )
        return self.add_series(series)

    def add_line(
        self,
        data: pl.DataFrame,
        time_col: str = "time",
        value_col: str = "value",
        **options,
    ) -> "Chart":
        """
        Add a line series.

        Args:
            data: Polars DataFrame with time and value columns
            time_col: Name of time column
            value_col: Name of value column
            **options: Additional series options

        Returns:
            Self for chaining
        """
        from wrchart.core.series import LineOptions

        series = LineSeries(
            data=data,
            time_col=time_col,
            value_col=value_col,
            options=LineOptions(**options) if options else None,
        )
        return self.add_series(series)

    def add_area(
        self,
        data: pl.DataFrame,
        time_col: str = "time",
        value_col: str = "value",
        **options,
    ) -> "Chart":
        """
        Add an area series.

        Args:
            data: Polars DataFrame with time and value columns
            time_col: Name of time column
            value_col: Name of value column
            **options: Additional series options

        Returns:
            Self for chaining
        """
        from wrchart.core.series import AreaOptions

        series = AreaSeries(
            data=data,
            time_col=time_col,
            value_col=value_col,
            options=AreaOptions(**options) if options else None,
        )
        return self.add_series(series)

    def add_histogram(
        self,
        data: pl.DataFrame,
        time_col: str = "time",
        value_col: str = "value",
        color_col: Optional[str] = None,
        **options,
    ) -> "Chart":
        """
        Add a histogram series.

        Args:
            data: Polars DataFrame with time and value columns
            time_col: Name of time column
            value_col: Name of value column
            color_col: Optional column for per-bar colors
            **options: Additional series options

        Returns:
            Self for chaining
        """
        from wrchart.core.series import HistogramOptions

        series = HistogramSeries(
            data=data,
            time_col=time_col,
            value_col=value_col,
            color_col=color_col,
            options=HistogramOptions(**options) if options else None,
        )
        return self.add_series(series)

    def add_volume(
        self,
        data: pl.DataFrame,
        time_col: str = "time",
        volume_col: str = "volume",
        open_col: str = "open",
        close_col: str = "close",
        up_color: Optional[str] = None,
        down_color: Optional[str] = None,
    ) -> "Chart":
        """
        Add a volume histogram with up/down coloring.

        Args:
            data: Polars DataFrame with OHLCV data
            time_col: Name of time column
            volume_col: Name of volume column
            open_col: Name of open price column (for color determination)
            close_col: Name of close price column (for color determination)
            up_color: Color for up bars (defaults to theme)
            down_color: Color for down bars (defaults to theme)

        Returns:
            Self for chaining
        """
        up_c = up_color or self.theme.colors.volume_up
        down_c = down_color or self.theme.colors.volume_down

        # Add color column based on open/close
        volume_data = data.select(
            [
                pl.col(time_col).alias("time"),
                pl.col(volume_col).alias("value"),
                pl.when(pl.col(close_col) >= pl.col(open_col))
                .then(pl.lit(up_c))
                .otherwise(pl.lit(down_c))
                .alias("color"),
            ]
        )

        from wrchart.core.series import HistogramOptions

        series = HistogramSeries(
            data=volume_data,
            time_col="time",
            value_col="value",
            color_col="color",
            options=HistogramOptions(
                price_scale_id="volume",
                price_line_visible=False,
                last_value_visible=False,
            ),
        )
        return self.add_series(series)

    def add_marker(
        self,
        time: Any,
        position: str = "aboveBar",  # aboveBar, belowBar, inBar
        shape: str = "circle",  # circle, square, arrowUp, arrowDown
        color: Optional[str] = None,
        text: str = "",
        size: int = 1,
    ) -> "Chart":
        """
        Add a marker to the chart.

        Args:
            time: Time value for the marker
            position: Where to place the marker
            shape: Shape of the marker
            color: Marker color (defaults to theme accent)
            text: Text to display with marker
            size: Size multiplier

        Returns:
            Self for chaining
        """
        self._markers.append(
            {
                "time": time,
                "position": position,
                "shape": shape,
                "color": color or self.theme.colors.highlight,
                "text": text,
                "size": size,
            }
        )
        return self

    def to_json(self) -> str:
        """
        Convert chart configuration to JSON for the frontend.

        Returns:
            JSON string with chart configuration
        """
        config = {
            "id": self._id,
            "width": self.width,
            "height": self.height,
            "title": self.title,
            "options": self.theme.to_lightweight_charts_options(),
            "series": [
                {
                    "id": s._id,
                    "type": s.series_type(),
                    "data": s.to_js_data(),
                    "options": s.to_js_options(self.theme),
                }
                for s in self._series
            ],
            "markers": self._markers,
        }
        return json.dumps(config)

    def _repr_html_(self) -> str:
        """
        Jupyter notebook HTML representation.

        Returns:
            HTML string for rendering in Jupyter
        """
        return self._generate_html()

    def _generate_html(self) -> str:
        """Generate the HTML/JS for rendering the chart."""
        config_json = self.to_json()

        # Load Google Fonts for Wayy branding
        fonts_css = """
        @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');
        """

        html = f"""
        <style>
            {fonts_css}
            #wrchart-container-{self._id} {{
                font-family: 'Space Grotesk', -apple-system, BlinkMacSystemFont, sans-serif;
            }}
            #wrchart-title-{self._id} {{
                font-size: 14px;
                font-weight: 600;
                color: {self.theme.colors.text_primary};
                margin-bottom: 8px;
                letter-spacing: -0.02em;
            }}
        </style>
        <div id="wrchart-container-{self._id}">
            {"<div id='wrchart-title-" + self._id + "'>" + self.title + "</div>" if self.title else ""}
            <div id="wrchart-{self._id}"></div>
        </div>
        <script src="https://unpkg.com/lightweight-charts@4.1.0/dist/lightweight-charts.standalone.production.js"></script>
        <script>
        (function() {{
            const config = {config_json};

            const container = document.getElementById('wrchart-' + config.id);
            const chart = LightweightCharts.createChart(container, {{
                width: config.width,
                height: config.height,
                ...config.options
            }});

            // Add each series
            const seriesMap = {{}};
            config.series.forEach(seriesConfig => {{
                let series;
                switch(seriesConfig.type) {{
                    case 'Candlestick':
                        series = chart.addCandlestickSeries(seriesConfig.options);
                        break;
                    case 'Line':
                        series = chart.addLineSeries(seriesConfig.options);
                        break;
                    case 'Area':
                        series = chart.addAreaSeries(seriesConfig.options);
                        break;
                    case 'Histogram':
                        series = chart.addHistogramSeries(seriesConfig.options);
                        break;
                    default:
                        console.warn('Unknown series type:', seriesConfig.type);
                        return;
                }}
                series.setData(seriesConfig.data);
                seriesMap[seriesConfig.id] = series;
            }});

            // Add markers to first candlestick series if any
            if (config.markers.length > 0) {{
                const candlestickSeries = config.series.find(s => s.type === 'Candlestick');
                if (candlestickSeries) {{
                    seriesMap[candlestickSeries.id].setMarkers(config.markers);
                }}
            }}

            // Configure volume scale if present
            const volumeSeries = config.series.find(s => s.options.priceScaleId === 'volume');
            if (volumeSeries) {{
                chart.priceScale('volume').applyOptions({{
                    scaleMargins: {{
                        top: 0.8,
                        bottom: 0
                    }}
                }});
            }}

            // Fit content
            chart.timeScale().fitContent();
        }})();
        </script>
        """
        return html

    def show(self) -> None:
        """
        Display the chart.

        In Jupyter, this renders the chart inline.
        Outside Jupyter, this opens a browser window.
        """
        try:
            from IPython.display import display, HTML

            display(HTML(self._generate_html()))
        except ImportError:
            # Not in Jupyter, save to temp file and open in browser
            import tempfile
            import webbrowser
            import os

            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>{self.title or 'wrchart'}</title>
                <style>
                    body {{
                        margin: 0;
                        padding: 20px;
                        background: {self.theme.colors.background};
                        font-family: 'Space Grotesk', sans-serif;
                    }}
                </style>
            </head>
            <body>
                {self._generate_html()}
            </body>
            </html>
            """

            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".html", delete=False
            ) as f:
                f.write(html_content)
                webbrowser.open(f"file://{f.name}")
