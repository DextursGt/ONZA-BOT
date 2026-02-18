"""Join events handler cog."""
import nextcord
from nextcord.ext import commands
import logging
from events.databases.guilds_db import GuildsDatabase
from events.template import Template

logger = logging.getLogger(__name__)

class JoinEventsHandler(commands.Cog):
    """Handle member join events."""

    def __init__(self, bot, db_path=None):
        """Initialize join events handler.

        Args:
            bot: Discord bot instance
            db_path: Optional path to database (for testing)
        """
        self.bot = bot
        self.db = GuildsDatabase(db_path)
        self.template = Template()

    @commands.Cog.listener()
    async def on_member_join(self, member: nextcord.Member):
        """Triggered when user joins guild."""
        await self._send_channel_message(member)
        await self._send_join_dm(member)

    async def _send_channel_message(self, member: nextcord.Member):
        """Send welcome message to configured channel."""
        guild_id = member.guild.id
        try:
            config = await self.db.get_join_config(guild_id)

            if not config or not config['enabled']:
                logger.debug(f"Join messages disabled for guild {guild_id}")
                return

            context = {
                'member': member,
                'guild': member.guild,
                'member_count': member.guild.member_count
            }

            message = self.template.render(config['message_template'], context)

            channel = self.bot.get_channel(int(config['channel_id']))
            if not channel:
                logger.error(f"Channel {config['channel_id']} not found for join message")
                return

            if config['embed_enabled']:
                embed = nextcord.Embed(
                    title=config.get('embed_title', ''),
                    description=message,
                    color=config.get('embed_color', 0x00E5A8)
                )
                if config.get('embed_image_url'):
                    embed.set_image(url=config['embed_image_url'])
                await channel.send(embed=embed)
                logger.info(f"Join embed sent for {member.id} in guild {guild_id}")
            else:
                await channel.send(message)
                logger.info(f"Join message sent for {member.id} in guild {guild_id}")

        except Exception as e:
            logger.error(f"Error sending join channel message for {member.id}: {e}", exc_info=True)

    async def _send_join_dm(self, member: nextcord.Member):
        """Send a DM to the new member if configured."""
        guild_id = member.guild.id
        try:
            dm_config = await self.db.get_join_dm_config(guild_id)

            if not dm_config or not dm_config['enabled']:
                return

            context = {
                'member': member,
                'guild': member.guild,
            }

            message = self.template.render(dm_config['message_template'], context)
            await member.send(message)
            logger.info(f"Join DM sent to {member.id} in guild {guild_id}")

        except Exception as e:
            logger.warning(f"Could not send join DM to {member.id}: {e}")

def setup(bot):
    """Load the cog."""
    bot.add_cog(JoinEventsHandler(bot))
