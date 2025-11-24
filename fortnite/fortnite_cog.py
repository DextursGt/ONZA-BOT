"""
Cog principal de Fortnite para ONZA-BOT
Integra todos los módulos y comandos de Fortnite
"""

import nextcord
from nextcord.ext import commands
import logging
from typing import Optional

from .security import check_owner_permission, get_permission_error_message, OWNER_DISCORD_ID
from .auth import EpicAuth
from .accounts import FortniteAccountManager
from .friends import FortniteFriends
from .gifting import FortniteGifting
from .store import FortniteStore

log = logging.getLogger('fortnite-cog')


class GiftConfirmationView(nextcord.ui.View):
    """Vista con botones para confirmar o cancelar regalos"""
    
    def __init__(self, confirmation_id: str, gifting_manager: FortniteGifting, user_id: int):
        super().__init__(timeout=300)  # 5 minutos de timeout
        self.confirmation_id = confirmation_id
        self.gifting_manager = gifting_manager
        self.user_id = user_id
    
    @nextcord.ui.button(label="✅ Confirmar", style=nextcord.ButtonStyle.green)
    async def confirm_button(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        """Botón para confirmar el regalo"""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "❌ Solo el usuario que preparó el regalo puede confirmarlo.",
                ephemeral=True
            )
            return
        
        await interaction.response.defer(ephemeral=True)
        
        try:
            result = await self.gifting_manager.confirm_and_send_gift(self.confirmation_id)
            
            if result.get('success'):
                await interaction.followup.send(
                    f"✅ {result.get('message', 'Regalo enviado correctamente')}",
                    ephemeral=True
                )
                log.info(f"Regalo confirmado vía botón por {self.user_id}")
            else:
                await interaction.followup.send(
                    f"❌ {result.get('error', 'Error desconocido')}",
                    ephemeral=True
                )
            
            # Deshabilitar botones
            self.confirm_button.disabled = True
            self.cancel_button.disabled = True
            await interaction.edit_original_message(view=self)
            
        except Exception as e:
            log.error(f"Error confirmando regalo: {e}")
            await interaction.followup.send(
                f"❌ Error inesperado: {str(e)}",
                ephemeral=True
            )
    
    @nextcord.ui.button(label="❌ Cancelar", style=nextcord.ButtonStyle.red)
    async def cancel_button(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        """Botón para cancelar el regalo"""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "❌ Solo el usuario que preparó el regalo puede cancelarlo.",
                ephemeral=True
            )
            return
        
        try:
            if self.confirmation_id in self.gifting_manager.pending_confirmations:
                del self.gifting_manager.pending_confirmations[self.confirmation_id]
                await interaction.response.send_message(
                    "✅ Regalo cancelado.",
                    ephemeral=True
                )
                log.info(f"Regalo cancelado vía botón por {self.user_id}")
            else:
                await interaction.response.send_message(
                    "❌ Este regalo ya fue procesado o expiró.",
                    ephemeral=True
                )
            
            # Deshabilitar botones
            self.confirm_button.disabled = True
            self.cancel_button.disabled = True
            await interaction.edit_original_message(view=self)
            
        except Exception as e:
            log.error(f"Error cancelando regalo: {e}")
            await interaction.response.send_message(
                f"❌ Error inesperado: {str(e)}",
                ephemeral=True
            )


