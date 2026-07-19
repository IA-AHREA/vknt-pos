import discord
from discord import app_commands
from discord.ext import commands

COLOR_AYUDA = 0x3498DB


class AyudaCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="ayuda", description="Muestra todos los comandos disponibles")
    async def ayuda(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="📖 Comandos del bot de POS",
            description="👑 = solo lo puede usar un CEO.",
            color=COLOR_AYUDA,
        )
        embed.add_field(
            name="POS",
            value=(
                "👑 `/registrar-pos` — Registra una POS nueva (el ID se asigna solo)\n"
                "👑 `/borrar-pos` — Elimina una POS\n"
                "👑 `/buscar` — Busca las POS de un usuario y permite editar nombre/estado "
                "(la respuesta solo la ves vos)\n"
                "👑 `/reporte` — Lista de POS con estado de pago, filtro (todos/morosos/al día) "
                "y ordenada por urgencia"
            ),
            inline=False,
        )
        embed.add_field(
            name="Pagos",
            value=(
                "👑 Clic derecho sobre un mensaje → **Pagar Outpost** — Registra un pago "
                "(meses + monto en ISK opcional). Si el usuario tiene varias POS, primero "
                "pide elegir cuál\n"
                "👑 `/corregir-pago` — Resta meses por error\n"
                "👑 `/historial-pos` — Historial de pagos y correcciones de una POS\n"
                "👑 `/recordar-mora` — Etiqueta a quienes no tienen pagado el mes actual"
            ),
            inline=False,
        )
        embed.add_field(
            name="Sistemas EVE",
            value=(
                "👑 `/sistema-agregar` — Agrega un sistema a la lista\n"
                "`/sistema-listar` — Lista los sistemas disponibles\n"
                "👑 `/sistema-borrar` — Elimina un sistema (si no tiene POS asignadas)"
            ),
            inline=False,
        )
        embed.set_footer(text='"Pendiente" significa que la POS nunca pagó.')
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(AyudaCog(bot))
