import os
from motor.motor_asyncio import AsyncIOMotorClient

MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://code7lab:XfZOOYjLLN8c4hs2@cluster0.jlosawe.mongodb.net/test?retryWrites=true&w=majority")

DB_NAME = "test"

client = AsyncIOMotorClient(MONGO_URI)
db = client[DB_NAME]

registered_trackers_collection = db["registered_trackers"]
shipment_data_collection = db["Shipment_Data"]
shipment_meta_collection = db["Shipment_Meta"]
