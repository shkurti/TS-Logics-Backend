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

        # Fetch the latest tracker data from Shipment_Data
        shipment_data = await shipment_data_collection.find_one(
            {"trackerID": tracker_id_int},
            sort=[("DT", -1)]  # Sort by DT (timestamp) in descending order
        )
        if not shipment_data:
            print(f"Shipment data for tracker ID {tracker_id_int} not found in shipment_data_collection.")
            return None

        # Fetch historical data for temperature, battery level, and geolocation
        historical_data = []
        async for record in shipment_data_collection.find(
            {"trackerID": tracker_id_int},
            sort=[("DT", 1)]  # Sort by DT (timestamp) in ascending order
        ):
            if record.get("Lat") is not None and record.get("Lng") is not None:
                historical_data.append({
                    "timestamp": record.get("DT", "N/A"),
                    "latitude": record.get("Lat"),
                    "longitude": record.get("Lng"),
                    "temperature": record.get("Temp", "N/A"),
                    "battery": record.get("Batt", "N/A"),
                    "humidity": record.get("Hum", "N/A")
                })

        # Combine data
        combined_data = {
            "tracker_id": tracker["tracker_id"],
            "tracker_name": tracker["tracker_name"],
            "device_type": tracker["device_type"],
            "model_number": tracker["model_number"],
            "batteryLevel": shipment_data.get("Batt", "N/A"),
            "lastConnected": shipment_data.get("DT", "N/A"),
            "location": f"{shipment_data.get('Lat', 'N/A')}, {shipment_data.get('Lng', 'N/A')}",
            "historical_data": historical_data  # Add historical data with geolocation
        }
        print(f"Combined data for tracker ID {tracker_id}: {combined_data}")
        return combined_data
    except Exception as e:
        print(f"Error in get_combined_tracker_data: {e}")
        return None
