from collections import defaultdict
from typing import Dict, Set

from fastapi import WebSocket


class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = defaultdict(set)

    async def connect(self, key: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[key].add(websocket)

    def disconnect(self, key: str, websocket: WebSocket):
        self.active_connections[key].discard(websocket)

    async def broadcast(self, key: str, message: dict):
        for ws in list(self.active_connections[key]):
            try:
                await ws.send_json(message)
            except Exception:
                self.disconnect(key, ws)


connection_manager = ConnectionManager()
