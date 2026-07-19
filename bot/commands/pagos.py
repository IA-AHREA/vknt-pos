from datetime import datetime

import discord
from discord import app_commands, ui
from discord.ext import commands

from ..checks import es_ceo, es_ceo_interaction
from ..db import db
from ..ui import PaginadorView
from ..utils import construir_paginas, estado_texto, sumar_meses


class PagoModal(ui.Modal, title="Registrar Meses de Pago"):
    meses_input = ui.TextInput(label="¿Cuántos meses paga?", placeholder="Ej: 1 o 12", default="1")
    monto_input = ui.TextInput(
        label="Monto pagado (ISK, opcional)",
        placeholder="Ej: 500000000",
        required=False,
    )

    def __init__(self, id_num: int, nombre: str):
        super().__init__()
        self.id_num = id_num
        self.nombre = nombre

    async def on_submit(self, interaction: discord.Interaction):
        try:
            cant_meses = int(self.meses_input.value)
        except ValueError:
            return await interaction.response.send_message(
                "❌ La cantidad de meses debe ser un número entero.", ephemeral=True
            )
        if cant_meses <= 0:
            return await interaction.response.send_message(
                "❌ La cantidad de meses debe ser mayor a 0.", ephemeral=True
            )

        monto = None
        if self.monto_input.value:
            try:
                monto = float(self.monto_input.value.replace(",", ""))
            except ValueError:
                return await interaction.response.send_message(
                    "❌ El monto debe ser un número (o dejarlo vacío).", ephemeral=True
                )

        outpost = await db.outpost.find_unique(where={"id_num": self.id_num})
        if not outpost:
            return await interaction.response.send_message(
                f"❌ No se encontró la POS #{self.id_num}.", ephemeral=True
            )

        nuevo_anio, nuevo_mes = sumar_meses(
            outpost.anio_vencimiento, outpost.pagado_hasta_mes, cant_meses
        )

        async with db.tx() as transaction:
            await transaction.outpost.update(
                where={"id_num": self.id_num},
                data={"pagado_hasta_mes": nuevo_mes, "anio_vencimiento": nuevo_anio},
            )
            await transaction.pago.create(
                data={
                    "outpost_id": self.id_num,
                    "tipo": "PAGO",
                    "meses": cant_meses,
                    "monto": monto,
                    "registrado_por_id": str(interaction.user.id),
                    "mes_resultante": nuevo_mes,
                    "anio_resultante": nuevo_anio,
                }
            )

        detalle_monto = f" ({monto:,.2f} ISK)" if monto is not None else ""
        await interaction.response.send_message(
            f"✅ Pago registrado para #{self.id_num}{detalle_monto}. "
            f"Pagado hasta: **{estado_texto(nuevo_mes, nuevo_anio)}**"
        )


@app_commands.context_menu(name="Pagar Outpost")
async def registrar_pago_context(interaction: discord.Interaction, message: discord.Message):
    if not es_ceo_interaction(interaction):
        return await interaction.response.send_message("❌ No autorizado", ephemeral=True)

    outpost = await db.outpost.find_first(where={"discord_id": str(message.author.id)})
    if not outpost:
        return await interaction.response.send_message("❌ Usuario no registrado.", ephemeral=True)
    await interaction.response.send_modal(PagoModal(outpost.id_num, outpost.nombre_pos))


class PagosCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="corregir-pago", description="Resta meses por error")
    @es_ceo()
    async def corregir_pago(self, interaction: discord.Interaction, id_id: int, meses_a_quitar: int):
        if meses_a_quitar <= 0:
            return await interaction.response.send_message(
                "❌ La cantidad a quitar debe ser mayor a 0.", ephemeral=True
            )

        outpost = await db.outpost.find_unique(where={"id_num": id_id})
        if not outpost:
            return await interaction.response.send_message(
                f"❌ No se encontró la POS #{id_id}.", ephemeral=True
            )

        nuevo_anio, nuevo_mes = sumar_meses(
            outpost.anio_vencimiento, outpost.pagado_hasta_mes, -meses_a_quitar
        )

        if nuevo_anio < datetime.now().year:
            return await interaction.response.send_message(
                "❌ Error: La POS quedaría con fecha anterior al año actual.", ephemeral=True
            )

        async with db.tx() as transaction:
            await transaction.outpost.update(
                where={"id_num": id_id},
                data={"pagado_hasta_mes": nuevo_mes, "anio_vencimiento": nuevo_anio},
            )
            await transaction.pago.create(
                data={
                    "outpost_id": id_id,
                    "tipo": "CORRECCION",
                    "meses": -meses_a_quitar,
                    "registrado_por_id": str(interaction.user.id),
                    "mes_resultante": nuevo_mes,
                    "anio_resultante": nuevo_anio,
                }
            )

        await interaction.response.send_message(
            f"⚠️ Corrección aplicada a #{id_id}. Nuevo vencimiento: **{estado_texto(nuevo_mes, nuevo_anio)}**"
        )

    @app_commands.command(name="historial-pos", description="Ver historial de pagos de una POS")
    @es_ceo()
    async def historial_pos(self, interaction: discord.Interaction, id_id: int):
        outpost = await db.outpost.find_unique(where={"id_num": id_id})
        if not outpost:
            return await interaction.response.send_message(
                f"❌ No se encontró la POS #{id_id}.", ephemeral=True
            )

        pagos = await db.pago.find_many(
            where={"outpost_id": id_id}, order={"created_at": "desc"}
        )
        if not pagos:
            return await interaction.response.send_message(
                f"POS #{id_id} ({outpost.nombre_pos}) no tiene pagos registrados todavía."
            )

        header = f"{'Fecha':<17} | {'Tipo':<10} | {'Meses':<6} | {'Monto':<15} | {'Por'}\n"
        separator = "-" * 17 + "+" + "-" * 12 + "+" + "-" * 8 + "+" + "-" * 17 + "+" + "-" * 10 + "\n"

        def fmt_fila(p) -> str:
            fecha = p.created_at.strftime("%Y-%m-%d %H:%M")
            monto = f"{p.monto:,.2f}" if p.monto is not None else "-"
            return f"{fecha:<17} | {p.tipo:<10} | {p.meses:<6} | {monto:<15} | <@{p.registrado_por_id}>\n"

        titulo = f"**Historial de pagos — POS #{id_id} ({outpost.nombre_pos})**"
        paginas = construir_paginas(pagos, fmt_fila, header, separator, titulo=titulo)
        view = PaginadorView(paginas, autor_id=interaction.user.id)
        await interaction.response.send_message(view.render(), view=view)
        view.message = await interaction.original_response()


async def setup(bot: commands.Bot):
    bot.tree.add_command(registrar_pago_context)
    await bot.add_cog(PagosCog(bot))
