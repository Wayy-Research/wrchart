"""
ForecastChart - Interactive Monte Carlo forecast visualization.

Provides efficient rendering of hundreds of paths with density-based coloring,
percentile lines, and confidence intervals using WebGL acceleration.
"""

from typing import Any, Dict, List, Optional, Tuple, Union
import json
import uuid

import numpy as np
import polars as pl

from wrchart.core.themes import Theme, DarkTheme, WayyTheme
from wrchart.forecast.colorscales import (
    Colorscale,
    VIRIDIS,
    PLASMA,
    INFERNO,
    HOT,
    get_colorscale,
)
from wrchart.forecast.utils import (
    compute_path_colors_by_density,
    compute_percentiles,
    compute_path_density,
)


class ForecastChart:
    """
    Interactive chart for Monte Carlo forecast visualization.

    Renders hundreds of paths with density-based coloring, showing
    where forecasts are most likely to occur.

    Example:
        >>> import wrchart as wrc
        >>> from wrchart.forecast import ForecastChart
        >>> import numpy as np
        >>>
        >>> # Historical prices and forecast result
        >>> prices = np.array([100, 101, 102, ...])
        >>> result = {
        ...     'paths': np.random.randn(500, 30),  # 500 paths, 30 steps
        ...     'probabilities': np.random.rand(500),
        ...     'weighted_forecast': np.mean(...),
        ... }
        >>>
        >>> chart = ForecastChart(width=1000, height=600)
        >>> chart.set_data(prices, result)
        >>> chart.show()
    """

    # Theme presets optimized for path visualization
    DARK_THEME = "dark"
    LIGHT_THEME = "light"

    def __init__(
        self,
        width: int = 1000,
        height: int = 600,
        theme: str = "dark",
        title: Optional[str] = None,
    ):
        """
        Initialize a ForecastChart.

        Args:
            width: Chart width in pixels
            height: Chart height in pixels
            theme: Theme preset ('dark' or 'light')
            title: Optional chart title
        """
        self.width = width
        self.height = height
        self.theme = theme
        self.title = title
        self._id = str(uuid.uuid4())[:8]

        # Data
        self._historical_prices: Optional[np.ndarray] = None
        self._historical_dates: Optional[np.ndarray] = None
        self._paths: Optional[np.ndarray] = None
        self._probabilities: Optional[np.ndarray] = None
        self._forecast_dates: Optional[np.ndarray] = None
        self._weighted_forecast: Optional[np.ndarray] = None

        # Display options
        self._colorscale: Colorscale = VIRIDIS
        self._max_paths: int = 500
        self._show_percentiles: bool = True
        self._show_density_heatmap: bool = False
        self._show_weighted_forecast: bool = True
        self._annotations: List[Dict[str, Any]] = []

    def set_data(
        self,
        prices: Union[np.ndarray, pl.Series, List],
        result: Dict[str, Any],
        dates: Optional[Union[np.ndarray, pl.Series, List]] = None,
    ) -> "ForecastChart":
        """
        Set the forecast data.

        Args:
            prices: Historical price data
            result: Forecast result dict containing:
                - paths: (n_paths, n_steps) array of Monte Carlo paths
                - probabilities: (n_paths,) array of path probabilities
                - weighted_forecast: (n_steps,) weighted forecast (optional)
                - dates: forecast dates (optional)
            dates: Historical dates (optional)

        Returns:
            Self for chaining
        """
        # Convert to numpy
        if isinstance(prices, pl.Series):
            self._historical_prices = prices.to_numpy()
        elif isinstance(prices, list):
            self._historical_prices = np.array(prices)
        else:
            self._historical_prices = np.asarray(prices)

        if dates is not None:
            if isinstance(dates, pl.Series):
                self._historical_dates = dates.to_numpy()
            elif isinstance(dates, list):
                self._historical_dates = np.array(dates)
            else:
                self._historical_dates = np.asarray(dates)

        # Extract forecast data
        self._paths = np.asarray(result["paths"])
        self._probabilities = result.get("probabilities")
        if self._probabilities is not None:
            self._probabilities = np.asarray(self._probabilities)

        self._weighted_forecast = result.get("weighted_forecast")
        if self._weighted_forecast is not None:
            self._weighted_forecast = np.asarray(self._weighted_forecast)

        self._forecast_dates = result.get("dates")
        if self._forecast_dates is not None:
            if isinstance(self._forecast_dates, pl.Series):
                self._forecast_dates = self._forecast_dates.to_numpy()
            else:
                self._forecast_dates = np.asarray(self._forecast_dates)

        return self

    def colorscale(self, name: str) -> "ForecastChart":
        """
        Set the colorscale for path density visualization.

        Args:
            name: Colorscale name ('viridis', 'plasma', 'inferno', 'hot')

        Returns:
            Self for chaining
        """
        self._colorscale = get_colorscale(name)
        return self

    def max_paths(self, n: int) -> "ForecastChart":
        """
        Set maximum number of paths to display.

        Args:
            n: Maximum number of paths

        Returns:
            Self for chaining
        """
        self._max_paths = n
        return self

    def show_percentiles(self, show: bool = True) -> "ForecastChart":
        """
        Toggle percentile line display.

        Args:
            show: Whether to show percentile lines

        Returns:
            Self for chaining
        """
        self._show_percentiles = show
        return self

    def show_density_heatmap(self, show: bool = True) -> "ForecastChart":
        """
        Toggle density heatmap display.

        Args:
            show: Whether to show density heatmap

        Returns:
            Self for chaining
        """
        self._show_density_heatmap = show
        return self

    def show_weighted_forecast(self, show: bool = True) -> "ForecastChart":
        """
        Toggle weighted forecast line display.

        Args:
            show: Whether to show weighted forecast

        Returns:
            Self for chaining
        """
        self._show_weighted_forecast = show
        return self

    def add_annotation(
        self,
        text: str,
        x: float = 0.02,
        y: float = 0.98,
        font_size: int = 10,
    ) -> "ForecastChart":
        """
        Add a text annotation to the chart.

        Args:
            text: Annotation text (can include HTML line breaks)
            x: X position (0-1, paper coordinates)
            y: Y position (0-1, paper coordinates)
            font_size: Font size in pixels

        Returns:
            Self for chaining
        """
        self._annotations.append(
            {
                "text": text,
                "x": x,
                "y": y,
                "font_size": font_size,
            }
        )
        return self

    def _prepare_data(self) -> Dict[str, Any]:
        """Prepare data for JavaScript rendering."""
        if self._paths is None or self._historical_prices is None:
            raise ValueError("No data set. Call set_data() first.")

        n_paths, n_steps = self._paths.shape
        n_hist = len(self._historical_prices)

        # Compute path density scores
        density_scores = compute_path_colors_by_density(
            self._paths, self._probabilities
        )

        # Sort paths by density (draw low density first)
        sort_idx = np.argsort(density_scores)

        # Subsample if too many paths
        if n_paths > self._max_paths:
            # Sample proportionally to density
            sample_probs = density_scores / density_scores.sum()
            sample_idx = np.random.choice(
                n_paths, size=self._max_paths, replace=False, p=sample_probs
            )
            display_idx = sort_idx[np.isin(sort_idx, sample_idx)]
        else:
            display_idx = sort_idx

        # Prepare path data
        paths_data = []
        last_price = float(self._historical_prices[-1])

        for idx in display_idx:
            score = float(density_scores[idx])
            path = self._paths[idx]
            # Prepend last historical price for connection
            path_values = [last_price] + path.tolist()
            color = self._colorscale.to_color(score)
            opacity = 0.2 + 0.6 * score
            width = 0.5 + 1.5 * score

            paths_data.append(
                {
                    "values": path_values,
                    "color": color,
                    "opacity": opacity,
                    "width": width,
                    "score": score,
                }
            )

        # Compute percentiles
        percentiles_data = {}
        if self._show_percentiles:
            percentiles = compute_percentiles(self._paths)
            for p, values in percentiles.items():
                percentiles_data[p] = [last_price] + values.tolist()

        # Weighted forecast
        weighted_data = None
        if self._show_weighted_forecast and self._weighted_forecast is not None:
            weighted_data = [last_price] + self._weighted_forecast.tolist()

        # Historical data
        hist_values = self._historical_prices.tolist()

        # Prepare x-axis indices
        hist_x = list(range(n_hist))
        forecast_x = list(range(n_hist - 1, n_hist + n_steps))

        # Density heatmap data
        heatmap_data = None
        if self._show_density_heatmap:
            density, time_edges, price_edges = compute_path_density(
                self._paths,
                n_time_bins=min(50, n_steps),
                n_price_bins=100,
                probabilities=self._probabilities,
            )
            heatmap_data = {
                "density": density.tolist(),
                "time_edges": time_edges.tolist(),
                "price_edges": price_edges.tolist(),
            }

        return {
            "historical": {
                "x": hist_x,
                "y": hist_values,
            },
            "paths": paths_data,
            "forecast_x": forecast_x,
            "percentiles": percentiles_data,
            "weighted_forecast": weighted_data,
            "heatmap": heatmap_data,
            "colorscale": self._colorscale.to_js_array(),
            "annotations": self._annotations,
        }

    def _generate_html(self) -> str:
        """Generate HTML/JS for rendering."""
        data = self._prepare_data()
        data_json = json.dumps(data)

        # Theme colors
        if self.theme == "dark":
            bg_color = "rgb(20, 20, 30)"
            text_color = "white"
            grid_color = "rgba(128, 128, 128, 0.2)"
            hist_color = "white"
        else:
            bg_color = "#fafafa"
            text_color = "black"
            grid_color = "rgba(128, 128, 128, 0.3)"
            hist_color = "black"

        html = f"""
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&display=swap');

            #forecast-container-{self._id} {{
                font-family: 'Space Grotesk', -apple-system, BlinkMacSystemFont, sans-serif;
                background: {bg_color};
                padding: 16px;
                border-radius: 0;
            }}
            #forecast-title-{self._id} {{
                font-size: 16px;
                font-weight: 600;
                color: {text_color};
                margin-bottom: 12px;
                letter-spacing: -0.02em;
            }}
            #forecast-canvas-{self._id} {{
                display: block;
            }}
            .forecast-legend-{self._id} {{
                display: flex;
                align-items: center;
                gap: 20px;
                margin-top: 12px;
                font-size: 11px;
                color: {text_color};
            }}
            .forecast-legend-item {{
                display: flex;
                align-items: center;
                gap: 6px;
            }}
            .forecast-legend-color {{
                width: 20px;
                height: 3px;
            }}
            .forecast-colorbar-{self._id} {{
                display: flex;
                align-items: center;
                gap: 8px;
                margin-top: 8px;
            }}
            .forecast-colorbar-gradient {{
                width: 150px;
                height: 12px;
                border-radius: 0;
            }}
            .forecast-colorbar-label {{
                font-size: 10px;
                color: {text_color};
                opacity: 0.7;
            }}
        </style>

        <div id="forecast-container-{self._id}">
            {"<div id='forecast-title-" + self._id + "'>" + (self.title or "Forecast with Path Density") + "</div>" if self.title else ""}
            <canvas id="forecast-canvas-{self._id}" width="{self.width}" height="{self.height}"></canvas>
            <div class="forecast-legend-{self._id}">
                <div class="forecast-legend-item">
                    <div class="forecast-legend-color" style="background: {hist_color};"></div>
                    <span>Historical</span>
                </div>
                <div class="forecast-legend-item">
                    <div class="forecast-legend-color" style="background: white; border: 1px solid red;"></div>
                    <span>Weighted Forecast</span>
                </div>
                <div class="forecast-legend-item">
                    <div class="forecast-legend-color" style="background: rgba(255, 100, 100, 1);"></div>
                    <span>Median (50th)</span>
                </div>
                <div class="forecast-legend-item">
                    <div class="forecast-legend-color" style="background: rgba(100, 100, 255, 0.8); border-style: dashed;"></div>
                    <span>5th/95th Percentile</span>
                </div>
            </div>
            <div class="forecast-colorbar-{self._id}">
                <span class="forecast-colorbar-label">Low Probability</span>
                <div class="forecast-colorbar-gradient" id="colorbar-{self._id}"></div>
                <span class="forecast-colorbar-label">High Probability</span>
            </div>
        </div>

        <script>
        (function() {{
            const data = {data_json};
            const canvas = document.getElementById('forecast-canvas-{self._id}');
            const ctx = canvas.getContext('2d');

            // High DPI support
            const dpr = window.devicePixelRatio || 1;
            canvas.width = {self.width} * dpr;
            canvas.height = {self.height} * dpr;
            canvas.style.width = '{self.width}px';
            canvas.style.height = '{self.height}px';
            ctx.scale(dpr, dpr);

            const width = {self.width};
            const height = {self.height};
            const padding = {{ top: 20, right: 80, bottom: 40, left: 60 }};
            const chartWidth = width - padding.left - padding.right;
            const chartHeight = height - padding.top - padding.bottom;

            // Compute data ranges
            const allValues = [...data.historical.y];
            data.paths.forEach(p => allValues.push(...p.values));
            if (data.weighted_forecast) allValues.push(...data.weighted_forecast);
            Object.values(data.percentiles).forEach(p => allValues.push(...p));

            const yMin = Math.min(...allValues) * 0.98;
            const yMax = Math.max(...allValues) * 1.02;
            const xMin = 0;
            const xMax = data.forecast_x[data.forecast_x.length - 1];

            // Scale functions
            const scaleX = (x) => padding.left + (x - xMin) / (xMax - xMin) * chartWidth;
            const scaleY = (y) => padding.top + chartHeight - (y - yMin) / (yMax - yMin) * chartHeight;

            // Clear and set background
            ctx.fillStyle = '{bg_color}';
            ctx.fillRect(0, 0, width, height);

            // Draw grid
            ctx.strokeStyle = '{grid_color}';
            ctx.lineWidth = 1;
            const nGridLines = 6;
            for (let i = 0; i <= nGridLines; i++) {{
                const y = padding.top + (chartHeight / nGridLines) * i;
                ctx.beginPath();
                ctx.moveTo(padding.left, y);
                ctx.lineTo(width - padding.right, y);
                ctx.stroke();
            }}

            // Draw y-axis labels
            ctx.fillStyle = '{text_color}';
            ctx.font = '11px Space Grotesk, sans-serif';
            ctx.textAlign = 'right';
            for (let i = 0; i <= nGridLines; i++) {{
                const y = padding.top + (chartHeight / nGridLines) * i;
                const value = yMax - (yMax - yMin) * (i / nGridLines);
                ctx.fillText(value.toFixed(2), padding.left - 8, y + 4);
            }}

            // Draw x-axis labels
            ctx.textAlign = 'center';
            const nXLabels = 6;
            for (let i = 0; i <= nXLabels; i++) {{
                const x = padding.left + (chartWidth / nXLabels) * i;
                const xVal = xMin + (xMax - xMin) * (i / nXLabels);
                ctx.fillText(Math.round(xVal).toString(), x, height - padding.bottom + 20);
            }}

            // Draw individual paths (low density first)
            data.paths.forEach(path => {{
                ctx.beginPath();
                ctx.strokeStyle = path.color;
                ctx.globalAlpha = path.opacity;
                ctx.lineWidth = path.width;

                for (let i = 0; i < path.values.length; i++) {{
                    const x = scaleX(data.forecast_x[i]);
                    const y = scaleY(path.values[i]);
                    if (i === 0) ctx.moveTo(x, y);
                    else ctx.lineTo(x, y);
                }}
                ctx.stroke();
            }});

            ctx.globalAlpha = 1;

            // Draw percentile lines
            const percentileStyles = {{
                5: {{ color: 'rgba(100, 100, 255, 0.8)', width: 1, dash: [4, 4] }},
                25: {{ color: 'rgba(100, 150, 255, 0.8)', width: 1.5, dash: [6, 3] }},
                50: {{ color: 'rgba(255, 100, 100, 1.0)', width: 3, dash: [] }},
                75: {{ color: 'rgba(100, 150, 255, 0.8)', width: 1.5, dash: [6, 3] }},
                95: {{ color: 'rgba(100, 100, 255, 0.8)', width: 1, dash: [4, 4] }}
            }};

            Object.entries(data.percentiles).forEach(([p, values]) => {{
                const style = percentileStyles[p];
                ctx.beginPath();
                ctx.strokeStyle = style.color;
                ctx.lineWidth = style.width;
                ctx.setLineDash(style.dash);

                for (let i = 0; i < values.length; i++) {{
                    const x = scaleX(data.forecast_x[i]);
                    const y = scaleY(values[i]);
                    if (i === 0) ctx.moveTo(x, y);
                    else ctx.lineTo(x, y);
                }}
                ctx.stroke();
                ctx.setLineDash([]);
            }});

            // Draw weighted forecast
            if (data.weighted_forecast) {{
                // White outline
                ctx.beginPath();
                ctx.strokeStyle = 'white';
                ctx.lineWidth = 4;
                for (let i = 0; i < data.weighted_forecast.length; i++) {{
                    const x = scaleX(data.forecast_x[i]);
                    const y = scaleY(data.weighted_forecast[i]);
                    if (i === 0) ctx.moveTo(x, y);
                    else ctx.lineTo(x, y);
                }}
                ctx.stroke();

                // Red dashed inner line
                ctx.beginPath();
                ctx.strokeStyle = 'red';
                ctx.lineWidth = 2;
                ctx.setLineDash([6, 4]);
                for (let i = 0; i < data.weighted_forecast.length; i++) {{
                    const x = scaleX(data.forecast_x[i]);
                    const y = scaleY(data.weighted_forecast[i]);
                    if (i === 0) ctx.moveTo(x, y);
                    else ctx.lineTo(x, y);
                }}
                ctx.stroke();
                ctx.setLineDash([]);
            }}

            // Draw historical prices
            ctx.beginPath();
            ctx.strokeStyle = '{hist_color}';
            ctx.lineWidth = 3;
            for (let i = 0; i < data.historical.x.length; i++) {{
                const x = scaleX(data.historical.x[i]);
                const y = scaleY(data.historical.y[i]);
                if (i === 0) ctx.moveTo(x, y);
                else ctx.lineTo(x, y);
            }}
            ctx.stroke();

            // Draw annotations
            ctx.font = '10px Space Grotesk, sans-serif';
            ctx.textAlign = 'left';
            data.annotations.forEach(ann => {{
                const x = padding.left + ann.x * chartWidth;
                const y = padding.top + (1 - ann.y) * chartHeight;

                // Background box
                ctx.fillStyle = 'rgba(0, 0, 0, 0.7)';
                const lines = ann.text.split('<br>');
                const lineHeight = ann.font_size + 4;
                const boxHeight = lines.length * lineHeight + 8;
                const boxWidth = Math.max(...lines.map(l => ctx.measureText(l.replace(/<[^>]+>/g, '')).width)) + 16;
                ctx.fillRect(x, y, boxWidth, boxHeight);

                // Text
                ctx.fillStyle = '{text_color}';
                ctx.font = ann.font_size + 'px Space Grotesk, sans-serif';
                lines.forEach((line, i) => {{
                    const cleanLine = line.replace(/<[^>]+>/g, '');
                    ctx.fillText(cleanLine, x + 8, y + 14 + i * lineHeight);
                }});
            }});

            // Draw colorbar gradient
            const colorbar = document.getElementById('colorbar-{self._id}');
            if (colorbar) {{
                const stops = data.colorscale.map(s => {{
                    const [pos, rgb] = s;
                    return `rgb(${{rgb[0]}}, ${{rgb[1]}}, ${{rgb[2]}}) ${{pos * 100}}%`;
                }});
                colorbar.style.background = `linear-gradient(to right, ${{stops.join(', ')}})`;
            }}
        }})();
        </script>
        """
        return html

    def _repr_html_(self) -> str:
        """Jupyter notebook HTML representation."""
        return self._generate_html()

    def show(self) -> None:
        """
        Display the chart.

        In Jupyter, this renders inline. Outside Jupyter, opens in browser.
        """
        try:
            from IPython.display import display, HTML

            display(HTML(self._generate_html()))
        except ImportError:
            import tempfile
            import webbrowser

            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>{self.title or 'Forecast Chart'}</title>
            </head>
            <body style="margin: 0; padding: 20px; background: #1a1a1a;">
                {self._generate_html()}
            </body>
            </html>
            """

            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".html", delete=False
            ) as f:
                f.write(html_content)
                webbrowser.open(f"file://{f.name}")

    def to_html(self, filepath: str) -> None:
        """
        Save chart to an HTML file.

        Args:
            filepath: Path to save the HTML file
        """
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>{self.title or 'Forecast Chart'}</title>
        </head>
        <body style="margin: 0; padding: 20px; background: {'rgb(20, 20, 30)' if self.theme == 'dark' else '#fafafa'};">
            {self._generate_html()}
        </body>
        </html>
        """

        with open(filepath, "w") as f:
            f.write(html_content)

    def streamlit(self, height: Optional[int] = None) -> None:
        """
        Display the chart in Streamlit.

        This method generates HTML optimized for Streamlit's iframe environment.

        Args:
            height: Optional height override (defaults to chart height + 100)
        """
        import streamlit.components.v1 as components

        render_height = height or (self.height + 100)
        html = self._generate_streamlit_html()
        components.html(html, height=render_height, scrolling=False)

    def _generate_streamlit_html(self) -> str:
        """Generate HTML optimized for Streamlit iframe rendering."""
        data = self._prepare_data()
        data_json = json.dumps(data)

        # Theme colors
        if self.theme == "dark":
            bg_color = "rgb(20, 20, 30)"
            text_color = "white"
            grid_color = "rgba(128, 128, 128, 0.2)"
            hist_color = "white"
        else:
            bg_color = "#fafafa"
            text_color = "black"
            grid_color = "rgba(128, 128, 128, 0.3)"
            hist_color = "black"

        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&display=swap');
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Space Grotesk', -apple-system, BlinkMacSystemFont, sans-serif;
            background: {bg_color};
            padding: 8px;
        }}
        #forecast-container {{
            width: 100%;
        }}
        #forecast-title {{
            font-size: 16px;
            font-weight: 600;
            color: {text_color};
            margin-bottom: 12px;
            letter-spacing: -0.02em;
        }}
        #forecast-canvas {{
            display: block;
            max-width: 100%;
        }}
        .forecast-legend {{
            display: flex;
            align-items: center;
            gap: 20px;
            margin-top: 12px;
            font-size: 11px;
            color: {text_color};
            flex-wrap: wrap;
        }}
        .forecast-legend-item {{
            display: flex;
            align-items: center;
            gap: 6px;
        }}
        .forecast-legend-color {{
            width: 20px;
            height: 3px;
        }}
        .forecast-colorbar {{
            display: flex;
            align-items: center;
            gap: 8px;
            margin-top: 8px;
        }}
        .forecast-colorbar-gradient {{
            width: 150px;
            height: 12px;
            border-radius: 0;
        }}
        .forecast-colorbar-label {{
            font-size: 10px;
            color: {text_color};
            opacity: 0.7;
        }}
        #forecast-tooltip {{
            position: absolute;
            background: rgba(0, 0, 0, 0.85);
            color: white;
            padding: 8px 12px;
            border-radius: 4px;
            font-size: 11px;
            pointer-events: none;
            display: none;
            z-index: 100;
            font-family: 'JetBrains Mono', monospace;
        }}
        #forecast-crosshair {{
            position: absolute;
            pointer-events: none;
            display: none;
        }}
        #forecast-crosshair-v {{
            position: absolute;
            width: 1px;
            background: rgba(128, 128, 128, 0.5);
            top: 20px;
        }}
        #forecast-crosshair-h {{
            position: absolute;
            height: 1px;
            background: rgba(128, 128, 128, 0.5);
            left: 60px;
        }}
    </style>
