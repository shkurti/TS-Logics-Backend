from database import registered_trackers_collection, shipment_data_collection
import pytz
from dateutil import parser as date_parser

def convert_utc_to_local_service(utc_time_str: str, local_timezone: str = "America/New_York") -> str:
    """
    Convert UTC timestamp to local timezone for service responses
    """
    try:
        utc_dt = date_parser.parse(utc_time_str)
        if utc_dt.tzinfo is None:
            utc_dt = pytz.utc.localize(utc_dt)
        
        local_tz = pytz.timezone(local_timezone)
        local_dt = utc_dt.astimezone(local_tz)
        return local_dt.strftime("%Y-%m-%d %H:%M:%S")
    except Exception as e:
        print(f"Error converting timezone in service: {e}")
        return utc_time_str

async def get_combined_tracker_data(tracker_id: str, timezone: str = "America/New_York"):
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

        # Process all documents with timezone conversion
        historical_data = []
        for shipment_data in shipment_documents:
            nested_data = shipment_data.get("data", [])
            for record in nested_data:
                if record.get("Lat") is not None and record.get("Lng") is not None:
                    utc_timestamp = record.get("DT", "N/A")
                    local_timestamp = convert_utc_to_local_service(utc_timestamp, timezone) if utc_timestamp != "N/A" else "N/A"
                    
                    historical_data.append({
                        "timestamp": local_timestamp,  # Local time
                        "timestamp_utc": utc_timestamp,  # UTC time for reference
                        "latitude": record.get("Lat"),
                        "longitude": record.get("Lng"),
                        "temperature": record.get("Temp", "N/A"),
                        "humidity": record.get("Hum", "N/A"),
                        "speed": record.get("Speed", "N/A"),
                        "battery": record.get("Batt", "N/A"),  # Fixed: Get battery from individual record
                    })

        # Combine data
        latest_shipment = shipment_documents[-1] if shipment_documents else {}
        latest_data = latest_shipment.get("data", [{}])[-1] if latest_shipment.get("data") else {}

        # Get battery level from the latest data record, not document level
        battery_level = latest_data.get("Batt", "N/A")

        # Convert last connected time to local timezone
        last_connected_utc = latest_data.get("DT", "N/A")
        last_connected_local = convert_utc_to_local_service(last_connected_utc, timezone) if last_connected_utc != "N/A" else "N/A"

        combined_data = {
            "tracker_id": tracker["tracker_id"],
            "tracker_name": tracker["tracker_name"],
            "device_type": tracker["device_type"],
            "model_number": tracker["model_number"],
            "batteryLevel": battery_level,  # Fixed: Get from latest data record
            "lastConnected": last_connected_local,  # Local time
            "lastConnected_utc": last_connected_utc,  # UTC for reference
            "location": f"{latest_data.get('Lat', 'N/A')}, {latest_data.get('Lng', 'N/A')}",  # Extract location from the latest data
            "data": historical_data,  # Add processed nested data
            "timezone": timezone  # Include timezone info in response
        }
        
        print(f"Combined data for tracker ID {tracker_id} in timezone {timezone}")
        return combined_data
    except Exception as e:
        print(f"Error in get_combined_tracker_data: {e}")
        return None
