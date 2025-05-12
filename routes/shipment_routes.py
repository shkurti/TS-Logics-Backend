from fastapi import APIRouter, HTTPException
from database import shipment_meta_collection

router = APIRouter()

@router.post("/shipment_meta")
async def insert_shipment_meta(data: dict):
    try:
        # Log the incoming data for debugging
        print(f"Received shipment data: {data}")  # Debugging log

        # Validate and process each leg
        for leg in data.get("legs", []):
            if not all(key in leg for key in ["shipFromAddress", "shipDate", "mode", "carrier", "stopAddress", "arrivalDate", "departureDate"]):
                raise HTTPException(status_code=400, detail="Missing required fields in one or more legs.")
            print(f"Processing leg: {leg}")  # Debugging log

        # Insert the shipment data into the Shipment_Meta collection
        result = await shipment_meta_collection.insert_one(data)
        print(f"Inserted shipment data with ID: {result.inserted_id}")  # Debugging log
        return {"message": "Shipment data inserted successfully", "id": str(result.inserted_id)}
    except Exception as e:
        print(f"Error inserting shipment data: {e}")
        raise HTTPException(status_code=500, detail="Failed to insert shipment data")
