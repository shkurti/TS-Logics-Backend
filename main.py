from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from bson import json_util  # Added missing import for json_util
from websocket_manager import manager
from database import shipment_data_collection
from routes.tracker_routes import router
from services.tracker_service import get_combined_tracker_data  # Added missing import for get_combined_tracker_data

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://frontend-ts-860909b3c437.herokuapp.com"],  # Ensure this matches your frontend's URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        async with shipment_data_collection.watch() as stream:
            async for change in stream:
                print(f"Change detected in Shipment_Data: {change}")  # Log the change
                if change["operationType"] == "insert":
                    tracker_id = change["fullDocument"].get("trackerID")
                    if tracker_id:
                        tracker_data = await get_combined_tracker_data(tracker_id)
                        if tracker_data:
                            # Include geolocation data in the broadcast
                            geolocation = {
                                "Lat": change["fullDocument"].get("Lat"),
                                "Lng": change["fullDocument"].get("Lng"),
                            }
                            print(f"Broadcasting updated tracker data: {tracker_data}")  # Log the broadcast
                            await manager.broadcast(json_util.dumps({
                                "operationType": "insert",
                                "data": tracker_data,
                                "geolocation": geolocation
                            }))
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        print("WebSocket client disconnected.")
    except Exception as e:
        print(f"Error in WebSocket endpoint: {e}")
    finally:
        manager.disconnect(websocket)  # Ensure the connection is removed in all cases

@app.on_event("startup")
async def startup_event():
    print("WebSocket and MongoDB Change Stream are running.")
