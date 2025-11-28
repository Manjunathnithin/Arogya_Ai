# routes/report_routes.py

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from typing import List
from datetime import datetime, timezone

from database import reports_collection
# Import ReportCreate here
from models.schemas import Report, ReportCreate, User 
from security import get_current_authenticated_user
from ai_core.rag_engine import index_report 

router = APIRouter()

@router.post("/", response_model=Report, status_code=status.HTTP_201_CREATED)
async def create_report(
    report_data: ReportCreate, # <--- Accepts only user-provided fields
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_authenticated_user)
):
    """Allows a user to create a record of a report and indexes it for AI."""
    
    # 1. Convert input data to a dictionary
    report_dict = report_data.model_dump()
    
    # 2. Manually add the system-generated fields
    report_dict["owner_email"] = current_user.email
    # Use UTC for consistency
    report_dict["upload_date"] = datetime.now(timezone.utc)
    
    try:
        # 3. Save to MongoDB (The source of truth)
        result = await reports_collection.insert_one(report_dict)
        report_id = str(result.inserted_id)
        report_dict["id"] = report_id
        
        # 4. Trigger AI Indexing (Background Task)
        # We only index if there is actually text in the description
        if report_data.description:
            metadata = {
                "report_id": report_id,
                "owner_email": current_user.email,
                "title": report_data.title,
                "report_type": report_data.report_type,
                # Convert datetime to string for ChromaDB compatibility
                "upload_date": report_dict["upload_date"].isoformat()
            }
            
            # This runs index_report without blocking the response
            background_tasks.add_task(
                index_report, 
                report_id, 
                report_data.description, 
                metadata
            )
        
        # 5. Return success immediately
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