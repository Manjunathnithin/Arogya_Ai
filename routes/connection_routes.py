# routes/connection_routes.py

from fastapi import APIRouter, Depends, HTTPException, status
from typing import List

from database import connection_requests_collection
from models.schemas import ConnectionRequest, ConnectionRequestCreate, User
from security import get_current_authenticated_user
from bson import ObjectId

router = APIRouter()

# --- Patient Routes ---

@router.post("/", response_model=ConnectionRequest, status_code=status.HTTP_201_CREATED)
async def create_connection_request(
    request_data: ConnectionRequestCreate,
    current_user: User = Depends(get_current_authenticated_user)
):
    """
    Allows a patient to request a connection with a doctor.
    """
    if current_user.user_type != 'patient':
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only patients can send connection requests.")

    # 1. Enforce patient email from authenticated user
    request_data.patient_email = current_user.email
    
    # 2. Check for existing pending or accepted request
    existing_request = await connection_requests_collection.find_one({
        "patient_email": current_user.email,
        "doctor_email": request_data.doctor_email,
        "status": {"$in": ["pending", "accepted"]}
    })
    
    if existing_request:
        if existing_request['status'] == 'accepted':
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You are already connected to this doctor.")
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="A pending request already exists for this doctor.")

    # 3. Insert new request
    request_dict = request_data.model_dump(exclude={'id'})
    result = await connection_requests_collection.insert_one(request_dict)
    request_dict["id"] = str(result.inserted_id)
    
    return ConnectionRequest(**request_dict)

# --- Doctor Routes ---

@router.get("/pending", response_model=List[ConnectionRequest])
async def list_pending_requests(
    current_user: User = Depends(get_current_authenticated_user)
):
    """Retrieves all pending connection requests for the authenticated doctor."""
    if current_user.user_type != 'doctor':
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only doctors can view pending requests.")

    query_filter = {
        "doctor_email": current_user.email,
        "status": "pending"
    }
        
    cursor = connection_requests_collection.find(query_filter).sort("request_date", 1)
    requests_list = await cursor.to_list(length=100)
    
    for req in requests_list:
        if '_id' in req:
            req['id'] = str(req['_id'])
            
    return [ConnectionRequest(**req) for req in requests_list]


@router.put("/{request_id}/accept", response_model=ConnectionRequest)
async def accept_connection_request(
    request_id: str,
    current_user: User = Depends(get_current_authenticated_user)
):
    """Allows a doctor to accept a pending connection request."""
    if current_user.user_type != 'doctor':
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only doctors can accept requests.")

    try:
        # Find and update the request, ensuring it belongs to the doctor and is pending
        update_result = await connection_requests_collection.find_one_and_update(
            {"_id": ObjectId(request_id), "doctor_email": current_user.email, "status": "pending"},
            {"$set": {"status": "accepted"}},
            return_document=True  # Return the updated document
        )
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid Request ID format.")

    if not update_result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pending request not found or not owned by doctor.")
    
    # Map _id to id for the response model
    update_result['id'] = str(update_result['_id'])
    
    return ConnectionRequest(**update_result)

# NOTE: A separate endpoint would be needed for rejecting a request.