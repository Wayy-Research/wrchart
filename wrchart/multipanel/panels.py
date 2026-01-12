"""
Panel types for MultiPanelChart.

Each panel type handles rendering of a specific chart type within the
multi-panel layout.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Union
import json

import numpy as np
import polars as pl


@dataclass
class Panel(ABC):
    """Base class for all panel types."""

    title: str = ""
    row: int = 0
    col: int = 0
    rowspan: int = 1
    colspan: int = 1

    @abstractmethod
    def render_js(self, panel_id: str, x: int, y: int, width: int, height: int) -> str:
        """
        Generate JavaScript code to render this panel.

        Args:
            panel_id: Unique identifier for this panel
            x: X position in pixels
            y: Y position in pixels
            width: Panel width in pixels
            height: Panel height in pixels

        Returns:
            JavaScript code string
        """
        pass

    def _draw_title(self, panel_id: str, x: int, y: int) -> str:
        """Generate JS to draw panel title."""
        if not self.title:
            return ""
        return f"""
            ctx.fillStyle = textColor;
            ctx.font = '12px Space Grotesk, sans-serif';
            ctx.textAlign = 'left';
            ctx.fillText('{self.title}', {x + 8}, {y + 16});
        """


@dataclass
class LinePanel(Panel):
    """Panel for line chart visualization."""

    x_data: Optional[List] = None
    y_data: Optional[List] = None  # Can be list of lists for multiple lines
    colors: Optional[List[str]] = None
    line_widths: Optional[List[float]] = None
    labels: Optional[List[str]] = None
    show_zero_line: bool = False
    y_label: str = ""
    x_label: str = ""

    def render_js(self, panel_id: str, x: int, y: int, width: int, height: int) -> str:
        if self.x_data is None or self.y_data is None:
            return ""

        # Normalize y_data to list of lists
        y_series = self.y_data if isinstance(self.y_data[0], list) else [self.y_data]
        n_series = len(y_series)

        colors = self.colors or [f"hsl({i * 360 // n_series}, 70%, 50%)" for i in range(n_series)]
        widths = self.line_widths or [2] * n_series

        # Compute ranges
        all_y = [v for series in y_series for v in series if v is not None]
        y_min = min(all_y) if all_y else 0
        y_max = max(all_y) if all_y else 1
        if y_min == y_max:
            y_min -= 1
            y_max += 1

        x_min = min(self.x_data)
        x_max = max(self.x_data)
        if x_min == x_max:
            x_min -= 1
            x_max += 1

        # Padding
        pad_top = 30 if self.title else 10
        pad_bottom = 30
        pad_left = 50
        pad_right = 10
        chart_width = width - pad_left - pad_right
        chart_height = height - pad_top - pad_bottom

        x_data_json = json.dumps(self.x_data)
        y_series_json = json.dumps(y_series)
        colors_json = json.dumps(colors)
        widths_json = json.dumps(widths)

        return f"""
            (function() {{
                const panelX = {x};
                const panelY = {y};
                const panelW = {width};
                const panelH = {height};
                const padTop = {pad_top};
                const padBottom = {pad_bottom};
                const padLeft = {pad_left};
                const padRight = {pad_right};
                const chartW = {chart_width};
                const chartH = {chart_height};

                const xData = {x_data_json};
                const ySeries = {y_series_json};
                const colors = {colors_json};
                const widths = {widths_json};

                const xMin = {x_min};
                const xMax = {x_max};
                const yMin = {y_min};
                const yMax = {y_max};

                const scaleX = (v) => panelX + padLeft + (v - xMin) / (xMax - xMin) * chartW;
                const scaleY = (v) => panelY + padTop + chartH - (v - yMin) / (yMax - yMin) * chartH;

                // Draw panel background
                ctx.fillStyle = bgColor;
                ctx.fillRect(panelX, panelY, panelW, panelH);

                // Draw title
                {self._draw_title(panel_id, x, y)}

                // Draw grid
                ctx.strokeStyle = gridColor;
                ctx.lineWidth = 0.5;
                for (let i = 0; i <= 4; i++) {{
                    const gy = panelY + padTop + (chartH / 4) * i;
                    ctx.beginPath();
                    ctx.moveTo(panelX + padLeft, gy);
                    ctx.lineTo(panelX + panelW - padRight, gy);
                    ctx.stroke();
                }}

                // Draw y-axis labels
                ctx.fillStyle = textColor;
                ctx.font = '10px Space Grotesk, sans-serif';
                ctx.textAlign = 'right';
                for (let i = 0; i <= 4; i++) {{
                    const gy = panelY + padTop + (chartH / 4) * i;
                    const val = yMax - (yMax - yMin) * (i / 4);
                    ctx.fillText(val.toFixed(2), panelX + padLeft - 5, gy + 3);
                }}

                // Draw zero line if requested
                {"if (yMin < 0 && yMax > 0) { const zy = scaleY(0); ctx.strokeStyle = 'rgba(128,128,128,0.5)'; ctx.lineWidth = 1; ctx.beginPath(); ctx.moveTo(panelX + padLeft, zy); ctx.lineTo(panelX + panelW - padRight, zy); ctx.stroke(); }" if self.show_zero_line else ""}

                // Draw lines
                ySeries.forEach((yData, seriesIdx) => {{
                    ctx.beginPath();
                    ctx.strokeStyle = colors[seriesIdx];
                    ctx.lineWidth = widths[seriesIdx];

                    let started = false;
                    for (let i = 0; i < xData.length; i++) {{
                        if (yData[i] === null) continue;
                        const px = scaleX(xData[i]);
                        const py = scaleY(yData[i]);
                        if (!started) {{
                            ctx.moveTo(px, py);
                            started = true;
                        }} else {{
                            ctx.lineTo(px, py);
                        }}
                    }}
                    ctx.stroke();
                }});

                // Draw y-axis label
                if ('{self.y_label}') {{
                    ctx.save();
                    ctx.translate(panelX + 12, panelY + panelH / 2);
                    ctx.rotate(-Math.PI / 2);
                    ctx.textAlign = 'center';
                    ctx.fillText('{self.y_label}', 0, 0);
                    ctx.restore();
                }}
            }})();
        """


@dataclass
class BarPanel(Panel):
    """Panel for bar chart visualization."""

    categories: Optional[List[str]] = None
    values: Optional[List] = None  # Can be list of lists for grouped bars
    colors: Optional[List[str]] = None
    labels: Optional[List[str]] = None
    orientation: str = "vertical"  # "vertical" or "horizontal"
    show_values: bool = True

    def render_js(self, panel_id: str, x: int, y: int, width: int, height: int) -> str:
        if self.categories is None or self.values is None:
            return ""

        # Normalize values to list of lists
        value_groups = self.values if isinstance(self.values[0], list) else [self.values]
        n_groups = len(value_groups)
        n_categories = len(self.categories)

        colors = self.colors or [f"hsl({i * 360 // n_groups}, 70%, 50%)" for i in range(n_groups)]

        all_vals = [v for group in value_groups for v in group if v is not None]
        v_min = min(0, min(all_vals)) if all_vals else 0
        v_max = max(all_vals) if all_vals else 1
        if v_min == v_max:
            v_max += 1

        pad_top = 30 if self.title else 10
        pad_bottom = 40
        pad_left = 60
        pad_right = 10
        chart_width = width - pad_left - pad_right
        chart_height = height - pad_top - pad_bottom

        categories_json = json.dumps(self.categories)
        value_groups_json = json.dumps(value_groups)
        colors_json = json.dumps(colors)
        labels_json = json.dumps(self.labels or [])

        return f"""
            (function() {{
                const panelX = {x};
                const panelY = {y};
                const panelW = {width};
                const panelH = {height};
                const padTop = {pad_top};
                const padBottom = {pad_bottom};
                const padLeft = {pad_left};
                const padRight = {pad_right};
                const chartW = {chart_width};
                const chartH = {chart_height};

                const categories = {categories_json};
                const valueGroups = {value_groups_json};
                const colors = {colors_json};
                const labels = {labels_json};
                const nGroups = {n_groups};
                const nCats = {n_categories};
                const vMin = {v_min};
                const vMax = {v_max};

                const scaleV = (v) => (v - vMin) / (vMax - vMin) * chartH;

                // Draw panel background
                ctx.fillStyle = bgColor;
                ctx.fillRect(panelX, panelY, panelW, panelH);

                // Draw title
                {self._draw_title(panel_id, x, y)}

                // Draw bars
                const groupWidth = chartW / nCats;
                const barWidth = (groupWidth * 0.8) / nGroups;
                const groupPad = groupWidth * 0.1;

                for (let catIdx = 0; catIdx < nCats; catIdx++) {{
                    for (let grpIdx = 0; grpIdx < nGroups; grpIdx++) {{
                        const val = valueGroups[grpIdx][catIdx];
                        if (val === null) continue;

                        const barX = panelX + padLeft + catIdx * groupWidth + groupPad + grpIdx * barWidth;
                        const barH = scaleV(val);
                        const barY = panelY + padTop + chartH - barH;

                        ctx.fillStyle = colors[grpIdx];
                        ctx.fillRect(barX, barY, barWidth - 2, barH);

                        // Value label
                        {"if (" + str(self.show_values).lower() + ") { ctx.fillStyle = textColor; ctx.font = '9px Space Grotesk'; ctx.textAlign = 'center'; ctx.fillText(val.toFixed(2), barX + barWidth/2 - 1, barY - 4); }"}
                    }}
                }}

                // Draw category labels
                ctx.fillStyle = textColor;
                ctx.font = '10px Space Grotesk, sans-serif';
                ctx.textAlign = 'center';
                for (let i = 0; i < nCats; i++) {{
                    const labelX = panelX + padLeft + i * groupWidth + groupWidth / 2;
                    ctx.fillText(categories[i], labelX, panelY + padTop + chartH + 15);
                }}

                // Draw y-axis labels
                ctx.textAlign = 'right';
                for (let i = 0; i <= 4; i++) {{
                    const gy = panelY + padTop + (chartH / 4) * i;
                    const val = vMax - (vMax - vMin) * (i / 4);
                    ctx.fillText(val.toFixed(2), panelX + padLeft - 5, gy + 3);
                }}

                // Draw legend if labels provided
                if (labels.length > 0 && nGroups > 1) {{
                    ctx.font = '9px Space Grotesk';
                    ctx.textAlign = 'left';
                    let legendX = panelX + padLeft;
                    for (let i = 0; i < labels.length; i++) {{
                        ctx.fillStyle = colors[i];
                        ctx.fillRect(legendX, panelY + padTop + chartH + 25, 12, 8);
                        ctx.fillStyle = textColor;
                        ctx.fillText(labels[i], legendX + 16, panelY + padTop + chartH + 33);
                        legendX += ctx.measureText(labels[i]).width + 30;
                    }}
                }}
            }})();
        """


@dataclass
class HeatmapPanel(Panel):
    """Panel for heatmap visualization."""

    data: Optional[List[List[float]]] = None
    x_labels: Optional[List[str]] = None
    y_labels: Optional[List[str]] = None
    colorscale: str = "viridis"
    show_values: bool = True
    v_min: Optional[float] = None
    v_max: Optional[float] = None

    def render_js(self, panel_id: str, x: int, y: int, width: int, height: int) -> str:
        if self.data is None:
            return ""

        n_rows = len(self.data)
        n_cols = len(self.data[0]) if n_rows > 0 else 0

        all_vals = [v for row in self.data for v in row if v is not None]
        v_min = self.v_min if self.v_min is not None else (min(all_vals) if all_vals else 0)
        v_max = self.v_max if self.v_max is not None else (max(all_vals) if all_vals else 1)

        pad_top = 30 if self.title else 10
        pad_bottom = 30
        pad_left = 60
        pad_right = 60  # Room for colorbar
        chart_width = width - pad_left - pad_right
        chart_height = height - pad_top - pad_bottom

        data_json = json.dumps(self.data)
        x_labels_json = json.dumps(self.x_labels or [])
        y_labels_json = json.dumps(self.y_labels or [])

        # Colorscale
        colorscale_stops = {
            "viridis": [[0, [68, 1, 84]], [0.25, [59, 82, 139]], [0.5, [33, 145, 140]], [0.75, [94, 201, 98]], [1, [253, 231, 37]]],
            "plasma": [[0, [13, 8, 135]], [0.25, [126, 3, 168]], [0.5, [204, 71, 120]], [0.75, [248, 149, 64]], [1, [240, 249, 33]]],
            "hot": [[0, [10, 10, 40]], [0.5, [200, 50, 50]], [1, [255, 255, 200]]],
        }
        stops = colorscale_stops.get(self.colorscale, colorscale_stops["viridis"])
        stops_json = json.dumps(stops)

        return f"""
            (function() {{
                const panelX = {x};
                const panelY = {y};
                const panelW = {width};
                const panelH = {height};
                const padTop = {pad_top};
                const padBottom = {pad_bottom};
                const padLeft = {pad_left};
                const padRight = {pad_right};
                const chartW = {chart_width};
                const chartH = {chart_height};

                const data = {data_json};
                const xLabels = {x_labels_json};
                const yLabels = {y_labels_json};
                const nRows = {n_rows};
                const nCols = {n_cols};
                const vMin = {v_min};
                const vMax = {v_max};
                const stops = {stops_json};

                // Color interpolation function
                const valueToColor = (v) => {{
                    const t = Math.max(0, Math.min(1, (v - vMin) / (vMax - vMin)));
                    for (let i = 0; i < stops.length - 1; i++) {{
                        if (t >= stops[i][0] && t <= stops[i + 1][0]) {{
                            const localT = (t - stops[i][0]) / (stops[i + 1][0] - stops[i][0]);
                            const c0 = stops[i][1];
                            const c1 = stops[i + 1][1];
                            const r = Math.round(c0[0] + localT * (c1[0] - c0[0]));
                            const g = Math.round(c0[1] + localT * (c1[1] - c0[1]));
                            const b = Math.round(c0[2] + localT * (c1[2] - c0[2]));
                            return `rgb(${{r}},${{g}},${{b}})`;
                        }}
                    }}
                    const last = stops[stops.length - 1][1];
                    return `rgb(${{last[0]}},${{last[1]}},${{last[2]}})`;
                }};

                // Draw panel background
                ctx.fillStyle = bgColor;
                ctx.fillRect(panelX, panelY, panelW, panelH);

                // Draw title
                {self._draw_title(panel_id, x, y)}

                // Draw cells
                const cellW = chartW / nCols;
                const cellH = chartH / nRows;

                for (let row = 0; row < nRows; row++) {{
                    for (let col = 0; col < nCols; col++) {{
                        const val = data[row][col];
                        if (val === null) continue;

                        const cx = panelX + padLeft + col * cellW;
                        const cy = panelY + padTop + row * cellH;

                        ctx.fillStyle = valueToColor(val);
                        ctx.fillRect(cx, cy, cellW - 1, cellH - 1);

                        // Value text
                        {"if (" + str(self.show_values).lower() + " && cellW > 30 && cellH > 20) { ctx.fillStyle = val > (vMin + vMax) / 2 ? 'black' : 'white'; ctx.font = '9px Space Grotesk'; ctx.textAlign = 'center'; ctx.fillText(val.toFixed(2), cx + cellW/2, cy + cellH/2 + 3); }"}
                    }}
                }}

                // Draw labels
                ctx.fillStyle = textColor;
                ctx.font = '10px Space Grotesk';

                // X labels
                ctx.textAlign = 'center';
                for (let i = 0; i < xLabels.length; i++) {{
                    const lx = panelX + padLeft + i * cellW + cellW / 2;
                    ctx.fillText(xLabels[i], lx, panelY + padTop + chartH + 15);
                }}

                // Y labels
                ctx.textAlign = 'right';
                for (let i = 0; i < yLabels.length; i++) {{
                    const ly = panelY + padTop + i * cellH + cellH / 2 + 3;
                    ctx.fillText(yLabels[i], panelX + padLeft - 5, ly);
                }}

                // Draw colorbar
                const cbX = panelX + padLeft + chartW + 10;
                const cbW = 15;
                const cbH = chartH;
                for (let i = 0; i < cbH; i++) {{
                    const t = 1 - i / cbH;
                    const v = vMin + t * (vMax - vMin);
                    ctx.fillStyle = valueToColor(v);
                    ctx.fillRect(cbX, panelY + padTop + i, cbW, 1);
                }}

                // Colorbar labels
                ctx.textAlign = 'left';
                ctx.fillStyle = textColor;
                ctx.fillText(vMax.toFixed(2), cbX + cbW + 5, panelY + padTop + 8);
                ctx.fillText(vMin.toFixed(2), cbX + cbW + 5, panelY + padTop + cbH);
            }})();
        """


@dataclass
class GaugePanel(Panel):
    """Panel for gauge indicator visualization."""

    value: float = 0
    min_value: float = 0
    max_value: float = 100
    thresholds: Optional[List[Tuple[float, str]]] = None  # [(value, color), ...]
    label: str = ""
    unit: str = ""

    def render_js(self, panel_id: str, x: int, y: int, width: int, height: int) -> str:
        thresholds = self.thresholds or [
            (self.max_value * 0.33, "#4CAF50"),  # Green
            (self.max_value * 0.66, "#FFC107"),  # Yellow
            (self.max_value, "#F44336"),  # Red
        ]

        thresholds_json = json.dumps(thresholds)
        center_x = x + width // 2
        center_y = y + height // 2 + 20
        radius = min(width, height) * 0.35

        return f"""
            (function() {{
                const panelX = {x};
                const panelY = {y};
                const panelW = {width};
                const panelH = {height};
                const centerX = {center_x};
                const centerY = {center_y};
                const radius = {radius};
                const value = {self.value};
                const minVal = {self.min_value};
                const maxVal = {self.max_value};
                const thresholds = {thresholds_json};

                // Draw panel background
                ctx.fillStyle = bgColor;
                ctx.fillRect(panelX, panelY, panelW, panelH);

                // Draw title
                {self._draw_title(panel_id, x, y)}

                // Draw gauge arcs
                const startAngle = Math.PI * 0.75;
                const endAngle = Math.PI * 2.25;
                const angleRange = endAngle - startAngle;

                let prevAngle = startAngle;
                thresholds.forEach(([thresh, color], i) => {{
                    const nextAngle = startAngle + (thresh - minVal) / (maxVal - minVal) * angleRange;
                    ctx.beginPath();
                    ctx.arc(centerX, centerY, radius, prevAngle, Math.min(nextAngle, endAngle));
                    ctx.strokeStyle = color;
                    ctx.lineWidth = 20;
                    ctx.stroke();
                    prevAngle = nextAngle;
                }});

                // Draw needle
                const valueAngle = startAngle + (value - minVal) / (maxVal - minVal) * angleRange;
                ctx.save();
                ctx.translate(centerX, centerY);
                ctx.rotate(valueAngle);

                ctx.beginPath();
                ctx.moveTo(0, 0);
                ctx.lineTo(radius - 25, 0);
                ctx.strokeStyle = textColor;
                ctx.lineWidth = 3;
                ctx.stroke();

                // Needle point
                ctx.beginPath();
                ctx.arc(radius - 25, 0, 5, 0, Math.PI * 2);
                ctx.fillStyle = textColor;
                ctx.fill();

                ctx.restore();

                // Center circle
                ctx.beginPath();
                ctx.arc(centerX, centerY, 8, 0, Math.PI * 2);
                ctx.fillStyle = textColor;
                ctx.fill();

                // Value text
                ctx.fillStyle = textColor;
                ctx.font = 'bold 24px Space Grotesk';
                ctx.textAlign = 'center';
                ctx.fillText(value.toFixed(1) + '{self.unit}', centerX, centerY + radius + 30);

                // Label
                if ('{self.label}') {{
                    ctx.font = '12px Space Grotesk';
                    ctx.fillText('{self.label}', centerX, centerY + radius + 50);
                }}

                // Min/max labels
                ctx.font = '10px Space Grotesk';
                ctx.textAlign = 'right';
                ctx.fillText(minVal.toString(), centerX - radius + 10, centerY + 30);
                ctx.textAlign = 'left';
                ctx.fillText(maxVal.toString(), centerX + radius - 10, centerY + 30);
            }})();
        """


@dataclass
class AreaPanel(Panel):
    """Panel for area chart visualization with fill."""

    x_data: Optional[List] = None
    y_data: Optional[List] = None
    color: str = "rgba(255, 0, 0, 0.5)"
    line_color: str = "red"
    baseline: float = 0
    show_baseline: bool = True
    y_label: str = ""

    def render_js(self, panel_id: str, x: int, y: int, width: int, height: int) -> str:
        if self.x_data is None or self.y_data is None:
            return ""

        y_min = min(self.baseline, min(self.y_data))
        y_max = max(self.y_data)
        if y_min == y_max:
            y_max += 1

        x_min = min(self.x_data)
        x_max = max(self.x_data)
        if x_min == x_max:
            x_max += 1

        pad_top = 30 if self.title else 10
        pad_bottom = 30
        pad_left = 50
        pad_right = 10
        chart_width = width - pad_left - pad_right
        chart_height = height - pad_top - pad_bottom

        x_data_json = json.dumps(self.x_data)
        y_data_json = json.dumps(self.y_data)

        return f"""
            (function() {{
                const panelX = {x};
                const panelY = {y};
                const panelW = {width};
                const panelH = {height};
                const padTop = {pad_top};
                const padBottom = {pad_bottom};
                const padLeft = {pad_left};
                const padRight = {pad_right};
                const chartW = {chart_width};
                const chartH = {chart_height};

                const xData = {x_data_json};
                const yData = {y_data_json};
                const baseline = {self.baseline};

                const xMin = {x_min};
                const xMax = {x_max};
                const yMin = {y_min};
                const yMax = {y_max};

                const scaleX = (v) => panelX + padLeft + (v - xMin) / (xMax - xMin) * chartW;
                const scaleY = (v) => panelY + padTop + chartH - (v - yMin) / (yMax - yMin) * chartH;

                // Draw panel background
                ctx.fillStyle = bgColor;
                ctx.fillRect(panelX, panelY, panelW, panelH);

                // Draw title
                {self._draw_title(panel_id, x, y)}

                // Draw grid
                ctx.strokeStyle = gridColor;
                ctx.lineWidth = 0.5;
                for (let i = 0; i <= 4; i++) {{
                    const gy = panelY + padTop + (chartH / 4) * i;
                    ctx.beginPath();
                    ctx.moveTo(panelX + padLeft, gy);
                    ctx.lineTo(panelX + panelW - padRight, gy);
                    ctx.stroke();
                }}

                // Draw area fill
                ctx.beginPath();
                ctx.moveTo(scaleX(xData[0]), scaleY(baseline));
                for (let i = 0; i < xData.length; i++) {{
                    ctx.lineTo(scaleX(xData[i]), scaleY(yData[i]));
                }}
                ctx.lineTo(scaleX(xData[xData.length - 1]), scaleY(baseline));
                ctx.closePath();
                ctx.fillStyle = '{self.color}';
                ctx.fill();

                // Draw line
                ctx.beginPath();
                ctx.strokeStyle = '{self.line_color}';
                ctx.lineWidth = 2;
                for (let i = 0; i < xData.length; i++) {{
                    const px = scaleX(xData[i]);
                    const py = scaleY(yData[i]);
                    if (i === 0) ctx.moveTo(px, py);
                    else ctx.lineTo(px, py);
                }}
                ctx.stroke();

                // Draw baseline
                {"if (" + str(self.show_baseline).lower() + ") { const by = scaleY(baseline); ctx.strokeStyle = 'rgba(128,128,128,0.5)'; ctx.lineWidth = 1; ctx.setLineDash([4, 4]); ctx.beginPath(); ctx.moveTo(panelX + padLeft, by); ctx.lineTo(panelX + panelW - padRight, by); ctx.stroke(); ctx.setLineDash([]); }"}

                // Draw y-axis labels
                ctx.fillStyle = textColor;
                ctx.font = '10px Space Grotesk';
                ctx.textAlign = 'right';
                for (let i = 0; i <= 4; i++) {{
                    const gy = panelY + padTop + (chartH / 4) * i;
                    const val = yMax - (yMax - yMin) * (i / 4);
                    ctx.fillText(val.toFixed(2), panelX + padLeft - 5, gy + 3);
                }}
            }})();
        """