class FortniteCommands(commands.Cog):
    """Comandos de Fortnite - Solo para el owner del bot"""
    
    def __init__(self, bot: commands.Bot):
        """Inicializa el cog de Fortnite"""
        self.bot = bot
        self.account_manager = FortniteAccountManager()
        self.friends_manager = FortniteFriends()
        self.gifting_manager = FortniteGifting()
        self.store_manager = FortniteStore()
        log.info("Cog de Fortnite inicializado")
    
    def cog_check(self, ctx_or_interaction) -> bool:
        """
        Verifica permisos antes de ejecutar cualquier comando
        Solo el owner puede usar estos comandos
        """
        if not check_owner_permission(ctx_or_interaction):
            return False
        return True
    
    async def cog_command_error(self, ctx: commands.Context, error: Exception):
        """Maneja errores en comandos del cog"""
        if isinstance(error, commands.CheckFailure):
            await ctx.send(get_permission_error_message())
        else:
            log.error(f"Error en comando Fortnite: {error}")
            await ctx.send(f"❌ Error ejecutando comando: {str(error)}")
    
    # ==================== COMANDOS DE CUENTAS ====================
    
    @nextcord.slash_command(
        name="fn_add_account",
        description="Agregar una cuenta de Fortnite (máximo 5)"
    )
    async def fn_add_account(
        self,
        interaction: nextcord.Interaction,
        account_number: int = nextcord.SlashOption(
            description="Número de cuenta (1-5)",
            required=True,
            min_value=1,
            max_value=5
        ),
        account_name: str = nextcord.SlashOption(
            description="Nombre descriptivo de la cuenta",
            required=True
        ),
        device_code: str = nextcord.SlashOption(
            description="Código de dispositivo de OAuth",
            required=True
        ),
        user_code: str = nextcord.SlashOption(
            description="Código de usuario de OAuth",
            required=True
        )
    ):
        """Agrega una nueva cuenta de Fortnite"""
        if not check_owner_permission(interaction):
            await interaction.response.send_message(
                get_permission_error_message(),
                ephemeral=True
            )
            return
        
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Autenticar con Epic Games
            auth = EpicAuth()
            token_data = await auth.authenticate_with_device_code(device_code, user_code)
            
            if not token_data:
                await interaction.followup.send(
                    "❌ Error al autenticar con Epic Games. Verifica los códigos.",
                    ephemeral=True
                )
                await auth.close()
                return
            
            # Cifrar tokens
            encrypted_access = auth.encrypt_token(token_data['access_token'])
            encrypted_refresh = auth.encrypt_token(token_data['refresh_token'])
            
            # Agregar cuenta
            success = self.account_manager.add_account(
                account_number=account_number,
                account_name=account_name,
                encrypted_access_token=encrypted_access,
                encrypted_refresh_token=encrypted_refresh,
                account_id=token_data.get('account_id', ''),
                expires_at=token_data.get('expires_at', ''),
                device_id=token_data.get('device_id')
            )
            
            await auth.close()
            
            if success:
                await interaction.followup.send(
                    f"✅ Cuenta **{account_name}** (Número {account_number}) agregada correctamente.",
                    ephemeral=True
                )
                log.info(f"Cuenta {account_number} agregada por {interaction.user.id}")
            else:
                await interaction.followup.send(
                    "❌ Error al agregar cuenta. Verifica que el número no esté en uso y que no hayas alcanzado el límite de 5 cuentas.",
                    ephemeral=True
                )
                
        except Exception as e:
            log.error(f"Error en fn_add_account: {e}")
            await interaction.followup.send(
                f"❌ Error inesperado: {str(e)}",
                ephemeral=True
            )
    
    @nextcord.slash_command(
        name="fn_switch",
        description="Cambiar la cuenta activa de Fortnite"
    )
    async def fn_switch(
        self,
        interaction: nextcord.Interaction,
        account_number: int = nextcord.SlashOption(
            description="Número de cuenta a activar (1-5)",
            required=True,
            min_value=1,
            max_value=5
        )
    ):
        """Cambia la cuenta activa"""
        if not check_owner_permission(interaction):
            await interaction.response.send_message(
                get_permission_error_message(),
                ephemeral=True
            )
            return
        
        try:
            success = self.account_manager.switch_account(account_number)
            
            if success:
                account = self.account_manager.get_account(account_number)
                account_name = account.get('account_name', 'Unknown') if account else 'Unknown'
                
                await interaction.response.send_message(
                    f"✅ Cuenta activa cambiada a: **{account_name}** (Número {account_number})",
                    ephemeral=True
                )
                log.info(f"Cuenta {account_number} activada por {interaction.user.id}")
            else:
                await interaction.response.send_message(
                    f"❌ No se encontró la cuenta número {account_number}.",
                    ephemeral=True
                )
                
        except Exception as e:
            log.error(f"Error en fn_switch: {e}")
            await interaction.response.send_message(
                f"❌ Error inesperado: {str(e)}",
                ephemeral=True
            )
    
    @nextcord.slash_command(
        name="fn_list_accounts",
        description="Listar todas las cuentas de Fortnite registradas"
    )
    async def fn_list_accounts(self, interaction: nextcord.Interaction):
        """Lista todas las cuentas registradas"""
        if not check_owner_permission(interaction):
            await interaction.response.send_message(
                get_permission_error_message(),
                ephemeral=True
            )
            return
        
        try:
            accounts = self.account_manager.list_accounts()
            
            if not accounts:
                await interaction.response.send_message(
                    "📋 No hay cuentas registradas.",
                    ephemeral=True
                )
                return
            
            # Crear embed con la lista
            embed = nextcord.Embed(
                title="🎮 Cuentas de Fortnite",
                description=f"Total: {len(accounts)}/{FortniteAccountManager.MAX_ACCOUNTS}",
                color=0x00E5A8
            )
            
            for acc in accounts:
                status = "✅ Activa" if acc.get('is_active') else "⏸️ Inactiva"
                embed.add_field(
                    name=f"Cuenta #{acc.get('account_number')} - {acc.get('account_name')}",
                    value=f"ID: `{acc.get('account_id')}`\nEstado: {status}",
                    inline=False
                )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            log.error(f"Error en fn_list_accounts: {e}")
            await interaction.response.send_message(
                f"❌ Error inesperado: {str(e)}",
                ephemeral=True
            )
    
    # ==================== COMANDOS DE AMIGOS ====================
    
    @nextcord.slash_command(
        name="fn_add_friend",
        description="Agregar un amigo en Fortnite"
    )
    async def fn_add_friend(
        self,
        interaction: nextcord.Interaction,
        username: str = nextcord.SlashOption(
            description="Nombre de usuario de Epic Games",
            required=True
        )
    ):
        """Agrega un amigo en Fortnite"""
        if not check_owner_permission(interaction):
            await interaction.response.send_message(
                get_permission_error_message(),
                ephemeral=True
            )
            return
        
        await interaction.response.defer(ephemeral=True)
        
        try:
            user_id = interaction.user.id
            result = await self.friends_manager.add_friend(username, user_id)
            
            if result.get('success'):
                await interaction.followup.send(
                    f"✅ {result.get('message', 'Amigo agregado correctamente')}",
                    ephemeral=True
                )
                log.info(f"Amigo {username} agregado por {user_id}")
            else:
                await interaction.followup.send(
                    f"❌ {result.get('error', 'Error desconocido')}",
                    ephemeral=True
                )
                
        except Exception as e:
            log.error(f"Error en fn_add_friend: {e}")
            await interaction.followup.send(
                f"❌ Error inesperado: {str(e)}",
                ephemeral=True
            )
    
    @nextcord.slash_command(
        name="fn_list_friends",
        description="Listar todos los amigos en Fortnite"
    )
    async def fn_list_friends(self, interaction: nextcord.Interaction):
        """Lista todos los amigos"""
        if not check_owner_permission(interaction):
            await interaction.response.send_message(
                get_permission_error_message(),
                ephemeral=True
            )
            return
        
        await interaction.response.defer(ephemeral=True)
        
        try:
            user_id = interaction.user.id
            result = await self.friends_manager.list_friends(user_id)
            
            if result.get('success'):
                friends = result.get('friends', [])
                
                if not friends:
                    await interaction.followup.send(
                        "📋 No tienes amigos agregados.",
                        ephemeral=True
                    )
                    return
                
                # Crear embed con la lista
                embed = nextcord.Embed(
                    title="👥 Amigos de Fortnite",
                    description=f"Total: {len(friends)}",
                    color=0x00E5A8
                )
                
                # Agrupar por estado
                for friend in friends[:25]:  # Discord limita a 25 campos
                    status_emoji = "🟢" if friend.get('status') == 'ACCEPTED' else "🟡"
                    embed.add_field(
                        name=f"{status_emoji} {friend.get('display_name', 'Unknown')}",
                        value=f"ID: `{friend.get('account_id')}`",
                        inline=True
                    )
                
                await interaction.followup.send(embed=embed, ephemeral=True)
            else:
                await interaction.followup.send(
                    f"❌ {result.get('error', 'Error desconocido')}",
                    ephemeral=True
                )
                
        except Exception as e:
            log.error(f"Error en fn_list_friends: {e}")
            await interaction.followup.send(
                f"❌ Error inesperado: {str(e)}",
                ephemeral=True
            )
    
    # ==================== COMANDOS DE REGALOS ====================
    
    @nextcord.slash_command(
        name="fn_gift",
        description="Preparar un regalo (requiere confirmación)"
    )
    async def fn_gift(
        self,
        interaction: nextcord.Interaction,
        username: str = nextcord.SlashOption(
            description="Nombre de usuario del destinatario",
            required=True
        ),
        item_id: str = nextcord.SlashOption(
            description="ID del item a regalar",
            required=True
        )
    ):
        """Prepara un regalo y solicita confirmación"""
        if not check_owner_permission(interaction):
            await interaction.response.send_message(
                get_permission_error_message(),
                ephemeral=True
            )
            return
        
        await interaction.response.defer(ephemeral=True)
        
        try:
            user_id = interaction.user.id
            
            # Preparar regalo (no enviar todavía)
            prep_result = self.gifting_manager.prepare_gift(username, item_id, user_id)
            
            if not prep_result.get('success'):
                await interaction.followup.send(
                    f"❌ Error preparando regalo: {prep_result.get('error', 'Error desconocido')}",
                    ephemeral=True
                )
                return
            
            confirmation_id = prep_result['confirmation_id']
            gift_info = prep_result['gift_info']
            
            # Obtener información de cuota restante
            account = self.account_manager.get_account()
            if account:
                from .tos_validator import get_tos_validator
                tos_validator = get_tos_validator()
                remaining = tos_validator.get_remaining_quota('gift_send', account.get('account_id'))
                
                # Crear embed de confirmación
                embed = nextcord.Embed(
                    title="🎁 Confirmar Envío de Regalo",
                    description="**⚠️ IMPORTANTE: Revisa los detalles antes de confirmar**",
                    color=0xFFD700
                )
                
                embed.add_field(
                    name="👤 Destinatario",
                    value=f"`{username}`",
                    inline=True
                )
                
                embed.add_field(
                    name="🎮 Item ID",
                    value=f"`{item_id}`",
                    inline=True
                )
                
                embed.add_field(
                    name="💬 Mensaje",
                    value=gift_info.get('message', 'Sin mensaje'),
                    inline=False
                )
                
                if remaining >= 0:
                    embed.add_field(
                        name="📊 Cuota Restante Hoy",
                        value=f"{remaining} regalos",
                        inline=True
                    )
                
                embed.add_field(
                    name="🔐 Confirmation ID",
                    value=f"`{confirmation_id}`",
                    inline=False
                )
                
                embed.set_footer(text="Usa /fn_gift_confirm para confirmar o /fn_gift_cancel para cancelar")
                
                # Crear botones de confirmación
                view = GiftConfirmationView(confirmation_id, self.gifting_manager, user_id)
                
                await interaction.followup.send(
                    embed=embed,
                    view=view,
                    ephemeral=True
                )
                
                log.info(f"Regalo preparado para {username} por {user_id} (confirmation: {confirmation_id})")
            else:
                await interaction.followup.send(
                    "❌ No hay cuenta activa. Usa /fn_switch para activar una cuenta.",
                    ephemeral=True
                )
                
        except Exception as e:
            log.error(f"Error en fn_gift: {e}")
            await interaction.followup.send(
                f"❌ Error inesperado: {str(e)}",
                ephemeral=True
            )
    
    @nextcord.slash_command(
        name="fn_gift_confirm",
        description="Confirmar y enviar un regalo preparado"
    )
    async def fn_gift_confirm(
        self,
        interaction: nextcord.Interaction,
        confirmation_id: str = nextcord.SlashOption(
            description="ID de confirmación del regalo",
            required=True
        )
    ):
        """Confirma y envía un regalo previamente preparado"""
        if not check_owner_permission(interaction):
            await interaction.response.send_message(
                get_permission_error_message(),
                ephemeral=True
            )
            return
        
        await interaction.response.defer(ephemeral=True)
        
        try:
            user_id = interaction.user.id
            result = await self.gifting_manager.confirm_and_send_gift(confirmation_id)
            
            if result.get('success'):
                await interaction.followup.send(
                    f"✅ {result.get('message', 'Regalo enviado correctamente')}",
                    ephemeral=True
                )
                log.info(f"Regalo confirmado y enviado por {user_id} (confirmation: {confirmation_id})")
            else:
                await interaction.followup.send(
                    f"❌ {result.get('error', 'Error desconocido')}",
                    ephemeral=True
                )
                
        except Exception as e:
            log.error(f"Error en fn_gift_confirm: {e}")
            await interaction.followup.send(
                f"❌ Error inesperado: {str(e)}",
                ephemeral=True
            )
    
    @nextcord.slash_command(
        name="fn_gift_cancel",
        description="Cancelar un regalo preparado"
    )
    async def fn_gift_cancel(
        self,
        interaction: nextcord.Interaction,
        confirmation_id: str = nextcord.SlashOption(
            description="ID de confirmación del regalo a cancelar",
            required=True
        )
    ):
        """Cancela un regalo previamente preparado"""
        if not check_owner_permission(interaction):
            await interaction.response.send_message(
                get_permission_error_message(),
                ephemeral=True
            )
            return
        
        try:
            if confirmation_id in self.gifting_manager.pending_confirmations:
                del self.gifting_manager.pending_confirmations[confirmation_id]
                await interaction.response.send_message(
                    f"✅ Regalo con confirmation ID `{confirmation_id}` cancelado.",
                    ephemeral=True
                )
                log.info(f"Regalo cancelado por {interaction.user.id} (confirmation: {confirmation_id})")
            else:
                await interaction.response.send_message(
                    f"❌ No se encontró un regalo con confirmation ID `{confirmation_id}`.",
                    ephemeral=True
                )
                
        except Exception as e:
            log.error(f"Error en fn_gift_cancel: {e}")
            await interaction.response.send_message(
                f"❌ Error inesperado: {str(e)}",
                ephemeral=True
            )
    
    @nextcord.slash_command(
        name="fn_gift_message",
        description="Establecer mensaje personalizado para regalos"
    )
    async def fn_gift_message(
        self,
        interaction: nextcord.Interaction,
        message: str = nextcord.SlashOption(
            description="Mensaje a incluir con los regalos",
            required=True
        )
    ):
        """Establece el mensaje de regalos"""
        if not check_owner_permission(interaction):
            await interaction.response.send_message(
                get_permission_error_message(),
                ephemeral=True
            )
            return
        
        try:
            self.gifting_manager.set_gift_message(message)
            await interaction.response.send_message(
                f"✅ Mensaje de regalo actualizado: **{message}**",
                ephemeral=True
            )
            log.info(f"Mensaje de regalo actualizado por {interaction.user.id}")
            
        except Exception as e:
            log.error(f"Error en fn_gift_message: {e}")
            await interaction.response.send_message(
                f"❌ Error inesperado: {str(e)}",
                ephemeral=True
            )
    
    # ==================== COMANDOS DE TIENDA ====================
    
    @nextcord.slash_command(
        name="fn_store",
        description="Ver la tienda actual de Fortnite"
    )
    async def fn_store(self, interaction: nextcord.Interaction):
        """Muestra la tienda actual"""
        if not check_owner_permission(interaction):
            await interaction.response.send_message(
                get_permission_error_message(),
                ephemeral=True
            )
            return
        
        await interaction.response.defer(ephemeral=True)
        
        try:
            user_id = interaction.user.id
            result = await self.store_manager.get_store(user_id=user_id)
            
            if result.get('success'):
                items = result.get('items', [])
                
                if not items:
                    await interaction.followup.send(
                        "🛒 La tienda está vacía o no se pudieron obtener los items.",
                        ephemeral=True
                    )
                    return
                
                # Crear embed con la tienda
                embed = nextcord.Embed(
                    title="🛒 Tienda de Fortnite",
                    description=f"Items disponibles: {len(items)}",
                    color=0x00E5A8
                )
                
                # Mostrar primeros 10 items
                for item in items[:10]:
                    rarity_emoji = self._get_rarity_emoji(item.get('rarity', 'common'))
                    price_text = f"{item.get('price', 0)} V-Bucks"
                    if item.get('original_price', 0) > item.get('price', 0):
                        price_text += f" ~~{item.get('original_price')}~~"
                    
                    embed.add_field(
                        name=f"{rarity_emoji} {item.get('name', 'Unknown')}",
                        value=f"💰 {price_text}\n🆔 `{item.get('item_id', 'N/A')}`",
                        inline=False
                    )
                
                if len(items) > 10:
                    embed.set_footer(text=f"Mostrando 10 de {len(items)} items. Usa /fn_item_info para más detalles.")
                
                await interaction.followup.send(embed=embed, ephemeral=True)
            else:
                await interaction.followup.send(
                    f"❌ {result.get('error', 'Error desconocido')}",
                    ephemeral=True
                )
                
        except Exception as e:
            log.error(f"Error en fn_store: {e}")
            await interaction.followup.send(
                f"❌ Error inesperado: {str(e)}",
                ephemeral=True
            )
    
    @nextcord.slash_command(
        name="fn_item_info",
        description="Obtener información detallada de un item"
    )
    async def fn_item_info(
        self,
        interaction: nextcord.Interaction,
        item_id: str = nextcord.SlashOption(
            description="ID del item",
            required=True
        )
    ):
        """Obtiene información de un item"""
        if not check_owner_permission(interaction):
            await interaction.response.send_message(
                get_permission_error_message(),
                ephemeral=True
            )
            return
        
        await interaction.response.defer(ephemeral=True)
        
        try:
            user_id = interaction.user.id
            result = await self.store_manager.get_item_info(item_id, user_id)
            
            if result.get('success'):
                item = result.get('item', {})
                
                embed = nextcord.Embed(
                    title=f"📦 {item.get('name', 'Unknown')}",
                    description=item.get('description', 'Sin descripción'),
                    color=self._get_rarity_color(item.get('rarity', 'common'))
                )
                
                rarity_emoji = self._get_rarity_emoji(item.get('rarity', 'common'))
                embed.add_field(
                    name="Rareza",
                    value=f"{rarity_emoji} {item.get('rarity', 'common').upper()}",
                    inline=True
                )
                
                embed.add_field(
                    name="Tipo",
                    value=item.get('type', 'unknown').upper(),
                    inline=True
                )
                
                price_text = f"{item.get('price', 0)} V-Bucks"
                if item.get('original_price', 0) > item.get('price', 0):
                    price_text += f"\n~~Precio original: {item.get('original_price')} V-Bucks~~"
                
                embed.add_field(
                    name="Precio",
                    value=price_text,
                    inline=False
                )
                
                embed.add_field(
                    name="Item ID",
                    value=f"`{item_id}`",
                    inline=False
                )
                
                if item.get('image_url'):
                    embed.set_image(url=item.get('image_url'))
                
                await interaction.followup.send(embed=embed, ephemeral=True)
            else:
                await interaction.followup.send(
                    f"❌ {result.get('error', 'Item no encontrado')}",
                    ephemeral=True
                )
                
        except Exception as e:
            log.error(f"Error en fn_item_info: {e}")
            await interaction.followup.send(
                f"❌ Error inesperado: {str(e)}",
                ephemeral=True
            )
    
    # ==================== UTILIDADES ====================
    
    def _get_rarity_emoji(self, rarity: str) -> str:
        """Obtiene el emoji correspondiente a la rareza"""
        rarity_map = {
            'common': '⚪',
            'uncommon': '🟢',
            'rare': '🔵',
            'epic': '🟣',
            'legendary': '🟠',
            'mythic': '🔴',
            'exotic': '🟡'
        }
        return rarity_map.get(rarity.lower(), '⚪')
    
    def _get_rarity_color(self, rarity: str) -> int:
        """Obtiene el color correspondiente a la rareza"""
        color_map = {
            'common': 0x808080,      # Gris
            'uncommon': 0x00FF00,     # Verde
            'rare': 0x0080FF,         # Azul
            'epic': 0x8000FF,         # Morado
            'legendary': 0xFF8000,    # Naranja
            'mythic': 0xFF0000,       # Rojo
            'exotic': 0xFFFF00        # Amarillo
        }
        return color_map.get(rarity.lower(), 0x00E5A8)
    
    def cog_unload(self):
        """Limpia recursos al descargar el cog"""
        log.info("Cog de Fortnite descargado, cerrando conexiones...")
        # Cerrar conexiones asíncronas si es necesario
        # Nota: Esto se ejecuta de forma síncrona, las conexiones se cerrarán en el próximo ciclo


def setup(bot: commands.Bot):
    """Setup del cog"""
    bot.add_cog(FortniteCommands(bot))
    log.info("Cog de Fortnite cargado")

