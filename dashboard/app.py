"""Web dashboard for ONZA-BOT control."""
from fastapi import FastAPI, Request, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
import os
from pathlib import Path

# Get dashboard directory
DASHBOARD_DIR = Path(__file__).parent

# Initialize FastAPI app
app = FastAPI(title="ONZA-BOT Dashboard", version="1.0.0")

# Mount static files
app.mount("/static", StaticFiles(directory=DASHBOARD_DIR / "static"), name="static")

# Setup templates
templates = Jinja2Templates(directory=DASHBOARD_DIR / "templates")

@app.get("/", response_class=HTMLResponse)
async def dashboard_home(request: Request):
    """Render main dashboard page."""
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "service": "ONZA-BOT Dashboard"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
