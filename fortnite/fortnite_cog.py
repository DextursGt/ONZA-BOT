"""
Cog principal de Fortnite para ONZA-BOT
Integra todos los módulos y comandos de Fortnite
"""

import nextcord
from nextcord.ext import commands
import logging
from typing import Optional
from datetime import datetime

from .security import check_owner_permission, get_permission_error_message, OWNER_DISCORD_ID
from .auth import EpicAuth
from .oauth import EpicOAuth
from .accounts import FortniteAccountManager
from .friends import FortniteFriends
from .gifting import FortniteGifting
from .store import FortniteStore

log = logging.getLogger('fortnite-cog')


class StorePaginationView(nextcord.ui.View):
    """Vista con botones para navegar entre páginas de la tienda"""
    
    def __init__(self, items: list, items_per_page: int = 10, user_id: int = 0):
        super().__init__(timeout=300)  # 5 minutos de timeout
        self.items = items
        self.items_per_page = items_per_page
        self.current_page = 0
        self.user_id = user_id
        self.total_pages = (len(items) + items_per_page - 1) // items_per_page
        self.update_buttons()
    
    def update_buttons(self):
        """Actualiza el estado de los botones según la página actual"""
        self.previous_button.disabled = self.current_page == 0
        self.next_button.disabled = self.current_page >= self.total_pages - 1
    
    def get_page_items(self) -> list:
        """Obtiene los items de la página actual"""
        start = self.current_page * self.items_per_page
        end = start + self.items_per_page
        return self.items[start:end]
    
    def create_embed(self) -> nextcord.Embed:
        """Crea el embed para la página actual"""
        page_items = self.get_page_items()
        
        embed = nextcord.Embed(
            title="🛒 Tienda de Fortnite",
            description=f"Página {self.current_page + 1} de {self.total_pages} | Total: {len(self.items)} items",
            color=0x00E5A8
        )
        
        for item in page_items:
            rarity_emoji = self._get_rarity_emoji(item.get('rarity', 'common'))
            price = item.get('price', 0)
            original_price = item.get('original_price', 0)
            item_id = item.get('item_id', 'N/A')
            offer_id = item.get('offer_id', '')
            name = item.get('name', 'Unknown')
            
            # Formato de precio
            if price > 0:
                price_text = f"💰 **{price} V-Bucks**"
                if original_price > price:
                    price_text += f" ~~{original_price}~~"
            else:
                price_text = "💰 Precio no disponible"
            
            # Formato del campo con ID para regalos
            id_text = f"🆔 ID: `{item_id}`"
            if offer_id and offer_id != item_id:
                id_text += f"\n📦 Offer ID: `{offer_id}`"
            
            embed.add_field(
                name=f"{rarity_emoji} {name}",
                value=f"{price_text}\n{id_text}",
                inline=False
            )
        
        if page_items and page_items[0].get('image_url'):
            embed.set_thumbnail(url=page_items[0].get('image_url'))
        
        embed.set_footer(text=f"Usa !fn_gift <username> <item_id> para enviar un regalo")
        return embed
    
    def _get_rarity_emoji(self, rarity: str) -> str:
        """Obtiene el emoji según la rareza"""
        rarity_emojis = {
            'common': '⚪',
            'uncommon': '🟢',
            'rare': '🔵',
            'epic': '🟣',
            'legendary': '🟠',
            'mythic': '🔴',
            'marvel': '⭐',
            'gaminglegends': '🎮',
            'icon': '💎'
        }
        return rarity_emojis.get(rarity.lower(), '⚪')
    
    @nextcord.ui.button(label="◀️ Anterior", style=nextcord.ButtonStyle.secondary, row=0)
    async def previous_button(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        """Botón para ir a la página anterior"""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Solo el usuario que ejecutó el comando puede navegar.", ephemeral=True)
            return
        
        if self.current_page > 0:
            self.current_page -= 1
            self.update_buttons()
            embed = self.create_embed()
            await interaction.response.edit_message(embed=embed, view=self)
    
    @nextcord.ui.button(label="Siguiente ▶️", style=nextcord.ButtonStyle.secondary, row=0)
    async def next_button(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        """Botón para ir a la página siguiente"""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Solo el usuario que ejecutó el comando puede navegar.", ephemeral=True)
            return
        
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            self.update_buttons()
            embed = self.create_embed()
            await interaction.response.edit_message(embed=embed, view=self)


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
        # Inicializar como None - se inicializarán bajo demanda en los comandos
        # Esto asegura que los comandos se registren incluso si hay errores de inicialización
        self.account_manager = None
        self.friends_manager = None
        self.gifting_manager = None
        self.store_manager = None
        
        log.info("✅ Cog de Fortnite creado - Los módulos se inicializarán bajo demanda")
    
    # TEMPORALMENTE DESHABILITADO para diagnosticar problema de registro
    # def cog_check(self, ctx) -> bool:
    #     """
    #     Verifica permisos antes de ejecutar cualquier comando
    #     Solo el owner puede usar estos comandos
    #     """
    #     return check_owner_permission(ctx)
    
    async def cog_command_error(self, ctx: commands.Context, error: Exception):
        """Maneja errores en comandos del cog"""
        if isinstance(error, commands.CheckFailure):
            await ctx.send(get_permission_error_message())
        else:
            log.error(f"Error en comando Fortnite: {error}")
            await ctx.send(f"❌ Error ejecutando comando: {str(error)}")
    
    # ==================== COMANDOS DE AUTENTICACIÓN OAUTH ====================
    
    @commands.command(name="fn_list")
    async def fn_list(self, ctx):
        """Lista todos los comandos de Fortnite disponibles
        
        Uso: !fn_list
        """
        if not check_owner_permission(ctx):
            await ctx.send(get_permission_error_message())
            return
        
        try:
            embed = nextcord.Embed(
                title="📋 Lista de Comandos de Fortnite",
                description="Todos los comandos disponibles para gestionar tus cuentas de Fortnite",
                color=0x00E5A8,
                timestamp=nextcord.utils.utcnow()
            )
            
                   # Categoría: Autenticación DeviceAuth
                   auth_commands = (
                       "`!fn_test_login` - Valida login con DeviceAuth\n"
                       "`!fn_token_info` - Muestra información de tokens actuales\n"
                   )
                   embed.add_field(
                       name="🔐 Autenticación DeviceAuth",
                       value=auth_commands,
                       inline=False
                   )
            
            # Categoría: Gestión de Cuentas
            account_commands = (
                "`!fn_list_accounts` - Lista todas las cuentas guardadas\n"
                "`!fn_switch <número>` - Cambia la cuenta activa (1-5)\n"
                "`!fn_rename_account <número> <nombre>` - Cambia el nombre de una cuenta\n"
                "`!fn_delete_account <número>` - Elimina una cuenta guardada\n"
            )
            embed.add_field(
                name="👤 Gestión de Cuentas",
                value=account_commands,
                inline=False
            )
            
            # Categoría: Amigos
            friends_commands = (
                "`!fn_add_friend <username>` - Agrega un amigo en Fortnite\n"
                "`!fn_list_friends` - Lista todos tus amigos\n"
            )
            embed.add_field(
                name="👥 Amigos",
                value=friends_commands,
                inline=False
            )
            
            # Categoría: Regalos
            gifting_commands = (
                "`!fn_gift <username> <item_id>` - Prepara un regalo\n"
                "`!fn_gift_confirm <id>` - Confirma y envía un regalo preparado\n"
                "`!fn_gift_cancel <id>` - Cancela un regalo preparado\n"
                "`!fn_gift_message <mensaje>` - Establece mensaje para regalos\n"
            )
            embed.add_field(
                name="🎁 Regalos",
                value=gifting_commands,
                inline=False
            )
            
            # Categoría: Tienda
            store_commands = (
                "`!fn_store` - Ver la tienda actual de Fortnite\n"
                "`!fn_item_info <item_id>` - Obtener información de un item\n"
            )
            embed.add_field(
                name="🛒 Tienda",
                value=store_commands,
                inline=False
            )
            
            embed.set_footer(
                text=f"Total: 18 comandos disponibles | Solo para el owner del bot"
            )
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            log.error(f"Error en fn_list: {e}")
            import traceback
            log.error(f"Traceback: {traceback.format_exc()}")
            await ctx.send(f"❌ Error inesperado: {str(e)}")
    
    @commands.command(name="fn_login")
    async def fn_login(self, ctx: commands.Context):
        """
        Genera URL de autorización OAuth con PKCE para Fortnite
        Usa Authorization Code Flow con PKCE (sin client_secret)
        
        Uso: !fn_login
        """
        if not check_owner_permission(ctx):
            await ctx.send(get_permission_error_message())
            return
        
        # Inicializar oauth_manager si no está inicializado
        if self.oauth_manager is None:
            try:
                from .oauth import EpicOAuth
                self.oauth_manager = EpicOAuth()
            except Exception as e:
                log.error(f"Error inicializando oauth_manager: {e}")
                await ctx.send("❌ Error inicializando módulo OAuth.")
                return
        
        try:
            await ctx.send("🔄 Generando URL de autorización OAuth con PKCE...")
            
            # Logs de debugging
            log.info(f"[DEBUG] !fn_login ejecutado por usuario {ctx.author.id}")
            log.info(f"[DEBUG] Usando Authorization Code Flow con PKCE")
            
            # Generar URL de login con PKCE
            login_url, state, code_verifier = self.oauth_manager.generate_login_url(ctx.author.id)
            
            # Crear embed con instrucciones
            embed = nextcord.Embed(
                title="🔐 Login de Epic Games / Fortnite (OAuth con PKCE)",
                description="Sigue estos pasos para autenticarte usando Authorization Code Flow:",
                color=nextcord.Color.blue(),
                timestamp=nextcord.utils.utcnow()
            )
            
            embed.add_field(
                name="📋 Pasos para Autenticarte",
                value="1. Haz clic en el botón **🔗 Autorizar** (abajo)\n"
                      "2. Inicia sesión con tu cuenta de Epic Games\n"
                      "3. Autoriza la aplicación\n"
                      "4. **Después de autorizar**, serás redirigido a una URL\n"
                      "5. **Copia el código `code=` de la URL** (ejemplo: `?code=ABC123...`)\n"
                      "6. Usa el comando: `!fn_code <código>` con el código copiado",
                inline=False
            )
            
            embed.add_field(
                name="🔗 URL de Autorización",
                value=f"[Haz clic aquí para autorizar]({login_url})",
                inline=False
            )
            
            embed.add_field(
                name="📝 Ejemplo de URL después de autorizar",
                value="`http://localhost:4000/callback?code=ABC123XYZ789&state=...`\n\n"
                      "**Copia solo la parte del `code=`** (ejemplo: `ABC123XYZ789`)",
                inline=False
            )
            
            embed.add_field(
                name="🔑 State (para verificación)",
                value=f"`{state}`\n\nEste código se usa para verificar la autorización",
                inline=False
            )
            
            embed.set_footer(text="El código de autorización expira en 10 minutos")
            
            # Crear botón de Login que abre la URL de autorización
            view = nextcord.ui.View()
            view.add_item(nextcord.ui.Button(
                label="🔗 Autorizar en Epic Games",
                url=login_url,
                style=nextcord.ButtonStyle.link
            ))
            
            await ctx.send(embed=embed, view=view)
            log.info(f"URL de autorización OAuth con PKCE generada para {ctx.author.id}")
            log.info(f"[DEBUG] AUTH URL: {login_url[:100]}...")
            log.info(f"[DEBUG] STATE: {state[:20]}...")
            
        except Exception as e:
            log.error(f"[DEBUG] EXCEPTION en fn_login: {e}")
            import traceback
            log.error(f"[DEBUG] TRACEBACK: {traceback.format_exc()}")
            log.error(f"Error en fn_login: {e}")
            await ctx.send(f"❌ Error generando URL de autorización: {str(e)}")
    
    @commands.command(name="fn_code")
    async def fn_code(self, ctx: commands.Context, authorization_code: str):
        """
        Intercambia código de autorización por tokens (método similar a bots de Telegram)
        
        Uso: !fn_code <código_de_32_dígitos>
        Ejemplo: !fn_code 1a1aa1a1111aaaaaaa11111a1aaaaaa1
        """
        if not check_owner_permission(ctx):
            await ctx.send(get_permission_error_message())
            return
        
        # Inicializar módulos si no están inicializados
        if self.account_manager is None:
            try:
                self.account_manager = FortniteAccountManager()
            except Exception as e:
                log.error(f"Error inicializando account_manager: {e}")
                await ctx.send("❌ Error inicializando módulo de cuentas.")
                return
        
        try:
            user_id = ctx.author.id
            log.info(f"[DEBUG] OAuth callback received - User ID: {user_id}, Code: {authorization_code[:10]}...")
            await ctx.send("🔄 Intercambiando código por tokens...")
            
            # Intercambiar código de autorización por tokens
            auth = EpicAuth()
            log.info(f"[DEBUG] Calling exchange_authorization_code with code: {authorization_code[:10]}...")
            token_data = await auth.exchange_authorization_code(authorization_code)
            
            if not token_data:
                log.error(f"[DEBUG] exchange_authorization_code returned None for user {user_id}")
                await ctx.send("❌ Error al intercambiar código. Verifica que:\n"
                              "• El código sea correcto (32 dígitos)\n"
                              "• Hayas hecho clic en Login y autorizado\n"
                              "• El código no haya expirado")
                await auth.close()
                return
            
            # Log tokens recibidos (mascarados para seguridad)
            access_token_masked = f"{token_data.get('access_token', '')[:10]}...{token_data.get('access_token', '')[-5:]}" if token_data.get('access_token') else 'None'
            refresh_token_masked = f"{token_data.get('refresh_token', '')[:10]}...{token_data.get('refresh_token', '')[-5:]}" if token_data.get('refresh_token') else 'None'
            log.info(f"[DEBUG] Received access_token: {access_token_masked}")
            log.info(f"[DEBUG] Received refresh_token: {refresh_token_masked}")
            log.info(f"[DEBUG] Received account_id: {token_data.get('account_id', 'None')}")
            log.info(f"[DEBUG] Received display_name: {token_data.get('display_name', 'None')}")
            log.info(f"[DEBUG] Received expires_at: {token_data.get('expires_at', 'None')}")
            
            # Cifrar refresh_token (único token que almacenamos)
            log.info(f"[DEBUG] Encrypting refresh_token...")
            encrypted_refresh = auth.encrypt_token(token_data['refresh_token'])
            log.info(f"[DEBUG] Refresh token encrypted successfully (length: {len(encrypted_refresh)})")
            
            # Determinar número de cuenta (usar el siguiente disponible)
            accounts = self.account_manager.list_accounts()
            account_numbers = [acc.get('account_number') for acc in accounts]
            next_number = 1
            for i in range(1, 6):
                if i not in account_numbers:
                    next_number = i
                    break
            
            if next_number > 5:
                await ctx.send("❌ Ya tienes 5 cuentas registradas. Elimina una antes de agregar otra.")
                await auth.close()
                return
            
            # Obtener display_name si es posible
            display_name = token_data.get('display_name', f'Cuenta {next_number}')
            
            # Agregar cuenta (solo refresh_token, account_id, display_name, token_expiry)
            success = self.account_manager.add_account(
                account_number=next_number,
                account_name=display_name,
                encrypted_refresh_token=encrypted_refresh,
                account_id=token_data.get('account_id', ''),
                display_name=display_name,
                token_expiry=token_data.get('expires_at', '')
            )
            
            await auth.close()
            
            if success:
                embed = nextcord.Embed(
                    title="✅ Autenticación Exitosa",
                    description=f"Cuenta **{display_name}** agregada correctamente",
                    color=nextcord.Color.green(),
                    timestamp=nextcord.utils.utcnow()
                )
                
                embed.add_field(
                    name="📊 Información",
                    value=f"• **Número de cuenta**: {next_number}\n"
                          f"• **Account ID**: `{token_data.get('account_id', 'N/A')[:20]}...`\n"
                          f"• **Display Name**: {display_name}\n"
                          f"• **Método**: Authorization Code Flow (OAuth Oficial)",
                    inline=False
                )
                
                embed.set_footer(text="Solo se almacena refresh_token encriptado")
                
                await ctx.send(embed=embed)
                log.info(f"Cuenta agregada por {user_id}, número: {next_number}")
            else:
                await ctx.send("❌ Error al guardar la cuenta. Verifica los logs.")
                
        except Exception as e:
            log.error(f"Error en fn_code: {e}")
            import traceback
            log.error(f"Traceback: {traceback.format_exc()}")
            await ctx.send(f"❌ Error procesando código: {str(e)}")
    
    @commands.command(name="fn_auth_device")
    async def fn_auth_device(self, ctx: commands.Context, device_code: str, user_code: str):
        """
        Completa la autenticación usando Device Code Flow
        
        Uso: !fn_auth_device <device_code> <user_code>
        Ejemplo: !fn_auth_device abc123def456 xyz789
        """
        if not check_owner_permission(ctx):
            await ctx.send(get_permission_error_message())
            return
        
        # Inicializar módulos si no están inicializados
        if self.account_manager is None:
            try:
                self.account_manager = FortniteAccountManager()
            except Exception as e:
                log.error(f"Error inicializando account_manager: {e}")
                await ctx.send("❌ Error inicializando módulo de cuentas.")
                return
        
        try:
            user_id = ctx.author.id
            await ctx.send("🔄 Autenticando con Epic Games usando Device Code...")
            
            # Autenticar con Device Code
            auth = EpicAuth()
            token_data = await auth.authenticate_with_device_code(device_code, user_code)
            
            if not token_data:
                await ctx.send("❌ Error al autenticar. Verifica que:\n"
                              "• Los códigos sean correctos\n"
                              "• Hayas autorizado el dispositivo en Epic Games\n"
                              "• Los códigos no hayan expirado")
                await auth.close()
                return
            
            # Cifrar refresh_token (único token que almacenamos)
            encrypted_refresh = auth.encrypt_token(token_data['refresh_token'])
            
            # Determinar número de cuenta (usar el siguiente disponible)
            accounts = self.account_manager.list_accounts()
            account_numbers = [acc.get('account_number') for acc in accounts]
            next_number = 1
            for i in range(1, 6):
                if i not in account_numbers:
                    next_number = i
                    break
            
            if next_number > 5:
                await ctx.send("❌ Ya tienes 5 cuentas registradas. Elimina una antes de agregar otra.")
                await auth.close()
                return
            
            # Obtener display_name si es posible
            display_name = token_data.get('display_name', f'Cuenta {next_number}')
            
            # Agregar cuenta (solo refresh_token, account_id, display_name, token_expiry)
            success = self.account_manager.add_account(
                account_number=next_number,
                account_name=display_name,
                encrypted_refresh_token=encrypted_refresh,
                account_id=token_data.get('account_id', ''),
                display_name=display_name,
                token_expiry=token_data.get('expires_at', '')
            )
            
            await auth.close()
            
            if success:
                embed = nextcord.Embed(
                    title="✅ Autenticación Exitosa",
                    description=f"Cuenta **{display_name}** agregada correctamente",
                    color=nextcord.Color.green(),
                    timestamp=nextcord.utils.utcnow()
                )
                
                embed.add_field(
                    name="📊 Información",
                    value=f"• **Número de cuenta**: {next_number}\n"
                          f"• **Account ID**: `{token_data.get('account_id', 'N/A')[:20]}...`\n"
                          f"• **Display Name**: {display_name}\n"
                          f"• **Método**: Device Code Flow (OAuth Oficial)",
                    inline=False
                )
                
                embed.set_footer(text="Solo se almacena refresh_token encriptado")
                
                await ctx.send(embed=embed)
                log.info(f"Cuenta agregada por {user_id}, número: {next_number}")
            else:
                await ctx.send("❌ Error al guardar la cuenta. Verifica los logs.")
                
        except Exception as e:
            log.error(f"Error en fn_auth_device: {e}")
            import traceback
            log.error(f"Traceback: {traceback.format_exc()}")
            await ctx.send(f"❌ Error procesando autenticación: {str(e)}")
    
    # fn_auth eliminado - Solo se usa DeviceAuth con PRIMARY_ACCOUNT
    
    @commands.command(name="fn_token_info")
    async def fn_token_info(self, ctx: commands.Context, account_number: int = None):
        """
        Muestra información sobre el estado y expiración de los tokens
        
        Uso: !fn_token_info [número]
        Ejemplo: !fn_token_info 1
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
            account = self.account_manager.get_account(account_number)
            
            if not account:
                await ctx.send(f"❌ No se encontró la cuenta número {account_number or 'activa'}.")
                return
            
            # Verificar expiración
            token_expiry = account.get('token_expiry', '')
            is_expired = False
            expires_in = "N/A"
            
            if token_expiry and token_expiry != 'N/A':
                try:
                    expiry_date = datetime.fromisoformat(token_expiry.replace('Z', '+00:00'))
                    now = datetime.utcnow()
                    if expiry_date.tzinfo:
                        now = now.replace(tzinfo=expiry_date.tzinfo)
                    else:
                        expiry_date = expiry_date.replace(tzinfo=None)
                    
                    if expiry_date < now:
                        is_expired = True
                        expires_in = "❌ Expirado"
                    else:
                        delta = expiry_date - now
                        days = delta.days
                        hours = delta.seconds // 3600
                        expires_in = f"{days} días, {hours} horas"
                except:
                    expires_in = "Error calculando"
            
            embed = nextcord.Embed(
                title="🔑 Información de Tokens",
                description=f"Cuenta: **{account.get('account_name', 'N/A')}**",
                color=nextcord.Color.green() if not is_expired else nextcord.Color.red(),
                timestamp=nextcord.utils.utcnow()
            )
            
            embed.add_field(
                name="📋 Detalles",
                value=f"• **Número**: {account.get('account_number', 'N/A')}\n"
                      f"• **Account ID**: `{account.get('account_id', 'N/A')[:20]}...`\n"
                      f"• **Display Name**: {account.get('display_name', 'N/A')}\n"
                      f"• **Estado**: {'✅ Activa' if account.get('is_active', False) else '⏸️ Inactiva'}",
                inline=False
            )
            
            embed.add_field(
                name="⏰ Expiración",
                value=f"• **Expira en**: {expires_in}\n"
                      f"• **Fecha de expiración**: {token_expiry or 'N/A'}\n"
                      f"• **Estado**: {'❌ Expirado' if is_expired else '✅ Válido'}",
                inline=False
            )
            
            embed.add_field(
                name="🔐 Seguridad",
                value=f"• **Método**: {account.get('auth_method', 'unknown').upper()}\n"
                      f"• **Tokens almacenados**: Solo refresh_token (encriptado)\n"
                      f"• **Access token**: Se genera dinámicamente",
                inline=False
            )
            
            if is_expired:
                embed.add_field(
                    name="⚠️ Acción Requerida",
                    value="El token ha expirado. El bot intentará renovarlo automáticamente con DeviceAuth.",
                    inline=False
                )
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            log.error(f"Error en fn_token_info: {e}")
            await ctx.send(f"❌ Error obteniendo información: {str(e)}")
    
    # ==================== COMANDOS DE CUENTAS ====================
    
    @commands.command(name="fn_add_account")
    async def fn_add_account(self, ctx, account_number: int, account_name: str):
        """Agregar PRIMARY_ACCOUNT usando DeviceAuth (máximo 5)
        
        Uso: !fn_add_account <número> <nombre>
        Ejemplo: !fn_add_account 1 "Mi Cuenta Principal"
        
        Nota: Usa automáticamente PRIMARY_ACCOUNT con DeviceAuth predefinido
        """
        if not check_owner_permission(ctx):
            await ctx.send(get_permission_error_message())
            return
        
        if not (1 <= account_number <= 5):
            await ctx.send("❌ El número de cuenta debe estar entre 1 y 5.")
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
            await ctx.send("🔄 Autenticando con DeviceAuth (PRIMARY_ACCOUNT)...")
            
            # Autenticar usando DeviceAuth con PRIMARY_ACCOUNT
            auth = EpicAuth()
            token_data = await auth.authenticate_primary_account()
            await auth.close()
            
            if not token_data:
                await ctx.send("❌ Error al autenticar con DeviceAuth. Revisa los logs del servidor.")
                return
            
            # Cifrar refresh_token (único token que almacenamos)
            encrypted_refresh = auth.encrypt_token(token_data['refresh_token'])
            
            # Agregar cuenta
            success = self.account_manager.add_account(
                account_number=account_number,
                account_name=account_name,
                encrypted_refresh_token=encrypted_refresh,
                account_id=token_data.get('account_id', ''),
                display_name=token_data.get('display_name', account_name),
                token_expiry=token_data.get('expires_at', '')
            )
            
            if success:
                embed = nextcord.Embed(
                    title="✅ Cuenta Agregada",
                    description=f"Cuenta **{account_name}** agregada correctamente usando DeviceAuth",
                    color=nextcord.Color.green(),
                    timestamp=nextcord.utils.utcnow()
                )
                
                embed.add_field(
                    name="📊 Información",
                    value=f"• **Número de cuenta**: {account_number}\n"
                          f"• **Account ID**: `{token_data.get('account_id', 'N/A')[:20]}...`\n"
                          f"• **Display Name**: {token_data.get('display_name', account_name)}\n"
                          f"• **Método**: DeviceAuth (PRIMARY_ACCOUNT)",
                    inline=False
                )
                
                await ctx.send(embed=embed)
                log.info(f"Cuenta {account_number} agregada por {ctx.author.id} usando DeviceAuth")
            else:
                await ctx.send("❌ Error al agregar cuenta. Verifica que el número no esté en uso y que no hayas alcanzado el límite de 5 cuentas.")
                
        except Exception as e:
            log.error(f"Error en fn_add_account: {e}")
            import traceback
            log.error(f"Traceback: {traceback.format_exc()}")
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
        
        # Inicializar account_manager si no está inicializado
        if self.account_manager is None:
            try:
                self.account_manager = FortniteAccountManager()
            except Exception as e:
                log.error(f"Error inicializando account_manager: {e}")
                await ctx.send("❌ Error inicializando módulo de cuentas.")
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
            from .accounts import MAX_ACCOUNTS
            embed = nextcord.Embed(
                title="🎮 Cuentas de Fortnite",
                description=f"Total: {len(accounts)}/{MAX_ACCOUNTS}",
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
    
    @commands.command(name="fn_delete_account")
    async def fn_delete_account(self, ctx, account_number: int):
        """Eliminar una cuenta de Fortnite guardada
        
        Uso: !fn_delete_account <número>
        Ejemplo: !fn_delete_account 1
        Nota: El número debe ser entre 1 y 5. Esta acción no se puede deshacer.
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
            # Validar número de cuenta
            from .accounts import MAX_ACCOUNTS
            if account_number < 1 or account_number > MAX_ACCOUNTS:
                await ctx.send(f"❌ El número de cuenta debe estar entre 1 y {MAX_ACCOUNTS}.")
                return
            
            # Verificar que la cuenta existe antes de eliminar
            account = self.account_manager.get_account(account_number)
            if not account:
                await ctx.send(f"❌ No se encontró la cuenta #{account_number}.")
                return
            
            account_name = account.get('account_name', 'Sin nombre')
            is_active = account.get('is_active', False)
            
            # Eliminar cuenta
            success = self.account_manager.remove_account(account_number)
            
            if success:
                embed = nextcord.Embed(
                    title="✅ Cuenta eliminada",
                    description=f"Cuenta #{account_number} eliminada correctamente",
                    color=0xFF6B6B,
                    timestamp=nextcord.utils.utcnow()
                )
                embed.add_field(
                    name="Información eliminada",
                    value=f"• **Nombre**: {account_name}\n"
                          f"• **Account ID**: `{account.get('account_id', 'N/A')[:20]}...`\n"
                          f"• **Estado**: {'Activa' if is_active else 'Inactiva'}",
                    inline=False
                )
                embed.set_footer(text="Los tokens y datos de esta cuenta han sido eliminados permanentemente")
                
                await ctx.send(embed=embed)
                log.info(f"Cuenta {account_number} ({account_name}) eliminada por {ctx.author.id}")
            else:
                await ctx.send(f"❌ Error al eliminar la cuenta #{account_number}.")
                
        except ValueError:
            await ctx.send("❌ El número de cuenta debe ser un número válido (1-5).")
        except Exception as e:
            log.error(f"Error en fn_delete_account: {e}")
            import traceback
            log.error(f"Traceback: {traceback.format_exc()}")
            await ctx.send(f"❌ Error inesperado: {str(e)}")
    
    @commands.command(name="fn_rename_account")
    async def fn_rename_account(self, ctx, account_number: int, *, new_name: str):
        """Cambiar el nombre de una cuenta de Fortnite
        
        Uso: !fn_rename_account <número> <nuevo_nombre>
        Ejemplo: !fn_rename_account 1 Mi Cuenta Principal
        Nota: El número debe ser entre 1 y 5
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
            # Validar número de cuenta
            from .accounts import MAX_ACCOUNTS
            if account_number < 1 or account_number > MAX_ACCOUNTS:
                await ctx.send(f"❌ El número de cuenta debe estar entre 1 y {MAX_ACCOUNTS}.")
                return
            
            # Validar nombre
            if not new_name or len(new_name.strip()) == 0:
                await ctx.send("❌ El nombre no puede estar vacío.")
                return
            
            if len(new_name) > 50:
                await ctx.send("❌ El nombre es demasiado largo (máximo 50 caracteres).")
                return
            
            # Verificar que la cuenta existe
            account = self.account_manager.get_account(account_number)
            if not account:
                await ctx.send(f"❌ No se encontró la cuenta #{account_number}.")
                return
            
            old_name = account.get('account_name', 'Sin nombre')
            
            # Actualizar nombre
            success = self.account_manager.update_account_name(account_number, new_name.strip())
            
            if success:
                embed = nextcord.Embed(
                    title="✅ Nombre de cuenta actualizado",
                    description=f"Cuenta #{account_number}",
                    color=0x00E5A8
                )
                embed.add_field(
                    name="Nombre anterior",
                    value=old_name,
                    inline=False
                )
                embed.add_field(
                    name="Nuevo nombre",
                    value=new_name.strip(),
                    inline=False
                )
                await ctx.send(embed=embed)
                log.info(f"Nombre de cuenta {account_number} cambiado por {ctx.author.id}: '{old_name}' -> '{new_name}'")
            else:
                await ctx.send(f"❌ Error al actualizar el nombre de la cuenta #{account_number}.")
                
        except ValueError:
            await ctx.send("❌ El número de cuenta debe ser un número válido (1-5).")
        except Exception as e:
            log.error(f"Error en fn_rename_account: {e}")
            import traceback
            log.error(f"Traceback: {traceback.format_exc()}")
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
        
        # Inicializar friends_manager si no está inicializado
        if self.friends_manager is None:
            try:
                self.friends_manager = FortniteFriends()
            except Exception as e:
                log.error(f"Error inicializando friends_manager: {e}")
                await ctx.send("❌ Error inicializando módulo de amigos.")
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
        
        # Inicializar friends_manager si no está inicializado
        if self.friends_manager is None:
            try:
                self.friends_manager = FortniteFriends()
            except Exception as e:
                log.error(f"Error inicializando friends_manager: {e}")
                await ctx.send("❌ Error inicializando módulo de amigos.")
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
        
        ⚠️ Nota: La API de regalos de Epic Games puede no estar disponible públicamente.
        """
        if not check_owner_permission(ctx):
            await ctx.send(get_permission_error_message())
            return
        
        # Inicializar módulos si no están inicializados
        if self.gifting_manager is None:
            try:
                self.gifting_manager = FortniteGifting()
            except Exception as e:
                log.error(f"Error inicializando gifting_manager: {e}")
                await ctx.send("❌ Error inicializando módulo de regalos.")
                return
        
        if self.account_manager is None:
            try:
                self.account_manager = FortniteAccountManager()
            except Exception as e:
                log.error(f"Error inicializando account_manager: {e}")
                await ctx.send("❌ Error inicializando módulo de cuentas.")
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
        
        # Inicializar gifting_manager si no está inicializado
        if self.gifting_manager is None:
            try:
                self.gifting_manager = FortniteGifting()
            except Exception as e:
                log.error(f"Error inicializando gifting_manager: {e}")
                await ctx.send("❌ Error inicializando módulo de regalos.")
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
        
        # Inicializar gifting_manager si no está inicializado
        if self.gifting_manager is None:
            try:
                self.gifting_manager = FortniteGifting()
            except Exception as e:
                log.error(f"Error inicializando gifting_manager: {e}")
                await ctx.send("❌ Error inicializando módulo de regalos.")
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
        
        # Inicializar gifting_manager si no está inicializado
        if self.gifting_manager is None:
            try:
                self.gifting_manager = FortniteGifting()
            except Exception as e:
                log.error(f"Error inicializando gifting_manager: {e}")
                await ctx.send("❌ Error inicializando módulo de regalos.")
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
        Nota: Usa API pública (fortnite-api.com). La API oficial de Epic puede no estar disponible.
        """
        if not check_owner_permission(ctx):
            await ctx.send(get_permission_error_message())
            return
        
        # Inicializar store_manager si no está inicializado
        if self.store_manager is None:
            try:
                self.store_manager = FortniteStore()
            except Exception as e:
                log.error(f"Error inicializando store_manager: {e}")
                await ctx.send("❌ Error inicializando módulo de tienda.")
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
                
                # Crear vista de paginación
                pagination_view = StorePaginationView(items, items_per_page=10, user_id=user_id)
                embed = pagination_view.create_embed()
                
                # Agregar fuente de datos
                source = result.get('source', 'unknown')
                source_text = "📡 API Pública" if source == 'fortnite-api.com' else "📡 API Oficial"
                embed.description += f"\n{source_text}"
                
                await ctx.send(embed=embed, view=pagination_view)
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
        
        # Inicializar store_manager si no está inicializado
        if self.store_manager is None:
            try:
                self.store_manager = FortniteStore()
            except Exception as e:
                log.error(f"Error inicializando store_manager: {e}")
                await ctx.send("❌ Error inicializando módulo de tienda.")
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
    
    # ==================== COMANDOS DE DEVICEAUTH PRIMARY ACCOUNT ====================
    
    @commands.command(name="fn_test_login")
    async def fn_test_login(self, ctx: commands.Context):
        """Valida login con DeviceAuth de PRIMARY_ACCOUNT
        
        Uso: !fn_test_login
        """
        if not check_owner_permission(ctx):
            await ctx.send(get_permission_error_message())
            return
        
        try:
            await ctx.send("🔄 Probando autenticación con DeviceAuth (PRIMARY_ACCOUNT)...")
            
            from .auth import EpicAuth
            auth = EpicAuth()
            token_data = await auth.authenticate_primary_account()
            await auth.close()
            
            if token_data:
                embed = nextcord.Embed(
                    title="✅ Login Exitoso (DeviceAuth)",
                    description="PRIMARY_ACCOUNT autenticado correctamente",
                    color=nextcord.Color.green(),
                    timestamp=nextcord.utils.utcnow()
                )
                
                embed.add_field(
                    name="📊 Información",
                    value=f"• **Account ID**: `{token_data.get('account_id', 'N/A')[:20]}...`\n"
                          f"• **Display Name**: {token_data.get('display_name', 'N/A')}\n"
                          f"• **Device ID**: `{token_data.get('device_id', 'N/A')[:20]}...`\n"
                          f"• **Método**: DeviceAuth (PRIMARY_ACCOUNT)\n"
                          f"• **Expira en**: {token_data.get('expires_at', 'N/A')}",
                    inline=False
                )
                
                await ctx.send(embed=embed)
                log.info(f"Login test exitoso para {ctx.author.id}")
            else:
                await ctx.send("❌ Error al autenticar con DeviceAuth. Revisa los logs del servidor.")
                
        except Exception as e:
            log.error(f"Error en fn_test_login: {e}")
            import traceback
            log.error(f"Traceback: {traceback.format_exc()}")
            await ctx.send(f"❌ Error: {str(e)}")
    
    @commands.command(name="fn_me")
    async def fn_me(self, ctx: commands.Context):
        """Muestra display_name y account_id de PRIMARY_ACCOUNT
        
        Uso: !fn_me
        """
        if not check_owner_permission(ctx):
            await ctx.send(get_permission_error_message())
            return
        
        try:
            await ctx.send("🔄 Obteniendo información de PRIMARY_ACCOUNT...")
            
            from .auth import EpicAuth
            auth = EpicAuth()
            token_data = await auth.authenticate_primary_account()
            await auth.close()
            
            if token_data:
                embed = nextcord.Embed(
                    title="👤 Información de PRIMARY_ACCOUNT",
                    description="Datos de la cuenta principal",
                    color=nextcord.Color.blue(),
                    timestamp=nextcord.utils.utcnow()
                )
                
                embed.add_field(
                    name="📝 Display Name",
                    value=token_data.get('display_name', 'N/A'),
                    inline=True
                )
                
                embed.add_field(
                    name="🆔 Account ID",
                    value=f"`{token_data.get('account_id', 'N/A')}`",
                    inline=True
                )
                
                embed.add_field(
                    name="🔑 Device ID",
                    value=f"`{token_data.get('device_id', 'N/A')[:20]}...`",
                    inline=False
                )
                
                await ctx.send(embed=embed)
            else:
                await ctx.send("❌ Error al obtener información. Revisa los logs del servidor.")
                
        except Exception as e:
            log.error(f"Error en fn_me: {e}")
            import traceback
            log.error(f"Traceback: {traceback.format_exc()}")
            await ctx.send(f"❌ Error: {str(e)}")
    
    @commands.command(name="fn_vbucks")
    async def fn_vbucks(self, ctx: commands.Context):
        """Muestra balance de V-Bucks de PRIMARY_ACCOUNT
        
        Uso: !fn_vbucks
        """
        if not check_owner_permission(ctx):
            await ctx.send(get_permission_error_message())
            return
        
        try:
            await ctx.send("🔄 Obteniendo balance de V-Bucks...")
            
            from .auth import EpicAuth
            import aiohttp
            
            auth = EpicAuth()
            token_data = await auth.authenticate_primary_account()
            
            if not token_data:
                await ctx.send("❌ Error al autenticar. Revisa los logs del servidor.")
                await auth.close()
                return
            
            access_token = token_data.get('access_token')
            account_id = token_data.get('account_id')
            
            # Obtener balance de V-Bucks desde la API de Epic Games
            # Endpoint: https://fortnite-public-service-prod11.ol.epicgames.com/fortnite/api/game/v2/profile/{accountId}/client/QueryProfile
            async with aiohttp.ClientSession() as session:
                headers = {
                    'Authorization': f'bearer {access_token}',
                    'Content-Type': 'application/json'
                }
                
                # Intentar obtener balance desde múltiples endpoints
                balance = None
                
                # Método 1: QueryProfile
                try:
                    url = f"https://fortnite-public-service-prod11.ol.epicgames.com/fortnite/api/game/v2/profile/{account_id}/client/QueryProfile"
                    data = {
                        "profileId": "common_core",
                        "rvn": -1
                    }
                    
                    async with session.post(url, headers=headers, json=data) as response:
                        if response.status == 200:
                            profile_data = await response.json()
                            # Buscar balance en la respuesta
                            if 'profile' in profile_data and 'stats' in profile_data['profile']:
                                stats = profile_data['profile']['stats']
                                balance = stats.get('attributes', {}).get('mtx_currency', {}).get('quantity', 0)
                except Exception as e:
                    log.warning(f"Error obteniendo balance desde QueryProfile: {e}")
                
                # Si no se obtuvo, intentar método alternativo
                if balance is None:
                    try:
                        # Método 2: Obtener desde account balance
                        balance_url = f"https://account-public-service-prod03.ol.epicgames.com/account/api/public/account/{account_id}/balance"
                        async with session.get(balance_url, headers=headers) as balance_response:
                            if balance_response.status == 200:
                                balance_data = await balance_response.json()
                                # Buscar V-Bucks en la respuesta
                                for currency in balance_data.get('currencies', []):
                                    if currency.get('currencyCode') == 'MtxCurrency':
                                        balance = currency.get('balance', 0)
                                        break
                    except Exception as e:
                        log.warning(f"Error obteniendo balance desde account balance: {e}")
            
            await auth.close()
            
            if balance is not None:
                embed = nextcord.Embed(
                    title="💰 Balance de V-Bucks",
                    description=f"Balance actual de PRIMARY_ACCOUNT",
                    color=nextcord.Color.gold(),
                    timestamp=nextcord.utils.utcnow()
                )
                
                embed.add_field(
                    name="💎 V-Bucks",
                    value=f"**{balance:,}**",
                    inline=False
                )
                
                embed.add_field(
                    name="👤 Account",
                    value=f"`{account_id[:20]}...`",
                    inline=True
                )
                
                embed.add_field(
                    name="📝 Display Name",
                    value=token_data.get('display_name', 'N/A'),
                    inline=True
                )
                
                await ctx.send(embed=embed)
            else:
                await ctx.send("❌ No se pudo obtener el balance de V-Bucks. El endpoint puede no estar disponible.")
                
        except Exception as e:
            log.error(f"Error en fn_vbucks: {e}")
            import traceback
            log.error(f"Traceback: {traceback.format_exc()}")
            await ctx.send(f"❌ Error: {str(e)}")
    
    def cog_unload(self):
        """Limpia recursos al descargar el cog"""
        log.info("Cog de Fortnite descargado, cerrando conexiones...")
        # Cerrar conexiones asíncronas si es necesario
        # Nota: Esto se ejecuta de forma síncrona, las conexiones se cerrarán en el próximo ciclo


def setup(bot: commands.Bot):
    """Setup del cog"""
    bot.add_cog(FortniteCommands(bot))
    log.info("Cog de Fortnite cargado")



