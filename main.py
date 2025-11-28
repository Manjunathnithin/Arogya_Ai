# main.py

from fastapi import FastAPI, Depends, HTTPException, status, Form, Request, UploadFile, File
from fastapi.staticfiles import StaticFiles 
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import List

# Import our tools and schemas
from ai_core.rag_engine import get_rag_response, get_summary_response 
from routes import user_routes, report_routes, doctor_routes, connection_routes, admin_routes,appointment_routes, ui_routes

from security import get_current_authenticated_user 
from database import chat_messages_collection 
from models.schemas import User, ChatMessage
import shutil
import os
from ai_core.transcriber import transcribe_audio

app = FastAPI(
    title="AarogyaAI",
    description=" medical ai assistant",
    version="0.1.0",
)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Include all the different routers for our application (CRUCIAL FOR 404 FIX)
app.include_router(ui_routes.router, prefix="", tags=["UI & Pages"])
app.include_router(user_routes.router, prefix="/users", tags=["Users"])
app.include_router(report_routes.router, prefix="/reports", tags=["Reports"])
app.include_router(doctor_routes.router, prefix="/doctor", tags=["Doctor"])
app.include_router(connection_routes.router, prefix="/connections", tags=["Connections"])
app.include_router(admin_routes.router, prefix="/admin",tags=["Admin"])
app.include_router(appointment_routes.router, prefix="/appointments", tags=["Appointments"])

@app.get("/")
def read_root():
    """This is the main endpoint of the API."""
    return {"message": "Welcome to your Arogya AI Backend! The service is running."}

@app.post("/chat", response_class=HTMLResponse)
async def chat_with_rag(
    request: Request,
    query: str = Form(...), 
    action: str = Form("ask"),
    current_user: User = Depends(get_current_authenticated_user)
):
    ai_response_text = ""
    query_to_save = query

    try:
        # 1. Process the User Intent
        if action == 'summarize':
            if current_user.user_type != 'patient':
                return HTMLResponse('<div class="text-xs text-red-500 p-2 text-center">Only patients can use summary features.</div>')
            ai_response_text = await get_summary_response(user_email=current_user.email)
            query_to_save = "Request for Medical Record Summary"
        
        elif action == 'ask':
            ai_response_text = await get_rag_response(query, user_email=current_user.email)
        
        # 2. Save to Database
        chat_message = ChatMessage(
            owner_email=current_user.email,
            user_query=query_to_save,
            ai_response=ai_response_text
        )
        await chat_messages_collection.insert_one(chat_message.model_dump())

        # 3. Return HTML Fragment
        return HTMLResponse(f"""
        <div class="flex flex-col space-y-2 mb-4 animate-message-entry">
            <div class="self-end bg-indigo-100 text-indigo-900 p-3 rounded-2xl rounded-tr-none max-w-[85%] text-sm shadow-sm border border-indigo-200">
                {query_to_save}
            </div>
            <div class="self-start bg-white border border-gray-200 text-gray-800 p-3 rounded-2xl rounded-tl-none max-w-[90%] text-sm shadow-md">
                <strong class="text-indigo-600 block text-xs mb-1 font-bold">Aarogya AI</strong>
                <div class="prose prose-sm text-gray-700 leading-relaxed">{ai_response_text}</div>
            </div>
        </div>
        """)
        
    except Exception as e:
        print(f"Chat Error: {e}")
        return HTMLResponse(f'<div class="text-xs text-red-500 p-2 text-center bg-red-50 rounded-lg">Error processing request. Please try again.</div>')

@app.get("/chat/history", response_class=HTMLResponse)
async def get_chat_history(current_user: User = Depends(get_current_authenticated_user)):
    history_cursor = chat_messages_collection.find(
        {"owner_email": current_user.email}
    ).sort("timestamp", 1)
    
    history_list = await history_cursor.to_list(length=50)
    
    if not history_list:
        return HTMLResponse('<div class="flex flex-col items-center justify-center h-40 text-gray-400 text-xs italic space-y-2"><svg class="w-8 h-8 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"></path></svg><span>No history yet. Ask me anything!</span></div>')

    html_content = ""
    for msg in history_list:
        html_content += f"""
        <div class="flex flex-col space-y-2 mb-4">
            <div class="self-end bg-indigo-100 text-indigo-900 p-3 rounded-2xl rounded-tr-none max-w-[85%] text-sm shadow-sm border border-indigo-200">
                {msg.get('user_query')}
            </div>
            <div class="self-start bg-white border border-gray-200 text-gray-800 p-3 rounded-2xl rounded-tl-none max-w-[90%] text-sm shadow-md">
                <strong class="text-indigo-600 block text-xs mb-1 font-bold">Aarogya AI</strong>
                <div class="prose prose-sm text-gray-700 leading-relaxed">{msg.get('ai_response')}</div>
            </div>
        </div>
        """
    return HTMLResponse(html_content)

@app.post("/transcribe")
async def transcribe_voice(audio_file: UploadFile = File(...)):
    """
    Receives an audio blob, saves it temporarily, transcribes it, and returns text.
    """
    temp_filename = f"temp_{audio_file.filename}"
    
    try:
        # 1. Save the uploaded file temporarily
        with open(temp_filename, "wb") as buffer:
            shutil.copyfileobj(audio_file.file, buffer)
            
        # 2. Transcribe using Whisper
        transcribed_text = transcribe_audio(temp_filename)
        
        # 3. Cleanup
        os.remove(temp_filename)
        
        return {"text": transcribed_text}
        
    except Exception as e:
        print(f"Transcription API Error: {e}")
        # Clean up if error
        if os.path.exists(temp_filename):
            os.remove(temp_filename)
        return {"text": "", "error": str(e)}