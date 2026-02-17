"""Web dashboard for ONZA-BOT control."""
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from typing import Optional, List, Dict, Union
import os
from pathlib import Path
from pydantic import BaseModel, field_validator

from .bot_api import bot_api
from .auth import authenticate_user
from dashboard.api.events import router as events_router

# Get dashboard directory
DASHBOARD_DIR = Path(__file__).parent

# Initialize FastAPI app
app = FastAPI(title="ONZA-BOT Dashboard", version="1.0.0")

# Mount static files
app.mount("/static", StaticFiles(directory=DASHBOARD_DIR / "static"), name="static")

# Setup templates
templates = Jinja2Templates(directory=DASHBOARD_DIR / "templates")

# Register API routers
app.include_router(events_router)

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
    channel_id: Union[int, str]  # Accept both int and string
    content: str

    @field_validator('channel_id')
    @classmethod
    def convert_channel_id(cls, v):
        """Convert string channel_id to int."""
        return int(v) if isinstance(v, str) else v

class EmbedRequest(BaseModel):
    channel_id: Union[int, str]  # Accept both int and string
    title: str
    description: str
    color: Optional[int] = None
    fields: Optional[List[Dict[str, str]]] = None
    footer: Optional[str] = None
    image_url: Optional[str] = None

    @field_validator('channel_id')
    @classmethod
    def convert_channel_id(cls, v):
        """Convert string channel_id to int."""
        return int(v) if isinstance(v, str) else v

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
