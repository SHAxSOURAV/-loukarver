from typing import Dict, Set
from collections import defaultdict
from fastapi import WebSocket
from fastapi.encoders import jsonable_encoder

class ConnectionManager:
    def __init__(self):
        # Maps user_id to a set of active WebSockets for that user
        self.active_connections: Dict[str, Set[WebSocket]] = defaultdict(set)

    async def connect(self, user_id: str, websocket: WebSocket):
        await websocket.accept()
        uid = str(user_id)
        self.active_connections[uid].add(websocket)
        print(f"WS CONNECTED for user_id {uid}. Total connections for user: {len(self.active_connections[uid])}")

    def disconnect(self, user_id: str, websocket: WebSocket):
        uid = str(user_id)
        if uid in self.active_connections:
            self.active_connections[uid].discard(websocket)
            if not self.active_connections[uid]:
                del self.active_connections[uid]
        print(f"WS DISCONNECTED for user_id {uid}")

    async def broadcast_to_user(self, user_id: str, message: dict):
        uid = str(user_id)
        if uid in self.active_connections:
            sockets = list(self.active_connections[uid])
            print(f"WS BROADCAST -> {uid} ({len(sockets)} sockets): {message.get('type')}")
            try:
                encoded_message = jsonable_encoder(message)
                for websocket in sockets:
                    try:
                        await websocket.send_json(encoded_message)
                    except Exception as e:
                        print(f"WS SEND ERROR to {uid}: {e}")
                        self.disconnect(uid, websocket)
            except Exception as enc_err:
                print(f"WS ENCODING ERROR for user {uid}: {enc_err}")
        else:
            print(f"WS BROADCAST SKIPPED -> {uid} not connected. Connected users: {list(self.active_connections.keys())}")

ws_manager = ConnectionManager()
