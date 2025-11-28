# routes/report_routes.py

from fastapi import APIRouter, Depends, HTTPException, status
from typing import List

from database import reports_collection
from models.schemas import Report, ReportBase, User # Assuming Report is imported/defined
from security import get_current_authenticated_user

router = APIRouter()

@router.post("/", response_model=Report, status_code=status.HTTP_201_CREATED)
async def create_report(
    report_data: ReportBase,
    current_user: User = Depends(get_current_authenticated_user)
):
    """Allows a user (typically a patient) to create a record of a report."""
    
    # Enforce that the report belongs to the authenticated user
    report_data.owner_email = current_user.email
    
    report_dict = report_data.model_dump(exclude={'id'})
    
    try:
        result = await reports_collection.insert_one(report_dict)
        report_dict["id"] = str(result.inserted_id)
        
        # Return the created report object
        return Report(**report_dict)
        
    except Exception as e:
        print(f"Report creation error: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to save report.")


@router.get("/", response_model=List[Report])
async def list_user_reports(
    current_user: User = Depends(get_current_authenticated_user)
):
    """Retrieves all reports belonging to the current authenticated user."""
    
    # Only fetch reports owned by the current user
    cursor = reports_collection.find({"owner_email": current_user.email}).sort("upload_date", -1)
    
    reports_list = await cursor.to_list(length=100)
    
    # Map MongoDB '_id' to Pydantic 'id'
    for report in reports_list:
        if '_id' in report:
            report['id'] = str(report['_id'])
            
    return [Report(**report) for report in reports_list]


# NOTE: In a real application, you would also add /reports/{id} routes for GET, PUT, and DELETE.