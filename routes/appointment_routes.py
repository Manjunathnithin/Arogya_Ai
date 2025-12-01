# routes/appointment_routes.py

from fastapi import APIRouter, Depends, HTTPException, status, Query, Path, Body # Added Body
from pydantic import BaseModel
from typing import List, Optional
from database import appointments_collection
from models.schemas import Appointment, AppointmentCreate, User
from security import get_current_authenticated_user
from bson import ObjectId

router = APIRouter()

# Schema for updating appointment status and/or meeting link
class AppointmentUpdate(BaseModel):
    status: Optional[str] = None
    meeting_link: Optional[str] = None 

@router.post("/", response_model=Appointment, status_code=status.HTTP_201_CREATED)
async def schedule_appointment(
    appointment_data: AppointmentCreate,
    current_user: User = Depends(get_current_authenticated_user)
):
    """Allows a patient to schedule an appointment with a doctor."""
    
    if current_user.user_type != 'patient':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Only patients can initiate appointment scheduling."
        )

    appointment_dict = appointment_data.model_dump()
    appointment_dict["patient_email"] = current_user.email
    appointment_dict["status"] = "scheduled" 
    appointment_dict["meeting_link"] = None 
    
    try:
        result = await appointments_collection.insert_one(appointment_dict)
        appointment_dict["id"] = str(result.inserted_id)
        
        return Appointment(**appointment_dict)
        
    except Exception as e:
        print(f"Appointment scheduling error: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to schedule appointment.")


@router.put("/{appointment_id}", response_model=Appointment)
async def update_appointment(
    # 1. Path Parameter (Has default, so subsequent params must have default)
    appointment_id: str = Path(..., description="The ObjectId of the appointment to update."),
    
    # 2. Body Parameter (FIX: Use Body(...) to give it a default value)
    update_data: AppointmentUpdate = Body(...), 
    
    # 3. Dependency Parameter (Has default, placed last)
    current_user: User = Depends(get_current_authenticated_user)
):
    """
    Allows a doctor to update the status or meeting link of an appointment they own.
    """
    if current_user.user_type != 'doctor':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Only the doctor can update appointment details."
        )
        
    update_fields = {}
    
    # 1. Handle Status Update if provided
    if update_data.status:
        new_status = update_data.status.lower()
        allowed_statuses = {"scheduled", "completed", "cancelled"}
        if new_status not in allowed_statuses:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid status: Must be one of {list(allowed_statuses)}")
        update_fields["status"] = new_status
        
    # 2. Handle Meeting Link Update if provided (or explicitly set to None)
    if update_data.meeting_link is not None:
        update_fields["meeting_link"] = update_data.meeting_link
    
    if not update_fields:
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields provided for update.")

    try:
        # Find the appointment, ensuring it belongs to the authenticated doctor
        update_result = await appointments_collection.find_one_and_update(
            {"_id": ObjectId(appointment_id), "doctor_email": current_user.email},
            {"$set": update_fields},
            return_document=True
        )
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid Appointment ID format.")

    if not update_result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found or not owned by doctor.")
    
    update_result['id'] = str(update_result['_id'])
    
    return Appointment(**update_result)


@router.get("/", response_model=List[Appointment])
async def list_user_appointments(
    status_filter: str = Query(None, description="Filter by status (scheduled, completed, cancelled)"),
    current_user: User = Depends(get_current_authenticated_user)
):
    """Retrieves appointments relevant to the current authenticated user (patient or doctor)."""
    
    query_filter = {}
    
    if current_user.user_type == 'patient':
        query_filter["patient_email"] = current_user.email
    elif current_user.user_type == 'doctor':
        query_filter["doctor_email"] = current_user.email
    
    if status_filter:
        query_filter["status"] = status_filter.lower()
        
    cursor = appointments_collection.find(query_filter).sort("appointment_time", 1)
    
    appointments_list = await cursor.to_list(length=100)
    
    for appointment in appointments_list:
        if '_id' in appointment:
            appointment['id'] = str(appointment['_id'])
            
    return [Appointment(**appointment) for appointment in appointments_list]