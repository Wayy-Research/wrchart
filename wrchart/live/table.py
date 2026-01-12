"""
LiveTable - Real-time updating data table.

Connects to websocket for live updates with row highlighting.
"""

from typing import Optional, List, Dict, Any
import json
import uuid

from wrchart.core.themes import Theme, WayyTheme


class LiveTable:
    """
    Real-time updating table.

    Shows streaming data with:
    - Auto-updating rows
    - New row highlighting
    - Configurable columns
    - Max rows with FIFO

    Usage:
        table = LiveTable(
            channel="trades",
            ws_url="ws://localhost:8765",
            columns=["time", "type", "price", "amount"]
        )
        table.show()
    """

    def __init__(
        self,
        channel: str,
        ws_url: str = "ws://localhost:8765",
        columns: Optional[List[Dict[str, Any]]] = None,
        title: Optional[str] = None,
        max_rows: int = 50,
        theme: Optional[Theme] = None,
        height: int = 500,
        highlight_duration: int = 2000,  # ms
    ):
        self.channel = channel
        self.ws_url = ws_url
        self.title = title or channel
        self.max_rows = max_rows
        self.theme = theme or WayyTheme
        self.height = height
        self.highlight_duration = highlight_duration
        self._id = str(uuid.uuid4())[:8]

        # Default columns if not specified
        self.columns = columns or [
            {"key": "timestamp", "label": "Time", "format": "time"},
            {"key": "type", "label": "Type"},
            {"key": "price", "label": "Price", "format": "price"},
            {"key": "amount", "label": "Amount", "format": "number"},
        ]

    def _generate_html(self) -> str:
        """Generate HTML with live-updating table."""
        theme = self.theme
        columns_json = json.dumps(self.columns)

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

        .table-container {{
            max-height: {self.height}px;
            overflow-y: auto;
            border: 1px solid {theme.colors.border};
            border-radius: 4px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            font-family: 'JetBrains Mono', monospace;
            font-size: 13px;
        }}
        thead {{
            position: sticky;
            top: 0;
            background: {theme.colors.background};
            z-index: 1;
        }}
        th {{
            text-align: left;
            padding: 10px 12px;
            border-bottom: 2px solid {theme.colors.border};
            color: {theme.colors.text_secondary};
            font-weight: 600;
            font-size: 11px;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }}
        td {{
            padding: 8px 12px;
            border-bottom: 1px solid {theme.colors.grid};
            color: {theme.colors.text_primary};
        }}
        tr:hover {{
            background: {theme.colors.grid};
        }}
        tr.new {{
            animation: highlight {self.highlight_duration}ms ease-out;
        }}
        @keyframes highlight {{
            0% {{ background: #fef08a; }}
            100% {{ background: transparent; }}
        }}
        .type-mint, .type-buy {{ color: #22c55e; font-weight: 600; }}
        .type-burn, .type-sell {{ color: #ef4444; font-weight: 600; }}
        .type-liquidation {{ color: #ef4444; font-weight: 600; background: #ef444411; }}
        .positive {{ color: #22c55e; }}
        .negative {{ color: #ef4444; }}

        .stats {{
            display: flex;
            gap: 24px;
            font-family: 'JetBrains Mono', monospace;
            font-size: 12px;
            color: {theme.colors.text_secondary};
            margin-top: 8px;
        }}
        .empty {{
            text-align: center;
            padding: 40px;
            color: {theme.colors.text_secondary};
        }}
    </style>
</head>
<body>
    <div class="header">
        <div class="title">{self.title}</div>
        <div id="status" class="status connecting">Connecting...</div>
    </div>

    <div class="table-container">
        <table>
            <thead>
                <tr id="header-row"></tr>
            </thead>
            <tbody id="table-body">
                <tr><td colspan="100" class="empty">Waiting for data...</td></tr>
            </tbody>
        </table>
    </div>

    <div class="stats">
        <span>Rows: <span id="row-count">0</span></span>
        <span>Updates: <span id="update-count">0</span></span>
        <span>Last: <span id="last-update">--</span></span>
    </div>

    <script>
        const wsUrl = '{self.ws_url}';
        const channel = '{self.channel}';
        const maxRows = {self.max_rows};
        const columns = {columns_json};
        const highlightDuration = {self.highlight_duration};

        // Build header
        const headerRow = document.getElementById('header-row');
        columns.forEach(col => {{
            const th = document.createElement('th');
            th.textContent = col.label || col.key;
            headerRow.appendChild(th);
        }});

        // State
        const tableBody = document.getElementById('table-body');
        let rows = [];
        let updateCount = 0;
        let hasData = false;

        // Elements
        const statusEl = document.getElementById('status');
        const rowCountEl = document.getElementById('row-count');
        const updateCountEl = document.getElementById('update-count');
        const lastEl = document.getElementById('last-update');

        // Format value based on column config
        function formatValue(value, format) {{
            if (value === null || value === undefined) return '--';

            switch (format) {{
                case 'time':
                    if (typeof value === 'string') {{
                        const d = new Date(value);
                        return d.toLocaleTimeString();
                    }}
                    return value;
                case 'datetime':
                    if (typeof value === 'string') {{
                        const d = new Date(value);
                        return d.toLocaleString();
                    }}
                    return value;
                case 'price':
                    const num = parseFloat(value);
                    if (num >= 1000) return num.toLocaleString('en-US', {{minimumFractionDigits: 2, maximumFractionDigits: 2}});
                    if (num >= 1) return num.toFixed(2);
                    return num.toFixed(6);
                case 'number':
                    return parseFloat(value).toLocaleString();
                case 'percent':
                    return (parseFloat(value) * 100).toFixed(2) + '%';
                default:
                    return String(value);
            }}
        }}

        // Get CSS class for cell
        function getCellClass(key, value) {{
            const val = String(value).toLowerCase();
            if (key === 'type') {{
                if (['mint', 'buy', 'open', 'long'].includes(val)) return 'type-mint';
                if (['burn', 'sell', 'close', 'short'].includes(val)) return 'type-burn';
                if (['liquidation', 'liq'].includes(val)) return 'type-liquidation';
            }}
            if (typeof value === 'number') {{
                if (value > 0) return 'positive';
                if (value < 0) return 'negative';
            }}
            return '';
        }}

        // Add row to table
        function addRow(data) {{
            if (!hasData) {{
                tableBody.innerHTML = '';
                hasData = true;
            }}

            const tr = document.createElement('tr');
            tr.className = 'new';

            columns.forEach(col => {{
                const td = document.createElement('td');
                const value = data[col.key];
                td.textContent = formatValue(value, col.format);
                td.className = getCellClass(col.key, value);
                tr.appendChild(td);
            }});

            // Insert at top
            tableBody.insertBefore(tr, tableBody.firstChild);

            // Remove highlight after animation
            setTimeout(() => {{
                tr.classList.remove('new');
            }}, highlightDuration);

            // Enforce max rows
            while (tableBody.children.length > maxRows) {{
                tableBody.removeChild(tableBody.lastChild);
            }}

            // Update counts
            rowCountEl.textContent = tableBody.children.length;
            updateCount++;
            updateCountEl.textContent = updateCount;
            lastEl.textContent = new Date().toLocaleTimeString();
        }}

        // WebSocket
        let ws = null;
        let reconnectAttempts = 0;

        function connect() {{
            ws = new WebSocket(wsUrl);

            ws.onopen = () => {{
                statusEl.className = 'status connected';
                statusEl.textContent = 'Live';
                reconnectAttempts = 0;
                ws.send(JSON.stringify({{ action: 'subscribe', channel: channel }}));
            }};

            ws.onmessage = (event) => {{
                const msg = JSON.parse(event.data);
                if (msg.type === 'update' && msg.channel === channel) {{
                    addRow(msg.data);
                }}
            }};

            ws.onclose = () => {{
                statusEl.className = 'status disconnected';
                statusEl.textContent = 'Disconnected';
                if (reconnectAttempts < 10) {{
                    reconnectAttempts++;
                    statusEl.className = 'status connecting';
                    statusEl.textContent = `Reconnecting (${{reconnectAttempts}})...`;
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
        """Display the live table in browser."""
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
