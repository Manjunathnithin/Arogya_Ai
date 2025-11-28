# models/schemas.py
from bson import ObjectId
from pydantic import BaseModel, EmailStr
from datetime import datetime, timezone, timedelta # timedelta is required for UserSession

# Constants based on security.py
SESSION_COOKIE_NAME = "session_token"
SESSION_EXPIRATION_MINUTES = 60 * 24 # 24 hours

class UserBase(BaseModel):
    email: EmailStr
    first_name: str
    last_name: str
    user_type: str # 'patient', 'doctor', or 'admin'

class UserCreate(UserBase):
    password: str

class User(UserBase):
    # This is the model returned from the database
    id: str | None = None
    
    class Config:
        from_attributes = True

class UserSession(BaseModel):
    id: str | None = None
    token: str
    user_id: str
    user_type: str
    created_at: datetime = datetime.now(timezone.utc)
    last_active: datetime = datetime.now(timezone.utc)
    # FIX: Use timedelta to add duration, not timezone
    expires_at: datetime = datetime.now(timezone.utc) + timedelta(minutes=SESSION_EXPIRATION_MINUTES)
    
class ChatMessageBase(BaseModel):
    user_query: str
    ai_response: str

class ChatMessage(ChatMessageBase):
    owner_email: str
    timestamp: datetime = datetime.now(timezone.utc)


class ReportBase(BaseModel):
    title: str
    description: str | None = None
    report_type: str # e.g., 'Blood Test', 'MRI Scan', 'Prescription'
    owner_email: EmailStr # Links the report to the user
    upload_date: datetime = datetime.now(timezone.utc)

class Report(ReportBase):
    id: str | None = None
    
    class Config:
        from_attributes = True
        json_encoders = {ObjectId: str}

# Helper for Pydantic/MongoDB
# Pydantic configuration for MongoDB object IDs
class PyObjectId(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate
    
    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return ObjectId(v)
    
    @classmethod
    def __modify_schema__(cls, field_schema):
        field_schema.update(type="string")

# Appointment Models
class AppointmentBase(BaseModel):
    # Subject of the appointment (e.g., "Annual Checkup", "Follow-up on Bloodwork")
    title: str
    
    # ISO 8601 formatted datetime string
    appointment_time: datetime
    
    # Status can be 'scheduled', 'completed', 'cancelled'
    status: str = 'scheduled' 
    
    # Identifier for the Patient
    patient_email: EmailStr
    
    # Identifier for the Doctor/Provider
    doctor_email: EmailStr

class AppointmentCreate(AppointmentBase):
    # When a patient creates an appointment, they only need these fields
    pass

class Appointment(AppointmentBase):
    # Model used when retrieving from the database
    id: str | None = None
    
    class Config:
        from_attributes = True
        json_encoders = {ObjectId: str}

# Connection Models
class ConnectionRequestBase(BaseModel):
    patient_email: EmailStr
    doctor_email: EmailStr
    # Status can be 'pending', 'accepted', 'rejected'
    status: str = 'pending' 
    request_date: datetime = datetime.now(timezone.utc)
    
class ConnectionRequestCreate(ConnectionRequestBase):
    # Only need the doctor's email when creating the request
    doctor_email: EmailStr

class ConnectionRequest(ConnectionRequestBase):
    # Model used when retrieving from the database
    id: str | None = None
    
    class Config:
        from_attributes = True
        json_encoders = {ObjectId: str}