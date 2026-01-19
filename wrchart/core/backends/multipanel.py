"""
Multi-panel backend for grid layouts with multiple charts.

Provides subplot-style visualization with different chart types
arranged in a configurable grid.
"""

from typing import Any, Dict, List, Optional, Tuple
import json

import polars as pl

from wrchart.core.backends.base import Backend, BackendType, RenderConfig


class MultiPanelBackend(Backend):
    """
    Multi-panel grid layout backend.

    Best for:
    - Dashboard layouts
    - Comparative analysis
    - Multiple related charts
    """

    def __init__(
        self,
        config: Optional[RenderConfig] = None,
        rows: int = 2,
        cols: int = 2,
    ):
        super().__init__(config)
        self.rows = rows
        self.cols = cols
        self._panels: List[Dict[str, Any]] = []
        self._row_heights: List[float] = [1 / rows] * rows
        self._col_widths: List[float] = [1 / cols] * cols
        self._h_spacing: float = 0.08
        self._v_spacing: float = 0.10

    @property
    def backend_type(self) -> BackendType:
        return BackendType.MULTIPANEL

    def set_grid(
        self,
        rows: int = None,
        cols: int = None,
        row_heights: List[float] = None,
        col_widths: List[float] = None,
    ) -> "MultiPanelBackend":
        """Configure grid layout."""
        if rows is not None:
            self.rows = rows
            self._row_heights = [1 / rows] * rows
        if cols is not None:
            self.cols = cols
            self._col_widths = [1 / cols] * cols
        if row_heights is not None:
            self._row_heights = row_heights
        if col_widths is not None:
            self._col_widths = col_widths
        return self

    def add_panel(
        self,
        data: pl.DataFrame,
        panel_type: str,
        row: int,
        col: int,
        title: Optional[str] = None,
        time_col: str = "time",
        value_col: str = "value",
        **options,
    ) -> "MultiPanelBackend":
        """
        Add a panel to the grid.

        Args:
            data: Panel data
            panel_type: Type of panel (line, bar, area, heatmap)
            row: Row position (0-indexed)
            col: Column position (0-indexed)
            title: Panel title
            time_col: Time column name
            value_col: Value column name
            **options: Additional options

        Returns:
            Self for chaining
        """
        self._panels.append({
            "data": data,
            "type": panel_type,
            "row": row,
            "col": col,
            "title": title,
            "time_col": time_col,
            "value_col": value_col,
            "options": options,
        })
        return self

    def add_series(
        self,
        data: pl.DataFrame,
        series_type: str,
        time_col: str,
        value_col: Optional[str] = None,
        **options,
    ) -> "MultiPanelBackend":
        """Add a panel using series-style API. Places in next available slot."""
        n_panels = len(self._panels)
        row = n_panels // self.cols
        col = n_panels % self.cols
        return self.add_panel(
            data=data,
            panel_type=series_type,
            row=row,
            col=col,
            time_col=time_col,
            value_col=value_col or "value",
            **options,
        )

    def _compute_panel_bounds(
        self, row: int, col: int
    ) -> Tuple[int, int, int, int]:
        """Compute pixel bounds for a panel."""
        title_height = 40 if self.config.title else 0
        available_width = self.config.width
        available_height = self.config.height - title_height

        h_space = self._h_spacing * available_width / (self.cols + 1)
        v_space = self._v_spacing * available_height / (self.rows + 1)

        usable_width = available_width - h_space * (self.cols + 1)
        usable_height = available_height - v_space * (self.rows + 1)

        x = h_space
        for c in range(col):
            x += self._col_widths[c] * usable_width + h_space

        y = title_height + v_space
        for r in range(row):
            y += self._row_heights[r] * usable_height + v_space

        panel_width = self._col_widths[col] * usable_width
        panel_height = self._row_heights[row] * usable_height

        return int(x), int(y), int(panel_width), int(panel_height)

    def to_json(self) -> str:
        """Generate JSON configuration."""
        panels_data = []
        for panel in self._panels:
            x, y, w, h = self._compute_panel_bounds(panel["row"], panel["col"])
            data = panel["data"]
            panels_data.append({
                "type": panel["type"],
                "title": panel["title"],
                "x": x,
                "y": y,
                "width": w,
                "height": h,
                "data": {
                    "x": data[panel["time_col"]].to_list(),
                    "y": data[panel["value_col"]].to_list(),
                },
            })

        return json.dumps({
            "id": self.config.chart_id,
            "width": self.config.width,
            "height": self.config.height,
            "title": self.config.title,
            "panels": panels_data,
        })

    def to_html(self) -> str:
        """Generate HTML for multi-panel rendering."""
        theme = self.config.theme
        chart_id = self.config.chart_id

        is_dark = theme.colors.background.lower() in ["#000000", "#0a0a0a", "#1a1a1e"]
        bg_color = "rgb(20, 20, 30)" if is_dark else "#fafafa"
        text_color = "white" if is_dark else "#333333"
        grid_color = "rgba(128, 128, 128, 0.2)" if is_dark else "rgba(128, 128, 128, 0.3)"
        line_color = theme.colors.line_primary

        # Generate panel rendering code
        panel_code = []
        for i, panel in enumerate(self._panels):
            x, y, w, h = self._compute_panel_bounds(panel["row"], panel["col"])
            data = panel["data"]
            x_data = data[panel["time_col"]].to_list()
            y_data = data[panel["value_col"]].to_list()

            panel_code.append(self._generate_panel_js(
                panel_id=f"panel_{i}",
                panel_type=panel["type"],
                title=panel["title"],
                x=x, y=y, w=w, h=h,
                x_data=x_data,
                y_data=y_data,
                text_color=text_color,
                grid_color=grid_color,
                line_color=line_color,
            ))

        panels_js = "\n".join(panel_code)

        return f"""
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&display=swap');
            #multipanel-container-{chart_id} {{
                font-family: 'Space Grotesk', -apple-system, BlinkMacSystemFont, sans-serif;
                background: {bg_color};
            }}
            #multipanel-title-{chart_id} {{
                font-size: 18px;
                font-weight: 600;
                color: {text_color};
                padding: 12px 16px;
            }}
            #multipanel-canvas-{chart_id} {{ display: block; }}
        </style>

        <div id="multipanel-container-{chart_id}">
            {"<div id='multipanel-title-" + chart_id + "'>" + self.config.title + "</div>" if self.config.title else ""}
            <canvas id="multipanel-canvas-{chart_id}" width="{self.config.width}" height="{self.config.height}"></canvas>
        </div>

        <script>
        (function() {{
            const canvas = document.getElementById('multipanel-canvas-{chart_id}');
            const ctx = canvas.getContext('2d');

            const dpr = window.devicePixelRatio || 1;
            canvas.width = {self.config.width} * dpr;
            canvas.height = {self.config.height} * dpr;
            canvas.style.width = '{self.config.width}px';
            canvas.style.height = '{self.config.height}px';
            ctx.scale(dpr, dpr);

            ctx.fillStyle = '{bg_color}';
            ctx.fillRect(0, 0, {self.config.width}, {self.config.height});

            {panels_js}
        }})();
        </script>
        """

    def _generate_panel_js(
        self,
        panel_id: str,
        panel_type: str,
        title: Optional[str],
        x: int, y: int, w: int, h: int,
        x_data: List,
        y_data: List,
        text_color: str,
        grid_color: str,
        line_color: str,
    ) -> str:
        """Generate JavaScript for a single panel."""
        x_json = json.dumps(x_data)
        y_json = json.dumps(y_data)

        return f"""
            (function() {{
                const px = {x}, py = {y}, pw = {w}, ph = {h};
                const padding = {{ top: 30, right: 10, bottom: 30, left: 50 }};
                const chartX = px + padding.left;
                const chartY = py + padding.top;
                const chartW = pw - padding.left - padding.right;
                const chartH = ph - padding.top - padding.bottom;

                const xData = {x_json};
                const yData = {y_json};

                const yMin = Math.min(...yData);
                const yMax = Math.max(...yData);
                const yRange = yMax - yMin || 1;

                // Panel border
                ctx.strokeStyle = '{grid_color}';
                ctx.lineWidth = 1;
                ctx.strokeRect(px, py, pw, ph);

                // Title
                if ('{title}') {{
                    ctx.fillStyle = '{text_color}';
                    ctx.font = '12px Space Grotesk, sans-serif';
                    ctx.textAlign = 'left';
                    ctx.fillText('{title}', px + 10, py + 18);
                }}

                // Grid
                for (let i = 0; i <= 4; i++) {{
                    const gy = chartY + (chartH / 4) * i;
                    ctx.beginPath();
                    ctx.strokeStyle = '{grid_color}';
                    ctx.moveTo(chartX, gy);
                    ctx.lineTo(chartX + chartW, gy);
                    ctx.stroke();
                }}

                // Data
                ctx.beginPath();
                ctx.strokeStyle = '{line_color}';
                ctx.lineWidth = 2;

                for (let i = 0; i < xData.length; i++) {{
                    const dx = chartX + (i / (xData.length - 1)) * chartW;
                    const dy = chartY + chartH - ((yData[i] - yMin) / yRange) * chartH;
                    if (i === 0) ctx.moveTo(dx, dy);
                    else ctx.lineTo(dx, dy);
                }}
                ctx.stroke();

                // Y-axis labels
                ctx.fillStyle = '{text_color}';
                ctx.font = '10px JetBrains Mono, monospace';
                ctx.textAlign = 'right';
                for (let i = 0; i <= 4; i++) {{
                    const val = yMax - (yRange / 4) * i;
                    const ly = chartY + (chartH / 4) * i + 4;
                    ctx.fillText(val.toFixed(2), chartX - 5, ly);
                }}
            }})();
        """
