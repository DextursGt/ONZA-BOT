"""Events configuration API endpoints."""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, field_validator
from typing import Optional, Union
from dashboard.auth import authenticate_user
from dashboard.bot_api import bot_api

router = APIRouter(prefix="/api/events", tags=["events"])

class JoinConfigRequest(BaseModel):
    """Join message configuration."""
    guild_id: Union[int, str]
    enabled: bool
    channel_id: Union[int, str]
    message_template: str
    embed_enabled: bool = False
    embed_title: Optional[str] = None
    embed_description: Optional[str] = None
    embed_color: Optional[int] = None
    embed_image_url: Optional[str] = None

    @field_validator('guild_id', 'channel_id')
    @classmethod
    def convert_ids(cls, v):
        return int(v) if isinstance(v, str) else v

@router.get("/join/{guild_id}")
async def get_join_config(guild_id: int, username: str = Depends(authenticate_user)):
    """Get join message configuration for a guild."""
    if not bot_api.bot:
        raise HTTPException(503, "Bot not connected")

    config = await bot_api.bot.guilds_db.get_join_config(guild_id)
    return config or {}

@router.post("/join/configure")
async def configure_join(request: JoinConfigRequest, username: str = Depends(authenticate_user)):
    """Configure join messages for a guild."""
    if not bot_api.bot:
        raise HTTPException(503, "Bot not connected")

    # Validate channel exists
    channel = bot_api.bot.get_channel(int(request.channel_id))
    if not channel:
        raise HTTPException(400, "Canal no encontrado")

    # Validate bot has permissions
    perms = channel.permissions_for(channel.guild.me)
    if not perms.send_messages:
        raise HTTPException(400, "Bot no tiene permisos para enviar mensajes en ese canal")

    # Save config
    await bot_api.bot.guilds_db.save_join_config(request.dict())

    return {"success": True, "message": "Configuración guardada"}

@router.post("/join/toggle")
async def toggle_join(guild_id: int, enabled: bool, username: str = Depends(authenticate_user)):
    """Toggle join messages on/off."""
    if not bot_api.bot:
        raise HTTPException(503, "Bot not connected")

    # Get current config
    config = await bot_api.bot.guilds_db.get_join_config(guild_id)
    if not config:
        raise HTTPException(404, "No configuration found")

    # Update enabled status
    config['enabled'] = enabled
    await bot_api.bot.guilds_db.save_join_config(config)

    return {"success": True, "enabled": enabled}
