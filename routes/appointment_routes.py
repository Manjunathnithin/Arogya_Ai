# routes/appointment_routes.py
from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List
from database import appointments_collection
from models.schemas import Appointment, AppointmentCreate, User
from security import get_current_authenticated_user

router = APIRouter()

@router.post("/", response_model=Appointment, status_code=status.HTTP_201_CREATED)
async def schedule_appointment(
    appointment_data: AppointmentCreate,
    current_user: User = Depends(get_current_authenticated_user)
):
    """
    Allows a patient to schedule an appointment with a doctor.
    NOTE: In a real app, you would add logic here to verify the doctor exists.
    """
    
    if current_user.user_type != 'patient':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Only patients can initiate appointment scheduling."
        )

    # Ensure the patient email in the payload matches the current user
    appointment_data.patient_email = current_user.email
    
    appointment_dict = appointment_data.model_dump(exclude={'id'})
    
    try:
        result = await appointments_collection.insert_one(appointment_dict)
        appointment_dict["id"] = str(result.inserted_id)
        
        # Return the created appointment object
        return Appointment(**appointment_dict)
        
    except Exception as e:
        print(f"Appointment scheduling error: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to schedule appointment.")


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
    
    # Map MongoDB '_id' to Pydantic 'id'
    for appointment in appointments_list:
        if '_id' in appointment:
            appointment['id'] = str(appointment['_id'])
            
    return [Appointment(**appointment) for appointment in appointments_list]


# NOTE: You would typically add PUT routes for updating status (e.g., doctor confirming appointment).

