# routes/user_routes.py

from fastapi import APIRouter, HTTPException, status, Form, Response, Depends, Request
from fastapi.responses import RedirectResponse
from bson import ObjectId

from database import user_collection 
from models.schemas import UserCreate, User, SESSION_COOKIE_NAME
from security import get_password_hash, verify_password, create_user_session, delete_user_session

router = APIRouter()

@router.post("/register", response_class=RedirectResponse, status_code=status.HTTP_303_SEE_OTHER)
async def register_user(
    first_name: str = Form(...),
    last_name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    user_type: str = Form(...)
):
    # 1. Check if user already exists
    if await user_collection.find_one({"email": email}):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    # 2. Hash password
    hashed_password = get_password_hash(password)

    # 3. Create new user document
    new_user_doc = {
        "email": email,
        "first_name": first_name,
        "last_name": last_name,
        "user_type": user_type,
        "hashed_password": hashed_password
    }

    try:
        # 4. Insert into database
        result = await user_collection.insert_one(new_user_doc)
        user_id = str(result.inserted_id)
        
        # 5. Create session
        session_token = await create_user_session(user_id, user_type)

        # 6. Prepare response (with session cookie)
        response = RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)
        response.set_cookie(
            key=SESSION_COOKIE_NAME,
            value=session_token,
            httponly=True,
            samesite="lax",
            secure=False 
        )
        return response

    except Exception as e:
        print(f"Registration Error: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not create user.")


@router.post("/login", status_code=status.HTTP_303_SEE_OTHER)
async def login_user(
    response: Response,
    email: str = Form(...),
    password: str = Form(...)
):
    # 1. Find the user
    user_doc = await user_collection.find_one({"email": email})
    
    if not user_doc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    # 2. Verify password
    if not verify_password(password, user_doc["hashed_password"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
        
    user_id = str(user_doc["_id"])
    user_type = user_doc["user_type"]

    try:
        # 3. Create session
        session_token = await create_user_session(user_id, user_type)
        
        # 4. Prepare response (with session cookie)
        redirect_response = RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)
        redirect_response.set_cookie(
            key=SESSION_COOKIE_NAME,
            value=session_token,
            httponly=True,
            samesite="lax",
            secure=False
        )
        return redirect_response
        
    except Exception as e:
        print(f"Login Error: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Login failed.")


@router.post("/logout", status_code=status.HTTP_303_SEE_OTHER)
async def logout_user(request: Request, response: Response):
    # Delete the session from the database and remove the cookie
    await delete_user_session(request, response)
    
    # Redirect to the home page after logout
    return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)