"""Base ticket view with shared functionality."""
import io
import nextcord
from datetime import datetime
from typing import Optional
from utils import logger
from data_manager import load_data, save_data
from config import TICKETS_LOG_CHANNEL_ID


async def enviar_transcripcion(channel, ticket_id: str, motivo: str):
    """Sube la conversación del ticket (y sus adjuntos) al canal de logs. Lanza excepción si no se pudo:
    quien llama NO debe borrar el canal en ese caso, porque ahí viven los comprobantes de pago."""
    log_channel = channel.guild.get_channel(TICKETS_LOG_CHANNEL_ID) if TICKETS_LOG_CHANNEL_ID else None
    if not log_channel:
        raise RuntimeError("TICKETS_LOG_CHANNEL_ID no configurado o canal inexistente")

    lineas, adjuntos = [], []
    async for m in channel.history(limit=None, oldest_first=True):
        texto = m.content or ""
        if m.embeds and not texto:
            texto = f"[embed] {m.embeds[0].title or ''}"
        if m.attachments:
            texto += " " + " ".join(f"[adjunto: {a.filename}]" for a in m.attachments)
            adjuntos += m.attachments
        lineas.append(f"[{m.created_at:%Y-%m-%d %H:%M} UTC] {m.author}: {texto}")

    archivo = nextcord.File(io.BytesIO("\n".join(lineas).encode("utf-8")), filename=f"{ticket_id}.txt")
    await log_channel.send(f"📄 Transcripción de **{ticket_id}** (`{channel.name}`) — {motivo}", file=archivo)
    # Los enlaces de Discord a adjuntos caducan; se vuelven a subir. shortcut: los de más de 8 MB se omiten.
    subibles = [a for a in adjuntos if a.size <= 8_000_000]
    for i in range(0, len(subibles), 10):
        await log_channel.send(files=[await a.to_file() for a in subibles[i:i + 10]])


class BaseTicketView(nextcord.ui.View):
    """Base class for all ticket views with common functionality."""

    def __init__(self, ticket_id: str = "persistent", timeout: Optional[int] = None):
        super().__init__(timeout=timeout)
        self.ticket_id = ticket_id
        self._persistent = ticket_id == "persistent"

    async def interaction_check(self, interaction: nextcord.Interaction) -> bool:
        # La vista persistente es una sola instancia para todos los canales: resolver el ticket en cada clic.
        # shortcut: dos clics simultáneos en canales distintos podrían cruzarse; pasar ticket_id por argumento si pasa.
        if self._persistent:
            self.ticket_id = self.get_ticket_id_from_channel(interaction.channel)
        return True

    def get_ticket_id_from_channel(self, channel) -> Optional[str]:
        """Busca la clave del ticket ("ticket-N") cuyo canal es este."""
        try:
            for ticket_id, ticket in load_data().get("tickets", {}).items():
                if str(ticket.get("channel_id")) == str(channel.id):
                    return ticket_id
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
