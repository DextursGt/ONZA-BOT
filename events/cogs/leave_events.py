"""Leave events handler cog."""
import nextcord
from nextcord.ext import commands
import logging
from events.databases.guilds_db import GuildsDatabase
from events.template import Template

logger = logging.getLogger(__name__)


class LeaveEventsHandler(commands.Cog):
    """Handle member leave events."""

    def __init__(self, bot, db_path=None):
        self.bot = bot
        self.db = GuildsDatabase(db_path)
        self.template = Template()

    @commands.Cog.listener()
    async def on_member_remove(self, member: nextcord.Member):
        """Triggered when user leaves guild."""
        guild_id = member.guild.id

        try:
            config = await self.db.get_leave_config(guild_id)

            if not config or not config['enabled']:
                logger.debug(f"Leave messages disabled for guild {guild_id}")
                return

            context = {
                'member': member,
                'guild': member.guild,
            }

            message = self.template.render(config['message_template'], context)

            channel = self.bot.get_channel(int(config['channel_id']))
            if not channel:
                logger.error(f"Channel {config['channel_id']} not found for leave message")
                return

            await channel.send(message)
            logger.info(f"Leave message sent for {member.id} in guild {guild_id}")

        except Exception as e:
            logger.error(f"Error in on_member_remove for {member.id}: {e}", exc_info=True)


def setup(bot):
    """Load the cog."""
    bot.add_cog(LeaveEventsHandler(bot))
