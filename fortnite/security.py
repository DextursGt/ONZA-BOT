"""
Módulo de seguridad para comandos Fortnite
Verifica que solo el owner específico pueda ejecutar comandos
"""

# ID del owner autorizado (único usuario que puede usar comandos Fortnite)
OWNER_DISCORD_ID = 857134594028601364


def is_authorized_owner(user_id: int) -> bool:
    """
    Verifica si el usuario es el owner autorizado
    
    Args:
        user_id: ID de Discord del usuario
        
    Returns:
        True si el usuario es el owner autorizado, False en caso contrario
    """
    return user_id == OWNER_DISCORD_ID


def check_owner_permission(ctx_or_interaction):
    """
    Verifica permisos del owner en un contexto o interacción
    
    Args:
        ctx_or_interaction: Contexto de comando o interacción de Discord
        
    Returns:
        True si tiene permisos, False en caso contrario
    """
    user_id = None
    
    # Obtener ID según el tipo de objeto
    if hasattr(ctx_or_interaction, 'author'):
        # Es un contexto de comando tradicional
        user_id = ctx_or_interaction.author.id
    elif hasattr(ctx_or_interaction, 'user'):
        # Es una interacción de slash command
        user_id = ctx_or_interaction.user.id
    
    if user_id is None:
        return False
    
    return is_authorized_owner(user_id)


def get_permission_error_message() -> str:
    """
    Retorna el mensaje de error estándar para permisos
    
    Returns:
        Mensaje de error formateado
    """
    return "❌ No tienes permisos para ejecutar este comando. Este comando está reservado exclusivamente para el owner del bot."

