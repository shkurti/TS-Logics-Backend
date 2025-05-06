from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from bson import json_util
from websocket_manager import manager
from database import shipment_data_collection
from routes.tracker_routes import router
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
                        new_record = change["fullDocument"]
                        data_array = new_record.get("data", [])
                        battery = new_record.get("Batt")  # Extract battery level

                        # Broadcast each record in the data array
                        for record in data_array:
                            geolocation = {
                                "Lat": record.get("Lat"),
                                "Lng": record.get("Lng"),
                            } if record else {}

                            # Include battery and timestamp in the broadcast
                            print(f"Broadcasting record for tracker ID {tracker_id}: {record}")  # Log the broadcast
                            await manager.broadcast(json_util.dumps({
                                "operationType": "insert",
                                "tracker_id": tracker_id,
                                "new_record": {
                                    **record,
                                    "battery": battery,  # Include battery level
                                    "timestamp": record.get("DT"),  # Use the record's timestamp
                                },
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
