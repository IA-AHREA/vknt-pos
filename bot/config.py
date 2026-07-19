import os

from dotenv import load_dotenv

load_dotenv()


def _require(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(
            f"Falta la variable de entorno '{name}'. Revisa tu archivo .env o la configuración en Railway."
        )
    return value


DISCORD_TOKEN = _require("DISCORD_TOKEN")
CEO_ROLE_ID = int(_require("CEO_ROLE_ID"))

# DATABASE_URL la lee Prisma directamente del entorno, pero la validamos acá
# para fallar rápido con un mensaje claro en vez de un error críptico de Prisma.
_require("DATABASE_URL")
