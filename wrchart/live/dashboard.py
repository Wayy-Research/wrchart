"""
LiveDashboard - Multi-component real-time dashboard.

Combines charts, tables, and metrics in a single live view.
"""

from typing import Optional, List, Dict, Any, Union
import json
import uuid

from wrchart.core.themes import Theme, WayyTheme
from wrchart.live.chart import LiveChart
from wrchart.live.table import LiveTable


class LiveDashboard:
    """
    Real-time dashboard with multiple components.

    Usage:
        dashboard = LiveDashboard(
            title="Trading Dashboard",
            ws_url="ws://localhost:8765"
        )

        dashboard.add_chart("btc_price", chart_type="candlestick", height=300)
        dashboard.add_table("trades", columns=[...])
        dashboard.add_metric("portfolio_value", label="Portfolio")

        dashboard.show()
    """

    def __init__(
        self,
        title: str = "Live Dashboard",
        ws_url: str = "ws://localhost:8765",
        theme: Optional[Theme] = None,
        layout: str = "auto",  # "auto", "grid", "rows"
        columns: int = 2,
    ):
        self.title = title
        self.ws_url = ws_url
        self.theme = theme or WayyTheme
        self.layout = layout
        self.columns = columns
        self._id = str(uuid.uuid4())[:8]
        self.components: List[Dict[str, Any]] = []

    def add_chart(
        self,
        channel: str,
        chart_type: str = "line",
        title: Optional[str] = None,
        height: int = 300,
        **kwargs
    ) -> "LiveDashboard":
        """Add a live chart component."""
        self.components.append({
            "type": "chart",
            "channel": channel,
            "chart_type": chart_type,
            "title": title or channel,
            "height": height,
            "options": kwargs,
        })
        return self

    def add_table(
        self,
        channel: str,
        columns: Optional[List[Dict]] = None,
        title: Optional[str] = None,
        max_rows: int = 30,
        height: int = 300,
        **kwargs
    ) -> "LiveDashboard":
        """Add a live table component."""
        self.components.append({
            "type": "table",
            "channel": channel,
            "columns": columns,
            "title": title or channel,
            "max_rows": max_rows,
            "height": height,
            "options": kwargs,
        })
        return self

    def add_metric(
        self,
        channel: str,
        label: str,
        format: str = "number",  # "number", "price", "percent"
        size: str = "normal",  # "small", "normal", "large"
    ) -> "LiveDashboard":
        """Add a live metric display."""
        self.components.append({
            "type": "metric",
            "channel": channel,
            "label": label,
            "format": format,
            "size": size,
        })
        return self

    def _generate_html(self) -> str:
        """Generate complete dashboard HTML."""
        theme = self.theme
        components_json = json.dumps(self.components)

        # Calculate grid layout
        num_components = len(self.components)
        grid_cols = min(self.columns, num_components) if self.layout != "rows" else 1

        html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>{self.title}</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=JetBrains+Mono&display=swap');
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            background: {theme.colors.background};
            font-family: 'Space Grotesk', sans-serif;
            min-height: 100vh;
        }}
        .dashboard-header {{
            background: #000;
            color: #fff;
            padding: 12px 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .dashboard-title {{
            font-size: 18px;
            font-weight: 600;
        }}
        .dashboard-status {{
            display: flex;
            gap: 16px;
            font-family: 'JetBrains Mono', monospace;
            font-size: 12px;
        }}
        .status-item {{
            display: flex;
            align-items: center;
            gap: 6px;
        }}
        .status-dot {{
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: #22c55e;
            animation: pulse 1s infinite;
        }}
        .status-dot.disconnected {{ background: #ef4444; animation: none; }}
        @keyframes pulse {{
            0%, 100% {{ opacity: 1; }}
            50% {{ opacity: 0.5; }}
        }}

        .dashboard-grid {{
            display: grid;
            grid-template-columns: repeat({grid_cols}, 1fr);
            gap: 16px;
            padding: 16px;
        }}

        .component {{
            background: #fff;
            border: 1px solid {theme.colors.border};
            border-radius: 4px;
            overflow: hidden;
        }}
        .component-header {{
            background: {theme.colors.grid};
            padding: 8px 12px;
            border-bottom: 1px solid {theme.colors.border};
            font-weight: 600;
            font-size: 13px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .component-body {{
            padding: 0;
        }}
        .component-body.padded {{
            padding: 12px;
        }}

        /* Metric styling */
        .metric {{
            text-align: center;
            padding: 20px;
        }}
        .metric-value {{
            font-family: 'JetBrains Mono', monospace;
            font-weight: 600;
            color: {theme.colors.text_primary};
        }}
        .metric-value.small {{ font-size: 24px; }}
        .metric-value.normal {{ font-size: 36px; }}
        .metric-value.large {{ font-size: 48px; }}
        .metric-label {{
            font-size: 12px;
            color: {theme.colors.text_secondary};
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-top: 4px;
        }}
        .metric-change {{
            font-family: 'JetBrains Mono', monospace;
            font-size: 14px;
            margin-top: 8px;
        }}
        .metric-change.up {{ color: #22c55e; }}
        .metric-change.down {{ color: #ef4444; }}

        /* Chart container */
        .chart-container {{ width: 100%; }}

        /* Table styling */
        .table-container {{
            max-height: 400px;
            overflow-y: auto;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            font-family: 'JetBrains Mono', monospace;
            font-size: 12px;
        }}
        thead {{
            position: sticky;
            top: 0;
            background: {theme.colors.background};
        }}
        th {{
            text-align: left;
            padding: 8px 10px;
            border-bottom: 2px solid {theme.colors.border};
            color: {theme.colors.text_secondary};
            font-weight: 600;
            font-size: 10px;
            text-transform: uppercase;
        }}
        td {{
            padding: 6px 10px;
            border-bottom: 1px solid {theme.colors.grid};
        }}
        tr.new {{ animation: highlight 2s ease-out; }}
        @keyframes highlight {{
            0% {{ background: #fef08a; }}
            100% {{ background: transparent; }}
        }}
        .type-mint {{ color: #22c55e; font-weight: 600; }}
        .type-burn {{ color: #888; }}
        .type-liq {{ color: #ef4444; font-weight: 600; }}
    </style>
</head>
<body>
    <div class="dashboard-header">
        <div class="dashboard-title">{self.title}</div>
        <div class="dashboard-status">
            <div class="status-item">
                <div id="ws-status" class="status-dot"></div>
                <span id="ws-status-text">Connecting...</span>
            </div>
            <div class="status-item">
                <span>Updates: <span id="total-updates">0</span></span>
            </div>
        </div>
    </div>

    <div class="dashboard-grid" id="grid"></div>

    <script src="https://unpkg.com/lightweight-charts@4.2.1/dist/lightweight-charts.standalone.production.js"></script>
    <script>
        const wsUrl = '{self.ws_url}';
        const components = {components_json};
        const theme = {{
            background: '{theme.colors.background}',
            text: '{theme.colors.text_primary}',
            textSecondary: '{theme.colors.text_secondary}',
            grid: '{theme.colors.grid}',
            border: '{theme.colors.border}',
            up: '#22c55e',
            down: '#ef4444',
            line: '{theme.colors.line_primary}',
        }};

        // State
        let totalUpdates = 0;
        const charts = {{}};
        const tables = {{}};
        const metrics = {{}};

        // Build components
        const grid = document.getElementById('grid');

        components.forEach((comp, idx) => {{
            const div = document.createElement('div');
            div.className = 'component';
            div.id = `component-${{idx}}`;

            if (comp.type === 'chart') {{
                div.innerHTML = `
                    <div class="component-header">
                        <span>${{comp.title}}</span>
                        <span style="font-size:11px;color:${{theme.textSecondary}}" id="chart-price-${{idx}}">--</span>
                    </div>
                    <div class="component-body">
                        <div class="chart-container" id="chart-${{idx}}"></div>
                    </div>
                `;
                grid.appendChild(div);

                // Create chart
                const chartEl = document.getElementById(`chart-${{idx}}`);
                const chart = LightweightCharts.createChart(chartEl, {{
                    width: chartEl.offsetWidth,
                    height: comp.height || 300,
                    layout: {{
                        background: {{ type: 'solid', color: theme.background }},
                        textColor: theme.text,
                        fontFamily: "'Space Grotesk', sans-serif",
                    }},
                    grid: {{
                        vertLines: {{ color: theme.grid }},
                        horzLines: {{ color: theme.grid }},
                    }},
                    timeScale: {{ timeVisible: true, secondsVisible: true, borderColor: theme.border }},
                    rightPriceScale: {{ borderColor: theme.border }},
                }});

                let series;
                if (comp.chart_type === 'candlestick') {{
                    series = chart.addCandlestickSeries({{
                        upColor: theme.up,
                        downColor: theme.down,
                        borderUpColor: theme.up,
                        borderDownColor: theme.down,
                        wickUpColor: theme.up,
                        wickDownColor: theme.down,
                    }});
                }} else if (comp.chart_type === 'area') {{
                    series = chart.addAreaSeries({{
                        lineColor: theme.line,
                        topColor: theme.line + '44',
                        bottomColor: theme.line + '00',
                    }});
                }} else {{
                    series = chart.addLineSeries({{ color: theme.line }});
                }}

                charts[comp.channel] = {{ chart, series, priceEl: document.getElementById(`chart-price-${{idx}}`), type: comp.chart_type }};

                // Resize observer
                new ResizeObserver(entries => {{
                    chart.applyOptions({{ width: entries[0].contentRect.width }});
                }}).observe(chartEl);

            }} else if (comp.type === 'table') {{
                const cols = comp.columns || [
                    {{key: 'timestamp', label: 'Time', format: 'time'}},
                    {{key: 'type', label: 'Type'}},
                    {{key: 'price', label: 'Price', format: 'price'}},
                ];

                div.innerHTML = `
                    <div class="component-header">
                        <span>${{comp.title}}</span>
                        <span style="font-size:11px;color:${{theme.textSecondary}}" id="table-count-${{idx}}">0 rows</span>
                    </div>
                    <div class="component-body">
                        <div class="table-container" style="max-height:${{comp.height || 300}}px">
                            <table>
                                <thead><tr>${{cols.map(c => `<th>${{c.label || c.key}}</th>`).join('')}}</tr></thead>
                                <tbody id="table-body-${{idx}}"></tbody>
                            </table>
                        </div>
                    </div>
                `;
                grid.appendChild(div);

                tables[comp.channel] = {{
                    body: document.getElementById(`table-body-${{idx}}`),
                    countEl: document.getElementById(`table-count-${{idx}}`),
                    columns: cols,
                    maxRows: comp.max_rows || 30,
                }};

            }} else if (comp.type === 'metric') {{
                div.innerHTML = `
                    <div class="component-body padded">
                        <div class="metric">
                            <div class="metric-value ${{comp.size || 'normal'}}" id="metric-value-${{idx}}">--</div>
                            <div class="metric-label">${{comp.label}}</div>
                            <div class="metric-change" id="metric-change-${{idx}}"></div>
                        </div>
                    </div>
                `;
                grid.appendChild(div);

                metrics[comp.channel] = {{
                    valueEl: document.getElementById(`metric-value-${{idx}}`),
                    changeEl: document.getElementById(`metric-change-${{idx}}`),
                    format: comp.format || 'number',
                    initialValue: null,
                }};
            }}
        }});

        // Format functions
        function formatValue(value, format) {{
            if (value === null || value === undefined) return '--';
            switch (format) {{
                case 'time':
                    return new Date(value).toLocaleTimeString();
                case 'price':
                    const n = parseFloat(value);
                    if (n >= 1000) return n.toLocaleString('en-US', {{minimumFractionDigits:2, maximumFractionDigits:2}});
                    return n >= 1 ? n.toFixed(2) : n.toFixed(6);
                case 'percent':
                    return (parseFloat(value) * 100).toFixed(2) + '%';
                default:
                    return String(value);
            }}
        }}

        // WebSocket
        const statusDot = document.getElementById('ws-status');
        const statusText = document.getElementById('ws-status-text');
        const totalUpdatesEl = document.getElementById('total-updates');

        let ws = null;
        let reconnectAttempts = 0;

        function connect() {{
            ws = new WebSocket(wsUrl);

            ws.onopen = () => {{
                statusDot.classList.remove('disconnected');
                statusText.textContent = 'Connected';
                reconnectAttempts = 0;

                // Subscribe to all channels
                const channels = new Set(components.map(c => c.channel));
                channels.forEach(ch => {{
                    ws.send(JSON.stringify({{ action: 'subscribe', channel: ch }}));
                }});
            }};

            ws.onmessage = (event) => {{
                const msg = JSON.parse(event.data);
                if (msg.type !== 'update') return;

                totalUpdates++;
                totalUpdatesEl.textContent = totalUpdates;

                const channel = msg.channel;
                const data = msg.data;

                // Update chart
                if (charts[channel]) {{
                    const c = charts[channel];
                    const time = data.timestamp ? Math.floor(new Date(data.timestamp).getTime() / 1000) : data.time;

                    if (c.type === 'candlestick') {{
                        c.series.update({{ time, open: data.open, high: data.high, low: data.low, close: data.close || data.price }});
                    }} else {{
                        c.series.update({{ time, value: data.value || data.close || data.price }});
                    }}

                    const price = data.close || data.price || data.value;
                    if (price && c.priceEl) c.priceEl.textContent = formatValue(price, 'price');
                }}

                // Update table
                if (tables[channel]) {{
                    const t = tables[channel];
                    const tr = document.createElement('tr');
                    tr.className = 'new';

                    t.columns.forEach(col => {{
                        const td = document.createElement('td');
                        td.textContent = formatValue(data[col.key], col.format);
                        if (col.key === 'type') {{
                            const val = String(data[col.key]).toLowerCase();
                            if (['mint','buy'].includes(val)) td.className = 'type-mint';
                            if (['burn','sell'].includes(val)) td.className = 'type-burn';
                            if (['liquidation','liq'].includes(val)) td.className = 'type-liq';
                        }}
                        tr.appendChild(td);
                    }});

                    t.body.insertBefore(tr, t.body.firstChild);
                    while (t.body.children.length > t.maxRows) t.body.removeChild(t.body.lastChild);
                    t.countEl.textContent = t.body.children.length + ' rows';

                    setTimeout(() => tr.classList.remove('new'), 2000);
                }}

                // Update metric
                if (metrics[channel]) {{
                    const m = metrics[channel];
                    const value = data.value || data.price || data.close;
                    if (value !== undefined) {{
                        m.valueEl.textContent = formatValue(value, m.format);
                        if (m.initialValue === null) m.initialValue = value;

                        const change = ((value - m.initialValue) / m.initialValue * 100).toFixed(2);
                        const sign = change >= 0 ? '+' : '';
                        m.changeEl.textContent = `${{sign}}${{change}}%`;
                        m.changeEl.className = 'metric-change ' + (change >= 0 ? 'up' : 'down');
                    }}
                }}
            }};

            ws.onclose = () => {{
                statusDot.classList.add('disconnected');
                statusText.textContent = 'Disconnected';
                if (reconnectAttempts < 10) {{
                    reconnectAttempts++;
                    statusText.textContent = `Reconnecting (${{reconnectAttempts}})...`;
                    setTimeout(connect, 1000 * reconnectAttempts);
                }}
            }};

            ws.onerror = (err) => console.error('WebSocket error:', err);
        }}

        connect();
    </script>
</body>
</html>
        """
        return html

    def show(self):
        """Display dashboard in browser."""
        import tempfile
        import webbrowser

        html = self._generate_html()

        with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
            f.write(html)
            webbrowser.open(f'file://{f.name}')

    def _repr_html_(self) -> str:
        return self._generate_html()

    def save(self, filepath: str):
        """Save HTML to file."""
        with open(filepath, 'w') as f:
            f.write(self._generate_html())
