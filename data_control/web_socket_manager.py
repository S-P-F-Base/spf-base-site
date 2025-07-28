import asyncio
from typing import Dict, Final, Set

from fastapi import WebSocket, WebSocketDisconnect

WEBSOCKET_PING: Final[bytes] = b"\x01"
WEBSOCKET_PONG: Final[bytes] = b"\x02"


class WebSocketManager:
    active_connections: Dict[str, WebSocket] = {}
    subscriptions: Dict[str, Set[str]] = {}

    @classmethod
    async def connect(cls, username: str, websocket: WebSocket) -> None:
        cls.active_connections[username] = websocket

    @classmethod
    def disconnect(cls, username: str) -> None:
        cls.active_connections.pop(username, None)
        for subs in cls.subscriptions.values():
            subs.discard(username)

    @classmethod
    def subscribe(cls, username: str, event_name: str) -> None:
        if event_name not in cls.subscriptions:
            cls.subscriptions[event_name] = set()

        cls.subscriptions[event_name].add(username)

    @classmethod
    def unsubscribe(cls, username: str, event_name: str) -> None:
        if event_name in cls.subscriptions:
            cls.subscriptions[event_name].discard(username)

    @classmethod
    async def send_json(cls, json: dict, username: str) -> None:
        websocket = cls.active_connections.get(username)
        if websocket:
            await websocket.send_json(json)

    @classmethod
    async def broadcast(cls, json: dict, event_name: str) -> None:
        users = cls.subscriptions.get(event_name, set())
        for username in users:
            websocket = cls.active_connections.get(username)
            if websocket:
                await websocket.send_json(json)

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
