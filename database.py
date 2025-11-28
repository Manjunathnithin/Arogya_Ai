# database.py

from motor.motor_asyncio import AsyncIOMotorClient 
import os
import certifi  # <--- Import this
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI") 
if not MONGO_URI:
    # IMPORTANT: This exception will be raised if .env is missing or MONGO_URI is empty
    raise ValueError("MONGO_URI not found in .env file.")

# <--- Add tlsCAFile=certifi.where() to the constructor
client = AsyncIOMotorClient(
    MONGO_URI, 
    serverSelectionTimeoutMS=5000,
    tlsCAFile=certifi.where() 
)

db = client.aarogyadb 

# Correct collection definitions (user_collection was the missing piece)
user_collection = db.users
sessions_collection = db.sessions 
chat_messages_collection = db.chat_messages
reports_collection = db.reports
connection_requests_collection = db.connection_requests
appointments_collection = db.appointments
medical_records_collection = db.medical_records
report_contents_collection = db.report_contents