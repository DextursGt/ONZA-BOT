"""Auto roles handler cog."""
import nextcord
from nextcord.ext import commands
import asyncio
import logging
from events.databases.guilds_db import GuildsDatabase

logger = logging.getLogger(__name__)

class AutoRolesHandler(commands.Cog):
    """Auto-assign roles on member join."""

    def __init__(self, bot, db_path=None):
        """Initialize auto roles handler.

        Args:
            bot: Discord bot instance
            db_path: Optional path to database (for testing)
        """
        self.bot = bot
        self.db = GuildsDatabase(db_path)

    @commands.Cog.listener()
    async def on_member_join(self, member: nextcord.Member):
        """Assign configured auto-roles when user joins.

        Args:
            member: Member who joined
        """
        guild_id = member.guild.id

        try:
            # Get auto-roles config
            roles_config = await self.db.get_auto_roles(guild_id)

            if not roles_config:
                logger.debug(f"No auto-roles configured for guild {guild_id}")
                return

            # Assign each role
            for role_config in roles_config:
                role = member.guild.get_role(int(role_config['role_id']))

                if not role:
                    logger.warning(f"Role {role_config['role_id']} not found in guild {guild_id}")
                    continue

                # Delay if configured
                if role_config['delay_seconds'] > 0:
                    await asyncio.sleep(role_config['delay_seconds'])

                # Assign role
                await member.add_roles(role, reason="Auto-role assignment")
                logger.info(f"Assigned role {role.name} to {member.id} in guild {guild_id}")

        except Exception as e:
            logger.error(f"Error assigning auto-roles to {member.id}: {e}", exc_info=True)

def setup(bot):
    """Load the cog."""
    bot.add_cog(AutoRolesHandler(bot))
