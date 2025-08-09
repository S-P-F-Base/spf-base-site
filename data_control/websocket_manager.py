import asyncio
from typing import Dict, Final, Set

from fastapi import WebSocket, WebSocketDisconnect

WEBSOCKET_PING: Final[bytes] = b"\x01"
WEBSOCKET_PONG: Final[bytes] = b"\x02"


class WebSocketManager:
    _active_connections: Dict[str, WebSocket] = {}
    _subscriptions: Dict[str, Set[str]] = {}

    @classmethod
    def has_user(cls, username: str) -> bool:
        return username in cls._active_connections

    @classmethod
    async def connect(cls, username: str, websocket: WebSocket) -> None:
        cls._active_connections[username] = websocket

    @classmethod
    def disconnect(cls, username: str) -> None:
        cls._active_connections.pop(username, None)
        for subs in cls._subscriptions.values():
            subs.discard(username)

    @classmethod
    def subscribe(cls, username: str, event_name: str) -> None:
        if event_name not in cls._subscriptions:
            cls._subscriptions[event_name] = set()

        cls._subscriptions[event_name].add(username)

    @classmethod
    def unsubscribe(cls, username: str, event_name: str) -> None:
        if event_name in cls._subscriptions:
            cls._subscriptions[event_name].discard(username)

    @classmethod
    async def send_json(cls, json: dict, username: str) -> None:
        websocket = cls._active_connections.get(username)
        if websocket:
            await websocket.send_json(json)

    @classmethod
    async def send_event(cls, event_name: str, json_data: dict) -> None:
        users = cls._subscriptions.get(event_name, set())
        json_data["event"] = event_name
        for username in users:
            websocket = cls._active_connections.get(username)
            if websocket:
                await websocket.send_json(json_data)

    @classmethod
    async def heartbeat(cls, websocket: WebSocket) -> bool:
        try:
            await websocket.send_bytes(WEBSOCKET_PING)
            msg = await asyncio.wait_for(websocket.receive_bytes(), timeout=30)
            if msg != WEBSOCKET_PONG:
                return False

            return True

        except (asyncio.TimeoutError, WebSocketDisconnect):
            return False
