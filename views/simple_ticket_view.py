"""Simple ticket view for basic ticket operations."""
import nextcord
from .base_ticket_view import BaseTicketView
from utils import is_staff, handle_interaction_response, logger


class SimpleTicketView(BaseTicketView):
    """Simplified ticket view for basic ticket management."""

    def __init__(self, ticket_id: str = "persistent"):
        super().__init__(ticket_id=ticket_id, timeout=None)

    @nextcord.ui.button(label="✅ Completado", style=nextcord.ButtonStyle.success, row=0)
    async def complete_ticket(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        """Mark ticket as completed."""
        try:
            if not is_staff(interaction.user):
                await handle_interaction_response(
                    interaction,
                    "❌ Solo el staff puede marcar tickets como completados."
                )
                return

            # Get ticket ID from channel if not set
            if not self.ticket_id or self.ticket_id == "persistent":
                self.ticket_id = self.get_ticket_id_from_channel(interaction.channel)

            if not self.ticket_id:
                await handle_interaction_response(
                    interaction,
                    "❌ No se pudo obtener el ID del ticket."
                )
                return

            # Load ticket data
            ticket_data = self.load_ticket_data()
            if not ticket_data:
                await handle_interaction_response(
                    interaction,
                    "❌ No se encontró el ticket."
                )
                return

            # Update ticket status
            success = self.update_ticket_data({
                "status": "completado",
                "estado_detallado": "completado_por_staff",
                "fecha_completado": nextcord.utils.utcnow().isoformat(),
                "completado_por": interaction.user.id
            })

            if not success:
                await handle_interaction_response(
                    interaction,
                    "❌ Error al actualizar el ticket."
                )
                return

            # Send log message
            await self.send_log_message(
                interaction,
                "Ticket Completado",
                f"El ticket ha sido marcado como completado."
            )

            # Notify user
            await handle_interaction_response(
                interaction,
                f"✅ Ticket **{self.ticket_id}** marcado como completado."
            )

            logger.info(f"Ticket {self.ticket_id} marked as completed by {interaction.user.id}")

        except Exception as e:
            logger.error(f"Error in complete_ticket: {e}")
            await handle_interaction_response(
                interaction,
                "❌ Error al completar el ticket."
            )

    @nextcord.ui.button(label="🔒 Cerrar", style=nextcord.ButtonStyle.danger, row=0)
    async def close_ticket(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        """Close ticket channel."""
        try:
            if not is_staff(interaction.user):
                await handle_interaction_response(
                    interaction,
                    "❌ Solo el staff pueden cerrar tickets."
                )
                return

            # Get ticket ID from channel if not set
            if not self.ticket_id or self.ticket_id == "persistent":
                self.ticket_id = self.get_ticket_id_from_channel(interaction.channel)

            if self.ticket_id:
                # Update status before deleting channel
                self.update_ticket_data({
                    "status": "cerrado",
                    "cerrado_por": interaction.user.id,
                    "fecha_cierre": nextcord.utils.utcnow().isoformat()
                })

                await self.send_log_message(
                    interaction,
                    "Ticket Cerrado",
                    f"El ticket ha sido cerrado."
                )

            await handle_interaction_response(
                interaction,
                "🔒 Cerrando ticket en 3 segundos..."
            )

            await interaction.channel.delete(reason=f"Ticket cerrado por {interaction.user}")
            logger.info(f"Ticket {self.ticket_id} closed by {interaction.user.id}")

        except Exception as e:
            logger.error(f"Error in close_ticket: {e}")
            await handle_interaction_response(
                interaction,
                "❌ Error al cerrar el ticket."
            )
