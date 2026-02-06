from typing import Dict
from fastapi import WebSocket


class ConnectionManager:
    _instance = None
    
    def __init__(self):
        # Maps device_id -> WebSocket object
        self.active_connections: Dict[str, WebSocket] = {}

    def add(self, device_id: str, websocket: WebSocket):
        self.active_connections[device_id] = websocket

    def remove(self, device_id: str):
        if device_id in self.active_connections:
            del self.active_connections[device_id]

    async def send_to_device(self, device_id: str, data: dict):
        ws = self.active_connections.get(device_id)
        if ws:
            await ws.send_json(data)
            return True
        return False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ConnectionManager, cls).__new__(cls)
            cls._instance.active_connections = {}
        return cls._instance

    async def connect(self, device_id: str, websocket: WebSocket):
        self.active_connections[device_id] = websocket

    def disconnect(self, device_id: str):
        self.active_connections.pop(device_id, None)

manager = ConnectionManager()
