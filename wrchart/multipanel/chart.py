"""
MultiPanelChart - Multi-panel visualization layouts.

Provides subplot-style charts with multiple panels arranged in a grid,
supporting different chart types in each panel.
"""

from typing import Any, Dict, List, Optional, Tuple, Union
import json
import uuid

from wrchart.multipanel.panels import Panel


class MultiPanelChart:
    """
    Multi-panel chart with subplot layout.

    Creates a grid of panels, each containing a different chart type.
    Useful for dashboards and comprehensive analysis visualizations.

    Example:
        >>> from wrchart.multipanel import MultiPanelChart, LinePanel, BarPanel
        >>>
        >>> chart = MultiPanelChart(
        ...     rows=2,
        ...     cols=2,
        ...     title="Analysis Dashboard"
        ... )
        >>>
        >>> chart.add_panel(LinePanel(
        ...     title="Price History",
        ...     x_data=dates,
        ...     y_data=prices,
        ...     row=0, col=0
        ... ))
        >>>
        >>> chart.add_panel(BarPanel(
        ...     title="Volume",
        ...     categories=["Q1", "Q2", "Q3", "Q4"],
        ...     values=[100, 150, 130, 180],
        ...     row=0, col=1
        ... ))
        >>>
        >>> chart.show()
    """

    def __init__(
        self,
        rows: int = 2,
        cols: int = 2,
        width: int = 1200,
        height: int = 800,
        title: Optional[str] = None,
        theme: str = "dark",
        row_heights: Optional[List[float]] = None,
        col_widths: Optional[List[float]] = None,
        horizontal_spacing: float = 0.08,
        vertical_spacing: float = 0.10,
    ):
        """
        Initialize a MultiPanelChart.

        Args:
            rows: Number of rows in the grid
            cols: Number of columns in the grid
            width: Total chart width in pixels
            height: Total chart height in pixels
            title: Optional main title
            theme: Color theme ('dark' or 'light')
            row_heights: Relative heights for each row (should sum to 1)
            col_widths: Relative widths for each column (should sum to 1)
            horizontal_spacing: Horizontal gap between panels (0-1)
            vertical_spacing: Vertical gap between panels (0-1)
        """
        self.rows = rows
        self.cols = cols
        self.width = width
        self.height = height
        self.title = title
        self.theme = theme
        self._id = str(uuid.uuid4())[:8]

        # Default equal sizes
        self.row_heights = row_heights or [1 / rows] * rows
        self.col_widths = col_widths or [1 / cols] * cols

        self.horizontal_spacing = horizontal_spacing
        self.vertical_spacing = vertical_spacing

        self._panels: List[Panel] = []

    def add_panel(self, panel: Panel) -> "MultiPanelChart":
        """
        Add a panel to the chart.

        Args:
            panel: Panel instance with row/col position set

        Returns:
            Self for chaining
        """
        self._panels.append(panel)
        return self

    def _compute_panel_bounds(
        self, row: int, col: int, rowspan: int = 1, colspan: int = 1
    ) -> Tuple[int, int, int, int]:
        """
        Compute pixel bounds for a panel.

        Returns:
            Tuple of (x, y, width, height)
        """
        # Account for main title
        title_height = 40 if self.title else 0

        # Available space
        available_width = self.width
        available_height = self.height - title_height

        # Spacing
        h_space = self.horizontal_spacing * available_width / (self.cols + 1)
        v_space = self.vertical_spacing * available_height / (self.rows + 1)

        # Usable space after spacing
        usable_width = available_width - h_space * (self.cols + 1)
        usable_height = available_height - v_space * (self.rows + 1)

        # Calculate position
        x = h_space
        for c in range(col):
            x += self.col_widths[c] * usable_width + h_space

        y = title_height + v_space
        for r in range(row):
            y += self.row_heights[r] * usable_height + v_space

        # Calculate size
        panel_width = 0
        for c in range(col, min(col + colspan, self.cols)):
            panel_width += self.col_widths[c] * usable_width
        panel_width += h_space * (colspan - 1)

        panel_height = 0
        for r in range(row, min(row + rowspan, self.rows)):
            panel_height += self.row_heights[r] * usable_height
        panel_height += v_space * (rowspan - 1)

        return int(x), int(y), int(panel_width), int(panel_height)

    def _generate_html(self) -> str:
        """Generate HTML/JS for rendering."""
        if self.theme == "dark":
            bg_color = "rgb(20, 20, 30)"
            text_color = "white"
            grid_color = "rgba(128, 128, 128, 0.2)"
        else:
            bg_color = "#fafafa"
            text_color = "#333333"
            grid_color = "rgba(128, 128, 128, 0.3)"

        # Generate panel rendering code
        panel_js = []
        for i, panel in enumerate(self._panels):
            x, y, w, h = self._compute_panel_bounds(
                panel.row, panel.col, panel.rowspan, panel.colspan
            )
            panel_id = f"panel_{i}"
            panel_js.append(panel.render_js(panel_id, x, y, w, h))

        panels_code = "\n".join(panel_js)

        html = f"""
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&display=swap');

            #multipanel-container-{self._id} {{
                font-family: 'Space Grotesk', -apple-system, BlinkMacSystemFont, sans-serif;
                background: {bg_color};
                padding: 0;
                border-radius: 0;
            }}
            #multipanel-title-{self._id} {{
                font-size: 18px;
                font-weight: 600;
                color: {text_color};
                padding: 12px 16px;
                letter-spacing: -0.02em;
            }}
            #multipanel-canvas-{self._id} {{
                display: block;
            }}
        </style>

        <div id="multipanel-container-{self._id}">
            {"<div id='multipanel-title-" + self._id + "'>" + self.title + "</div>" if self.title else ""}
            <canvas id="multipanel-canvas-{self._id}" width="{self.width}" height="{self.height}"></canvas>
        </div>

        <script>
        (function() {{
            const canvas = document.getElementById('multipanel-canvas-{self._id}');
            const ctx = canvas.getContext('2d');

            // High DPI support
            const dpr = window.devicePixelRatio || 1;
            canvas.width = {self.width} * dpr;
            canvas.height = {self.height} * dpr;
            canvas.style.width = '{self.width}px';
            canvas.style.height = '{self.height}px';
            ctx.scale(dpr, dpr);

            // Theme colors
            const bgColor = '{bg_color}';
            const textColor = '{text_color}';
            const gridColor = '{grid_color}';

            // Clear canvas
            ctx.fillStyle = bgColor;
            ctx.fillRect(0, 0, {self.width}, {self.height});

            // Render panels
            {panels_code}
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

        In Jupyter, renders inline. Outside Jupyter, opens in browser.
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
                <title>{self.title or 'Multi-Panel Chart'}</title>
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
        bg = "rgb(20, 20, 30)" if self.theme == "dark" else "#fafafa"

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>{self.title or 'Multi-Panel Chart'}</title>
        </head>
        <body style="margin: 0; padding: 20px; background: {bg};">
            {self._generate_html()}
        </body>
        </html>
        """

        with open(filepath, "w") as f:
            f.write(html_content)
