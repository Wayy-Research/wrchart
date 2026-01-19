"""
WebGL backend for GPU-accelerated high-frequency data visualization.

Handles millions of data points with dynamic Level of Detail (LOD)
and efficient viewport culling.
"""

from typing import Any, Dict, List, Optional, Tuple
import json

import polars as pl

from wrchart.core.backends.base import Backend, BackendType, RenderConfig
from wrchart.transforms.decimation import lttb_downsample


class WebGLBackend(Backend):
    """
    GPU-accelerated backend using WebGL.

    Best for:
    - High-frequency tick data (100k+ points)
    - Real-time streaming data
    - Datasets with millions of points
    """

    # LOD levels: (target_points, label)
    LOD_LEVELS = [
        (None, "Full"),
        (100_000, "100K"),
        (50_000, "50K"),
        (20_000, "20K"),
        (10_000, "10K"),
        (5_000, "5K"),
        (2_000, "2K"),
    ]

    def __init__(self, config: Optional[RenderConfig] = None):
        super().__init__(config)
        self._data: Optional[pl.DataFrame] = None
        self._time_col: str = "time"
        self._value_col: str = "value"
        self._lod_data: List[List[Tuple[float, float]]] = []

    @property
    def backend_type(self) -> BackendType:
        return BackendType.WEBGL

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
    ) -> "WebGLBackend":
        """Add line data to the chart. WebGL backend only supports line series."""
        self._data = data
        self._time_col = time_col
        self._value_col = value_col or close_col or "value"
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
                lod_df = self._data
            else:
                lod_df = lttb_downsample(
                    self._data,
                    time_col=self._time_col,
                    value_col=self._value_col,
                    target_points=target,
                )

            times = lod_df[self._time_col].to_list()
            values = lod_df[self._value_col].to_list()

            if len(times) == 0:
                continue

            t_min, t_max = min(times), max(times)
            v_min, v_max = min(values), max(values)

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

    def to_json(self) -> str:
        """Generate JSON configuration."""
        lod_arrays = []
        for lod_points in self._lod_data:
            flat_data = []
            for x, y in lod_points:
                flat_data.extend([x, y])
            lod_arrays.append(flat_data)

        return json.dumps({
            "id": self.config.chart_id,
            "width": self.config.width,
            "height": self.config.height,
            "lod": lod_arrays,
            "total_points": len(self._data) if self._data else 0,
        })

    def to_html(self) -> str:
        """Generate HTML for WebGL rendering."""
        lod_arrays = []
        for lod_points in self._lod_data:
            flat_data = []
            for x, y in lod_points:
                flat_data.extend([x, y])
            lod_arrays.append(flat_data)

        lod_json = json.dumps(lod_arrays)
        total_points = len(self._data) if self._data is not None else 0
        colors = self.config.theme.colors
        chart_id = self.config.chart_id

        # Parse colors for WebGL
        def parse_hex(hex_color):
            return (
                int(hex_color[1:3], 16) / 255,
                int(hex_color[3:5], 16) / 255,
                int(hex_color[5:7], 16) / 255,
            )

        bg_r, bg_g, bg_b = parse_hex(colors.background)
        hl_r, hl_g, hl_b = parse_hex(colors.highlight)

        return f"""
        <style>
            #webgl-container-{chart_id} {{
                font-family: 'Space Grotesk', -apple-system, BlinkMacSystemFont, sans-serif;
                background: {colors.background};
                padding: 16px;
            }}
            #webgl-title-{chart_id} {{
                font-size: 14px;
                font-weight: 600;
                color: {colors.text_primary};
                margin-bottom: 8px;
            }}
            #webgl-{chart_id} {{
                width: {self.config.width}px;
                height: {self.config.height}px;
                cursor: crosshair;
            }}
            #stat-{chart_id} {{
                font-family: 'JetBrains Mono', monospace;
                font-size: 11px;
                color: {colors.text_secondary};
                margin-top: 8px;
            }}
        </style>
        <div id="webgl-container-{chart_id}">
            <div id="webgl-title-{chart_id}">{self.config.title or "WebGL Chart"} ({total_points:,} points)</div>
            <canvas id="webgl-{chart_id}"></canvas>
            <div id="stat-{chart_id}">Loading...</div>
        </div>
        <script>
        (function() {{
            const canvas = document.getElementById('webgl-{chart_id}');
            if (!canvas) return;

            const dpr = window.devicePixelRatio || 1;
            const rect = canvas.getBoundingClientRect();
            canvas.width = rect.width * dpr;
            canvas.height = rect.height * dpr;

            const gl = canvas.getContext('webgl', {{ antialias: true, alpha: false }});
            if (!gl) {{ console.error('WebGL not supported'); return; }}

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
                void main() {{ gl_FragColor = uColor; }}
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

            const lodArrays = {lod_json};
            const lodLevels = lodArrays.map(arr => ({{ data: new Float32Array(arr), points: arr.length / 2 }}));
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
            const statEl = document.getElementById('stat-{chart_id}');

            function render() {{
                gl.viewport(0, 0, canvas.width, canvas.height);
                gl.clearColor({bg_r}, {bg_g}, {bg_b}, 1.0);
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
                    gl.uniform4f(uColor, {hl_r}, {hl_g}, {hl_b}, 1.0);
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

                if (statEl) statEl.textContent = 'LOD ' + lodIndex + ' | ' + visible.count + '/' + lod.points + ' pts | ' + fps + ' fps';
                requestAnimationFrame(render);
            }}

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
        </script>
        """
