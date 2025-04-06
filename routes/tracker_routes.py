from fastapi import APIRouter, HTTPException
from bson import json_util
from models import Tracker
from database import registered_trackers_collection
from services.tracker_service import get_combined_tracker_data
from websocket_manager import manager

router = APIRouter()

@router.post("/register_tracker")
async def register_tracker(tracker: Tracker):
    tracker_dict = tracker.dict()
    try:
        # Log the tracker data being inserted
        print(f"Registering tracker with data: {tracker_dict}")
        
        # Insert tracker into the database
        result = await registered_trackers_collection.insert_one(tracker_dict)
        print(f"Tracker inserted with ID: {result.inserted_id}")
        
        # Fetch the combined tracker data
        tracker_data = await get_combined_tracker_data(tracker.tracker_id)
        print(f"Combined tracker data: {tracker_data}")
        
        # Broadcast the new tracker data to WebSocket clients
        if tracker_data:
            try:
                print("Broadcasting tracker data to WebSocket clients...")
                await manager.broadcast(json_util.dumps({"operationType": "insert", "data": tracker_data}))
                print("Broadcast successful.")
            except Exception as e:
                print(f"Error during WebSocket broadcast: {e}")
        
        # Return the combined tracker data
        return {"message": "Tracker registered successfully", "tracker": tracker_data}
    except Exception as e:
        # Log the error and raise an HTTPException
        print(f"Error registering tracker: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to register tracker: {str(e)}")

@router.get("/trackers")
async def get_trackers():
    trackers = []
    async for tracker in registered_trackers_collection.find():
        combined_data = await get_combined_tracker_data(tracker["tracker_id"])
        if combined_data:
            trackers.append(combined_data)
    return trackers

@router.get("/tracker_data/{tracker_id}")
async def get_tracker_data(tracker_id: str):
    try:
        # Fetch the combined tracker data
        tracker_data = await get_combined_tracker_data(tracker_id)
        if not tracker_data:
            raise HTTPException(status_code=404, detail=f"Tracker with ID {tracker_id} not found.")
        return tracker_data
    except Exception as e:
        print(f"Error fetching tracker data for ID {tracker_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.delete("/delete_tracker/{tracker_id}")
async def delete_tracker(tracker_id: str):
    try:
        # Attempt to delete the tracker from the database
        result = await registered_trackers_collection.delete_one({"tracker_id": tracker_id})
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail=f"Tracker with ID {tracker_id} not found.")
        
        # Broadcast the deletion to WebSocket clients
        await manager.broadcast(json_util.dumps({"operationType": "delete", "tracker_id": tracker_id}))
        return {"message": f"Tracker with ID {tracker_id} deleted successfully."}
    except Exception as e:
        print(f"Error deleting tracker with ID {tracker_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
