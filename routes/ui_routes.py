# routes/ui_routes.py

from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from typing import Optional

# Import dependencies
from security import get_optional_user, get_current_authenticated_user
from models.schemas import User

router = APIRouter()
templates = Jinja2Templates(directory="templates")

@router.get("/", response_class=HTMLResponse)
async def serve_home_page(request: Request, current_user: Optional[User] = Depends(get_optional_user)):
    """Serves the login/register page or redirects to the dashboard if logged in."""
    if current_user:
        return RedirectResponse(url="/dashboard", status_code=302)
        
    return templates.TemplateResponse(
        "index.html",
        {"request": request}
    )

@router.get("/dashboard", response_class=HTMLResponse)
async def serve_dashboard(request: Request, current_user: User = Depends(get_current_authenticated_user)):
    """Serves the main dashboard (requires authentication)."""
    
    context = {
        "request": request,
        "user": current_user,
        "is_patient": current_user.user_type == 'patient',
        "is_doctor": current_user.user_type == 'doctor',
    }
    return templates.TemplateResponse("dashboard.html", context)