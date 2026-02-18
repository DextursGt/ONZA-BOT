"""Message template engine with placeholder support."""
import logging

logger = logging.getLogger(__name__)

class Template:
    """Render message templates with placeholders."""

    PLACEHOLDERS = {
        '%member_mention%': lambda ctx: ctx['member'].mention,
        '%member_name%': lambda ctx: ctx['member'].name,
        '%member_tag%': lambda ctx: str(ctx['member']),
        '%member_id%': lambda ctx: ctx['member'].id,
        '%guild_name%': lambda ctx: ctx['guild'].name,
        '%member_count%': lambda ctx: ctx['guild'].member_count,
        '%inviter%': lambda ctx: ctx.get('inviter', {}).get('name', 'Unknown'),
        '%inviter_mention%': lambda ctx: ctx.get('inviter', {}).get('mention', '@Unknown'),
        '%invite_count%': lambda ctx: ctx.get('invite_count', 0),
        '%server_rules%': lambda ctx: ctx.get('rules', 'Ver #reglas'),
        '%verification_emoji%': lambda ctx: '✅',
        '%member_avatar%': lambda ctx: ctx['member'].display_avatar.url if hasattr(ctx['member'], 'display_avatar') else '[N/A]'
    }

    def render(self, template: str, context: dict) -> str:
        """Render template with context data.

        Args:
            template: Template string with placeholders
            context: Dictionary with data (member, guild, etc.)

        Returns:
            Rendered message string
        """
        if not template:
            return ""

        result = template

        for placeholder, func in self.PLACEHOLDERS.items():
            try:
                value = func(context)
                result = result.replace(placeholder, str(value))
            except KeyError:
                result = result.replace(placeholder, "[N/A]")
                logger.debug(f"Missing context for {placeholder}")
            except AttributeError as e:
                result = result.replace(placeholder, "[Error]")
                logger.warning(f"Attribute error for {placeholder}: {e}")
            except Exception as e:
                result = result.replace(placeholder, "[Error]")
                logger.error(f"Unexpected error for {placeholder}: {e}")

        return result
