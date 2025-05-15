from fastapi import APIRouter, HTTPException, Request
from database import shipment_meta_collection
from datetime import datetime

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
