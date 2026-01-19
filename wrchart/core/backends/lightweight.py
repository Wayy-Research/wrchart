"""
Lightweight Charts backend for interactive financial charts.

Uses TradingView's Lightweight Charts library (v4.2.1) for rendering
interactive candlestick, line, area, and histogram charts.
"""

from typing import Any, Dict, List, Optional
import json

import polars as pl

from wrchart.core.backends.base import Backend, BackendType, RenderConfig
from wrchart.core.series import (
    BaseSeries,
    CandlestickSeries,
    CandlestickOptions,
    LineSeries,
    LineOptions,
    AreaSeries,
    AreaOptions,
    HistogramSeries,
    HistogramOptions,
)


class LightweightChartsBackend(Backend):
    """
    Backend using TradingView's Lightweight Charts library.

    Best for:
    - Interactive OHLC charts
    - Data up to ~100k points
    - Full feature set (crosshair, legend, zoom, pan)
    """

    def __init__(self, config: Optional[RenderConfig] = None):
        super().__init__(config)
        self._series: List[BaseSeries] = []

    @property
    def backend_type(self) -> BackendType:
        return BackendType.LIGHTWEIGHT

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
    ) -> "LightweightChartsBackend":
        """Add a data series to the chart."""
        if series_type == "candlestick":
            series = CandlestickSeries(
                data=data,
                time_col=time_col,
                open_col=open_col or "open",
                high_col=high_col or "high",
                low_col=low_col or "low",
                close_col=close_col or "close",
                options=CandlestickOptions(**options) if options else None,
            )
        elif series_type == "line":
            series = LineSeries(
                data=data,
                time_col=time_col,
                value_col=value_col or close_col or "value",
                options=LineOptions(**options) if options else None,
            )
        elif series_type == "area":
            series = AreaSeries(
                data=data,
                time_col=time_col,
                value_col=value_col or close_col or "value",
                options=AreaOptions(**options) if options else None,
            )
        elif series_type == "histogram":
            series = HistogramSeries(
                data=data,
                time_col=time_col,
                value_col=value_col or "value",
                color_col=options.pop("color_col", None),
                options=HistogramOptions(**options) if options else None,
            )
        else:
            raise ValueError(f"Unknown series type: {series_type}")

        series._id = f"series_{len(self._series)}"
        self._series.append(series)
        return self

    def add_volume(
        self,
        data: pl.DataFrame,
        time_col: str = "time",
        volume_col: str = "volume",
        open_col: str = "open",
        close_col: str = "close",
        up_color: Optional[str] = None,
        down_color: Optional[str] = None,
    ) -> "LightweightChartsBackend":
        """Add a volume histogram with up/down coloring."""
        up_c = up_color or self.config.theme.colors.volume_up
        down_c = down_color or self.config.theme.colors.volume_down

        volume_data = data.select([
            pl.col(time_col).alias("time"),
            pl.col(volume_col).alias("value"),
            pl.when(pl.col(close_col) >= pl.col(open_col))
            .then(pl.lit(up_c))
            .otherwise(pl.lit(down_c))
            .alias("color"),
        ])

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
        series._id = f"series_{len(self._series)}"
        self._series.append(series)
        return self

    def to_json(self) -> str:
        """Generate JSON configuration for the chart."""
        # Sort series so candlestick comes last (renders on top)
        sorted_series = sorted(
            self._series,
            key=lambda s: 1 if s.series_type() == "Candlestick" else 0
        )

        config = {
            "id": self.config.chart_id,
            "width": self.config.width,
            "height": self.config.height,
            "title": self.config.title,
            "options": self.config.theme.to_lightweight_charts_options(),
            "series": [
                {
                    "id": s._id,
                    "type": s.series_type(),
                    "data": s.to_js_data(),
                    "options": s.to_js_options(self.config.theme),
                }
                for s in sorted_series
            ],
            "markers": self._markers,
            "priceLines": self._price_lines,
        }
        return json.dumps(config)

    def to_html(self) -> str:
        """Generate HTML for rendering the chart."""
        config_json = self.to_json()
        theme = self.config.theme
        chart_id = self.config.chart_id

        return f"""
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');
            #wrchart-container-{chart_id} {{
                font-family: 'Space Grotesk', -apple-system, BlinkMacSystemFont, sans-serif;
                width: 100%;
                position: relative;
            }}
            #wrchart-title-{chart_id} {{
                font-size: 14px;
                font-weight: 600;
                color: {theme.colors.text_primary};
                margin-bottom: 8px;
                letter-spacing: -0.02em;
            }}
            #wrchart-{chart_id} {{ width: 100%; }}
            #wrchart-legend-{chart_id} {{
                position: absolute;
                top: {32 if self.config.title else 8}px;
                left: 12px;
                z-index: 10;
                font-family: 'JetBrains Mono', monospace;
                font-size: 12px;
                color: {theme.colors.text_primary};
                background: {theme.colors.background}ee;
                padding: 6px 10px;
                border-radius: 4px;
                pointer-events: none;
                min-width: 200px;
            }}
            #wrchart-legend-{chart_id} .legend-date {{
                font-weight: 600;
                margin-bottom: 4px;
                color: {theme.colors.text_secondary};
            }}
            #wrchart-legend-{chart_id} .legend-row {{
                display: flex;
                justify-content: space-between;
                gap: 12px;
            }}
            #wrchart-legend-{chart_id} .legend-label {{ color: {theme.colors.text_secondary}; }}
            #wrchart-legend-{chart_id} .legend-value {{ font-weight: 500; }}
            #wrchart-legend-{chart_id} .legend-value.up {{ color: {theme.colors.candle_up}; }}
            #wrchart-legend-{chart_id} .legend-value.down {{ color: {theme.colors.candle_down}; }}
        </style>
        <div id="wrchart-container-{chart_id}">
            {"<div id='wrchart-title-" + chart_id + "'>" + self.config.title + "</div>" if self.config.title else ""}
            <div id="wrchart-legend-{chart_id}"></div>
            <div id="wrchart-{chart_id}"></div>
        </div>
        <script src="https://unpkg.com/lightweight-charts@4.2.1/dist/lightweight-charts.standalone.production.js"></script>
        <script>
        (function() {{
            const config = {config_json};
            const container = document.getElementById('wrchart-' + config.id);
            const legendEl = document.getElementById('wrchart-legend-' + config.id);
            const containerWidth = container.parentElement.offsetWidth || config.width;

            const chart = LightweightCharts.createChart(container, {{
                width: containerWidth,
                height: config.height,
                ...config.options,
                timeScale: {{
                    ...config.options.timeScale,
                    timeVisible: true,
                    secondsVisible: false,
                }},
            }});

            const seriesMap = {{}};
            let mainSeries = null;
            let fallbackMainSeries = null;

            config.series.forEach(seriesConfig => {{
                let series;
                switch(seriesConfig.type) {{
                    case 'Candlestick':
                        series = chart.addCandlestickSeries(seriesConfig.options);
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

            if (!mainSeries) mainSeries = fallbackMainSeries;

            if (config.markers.length > 0) {{
                const candlestickSeries = config.series.find(s => s.type === 'Candlestick');
                if (candlestickSeries) seriesMap[candlestickSeries.id].setMarkers(config.markers);
            }}

            const volumeSeries = config.series.find(s => s.options.priceScaleId === 'volume');
            if (volumeSeries) {{
                chart.priceScale('volume').applyOptions({{ scaleMargins: {{ top: 0.8, bottom: 0 }} }});
            }}

            if (config.priceLines && config.priceLines.length > 0 && mainSeries) {{
                config.priceLines.forEach(lineConfig => mainSeries.series.createPriceLine(lineConfig));
            }}

            function formatTime(time) {{
                if (typeof time === 'string') return time;
                const date = new Date(time * 1000);
                return date.toLocaleDateString('en-US', {{
                    weekday: 'short', year: 'numeric', month: 'short', day: 'numeric',
                    hour: '2-digit', minute: '2-digit'
                }});
            }}

            function formatValue(value) {{
                if (value === undefined || value === null) return '-';
                if (Math.abs(value) >= 1000) {{
                    return value.toLocaleString('en-US', {{ minimumFractionDigits: 2, maximumFractionDigits: 2 }});
                }}
                return value.toFixed(Math.abs(value) < 1 ? 4 : 2);
            }}

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

            container.addEventListener('dblclick', () => chart.timeScale().fitContent());

            const resizeObserver = new ResizeObserver(entries => {{
                for (let entry of entries) {{
                    const width = entry.contentRect.width;
                    if (width > 0) chart.applyOptions({{ width: width }});
                }}
            }});
            resizeObserver.observe(container.parentElement);

            chart.timeScale().fitContent();
        }})();
        </script>
        """
