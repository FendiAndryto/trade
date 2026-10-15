"""
WebSocket Connection Manager — tracks connected clients and broadcasts events.
"""

from uuid import UUID

from fastapi import WebSocket


class ConnectionManager:
    """Manages WebSocket connections per user."""

    def __init__(self):
        # user_id -> WebSocket connection
        self._connections: dict[UUID, WebSocket] = {}
        # user_id -> subscribed symbols
        self._subscriptions: dict[UUID, set[str]] = {}
        # account_id -> WebSocket connection (MT5 Agent)
        self._agents: dict[UUID, WebSocket] = {}

    async def connect(self, websocket: WebSocket, user_id: UUID):
        """Accept and register a WebSocket connection."""
        await websocket.accept()
        self._connections[user_id] = websocket
        self._subscriptions[user_id] = set()

    def disconnect(self, user_id: UUID):
        """Remove a disconnected client."""
        self._connections.pop(user_id, None)
        self._subscriptions.pop(user_id, None)

    async def connect_agent(self, websocket: WebSocket, account_id: UUID):
        """Accept and register an MT5 Agent connection."""
        await websocket.accept()
        self._agents[account_id] = websocket

    def disconnect_agent(self, account_id: UUID):
        """Remove a disconnected MT5 Agent."""
        self._agents.pop(account_id, None)

    def is_agent_connected(self, account_id: UUID) -> bool:
        """Check if an MT5 Agent is currently connected."""
        return account_id in self._agents

    async def send_to_agent(self, account_id: UUID, event: str, data: dict) -> bool:
        """Send a command to a connected MT5 Agent."""
        ws = self._agents.get(account_id)
        if ws:
            try:
                await ws.send_json({"event": event, "data": data})
                return True
            except Exception:
                self.disconnect_agent(account_id)
        return False

    async def subscribe(self, user_id: UUID, symbols: list[str]):
        """Subscribe a user to price updates for given symbols."""
        if user_id in self._subscriptions:
            self._subscriptions[user_id] = set(s.upper() for s in symbols)

    async def send_to_user(self, user_id: UUID, event: str, data: dict):
        """Send an event to a specific user."""
        ws = self._connections.get(user_id)
        if ws:
            try:
                await ws.send_json({"event": event, "data": data})
            except Exception:
                self.disconnect(user_id)

    async def broadcast_tick(self, symbol: str, tick_data: dict):
        """Broadcast a price tick to all users subscribed to this symbol."""
        symbol_upper = symbol.upper()
        for user_id, subs in self._subscriptions.items():
            if symbol_upper in subs:
                await self.send_to_user(user_id, "tick", tick_data)

    async def broadcast_all(self, event: str, data: dict):
        """Broadcast an event to all connected users."""
        disconnected = []
        for user_id, ws in self._connections.items():
            try:
                await ws.send_json({"event": event, "data": data})
            except Exception:
                disconnected.append(user_id)
        for uid in disconnected:
            self.disconnect(uid)

    @property
    def active_connections(self) -> int:
        return len(self._connections)

    @property
    def has_connected_agents(self) -> bool:
        return len(self._agents) > 0

    def is_connected(self, user_id: UUID) -> bool:
        return user_id in self._connections

    def get_all_subscribed_symbols(self) -> set[str]:
        all_symbols = set()
        for subs in self._subscriptions.values():
            all_symbols.update(subs)
        return all_symbols


# Singleton instance
ws_manager = ConnectionManager()
