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
        value_format: str = "number",
        y_label: Optional[str] = None,
    ):
        """
        Initialize a new chart.

        Args:
            width: Chart width in pixels
            height: Chart height in pixels
            theme: Theme to use (defaults to WayyTheme)
            title: Optional chart title
            value_format: Format for values - "number", "percent", "currency"
            y_label: Optional y-axis label
        """
        self.width = width
        self.height = height
        self.theme = theme or WayyTheme
        self.title = title
        self.value_format = value_format
        self.y_label = y_label
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

    def add_horizontal_line(
        self,
        price: float,
        color: Optional[str] = None,
        line_width: int = 1,
        line_style: int = 0,  # 0=solid, 1=dotted, 2=dashed, 3=large dashed, 4=sparse dotted
        label: str = "",
        label_visible: bool = True,
    ) -> "Chart":
        """
        Add a horizontal price line to the chart.

        Args:
            price: Price level for the line
            color: Line color (defaults to theme highlight)
            line_width: Width of the line in pixels
            line_style: Style of the line (0=solid, 1=dotted, 2=dashed)
            label: Label text for the price line
            label_visible: Whether to show the label

        Returns:
            Self for chaining
        """
        if not hasattr(self, "_price_lines"):
            self._price_lines: List[Dict[str, Any]] = []

        self._price_lines.append(
            {
                "price": price,
                "color": color or self.theme.colors.highlight,
                "lineWidth": line_width,
                "lineStyle": line_style,
                "title": label,
                "axisLabelVisible": label_visible,
            }
        )
        return self

    def to_json(self) -> str:
        """
        Convert chart configuration to JSON for the frontend.

        Returns:
            JSON string with chart configuration
        """
        # Sort series so candlestick comes last (renders on top)
        # but is still identified as mainSeries for legend/price lines
        sorted_series = sorted(
            self._series,
            key=lambda s: 1 if s.series_type() == "Candlestick" else 0
        )
        config = {
            "id": self._id,
            "width": self.width,
            "height": self.height,
            "title": self.title,
            "valueFormat": self.value_format,
            "yLabel": self.y_label,
            "options": self.theme.to_lightweight_charts_options(),
            "series": [
                {
                    "id": s._id,
                    "type": s.series_type(),
                    "data": s.to_js_data(),
                    "options": s.to_js_options(self.theme),
                }
                for s in sorted_series
            ],
            "markers": self._markers,
            "priceLines": getattr(self, "_price_lines", []),
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
                width: 100%;
                position: relative;
            }}
            #wrchart-title-{self._id} {{
                font-size: 14px;
                font-weight: 600;
                color: {self.theme.colors.text_primary};
                margin-bottom: 8px;
                letter-spacing: -0.02em;
            }}
            #wrchart-{self._id} {{
                width: 100%;
            }}
            #wrchart-legend-{self._id} {{
                position: absolute;
                top: {32 if self.title else 8}px;
                left: 12px;
                z-index: 10;
                font-family: 'JetBrains Mono', monospace;
                font-size: 12px;
                color: {self.theme.colors.text_primary};
                background: {self.theme.colors.background}ee;
                padding: 6px 10px;
                border-radius: 4px;
                pointer-events: none;
                min-width: 200px;
            }}
            #wrchart-legend-{self._id} .legend-date {{
                font-weight: 600;
                margin-bottom: 4px;
                color: {self.theme.colors.text_secondary};
            }}
            #wrchart-legend-{self._id} .legend-row {{
                display: flex;
                justify-content: space-between;
                gap: 12px;
            }}
            #wrchart-legend-{self._id} .legend-label {{
                color: {self.theme.colors.text_secondary};
            }}
            #wrchart-legend-{self._id} .legend-value {{
                font-weight: 500;
            }}
            #wrchart-legend-{self._id} .legend-value.up {{
                color: {self.theme.colors.candle_up};
            }}
            #wrchart-legend-{self._id} .legend-value.down {{
                color: {self.theme.colors.candle_down};
            }}
        </style>
        <div id="wrchart-container-{self._id}">
            {"<div id='wrchart-title-" + self._id + "'>" + self.title + "</div>" if self.title else ""}
            <div id="wrchart-legend-{self._id}"></div>
            <div id="wrchart-{self._id}"></div>
        </div>
        <script src="https://unpkg.com/lightweight-charts@4.2.1/dist/lightweight-charts.standalone.production.js"></script>
        <script>
        (function() {{
            const config = {config_json};

            const container = document.getElementById('wrchart-' + config.id);
            const legendEl = document.getElementById('wrchart-legend-' + config.id);

            // Auto-size to container width
            const containerWidth = container.parentElement.offsetWidth || config.width;

            const chart = LightweightCharts.createChart(container, {{
                width: containerWidth,
                height: config.height,
                ...config.options,
                timeScale: {{
                    ...config.options.timeScale,
                    timeVisible: true,
                    secondsVisible: false,
                    tickMarkFormatter: (time, tickMarkType, locale) => {{
                        if (typeof time === 'string') return time;
                        const date = new Date(time * 1000);
                        // For intraday charts, show time; for daily+ show date
                        // tickMarkType: 0=Year, 1=Month, 2=DayOfMonth, 3=Time, 4=TimeWithSeconds
                        if (tickMarkType >= 3) {{
                            return date.toLocaleTimeString('en-US', {{ hour: '2-digit', minute: '2-digit', hour12: false }});
                        }} else if (tickMarkType === 2) {{
                            return date.toLocaleDateString('en-US', {{ month: 'short', day: 'numeric' }});
                        }} else if (tickMarkType === 1) {{
                            return date.toLocaleDateString('en-US', {{ month: 'short' }});
                        }} else {{
                            return date.getFullYear().toString();
                        }}
                    }},
                }},
                localization: {{
                    timeFormatter: (time) => {{
                        if (typeof time === 'string') {{
                            return time;
                        }}
                        const date = new Date(time * 1000);
                        return date.toLocaleDateString('en-US', {{
                            year: 'numeric',
                            month: 'short',
                            day: 'numeric',
                            hour: '2-digit',
                            minute: '2-digit'
                        }});
                    }},
                    priceFormatter: (price) => {{
                        if (price >= 1000) {{
                            return price.toLocaleString('en-US', {{ minimumFractionDigits: 2, maximumFractionDigits: 2 }});
                        }}
                        return price.toFixed(price < 1 ? 6 : 2);
                    }},
                }},
            }});

            // Add each series (candlestick comes last to render on top)
            const seriesMap = {{}};
            let mainSeries = null;
            let fallbackMainSeries = null;
            config.series.forEach(seriesConfig => {{
                let series;
                switch(seriesConfig.type) {{
                    case 'Candlestick':
                        series = chart.addCandlestickSeries(seriesConfig.options);
                        // Candlestick always becomes mainSeries (for legend, price lines)
                        mainSeries = {{ series, type: 'candlestick', data: seriesConfig.data }};
                        break;
                    case 'Line':
                        series = chart.addLineSeries(seriesConfig.options);
                        if (!fallbackMainSeries) fallbackMainSeries = {{ series, type: 'line', data: seriesConfig.data }};
                        break;
                    case 'Area':
                        series = chart.addAreaSeries(seriesConfig.options);
                        if (!fallbackMainSeries) fallbackMainSeries = {{ series, type: 'area', data: seriesConfig.data }};
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
            // Use candlestick as mainSeries, or fallback to first line/area series
            if (!mainSeries) mainSeries = fallbackMainSeries;

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

            // Add horizontal price lines to main series
            if (config.priceLines && config.priceLines.length > 0 && mainSeries) {{
                config.priceLines.forEach(lineConfig => {{
                    mainSeries.series.createPriceLine(lineConfig);
                }});
            }}

            // Format time for legend
            function formatTime(time) {{
                if (typeof time === 'string') {{
                    return time;
                }}
                const date = new Date(time * 1000);
                return date.toLocaleDateString('en-US', {{
                    weekday: 'short',
                    year: 'numeric',
                    month: 'short',
                    day: 'numeric',
                    hour: '2-digit',
                    minute: '2-digit'
                }});
            }}

            // Format value for legend based on valueFormat config
            function formatValue(value) {{
                if (value === undefined || value === null) return '-';
                const fmt = config.valueFormat || 'number';

                if (fmt === 'currency') {{
                    if (Math.abs(value) >= 1000) {{
                        return '$' + value.toLocaleString('en-US', {{ minimumFractionDigits: 2, maximumFractionDigits: 2 }});
                    }}
                    return '$' + value.toFixed(2);
                }} else if (fmt === 'percent') {{
                    return (value * 100).toFixed(2) + '%';
                }} else {{
                    // number format - no prefix
                    if (Math.abs(value) >= 1000) {{
                        return value.toLocaleString('en-US', {{ minimumFractionDigits: 2, maximumFractionDigits: 2 }});
                    }}
                    return value.toFixed(Math.abs(value) < 1 ? 4 : 2);
                }}
            }}

            // Update legend on crosshair move
            chart.subscribeCrosshairMove((param) => {{
                if (!param || !param.time || !mainSeries) {{
                    legendEl.innerHTML = '';
                    return;
                }}

                const data = param.seriesData.get(mainSeries.series);
                if (!data) {{
                    legendEl.innerHTML = '';
                    return;
                }}

                const timeStr = formatTime(param.time);
                let legendHtml = '<div class="legend-date">' + timeStr + '</div>';

                if (mainSeries.type === 'candlestick' && data.open !== undefined) {{
                    const change = data.close - data.open;
                    const changePct = ((change / data.open) * 100).toFixed(2);
                    const colorClass = change >= 0 ? 'up' : 'down';
                    legendHtml += `
                        <div class="legend-row"><span class="legend-label">O</span><span class="legend-value">${{formatValue(data.open)}}</span></div>
                        <div class="legend-row"><span class="legend-label">H</span><span class="legend-value">${{formatValue(data.high)}}</span></div>
                        <div class="legend-row"><span class="legend-label">L</span><span class="legend-value">${{formatValue(data.low)}}</span></div>
                        <div class="legend-row"><span class="legend-label">C</span><span class="legend-value ${{colorClass}}">${{formatValue(data.close)}}</span></div>
                        <div class="legend-row"><span class="legend-label">Chg</span><span class="legend-value ${{colorClass}}">${{change >= 0 ? '+' : ''}}${{changePct}}%</span></div>
                    `;
                }} else if (data.value !== undefined) {{
                    legendHtml += `
                        <div class="legend-row"><span class="legend-label">Value</span><span class="legend-value">${{formatValue(data.value)}}</span></div>
                    `;
                }}

                legendEl.innerHTML = legendHtml;
            }});

            // Double-click to reset view
            container.addEventListener('dblclick', () => {{
                chart.timeScale().fitContent();
            }});

            // Resize observer for responsive sizing
            const resizeObserver = new ResizeObserver(entries => {{
                for (let entry of entries) {{
                    const width = entry.contentRect.width;
                    if (width > 0) {{
                        chart.applyOptions({{ width: width }});
                    }}
                }}
            }});
            resizeObserver.observe(container.parentElement);

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

    def streamlit(
        self,
        height: Optional[int] = None,
        live_source: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Display the chart in Streamlit.

        This method generates HTML optimized for Streamlit's iframe environment
        with explicit dimensions and proper script loading.

        Args:
            height: Optional height override (defaults to chart height + 50)
            live_source: Optional WebSocket configuration for live updates:
                {
                    "type": "coinbase",  # or "custom"
                    "symbol": "BTC-USD",  # for coinbase
                    "ws_url": "wss://...",  # for custom
                    "channel": "...",  # for custom LiveServer
                }

        Examples:
            # Static chart
            chart.streamlit()

            # Live chart with Coinbase data
            chart.streamlit(live_source={"type": "coinbase", "symbol": "BTC-USD"})

            # Live chart with custom WebSocket
            chart.streamlit(live_source={"type": "custom", "ws_url": "wss://...", "channel": "btc"})
        """
        import streamlit.components.v1 as components

        render_height = height or (self.height + 80)

        if live_source:
            html = self._generate_live_streamlit_html(live_source)
        else:
            html = self._generate_streamlit_html()

        components.html(html, height=render_height, scrolling=False)

    def _generate_streamlit_html(self) -> str:
        """Generate HTML optimized for Streamlit iframe rendering."""
        config_json = self.to_json()

        # Full HTML document for iframe with explicit dimensions
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Space Grotesk', -apple-system, BlinkMacSystemFont, sans-serif;
            background: {self.theme.colors.background};
            padding: 8px;
        }}
        #wrchart-container {{
            width: 100%;
            min-width: {self.width}px;
        }}
        #wrchart-title {{
            font-size: 14px;
            font-weight: 600;
            color: {self.theme.colors.text_primary};
            margin-bottom: 8px;
            letter-spacing: -0.02em;
        }}
        #wrchart {{
            width: {self.width}px;
            height: {self.height}px;
            min-height: {self.height}px;
        }}
        #wrchart-legend {{
            position: absolute;
            top: {40 if self.title else 16}px;
            left: 20px;
            z-index: 10;
            font-family: 'JetBrains Mono', monospace;
            font-size: 12px;
            color: {self.theme.colors.text_primary};
            background: {self.theme.colors.background}ee;
            padding: 6px 10px;
            border-radius: 4px;
            pointer-events: none;
            min-width: 200px;
        }}
        #wrchart-legend .legend-date {{
            font-weight: 600;
            margin-bottom: 4px;
            color: {self.theme.colors.text_secondary};
        }}
        #wrchart-legend .legend-row {{
            display: flex;
            justify-content: space-between;
            gap: 12px;
        }}
        #wrchart-legend .legend-label {{
            color: {self.theme.colors.text_secondary};
        }}
        #wrchart-legend .legend-value {{
            font-weight: 500;
        }}
        #wrchart-legend .legend-value.up {{
            color: {self.theme.colors.candle_up};
        }}
        #wrchart-legend .legend-value.down {{
            color: {self.theme.colors.candle_down};
        }}
    </style>
    <script src="https://unpkg.com/lightweight-charts@4.2.1/dist/lightweight-charts.standalone.production.js"></script>
</head>
<body>
    <div id="wrchart-container" style="position: relative;">
        {"<div id='wrchart-title'>" + self.title + "</div>" if self.title else ""}
        <div id="wrchart-legend"></div>
        <div id="wrchart"></div>
    </div>
    <script>
    // Wait for lightweight-charts to load
    let initAttempts = 0;
    function initChart() {{
        initAttempts++;
        if (typeof LightweightCharts === 'undefined') {{
            if (initAttempts < 100) {{
                setTimeout(initChart, 50);
            }} else {{
                console.error('Failed to load LightweightCharts after 100 attempts');
            }}
            return;
        }}

        try {{
            const config = {config_json};
            const container = document.getElementById('wrchart');
            const legendEl = document.getElementById('wrchart-legend');

            if (!container) {{
                console.error('Chart container not found');
                return;
            }}

            // Use explicit width for Streamlit iframe (don't rely on container.offsetWidth)
            const chartWidth = {self.width};

            const chart = LightweightCharts.createChart(container, {{
                width: chartWidth,
                height: {self.height},
                ...config.options,
            timeScale: {{
                ...config.options.timeScale,
                timeVisible: true,
                secondsVisible: false,
                tickMarkFormatter: (time, tickMarkType, locale) => {{
                    if (typeof time === 'string') return time;
                    const date = new Date(time * 1000);
                    // For intraday charts, show time; for daily+ show date
                    // tickMarkType: 0=Year, 1=Month, 2=DayOfMonth, 3=Time, 4=TimeWithSeconds
                    if (tickMarkType >= 3) {{
                        return date.toLocaleTimeString('en-US', {{ hour: '2-digit', minute: '2-digit', hour12: false }});
                    }} else if (tickMarkType === 2) {{
                        return date.toLocaleDateString('en-US', {{ month: 'short', day: 'numeric' }});
                    }} else if (tickMarkType === 1) {{
                        return date.toLocaleDateString('en-US', {{ month: 'short' }});
                    }} else {{
                        return date.getFullYear().toString();
                    }}
                }},
            }},
            localization: {{
                timeFormatter: (time) => {{
                    if (typeof time === 'string') return time;
                    const date = new Date(time * 1000);
                    return date.toLocaleDateString('en-US', {{
                        year: 'numeric', month: 'short', day: 'numeric',
                        hour: '2-digit', minute: '2-digit'
                    }});
                }},
                priceFormatter: (price) => {{
                    if (price >= 1000) return price.toLocaleString('en-US', {{ minimumFractionDigits: 2, maximumFractionDigits: 2 }});
                    return price.toFixed(price < 1 ? 6 : 2);
                }},
            }},
        }});

        // Add each series (candlestick comes last to render on top)
        const seriesMap = {{}};
        let mainSeries = null;
        let fallbackMainSeries = null;
        console.log('Adding series, count:', config.series.length);
        config.series.forEach(seriesConfig => {{
            console.log('Series type:', seriesConfig.type, 'Data points:', seriesConfig.data ? seriesConfig.data.length : 0);
            let series;
            switch(seriesConfig.type) {{
                case 'Candlestick':
                    series = chart.addCandlestickSeries(seriesConfig.options);
                    // Candlestick always becomes mainSeries
                    mainSeries = {{ series, type: 'candlestick', data: seriesConfig.data }};
                    console.log('Created candlestick series, setting data...');
                    break;
                case 'Line':
                    series = chart.addLineSeries(seriesConfig.options);
                    if (!fallbackMainSeries) fallbackMainSeries = {{ series, type: 'line', data: seriesConfig.data }};
                    break;
                case 'Area':
                    series = chart.addAreaSeries(seriesConfig.options);
                    if (!fallbackMainSeries) fallbackMainSeries = {{ series, type: 'area', data: seriesConfig.data }};
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
            console.log('Data set for series:', seriesConfig.id);
        }});
        // Use candlestick as mainSeries, or fallback to first line/area series
        if (!mainSeries) mainSeries = fallbackMainSeries;

        // Add markers
        if (config.markers.length > 0) {{
            const candlestickSeries = config.series.find(s => s.type === 'Candlestick');
            if (candlestickSeries) {{
                seriesMap[candlestickSeries.id].setMarkers(config.markers);
            }}
        }}

        // Configure volume scale
        const volumeSeries = config.series.find(s => s.options.priceScaleId === 'volume');
        if (volumeSeries) {{
            chart.priceScale('volume').applyOptions({{
                scaleMargins: {{ top: 0.8, bottom: 0 }}
            }});
        }}

        // Add price lines
        if (config.priceLines && config.priceLines.length > 0 && mainSeries) {{
            config.priceLines.forEach(lineConfig => {{
                mainSeries.series.createPriceLine(lineConfig);
            }});
        }}

        // Format helpers
        function formatTime(time) {{
            if (typeof time === 'string') return time;
            const date = new Date(time * 1000);
            return date.toLocaleDateString('en-US', {{
                weekday: 'short', year: 'numeric', month: 'short', day: 'numeric',
                hour: '2-digit', minute: '2-digit'
            }});
        }}

        // Format value based on valueFormat config
        function formatValue(value) {{
            if (value === undefined || value === null) return '-';
            const fmt = config.valueFormat || 'number';

            if (fmt === 'currency') {{
                if (Math.abs(value) >= 1000) {{
                    return '$' + value.toLocaleString('en-US', {{ minimumFractionDigits: 2, maximumFractionDigits: 2 }});
                }}
                return '$' + value.toFixed(2);
            }} else if (fmt === 'percent') {{
                return (value * 100).toFixed(2) + '%';
            }} else {{
                if (Math.abs(value) >= 1000) {{
                    return value.toLocaleString('en-US', {{ minimumFractionDigits: 2, maximumFractionDigits: 2 }});
                }}
                return value.toFixed(Math.abs(value) < 1 ? 4 : 2);
            }}
        }}

        // Legend updates
        chart.subscribeCrosshairMove((param) => {{
            if (!param || !param.time || !mainSeries) {{
                legendEl.innerHTML = '';
                return;
            }}

            const data = param.seriesData.get(mainSeries.series);
            if (!data) {{
                legendEl.innerHTML = '';
                return;
            }}

            const timeStr = formatTime(param.time);
            let legendHtml = '<div class="legend-date">' + timeStr + '</div>';

            if (mainSeries.type === 'candlestick' && data.open !== undefined) {{
                const change = data.close - data.open;
                const changePct = ((change / data.open) * 100).toFixed(2);
                const colorClass = change >= 0 ? 'up' : 'down';
                legendHtml += `
                    <div class="legend-row"><span class="legend-label">O</span><span class="legend-value">${{formatValue(data.open)}}</span></div>
                    <div class="legend-row"><span class="legend-label">H</span><span class="legend-value">${{formatValue(data.high)}}</span></div>
                    <div class="legend-row"><span class="legend-label">L</span><span class="legend-value">${{formatValue(data.low)}}</span></div>
                    <div class="legend-row"><span class="legend-label">C</span><span class="legend-value ${{colorClass}}">${{formatValue(data.close)}}</span></div>
                    <div class="legend-row"><span class="legend-label">Chg</span><span class="legend-value ${{colorClass}}">${{change >= 0 ? '+' : ''}}${{changePct}}%</span></div>
                `;
            }} else if (data.value !== undefined) {{
                legendHtml += `<div class="legend-row"><span class="legend-label">Value</span><span class="legend-value">${{formatValue(data.value)}}</span></div>`;
            }}

            legendEl.innerHTML = legendHtml;
        }});

        // Fit content
        chart.timeScale().fitContent();

        // Responsive resize
        window.addEventListener('resize', () => {{
            const newWidth = container.offsetWidth;
            if (newWidth > 0) chart.applyOptions({{ width: newWidth }});
        }});

        }} catch (error) {{
            console.error('Chart initialization error:', error);
        }}
    }}

    // Start initialization
    initChart();
    </script>
</body>
</html>
        """
        return html

    def _generate_live_streamlit_html(self, live_source: Dict[str, Any]) -> str:
        """
        Generate HTML with live WebSocket updates for Streamlit.

        This enables real-time candlestick updates without page refresh.
        Supports Coinbase public WebSocket and custom LiveServer connections.
        """
        config_json = self.to_json()
        source_type = live_source.get("type", "coinbase")
        symbol = live_source.get("symbol", "BTC-USD")

        # WebSocket connection code based on source type
        if source_type == "coinbase":
            ws_connect_code = f"""
            // Coinbase WebSocket connection
            const wsUrl = 'wss://ws-feed.exchange.coinbase.com';
            const wsSymbol = '{symbol}';

            function connectWebSocket() {{
                console.log('[WS] Connecting to', wsUrl);
                const ws = new WebSocket(wsUrl);

                ws.onopen = () => {{
                    console.log('[WS] Connected! Subscribing to', wsSymbol);
                    statusDot.className = 'status-dot connected';
                    statusText.textContent = 'Live';

                    ws.send(JSON.stringify({{
                        type: 'subscribe',
                        product_ids: [wsSymbol],
                        channels: ['ticker']
                    }}));
                }};

                ws.onmessage = (event) => {{
                    const msg = JSON.parse(event.data);

                    if (msg.type === 'ticker' && msg.product_id === wsSymbol) {{
                        const price = parseFloat(msg.price);
                        const time = Math.floor(new Date(msg.time).getTime() / 1000);
                        const barTime = Math.floor(time / 60) * 60;  // Round to minute

                        console.log('[WS] Price update:', price, 'barTime:', barTime);
                        handlePriceUpdate(price, barTime);
                    }}
                }};

                ws.onclose = (e) => {{
                    console.log('[WS] Closed:', e.code, e.reason);
                    statusDot.className = 'status-dot';
                    statusText.textContent = 'Reconnecting...';
                    setTimeout(connectWebSocket, 3000);
                }};

                ws.onerror = (err) => {{
                    console.error('[WS] Error:', err);
                    statusDot.className = 'status-dot error';
                    statusText.textContent = 'Error';
                }};
            }}
            """
        else:
            # Custom LiveServer connection
            ws_url = live_source.get("ws_url", "ws://localhost:8765")
            channel = live_source.get("channel", "price")
            ws_connect_code = f"""
            // Custom WebSocket connection
            const wsUrl = '{ws_url}';
            const channel = '{channel}';

            function connectWebSocket() {{
                const ws = new WebSocket(wsUrl);

                ws.onopen = () => {{
                    statusDot.className = 'status-dot connected';
                    statusText.textContent = 'Live';

                    ws.send(JSON.stringify({{
                        action: 'subscribe',
                        channel: channel
                    }}));
                }};

                ws.onmessage = (event) => {{
                    const msg = JSON.parse(event.data);

                    if (msg.type === 'update' && msg.channel === channel) {{
                        const data = msg.data;
                        const price = data.close || data.price;
                        let time = data.time || data.timestamp;
                        if (typeof time === 'string') {{
                            time = Math.floor(new Date(time).getTime() / 1000);
                        }}
                        const barTime = Math.floor(time / 60) * 60;

                        handlePriceUpdate(price, barTime);
                    }}
                }};

                ws.onclose = () => {{
                    statusDot.className = 'status-dot';
                    statusText.textContent = 'Reconnecting...';
                    setTimeout(connectWebSocket, 3000);
                }};

                ws.onerror = () => {{
                    statusDot.className = 'status-dot error';
                    statusText.textContent = 'Error';
                }};
            }}
            """

        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Space Grotesk', -apple-system, BlinkMacSystemFont, sans-serif;
            background: {self.theme.colors.background};
            padding: 8px;
        }}
        #wrchart-container {{
            width: 100%;
            position: relative;
        }}
        #header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 8px 0;
            border-bottom: 1px solid {self.theme.colors.border};
            margin-bottom: 8px;
        }}
        #price-display {{
            font-family: 'JetBrains Mono', monospace;
            font-size: 24px;
            font-weight: 600;
            color: {self.theme.colors.text_primary};
        }}
        #price-change {{
            font-size: 14px;
            margin-left: 8px;
        }}
        #price-change.up {{ color: {self.theme.colors.candle_up}; }}
        #price-change.down {{ color: {self.theme.colors.candle_down}; }}
        #status {{
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 12px;
            color: {self.theme.colors.text_secondary};
        }}
        .status-dot {{
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: {self.theme.colors.text_secondary};
        }}
        .status-dot.connected {{
            background: #22c55e;
            animation: pulse 2s infinite;
        }}
        .status-dot.error {{ background: #ef4444; }}
        @keyframes pulse {{
            0%, 100% {{ opacity: 1; }}
            50% {{ opacity: 0.5; }}
        }}
        #wrchart {{
            width: 100%;
            height: {self.height}px;
        }}
        #wrchart-legend {{
            position: absolute;
            top: 60px;
            left: 12px;
            z-index: 10;
            font-family: 'JetBrains Mono', monospace;
            font-size: 11px;
            color: {self.theme.colors.text_primary};
            background: {self.theme.colors.background}ee;
            padding: 6px 10px;
            border-radius: 4px;
            pointer-events: none;
            min-width: 180px;
        }}
        #wrchart-legend .legend-date {{
            font-weight: 600;
            margin-bottom: 4px;
            color: {self.theme.colors.text_secondary};
        }}
        #wrchart-legend .legend-row {{
            display: flex;
            justify-content: space-between;
            gap: 12px;
        }}
        #wrchart-legend .legend-label {{ color: {self.theme.colors.text_secondary}; }}
        #wrchart-legend .legend-value {{ font-weight: 500; }}
        #wrchart-legend .legend-value.up {{ color: {self.theme.colors.candle_up}; }}
        #wrchart-legend .legend-value.down {{ color: {self.theme.colors.candle_down}; }}
        .zoom-hint {{
            position: absolute;
            bottom: 8px;
            right: 12px;
            font-size: 10px;
            color: {self.theme.colors.text_secondary};
            opacity: 0.7;
        }}
    </style>
    <script src="https://unpkg.com/lightweight-charts@4.2.1/dist/lightweight-charts.standalone.production.js"></script>
