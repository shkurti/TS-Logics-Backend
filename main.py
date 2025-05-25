from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from bson import json_util
from websocket_manager import manager
from database import shipment_data_collection
from routes.tracker_routes import router
from routes.shipment_routes import router as shipment_router
from services.tracker_service import get_combined_tracker_data

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://ui-ts-logic-2ba3bbfcc572.herokuapp.com"],  # Ensure this matches your frontend's URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
app.include_router(shipment_router)

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
                        # Only broadcast the new record(s) from the inserted document
                        new_data = change["fullDocument"].get("data", [])
                        for record in new_data:
                            # Store real-time data for persistence
                            await manager.store_realtime_data(tracker_id, record)
                            
                            geolocation = {
                                "Lat": record.get("Lat"),
                                "Lng": record.get("Lng"),
                            } if record else {}

                            print(f"Broadcasting ONLY new record for tracker ID {tracker_id}: {record}")  # Log the broadcast
                            await manager.broadcast(json_util.dumps({
                                "operationType": "insert",
                                "tracker_id": tracker_id,
                                "new_record": record,
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
