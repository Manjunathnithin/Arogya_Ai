# routes/admin_routes.py

from fastapi import APIRouter, Depends, HTTPException, Response, status, Path
from typing import List

from database import user_collection 
from models.schemas import User
from security import get_current_authenticated_user
from bson import ObjectId

router = APIRouter()

# --- Helper Function ---
async def check_admin_permission(current_user: User):
    """Ensures the authenticated user is an administrator."""
    if current_user.user_type != 'admin':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Only administrators can access this resource."
        )

# --- Admin Endpoints ---

@router.get("/users", response_model=List[User])
async def list_all_users(
    current_user: User = Depends(get_current_authenticated_user)
):
    """Retrieves a list of all users in the system."""
    await check_admin_permission(current_user)

    cursor = user_collection.find()
    users_list = await cursor.to_list(length=1000)
    
    # Map MongoDB '_id' to Pydantic 'id'
    users_parsed = []
    for user_doc in users_list:
        if '_id' in user_doc:
            user_doc['id'] = str(user_doc['_id'])
            # Remove sensitive data before returning
            user_doc.pop('hashed_password', None) 
            users_parsed.append(User(**user_doc))
            
    return users_parsed


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: str = Path(..., description="The ObjectId of the user to delete."),
    current_user: User = Depends(get_current_authenticated_user)
):
    """Deletes a user by their ID."""
    await check_admin_permission(current_user)

    try:
        # Prevent admins from deleting themselves (optional security measure)
        if current_user.id == user_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot delete your own admin account.")
            
        delete_result = await user_collection.delete_one({"_id": ObjectId(user_id)})
        
        if delete_result.deleted_count == 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
            
    except Exception as e:
        if isinstance(e, HTTPException):
            raise
        # Catch exception if the user_id is not a valid ObjectId format
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid User ID format.")
    
    return Response(status_code=status.HTTP_204_NO_CONTENT)