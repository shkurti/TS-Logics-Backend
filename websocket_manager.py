from fastapi import WebSocket, WebSocketDisconnect

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        print(f"WebSocket connected: {websocket.client}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            print(f"WebSocket disconnected: {websocket.client}")

    async def broadcast(self, message: str):
        print(f"Broadcasting message to {len(self.active_connections)} WebSocket clients...")
        for connection in self.active_connections[:]:  # Iterate over a copy of the list
            try:
                await connection.send_text(message)
            except Exception as e:
                print(f"Error sending message to WebSocket client: {e}")
                self.disconnect(connection)  # Remove the connection if sending fails

manager = ConnectionManager()
