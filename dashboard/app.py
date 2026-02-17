"""Web dashboard for ONZA-BOT control."""
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from typing import Optional, List, Dict
import os
from pathlib import Path
from pydantic import BaseModel

from .bot_api import bot_api
from .auth import authenticate_user

# Get dashboard directory
DASHBOARD_DIR = Path(__file__).parent

# Initialize FastAPI app
app = FastAPI(title="ONZA-BOT Dashboard", version="1.0.0")

# Mount static files
app.mount("/static", StaticFiles(directory=DASHBOARD_DIR / "static"), name="static")

# Setup templates
templates = Jinja2Templates(directory=DASHBOARD_DIR / "templates")

@app.get("/", response_class=HTMLResponse)
async def dashboard_home(request: Request, username: str = Depends(authenticate_user)):
    """Render main dashboard page."""
    return templates.TemplateResponse("index.html", {"request": request, "username": username})

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "service": "ONZA-BOT Dashboard"}

@app.get("/api/config")
async def get_config(username: str = Depends(authenticate_user)):
    """Get dashboard configuration."""
    from .config import GUILD_ID
    return {"guild_id": str(GUILD_ID)}  # Return as string to preserve precision

# Pydantic models for requests
class MessageRequest(BaseModel):
    channel_id: int
    content: str

class EmbedRequest(BaseModel):
    channel_id: int
    title: str
    description: str
    color: Optional[int] = None
    fields: Optional[List[Dict[str, str]]] = None
    footer: Optional[str] = None
    image_url: Optional[str] = None

@app.get("/api/bot/status")
async def get_bot_status(username: str = Depends(authenticate_user)):
    """Get bot status."""
    return await bot_api.get_bot_status()

@app.get("/api/channels/{guild_id}")
async def get_channels(guild_id: int, username: str = Depends(authenticate_user)):
    """Get list of channels."""
    channels = await bot_api.get_channels(guild_id)
    return {"channels": channels}

@app.post("/api/message/send")
async def send_message(request: MessageRequest, username: str = Depends(authenticate_user)):
    """Send a text message."""
    result = await bot_api.send_message(request.channel_id, request.content)
    return result

@app.post("/api/message/embed")
async def send_embed(request: EmbedRequest, username: str = Depends(authenticate_user)):
    """Send an embed message."""
    result = await bot_api.send_embed(
        request.channel_id,
        request.title,
        request.description,
        request.color,
        request.fields,
        request.footer,
        request.image_url
    )
    return result

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