</head>
<body>
    <div id="wrchart-container">
        <div id="header">
            <div>
                <span id="price-display">--</span>
                <span id="price-change"></span>
            </div>
            <div id="status">
                <div class="status-dot" id="status-dot"></div>
                <span id="status-text">Connecting...</span>
            </div>
        </div>
        <div id="wrchart-legend"></div>
        <div id="wrchart"></div>
        <div class="zoom-hint">Scroll to zoom • Drag to pan • Double-click to reset</div>
    </div>
    <script>
    let initAttempts = 0;
    function initChart() {{
        initAttempts++;
        if (typeof LightweightCharts === 'undefined') {{
            if (initAttempts < 100) setTimeout(initChart, 50);
            return;
        }}

        try {{
            const config = {config_json};
            const container = document.getElementById('wrchart');
            const legendEl = document.getElementById('wrchart-legend');
            const priceDisplay = document.getElementById('price-display');
            const priceChange = document.getElementById('price-change');
            const statusDot = document.getElementById('status-dot');
            const statusText = document.getElementById('status-text');

            // Create chart with zoom/pan enabled
            const chart = LightweightCharts.createChart(container, {{
                width: container.offsetWidth || {self.width},
                height: {self.height},
                ...config.options,
                handleScroll: {{ mouseWheel: true, pressedMouseMove: true }},
                handleScale: {{ axisPressedMouseMove: true, mouseWheel: true, pinch: true }},
                timeScale: {{
                    ...config.options.timeScale,
                    timeVisible: true,
                    secondsVisible: true,
                }},
                crosshair: {{
                    mode: LightweightCharts.CrosshairMode.Normal,
                }},
            }});

            // Add series (candlestick comes last to render on top)
            const seriesMap = {{}};
            let mainSeries = null;
            let fallbackMainSeries = null;
            config.series.forEach(seriesConfig => {{
                let series;
                switch(seriesConfig.type) {{
                    case 'Candlestick':
                        series = chart.addCandlestickSeries(seriesConfig.options);
                        // Candlestick always becomes mainSeries
                        mainSeries = {{ series, type: 'candlestick', data: seriesConfig.data }};
                        break;
                    case 'Line':
                        series = chart.addLineSeries(seriesConfig.options);
                        if (!fallbackMainSeries) fallbackMainSeries = {{ series, type: 'line', data: seriesConfig.data }};
                        break;
                    case 'Area':
                        series = chart.addAreaSeries(seriesConfig.options);
                        if (!fallbackMainSeries) fallbackMainSeries = {{ series, type: 'area', data: seriesConfig.data }};
                        break;
                    case 'Histogram':
                        series = chart.addHistogramSeries(seriesConfig.options);
                        break;
                }}
                if (series) {{
                    series.setData(seriesConfig.data);
                    seriesMap[seriesConfig.id] = series;
                }}
            }});
            // Use candlestick as mainSeries, or fallback to first line/area series
            if (!mainSeries) mainSeries = fallbackMainSeries;

            // Volume scale
            const volumeSeries = config.series.find(s => s.options.priceScaleId === 'volume');
            if (volumeSeries) {{
                chart.priceScale('volume').applyOptions({{ scaleMargins: {{ top: 0.8, bottom: 0 }} }});
            }}

            // Track current bar for live updates
            let currentBar = null;
            let lastPrice = mainSeries && mainSeries.data.length > 0
                ? mainSeries.data[mainSeries.data.length - 1].close
                : null;
            let firstPrice = mainSeries && mainSeries.data.length > 0
                ? mainSeries.data[0].close || mainSeries.data[0].open
                : null;

            // Update price display
            function updatePriceDisplay(price) {{
                priceDisplay.textContent = '$' + price.toLocaleString('en-US', {{
                    minimumFractionDigits: 2, maximumFractionDigits: 2
                }});

                if (firstPrice) {{
                    const change = price - firstPrice;
                    const changePct = ((change / firstPrice) * 100).toFixed(2);
                    const sign = change >= 0 ? '+' : '';
                    priceChange.className = change >= 0 ? 'up' : 'down';
                    priceChange.textContent = sign + changePct + '%';
                }}
            }}

            if (lastPrice) updatePriceDisplay(lastPrice);

            // Handle live price updates
            function handlePriceUpdate(price, barTime) {{
                console.log('[handlePriceUpdate] mainSeries:', mainSeries ? mainSeries.type : 'null');
                if (!mainSeries || mainSeries.type !== 'candlestick') {{
                    console.log('[handlePriceUpdate] Skipping - no candlestick series');
                    return;
                }}

                // Update or create current bar
                if (!currentBar || currentBar.time !== barTime) {{
                    // New bar
                    console.log('[handlePriceUpdate] New bar at', barTime);
                    currentBar = {{
                        time: barTime,
                        open: price,
                        high: price,
                        low: price,
                        close: price,
                    }};
                }} else {{
                    // Update existing bar
                    currentBar.high = Math.max(currentBar.high, price);
                    currentBar.low = Math.min(currentBar.low, price);
                    currentBar.close = price;
                }}

                mainSeries.series.update(currentBar);
                updatePriceDisplay(price);
                lastPrice = price;
            }}

            // Format helpers
            function formatTime(time) {{
                if (typeof time === 'string') return time;
                const date = new Date(time * 1000);
                return date.toLocaleDateString('en-US', {{
                    month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'
                }});
            }}

            // Format value based on valueFormat config
            function formatValue(value) {{
                if (value === undefined || value === null) return '-';
                const fmt = config.valueFormat || 'currency';

                if (fmt === 'currency') {{
                    if (Math.abs(value) >= 1000) {{
                        return '$' + value.toLocaleString('en-US', {{ minimumFractionDigits: 2, maximumFractionDigits: 2 }});
                    }}
                    return '$' + value.toFixed(2);
                }} else if (fmt === 'percent') {{
                    return (value * 100).toFixed(2) + '%';
                }} else {{
                    if (Math.abs(value) >= 1000) {{
                        return value.toLocaleString('en-US', {{ minimumFractionDigits: 2, maximumFractionDigits: 2 }});
                    }}
                    return value.toFixed(Math.abs(value) < 1 ? 4 : 2);
                }}
            }}

            // Legend on crosshair move
            chart.subscribeCrosshairMove((param) => {{
                if (!param || !param.time || !mainSeries) {{
                    legendEl.innerHTML = '';
                    return;
                }}

                const data = param.seriesData.get(mainSeries.series);
                if (!data) {{
                    legendEl.innerHTML = '';
                    return;
                }}

                let legendHtml = '<div class="legend-date">' + formatTime(param.time) + '</div>';

                if (mainSeries.type === 'candlestick' && data.open !== undefined) {{
                    const change = data.close - data.open;
                    const changePct = ((change / data.open) * 100).toFixed(2);
                    const colorClass = change >= 0 ? 'up' : 'down';
                    legendHtml += `
                        <div class="legend-row"><span class="legend-label">O</span><span class="legend-value">${{formatValue(data.open)}}</span></div>
                        <div class="legend-row"><span class="legend-label">H</span><span class="legend-value">${{formatValue(data.high)}}</span></div>
                        <div class="legend-row"><span class="legend-label">L</span><span class="legend-value">${{formatValue(data.low)}}</span></div>
                        <div class="legend-row"><span class="legend-label">C</span><span class="legend-value ${{colorClass}}">${{formatValue(data.close)}}</span></div>
                    `;
                }}

                legendEl.innerHTML = legendHtml;
            }});

            // WebSocket connection
            {ws_connect_code}

            // Start WebSocket
            connectWebSocket();

            // Fit content and resize handling
            chart.timeScale().fitContent();

            window.addEventListener('resize', () => {{
                const newWidth = container.offsetWidth;
                if (newWidth > 0) chart.applyOptions({{ width: newWidth }});
            }});

            // Double-click to reset zoom
            container.addEventListener('dblclick', () => {{
                chart.timeScale().fitContent();
            }});

        }} catch (error) {{
            console.error('Chart initialization error:', error);
        }}
    }}

    initChart();
    </script>
</body>
</html>
        """
        return html
