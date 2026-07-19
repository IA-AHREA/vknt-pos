import discord
from discord import app_commands
from discord.ext import commands
from prisma.errors import ForeignKeyViolationError

from ..checks import es_ceo
from ..db import db


async def sistema_autocomplete(
    interaction: discord.Interaction, current: str
) -> list[app_commands.Choice[str]]:
    sistemas = await db.sistema.find_many(order={"nombre": "asc"})
    current_lower = current.lower()
    return [
        app_commands.Choice(name=s.nombre, value=s.nombre)
        for s in sistemas
        if current_lower in s.nombre.lower()
    ][:25]


class SistemasCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="sistema-agregar", description="Agrega un sistema EVE a la lista disponible")
    @es_ceo()
    async def sistema_agregar(self, interaction: discord.Interaction, nombre: str):
        nombre = nombre.strip().upper()
        existente = await db.sistema.find_unique(where={"nombre": nombre})
        if existente:
            return await interaction.response.send_message(
                f"❌ El sistema **{nombre}** ya existe.", ephemeral=True
            )
        await db.sistema.create(data={"nombre": nombre})
        await interaction.response.send_message(f"✅ Sistema **{nombre}** agregado.")

    @app_commands.command(name="sistema-listar", description="Lista los sistemas EVE disponibles")
    async def sistema_listar(self, interaction: discord.Interaction):
        sistemas = await db.sistema.find_many(order={"nombre": "asc"})
        if not sistemas:
            return await interaction.response.send_message(
                "No hay sistemas registrados todavía. Usa /sistema-agregar.", ephemeral=True
            )
        lista = "\n".join(f"- {s.nombre}" for s in sistemas)
        await interaction.response.send_message(f"**Sistemas disponibles:**\n{lista}")

    @app_commands.command(name="sistema-borrar", description="Elimina un sistema de la lista disponible")
    @app_commands.autocomplete(nombre=sistema_autocomplete)
    @es_ceo()
    async def sistema_borrar(self, interaction: discord.Interaction, nombre: str):
        sistema = await db.sistema.find_unique(where={"nombre": nombre})
        if not sistema:
            return await interaction.response.send_message(
                f"❌ No existe el sistema **{nombre}**.", ephemeral=True
            )
        try:
            await db.sistema.delete(where={"id": sistema.id})
        except ForeignKeyViolationError:
            return await interaction.response.send_message(
                f"❌ No se puede borrar **{nombre}**: todavía hay POS asignadas a ese sistema.",
                ephemeral=True,
            )
        await interaction.response.send_message(f"🗑️ Sistema **{nombre}** eliminado.")


async def setup(bot: commands.Bot):
    await bot.add_cog(SistemasCog(bot))