</head>
<body>
    <div id="forecast-container" style="position: relative;">
        {"<div id='forecast-title'>" + (self.title or "Forecast with Path Density") + "</div>" if self.title else ""}
        <div id="forecast-tooltip"></div>
        <div id="forecast-crosshair">
            <div id="forecast-crosshair-v"></div>
            <div id="forecast-crosshair-h"></div>
        </div>
        <canvas id="forecast-canvas" width="{self.width}" height="{self.height}" style="cursor: crosshair;"></canvas>
        <div class="forecast-legend">
            <div class="forecast-legend-item">
                <div class="forecast-legend-color" style="background: {hist_color};"></div>
                <span>Historical</span>
            </div>
            <div class="forecast-legend-item">
                <div class="forecast-legend-color" style="background: white; border: 1px solid red;"></div>
                <span>Weighted Forecast</span>
            </div>
            <div class="forecast-legend-item">
                <div class="forecast-legend-color" style="background: rgba(255, 100, 100, 1);"></div>
                <span>Median (50th)</span>
            </div>
            <div class="forecast-legend-item">
                <div class="forecast-legend-color" style="background: rgba(100, 100, 255, 0.8); border-style: dashed;"></div>
                <span>5th/95th Percentile</span>
            </div>
        </div>
        <div class="forecast-colorbar">
            <span class="forecast-colorbar-label">Low Probability</span>
            <div class="forecast-colorbar-gradient" id="colorbar"></div>
            <span class="forecast-colorbar-label">High Probability</span>
        </div>
    </div>
    <script>
    (function() {{
        const data = {data_json};
        const canvas = document.getElementById('forecast-canvas');
        const ctx = canvas.getContext('2d');

        // High DPI support
        const dpr = window.devicePixelRatio || 1;
        canvas.width = {self.width} * dpr;
        canvas.height = {self.height} * dpr;
        canvas.style.width = '{self.width}px';
        canvas.style.height = '{self.height}px';
        ctx.scale(dpr, dpr);

        const width = {self.width};
        const height = {self.height};
        const padding = {{ top: 20, right: 80, bottom: 40, left: 60 }};
        const chartWidth = width - padding.left - padding.right;
        const chartHeight = height - padding.top - padding.bottom;

        // Compute data ranges
        const allValues = [...data.historical.y];
        data.paths.forEach(p => allValues.push(...p.values));
        if (data.weighted_forecast) allValues.push(...data.weighted_forecast);
        Object.values(data.percentiles).forEach(p => allValues.push(...p));

        const yMin = Math.min(...allValues) * 0.98;
        const yMax = Math.max(...allValues) * 1.02;
        const xMin = 0;
        const xMax = data.forecast_x[data.forecast_x.length - 1];

        // Scale functions
        const scaleX = (x) => padding.left + (x - xMin) / (xMax - xMin) * chartWidth;
        const scaleY = (y) => padding.top + chartHeight - (y - yMin) / (yMax - yMin) * chartHeight;

        // Clear and set background
        ctx.fillStyle = '{bg_color}';
        ctx.fillRect(0, 0, width, height);

        // Draw grid
        ctx.strokeStyle = '{grid_color}';
        ctx.lineWidth = 1;
        const nGridLines = 6;
        for (let i = 0; i <= nGridLines; i++) {{
            const y = padding.top + (chartHeight / nGridLines) * i;
            ctx.beginPath();
            ctx.moveTo(padding.left, y);
            ctx.lineTo(width - padding.right, y);
            ctx.stroke();
        }}

        // Draw y-axis labels
        ctx.fillStyle = '{text_color}';
        ctx.font = '11px Space Grotesk, sans-serif';
        ctx.textAlign = 'right';
        for (let i = 0; i <= nGridLines; i++) {{
            const y = padding.top + (chartHeight / nGridLines) * i;
            const value = yMax - (yMax - yMin) * (i / nGridLines);
            ctx.fillText(value.toFixed(2), padding.left - 8, y + 4);
        }}

        // Draw x-axis labels
        ctx.textAlign = 'center';
        const nXLabels = 6;
        for (let i = 0; i <= nXLabels; i++) {{
            const x = padding.left + (chartWidth / nXLabels) * i;
            const xVal = xMin + (xMax - xMin) * (i / nXLabels);
            ctx.fillText(Math.round(xVal).toString(), x, height - padding.bottom + 20);
        }}

        // Draw individual paths (low density first)
        data.paths.forEach(path => {{
            ctx.beginPath();
            ctx.strokeStyle = path.color;
            ctx.globalAlpha = path.opacity;
            ctx.lineWidth = path.width;

            for (let i = 0; i < path.values.length; i++) {{
                const x = scaleX(data.forecast_x[i]);
                const y = scaleY(path.values[i]);
                if (i === 0) ctx.moveTo(x, y);
                else ctx.lineTo(x, y);
            }}
            ctx.stroke();
        }});

        ctx.globalAlpha = 1;

        // Draw percentile lines
        const percentileStyles = {{
            5: {{ color: 'rgba(100, 100, 255, 0.8)', width: 1, dash: [4, 4] }},
            25: {{ color: 'rgba(100, 150, 255, 0.8)', width: 1.5, dash: [6, 3] }},
            50: {{ color: 'rgba(255, 100, 100, 1.0)', width: 3, dash: [] }},
            75: {{ color: 'rgba(100, 150, 255, 0.8)', width: 1.5, dash: [6, 3] }},
            95: {{ color: 'rgba(100, 100, 255, 0.8)', width: 1, dash: [4, 4] }}
        }};

        Object.entries(data.percentiles).forEach(([p, values]) => {{
            const style = percentileStyles[p];
            ctx.beginPath();
            ctx.strokeStyle = style.color;
            ctx.lineWidth = style.width;
            ctx.setLineDash(style.dash);

            for (let i = 0; i < values.length; i++) {{
                const x = scaleX(data.forecast_x[i]);
                const y = scaleY(values[i]);
                if (i === 0) ctx.moveTo(x, y);
                else ctx.lineTo(x, y);
            }}
            ctx.stroke();
            ctx.setLineDash([]);
        }});

        // Draw weighted forecast
        if (data.weighted_forecast) {{
            // White outline
            ctx.beginPath();
            ctx.strokeStyle = 'white';
            ctx.lineWidth = 4;
            for (let i = 0; i < data.weighted_forecast.length; i++) {{
                const x = scaleX(data.forecast_x[i]);
                const y = scaleY(data.weighted_forecast[i]);
                if (i === 0) ctx.moveTo(x, y);
                else ctx.lineTo(x, y);
            }}
            ctx.stroke();

            // Red dashed inner line
            ctx.beginPath();
            ctx.strokeStyle = 'red';
            ctx.lineWidth = 2;
            ctx.setLineDash([6, 4]);
            for (let i = 0; i < data.weighted_forecast.length; i++) {{
                const x = scaleX(data.forecast_x[i]);
                const y = scaleY(data.weighted_forecast[i]);
                if (i === 0) ctx.moveTo(x, y);
                else ctx.lineTo(x, y);
            }}
            ctx.stroke();
            ctx.setLineDash([]);
        }}

        // Draw historical prices
        ctx.beginPath();
        ctx.strokeStyle = '{hist_color}';
        ctx.lineWidth = 3;
        for (let i = 0; i < data.historical.x.length; i++) {{
            const x = scaleX(data.historical.x[i]);
            const y = scaleY(data.historical.y[i]);
            if (i === 0) ctx.moveTo(x, y);
            else ctx.lineTo(x, y);
        }}
        ctx.stroke();

        // Draw annotations
        ctx.font = '10px Space Grotesk, sans-serif';
        ctx.textAlign = 'left';
        data.annotations.forEach(ann => {{
            const x = padding.left + ann.x * chartWidth;
            const y = padding.top + (1 - ann.y) * chartHeight;

            // Background box
            ctx.fillStyle = 'rgba(0, 0, 0, 0.7)';
            const lines = ann.text.split('<br>');
            const lineHeight = ann.font_size + 4;
            const boxHeight = lines.length * lineHeight + 8;
            const boxWidth = Math.max(...lines.map(l => ctx.measureText(l.replace(/<[^>]+>/g, '')).width)) + 16;
            ctx.fillRect(x, y, boxWidth, boxHeight);

            // Text
            ctx.fillStyle = '{text_color}';
            ctx.font = ann.font_size + 'px Space Grotesk, sans-serif';
            lines.forEach((line, i) => {{
                const cleanLine = line.replace(/<[^>]+>/g, '');
                ctx.fillText(cleanLine, x + 8, y + 14 + i * lineHeight);
            }});
        }});

        // Draw colorbar gradient
        const colorbar = document.getElementById('colorbar');
        if (colorbar) {{
            const stops = data.colorscale.map(s => {{
                const [pos, rgb] = s;
                return `rgb(${{rgb[0]}}, ${{rgb[1]}}, ${{rgb[2]}}) ${{pos * 100}}%`;
            }});
            colorbar.style.background = `linear-gradient(to right, ${{stops.join(', ')}})`;
        }}

        // Interactive tooltip
        const tooltip = document.getElementById('forecast-tooltip');
        const crosshair = document.getElementById('forecast-crosshair');
        const crosshairV = document.getElementById('forecast-crosshair-v');
        const crosshairH = document.getElementById('forecast-crosshair-h');

        // Get value at x position
        function getValuesAtX(xIdx) {{
            const result = {{}};

            // Historical
            if (xIdx < data.historical.x.length) {{
                result.historical = data.historical.y[xIdx];
                result.type = 'historical';
                result.idx = xIdx;
            }} else {{
                // Forecast region
                const forecastIdx = xIdx - data.historical.x.length + 1;
                result.type = 'forecast';
                result.idx = forecastIdx;

                if (data.weighted_forecast && forecastIdx < data.weighted_forecast.length) {{
                    result.forecast = data.weighted_forecast[forecastIdx];
                }}
                if (data.percentiles['50'] && forecastIdx < data.percentiles['50'].length) {{
                    result.median = data.percentiles['50'][forecastIdx];
                }}
                if (data.percentiles['5'] && forecastIdx < data.percentiles['5'].length) {{
                    result.p5 = data.percentiles['5'][forecastIdx];
                }}
                if (data.percentiles['95'] && forecastIdx < data.percentiles['95'].length) {{
                    result.p95 = data.percentiles['95'][forecastIdx];
                }}
            }}
            return result;
        }}

        canvas.addEventListener('mousemove', (e) => {{
            const rect = canvas.getBoundingClientRect();
            const x = e.clientX - rect.left;
            const y = e.clientY - rect.top;

            // Check if in chart area
            if (x < padding.left || x > width - padding.right ||
                y < padding.top || y > height - padding.bottom) {{
                tooltip.style.display = 'none';
                crosshair.style.display = 'none';
                return;
            }}

            // Calculate data index
            const xRatio = (x - padding.left) / chartWidth;
            const xVal = xMin + xRatio * (xMax - xMin);
            const xIdx = Math.round(xVal);

            // Calculate price at y
            const yRatio = 1 - (y - padding.top) / chartHeight;
            const price = yMin + yRatio * (yMax - yMin);

            // Get values at this x
            const values = getValuesAtX(xIdx);

            // Build tooltip content
            let html = '';
            if (values.type === 'historical') {{
                html = `<div style="color: #888;">Historical</div>`;
                html += `<div>Bar: ${{values.idx}}</div>`;
                html += `<div>Price: <b>$${{values.historical.toFixed(2)}}</b></div>`;
            }} else {{
                html = `<div style="color: #888;">Forecast Step ${{values.idx}}</div>`;
                if (values.forecast !== undefined) {{
                    html += `<div>Forecast: <b>$${{values.forecast.toFixed(2)}}</b></div>`;
                }}
                if (values.median !== undefined) {{
                    html += `<div>Median: $${{values.median.toFixed(2)}}</div>`;
                }}
                if (values.p5 !== undefined && values.p95 !== undefined) {{
                    html += `<div style="color: #888; font-size: 10px;">Range: $${{values.p5.toFixed(2)}} - $${{values.p95.toFixed(2)}}</div>`;
                }}
            }}
            html += `<div style="color: #666; font-size: 10px; margin-top: 4px;">Cursor: $${{price.toFixed(2)}}</div>`;

            tooltip.innerHTML = html;
            tooltip.style.display = 'block';

            // Position tooltip
            let tooltipX = x + 15;
            let tooltipY = y - 10;
            if (tooltipX + 150 > width) tooltipX = x - 160;
            if (tooltipY < 0) tooltipY = y + 20;
            tooltip.style.left = tooltipX + 'px';
            tooltip.style.top = tooltipY + 'px';

            // Position crosshair
            crosshair.style.display = 'block';
            crosshairV.style.left = x + 'px';
            crosshairV.style.height = chartHeight + 'px';
            crosshairH.style.top = y + 'px';
            crosshairH.style.width = chartWidth + 'px';
        }});

        canvas.addEventListener('mouseleave', () => {{
            tooltip.style.display = 'none';
            crosshair.style.display = 'none';
        }});
    }})();
    </script>
</body>
</html>
        """
        return html
