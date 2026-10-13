import nextcord
import asyncio
from datetime import datetime
from utils import handle_interaction_response, logger, is_staff
from .base_ticket_view import BaseTicketView, enviar_transcripcion


class TicketManagementView(BaseTicketView):
    def __init__(self, ticket_id: str = "persistent"):
        super().__init__(ticket_id=ticket_id, timeout=None)

    @nextcord.ui.button(label="🙋 Tomar", style=nextcord.ButtonStyle.primary, row=1, custom_id="ticket_claim")
    async def claim_ticket(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        if not is_staff(interaction.user):
            await interaction.response.send_message("❌ Solo el staff puede tomar tickets.", ephemeral=True)
            return

        ticket_data = self.load_ticket_data() if self.ticket_id else None
        if not ticket_data:
            await interaction.response.send_message("❌ No se encontró el ticket.", ephemeral=True)
            return

        asignado = ticket_data.get("asignado_a")
        if asignado and asignado != str(interaction.user.id):
            await interaction.response.send_message(f"❌ Este ticket ya lo tomó <@{asignado}>.", ephemeral=True)
            return

        self.update_ticket_data({"asignado_a": str(interaction.user.id), "asignado_at": datetime.utcnow().isoformat()})
        await interaction.response.send_message(f"🙋 {interaction.user.mention} tomó este ticket y te va a atender.")
        logger.info(f"Ticket {self.ticket_id} tomado por {interaction.user.id}")

    @nextcord.ui.button(label="✅ Completado", style=nextcord.ButtonStyle.success, row=0, custom_id="ticket_complete")
    async def complete_ticket(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        if not is_staff(interaction.user):
            try:
                await interaction.response.send_message("❌ Solo el staff puede marcar tickets como completados.", ephemeral=True)
            except:
                try:
                    await interaction.followup.send("❌ Solo el staff puede marcar tickets como completados.", ephemeral=True)
                except:
                    pass
            return

        # Obtener ticket_id del canal si no está disponible
        if not self.ticket_id or self.ticket_id == "persistent":
            self.ticket_id = self.get_ticket_id_from_channel(interaction.channel)

        if not self.ticket_id:
            try:
                await interaction.response.send_message("❌ No se pudo obtener el ID del ticket.", ephemeral=True)
            except:
                try:
                    await interaction.followup.send("❌ No se pudo obtener el ID del ticket.", ephemeral=True)
                except:
                    pass
            return

        try:
            ticket_data = self.load_ticket_data()
            if not ticket_data:
                try:
                    await interaction.response.send_message("❌ No se encontró el ticket.", ephemeral=True)
                except:
                    try:
                        await interaction.followup.send("❌ No se encontró el ticket.", ephemeral=True)
                    except:
                        pass
                return

            # Actualizar estado del ticket
            updates = {
                "status": "completado",
                "estado_detallado": "completado_por_staff",
                "completed_by": str(interaction.user.id),
                "completed_at": datetime.utcnow().isoformat(),
                "historial": ticket_data.get("historial", []) + [{
                    "estado": "completado",
                    "timestamp": datetime.utcnow().isoformat(),
                    "detalles": f"Ticket completado por {interaction.user.name}"
                }]
            }

            self.update_ticket_data(updates)

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
            
            # Responder a la interacción - editar el mensaje original
            try:
                if not interaction.response.is_done():
                    await interaction.response.edit_message(embed=embed, view=self)
                else:
                    await interaction.edit_original_message(embed=embed, view=self)
            except Exception as e:
                logger.error(f"Error editando mensaje en complete_ticket: {e}")
                try:
                    if not interaction.response.is_done():
                        await interaction.response.send_message(embed=embed, view=self)
                    else:
                        await interaction.followup.send(embed=embed, view=self)
                except:
                    pass
            
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

    @nextcord.ui.button(label="⏸️ Pausar", style=nextcord.ButtonStyle.secondary, row=0, custom_id="ticket_pause")
    async def pause_ticket(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        if not is_staff(interaction.user):
            try:
                await interaction.response.send_message("❌ Solo el staff puede pausar tickets.", ephemeral=True)
            except:
                try:
                    await interaction.followup.send("❌ Solo el staff puede pausar tickets.", ephemeral=True)
                except:
                    pass
            return

        # Obtener ticket_id del canal si no está disponible
        if not self.ticket_id or self.ticket_id == "persistent":
            self.ticket_id = self.get_ticket_id_from_channel(interaction.channel)

        if not self.ticket_id:
            try:
                await interaction.response.send_message("❌ No se pudo obtener el ID del ticket.", ephemeral=True)
            except:
                try:
                    await interaction.followup.send("❌ No se pudo obtener el ID del ticket.", ephemeral=True)
                except:
                    pass
            return

        try:
            ticket_data = self.load_ticket_data()
            if not ticket_data:
                try:
                    await interaction.response.send_message("❌ No se encontró el ticket.", ephemeral=True)
                except:
                    try:
                        await interaction.followup.send("❌ No se encontró el ticket.", ephemeral=True)
                    except:
                        pass
                return

            # Actualizar estado del ticket
            updates = {
                "status": "pausado",
                "estado_detallado": "pausado_por_staff",
                "paused_by": str(interaction.user.id),
                "paused_at": datetime.utcnow().isoformat(),
                "historial": ticket_data.get("historial", []) + [{
                    "estado": "pausado",
                    "timestamp": datetime.utcnow().isoformat(),
                    "detalles": f"Ticket pausado por {interaction.user.name}"
                }]
            }

            self.update_ticket_data(updates)

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
            
            # Responder a la interacción
            try:
                if not interaction.response.is_done():
                    await interaction.response.edit_message(embed=embed, view=self)
                else:
                    await interaction.edit_original_message(embed=embed, view=self)
            except Exception as e:
                logger.error(f"Error editando mensaje en pause_ticket: {e}")
                try:
                    if not interaction.response.is_done():
                        await interaction.response.send_message(embed=embed, view=self)
                    else:
                        await interaction.followup.send(embed=embed, view=self)
                except:
                    pass
            
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

    @nextcord.ui.button(label="🔄 Reabrir", style=nextcord.ButtonStyle.primary, row=0, custom_id="ticket_reopen")
    async def reopen_ticket(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        if not is_staff(interaction.user):
            try:
                await interaction.response.send_message("❌ Solo el staff puede reabrir tickets.", ephemeral=True)
            except:
                try:
                    await interaction.followup.send("❌ Solo el staff puede reabrir tickets.", ephemeral=True)
                except:
                    pass
            return

        # Obtener ticket_id del canal si no está disponible
        if not self.ticket_id or self.ticket_id == "persistent":
            self.ticket_id = self.get_ticket_id_from_channel(interaction.channel)

        if not self.ticket_id:
            try:
                await interaction.response.send_message("❌ No se pudo obtener el ID del ticket.", ephemeral=True)
            except:
                try:
                    await interaction.followup.send("❌ No se pudo obtener el ID del ticket.", ephemeral=True)
                except:
                    pass
            return

        try:
            ticket_data = self.load_ticket_data()
            if not ticket_data:
                try:
                    await interaction.response.send_message("❌ No se encontró el ticket.", ephemeral=True)
                except:
                    try:
                        await interaction.followup.send("❌ No se encontró el ticket.", ephemeral=True)
                    except:
                        pass
                return

            # Actualizar estado del ticket
            updates = {
                "status": "abierto",
                "estado_detallado": "reabierto_por_staff",
                "reopened_by": str(interaction.user.id),
                "reopened_at": datetime.utcnow().isoformat(),
                "historial": ticket_data.get("historial", []) + [{
                    "estado": "reabierto",
                    "timestamp": datetime.utcnow().isoformat(),
                    "detalles": f"Ticket reabierto por {interaction.user.name}"
                }]
            }

            self.update_ticket_data(updates)

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
            
            # Responder a la interacción
            try:
                if not interaction.response.is_done():
                    await interaction.response.edit_message(embed=embed, view=self)
                else:
                    await interaction.edit_original_message(embed=embed, view=self)
            except Exception as e:
                logger.error(f"Error editando mensaje en reopen_ticket: {e}")
                try:
                    if not interaction.response.is_done():
                        await interaction.response.send_message(embed=embed, view=self)
                    else:
                        await interaction.followup.send(embed=embed, view=self)
                except:
                    pass
            
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

    @nextcord.ui.button(label="🔒 Cerrar", style=nextcord.ButtonStyle.danger, row=1, custom_id="ticket_close")
    async def close_ticket(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        if not is_staff(interaction.user):
            try:
                await interaction.response.send_message("❌ Solo el staff puede cerrar tickets.", ephemeral=True)
            except:
                try:
                    await interaction.followup.send("❌ Solo el staff puede cerrar tickets.", ephemeral=True)
                except:
                    pass
            return

        # Obtener ticket_id del canal si no está disponible
        if not self.ticket_id or self.ticket_id == "persistent":
            self.ticket_id = self.get_ticket_id_from_channel(interaction.channel)

        if not self.ticket_id:
            try:
                await interaction.response.send_message("❌ No se pudo obtener el ID del ticket.", ephemeral=True)
            except:
                try:
                    await interaction.followup.send("❌ No se pudo obtener el ID del ticket.", ephemeral=True)
                except:
                    pass
            return

        try:
            ticket_data = self.load_ticket_data()
            if not ticket_data:
                try:
                    await interaction.response.send_message("❌ No se encontró el ticket.", ephemeral=True)
                except:
                    try:
                        await interaction.followup.send("❌ No se encontró el ticket.", ephemeral=True)
                    except:
                        pass
                return

            # Actualizar estado del ticket
            updates = {
                "status": "cerrado",
                "estado_detallado": "cerrado_por_staff",
                "closed_by": str(interaction.user.id),
                "closed_at": datetime.utcnow().isoformat(),
                "historial": ticket_data.get("historial", []) + [{
                    "estado": "cerrado",
                    "timestamp": datetime.utcnow().isoformat(),
                    "detalles": f"Ticket cerrado por {interaction.user.name}"
                }]
            }

            self.update_ticket_data(updates)

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
            
            # Responder a la interacción
            try:
                if not interaction.response.is_done():
                    await interaction.response.edit_message(embed=embed, view=self)
                else:
                    await interaction.edit_original_message(embed=embed, view=self)
            except Exception as e:
                logger.error(f"Error editando mensaje en close_ticket: {e}")
                try:
                    if not interaction.response.is_done():
                        await interaction.response.send_message(embed=embed, view=self)
                    else:
                        await interaction.followup.send(embed=embed, view=self)
                except:
                    pass
            
            # Enviar log
            await self.send_log_message(
                interaction, 
                "Ticket Cerrado", 
                f"El ticket {self.ticket_id} ha sido cerrado por {interaction.user.name}"
            )
            
            try:
                await enviar_transcripcion(interaction.channel, self.ticket_id, f"cerrado por {interaction.user.name}")
            except Exception as e:
                logger.error(f"Transcripción de {self.ticket_id} falló, el canal no se borra: {e}")
                await interaction.channel.send("⚠️ No se pudo guardar la transcripción; el canal **no** se borró. Bórralo a mano cuando la respaldes.")
                return

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
