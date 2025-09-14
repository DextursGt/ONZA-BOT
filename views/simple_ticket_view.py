import nextcord
from utils import is_staff, handle_interaction_response, logger
from data_manager import load_data, save_data
from config import TICKETS_LOG_CHANNEL_ID

class SimpleTicketView(nextcord.ui.View):
    def __init__(self, ticket_id: str = "persistent"):
        super().__init__(timeout=None)
        self.ticket_id = ticket_id

    def _get_ticket_id_from_channel(self, channel):
        """Obtener ticket_id del nombre del canal"""
        try:
            if channel.name.startswith("ticket-"):
                parts = channel.name.split("-")
                if len(parts) >= 2:
                    return parts[1]
        except Exception as e:
            logger.error(f"Error obteniendo ticket_id del canal: {e}")
        return None

    @nextcord.ui.button(label="🔒 Cerrar", style=nextcord.ButtonStyle.danger, row=0)
    async def close_ticket(self, interaction: nextcord.Interaction, button: nextcord.ui.Button):
        try:
            # Verificar permisos
            if not is_staff(interaction.user):
                await handle_interaction_response(interaction, "❌ Solo el staff puede cerrar tickets.")
                return

            # Obtener ticket_id del canal si no está disponible
            if not self.ticket_id or self.ticket_id == "persistent":
                self.ticket_id = self._get_ticket_id_from_channel(interaction.channel)

            if not self.ticket_id:
                await handle_interaction_response(interaction, "❌ No se pudo obtener el ID del ticket.")
                return

            # Cargar datos
            data = load_data()
            if self.ticket_id not in data["tickets"]:
                await handle_interaction_response(interaction, "❌ No se encontró el ticket.")
                return

            ticket_data = data["tickets"][self.ticket_id]
            
            # Actualizar estado del ticket
            ticket_data["status"] = "cerrado"
            ticket_data["estado_detallado"] = "cerrado_por_staff"
            ticket_data["fecha_cierre"] = nextcord.utils.utcnow().isoformat()
            ticket_data["cerrado_por"] = interaction.user.id

            # Guardar datos
            save_data(data)

            # Enviar mensaje de confirmación
            embed = nextcord.Embed(
                title="🔒 Ticket Cerrado",
                description=f"El ticket ha sido cerrado por {interaction.user.mention}",
                color=0xff0000
            )
            await handle_interaction_response(interaction, embed=embed)

            # Enviar log
            if TICKETS_LOG_CHANNEL_ID:
                try:
                    log_channel = interaction.guild.get_channel(TICKETS_LOG_CHANNEL_ID)
                    if log_channel:
                        log_embed = nextcord.Embed(
                            title="📋 Ticket Cerrado",
                            description=f"Ticket #{self.ticket_id} cerrado por staff",
                            color=0xff0000,
                            timestamp=nextcord.utils.utcnow()
                        )
                        log_embed.add_field(name="Ticket ID", value=self.ticket_id, inline=True)
                        log_embed.add_field(name="Staff", value=interaction.user.mention, inline=True)
                        log_embed.add_field(name="Canal", value=interaction.channel.mention, inline=True)
                        await log_channel.send(embed=log_embed)
                except Exception as e:
                    logger.error(f"Error enviando log: {e}")

            # Eliminar canal después de un delay
            await nextcord.utils.sleep_until(nextcord.utils.utcnow() + nextcord.timedelta(seconds=5))
            await interaction.channel.delete()

        except Exception as e:
            logger.error(f"Error cerrando ticket: {e}")
            await handle_interaction_response(
                interaction,
                "❌ Hubo un error al cerrar el ticket. Por favor, inténtalo de nuevo."
            )
