"""Invite tracker cog."""
import nextcord
from nextcord.ext import commands
import logging
from events.databases.invites_db import InvitesDatabase
from events.databases.loyalty_db import LoyaltyDatabase

logger = logging.getLogger(__name__)

POINTS_PER_INVITE = 10


class InviteTracker(commands.Cog):
    """Track invite usage and assign loyalty points."""

    def __init__(self, bot, db_path=None, loyalty_db_path=None):
        self.bot = bot
        self.db = InvitesDatabase(db_path)
        self.loyalty_db = LoyaltyDatabase(loyalty_db_path)
        self.invite_cache: dict[int, dict] = {}

    def _find_used_invite(self, before: dict, after: list):
        """Find which invite was used by comparing before/after counts."""
        after_map = {inv.code: inv for inv in after}
        for code, inv_before in before.items():
            inv_after = after_map.get(code)
            if inv_after and inv_after.uses > inv_before.uses:
                return inv_after
        return None

    @commands.Cog.listener()
    async def on_ready(self):
        """Cache all guild invites on startup."""
        for guild in self.bot.guilds:
            try:
                invites = await guild.invites()
                self.invite_cache[guild.id] = {inv.code: inv for inv in invites}
                # Sync to DB
                for inv in invites:
                    if inv.inviter:
                        await self.db.save_invite(
                            guild_id=guild.id,
                            code=inv.code,
                            inviter_id=str(inv.inviter.id),
                            uses=inv.uses
                        )
                logger.info(f"Cached {len(invites)} invites for guild {guild.id}")
            except Exception as e:
                logger.error(f"Error caching invites for guild {guild.id}: {e}")

    @commands.Cog.listener()
    async def on_invite_create(self, invite: nextcord.Invite):
        """Cache new invite when created."""
        guild_id = invite.guild.id
        if guild_id not in self.invite_cache:
            self.invite_cache[guild_id] = {}
        self.invite_cache[guild_id][invite.code] = invite
        if invite.inviter:
            await self.db.save_invite(
                guild_id=guild_id,
                code=invite.code,
                inviter_id=str(invite.inviter.id),
                uses=invite.uses
            )

    @commands.Cog.listener()
    async def on_invite_delete(self, invite: nextcord.Invite):
        """Remove deleted invite from cache."""
        guild_id = invite.guild.id
        if guild_id in self.invite_cache:
            self.invite_cache[guild_id].pop(invite.code, None)

    @commands.Cog.listener()
    async def on_member_join(self, member: nextcord.Member):
        """Detect which invite was used and record it."""
        guild = member.guild
        guild_id = guild.id

        try:
            before = self.invite_cache.get(guild_id, {})
            after = await guild.invites()

            used_invite = self._find_used_invite(before, after)

            # Update cache
            self.invite_cache[guild_id] = {inv.code: inv for inv in after}

            if not used_invite or not used_invite.inviter:
                logger.info(f"Could not determine invite for {member.id} in guild {guild_id}")
                return

            inviter_id = str(used_invite.inviter.id)
            joiner_id = str(member.id)

            # Check fraud
            is_fraud, fraud_reason = self._check_fraud(member, used_invite, inviter_id)

            # Record use
            await self.db.record_use(
                guild_id=guild_id,
                code=used_invite.code,
                joiner_id=joiner_id,
                is_fraud=is_fraud,
                fraud_reason=fraud_reason
            )

            if not is_fraud:
                await self.loyalty_db.add_points(
                    guild_id=guild_id,
                    user_id=inviter_id,
                    points=POINTS_PER_INVITE,
                    reason=f"invite:{used_invite.code}"
                )
                logger.info(f"Recorded invite use: {joiner_id} via {used_invite.code} (inviter: {inviter_id})")
            else:
                logger.warning(f"Fraud detected for invite {used_invite.code}: {fraud_reason}")

        except Exception as e:
            logger.error(f"Error tracking invite for {member.id}: {e}", exc_info=True)

    def _check_fraud(self, member: nextcord.Member, invite, inviter_id: str) -> tuple[bool, str]:
        """Check if this is a fraudulent invite use."""
        # Self-invite
        if str(member.id) == inviter_id:
            return True, "self_invite"

        # Account too new (< 7 days)
        from datetime import timezone, timedelta
        import datetime
        account_age = datetime.datetime.now(timezone.utc) - member.created_at
        if account_age < timedelta(days=7):
            return True, "new_account"

        return False, None


def setup(bot):
    """Load the cog."""
    bot.add_cog(InviteTracker(bot))
