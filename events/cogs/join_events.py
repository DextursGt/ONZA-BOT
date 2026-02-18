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
        """Triggered when user joins guild.

        Args:
            member: Member who joined
        """
        guild_id = member.guild.id

        try:
            # Load config from DB
            config = await self.db.get_join_config(guild_id)

            if not config or not config['enabled']:
                logger.debug(f"Join messages disabled for guild {guild_id}")
                return

            # Build context
            context = {
                'member': member,
                'guild': member.guild,
                'member_count': member.guild.member_count
            }

            # Render template
            message = self.template.render(config['message_template'], context)

            # Get channel
            channel = self.bot.get_channel(int(config['channel_id']))
            if not channel:
                logger.error(f"Channel {config['channel_id']} not found for join message")
                return

            # Send message
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
            logger.error(f"Error in on_member_join for {member.id}: {e}", exc_info=True)

def setup(bot):
    """Load the cog."""
    bot.add_cog(JoinEventsHandler(bot))
