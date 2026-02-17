"""API client to communicate with Discord bot."""
import asyncio
from typing import Optional, Dict, Any, List
import logging

logger = logging.getLogger(__name__)

class BotAPIClient:
    """Client to interact with the running Discord bot."""

    def __init__(self, bot_instance=None):
        """Initialize with optional bot instance."""
        self.bot = bot_instance
        self._channels_cache = {}

    async def get_bot_status(self) -> Dict[str, Any]:
        """Get bot status information."""
        if not self.bot:
            return {"online": False, "error": "Bot not connected"}

        try:
            return {
                "online": True,
                "user": str(self.bot.user) if self.bot.user else "Unknown",
                "guild_count": len(self.bot.guilds),
                "latency": round(self.bot.latency * 1000, 2)  # ms
            }
        except Exception as e:
            logger.error(f"Error getting bot status: {e}")
            return {"online": False, "error": str(e)}

    async def get_channels(self, guild_id: int) -> List[Dict[str, Any]]:
        """Get list of channels in a guild."""
        if not self.bot:
            return []

        try:
            guild = self.bot.get_guild(guild_id)
            if not guild:
                return []

            channels = []
            for channel in guild.text_channels:
                channels.append({
                    "id": str(channel.id),  # Convert to string to preserve precision
                    "name": channel.name,
                    "category": channel.category.name if channel.category else "Sin categoría"
                })

            self._channels_cache = {ch["id"]: ch for ch in channels}
            return sorted(channels, key=lambda x: x["name"])

        except Exception as e:
            logger.error(f"Error getting channels: {e}")
            return []

    async def send_message(self, channel_id: int, content: str) -> Dict[str, Any]:
        """Send a text message to a channel."""
        if not self.bot:
            return {"success": False, "error": "Bot not connected"}

        try:
            channel = self.bot.get_channel(channel_id)
            if not channel:
                return {"success": False, "error": "Canal no encontrado"}

            message = await channel.send(content)
            return {
                "success": True,
                "message_id": message.id,
                "channel": channel.name
            }

        except Exception as e:
            logger.error(f"Error sending message: {e}")
            return {"success": False, "error": str(e)}

    async def send_embed(
        self,
        channel_id: int,
        title: str,
        description: str,
        color: Optional[int] = None,
        fields: Optional[List[Dict[str, str]]] = None,
        footer: Optional[str] = None,
        image_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """Send an embed message to a channel."""
        if not self.bot:
            return {"success": False, "error": "Bot not connected"}

        try:
            import nextcord

            channel = self.bot.get_channel(channel_id)
            if not channel:
                return {"success": False, "error": "Canal no encontrado"}

            embed = nextcord.Embed(
                title=title,
                description=description,
                color=color or 0x00E5A8
            )

            if fields:
                for field in fields:
                    embed.add_field(
                        name=field.get("name", ""),
                        value=field.get("value", ""),
                        inline=field.get("inline", False)
                    )

            if footer:
                embed.set_footer(text=footer)

            if image_url:
                embed.set_image(url=image_url)

            message = await channel.send(embed=embed)
            return {
                "success": True,
                "message_id": message.id,
                "channel": channel.name
            }

        except Exception as e:
            logger.error(f"Error sending embed: {e}")
            return {"success": False, "error": str(e)}

# Global bot API client instance
bot_api = BotAPIClient()
