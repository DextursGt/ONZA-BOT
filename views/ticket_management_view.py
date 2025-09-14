import nextcord
import asyncio
from datetime import datetime
from utils import check_user_permissions, handle_interaction_response, logger, is_staff
from data_manager import load_data, save_data
from config import OWNER_ROLE_ID, STAFF_ROLE_ID, SUPPORT_ROLE_ID, TICKETS_LOG_CHANNEL_ID

class TicketManagementView(nextcord.ui.View):
    def __init__(self, ticket_id: str):
        super().__init__(timeout=None)  # Sin timeout para botones persistentes
        self.ticket_id = ticket_id


    async def send_log_message(self, interaction, action, description):
        """Enviar mensaje al canal de logs"""
        try:
            if TICKETS_LOG_CHANNEL_ID:
                log_channel = interaction.guild.get_channel(TICKETS_LOG_CHANNEL_ID)
                if log_channel:
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
            logger.error(f"Error enviando log: {e}")

    @nextcord.ui.button(label="✅ Completado", style=nextcord.ButtonStyle.success, row=0)
    async def complete_ticket(self, interaction: nextcord.Interaction):
        if not is_staff(interaction.user):
            await handle_interaction_response(interaction, "❌ Solo el staff puede marcar tickets como completados.")
            return

        try:
            data = load_data()
            if self.ticket_id not in data["tickets"]:
                await handle_interaction_response(interaction, "❌ No se encontró el ticket.")
                return

            ticket_data = data["tickets"][self.ticket_id]
            
            # Actualizar estado del ticket
            ticket_data["status"] = "completado"
            ticket_data["estado_detallado"] = "completado_por_staff"
            ticket_data["completed_by"] = str(interaction.user.id)
            ticket_data["completed_at"] = datetime.utcnow().isoformat()
            
            # Agregar al historial
            ticket_data["historial"].append({
                "estado": "completado",
                "timestamp": datetime.utcnow().isoformat(),
                "detalles": f"Ticket completado por {interaction.user.name}"
            })
            
            save_data(data)

            # Crear embed de completado
            embed = nextcord.Embed(
                title="✅ Ticket Completado",
                description=f"Este ticket ha sido marcado como completado por {interaction.user.mention}.",
                color=0x00FF00,
                timestamp=datetime.utcnow()
            )
            embed.add_field(
                name="📋 Detalles",
                value=f"**ID del Ticket:** {self.ticket_id}\n**Completado por:** {interaction.user.name}",
                inline=False
            )
            embed.set_footer(text="El ticket permanecerá abierto para consultas adicionales")

            # Deshabilitar el botón
            button.disabled = True
            button.label = "✅ Completado"
            
            await interaction.response.edit_message(embed=embed, view=self)
            
            # Enviar log
            await self.send_log_message(
                interaction, 
                "Ticket Completado", 
                f"El ticket {self.ticket_id} ha sido marcado como completado por {interaction.user.name}"
            )

            logger.info(f'Ticket {self.ticket_id} completado por {interaction.user.id}')

        except Exception as e:
            logger.error(f'Error al completar ticket: {str(e)}')
            await handle_interaction_response(
                interaction,
                "❌ Hubo un error al marcar el ticket como completado. Por favor, inténtalo de nuevo."
            )

    @nextcord.ui.button(label="⏸️ Pausar", style=nextcord.ButtonStyle.secondary, row=0)
    async def pause_ticket(self, interaction: nextcord.Interaction):
        if not is_staff(interaction.user):
            await handle_interaction_response(interaction, "❌ Solo el staff puede pausar tickets.")
            return

        try:
            data = load_data()
            if self.ticket_id not in data["tickets"]:
                await handle_interaction_response(interaction, "❌ No se encontró el ticket.")
                return

            ticket_data = data["tickets"][self.ticket_id]
            
            # Actualizar estado del ticket
            ticket_data["status"] = "pausado"
            ticket_data["estado_detallado"] = "pausado_por_staff"
            ticket_data["paused_by"] = str(interaction.user.id)
            ticket_data["paused_at"] = datetime.utcnow().isoformat()
            
            # Agregar al historial
            ticket_data["historial"].append({
                "estado": "pausado",
                "timestamp": datetime.utcnow().isoformat(),
                "detalles": f"Ticket pausado por {interaction.user.name}"
            })
            
            save_data(data)

            # Crear embed de pausado
            embed = nextcord.Embed(
                title="⏸️ Ticket Pausado",
                description=f"Este ticket ha sido pausado por {interaction.user.mention}.",
                color=0xFFA500,
                timestamp=datetime.utcnow()
            )
            embed.add_field(
                name="📋 Detalles",
                value=f"**ID del Ticket:** {self.ticket_id}\n**Pausado por:** {interaction.user.name}",
                inline=False
            )
            embed.set_footer(text="El ticket permanecerá abierto pero marcado como pausado")

            # Deshabilitar el botón
            button.disabled = True
            button.label = "⏸️ Pausado"
            
            await interaction.response.edit_message(embed=embed, view=self)
            
            # Enviar log
            await self.send_log_message(
                interaction, 
                "Ticket Pausado", 
                f"El ticket {self.ticket_id} ha sido pausado por {interaction.user.name}"
            )

            logger.info(f'Ticket {self.ticket_id} pausado por {interaction.user.id}')

        except Exception as e:
            logger.error(f'Error al pausar ticket: {str(e)}')
            await handle_interaction_response(
                interaction,
                "❌ Hubo un error al pausar el ticket. Por favor, inténtalo de nuevo."
            )

    @nextcord.ui.button(label="🔄 Reabrir", style=nextcord.ButtonStyle.primary, row=0)
    async def reopen_ticket(self, interaction: nextcord.Interaction):
        if not is_staff(interaction.user):
            await handle_interaction_response(interaction, "❌ Solo el staff puede reabrir tickets.")
            return

        try:
            data = load_data()
            if self.ticket_id not in data["tickets"]:
                await handle_interaction_response(interaction, "❌ No se encontró el ticket.")
                return

            ticket_data = data["tickets"][self.ticket_id]
            
            # Actualizar estado del ticket
            ticket_data["status"] = "abierto"
            ticket_data["estado_detallado"] = "reabierto_por_staff"
            ticket_data["reopened_by"] = str(interaction.user.id)
            ticket_data["reopened_at"] = datetime.utcnow().isoformat()
            
            # Agregar al historial
            ticket_data["historial"].append({
                "estado": "reabierto",
                "timestamp": datetime.utcnow().isoformat(),
                "detalles": f"Ticket reabierto por {interaction.user.name}"
            })
            
            save_data(data)

            # Crear embed de reabierto
            embed = nextcord.Embed(
                title="🔄 Ticket Reabierto",
                description=f"Este ticket ha sido reabierto por {interaction.user.mention}.",
                color=0x00E5A8,
                timestamp=datetime.utcnow()
            )
            embed.add_field(
                name="📋 Detalles",
                value=f"**ID del Ticket:** {self.ticket_id}\n**Reabierto por:** {interaction.user.name}",
                inline=False
            )
            embed.set_footer(text="El ticket está nuevamente activo")

            # Habilitar todos los botones
            for item in self.children:
                if hasattr(item, 'disabled'):
                    item.disabled = False
            
            await interaction.response.edit_message(embed=embed, view=self)
            
            # Enviar log
            await self.send_log_message(
                interaction, 
                "Ticket Reabierto", 
                f"El ticket {self.ticket_id} ha sido reabierto por {interaction.user.name}"
            )

            logger.info(f'Ticket {self.ticket_id} reabierto por {interaction.user.id}')

        except Exception as e:
            logger.error(f'Error al reabrir ticket: {str(e)}')
            await handle_interaction_response(
                interaction,
                "❌ Hubo un error al reabrir el ticket. Por favor, inténtalo de nuevo."
            )

    @nextcord.ui.button(label="🔒 Cerrar", style=nextcord.ButtonStyle.danger, row=1)
    async def close_ticket(self, interaction: nextcord.Interaction):
        if not is_staff(interaction.user):
            await handle_interaction_response(interaction, "❌ Solo el staff puede cerrar tickets.")
            return

        try:
            data = load_data()
            if self.ticket_id not in data["tickets"]:
                await handle_interaction_response(interaction, "❌ No se encontró el ticket.")
                return

            ticket_data = data["tickets"][self.ticket_id]
            
            # Actualizar estado del ticket
            ticket_data["status"] = "cerrado"
            ticket_data["estado_detallado"] = "cerrado_por_staff"
            ticket_data["closed_by"] = str(interaction.user.id)
            ticket_data["closed_at"] = datetime.utcnow().isoformat()
            
            # Agregar al historial
            ticket_data["historial"].append({
                "estado": "cerrado",
                "timestamp": datetime.utcnow().isoformat(),
                "detalles": f"Ticket cerrado por {interaction.user.name}"
            })
            
            save_data(data)

            # Crear embed de cierre
            embed = nextcord.Embed(
                title="🔒 Ticket Cerrado",
                description=f"Este ticket ha sido cerrado por {interaction.user.mention}. El canal será eliminado en 5 segundos.",
                color=0xFF0000,
                timestamp=datetime.utcnow()
            )
            embed.add_field(
                name="📋 Detalles",
                value=f"**ID del Ticket:** {self.ticket_id}\n**Cerrado por:** {interaction.user.name}",
                inline=False
            )
            embed.set_footer(text="El ticket será archivado próximamente")

            # Deshabilitar todos los botones
            for item in self.children:
                if hasattr(item, 'disabled'):
                    item.disabled = True
            
            await interaction.response.edit_message(embed=embed, view=self)
            
            # Enviar log
            await self.send_log_message(
                interaction, 
                "Ticket Cerrado", 
                f"El ticket {self.ticket_id} ha sido cerrado por {interaction.user.name}"
            )
            
            # Esperar 5 segundos y eliminar el canal
            await asyncio.sleep(5)
            await interaction.channel.delete(reason=f"Ticket {self.ticket_id} cerrado por {interaction.user.name}")
            
            # Notificar al usuario original
            if ticket_data.get("user_id"):
                try:
                    user = await interaction.guild.fetch_member(int(ticket_data["user_id"]))
                    if user:
                        user_embed = nextcord.Embed(
                            title="📬 Ticket Cerrado",
                            description=f"Tu ticket `{self.ticket_id}` ha sido cerrado por el staff.",
                            color=0xFF0000
                        )
                        await user.send(embed=user_embed)
                except Exception as e:
                    logger.error(f"Error al notificar al usuario: {str(e)}")

            logger.info(f'Ticket {self.ticket_id} cerrado por {interaction.user.id}')

        except Exception as e:
            logger.error(f'Error al cerrar ticket: {str(e)}')
            await handle_interaction_response(
                interaction,
                "❌ Hubo un error al cerrar el ticket. Por favor, inténtalo de nuevo."
            )
