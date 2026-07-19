import logging

import discord
from discord import app_commands
from discord.ext import commands

from . import db as db_module
from .config import CEO_ROLE_ID, DISCORD_TOKEN

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("vknt-pos")

EXTENSIONS = (
    "bot.commands.sistemas",
    "bot.commands.outposts",
    "bot.commands.pagos",
    "bot.commands.recordatorios",
)


class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        await db_module.connect()
        logger.info("Conectado a la base de datos.")

        for extension in EXTENSIONS:
            await self.load_extension(extension)

        await self.tree.sync()
        logger.info("Comandos sincronizados.")

    async def close(self):
        await db_module.disconnect()
        await super().close()


bot = MyBot()


@bot.event
async def on_ready():
    logger.info("✅ Bot iniciado como %s", bot.user)


@bot.tree.error
async def on_app_command_error(
    interaction: discord.Interaction, error: app_commands.AppCommandError
):
    if isinstance(error, app_commands.CheckFailure):
        mensaje = "❌ No autorizado."
    else:
        logger.exception(
            "Error en el comando '%s'",
            interaction.command.name if interaction.command else "?",
            exc_info=error,
        )
        mensaje = "❌ Ocurrió un error inesperado. Ya quedó registrado en los logs."

    if interaction.response.is_done():
        await interaction.followup.send(mensaje, ephemeral=True)
    else:
        await interaction.response.send_message(mensaje, ephemeral=True)


def main():
    if not CEO_ROLE_ID:
        raise RuntimeError("CEO_ROLE_ID no configurado.")
    bot.run(DISCORD_TOKEN, log_handler=None)


if __name__ == "__main__":
    main()
