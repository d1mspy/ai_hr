from fastapi import WebSocket
from typing import Dict
import asyncio

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[int, WebSocket] = {}
        self.lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, user_id: int) -> bool:
        async with self.lock:
            if user_id in self.active_connections:
                return False  # Пользователь уже подключен
            
            await websocket.accept()
            self.active_connections[user_id] = websocket
            return True

    def disconnect(self, user_id: int):
        if user_id in self.active_connections:
            del self.active_connections[user_id]

    def is_user_connected(self, user_id: int) -> bool:
        return user_id in self.active_connections