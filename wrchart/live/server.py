"""
WebSocket server for live chart updates.

Bridges wrdata streams to browser clients.
"""

import asyncio
import json
import logging
from typing import Dict, Set, Callable, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
import weakref

try:
    import websockets
    from websockets.server import serve
except ImportError:
    websockets = None

logger = logging.getLogger(__name__)


@dataclass
class LiveMessage:
    """Message sent to clients."""
    channel: str  # Chart/table ID
    type: str     # "update", "snapshot", "error"
    data: Any
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.utcnow().isoformat()

    def to_json(self) -> str:
        return json.dumps(asdict(self))


class LiveServer:
    """
    WebSocket server for streaming data to charts/tables.

    Usage:
        server = LiveServer(port=8765)

        # Register a data source
        async def price_stream():
            async for msg in wrdata_stream:
                yield {"price": msg.price, "time": msg.timestamp}

        server.add_stream("btc_price", price_stream)

        # Run server
        await server.start()
    """

    def __init__(self, host: str = "localhost", port: int = 8765):
        if websockets is None:
            raise ImportError("websockets required: pip install websockets")

        self.host = host
        self.port = port
        self.clients: Set = set()
        self.subscriptions: Dict[str, Set] = {}  # channel -> clients
        self.streams: Dict[str, Callable] = {}   # channel -> async generator factory
        self.stream_tasks: Dict[str, asyncio.Task] = {}
        self._server = None
        self._running = False

    def add_stream(self, channel: str, stream_factory: Callable):
        """
        Register a stream source for a channel.

        Args:
            channel: Unique channel ID (e.g., "btc_price", "trades")
            stream_factory: Async function that yields data dicts
        """
        self.streams[channel] = stream_factory

    async def broadcast(self, channel: str, data: Any, msg_type: str = "update"):
        """Broadcast data to all subscribers of a channel."""
        if channel not in self.subscriptions:
            return

        msg = LiveMessage(channel=channel, type=msg_type, data=data)
        json_msg = msg.to_json()

        # Send to all subscribed clients
        dead_clients = set()
        for client in self.subscriptions[channel]:
            try:
                await client.send(json_msg)
            except websockets.exceptions.ConnectionClosed:
                dead_clients.add(client)

        # Clean up dead clients
        for client in dead_clients:
            self._remove_client(client)

    async def _handle_client(self, websocket):
        """Handle a client connection."""
        self.clients.add(websocket)
        logger.info(f"Client connected: {websocket.remote_address}")

        try:
            async for message in websocket:
                await self._process_message(websocket, message)
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            self._remove_client(websocket)
            logger.info(f"Client disconnected: {websocket.remote_address}")

    async def _process_message(self, client, message: str):
        """Process incoming client message."""
        try:
            data = json.loads(message)
            action = data.get("action")
            channel = data.get("channel")

            if action == "subscribe" and channel:
                await self._subscribe_client(client, channel)
            elif action == "unsubscribe" and channel:
                self._unsubscribe_client(client, channel)
            elif action == "ping":
                await client.send(json.dumps({"type": "pong"}))

        except json.JSONDecodeError:
            logger.warning(f"Invalid JSON from client: {message[:100]}")

    async def _subscribe_client(self, client, channel: str):
        """Subscribe client to a channel."""
        if channel not in self.subscriptions:
            self.subscriptions[channel] = set()

        self.subscriptions[channel].add(client)
        logger.info(f"Client subscribed to {channel}")

        # Start stream if not running
        if channel in self.streams and channel not in self.stream_tasks:
            task = asyncio.create_task(self._run_stream(channel))
            self.stream_tasks[channel] = task

        # Send confirmation
        await client.send(json.dumps({
            "type": "subscribed",
            "channel": channel
        }))

    def _unsubscribe_client(self, client, channel: str):
        """Unsubscribe client from a channel."""
        if channel in self.subscriptions:
            self.subscriptions[channel].discard(client)

            # Stop stream if no subscribers
            if not self.subscriptions[channel]:
                if channel in self.stream_tasks:
                    self.stream_tasks[channel].cancel()
                    del self.stream_tasks[channel]

    def _remove_client(self, client):
        """Remove client from all subscriptions."""
        self.clients.discard(client)
        for channel in list(self.subscriptions.keys()):
            self.subscriptions[channel].discard(client)

            # Clean up empty channels
            if not self.subscriptions[channel]:
                del self.subscriptions[channel]
                if channel in self.stream_tasks:
                    self.stream_tasks[channel].cancel()
                    del self.stream_tasks[channel]

    async def _run_stream(self, channel: str):
        """Run a stream and broadcast updates."""
        stream_factory = self.streams.get(channel)
        if not stream_factory:
            return

        try:
            async for data in stream_factory():
                if channel not in self.subscriptions:
                    break
                await self.broadcast(channel, data)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Stream error on {channel}: {e}")
            await self.broadcast(channel, {"error": str(e)}, msg_type="error")

    async def start(self):
        """Start the WebSocket server."""
        self._running = True
        self._server = await serve(
            self._handle_client,
            self.host,
            self.port,
            ping_interval=20,
            ping_timeout=20,
        )
        logger.info(f"LiveServer running on ws://{self.host}:{self.port}")

        # Keep running
        await self._server.wait_closed()

    async def stop(self):
        """Stop the server."""
        self._running = False

        # Cancel all stream tasks
        for task in self.stream_tasks.values():
            task.cancel()

        # Close all client connections
        for client in list(self.clients):
            await client.close()

        # Close server
        if self._server:
            self._server.close()
            await self._server.wait_closed()

    def run(self):
        """Run server (blocking)."""
        asyncio.run(self.start())


class StreamBridge:
    """
    Bridge wrdata StreamMessage to LiveServer.

    Usage:
        from wrdata.streaming import BinanceStreamProvider

        bridge = StreamBridge(live_server)
        bridge.connect_wrdata_stream(
            "btc_price",
            binance.subscribe_ticker("BTCUSDT")
        )
    """

    def __init__(self, server: LiveServer):
        self.server = server

    def connect_wrdata_stream(self, channel: str, stream_coro):
        """
        Connect a wrdata async stream to a channel.

        Args:
            channel: Channel name for clients to subscribe
            stream_coro: Async generator from wrdata (e.g., provider.subscribe_ticker())
        """
        async def stream_factory():
            async for msg in stream_coro:
                yield {
                    "symbol": msg.symbol,
                    "timestamp": msg.timestamp.isoformat() if msg.timestamp else None,
                    "price": msg.price,
                    "bid": msg.bid,
                    "ask": msg.ask,
                    "volume": msg.volume,
                    "open": msg.open,
                    "high": msg.high,
                    "low": msg.low,
                    "close": msg.close,
                    "type": msg.stream_type,
                }

        self.server.add_stream(channel, stream_factory)

    def connect_custom_stream(self, channel: str, async_generator_factory: Callable):
        """Connect any async generator to a channel."""
        self.server.add_stream(channel, async_generator_factory)
