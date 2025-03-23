from pydantic import BaseModel

class Tracker(BaseModel):
    tracker_name: str
    tracker_id: str
    device_type: str
    model_number: str
