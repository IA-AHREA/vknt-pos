from datetime import datetime

import discord
from discord import app_commands
from discord.ext import commands

from ..checks import es_ceo
from ..db import db
from ..ui import PaginadorView
from ..utils import construir_paginas, estado_texto
from .sistemas import sistema_autocomplete


class OutpostsCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="registrar-pos", description="Registra un Outpost con ID único (100-999)")
    @app_commands.autocomplete(sistema=sistema_autocomplete)
    @es_ceo()
    async def registrar_pos(
        self,
        interaction: discord.Interaction,
        id_id: app_commands.Range[int, 100, 999],
        dueño: discord.Member,
        nombre_pos: str,
        sistema: str,
    ):
        sistema_row = await db.sistema.find_unique(where={"nombre": sistema})
        if not sistema_row:
            return await interaction.response.send_message(
                f"❌ El sistema **{sistema}** no existe. Agrégalo primero con /sistema-agregar.",
                ephemeral=True,
            )

        existente = await db.outpost.find_unique(where={"id_num": id_id})
        if existente:
            return await interaction.response.send_message(
                f"❌ El ID {id_id} ya existe.", ephemeral=True
            )

        await db.outpost.create(
            data={
                "id_num": id_id,
                "discord_id": str(dueño.id),
                "nombre_pos": nombre_pos,
                "sistema_id": sistema_row.id,
                "pagado_hasta_mes": 0,
                "anio_vencimiento": datetime.now().year,
            }
        )
        await interaction.response.send_message(
            f"✅ POS #{id_id} registrada para {dueño.mention} en {sistema}."
        )

    @app_commands.command(name="borrar-pos", description="Borra una POS")
    @es_ceo()
    async def borrar_pos(self, interaction: discord.Interaction, id_id: int):
        eliminado = await db.outpost.delete(where={"id_num": id_id})
        if not eliminado:
            return await interaction.response.send_message(
                f"❌ No se encontró la POS #{id_id}.", ephemeral=True
            )
        await interaction.response.send_message(f"🗑️ POS #{id_id} eliminada.")

    @app_commands.command(name="reporte", description="Ver lista de pagos")
    @es_ceo()
    async def reporte(self, interaction: discord.Interaction):
        filas = await db.outpost.find_many(include={"sistema": True}, order={"id_num": "asc"})
        if not filas:
            return await interaction.response.send_message("No hay datos.")

        header = f"{'ID':<4} | {'Dueño':<22} | {'Outpost':<15} | {'Estado':<20} | {'Sistema'}\n"
        separator = "-" * 4 + "+" + "-" * 24 + "+" + "-" * 17 + "+" + "-" * 22 + "+" + "-" * 10 + "\n"

        def fmt_fila(o) -> str:
            estado = estado_texto(o.pagado_hasta_mes, o.anio_vencimiento)
            dueno = f"<@{o.discord_id}>"
            return f"#{o.id_num:<3} | {dueno:<22} | {o.nombre_pos[:15]:<15} | {estado:<20} | {o.sistema.nombre}\n"

        paginas = construir_paginas(filas, fmt_fila, header, separator)
        view = PaginadorView(paginas, autor_id=interaction.user.id)
        await interaction.response.send_message(view.render(), view=view)
        view.message = await interaction.original_response()


async def setup(bot: commands.Bot):
    await bot.add_cog(OutpostsCog(bot))
