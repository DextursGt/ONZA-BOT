"""Helper functions for ticket system."""
from datetime import datetime, timezone
from typing import Tuple, Dict, List
import logging

logger = logging.getLogger('onza-bot')


class TicketRateLimiter:
    """Rate limiting and cooldown management for tickets."""

    def __init__(self):
        self.user_cooldowns: Dict[int, datetime] = {}
        self.user_ticket_counts: Dict[int, List[datetime]] = {}
        self.cooldown_seconds = 300  # 5 minutes
        self.max_tickets_per_hour = 3
        self.rate_limit_window = 3600  # 1 hour

    def check_cooldown(self, user_id: int, owner_id: int) -> Tuple[bool, int]:
        """
        Check if user can create a ticket.

        Args:
            user_id: Discord user ID
            owner_id: Bot owner ID (bypasses limits)

        Returns:
            Tuple of (can_create: bool, remaining_seconds: int)
        """
        # Owner bypasses all limits
        if user_id == owner_id:
            return True, 0

        current_time = datetime.now(timezone.utc)

        # Check cooldown
        if user_id in self.user_cooldowns:
            last_ticket_time = self.user_cooldowns[user_id]
            time_diff = (current_time - last_ticket_time).total_seconds()
            if time_diff < self.cooldown_seconds:
                remaining = self.cooldown_seconds - int(time_diff)
                return False, remaining

        # Check rate limiting
        if user_id in self.user_ticket_counts:
            ticket_times = self.user_ticket_counts[user_id]
            recent_tickets = [
                t for t in ticket_times
                if (current_time - t).total_seconds() < self.rate_limit_window
            ]
            if len(recent_tickets) >= self.max_tickets_per_hour:
                oldest_ticket = min(recent_tickets)
                remaining = self.rate_limit_window - int(
                    (current_time - oldest_ticket).total_seconds()
                )
                return False, remaining

        return True, 0

    def update_user_ticket_tracking(self, user_id: int):
        """Update tracking after ticket creation."""
        current_time = datetime.now(timezone.utc)

        # Update cooldown
        self.user_cooldowns[user_id] = current_time

        # Update ticket count
        if user_id not in self.user_ticket_counts:
            self.user_ticket_counts[user_id] = []
        self.user_ticket_counts[user_id].append(current_time)

        # Clean old tickets (outside rate limit window)
        self.user_ticket_counts[user_id] = [
            t for t in self.user_ticket_counts[user_id]
            if (current_time - t).total_seconds() < self.rate_limit_window
        ]


def format_ticket_embed(ticket_id: str, user_mention: str, brand_name: str):
    """Create formatted embed for ticket channel."""
    import nextcord

    embed = nextcord.Embed(
        title=f"🎫 Ticket #{ticket_id}",
        description=f"Bienvenido {user_mention}\n\n"
                   f"Gracias por contactar al equipo de **{brand_name}**.\n"
                   f"Un miembro del staff te atenderá pronto.",
        color=0x00E5A8,
        timestamp=datetime.now(timezone.utc)
    )
    embed.add_field(
        name="ℹ️ Información",
        value="• Describe tu consulta claramente\n"
              "• El staff responderá lo antes posible\n"
              "• Mantén la conversación respetuosa",
        inline=False
    )
    embed.set_footer(text=f"Ticket ID: {ticket_id}")

    return embed
