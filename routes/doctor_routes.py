# routes/doctor_routes.py

from fastapi import APIRouter, Depends, HTTPException, status, Path
from typing import List, Dict, Any, Optional

from database import connection_requests_collection, reports_collection, appointments_collection
from models.schemas import User, Report, Appointment, ConnectionRequest
from security import get_current_authenticated_user

router = APIRouter()

# --- Helper Function ---
async def check_doctor_permission(current_user: User):
    """Ensures the authenticated user is a doctor."""
    if current_user.user_type != 'doctor':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Only doctors can access this resource."
        )

# --- Core Doctor Endpoints ---

@router.get("/patients", response_model=List[str])
async def list_connected_patients(
    current_user: User = Depends(get_current_authenticated_user)
):
    """
    Retrieves a list of email addresses of all patients who have an 'accepted' 
    connection request with the authenticated doctor.
    """
    await check_doctor_permission(current_user)

    # Find all accepted connection requests for the current doctor
    cursor = connection_requests_collection.find({
        "doctor_email": current_user.email,
        "status": "accepted"
    }, {"patient_email": 1, "_id": 0}) # Project only the patient_email field

    # Extract emails from the results
    patients_list = await cursor.to_list(length=1000)
    
    return [patient['patient_email'] for patient in patients_list]


async def check_patient_connection(doctor_email: str, patient_email: str) -> bool:
    """Verifies if the doctor is currently connected (status: accepted) to the patient."""
    connection = await connection_requests_collection.find_one({
        "doctor_email": doctor_email,
        "patient_email": patient_email,
        "status": "accepted"
    })
    return connection is not None


@router.get("/patients/{patient_email}/reports", response_model=List[Report])
async def get_patient_reports(
    patient_email: str = Path(..., description="Email of the connected patient."),
    current_user: User = Depends(get_current_authenticated_user)
):
    """Retrieves all reports for a specific connected patient."""
    await check_doctor_permission(current_user)

    # 1. Verify connection authorization
    if not await check_patient_connection(current_user.email, patient_email):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to view reports for this patient."
        )

    # 2. Fetch reports
    cursor = reports_collection.find({"owner_email": patient_email}).sort("upload_date", -1)
    reports_list = await cursor.to_list(length=100)
    
    # Map MongoDB '_id' to Pydantic 'id'
    for report in reports_list:
        if '_id' in report:
            report['id'] = str(report['_id'])
            
    return [Report(**report) for report in reports_list]


@router.get("/patients/{patient_email}/appointments", response_model=List[Appointment])
async def get_patient_appointments(
    patient_email: str = Path(..., description="Email of the connected patient."),
    current_user: User = Depends(get_current_authenticated_user)
):
    """Retrieves all appointments for a specific connected patient where the current user is the doctor."""
    await check_doctor_permission(current_user)

    # We do not need to check the ConnectionRequest table here, as the Appointment
    # record itself ties the doctor and patient together.

    # 1. Fetch appointments where the current user is the doctor AND the patient matches
    cursor = appointments_collection.find({
        "doctor_email": current_user.email,
        "patient_email": patient_email
    }).sort("appointment_time", 1)
    
    appointments_list = await cursor.to_list(length=100)
    
    # Map MongoDB '_id' to Pydantic 'id'
    for appointment in appointments_list:
        if '_id' in appointment:
            appointment['id'] = str(appointment['_id'])
            
    return [Appointment(**appointment) for appointment in appointments_list]