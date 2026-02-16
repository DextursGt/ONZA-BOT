"""Base ticket view with shared functionality."""
import nextcord
from datetime import datetime
from typing import Optional
from utils import is_staff, handle_interaction_response, logger
from data_manager import load_data, save_data
from config import TICKETS_LOG_CHANNEL_ID


class BaseTicketView(nextcord.ui.View):
    """Base class for all ticket views with common functionality."""

    def __init__(self, ticket_id: str = "persistent", timeout: Optional[int] = None):
        super().__init__(timeout=timeout)
        self.ticket_id = ticket_id

    def get_ticket_id_from_channel(self, channel) -> Optional[str]:
        """Extract ticket ID from channel name format: ticket-{id}-{username}."""
        try:
            if channel.name.startswith("ticket-"):
                parts = channel.name.split("-")
                if len(parts) >= 2:
                    return parts[1]
        except Exception as e:
            logger.error(f"Error extracting ticket_id from channel: {e}")
        return None

    async def send_log_message(self, interaction: nextcord.Interaction, action: str, description: str):
        """Send formatted log message to tickets log channel."""
        try:
            if not TICKETS_LOG_CHANNEL_ID:
                return

            log_channel = interaction.guild.get_channel(TICKETS_LOG_CHANNEL_ID)
            if not log_channel:
                logger.warning(f"Log channel {TICKETS_LOG_CHANNEL_ID} not found")
                return

            embed = nextcord.Embed(
                title=f"📋 {action}",
                description=description,
                color=0x00E5A8,
                timestamp=datetime.utcnow()
            )
            embed.add_field(name="Ticket ID", value=self.ticket_id, inline=True)
            embed.add_field(name="Staff", value=interaction.user.mention, inline=True)
            embed.add_field(name="Canal", value=interaction.channel.mention, inline=True)

            await log_channel.send(embed=embed)
        except Exception as e:
            logger.error(f"Error sending log message: {e}")

    def load_ticket_data(self) -> Optional[dict]:
        """Load ticket data from storage."""
        try:
            data = load_data()
            if self.ticket_id not in data.get("tickets", {}):
                logger.warning(f"Ticket {self.ticket_id} not found in data")
                return None
            return data["tickets"][self.ticket_id]
        except Exception as e:
            logger.error(f"Error loading ticket data: {e}")
            return None

    def update_ticket_data(self, updates: dict) -> bool:
        """Update ticket data with provided fields."""
        try:
            data = load_data()
            if self.ticket_id not in data.get("tickets", {}):
                return False

            data["tickets"][self.ticket_id].update(updates)
            save_data(data)
            return True
        except Exception as e:
            logger.error(f"Error updating ticket data: {e}")
            return False
