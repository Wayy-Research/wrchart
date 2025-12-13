"""
WebGL-accelerated chart for high-frequency data visualization.

Handles millions of data points with GPU acceleration, dynamic LOD,
and virtual viewport rendering.
"""

from typing import Optional, List, Tuple
import json
import uuid

import polars as pl

from wrchart.core.themes import Theme, WayyTheme
from wrchart.transforms.decimation import lttb_downsample


class WebGLChart:
    """
    GPU-accelerated chart for high-frequency tick data.

    Uses WebGL for rendering millions of data points at 60fps
    with dynamic Level of Detail (LOD) based on zoom level.

    Example:
        >>> import wrchart as wrc
        >>> import polars as pl
        >>>
        >>> # Create tick data (millions of points)
        >>> df = pl.DataFrame({
        ...     "time": range(1_000_000),
        ...     "price": [...],  # Your tick prices
        ... })
        >>>
        >>> # Create WebGL chart
        >>> chart = wrc.WebGLChart(width=800, height=400)
        >>> chart.add_line(df, time_col="time", value_col="price")
        >>> chart.show()
    """

    # LOD levels: (target_points, label)
    LOD_LEVELS = [
        (None, "Full"),      # LOD 0: Full resolution
        (100_000, "100K"),   # LOD 1
        (50_000, "50K"),     # LOD 2
        (20_000, "20K"),     # LOD 3
        (10_000, "10K"),     # LOD 4
        (5_000, "5K"),       # LOD 5
        (2_000, "2K"),       # LOD 6
    ]

    def __init__(
        self,
        width: int = 800,
        height: int = 400,
        theme: Optional[Theme] = None,
        title: Optional[str] = None,
    ):
        """
        Initialize a WebGL chart.

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

        self._data: Optional[pl.DataFrame] = None
        self._time_col: str = "time"
        self._value_col: str = "value"
        self._lod_data: List[List[Tuple[float, float]]] = []

    def add_line(
        self,
        data: pl.DataFrame,
        time_col: str = "time",
        value_col: str = "value",
    ) -> "WebGLChart":
        """
        Add line data to the chart.

        Args:
            data: Polars DataFrame with time and value columns
            time_col: Name of time column
            value_col: Name of value column

        Returns:
            Self for chaining
        """
        self._data = data
        self._time_col = time_col
        self._value_col = value_col
        self._precompute_lod()
        return self

    def _precompute_lod(self) -> None:
        """Pre-compute LOD levels using LTTB downsampling."""
        if self._data is None:
            return

        n_points = len(self._data)
        self._lod_data = []

        for target, label in self.LOD_LEVELS:
            if target is None or n_points <= target:
                # Full resolution
                lod_df = self._data
            else:
                # Downsample using LTTB
                lod_df = lttb_downsample(
                    self._data,
                    time_col=self._time_col,
                    value_col=self._value_col,
                    target_points=target,
                )

            # Normalize data to 0-1 range for WebGL
            times = lod_df[self._time_col].to_list()
            values = lod_df[self._value_col].to_list()

            if len(times) == 0:
                continue

            t_min, t_max = min(times), max(times)
            v_min, v_max = min(values), max(values)

            # Add padding to value range
            v_range = v_max - v_min
            v_min -= v_range * 0.05
            v_max += v_range * 0.05
            v_range = v_max - v_min

            t_range = t_max - t_min if t_max != t_min else 1

            normalized = [
                (
                    (t - t_min) / t_range,
                    (v - v_min) / v_range if v_range != 0 else 0.5
                )
                for t, v in zip(times, values)
            ]

            self._lod_data.append(normalized)

    def _generate_webgl_js(self) -> str:
        """Generate the WebGL JavaScript code."""
        # Convert LOD data to JavaScript arrays
        lod_arrays = []
        for lod_points in self._lod_data:
            flat_data = []
            for x, y in lod_points:
                flat_data.extend([x, y])
            lod_arrays.append(flat_data)

        lod_json = json.dumps(lod_arrays)
        total_points = len(self._data) if self._data is not None else 0

        colors = self.theme.colors

        return f"""
        (function() {{
            const canvas = document.getElementById('webgl-{self._id}');
            if (!canvas) return;

            const dpr = window.devicePixelRatio || 1;
            const rect = canvas.getBoundingClientRect();
            canvas.width = rect.width * dpr;
            canvas.height = rect.height * dpr;

            const gl = canvas.getContext('webgl', {{ antialias: true, alpha: false }});
            if (!gl) {{
                console.error('WebGL not supported');
                return;
            }}

            // Shaders
            const vsSource = `
                attribute vec2 aPosition;
                uniform vec2 uScale;
                uniform vec2 uOffset;
                void main() {{
                    vec2 pos = (aPosition + uOffset) * uScale;
                    gl_Position = vec4(pos * 2.0 - 1.0, 0.0, 1.0);
                }}
            `;

            const fsSource = `
                precision mediump float;
                uniform vec4 uColor;
                void main() {{
                    gl_FragColor = uColor;
                }}
            `;

            function compileShader(source, type) {{
                const shader = gl.createShader(type);
                gl.shaderSource(shader, source);
                gl.compileShader(shader);
                return shader;
            }}

            const vs = compileShader(vsSource, gl.VERTEX_SHADER);
            const fs = compileShader(fsSource, gl.FRAGMENT_SHADER);
            const program = gl.createProgram();
            gl.attachShader(program, vs);
            gl.attachShader(program, fs);
            gl.linkProgram(program);
            gl.useProgram(program);

            const aPosition = gl.getAttribLocation(program, 'aPosition');
            const uScale = gl.getUniformLocation(program, 'uScale');
            const uOffset = gl.getUniformLocation(program, 'uOffset');
            const uColor = gl.getUniformLocation(program, 'uColor');

            // Load LOD data
            const lodArrays = {lod_json};
            const lodLevels = lodArrays.map(arr => ({{
                data: new Float32Array(arr),
                points: arr.length / 2
            }}));

            // Create buffers
            const buffers = lodLevels.map(lod => {{
                const buffer = gl.createBuffer();
                gl.bindBuffer(gl.ARRAY_BUFFER, buffer);
                gl.bufferData(gl.ARRAY_BUFFER, lod.data, gl.STATIC_DRAW);
                return buffer;
            }});

            const visibleBuffer = gl.createBuffer();

            let viewX = 0, viewScale = 1;

            function selectLOD() {{
                if (viewScale > 50) return 0;
                if (viewScale > 20) return 1;
                if (viewScale > 10) return 2;
                if (viewScale > 5) return 3;
                if (viewScale > 2) return 4;
                if (viewScale > 1.2) return 5;
                return Math.min(6, lodLevels.length - 1);
            }}

            function getVisiblePoints(lodData, lodPoints, startX, endX) {{
                const padding = (endX - startX) * 0.1;
                const paddedStart = Math.max(0, startX - padding);
                const paddedEnd = Math.min(1, endX + padding);
                const startIdx = Math.max(0, Math.floor(paddedStart * lodPoints));
                const endIdx = Math.min(lodPoints - 1, Math.ceil(paddedEnd * lodPoints));
                const count = endIdx - startIdx + 1;
                if (count <= 0) return {{ data: null, count: 0 }};
                const sliceData = new Float32Array(count * 2);
                for (let i = 0; i < count; i++) {{
                    sliceData[i * 2] = lodData[(startIdx + i) * 2];
                    sliceData[i * 2 + 1] = lodData[(startIdx + i) * 2 + 1];
                }}
                return {{ data: sliceData, count: count }};
            }}

            let lastFrameTime = performance.now(), frameCount = 0, fps = 0;
            const statEl = document.getElementById('stat-{self._id}');

            function render() {{
                gl.viewport(0, 0, canvas.width, canvas.height);
                gl.clearColor({int(colors.background[1:3], 16)/255}, {int(colors.background[3:5], 16)/255}, {int(colors.background[5:7], 16)/255}, 1.0);
                gl.clear(gl.COLOR_BUFFER_BIT);

                const lodIndex = selectLOD();
                const lod = lodLevels[lodIndex];
                const visibleStart = Math.max(0, viewX);
                const visibleEnd = Math.min(1, viewX + 1 / viewScale);
                const visible = getVisiblePoints(lod.data, lod.points, visibleStart, visibleEnd);

                if (visible.data && visible.count > 1) {{
                    gl.bindBuffer(gl.ARRAY_BUFFER, visibleBuffer);
                    gl.bufferData(gl.ARRAY_BUFFER, visible.data, gl.DYNAMIC_DRAW);
                    gl.enableVertexAttribArray(aPosition);
                    gl.vertexAttribPointer(aPosition, 2, gl.FLOAT, false, 0, 0);
                    gl.uniform2f(uScale, viewScale, 1.0);
                    gl.uniform2f(uOffset, -viewX, 0.0);
                    gl.uniform4f(uColor, {int(colors.highlight[1:3], 16)/255}, {int(colors.highlight[3:5], 16)/255}, {int(colors.highlight[5:7], 16)/255}, 1.0);
                    gl.drawArrays(gl.LINE_STRIP, 0, visible.count);
                }}

                // Grid
                gl.uniform4f(uColor, 0.2, 0.2, 0.2, 1.0);
                [0.25, 0.5, 0.75].forEach(y => {{
                    const gridBuffer = gl.createBuffer();
                    gl.bindBuffer(gl.ARRAY_BUFFER, gridBuffer);
                    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([0, y, 1, y]), gl.DYNAMIC_DRAW);
                    gl.vertexAttribPointer(aPosition, 2, gl.FLOAT, false, 0, 0);
                    gl.drawArrays(gl.LINES, 0, 2);
                    gl.deleteBuffer(gridBuffer);
                }});

                frameCount++;
                const elapsed = performance.now() - lastFrameTime;
                if (elapsed >= 1000) {{
                    fps = Math.round(frameCount * 1000 / elapsed);
                    frameCount = 0;
                    lastFrameTime = performance.now();
                }}

                if (statEl) {{
                    statEl.textContent = 'LOD ' + lodIndex + ' | ' + visible.count + '/' + lod.points + ' pts | ' + fps + ' fps';
                }}

                requestAnimationFrame(render);
            }}

            // Mouse interaction
            let isDragging = false, lastMouseX = 0;
            canvas.addEventListener('mousedown', e => {{ isDragging = true; lastMouseX = e.clientX; canvas.style.cursor = 'grabbing'; }});
            canvas.addEventListener('mousemove', e => {{
                if (!isDragging) return;
                const dx = (e.clientX - lastMouseX) / rect.width;
                viewX -= dx / viewScale;
                viewX = Math.max(0, Math.min(1 - 1/viewScale, viewX));
                lastMouseX = e.clientX;
            }});
            canvas.addEventListener('mouseup', () => {{ isDragging = false; canvas.style.cursor = 'crosshair'; }});
            canvas.addEventListener('mouseleave', () => {{ isDragging = false; canvas.style.cursor = 'crosshair'; }});
            canvas.addEventListener('wheel', e => {{
                e.preventDefault();
                const zoomFactor = e.deltaY > 0 ? 0.9 : 1.1;
                const mouseX = e.offsetX / rect.width;
                const oldScale = viewScale;
                viewScale *= zoomFactor;
                viewScale = Math.max(1, Math.min(100, viewScale));
                const scaleRatio = viewScale / oldScale;
                viewX = mouseX - (mouseX - viewX) * scaleRatio;
                viewX = Math.max(0, Math.min(1 - 1/viewScale, viewX));
            }}, {{ passive: false }});

            render();
        }})();
        """

    def _generate_html(self) -> str:
        """Generate the complete HTML for the chart."""
        colors = self.theme.colors
        total_points = len(self._data) if self._data is not None else 0

        return f"""
        <style>
            #webgl-container-{self._id} {{
                font-family: 'Space Grotesk', -apple-system, BlinkMacSystemFont, sans-serif;
                background: {colors.background};
                padding: 16px;
            }}
            #webgl-title-{self._id} {{
                font-size: 14px;
                font-weight: 600;
                color: {colors.text_primary};
                margin-bottom: 8px;
            }}
            #webgl-{self._id} {{
                width: {self.width}px;
                height: {self.height}px;
                cursor: crosshair;
            }}
            #stat-{self._id} {{
                font-family: 'JetBrains Mono', monospace;
                font-size: 11px;
                color: {colors.text_secondary};
                margin-top: 8px;
            }}
            .webgl-stat-value {{ color: {colors.highlight}; }}
        </style>
        <div id="webgl-container-{self._id}">
            {"<div id='webgl-title-" + self._id + "'>" + (self.title or "WebGL Chart") + " (" + f"{total_points:,}" + " points)</div>" if self.title else f"<div id='webgl-title-{self._id}'>WebGL Chart ({total_points:,} points)</div>"}
            <canvas id="webgl-{self._id}"></canvas>
            <div id="stat-{self._id}">Loading...</div>
        </div>
        <script>
        {self._generate_webgl_js()}
        </script>
        """

    def _repr_html_(self) -> str:
        """Jupyter notebook HTML representation."""
        return self._generate_html()

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

            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>{self.title or 'WebGL Chart'}</title>
                <link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;600&family=JetBrains+Mono:wght@400&display=swap" rel="stylesheet">
            </head>
            <body style="margin: 0; padding: 20px; background: {self.theme.colors.background};">
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
        Save the chart to an HTML file.

        Args:
            filepath: Path to save the HTML file
        """
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>{self.title or 'WebGL Chart'}</title>
            <link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;600&family=JetBrains+Mono:wght@400&display=swap" rel="stylesheet">
        </head>
        <body style="margin: 0; padding: 20px; background: {self.theme.colors.background};">
            {self._generate_html()}
        </body>
        </html>
        """

        with open(filepath, "w") as f:
            f.write(html_content)
