from fastapi import APIRouter, HTTPException, Request, Query
from database import shipment_meta_collection, shipment_data_collection
from datetime import datetime
from dateutil import parser as date_parser

router = APIRouter()

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
    start: str = Query(...),  # ISO format string
    end: str = Query(...),    # ISO format string
):
    try:
        # Convert tracker_id to int for Shipment_Data collection
        try:
            tracker_id_int = int(tracker_id)
        except ValueError:
            return []

        # Parse start and end to datetime
        start_dt = date_parser.parse(start)
        end_dt = date_parser.parse(end)

        shipment_records = []
        async for doc in shipment_data_collection.find({"trackerID": tracker_id_int}):
            for record in doc.get("data", []):
                dt_str = record.get("DT")
                if not dt_str:
                    continue
                try:
                    # Parse the DT string in the data (format: "2025-5-3 14:40:57")
                    dt = date_parser.parse(dt_str)
                except Exception:
                    continue
                if start_dt <= dt <= end_dt:
                    shipment_records.append({
                        "timestamp": dt_str,
                        "latitude": record.get("Lat"),
                        "longitude": record.get("Lng"),
                        "temperature": record.get("Temp"),
                        "humidity": record.get("Hum"),
                        "speed": record.get("Speed"),
                        "battery": doc.get("Batt"),
                    })
        # Sort by timestamp
        shipment_records.sort(key=lambda x: date_parser.parse(x["timestamp"]))
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
