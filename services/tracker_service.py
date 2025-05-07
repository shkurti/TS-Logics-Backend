from database import registered_trackers_collection, shipment_data_collection

async def get_combined_tracker_data(tracker_id: str):
    try:
        # Convert tracker_id to a string for querying registered_trackers_collection
        tracker_id_str = str(tracker_id)

        # Fetch tracker details from registered_trackers
        tracker = await registered_trackers_collection.find_one({"tracker_id": tracker_id_str})
        if not tracker:
            print(f"Tracker with ID {tracker_id} not found in registered_trackers_collection.")
            return None

        # Convert tracker_id to an integer for querying Shipment_Data
        try:
            tracker_id_int = int(tracker_id)
        except ValueError:
            print(f"Tracker ID {tracker_id} is not a valid integer.")
            return None

        # Fetch all documents for the tracker from Shipment_Data
        shipment_documents = []
        async for document in shipment_data_collection.find({"trackerID": tracker_id_int}):
            shipment_documents.append(document)

        if not shipment_documents:
            print(f"No shipment data found for tracker ID {tracker_id_int}.")
            return None

        # Process all documents to extract nested 'data' arrays
        historical_data = []
        for shipment_data in shipment_documents:
            nested_data = shipment_data.get("data", [])
            for record in nested_data:
                if record.get("Lat") is not None and record.get("Lng") is not None:
                    historical_data.append({
                        "timestamp": record.get("DT", "N/A"),
                        "latitude": record.get("Lat"),
                        "longitude": record.get("Lng"),
                        "temperature": record.get("Temp", "N/A"),
                        "humidity": record.get("Hum", "N/A"),
                        "speed": record.get("Speed", "N/A"),
                        "battery": record.get("Batt", "N/A"),
                    })

        # Combine data
        latest_shipment = shipment_documents[-1] if shipment_documents else {}
        latest_data = latest_shipment.get("data", [{}])[-1] if latest_shipment.get("data") else {}

        combined_data = {
            "tracker_id": tracker["tracker_id"],
            "tracker_name": tracker["tracker_name"],
            "device_type": tracker["device_type"],
            "model_number": tracker["model_number"],
            "batteryLevel": latest_shipment.get("Batt", "N/A"),  # Extract battery level from the latest shipment
            "lastConnected": latest_data.get("DT", "N/A"),  # Extract last connected time from the latest data
            "location": f"{latest_data.get('Lat', 'N/A')}, {latest_data.get('Lng', 'N/A')}",  # Extract location from the latest data
            "data": historical_data  # Add processed nested data
        }
        print(f"Combined data for tracker ID {tracker_id}: {combined_data}")
        return combined_data
    except Exception as e:
        print(f"Error in get_combined_tracker_data: {e}")
        return None
