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
        # Inicializar como None primero para que los comandos se registren
        self.account_manager = None
        self.friends_manager = None
        self.gifting_manager = None
        self.store_manager = None
        
        # Intentar inicializar los módulos
        try:
            self.account_manager = FortniteAccountManager()
            self.friends_manager = FortniteFriends()
            self.gifting_manager = FortniteGifting()
            self.store_manager = FortniteStore()
            log.info("Cog de Fortnite inicializado correctamente")
        except Exception as e:
            log.error(f"Error inicializando módulos de Fortnite: {e}")
            import traceback
            log.error(f"Traceback: {traceback.format_exc()}")
            # Los módulos quedan como None, pero los comandos se registrarán
            log.warning("⚠️ Módulos de Fortnite no inicializados, pero comandos disponibles")
    
    async def cog_check(self, ctx) -> bool:
        """
        Verifica permisos antes de ejecutar cualquier comando
        Solo el owner puede usar estos comandos
        """
        # Verificar permisos del owner
        if not check_owner_permission(ctx):
            await ctx.send(get_permission_error_message())
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
    
    @commands.command(name="fn_add_account")
    async def fn_add_account(self, ctx, account_number: int, account_name: str, device_code: str, user_code: str):
        """Agregar una cuenta de Fortnite (máximo 5)
        
        Uso: !fn_add_account <número> <nombre> <device_code> <user_code>
        Ejemplo: !fn_add_account 1 "Mi Cuenta" abc123 xyz789
        """
        if not check_owner_permission(ctx):
            await ctx.send(get_permission_error_message())
            return
        
        if not (1 <= account_number <= 5):
            await ctx.send("❌ El número de cuenta debe estar entre 1 y 5.")
            return
        
        try:
            await ctx.send("🔄 Autenticando con Epic Games...")
            
            # Autenticar con Epic Games
            auth = EpicAuth()
            token_data = await auth.authenticate_with_device_code(device_code, user_code)
            
            if not token_data:
                await ctx.send("❌ Error al autenticar con Epic Games. Verifica los códigos.")
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
                await ctx.send(f"✅ Cuenta **{account_name}** (Número {account_number}) agregada correctamente.")
                log.info(f"Cuenta {account_number} agregada por {ctx.author.id}")
            else:
                await ctx.send("❌ Error al agregar cuenta. Verifica que el número no esté en uso y que no hayas alcanzado el límite de 5 cuentas.")
                
        except Exception as e:
            log.error(f"Error en fn_add_account: {e}")
            await ctx.send(f"❌ Error inesperado: {str(e)}")
    
    @commands.command(name="fn_switch")
    async def fn_switch(self, ctx, account_number: int):
        """Cambiar la cuenta activa de Fortnite
        
        Uso: !fn_switch <número>
        Ejemplo: !fn_switch 1
        """
        if not check_owner_permission(ctx):
            await ctx.send(get_permission_error_message())
            return
        
        if not (1 <= account_number <= 5):
            await ctx.send("❌ El número de cuenta debe estar entre 1 y 5.")
            return
        
        try:
            success = self.account_manager.switch_account(account_number)
            
            if success:
                account = self.account_manager.get_account(account_number)
                account_name = account.get('account_name', 'Unknown') if account else 'Unknown'
                
                await ctx.send(f"✅ Cuenta activa cambiada a: **{account_name}** (Número {account_number})")
                log.info(f"Cuenta {account_number} activada por {ctx.author.id}")
            else:
                await ctx.send(f"❌ No se encontró la cuenta número {account_number}.")
                
        except Exception as e:
            log.error(f"Error en fn_switch: {e}")
            await ctx.send(f"❌ Error inesperado: {str(e)}")
    
    @commands.command(name="fn_list_accounts")
    async def fn_list_accounts(self, ctx):
        """Listar todas las cuentas de Fortnite registradas
        
        Uso: !fn_list_accounts
        """
        if not check_owner_permission(ctx):
            await ctx.send(get_permission_error_message())
            return
        
        # Inicializar account_manager si no está inicializado
        if self.account_manager is None:
            try:
                self.account_manager = FortniteAccountManager()
            except Exception as e:
                log.error(f"Error inicializando account_manager: {e}")
                await ctx.send("❌ Error inicializando módulo de cuentas.")
                return
        
        try:
            accounts = self.account_manager.list_accounts()
            
            if not accounts:
                await ctx.send("📋 No hay cuentas registradas.")
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
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            log.error(f"Error en fn_list_accounts: {e}")
            await ctx.send(f"❌ Error inesperado: {str(e)}")
    
    # ==================== COMANDOS DE AMIGOS ====================
    
    @commands.command(name="fn_add_friend")
    async def fn_add_friend(self, ctx, username: str):
        """Agregar un amigo en Fortnite
        
        Uso: !fn_add_friend <username>
        Ejemplo: !fn_add_friend jugador123
        """
        if not check_owner_permission(ctx):
            await ctx.send(get_permission_error_message())
            return
        
        try:
            await ctx.send(f"🔄 Agregando amigo {username}...")
            user_id = ctx.author.id
            result = await self.friends_manager.add_friend(username, user_id)
            
            if result.get('success'):
                await ctx.send(f"✅ {result.get('message', 'Amigo agregado correctamente')}")
                log.info(f"Amigo {username} agregado por {user_id}")
            else:
                await ctx.send(f"❌ {result.get('error', 'Error desconocido')}")
                
        except Exception as e:
            log.error(f"Error en fn_add_friend: {e}")
            await ctx.send(f"❌ Error inesperado: {str(e)}")
    
    @commands.command(name="fn_list_friends")
    async def fn_list_friends(self, ctx):
        """Listar todos los amigos en Fortnite
        
        Uso: !fn_list_friends
        """
        if not check_owner_permission(ctx):
            await ctx.send(get_permission_error_message())
            return
        
        try:
            await ctx.send("🔄 Obteniendo lista de amigos...")
            user_id = ctx.author.id
            result = await self.friends_manager.list_friends(user_id)
            
            if result.get('success'):
                friends = result.get('friends', [])
                
                if not friends:
                    await ctx.send("📋 No tienes amigos agregados.")
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
                
                await ctx.send(embed=embed)
            else:
                await ctx.send(f"❌ {result.get('error', 'Error desconocido')}")
                
        except Exception as e:
            log.error(f"Error en fn_list_friends: {e}")
            await ctx.send(f"❌ Error inesperado: {str(e)}")
    
    # ==================== COMANDOS DE REGALOS ====================
    
    @commands.command(name="fn_gift")
    async def fn_gift(self, ctx, username: str, item_id: str):
        """Preparar un regalo (requiere confirmación)
        
        Uso: !fn_gift <username> <item_id>
        Ejemplo: !fn_gift jugador123 AthenaCharacter:cid_001
        """
        if not check_owner_permission(ctx):
            await ctx.send(get_permission_error_message())
            return
        
        try:
            await ctx.send(f"🔄 Preparando regalo para {username}...")
            user_id = ctx.author.id
            
            # Preparar regalo (no enviar todavía)
            prep_result = self.gifting_manager.prepare_gift(username, item_id, user_id)
            
            if not prep_result.get('success'):
                await ctx.send(f"❌ Error preparando regalo: {prep_result.get('error', 'Error desconocido')}")
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
                
                embed.set_footer(text="Usa !fn_gift_confirm <confirmation_id> para confirmar o !fn_gift_cancel <confirmation_id> para cancelar")
                
                # Crear botones de confirmación
                view = GiftConfirmationView(confirmation_id, self.gifting_manager, user_id)
                
                await ctx.send(embed=embed, view=view)
                
                log.info(f"Regalo preparado para {username} por {user_id} (confirmation: {confirmation_id})")
            else:
                await ctx.send("❌ No hay cuenta activa. Usa !fn_switch para activar una cuenta.")
                
        except Exception as e:
            log.error(f"Error en fn_gift: {e}")
            await ctx.send(f"❌ Error inesperado: {str(e)}")
    
    @commands.command(name="fn_gift_confirm")
    async def fn_gift_confirm(self, ctx, confirmation_id: str):
        """Confirmar y enviar un regalo preparado
        
        Uso: !fn_gift_confirm <confirmation_id>
        Ejemplo: !fn_gift_confirm abc123xyz
        """
        if not check_owner_permission(ctx):
            await ctx.send(get_permission_error_message())
            return
        
        try:
            await ctx.send(f"🔄 Confirmando y enviando regalo...")
            user_id = ctx.author.id
            result = await self.gifting_manager.confirm_and_send_gift(confirmation_id)
            
            if result.get('success'):
                await ctx.send(f"✅ {result.get('message', 'Regalo enviado correctamente')}")
                log.info(f"Regalo confirmado y enviado por {user_id} (confirmation: {confirmation_id})")
            else:
                await ctx.send(f"❌ {result.get('error', 'Error desconocido')}")
                
        except Exception as e:
            log.error(f"Error en fn_gift_confirm: {e}")
            await ctx.send(f"❌ Error inesperado: {str(e)}")
    
    @commands.command(name="fn_gift_cancel")
    async def fn_gift_cancel(self, ctx, confirmation_id: str):
        """Cancelar un regalo preparado
        
        Uso: !fn_gift_cancel <confirmation_id>
        Ejemplo: !fn_gift_cancel abc123xyz
        """
        if not check_owner_permission(ctx):
            await ctx.send(get_permission_error_message())
            return
        
        try:
            if confirmation_id in self.gifting_manager.pending_confirmations:
                del self.gifting_manager.pending_confirmations[confirmation_id]
                await ctx.send(f"✅ Regalo con confirmation ID `{confirmation_id}` cancelado.")
                log.info(f"Regalo cancelado por {ctx.author.id} (confirmation: {confirmation_id})")
            else:
                await ctx.send(f"❌ No se encontró un regalo con confirmation ID `{confirmation_id}`.")
                
        except Exception as e:
            log.error(f"Error en fn_gift_cancel: {e}")
            await ctx.send(f"❌ Error inesperado: {str(e)}")
    
    @commands.command(name="fn_gift_message")
    async def fn_gift_message(self, ctx, *, message: str):
        """Establecer mensaje personalizado para regalos
        
        Uso: !fn_gift_message <mensaje>
        Ejemplo: !fn_gift_message ¡Disfruta tu regalo!
        """
        if not check_owner_permission(ctx):
            await ctx.send(get_permission_error_message())
            return
        
        try:
            self.gifting_manager.set_gift_message(message)
            await ctx.send(f"✅ Mensaje de regalo actualizado: **{message}**")
            log.info(f"Mensaje de regalo actualizado por {ctx.author.id}")
            
        except Exception as e:
            log.error(f"Error en fn_gift_message: {e}")
            await ctx.send(f"❌ Error inesperado: {str(e)}")
    
    # ==================== COMANDOS DE TIENDA ====================
    
    @commands.command(name="fn_store")
    async def fn_store(self, ctx):
        """Ver la tienda actual de Fortnite
        
        Uso: !fn_store
        """
        if not check_owner_permission(ctx):
            await ctx.send(get_permission_error_message())
            return
        
        try:
            await ctx.send("🔄 Obteniendo tienda de Fortnite...")
            user_id = ctx.author.id
            result = await self.store_manager.get_store(user_id=user_id)
            
            if result.get('success'):
                items = result.get('items', [])
                
                if not items:
                    await ctx.send("🛒 La tienda está vacía o no se pudieron obtener los items.")
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
                    embed.set_footer(text=f"Mostrando 10 de {len(items)} items. Usa !fn_item_info <item_id> para más detalles.")
                
                await ctx.send(embed=embed)
            else:
                await ctx.send(f"❌ {result.get('error', 'Error desconocido')}")
                
        except Exception as e:
            log.error(f"Error en fn_store: {e}")
            await ctx.send(f"❌ Error inesperado: {str(e)}")
    
    @commands.command(name="fn_item_info")
    async def fn_item_info(self, ctx, item_id: str):
        """Obtener información detallada de un item
        
        Uso: !fn_item_info <item_id>
        Ejemplo: !fn_item_info AthenaCharacter:cid_001
        """
        if not check_owner_permission(ctx):
            await ctx.send(get_permission_error_message())
            return
        
        try:
            await ctx.send(f"🔄 Obteniendo información del item {item_id}...")
            user_id = ctx.author.id
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
                
                await ctx.send(embed=embed)
            else:
                await ctx.send(f"❌ {result.get('error', 'Item no encontrado')}")
                
        except Exception as e:
            log.error(f"Error en fn_item_info: {e}")
            await ctx.send(f"❌ Error inesperado: {str(e)}")
    
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

