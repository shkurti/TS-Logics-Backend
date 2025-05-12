from fastapi import APIRouter, HTTPException, Request
from database import shipment_meta_collection

router = APIRouter()

@router.post("/shipment_meta")
async def insert_shipment_meta(request: Request):
    try:
        data = await request.json()
        print(f"Received shipment data: {data}")  # Debugging log

        for i, leg in enumerate(data.get("legs", [])):
            required_fields = ["shipDate", "mode", "carrier", "arrivalDate", "departureDate"]
            if i == 0:
                required_fields.append("shipFromAddress")  # First leg requires Ship From Address
            required_fields.append("stopAddress")  # All legs require Stop Address (or Ship To Address for the last leg)

            if not all(key in leg and leg[key] for key in required_fields):
                print(f"Validation failed for leg {i + 1}: {leg}")  # Debugging log
                raise HTTPException(status_code=400, detail="Missing required fields in one or more legs.")

        result = await shipment_meta_collection.insert_one(data)
        print(f"Inserted shipment data with ID: {result.inserted_id}")  # Debugging log
        return {"message": "Shipment data inserted successfully", "id": str(result.inserted_id)}
    except Exception as e:
        print(f"Error inserting shipment data: {e}")
        raise HTTPException(status_code=500, detail="Failed to insert shipment data")
