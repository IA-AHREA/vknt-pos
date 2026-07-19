from datetime import datetime

import discord
from discord import app_commands, ui
from discord.ext import commands

from ..checks import es_ceo
from ..db import db
from ..ui import PaginadorView, SelectorPosView
from ..utils import a_total_meses, construir_paginas, estado_texto
from .sistemas import sistema_autocomplete

RANGO_ID_MIN = 100
RANGO_ID_MAX = 999


async def _siguiente_id_disponible() -> int | None:
    existentes = await db.outpost.find_many(order={"id_num": "asc"})
    usados = {o.id_num for o in existentes}
    for candidato in range(RANGO_ID_MIN, RANGO_ID_MAX + 1):
        if candidato not in usados:
            return candidato
    return None


class EditarPosModal(ui.Modal):
    nombre_input = ui.TextInput(label="Nombre de la POS", max_length=100)
    mes_input = ui.TextInput(label="Mes pagado hasta (0-12)", max_length=2)
    anio_input = ui.TextInput(label="Año", max_length=4)

    def __init__(self, outpost):
        super().__init__(title=f"Editar POS #{outpost.id_num}")
        self.id_num = outpost.id_num
        self.nombre_input.default = outpost.nombre_pos
        self.mes_input.default = str(outpost.pagado_hasta_mes)
        self.anio_input.default = str(outpost.anio_vencimiento)

    async def on_submit(self, interaction: discord.Interaction):
        nombre = self.nombre_input.value.strip()
        if not nombre:
            return await interaction.response.send_message(
                "❌ El nombre no puede estar vacío.", ephemeral=True
            )
        try:
            mes = int(self.mes_input.value)
            anio = int(self.anio_input.value)
        except ValueError:
            return await interaction.response.send_message(
                "❌ Mes y año deben ser números.", ephemeral=True
            )
        if not (0 <= mes <= 12):
            return await interaction.response.send_message(
                "❌ El mes debe estar entre 0 y 12.", ephemeral=True
            )

        outpost = await db.outpost.find_unique(where={"id_num": self.id_num})
        if not outpost:
            return await interaction.response.send_message(
                f"❌ La POS #{self.id_num} ya no existe.", ephemeral=True
            )

        delta = a_total_meses(anio, mes) - a_total_meses(
            outpost.anio_vencimiento, outpost.pagado_hasta_mes
        )

        async with db.tx() as transaction:
            await transaction.outpost.update(
                where={"id_num": self.id_num},
                data={"nombre_pos": nombre, "pagado_hasta_mes": mes, "anio_vencimiento": anio},
            )
            if delta != 0:
                await transaction.pago.create(
                    data={
                        "outpost_id": self.id_num,
                        "tipo": "CORRECCION",
                        "meses": delta,
                        "registrado_por_id": str(interaction.user.id),
                        "mes_resultante": mes,
                        "anio_resultante": anio,
                    }
                )

        await interaction.response.send_message(
            f"✏️ POS #{self.id_num} actualizada: **{nombre}**, pagado hasta **{estado_texto(mes, anio)}**."
        )


async def _abrir_editor(interaction: discord.Interaction, outpost):
    await interaction.response.send_modal(EditarPosModal(outpost))


class OutpostsCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="registrar-pos", description="Registra una POS (el ID se asigna solo)")
    @app_commands.autocomplete(sistema=sistema_autocomplete)
    @es_ceo()
    async def registrar_pos(
        self,
        interaction: discord.Interaction,
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

        id_id = await _siguiente_id_disponible()
        if id_id is None:
            return await interaction.response.send_message(
                f"❌ No quedan IDs disponibles en el rango {RANGO_ID_MIN}-{RANGO_ID_MAX}.",
                ephemeral=True,
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

    @app_commands.command(name="buscar", description="Busca las POS de un usuario (solo vos lo ves)")
    @es_ceo()
    async def buscar(self, interaction: discord.Interaction, usuario: discord.Member):
        outposts = await db.outpost.find_many(
            where={"discord_id": str(usuario.id)}, include={"sistema": True}, order={"id_num": "asc"}
        )
        if not outposts:
            return await interaction.response.send_message(
                f"{usuario.mention} no tiene POS registradas.", ephemeral=True
            )

        header = f"{'ID':<4} | {'Outpost':<15} | {'Estado':<20} | {'Sistema'}\n"
        separator = "-" * 4 + "+" + "-" * 17 + "+" + "-" * 22 + "+" + "-" * 10 + "\n"
        cuerpo = "".join(
            f"#{o.id_num:<3} | {o.nombre_pos[:15]:<15} | "
            f"{estado_texto(o.pagado_hasta_mes, o.anio_vencimiento):<20} | {o.sistema.nombre}\n"
            for o in outposts
        )
        tabla = f"**POS de {usuario.mention}**\n```\n{header}{separator}{cuerpo}```"

        view = SelectorPosView(outposts, autor_id=interaction.user.id, on_select=_abrir_editor)
        await interaction.response.send_message(
            f"{tabla}\nElegí una POS del menú para editarla:", view=view, ephemeral=True
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(OutpostsCog(bot))
