from fastapi import APIRouter, HTTPException, Request, Query
from database import shipment_meta_collection, shipment_data_collection
from datetime import datetime
from dateutil import parser as date_parser
import pytz
from typing import Optional

router = APIRouter()

def convert_utc_to_local(utc_time_str: str, local_timezone: str = "America/New_York") -> str:
    """
    Convert UTC timestamp string to local timezone
    """
    try:
        # Parse the UTC timestamp
        utc_dt = date_parser.parse(utc_time_str)
        
        # If the datetime is naive (no timezone info), assume it's UTC
        if utc_dt.tzinfo is None:
            utc_dt = pytz.utc.localize(utc_dt)
        else:
            # Convert to UTC if it has timezone info
            utc_dt = utc_dt.astimezone(pytz.utc)
        
        # Convert to local timezone
        local_tz = pytz.timezone(local_timezone)
        local_dt = utc_dt.astimezone(local_tz)
        
        # Return as string in the same format
        return local_dt.strftime("%Y-%m-%d %H:%M:%S")
    except Exception as e:
        print(f"Error converting timezone for {utc_time_str}: {e}")
        return utc_time_str  # Return original if conversion fails

def convert_local_to_utc(local_time_str: str, local_timezone: str = "America/New_York") -> datetime:
    """
    Convert local time string to UTC datetime for database queries
    """
    try:
        # Parse the local time
        local_dt = date_parser.parse(local_time_str)
        
        # If naive, localize to the specified timezone
        if local_dt.tzinfo is None:
            local_tz = pytz.timezone(local_timezone)
            local_dt = local_tz.localize(local_dt)
        
        # Convert to UTC
        utc_dt = local_dt.astimezone(pytz.utc)
        return utc_dt
    except Exception as e:
        print(f"Error converting local time to UTC for {local_time_str}: {e}")
        raise HTTPException(status_code=400, detail=f"Invalid datetime format: {local_time_str}")

@router.post("/shipment_meta")
async def insert_shipment_meta(request: Request):
    try:
        data = await request.json()
        print(f"Received shipment data: {data}")  # Debugging log

        # Validate trackerId
        if "trackerId" not in data or not data["trackerId"]:
            raise HTTPException(status_code=400, detail="Missing trackerId.")

        for i, leg in enumerate(data.get("legs", [])):
            required_fields = ["shipDate", "mode", "carrier", "arrivalDate", "departureDate"]
            if i == 0:
                required_fields.append("shipFromAddress")  # First leg requires Ship From Address
            required_fields.append("stopAddress")  # All legs require Stop Address (or Ship To Address for the last leg)

            if not all(key in leg and leg[key] for key in required_fields):
                print(f"Validation failed for leg {i + 1}: {leg}")  # Debugging log
                raise HTTPException(status_code=400, detail="Missing required fields in one or more legs.")

            # Validate datetime fields
            for field in ["shipDate", "arrivalDate", "departureDate"]:
                try:
                    datetime.fromisoformat(leg[field])  # Validate ISO 8601 format
                except ValueError:
                    raise HTTPException(status_code=400, detail=f"Invalid datetime format for {field} in leg {i + 1}.")

        result = await shipment_meta_collection.insert_one(data)
        print(f"Inserted shipment data with ID: {result.inserted_id}")  # Debugging log
        return {"message": "Shipment data inserted successfully", "id": str(result.inserted_id)}
    except Exception as e:
        print(f"Error inserting shipment data: {e}")
        raise HTTPException(status_code=500, detail="Failed to insert shipment data")

@router.get("/shipment_meta")
async def get_all_shipments():
    try:
        shipments = []
        async for shipment in shipment_meta_collection.find():
            shipment["_id"] = str(shipment["_id"])  # Convert ObjectId to string
            shipment["legs"] = shipment.get("legs", [])  # Ensure legs is always present
            shipments.append(shipment)
        return shipments
    except Exception as e:
        print(f"Error fetching shipments: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch shipments.")

@router.get("/shipment_route_data")
async def get_shipment_route_data(
    tracker_id: str = Query(...),
    start: str = Query(...),  # Local time ISO format string
    end: str = Query(...),    # Local time ISO format string
    timezone: str = Query("America/New_York", description="Client timezone (e.g., 'America/New_York', 'America/Los_Angeles')")
):
    try:
        # Convert tracker_id to int for Shipment_Data collection
        try:
            tracker_id_int = int(tracker_id)
        except ValueError:
            return []

        # Convert local time inputs to UTC for database query
        start_utc = convert_local_to_utc(start, timezone)
        end_utc = convert_local_to_utc(end, timezone)

        print(f"Querying data from {start_utc} UTC to {end_utc} UTC (converted from local times {start} to {end} in {timezone})")

        shipment_records = []
        async for doc in shipment_data_collection.find({"trackerID": tracker_id_int}):
            for record in doc.get("data", []):
                dt_str = record.get("DT")
                if not dt_str:
                    continue
                try:
                    # Parse the UTC timestamp from database
                    dt_utc = date_parser.parse(dt_str)
                    
                    # If naive, assume UTC
                    if dt_utc.tzinfo is None:
                        dt_utc = pytz.utc.localize(dt_utc)
                    
                    # Check if the UTC time falls within our UTC range
                    if start_utc <= dt_utc <= end_utc:
                        # Convert UTC timestamp to local time for response
                        local_timestamp = convert_utc_to_local(dt_str, timezone)
                        
                        shipment_records.append({
                            "timestamp": local_timestamp,  # Return in local time
                            "timestamp_utc": dt_str,       # Also provide UTC for reference
                            "latitude": record.get("Lat"),
                            "longitude": record.get("Lng"),
                            "temperature": record.get("Temp"),
                            "humidity": record.get("Hum"),
                            "speed": record.get("Speed"),
                            "battery": doc.get("Batt"),
                        })
                except Exception as e:
                    print(f"Error processing timestamp {dt_str}: {e}")
                    continue
        
        # Sort by UTC timestamp to maintain proper order
        shipment_records.sort(key=lambda x: date_parser.parse(x["timestamp_utc"]))
        
        print(f"Found {len(shipment_records)} records for tracker {tracker_id} in the specified time range")
        return shipment_records
    except Exception as e:
        print(f"Error in get_shipment_route_data: {e}")
        return []

@router.delete("/shipment_meta/{shipment_id}")
async def delete_shipment_meta(shipment_id: str):
    from bson import ObjectId
    try:
        result = await shipment_meta_collection.delete_one({"_id": ObjectId(shipment_id)})
        if result.deleted_count == 1:
            return {"message": "Shipment deleted successfully"}
        else:
            raise HTTPException(status_code=404, detail="Shipment not found")
    except Exception as e:
        print(f"Error deleting shipment: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete shipment")
