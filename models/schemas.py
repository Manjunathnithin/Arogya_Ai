# models/schemas.py
from bson import ObjectId
from pydantic import BaseModel, EmailStr
from datetime import datetime, timezone, timedelta 

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
    expires_at: datetime = datetime.now(timezone.utc) + timedelta(minutes=SESSION_EXPIRATION_MINUTES)
    
class ChatMessageBase(BaseModel):
    user_query: str
    ai_response: str

class ChatMessage(ChatMessageBase):
    owner_email: str
    timestamp: datetime = datetime.now(timezone.utc)

# --- REPORT MODELS (UPDATED) ---

# 1. Model for CREATING a report (What the frontend sends)
class ReportCreate(BaseModel):
    title: str
    description: str | None = None
    report_type: str # e.g., 'Blood Test', 'MRI Scan', 'Prescription'

# 2. Model for DATABASE/READING (Includes system fields like email/date)
class ReportBase(ReportCreate):
    owner_email: EmailStr 
    upload_date: datetime = datetime.now(timezone.utc)

class Report(ReportBase):
    id: str | None = None
    
    class Config:
        from_attributes = True
        json_encoders = {ObjectId: str}

# Helper for Pydantic/MongoDB
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
    title: str
    appointment_time: datetime
    status: str = 'scheduled' 
    patient_email: EmailStr
    doctor_email: EmailStr

class AppointmentCreate(AppointmentBase):
    pass

class Appointment(AppointmentBase):
    id: str | None = None
    
    class Config:
        from_attributes = True
        json_encoders = {ObjectId: str}

# Connection Models
class ConnectionRequestBase(BaseModel):
    patient_email: EmailStr
    doctor_email: EmailStr
    status: str = 'pending' 
    request_date: datetime = datetime.now(timezone.utc)
    
class ConnectionRequestCreate(ConnectionRequestBase):
    doctor_email: EmailStr

class ConnectionRequest(ConnectionRequestBase):
    id: str | None = None
    
    class Config:
        from_attributes = True
        json_encoders = {ObjectId: str}