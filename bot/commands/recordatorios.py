from datetime import datetime

import discord
from discord import app_commands
from discord.ext import commands

from ..checks import es_ceo
from ..db import db
from ..utils import estado_texto


def _esta_moroso(outpost, anio_actual: int, mes_limite: int) -> bool:
    if outpost.pagado_hasta_mes == 0:
        return True
    if outpost.anio_vencimiento < anio_actual:
        return True
    return outpost.anio_vencimiento == anio_actual and outpost.pagado_hasta_mes < mes_limite


class RecordatoriosCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="recordar-mora",
        description="Etiqueta a quienes deban meses anteriores al mes límite",
    )
    @app_commands.describe(
        mes_limite="Si pones 2, etiqueta a los que tienen pagado Enero o Pendiente (1 o 0)"
    )
    @es_ceo()
    async def recordar_mora(
        self, interaction: discord.Interaction, mes_limite: app_commands.Range[int, 1, 12]
    ):
        await interaction.response.defer()

        anio_actual = datetime.now().year
        outposts = await db.outpost.find_many(include={"sistema": True}, order={"id_num": "asc"})
        morosos = [o for o in outposts if _esta_moroso(o, anio_actual, mes_limite)]

        if not morosos:
            return await interaction.followup.send(f"✅ Todos están al día con el mes {mes_limite}.")

        menciones = [
            f"- <@{o.discord_id}> | POS #{o.id_num} ({o.nombre_pos}) en **{o.sistema.nombre}** | "
            f"Pago: {estado_texto(o.pagado_hasta_mes, o.anio_vencimiento)}"
            for o in morosos
        ]

        lista_final = "\n".join(menciones)
        nombre_mes_limite = estado_texto(mes_limite, anio_actual).split(" ")[0]

        mensaje_alerta = (
            f"⚠️ **RECORDATORIO DE COBRO - MES {nombre_mes_limite.upper()}** ⚠️\n"
            f"Los siguientes pilotos tienen pagos pendientes o meses anteriores a {nombre_mes_limite}:\n\n"
            f"{lista_final}\n\n"
            f"Por favor, contacten con un CEO para pagar. ¡Eviten estarles molestando!"
        )

        await interaction.followup.send(mensaje_alerta)


async def setup(bot: commands.Bot):
    await bot.add_cog(RecordatoriosCog(bot))
