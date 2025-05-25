from fastapi import WebSocket, WebSocketDisconnect
from database import shipment_data_collection
from datetime import datetime

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []
        self.shipment_realtime_data = {}  # Store real-time data per shipment

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

    async def store_realtime_data(self, tracker_id: int, data: dict):
        """Store real-time data for persistence"""
        try:
            # Store in MongoDB for persistence
            await shipment_data_collection.update_one(
                {"trackerID": tracker_id},
                {
                    "$push": {
                        "realtime_data": {
                            **data,
                            "received_at": datetime.utcnow().isoformat()
                        }
                    }
                },
                upsert=True
            )
            print(f"Stored real-time data for tracker {tracker_id}")
        except Exception as e:
            print(f"Error storing real-time data: {e}")

    async def get_shipment_realtime_data(self, tracker_id: int):
        """Retrieve stored real-time data for a shipment"""
        try:
            result = await shipment_data_collection.find_one(
                {"trackerID": tracker_id},
                {"realtime_data": 1}
            )
            return result.get("realtime_data", []) if result else []
        except Exception as e:
            print(f"Error retrieving real-time data: {e}")
            return []

manager = ConnectionManager()
