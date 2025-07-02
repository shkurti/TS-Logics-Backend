from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from bson import json_util
from websocket_manager import manager
from database import shipment_data_collection
from routes.tracker_routes import router
from routes.shipment_routes import router as shipment_router
from services.tracker_service import get_combined_tracker_data
import pytz
from datetime import datetime
from dateutil import parser as date_parser
import os

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://ui-ts-988f3aaae0ba.herokuapp.com"],  # Ensure this matches your frontend's URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
app.include_router(shipment_router)

def convert_utc_to_local_for_websocket(utc_time_str: str, local_timezone: str = "America/New_York") -> dict:
    """
    Convert UTC timestamp to local time and return both for WebSocket broadcast
    """
    try:
        utc_dt = date_parser.parse(utc_time_str)
        if utc_dt.tzinfo is None:
            utc_dt = pytz.utc.localize(utc_dt)
        
        local_tz = pytz.timezone(local_timezone)
        local_dt = utc_dt.astimezone(local_tz)
        
        return {
            "timestamp_utc": utc_time_str,
            "timestamp_local": local_dt.strftime("%Y-%m-%d %H:%M:%S"),
            "timezone": local_timezone
        }
    except Exception as e:
        print(f"Error converting timezone for WebSocket: {e}")
        return {"timestamp_utc": utc_time_str, "timestamp_local": utc_time_str, "timezone": "UTC"}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    print(f"WebSocket handler started in process {os.getpid()}")
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
                            geolocation = {
                                "Lat": record.get("Lat"),
                                "Lng": record.get("Lng"),
                            } if record else {}

                            # Convert timestamp to include both UTC and local time
                            timestamp_info = convert_utc_to_local_for_websocket(
                                record.get("DT", ""), 
                                "America/New_York"  # Default timezone, could be made configurable
                            )
                            
                            # Add timezone info to the record
                            enhanced_record = {
                                **record,
                                **timestamp_info
                            }

                            print(f"Broadcasting new record with timezone info for tracker ID {tracker_id}")  # Log the broadcast
                            print(f"Broadcasting message to {len(manager.active_connections)} WebSocket clients...")
                            await manager.broadcast(json_util.dumps({
                                "operationType": "insert",
                                "tracker_id": tracker_id,
                                "new_record": enhanced_record,
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
