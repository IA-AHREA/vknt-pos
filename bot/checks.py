import discord
from discord import app_commands

from .config import CEO_ROLE_ID


def _es_ceo(interaction: discord.Interaction) -> bool:
    if interaction.guild is None or not isinstance(interaction.user, discord.Member):
        return False
    return any(role.id == CEO_ROLE_ID for role in interaction.user.roles)


def es_ceo():
    """Decorator para slash commands: exige el rol de CEO configurado."""
    return app_commands.check(_es_ceo)


def es_ceo_interaction(interaction: discord.Interaction) -> bool:
    """Misma validación pero para usarla a mano (ej. context menus)."""
    return _es_ceo(interaction)
