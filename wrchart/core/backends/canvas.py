"""
Canvas backend for Monte Carlo forecast visualization.

Renders hundreds of paths with density-based coloring using HTML5 Canvas.
"""

from typing import Any, Dict, List, Optional, Union
import json

import numpy as np
import polars as pl

from wrchart.core.backends.base import Backend, BackendType, RenderConfig


class CanvasBackend(Backend):
    """
    Canvas-based backend for forecast path visualization.

    Best for:
    - Monte Carlo simulation paths
    - Density visualizations
    - Forecast fan charts
    """

    def __init__(self, config: Optional[RenderConfig] = None):
        super().__init__(config)
        self._historical: Optional[np.ndarray] = None
        self._paths: Optional[np.ndarray] = None
        self._probabilities: Optional[np.ndarray] = None
        self._weighted_forecast: Optional[np.ndarray] = None
        self._colorscale: str = "viridis"
        self._max_paths: int = 500
        self._show_percentiles: bool = True

    @property
    def backend_type(self) -> BackendType:
        return BackendType.CANVAS

    def set_forecast_data(
        self,
        historical: Union[np.ndarray, pl.Series, List],
        paths: np.ndarray,
        probabilities: Optional[np.ndarray] = None,
        weighted_forecast: Optional[np.ndarray] = None,
    ) -> "CanvasBackend":
        """
        Set forecast data.

        Args:
            historical: Historical price data
            paths: Monte Carlo paths (n_paths, n_steps)
            probabilities: Path probabilities (optional)
            weighted_forecast: Weighted forecast line (optional)

        Returns:
            Self for chaining
        """
        if isinstance(historical, pl.Series):
            self._historical = historical.to_numpy()
        elif isinstance(historical, list):
            self._historical = np.array(historical)
        else:
            self._historical = np.asarray(historical)

        self._paths = np.asarray(paths)
        self._probabilities = np.asarray(probabilities) if probabilities is not None else None
        self._weighted_forecast = np.asarray(weighted_forecast) if weighted_forecast is not None else None

        return self

    def add_series(
        self,
        data: pl.DataFrame,
        series_type: str,
        time_col: str,
        value_col: Optional[str] = None,
        **options,
    ) -> "CanvasBackend":
        """Not used for canvas backend - use set_forecast_data instead."""
        return self

    def colorscale(self, name: str) -> "CanvasBackend":
        """Set the colorscale for path density visualization."""
        self._colorscale = name
        return self

    def max_paths(self, n: int) -> "CanvasBackend":
        """Set maximum number of paths to display."""
        self._max_paths = n
        return self

    def show_percentiles(self, show: bool = True) -> "CanvasBackend":
        """Toggle percentile line display."""
        self._show_percentiles = show
        return self

    def _compute_density_scores(self) -> np.ndarray:
        """Compute path density scores for coloring."""
        if self._paths is None:
            return np.array([])

        n_paths, n_steps = self._paths.shape

        # Compute median path
        median_path = np.median(self._paths, axis=0)

        # Distance from median
        distances = np.mean(np.abs(self._paths - median_path), axis=1)

        # Convert to score (closer = higher score)
        max_dist = np.max(distances)
        if max_dist == 0:
            scores = np.ones(n_paths)
        else:
            scores = 1 - (distances / max_dist)

        # Weight by probabilities if available
        if self._probabilities is not None:
            prob_norm = self._probabilities / np.max(self._probabilities)
            scores = scores * 0.5 + prob_norm * 0.5

        return scores

    def _compute_percentiles(self) -> Dict[int, np.ndarray]:
        """Compute percentile lines."""
        if self._paths is None:
            return {}

        return {
            5: np.percentile(self._paths, 5, axis=0),
            25: np.percentile(self._paths, 25, axis=0),
            50: np.percentile(self._paths, 50, axis=0),
            75: np.percentile(self._paths, 75, axis=0),
            95: np.percentile(self._paths, 95, axis=0),
        }

    def _get_colorscale_stops(self) -> List[List]:
        """Get colorscale gradient stops."""
        colorscales = {
            "viridis": [[0, [68, 1, 84]], [0.25, [59, 82, 139]], [0.5, [33, 145, 140]], [0.75, [94, 201, 98]], [1, [253, 231, 37]]],
            "plasma": [[0, [13, 8, 135]], [0.25, [126, 3, 168]], [0.5, [204, 71, 120]], [0.75, [248, 149, 64]], [1, [240, 249, 33]]],
            "inferno": [[0, [0, 0, 4]], [0.25, [87, 16, 110]], [0.5, [188, 55, 84]], [0.75, [249, 142, 9]], [1, [252, 255, 164]]],
            "hot": [[0, [0, 0, 0]], [0.33, [230, 0, 0]], [0.66, [255, 210, 0]], [1, [255, 255, 255]]],
        }
        return colorscales.get(self._colorscale, colorscales["viridis"])

    def _score_to_color(self, score: float) -> str:
        """Convert score to color using colorscale."""
        stops = self._get_colorscale_stops()
        score = max(0, min(1, score))

        # Find surrounding stops
        for i in range(len(stops) - 1):
            if stops[i][0] <= score <= stops[i + 1][0]:
                t = (score - stops[i][0]) / (stops[i + 1][0] - stops[i][0])
                r = int(stops[i][1][0] + t * (stops[i + 1][1][0] - stops[i][1][0]))
                g = int(stops[i][1][1] + t * (stops[i + 1][1][1] - stops[i][1][1]))
                b = int(stops[i][1][2] + t * (stops[i + 1][1][2] - stops[i][1][2]))
                return f"rgb({r},{g},{b})"

        return "rgb(128,128,128)"

    def to_json(self) -> str:
        """Generate JSON configuration."""
        if self._paths is None or self._historical is None:
            return json.dumps({})

        n_paths, n_steps = self._paths.shape
        n_hist = len(self._historical)

        density_scores = self._compute_density_scores()
        sort_idx = np.argsort(density_scores)

        # Subsample if needed
        if n_paths > self._max_paths:
            sample_idx = np.random.choice(n_paths, size=self._max_paths, replace=False)
            display_idx = sort_idx[np.isin(sort_idx, sample_idx)]
        else:
            display_idx = sort_idx

        last_price = float(self._historical[-1])

        paths_data = []
        for idx in display_idx:
            score = float(density_scores[idx])
            path_values = [last_price] + self._paths[idx].tolist()
            paths_data.append({
                "values": path_values,
                "color": self._score_to_color(score),
                "opacity": 0.2 + 0.6 * score,
                "width": 0.5 + 1.5 * score,
            })

        percentiles = {}
        if self._show_percentiles:
            for p, values in self._compute_percentiles().items():
                percentiles[p] = [last_price] + values.tolist()

        weighted = None
        if self._weighted_forecast is not None:
            weighted = [last_price] + self._weighted_forecast.tolist()

        return json.dumps({
            "historical": {"x": list(range(n_hist)), "y": self._historical.tolist()},
            "paths": paths_data,
            "forecast_x": list(range(n_hist - 1, n_hist + n_steps)),
            "percentiles": percentiles,
            "weighted_forecast": weighted,
            "colorscale": self._get_colorscale_stops(),
        })

    def to_html(self) -> str:
        """Generate HTML for canvas rendering."""
        data_json = self.to_json()
        chart_id = self.config.chart_id
        theme = self.config.theme

        is_dark = theme.colors.background.lower() in ["#000000", "#0a0a0a", "#1a1a1e", "rgb(20, 20, 30)"]
        bg_color = "rgb(20, 20, 30)" if is_dark else "#fafafa"
        text_color = "white" if is_dark else "black"
        grid_color = "rgba(128, 128, 128, 0.2)" if is_dark else "rgba(128, 128, 128, 0.3)"
        hist_color = "white" if is_dark else "black"

        return f"""
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&display=swap');
            #forecast-container-{chart_id} {{
                font-family: 'Space Grotesk', -apple-system, BlinkMacSystemFont, sans-serif;
                background: {bg_color};
                padding: 16px;
            }}
            #forecast-title-{chart_id} {{
                font-size: 16px;
                font-weight: 600;
                color: {text_color};
                margin-bottom: 12px;
            }}
            #forecast-canvas-{chart_id} {{ display: block; }}
            .forecast-legend-{chart_id} {{
                display: flex;
                align-items: center;
                gap: 20px;
                margin-top: 12px;
                font-size: 11px;
                color: {text_color};
            }}
            .forecast-legend-item {{ display: flex; align-items: center; gap: 6px; }}
            .forecast-legend-color {{ width: 20px; height: 3px; }}
            .forecast-colorbar-{chart_id} {{
                display: flex;
                align-items: center;
                gap: 8px;
                margin-top: 8px;
            }}
            .forecast-colorbar-gradient {{ width: 150px; height: 12px; }}
            .forecast-colorbar-label {{ font-size: 10px; color: {text_color}; opacity: 0.7; }}
        </style>

        <div id="forecast-container-{chart_id}">
            {"<div id='forecast-title-" + chart_id + "'>" + (self.config.title or "Forecast") + "</div>" if self.config.title else ""}
            <canvas id="forecast-canvas-{chart_id}" width="{self.config.width}" height="{self.config.height}"></canvas>
            <div class="forecast-legend-{chart_id}">
                <div class="forecast-legend-item">
                    <div class="forecast-legend-color" style="background: {hist_color};"></div>
                    <span>Historical</span>
                </div>
                <div class="forecast-legend-item">
                    <div class="forecast-legend-color" style="background: rgba(255, 100, 100, 1);"></div>
                    <span>Median</span>
                </div>
                <div class="forecast-legend-item">
                    <div class="forecast-legend-color" style="background: rgba(100, 100, 255, 0.8);"></div>
                    <span>5th/95th</span>
                </div>
            </div>
            <div class="forecast-colorbar-{chart_id}">
                <span class="forecast-colorbar-label">Low Prob</span>
                <div class="forecast-colorbar-gradient" id="colorbar-{chart_id}"></div>
                <span class="forecast-colorbar-label">High Prob</span>
            </div>
        </div>

        <script>
        (function() {{
            const data = {data_json};
            const canvas = document.getElementById('forecast-canvas-{chart_id}');
            const ctx = canvas.getContext('2d');

            const dpr = window.devicePixelRatio || 1;
            canvas.width = {self.config.width} * dpr;
            canvas.height = {self.config.height} * dpr;
            canvas.style.width = '{self.config.width}px';
            canvas.style.height = '{self.config.height}px';
            ctx.scale(dpr, dpr);

            const width = {self.config.width};
            const height = {self.config.height};
            const padding = {{ top: 20, right: 80, bottom: 40, left: 60 }};
            const chartWidth = width - padding.left - padding.right;
            const chartHeight = height - padding.top - padding.bottom;

            const allValues = [...data.historical.y];
            data.paths.forEach(p => allValues.push(...p.values));
            if (data.weighted_forecast) allValues.push(...data.weighted_forecast);
            Object.values(data.percentiles).forEach(p => allValues.push(...p));

            const yMin = Math.min(...allValues) * 0.98;
            const yMax = Math.max(...allValues) * 1.02;
            const xMin = 0;
            const xMax = data.forecast_x[data.forecast_x.length - 1];

            const scaleX = (x) => padding.left + (x - xMin) / (xMax - xMin) * chartWidth;
            const scaleY = (y) => padding.top + chartHeight - (y - yMin) / (yMax - yMin) * chartHeight;

            ctx.fillStyle = '{bg_color}';
            ctx.fillRect(0, 0, width, height);

            // Grid
            ctx.strokeStyle = '{grid_color}';
            ctx.lineWidth = 1;
            for (let i = 0; i <= 6; i++) {{
                const y = padding.top + (chartHeight / 6) * i;
                ctx.beginPath();
                ctx.moveTo(padding.left, y);
                ctx.lineTo(width - padding.right, y);
                ctx.stroke();
            }}

            // Paths
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

            // Percentiles
            const pStyles = {{
                5: {{ color: 'rgba(100, 100, 255, 0.8)', width: 1, dash: [4, 4] }},
                50: {{ color: 'rgba(255, 100, 100, 1.0)', width: 3, dash: [] }},
                95: {{ color: 'rgba(100, 100, 255, 0.8)', width: 1, dash: [4, 4] }}
            }};

            Object.entries(data.percentiles).forEach(([p, values]) => {{
                const style = pStyles[p];
                if (!style) return;
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

            // Historical
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

            // Colorbar
            const colorbar = document.getElementById('colorbar-{chart_id}');
            if (colorbar && data.colorscale) {{
                const stops = data.colorscale.map(s => `rgb(${{s[1][0]}}, ${{s[1][1]}}, ${{s[1][2]}}) ${{s[0] * 100}}%`);
                colorbar.style.background = `linear-gradient(to right, ${{stops.join(', ')}})`;
            }}
        }})();
        </script>
        """
