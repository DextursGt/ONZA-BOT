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


# --- Leave Config Endpoints ---

class LeaveConfigRequest(BaseModel):
    guild_id: Union[int, str]
    enabled: bool
    channel_id: Union[int, str]
    message_template: str

    @field_validator('guild_id', 'channel_id')
    @classmethod
    def convert_ids(cls, v):
        return int(v) if isinstance(v, str) else v

@router.get("/leave/{guild_id}")
async def get_leave_config(guild_id: int, username: str = Depends(authenticate_user)):
    """Get leave message configuration for a guild."""
    if not bot_api.bot:
        raise HTTPException(503, "Bot not connected")
    config = await bot_api.bot.guilds_db.get_leave_config(guild_id)
    return config or {}

@router.post("/leave/configure")
async def configure_leave(request: LeaveConfigRequest, username: str = Depends(authenticate_user)):
    """Configure leave messages for a guild."""
    if not bot_api.bot:
        raise HTTPException(503, "Bot not connected")
    channel = bot_api.bot.get_channel(int(request.channel_id))
    if not channel:
        raise HTTPException(400, "Canal no encontrado")
    await bot_api.bot.guilds_db.save_leave_config(request.dict())
    return {"success": True, "message": "Configuración guardada"}


# --- Join DM Config Endpoints ---

class JoinDMConfigRequest(BaseModel):
    guild_id: Union[int, str]
    enabled: bool
    message_template: str

    @field_validator('guild_id')
    @classmethod
    def convert_id(cls, v):
        return int(v) if isinstance(v, str) else v

@router.get("/join-dm/{guild_id}")
async def get_join_dm_config(guild_id: int, username: str = Depends(authenticate_user)):
    """Get join DM configuration for a guild."""
    if not bot_api.bot:
        raise HTTPException(503, "Bot not connected")
    config = await bot_api.bot.guilds_db.get_join_dm_config(guild_id)
    return config or {}

@router.post("/join-dm/configure")
async def configure_join_dm(request: JoinDMConfigRequest, username: str = Depends(authenticate_user)):
    """Configure join DM for a guild."""
    if not bot_api.bot:
        raise HTTPException(503, "Bot not connected")
    await bot_api.bot.guilds_db.save_join_dm_config(request.dict())
    return {"success": True, "message": "Configuración guardada"}


# --- Invite Stats Endpoints ---

@router.get("/invites/{guild_id}/stats")
async def get_invite_stats(guild_id: int, username: str = Depends(authenticate_user)):
    """Get invite statistics for a guild."""
    if not bot_api.bot:
        raise HTTPException(503, "Bot not connected")

    invites = await bot_api.bot.invites_db.get_all_invites(guild_id)
    total_uses = sum(inv.get('uses', 0) for inv in invites)

    return {
        "guild_id": guild_id,
        "total_invites": len(invites),
        "total_uses": total_uses,
        "invites": invites
    }


@router.get("/invites/{guild_id}/leaderboard")
async def get_invite_leaderboard(guild_id: int, limit: int = 10,
                                  username: str = Depends(authenticate_user)):
    """Get top inviters leaderboard for a guild."""
    if not bot_api.bot:
        raise HTTPException(503, "Bot not connected")

    leaderboard = await bot_api.bot.loyalty_db.get_leaderboard(guild_id, limit=limit)
    return {"guild_id": guild_id, "leaderboard": leaderboard}


@router.get("/invites/{guild_id}/user/{user_id}")
async def get_user_invite_stats(guild_id: int, user_id: str,
                                 username: str = Depends(authenticate_user)):
    """Get invite stats and points for a specific user."""
    if not bot_api.bot:
        raise HTTPException(503, "Bot not connected")

    stats = await bot_api.bot.invites_db.get_inviter_stats(guild_id, user_id)
    points = await bot_api.bot.loyalty_db.get_points(guild_id, user_id)
    history = await bot_api.bot.loyalty_db.get_history(guild_id, user_id, limit=10)

    return {
        "user_id": user_id,
        "guild_id": guild_id,
        "total_invites": stats['total_uses'],
        "loyalty_points": points,
        "recent_history": history
    }
