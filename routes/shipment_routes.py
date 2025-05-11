from fastapi import APIRouter, HTTPException
from database import shipment_meta_collection

router = APIRouter()

@router.post("/shipment_meta")
async def insert_shipment_meta(data: dict):
    try:
        # Log the incoming data for debugging
        print(f"Received shipment data: {data}")  # Debugging log

        # Check if shipDate and arrivalDate are properly formatted
        for leg in data.get("legs", []):
            print(f"Leg shipDate: {leg.get('shipDate')}, arrivalDate: {leg.get('arrivalDate')}")

        # Log the formatted legs data
        formattedLegs = [{"shipDate": leg.get("shipDate"), "arrivalDate": leg.get("arrivalDate")} for leg in data.get("legs", [])]
        print(f"Formatted legs data: {formattedLegs}")

        # Insert the shipment data into the Shipment_Meta collection
        result = await shipment_meta_collection.insert_one(data)
        return {"message": "Shipment data inserted successfully", "id": str(result.inserted_id)}
    except Exception as e:
        print(f"Error inserting shipment data: {e}")
        raise HTTPException(status_code=500, detail="Failed to insert shipment data")
