"""
LiveChart - Real-time updating chart component.

Uses lightweight-charts with websocket connection for live updates.
"""

from typing import Optional, List, Dict, Any
import json
import uuid

import polars as pl

from wrchart.core.themes import Theme, WayyTheme


class LiveChart:
    """
    Real-time updating chart.

    Connects to a LiveServer websocket channel and updates automatically.

    Usage:
        chart = LiveChart(
            channel="btc_price",
            ws_url="ws://localhost:8765",
            chart_type="candlestick"
        )
        chart.show()  # Opens in browser with live updates
    """

    def __init__(
        self,
        channel: str,
        ws_url: str = "ws://localhost:8765",
        chart_type: str = "line",  # "line", "candlestick", "area"
        width: int = 800,
        height: int = 400,
        title: Optional[str] = None,
        theme: Optional[Theme] = None,
        max_points: int = 500,  # Rolling window
        initial_data: Optional[pl.DataFrame] = None,
    ):
        self.channel = channel
        self.ws_url = ws_url
        self.chart_type = chart_type
        self.width = width
        self.height = height
        self.title = title or channel
        self.theme = theme or WayyTheme
        self.max_points = max_points
        self.initial_data = initial_data
        self._id = str(uuid.uuid4())[:8]

    def _get_initial_data_json(self) -> str:
        """Convert initial data to JSON."""
        if self.initial_data is None:
            return "[]"

        if self.chart_type == "candlestick":
            data = []
            for row in self.initial_data.iter_rows(named=True):
                data.append({
                    "time": row.get("time") or row.get("timestamp"),
                    "open": row.get("open"),
                    "high": row.get("high"),
                    "low": row.get("low"),
                    "close": row.get("close"),
                })
        else:
            data = []
            for row in self.initial_data.iter_rows(named=True):
                data.append({
                    "time": row.get("time") or row.get("timestamp"),
                    "value": row.get("value") or row.get("close") or row.get("price"),
                })

        return json.dumps(data)

    def _generate_html(self) -> str:
        """Generate HTML with live-updating chart."""
        theme = self.theme
        initial_data = self._get_initial_data_json()

        # Series creation based on type
        if self.chart_type == "candlestick":
            series_create = "chart.addCandlestickSeries"
            series_options = f"""{{
                upColor: '{theme.colors.candle_up}',
                downColor: '{theme.colors.candle_down}',
                borderUpColor: '{theme.colors.candle_up_border}',
                borderDownColor: '{theme.colors.candle_down_border}',
                wickUpColor: '{theme.colors.wick_up}',
                wickDownColor: '{theme.colors.wick_down}',
            }}"""
            update_code = """
                // Get timestamp - handle various formats
                let time = data.time;
                if (data.timestamp) {
                    time = typeof data.timestamp === 'string'
                        ? Math.floor(new Date(data.timestamp).getTime() / 1000)
                        : Math.floor(data.timestamp);
                }
                time = Math.floor(time);  // Ensure integer

                // Handle both tick data (price only) and bar data (OHLC)
                const price = data.close || data.price;
                const point = {
                    time: time,
                    open: data.open !== undefined ? data.open : price,
                    high: data.high !== undefined ? data.high : price,
                    low: data.low !== undefined ? data.low : price,
                    close: price,
                };

                // Only update if we have valid data
                if (point.time && point.close) {
                    series.update(point);
                }
            """
        elif self.chart_type == "area":
            series_create = "chart.addAreaSeries"
            series_options = f"""{{
                lineColor: '{theme.colors.line_primary}',
                topColor: '{theme.colors.line_primary}44',
                bottomColor: '{theme.colors.line_primary}00',
                lineWidth: 2,
            }}"""
            update_code = """
                let time = data.time;
                if (data.timestamp) {
                    time = typeof data.timestamp === 'string'
                        ? Math.floor(new Date(data.timestamp).getTime() / 1000)
                        : Math.floor(data.timestamp);
                }
                time = Math.floor(time);

                const point = {
                    time: time,
                    value: data.value || data.close || data.price,
                };
                if (point.time && point.value) {
                    series.update(point);
                }
            """
        else:  # line
            series_create = "chart.addLineSeries"
            series_options = f"""{{
                color: '{theme.colors.line_primary}',
                lineWidth: 2,
            }}"""
            update_code = """
                let time = data.time;
                if (data.timestamp) {
                    time = typeof data.timestamp === 'string'
                        ? Math.floor(new Date(data.timestamp).getTime() / 1000)
                        : Math.floor(data.timestamp);
                }
                time = Math.floor(time);

                const point = {
                    time: time,
                    value: data.value || data.close || data.price,
                };
                if (point.time && point.value) {
                    series.update(point);
                }
            """

        html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>{self.title}</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600&family=JetBrains+Mono&display=swap');
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            background: {theme.colors.background};
            font-family: 'Space Grotesk', sans-serif;
            padding: 16px;
        }}
        .header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 12px;
        }}
        .title {{
            font-size: 18px;
            font-weight: 600;
            color: {theme.colors.text_primary};
        }}
        .status {{
            font-family: 'JetBrains Mono', monospace;
            font-size: 12px;
            padding: 4px 8px;
            border-radius: 4px;
        }}
        .status.connected {{ background: #22c55e22; color: #22c55e; }}
        .status.disconnected {{ background: #ef444422; color: #ef4444; }}
        .status.connecting {{ background: #f59e0b22; color: #f59e0b; }}
        #chart {{ width: 100%; }}
        .price-display {{
            font-family: 'JetBrains Mono', monospace;
            font-size: 24px;
            font-weight: 600;
            color: {theme.colors.text_primary};
            margin: 8px 0;
        }}
        .price-change {{
            font-size: 14px;
            margin-left: 8px;
        }}
        .price-change.up {{ color: #22c55e; }}
        .price-change.down {{ color: #ef4444; }}
        .stats {{
            display: flex;
            gap: 24px;
            font-family: 'JetBrains Mono', monospace;
            font-size: 12px;
            color: {theme.colors.text_secondary};
            margin-top: 8px;
        }}
    </style>
</head>
<body>
    <div class="header">
        <div class="title">{self.title}</div>
        <div id="status" class="status connecting">Connecting...</div>
    </div>
    <div id="price-display" class="price-display">--</div>
    <div id="chart"></div>
    <div class="stats">
        <span>Updates: <span id="update-count">0</span></span>
        <span>Last: <span id="last-update">--</span></span>
    </div>

    <script src="https://unpkg.com/lightweight-charts@4.2.1/dist/lightweight-charts.standalone.production.js"></script>
    <script>
        const wsUrl = '{self.ws_url}';
        const channel = '{self.channel}';
        const maxPoints = {self.max_points};

        // Create chart
        const chart = LightweightCharts.createChart(document.getElementById('chart'), {{
            width: {self.width},
            height: {self.height},
            layout: {{
                background: {{ type: 'solid', color: '{theme.colors.background}' }},
                textColor: '{theme.colors.text_primary}',
                fontFamily: "'Space Grotesk', sans-serif",
            }},
            grid: {{
                vertLines: {{ color: '{theme.colors.grid}' }},
                horzLines: {{ color: '{theme.colors.grid}' }},
            }},
            timeScale: {{
                timeVisible: true,
                secondsVisible: true,
                borderColor: '{theme.colors.border}',
            }},
            rightPriceScale: {{
                borderColor: '{theme.colors.border}',
            }},
            crosshair: {{
                mode: LightweightCharts.CrosshairMode.Normal,
            }},
        }});

        // Create series
        const series = {series_create}({series_options});

        // Set initial data
        const initialData = {initial_data};
        if (initialData.length > 0) {{
            series.setData(initialData);
        }}

        // Track data for rolling window
        let dataPoints = [...initialData];
        let updateCount = 0;
        let lastPrice = null;
        let firstPrice = initialData.length > 0 ? (initialData[0].close || initialData[0].value) : null;

        // Status elements
        const statusEl = document.getElementById('status');
        const priceEl = document.getElementById('price-display');
        const countEl = document.getElementById('update-count');
        const lastEl = document.getElementById('last-update');

        // WebSocket connection
        let ws = null;
        let reconnectAttempts = 0;
        const maxReconnectAttempts = 10;

        function connect() {{
            ws = new WebSocket(wsUrl);

            ws.onopen = () => {{
                statusEl.className = 'status connected';
                statusEl.textContent = 'Live';
                reconnectAttempts = 0;

                // Subscribe to channel
                ws.send(JSON.stringify({{
                    action: 'subscribe',
                    channel: channel
                }}));
            }};

            ws.onmessage = (event) => {{
                const msg = JSON.parse(event.data);

                if (msg.type === 'update' && msg.channel === channel) {{
                    const data = msg.data;

                    // Update chart
                    {update_code}

                    // Update price display
                    const price = data.close || data.price || data.value;
                    if (price) {{
                        priceEl.innerHTML = formatPrice(price);
                        if (firstPrice === null) firstPrice = price;
                        lastPrice = price;

                        // Show change
                        if (firstPrice) {{
                            const change = ((price - firstPrice) / firstPrice * 100).toFixed(2);
                            const changeClass = change >= 0 ? 'up' : 'down';
                            const sign = change >= 0 ? '+' : '';
                            priceEl.innerHTML += `<span class="price-change ${{changeClass}}">${{sign}}${{change}}%</span>`;
                        }}
                    }}

                    // Update stats
                    updateCount++;
                    countEl.textContent = updateCount;
                    lastEl.textContent = new Date().toLocaleTimeString();

                    // Rolling window
                    dataPoints.push(point);
                    if (dataPoints.length > maxPoints) {{
                        dataPoints = dataPoints.slice(-maxPoints);
                    }}
                }}
            }};

            ws.onclose = () => {{
                statusEl.className = 'status disconnected';
                statusEl.textContent = 'Disconnected';

                // Reconnect
                if (reconnectAttempts < maxReconnectAttempts) {{
                    reconnectAttempts++;
                    statusEl.className = 'status connecting';
                    statusEl.textContent = `Reconnecting (${{reconnectAttempts}})...`;
                    setTimeout(connect, 1000 * reconnectAttempts);
                }}
            }};

            ws.onerror = (err) => {{
                console.error('WebSocket error:', err);
            }};
        }}

        function formatPrice(price) {{
            if (price >= 1000) return price.toLocaleString('en-US', {{minimumFractionDigits: 2, maximumFractionDigits: 2}});
            if (price >= 1) return price.toFixed(2);
            return price.toFixed(6);
        }}

        // Auto-resize
        const resizeObserver = new ResizeObserver(entries => {{
            chart.applyOptions({{ width: entries[0].contentRect.width }});
        }});
        resizeObserver.observe(document.getElementById('chart').parentElement);

        // Start connection
        connect();

        // Fit content on double-click
        document.getElementById('chart').addEventListener('dblclick', () => {{
            chart.timeScale().fitContent();
        }});
    </script>
</body>
</html>
        """
        return html

    def show(self):
        """Display the live chart in browser."""
        import tempfile
        import webbrowser

        html = self._generate_html()

        with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
            f.write(html)
            webbrowser.open(f'file://{f.name}')

    def _repr_html_(self) -> str:
        """Jupyter notebook display."""
        return self._generate_html()

    def save(self, filepath: str):
        """Save the HTML to a file."""
        with open(filepath, 'w') as f:
            f.write(self._generate_html())
